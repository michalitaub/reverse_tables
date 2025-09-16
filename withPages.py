# # withPages.py
# # Flip table row cell order (LTR <-> RTL) in Tagged PDFs with robust page selection.
# # Prefers descendant /Pg (MCR) over inherited parent /Pg to handle multi-page tables correctly.
# #
# # Usage examples:
# #   List TR pages only (no changes):
# #       python withPages.py input.pdf output.pdf --list-tr-pages
# #   Flip only page 3:
# #       python withPages.py input.pdf output.pdf --pages "3" --verbose
# #   If no TR matched pages, flip all (fallback):
# #       python withPages.py input.pdf output.pdf --pages "3" --on-miss all
# #
# # Requires: pip install pikepdf
#
# import sys
# import argparse
# from pathlib import Path
# import json
# from typing import Optional, Set, Dict
#
# import pikepdf
#
# def is_name(x, literal: str) -> bool:
#     return isinstance(x, pikepdf.Name) and str(x) == literal
#
# def parse_pages(pages_str: str, total_pages: int) -> Set[int]:
#     if not pages_str:
#         return set()
#     out: Set[int] = set()
#     parts = [p.strip() for p in pages_str.split(",") if p.strip()]
#     for part in parts:
#         if "-" in part:
#             a, b = part.split("-", 1)
#             start, end = int(a), int(b)
#             if start > end:
#                 start, end = end, start
#             for i in range(start, end + 1):
#                 if 1 <= i <= total_pages:
#                     out.add(i)
#         else:
#             i = int(part)
#             if 1 <= i <= total_pages:
#                 out.add(i)
#     return out
#
# def build_page_index(pdf: pikepdf.Pdf) -> Dict[object, int]:
#     """Map page.objgen -> 1-based page number."""
#     mapping: Dict[object, int] = {}
#     for idx, page in enumerate(pdf.pages, start=1):
#         try:
#             mapping[page.objgen] = idx
#         except Exception:
#             pass
#         try:
#             mapping[page.get_object().objgen] = idx
#         except Exception:
#             pass
#     return mapping
#
# def get_elem_page_number_direct(elem, page_map: Dict[object, int]) -> int:
#     """Get page from elem's /Pg, or 0 if none."""
#     try:
#         obj = elem.get_object() if hasattr(elem, "get_object") else elem
#         if not isinstance(obj, pikepdf.Dictionary):
#             return 0
#         pg = obj.get("/Pg", None)
#         if pg is None:
#             return 0
#         pg_obj = pg.get_object() if hasattr(pg, "get_object") else pg
#         key = getattr(pg_obj, "objgen", None)
#         return page_map.get(key, 0)
#     except Exception:
#         return 0
#
# def find_descendant_page(elem, page_map: Dict[object, int], max_depth: int = 3) -> int:
#     """Shallow scan to find first /Pg in descendants (MCR/inner kids)."""
#     try:
#         if max_depth < 0:
#             return 0
#         obj = elem.get_object() if hasattr(elem, "get_object") else elem
#         if not isinstance(obj, pikepdf.Dictionary):
#             return 0
#
#         # try direct first
#         pgnum = get_elem_page_number_direct(obj, page_map)
#         if pgnum:
#             return pgnum
#
#         K = obj.get("/K", None)
#         if K is None:
#             return 0
#         if isinstance(K, pikepdf.Array):
#             for child in K:
#                 pgnum = find_descendant_page(child, page_map, max_depth - 1)
#                 if pgnum:
#                     return pgnum
#         else:
#             return find_descendant_page(K, page_map, max_depth - 1)
#         return 0
#     except Exception:
#         return 0
#
# def resolve_page_pref_descendant(elem, page_map: Dict[object, int], inherited_pg: int) -> int:
#     """
#     Resolve page number with priority:
#       1) direct /Pg on elem
#       2) descendant scan (MCR) up to depth
#       3) inherited from parent
#     """
#     direct = get_elem_page_number_direct(elem, page_map)
#     if direct:
#         return direct
#     desc = find_descendant_page(elem, page_map, max_depth=3)
#     if desc:
#         return desc
#     return inherited_pg or 0
#
# def collect_tr_pages(struct_root, page_map: Dict[object, int]) -> Dict[int, int]:
#     """Return {page_number: count_of_TR} across the structure tree."""
#     counts: Dict[int, int] = {}
#
#     def walk(elem, inherited_pg: int = 0):
#         try:
#             obj = elem.get_object() if hasattr(elem, "get_object") else elem
#             if not isinstance(obj, pikepdf.Dictionary):
#                 return
#             k = obj.get("/K", None)
#             s = obj.get("/S", None)
#
#             current_pg = resolve_page_pref_descendant(obj, page_map, inherited_pg)
#
#             if is_name(s, "/TR"):
#                 counts[current_pg] = counts.get(current_pg, 0) + 1
#
#             if k is not None:
#                 if isinstance(k, pikepdf.Array):
#                     for child in k:
#                         walk(child, current_pg)
#                 else:
#                     walk(k, current_pg)
#         except Exception:
#             return
#
#     walk(struct_root, 0)
#     return counts
#
# def reverse_row_cells_loose(tr_dict) -> int:
#     """
#     Try to reverse TR children. Primary path: /K is an array of cells (TD/TH/MCR).
#     Fallback: if /K is a dict or array with a single dict that itself has /K array,
#     try to reverse that inner array.
#     """
#     try:
#         if "/K" not in tr_dict:
#             return 0
#         K = tr_dict["/K"]
#
#         # Case 1: direct array
#         if isinstance(K, pikepdf.Array):
#             cells = list(K)
#             if len(cells) <= 1:
#                 return 0
#             tr_dict["/K"] = pikepdf.Array(reversed(cells))
#             return len(cells)
#
#         # Case 2: single dict with its own /K array (one-level nesting)
#         if isinstance(K, pikepdf.Dictionary):
#             inner = K.get("/K", None)
#             if isinstance(inner, pikepdf.Array):
#                 cells = list(inner)
#                 if len(cells) <= 1:
#                     return 0
#                 K["/K"] = pikepdf.Array(reversed(cells))
#                 return len(cells)
#
#         return 0
#     except Exception:
#         return 0
#
# def traverse_and_flip(struct_root, page_filter: Set[int], page_map: Dict[object, int],
#                       verbose: bool = False, on_miss: str = "abort"):
#     """
#     Walk structure tree:
#       - Determine effective page for each TR (direct /Pg -> descendant scan -> inherited).
#       - Reverse child order of TR that passes page filter.
#     on_miss: 'abort' (default) or 'all' — if no TR matched pages, flip all TRs instead.
#     """
#     tables = rows = cells = 0
#     tr_seen = 0
#     tr_matched = 0
#
#     # First pass: collect all TRs with their page numbers (using preferred descendant)
#     tr_nodes = []  # list of (obj, page_num)
#     def collect(elem, inherited_pg: int = 0):
#         nonlocal tr_seen
#         try:
#             obj = elem.get_object() if hasattr(elem, "get_object") else elem
#             if not isinstance(obj, pikepdf.Dictionary):
#                 return
#             s = obj.get("/S", None)
#             k = obj.get("/K", None)
#
#             current_pg = resolve_page_pref_descendant(obj, page_map, inherited_pg)
#
#             if is_name(s, "/TR"):
#                 tr_seen += 1
#                 tr_nodes.append((obj, current_pg))
#
#             if k is not None:
#                 if isinstance(k, pikepdf.Array):
#                     for child in k:
#                         collect(child, current_pg)
#                 else:
#                     collect(k, current_pg)
#         except Exception:
#             return
#
#     collect(struct_root, 0)
#
#     # Decide which TRs to flip
#     if page_filter:
#         candidates = [(obj, pg) for (obj, pg) in tr_nodes if pg in page_filter]
#         if not candidates and on_miss == "all":
#             candidates = tr_nodes[:]  # fallback: flip everything
#     else:
#         candidates = tr_nodes[:]
#
#     # Count tables in separate pass (simple)
#     def count_tables(elem):
#         nonlocal tables
#         try:
#             obj = elem.get_object() if hasattr(elem, "get_object") else elem
#             if not isinstance(obj, pikepdf.Dictionary):
#                 return
#             s = obj.get("/S", None)
#             k = obj.get("/K", None)
#             if is_name(s, "/Table"):
#                 tables += 1
#             if k is not None:
#                 if isinstance(k, pikepdf.Array):
#                     for child in k:
#                         count_tables(child)
#                 else:
#                     count_tables(k)
#         except Exception:
#             return
#
#     count_tables(struct_root)
#
#     # Flip
#     for obj, pg in candidates:
#         if verbose:
#             print(f"[flip] TR on page {pg or 'UNKNOWN'}")
#         c = reverse_row_cells_loose(obj)
#         if c > 0:
#             rows += 1
#             cells += c
#             tr_matched += 1
#
#     return {
#         "tables_found": tables,
#         "rows_processed": rows,
#         "cells_reversed": cells,
#         "tr_seen": tr_seen,
#         "tr_selected": len(candidates),
#         "tr_flipped": tr_matched
#     }
#
# def main():
#     ap = argparse.ArgumentParser(description="Flip table cells (LTR<->RTL) in Tagged PDFs with robust page selection.")
#     ap.add_argument("input_pdf", help="Tagged PDF input")
#     ap.add_argument("output_pdf", help="Output PDF (will overwrite)")
#     ap.add_argument("--pages", default="", help='e.g. "1,3,5-7". Empty = all pages')
#     ap.add_argument("--list-tr-pages", action="store_true", help="List pages that contain TR rows and exit")
#     ap.add_argument("--on-miss", choices=["abort", "all"], default="abort",
#                     help="If no TR matched selected pages: abort (default) or flip all TRs")
#     ap.add_argument("--verbose", action="store_true", help="Print verbose logs")
#     args = ap.parse_args()
#
#     input_pdf = Path(args.input_pdf)
#     output_pdf = Path(args.output_pdf)
#
#     result = {
#         "input": str(input_pdf),
#         "output": str(output_pdf),
#         "pages": args.pages or "ALL",
#         "tagged_pdf": False,
#         "tables_found": 0,
#         "rows_processed": 0,
#         "cells_reversed": 0,
#         "notes": [],
#         "debug": {}
#     }
#
#     with pikepdf.open(str(input_pdf)) as pdf:
#         root = pdf.Root
#         if "/StructTreeRoot" not in root:
#             result["notes"].append("אין /StructTreeRoot – הקובץ אינו מתויג (Tagged PDF).")
#             print(json.dumps(result, ensure_ascii=False, indent=2))
#             sys.exit(2)
#
#         struct_root = root["/StructTreeRoot"]
#         result["tagged_pdf"] = True
#
#         total_pages = len(list(pdf.pages))
#         page_filter = parse_pages(args.pages, total_pages)
#         page_map = build_page_index(pdf)
#
#         # Just list and exit?
#         if args.list_tr_pages:
#             counts = collect_tr_pages(struct_root, page_map)
#             result["debug"]["tr_pages"] = counts
#             print(json.dumps(result, ensure_ascii=False, indent=2))
#             return
#
#         stats = traverse_and_flip(struct_root, page_filter, page_map,
#                                   verbose=args.verbose, on_miss=args.on_miss)
#
#         result["tables_found"] = stats["tables_found"]
#         result["rows_processed"] = stats["rows_processed"]
#         result["cells_reversed"] = stats["cells_reversed"]
#         result["debug"].update({
#             "tr_seen": stats["tr_seen"],
#             "tr_selected": stats["tr_selected"],
#             "tr_flipped": stats["tr_flipped"]
#         })
#
#         # Save (overwrite; fallback if locked)
#         try:
#             output_pdf.unlink(missing_ok=True)
#         except PermissionError:
#             pass
#         try:
#             pdf.save(str(output_pdf))
#         except PermissionError:
#             from datetime import datetime
#             fallback = output_pdf.with_stem(output_pdf.stem + "_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
#             pdf.save(str(fallback))
#             result["notes"].append(f'קובץ הפלט היה נעול. נשמר בשם חלופי: "{fallback.name}"')
#
#     print(json.dumps(result, ensure_ascii=False, indent=2))
#
# if __name__ == "__main__":
#     main()

