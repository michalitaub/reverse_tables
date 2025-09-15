const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('pdf-input');
const pagesList = document.getElementById('pages-list');
const form = document.getElementById('upload-form');

dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', e => {
  e.preventDefault();
  dropZone.classList.add('dragover');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  fileInput.files = e.dataTransfer.files;
  fetchPages();
});
fileInput.addEventListener('change', fetchPages);

function fetchPages() {
  const f = fileInput.files[0];
  if (!f) return;
  const data = new FormData();
  data.append("pdf", f);
  fetch("/api/list_tr_pages", { method: "POST", body: data })
    .then(r => r.json())
    .then(j => {
      if (j.pages && j.pages.length) {
        pagesList.innerHTML = '<label class="form-label">בחר עמודים:</label>';
        j.pages.forEach(pg => {
          pagesList.innerHTML += `
          <div class="form-check">
            <input class="form-check-input" type="checkbox" name="pages" value="${pg}" id="pg${pg}">
            <label class="form-check-label" for="pg${pg}">עמוד ${pg}</label>
          </div>`;
        });
      } else {
        pagesList.innerHTML = '<p class="text-danger">לא נמצאו טבלאות בקובץ.</p>';
      }
    })
    .catch(err => {
      console.error(err);
      pagesList.innerHTML = '<p class="text-danger">שגיאה בקריאת עמודים.</p>';
    });
}

form.addEventListener('submit', function (e) {
  e.preventDefault();
  const pages = [...form.querySelectorAll('input[name="pages"]:checked')]
                 .map(cb => cb.value).join(',');
  const f = fileInput.files[0];
  if (!f) return alert("נא לבחור קובץ PDF");

  const data = new FormData();
  data.append("pdf", f);
  data.append("pages", pages);

  fetch("/", { method: "POST", body: data })
    .then(resp => resp.blob())
    .then(blob => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "output.pdf";
      a.click();
      window.URL.revokeObjectURL(url);
    });
});
