# # from flask import Flask, render_template, request, send_file
# # import tempfile, os
# # from pathlib import Path
# # import subprocess
# #
# # from flask import Flask, render_template, request, send_file, jsonify
# # import tempfile, os, subprocess
# #
# # app = Flask(__name__)
# #
# # # ----- דף ראשי -----
# # @app.route("/", methods=["GET", "POST"])
# # def index():
# #     if request.method == "POST":
# #         # קבלת קובץ והעמודים
# #         f = request.files["pdf"]
# #         pages = request.form.get("pages", "")
# #         tmp_in = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
# #         tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
# #         tmp_in.close()
# #         tmp_out.close()
# #         f.save(tmp_in.name)
# #
# #         # קריאה לסקריפט הקיים שלך (לדוגמה withPages.py)
# #         cmd = ["python", "withPages.py", tmp_in.name, tmp_out.name]
# #         if pages:
# #             cmd += ["--pages", pages]
# #         subprocess.run(cmd, check=True)
# #
# #         return send_file(tmp_out.name,
# #                          as_attachment=True,
# #                          download_name="output.pdf")
# #
# #     return render_template("index.html")
# #
#
# # # ----- API מחזיר עמודים עם טבלאות -----
# # @app.route("/api/list_tr_pages", methods=["POST"])
# # def list_tr_pages():
# #     f = request.files["pdf"]
# #     tmp_in = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
# #     tmp_in.close()
# #     f.save(tmp_in.name)
# #
# #     # קריאה לסקריפט עם --list-tr-pages
# #     cmd = ["python", "withPages.py", tmp_in.name, "dummy.pdf", "--list-tr-pages"]
# #     result = subprocess.run(cmd, capture_output=True, text=True)
# #
# #     # כאן נניח שהסקריפט מחזיר JSON עם debug.tr_pages
# #     # את יכולה להתאים לפי הפלט המדויק שלך
# #     import json
# #     pages = []
# #     try:
# #         data = json.loads(result.stdout)
# #         if "debug" in data and "tr_pages" in data["debug"]:
# #             pages = list(data["debug"]["tr_pages"].keys())
# #     except Exception as e:
# #         print("Parsing error:", e)
# #
# #     return jsonify({"pages": pages})
#
# # app.py
# from flask import Flask, render_template, request, send_file, jsonify
# import tempfile, os, subprocess, sys, shutil
# from pathlib import Path
#
# app = Flask(__name__)
#
# @app.route("/", methods=["GET", "POST"])
# def index():
#     if request.method == "POST":
#         f = request.files.get("pdf")
#         if not f:
#             return "לא נבחר קובץ", 400
#
#         pages = (request.form.get("pages") or "").strip()
#
#         # קבצים זמניים
#         tmp_in  = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf");  tmp_in.close()
#         tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf");  tmp_out.close()
#         f.save(tmp_in.name)
#
#         # מריצים את withPages.py עם אותו מפרש פייתון של הסביבה
#         script = str(Path(__file__).with_name("withPages.py"))
#         cmd = [sys.executable, script, tmp_in.name, tmp_out.name]
#         if pages:
#             cmd += ["--pages", pages]
#
#         # מריצים ולוכדים פלט לשם דיבוג
#         run = subprocess.run(cmd, capture_output=True, text=True)
#
#         if run.returncode != 0:
#             # למשל: אם הקובץ אינו Tagged (withPages יוצא עם קוד != 0 במצבים מסוימים)
#             return (
#                 f"<h3>שגיאה בעיבוד</h3>"
#                 f"<pre>פקודה: {' '.join(cmd)}</pre>"
#                 f"<pre>stdout:\n{run.stdout}</pre>"
#                 f"<pre>stderr:\n{run.stderr}</pre>",
#                 500
#             )
#
#         # אימות קובץ הפלט
#         if not os.path.exists(tmp_out.name) or os.path.getsize(tmp_out.name) == 0:
#             # אם מכל סיבה אין פלט – נשמור לפחות עותק מקורי תקין
#             shutil.copyfile(tmp_in.name, tmp_out.name)
#
#         return send_file(tmp_out.name, as_attachment=True, download_name="output.pdf")
#
#     return render_template("index.html")
#
# @app.route("/api/list_tr_pages", methods=["POST"])
# def list_tr_pages():
#     f = request.files.get("pdf")
#     if not f:
#         return jsonify({"ok": False, "error": "no file"}), 400
#
#     tmp_in = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf"); tmp_in.close()
#     f.save(tmp_in.name)
#
#     script = str(Path(__file__).with_name("withPages.py"))
#     cmd = [sys.executable, script, tmp_in.name, "dummy.pdf", "--list-tr-pages"]
#     run = subprocess.run(cmd, capture_output=True, text=True)
#
#     if run.returncode != 0:
#         return jsonify({"ok": False, "error": "script failed", "stderr": run.stderr}), 500
#
#     import json
#     pages = []
#     try:
#         data = json.loads(run.stdout)
#         pages = list(data.get("debug", {}).get("tr_pages", {}).keys())
#     except Exception as e:
#         return jsonify({"ok": False, "error": f"parse error: {e}", "raw": run.stdout}), 500
#
#     return jsonify({"ok": True, "pages": pages})
#
# if __name__ == "__main__":
#     # host="0.0.0.0" מאפשר גישה ממחשב אחר ברשת אם תרצי
#     app.run(host="127.0.0.1", port=5000, debug=True)
#