# withPages.py (low-memory)
# Flip table row cell order (LTR <-> RTL) in Tagged PDFs with robust page selection.
# Memory-friendly: no list(pdf.pages), no TR node accumulation, iterative traversal.

import sys
import argparse
from pathlib import Path
import json
from typing import Set, Dict, Tuple, Iterator

import pikepdf

def is_name(x, literal: str) -> bool:
    return isinstance(x, pikepdf.Name) and str(x) == literal

def parse_pages(pages_str: str, total_pages: int) -> Set[int]:
    if not pages_str:
        return set()
    out: Set[int] = set()
    parts = [p.strip() for p in pages_str.split(",") if p.strip()]
    for part in parts:
        if "-" in part:
            a, b = part.split("-", 1)
            start, end = int(a), int(b)
            if start > end:
                start, end = end, start
            for i in range(start, end + 1):
                if 1 <= i <= total_pages:
                    out.add(i)
        else:
            i = int(part)
            if 1 <= i <= total_pages:
                out.add(i)
    return out

def build_page_index(pdf: pikepdf.Pdf) -> Dict[object, int]:
    """Map page.objgen -> 1-based page number, without materializing list(pdf.pages)."""
    mapping: Dict[object, int] = {}
    for idx, page in enumerate(pdf.pages, start=1):
        try:
            mapping[page.objgen] = idx
        except Exception:
            pass
        # לרוב זה מיותר, אבל שומר תאימות למקרים בהם get_object מחזיר מזהה שונה
        try:
            mapping[page.get_object().objgen] = idx
        except Exception:
            pass
    return mapping

