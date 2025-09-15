# flip_tables_simple.py
# הופך סדר תאים בכל שורה של טבלאות ב-PDF מתויג (LTR <-> RTL) – על כל המסמך.
# דרוש: pip install pikepdf

import sys
from pathlib import Path
import json
import pikepdf

def is_name(x, literal: str) -> bool:
    return isinstance(x, pikepdf.Name) and str(x) == literal

def reverse_row_cells(tr_dict) -> int:
    """
    מקבל אלמנט /TR ומנסה להפוך את רשימת הילדים (/K) – שהם התאים.
    מחזיר כמה תאים הוחזרו (0 אם אין מה להפוך).
    """
    if "/K" not in tr_dict:
        return 0
    kids = tr_dict["/K"]
    if isinstance(kids, pikepdf.Array):
        cells = list(kids)
        tr_dict["/K"] = pikepdf.Array(reversed(cells))
        return len(cells)
    return 0

def traverse_and_flip(struct_root):
    tables = rows = cells = 0

    def walk(elem):
        nonlocal tables, rows, cells
        try:
            obj = elem.get_object() if hasattr(elem, "get_object") else elem
            if not isinstance(obj, pikepdf.Dictionary):
                return
            s = obj.get("/S", None)
            k = obj.get("/K", None)

            if is_name(s, "/Table"):
                tables += 1
            if is_name(s, "/TR"):
                c = reverse_row_cells(obj)
                if c > 0:
                    rows += 1
                    cells += c

            if k is not None:
                if isinstance(k, pikepdf.Array):
                    for child in k:
                        walk(child)
                else:
                    walk(k)
        except Exception:
            # לא נכשלים על שגיאה נקודתית – ממשיכים
            return

    walk(struct_root)
    return tables, rows, cells

def main():
    if len(sys.argv) != 3:
        print("שימוש: python flip_tables_simple.py input.pdf output.pdf")
        sys.exit(1)

    input_pdf = Path(sys.argv[1])
    output_pdf = Path(sys.argv[2])

    result = {
        "input": str(input_pdf),
        "output": str(output_pdf),
        "tagged_pdf": False,
        "tables_found": 0,
        "rows_processed": 0,
        "cells_reversed": 0,
        "notes": []
    }

    with pikepdf.open(str(input_pdf)) as pdf:
        root = pdf.Root
        if "/StructTreeRoot" not in root:
            result["notes"].append("אין /StructTreeRoot – הקובץ אינו מתויג.")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            sys.exit(2)

        result["tagged_pdf"] = True
        struct_root = root["/StructTreeRoot"]
        t, r, c = traverse_and_flip(struct_root)
        result["tables_found"] = t
        result["rows_processed"] = r
        result["cells_reversed"] = c

        # שומרים תמיד כקובץ חדש
        pdf.save(str(output_pdf))

    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
