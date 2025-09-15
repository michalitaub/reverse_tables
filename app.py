# from flask import Flask, render_template, request, send_file
# import tempfile, os
# from pathlib import Path
# import subprocess
#
# app = Flask(__name__)
#
# @app.route("/", methods=["GET", "POST"])
# def index():
#     if request.method == "POST":
#         file = request.files["pdf"]
#         pages = request.form.get("pages", "")
#
#         # שמירה זמנית
#         tmp_in = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
#         file.save(tmp_in.name)
#         tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
#         tmp_out.close()
#
#         # קריאה לסקריפט שלך (כמודול או subprocess)
#         cmd = ["python", "withPages.py", tmp_in.name, tmp_out.name, "--pages", pages]
#         subprocess.run(cmd, check=True)
#
#         return send_file(tmp_out.name, as_attachment=True, download_name="output.pdf")
#
#     return '''
#     <h1>הפוך טבלאות PDF</h1>
#     <form method="post" enctype="multipart/form-data">
#       <input type="file" name="pdf" required><br><br>
#       <label>עמודים (למשל: 1,3,5-7):</label><br>
#       <input type="text" name="pages"><br><br>
#       <button type="submit">העלה והפוך</button>
#     </form>
#     '''
#
# if __name__ == "__main__":
#     app.run(debug=True)

from flask import Flask, render_template, request, send_file, jsonify
import tempfile, os, subprocess

app = Flask(__name__)

# ----- דף ראשי -----
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # קבלת קובץ והעמודים
        f = request.files["pdf"]
        pages = request.form.get("pages", "")
        tmp_in = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp_in.close()
        tmp_out.close()
        f.save(tmp_in.name)

        # קריאה לסקריפט הקיים שלך (לדוגמה withPages.py)
        cmd = ["python", "withPages.py", tmp_in.name, tmp_out.name]
        if pages:
            cmd += ["--pages", pages]
        subprocess.run(cmd, check=True)

        return send_file(tmp_out.name,
                         as_attachment=True,
                         download_name="output.pdf")

    return render_template("index.html")


# ----- API מחזיר עמודים עם טבלאות -----
@app.route("/api/list_tr_pages", methods=["POST"])
def list_tr_pages():
    f = request.files["pdf"]
    tmp_in = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp_in.close()
    f.save(tmp_in.name)

    # קריאה לסקריפט עם --list-tr-pages
    cmd = ["python", "withPages.py", tmp_in.name, "dummy.pdf", "--list-tr-pages"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    # כאן נניח שהסקריפט מחזיר JSON עם debug.tr_pages
    # את יכולה להתאים לפי הפלט המדויק שלך
    import json
    pages = []
    try:
        data = json.loads(result.stdout)
        if "debug" in data and "tr_pages" in data["debug"]:
            pages = list(data["debug"]["tr_pages"].keys())
    except Exception as e:
        print("Parsing error:", e)

    return jsonify({"pages": pages})


if __name__ == "__main__":
    # host="0.0.0.0" מאפשר גישה ממחשב אחר ברשת אם תרצי
    app.run(host="127.0.0.1", port=5000, debug=True)