def _get_obj(x):
    return x.get_object() if hasattr(x, "get_object") else x

def get_elem_page_number_direct(elem, page_map: Dict[object, int]) -> int:
    try:
        obj = _get_obj(elem)
        if not isinstance(obj, pikepdf.Dictionary):
            return 0
        pg = obj.get("/Pg", None)
        if pg is None:
            return 0
        pg_obj = _get_obj(pg)
        key = getattr(pg_obj, "objgen", None)
        return page_map.get(key, 0)
    except Exception:
        return 0

def find_descendant_page(elem, page_map: Dict[object, int], max_depth: int = 3) -> int:
    try:
        if max_depth < 0:
            return 0
        obj = _get_obj(elem)
        if not isinstance(obj, pikepdf.Dictionary):
            return 0

        # direct first
        pgnum = get_elem_page_number_direct(obj, page_map)
        if pgnum:
            return pgnum

        K = obj.get("/K", None)
        if K is None:
            return 0

        # איטרטיבי רדוד במקום רקורסיה עמוקה
        def children_iter(k):
            if isinstance(k, pikepdf.Array):
                for c in k:
                    yield c
            else:
                yield k

        depth = 0
        frontier = list(children_iter(K))
        while frontier and depth < max_depth:
            next_frontier = []
            for ch in frontier:
                pgnum = get_elem_page_number_direct(ch, page_map)
                if pgnum:
                    return pgnum
                ch_obj = _get_obj(ch)
                if isinstance(ch_obj, pikepdf.Dictionary) and "/K" in ch_obj:
                    next_frontier.extend(list(children_iter(ch_obj["/K"])))
            frontier = next_frontier
            depth += 1
        return 0
    except Exception:
        return 0