# app.py
from flask import Flask, render_template, request, send_file, jsonify, after_this_request, abort
import tempfile, os, subprocess, sys, shutil, json
from pathlib import Path

app = Flask(__name__)

# הגדרת מגבלת גודל קבצים (למשל 100MB) כדי למנוע קריסות
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

def stream_to_temp_pdf(filestorage) -> str:
    """זירום הקובץ מהקליינט לדיסק בלי להחזיק בזיכרון."""
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as dst:
        # קריאה בחתיכות 1MB (התאם לפי הצורך)
        src = filestorage.stream
        for chunk in iter(lambda: src.read(1024 * 1024), b""):
            dst.write(chunk)
    return path

def safe_run(cmd, cwd=None, capture=False, timeout=None):
    """הרצת subprocess עם אפשרות ללא לכידת פלט כדי לחסוך זיכרון."""
    if capture:
        return subprocess.run(
            cmd, cwd=cwd, text=True, capture_output=True, check=False
        )
    # ללא לכידה: מפנה stdout/stderr לקבצים זמניים/DEVNULL
    with open(os.devnull, "w") as devnull:
        return subprocess.run(
            cmd, cwd=cwd, stdout=devnull, stderr=devnull, check=False
        )

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        f = request.files.get("pdf")
        if not f:
            return "לא נבחר קובץ", 400

        pages = (request.form.get("pages") or "").strip()

        # 1) לקובץ זמני על הדיסק בזרימה
        tmp_in = stream_to_temp_pdf(f)
        # 2) מסלול פלט
        fd_out, tmp_out = tempfile.mkstemp(suffix=".pdf")
        os.close(fd_out)

        # נוודא ניקוי קבצים בסוף הבקשה (גם אם יש שגיאה)
        @after_this_request
        def cleanup(response):
            for p in (tmp_in, tmp_out):
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass
            return response

        # 3) הרצת הסקריפט – ללא capture_output כדי לא לצבור פלט גדול בזיכרון
        script = str(Path(__file__).with_name("withPages.py"))
        cmd = [sys.executable, script, tmp_in, tmp_out]
        if pages:
            cmd += ["--pages", pages]

        run = safe_run(cmd, capture=False, timeout=None)

        if run.returncode != 0 or not os.path.exists(tmp_out) or os.path.getsize(tmp_out) == 0:
            # אם אין פלט – נחזיר את המקור (עדיף מסמך תקין מאשר שגיאה קשה)
            shutil.copyfile(tmp_in, tmp_out)

        # 4) שליחה בזרימה; Flask ישתמש ב־wsgi.file_wrapper כשזמין
        #    ביטול etag/conditional מקטין קצת עבודה מיותרת
        return send_file(tmp_out, as_attachment=True, download_name="output.pdf",
                         conditional=False, etag=False)

    return render_template("index.html")

@app.route("/api/list_tr_pages", methods=["POST"])
def list_tr_pages():
    f = request.files.get("pdf")
    if not f:
        return jsonify({"ok": False, "error": "no file"}), 400

    tmp_in = stream_to_temp_pdf(f)

    @after_this_request
    def cleanup(response):
        try:
            if os.path.exists(tmp_in):
                os.remove(tmp_in)
        except Exception:
            pass
        return response

    # כאן כן לוכדים כי מצופה JSON קטן
    script = str(Path(__file__).with_name("withPages.py"))
    cmd = [sys.executable, script, tmp_in, "dummy.pdf", "--list-tr-pages"]
    run = safe_run(cmd, capture=True)

    if run.returncode != 0:
        return jsonify({"ok": False, "error": "script failed", "stderr": run.stderr}), 500

    try:
        data = json.loads(run.stdout or "{}")
        pages = list(data.get("debug", {}).get("tr_pages", {}).keys())
    except Exception as e:
        return jsonify({"ok": False, "error": f"parse error: {e}", "raw": run.stdout}), 500

    return jsonify({"ok": True, "pages": pages})

if __name__ == "__main__":
    # בייצור: להריץ מאחורי gunicorn/uwsgi ולכבות debug
    app.run(host="127.0.0.1", port=5000, debug=True)

