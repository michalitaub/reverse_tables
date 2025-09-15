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
        renderPages(j.pages);
      } else {
        pagesList.innerHTML = '<p class="text-danger">לא נמצאו טבלאות בקובץ.</p>';
      }
    })
    .catch(err => {
      console.error(err);
      pagesList.innerHTML = '<p class="text-danger">שגיאה בקריאת עמודים.</p>';
    });
}

/* === חדש: יצירת הרשימה + "בחר הכל" === */
function renderPages(pages) {
  pagesList.innerHTML = `
    <div class="d-flex flex-column align-items-start gap-2 mb-2">
      <label class="form-label m-0">בחר עמודים:</label>
      <div class="form-check d-inline-flex flex-row-reverse align-items-center gap-2">
        <label class="form-check-label" for="selectAll">בחר הכל</label>
        <input class="form-check-input" type="checkbox" id="selectAll">
      </div>
    </div>
    <div id="page-items"></div>
  `;

  const items = document.getElementById('page-items');

  pages.forEach(pg => {
    items.insertAdjacentHTML('beforeend', `
      <div class="form-check d-inline-flex flex-row-reverse align-items-center gap-2 me-3 mb-2">
        <label class="form-check-label" for="pg${pg}">עמוד ${pg}</label>
        <input class="form-check-input page-cb" type="checkbox" name="pages" value="${pg}" id="pg${pg}">
      </div>
    `);
  });

  const selectAll = document.getElementById('selectAll');
  const pageCbs = [...document.querySelectorAll('.page-cb')];

  // סימון/ביטול של כולם
  selectAll.addEventListener('change', () => {
    pageCbs.forEach(cb => cb.checked = selectAll.checked);
    updateMasterState();
  });

  // עדכון מצב "בחר הכל" לפי בחירות המשתמש
  pageCbs.forEach(cb => cb.addEventListener('change', updateMasterState));

  function updateMasterState() {
    const total = pageCbs.length;
    const checked = pageCbs.filter(cb => cb.checked).length;
    selectAll.indeterminate = checked > 0 && checked < total;
    selectAll.checked = checked === total;
  }
}

form.addEventListener('submit', function (e) {
  e.preventDefault();
  const selected = [...form.querySelectorAll('input[name="pages"]:checked')];
  if (selected.length === 0) return alert("נא לבחור לפחות עמוד אחד או 'בחר הכל'.");

  const pages = selected.map(cb => cb.value).join(',');
  const f = fileInput.files[0];
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