def resolve_page_pref_descendant(elem, page_map: Dict[object, int], inherited_pg: int) -> int:
    direct = get_elem_page_number_direct(elem, page_map)
    if direct:
        return direct
    desc = find_descendant_page(elem, page_map, max_depth=3)
    if desc:
        return desc
    return inherited_pg or 0

def iter_struct(struct_root, page_map: Dict[object, int]) -> Iterator[Tuple[pikepdf.Dictionary, int]]:
    """
    איטרטור על כל ה־Dictionary בעץ המבנה, ללא רקורסיה.
    מחזיר (האובייקט, מספר העמוד האפקטיבי).
    """
    stack: list[Tuple[object, int]] = [(struct_root, 0)]
    while stack:
        elem, inherited_pg = stack.pop()
        try:
            obj = _get_obj(elem)
            if not isinstance(obj, pikepdf.Dictionary):
                continue
            current_pg = resolve_page_pref_descendant(obj, page_map, inherited_pg)
            yield obj, current_pg
            K = obj.get("/K", None)
            if K is not None:
                if isinstance(K, pikepdf.Array):
                    # הוספה בסדר הפוך כדי לשמור על סדר טבעי ב-pop()
                    for child in reversed(list(K)):
                        stack.append((child, current_pg))
                else:
                    stack.append((K, current_pg))
        except Exception:
            continue

