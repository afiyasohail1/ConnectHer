// Toggle comment section open/close
function toggleComments(id) {
  const section = document.getElementById(id);
  if (!section) return;
  const isOpen = section.style.display !== 'none';
  section.style.display = isOpen ? 'none' : 'block';
}

// Toggle edit/delete dropdown menu
function toggleMenu(id) {
  const menu = document.getElementById(id);
  if (!menu) return;
  // Close all other open menus first
  document.querySelectorAll('.dropdown-menu.open').forEach(m => {
    if (m.id !== id) m.classList.remove('open');
  });
  menu.classList.toggle('open');
}

// Close menus when clicking outside
document.addEventListener('click', function(e) {
  if (!e.target.closest('.post-menu')) {
    document.querySelectorAll('.dropdown-menu.open').forEach(m => m.classList.remove('open'));
  }
});

// Character count for post textarea
function updateCharCount() {
  const textarea = document.getElementById('postContent');
  const counter  = document.getElementById('charCount');
  if (!textarea || !counter) return;
  const len = textarea.value.length;
  counter.textContent = len + ' / 1000';
  counter.style.color = len > 900 ? '#e74c3c' : 'var(--text-light)';
}

// Image preview before uploading
function previewImage(event) {
  const file    = event.target.files[0];
  const preview = document.getElementById('imagePreview');
  const img     = document.getElementById('previewImg');
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    img.src = e.target.result;
    preview.style.display = 'block';
  };
  reader.readAsDataURL(file);
}

// Clear image preview
function clearImage() {
  document.getElementById('imageUpload').value = '';
  document.getElementById('previewImg').src = '';
  document.getElementById('imagePreview').style.display = 'none';
}