def reverse_row_cells_loose(tr_dict) -> int:
    try:
        if "/K" not in tr_dict:
            return 0
        K = tr_dict["/K"]

        if isinstance(K, pikepdf.Array):
            n = len(K)
            if n <= 1:
                return 0
            # לא להעתיק לרשימה ואז להפוך — Array חדש ישר מ־iter הפוך
            tr_dict["/K"] = pikepdf.Array(reversed(list(K)))
            return n

        if isinstance(K, pikepdf.Dictionary):
            inner = K.get("/K", None)
            if isinstance(inner, pikepdf.Array):
                n = len(inner)
                if n <= 1:
                    return 0
                K["/K"] = pikepdf.Array(reversed(list(inner)))
                return n

        return 0
    except Exception:
        return 0

def collect_tr_pages(struct_root, page_map: Dict[object, int]) -> Dict[int, int]:
    counts: Dict[int, int] = {}
    for obj, pg in iter_struct(struct_root, page_map):
        try:
            s = obj.get("/S", None)
            if is_name(s, "/TR"):
                counts[pg] = counts.get(pg, 0) + 1
        except Exception:
            continue
    return counts

def traverse_and_flip(struct_root, page_filter: Set[int], page_map: Dict[object, int],
                      verbose: bool = False, on_miss: str = "abort"):
    tables = 0
    rows = 0
    cells = 0
    tr_seen = 0

    # שלב 1: לבדוק האם יש התאמות בפילטר (בלי לאגור צמתים)
    matched_exists = False
    if page_filter:
        for obj, pg in iter_struct(struct_root, page_map):
            try:
                s = obj.get("/S", None)
                if is_name(s, "/TR"):
                    tr_seen += 1
                    if pg in page_filter:
                        matched_exists = True
                elif is_name(s, "/Table"):
                    tables += 1
            except Exception:
                continue
    else:
        # אם אין פילטר, נצבור רק טבלאות בסטייג' הזה
        for obj, _ in iter_struct(struct_root, page_map):
            try:
                s = obj.get("/S", None)
                if is_name(s, "/Table"):
                    tables += 1
                if is_name(s, "/TR"):
                    tr_seen += 1
            except Exception:
                continue
        matched_exists = True  # “הכול מתאים”

    # לקבוע את פרדיקט הבחירה לפי on_miss
    def candidate(pg: int) -> bool:
        if not page_filter:
            return True
        if matched_exists:
            return pg in page_filter
        # אין התאמות – אם on_miss='all' נהפוך הכול; אחרת לא נהפוך כלום
        return on_miss == "all"

    tr_selected = 0
    tr_flipped = 0

    # שלב 2: מעבר שני – הופך בפועל רק את המועמדים
    for obj, pg in iter_struct(struct_root, page_map):
        try:
            s = obj.get("/S", None)
            if is_name(s, "/TR") and candidate(pg):
                tr_selected += 1
                if verbose:
                    print(f"[flip] TR on page {pg or 'UNKNOWN'}")
                c = reverse_row_cells_loose(obj)
                if c > 0:
                    rows += 1
                    cells += c
                    tr_flipped += 1
        except Exception:
            continue

    return {
        "tables_found": tables,
        "rows_processed": rows,
        "cells_reversed": cells,
        "tr_seen": tr_seen,
        "tr_selected": tr_selected,
        "tr_flipped": tr_flipped,
        "matched_exists": matched_exists,
    }

def main():
    ap = argparse.ArgumentParser(description="Flip table cells (LTR<->RTL) in Tagged PDFs with robust page selection.")
    ap.add_argument("input_pdf", help="Tagged PDF input")
    ap.add_argument("output_pdf", help="Output PDF (will overwrite)")
    ap.add_argument("--pages", default="", help='e.g. "1,3,5-7". Empty = all pages')
    ap.add_argument("--list-tr-pages", action="store_true", help="List pages that contain TR rows and exit")
    ap.add_argument("--on-miss", choices=["abort", "all"], default="abort",
                    help="If no TR matched selected pages: abort (default) or flip all TRs")
    ap.add_argument("--verbose", action="store_true", help="Print verbose logs")
    ap.add_argument("--pretty", action="store_true", help="Pretty-print JSON (for debugging)")
    args = ap.parse_args()

    input_pdf = Path(args.input_pdf)
    output_pdf = Path(args.output_pdf)

    result = {
        "input": str(input_pdf),
        "output": str(output_pdf),
        "pages": args.pages or "ALL",
        "tagged_pdf": False,
        "tables_found": 0,
        "rows_processed": 0,
        "cells_reversed": 0,
        "notes": [],
        "debug": {}
    }

    with pikepdf.open(str(input_pdf)) as pdf:
        root = pdf.Root
        if "/StructTreeRoot" not in root:
            result["notes"].append("אין /StructTreeRoot – הקובץ אינו מתויג (Tagged PDF).")
            print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, separators=(",", ":")))
            sys.exit(2)

        struct_root = root["/StructTreeRoot"]
        result["tagged_pdf"] = True

        total_pages = len(pdf.pages)  # לא list(pdf.pages)!
        page_filter = parse_pages(args.pages, total_pages)
        page_map = build_page_index(pdf)

        if args.list_tr_pages:
            counts = collect_tr_pages(struct_root, page_map)
            result["debug"]["tr_pages"] = counts
            print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, separators=(",", ":")))
            return

        stats = traverse_and_flip(struct_root, page_filter, page_map,
                                  verbose=args.verbose, on_miss=args.on_miss)

        result["tables_found"] = stats["tables_found"]
        result["rows_processed"] = stats["rows_processed"]
        result["cells_reversed"] = stats["cells_reversed"]
        result["debug"].update({
            "tr_seen": stats["tr_seen"],
            "tr_selected": stats["tr_selected"],
            "tr_flipped": stats["tr_flipped"],
            "matched_exists": stats["matched_exists"]
        })

        # Save (overwrite; fallback if locked)
        try:
            output_pdf.unlink(missing_ok=True)
        except PermissionError:
            pass
        try:
            pdf.save(str(output_pdf))
        except PermissionError:
            from datetime import datetime
            fallback = output_pdf.with_stem(output_pdf.stem + "_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
            pdf.save(str(fallback))
            result["notes"].append(f'קובץ הפלט היה נעול. נשמר בשם חלופי: "{fallback.name}"')

    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, separators=(",", ":")))

if __name__ == "__main__":
    main()
