// Tab switching
function switchTab(tab, btn) {
  document.querySelectorAll('.tab-section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + tab).classList.add('active');
  btn.classList.add('active');
}

// Search filter
function filterItems() {
  const query = document.getElementById('searchInput').value.toLowerCase();
  document.querySelectorAll('#itemsGrid .item-card').forEach(card => {
    const name = card.getAttribute('data-name') || '';
    card.style.display = name.includes(query) ? '' : 'none';
  });
}

// Category filter
let activeCategory = 'all';
function filterCategory(cat, btn) {
  activeCategory = cat;
  document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('#itemsGrid .item-card').forEach(card => {
    const cardCat = card.getAttribute('data-category') || '';
    card.style.display = (cat === 'all' || cardCat === cat) ? '' : 'none';
  });
}

// Image preview for post item form
function previewImage(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    const img = document.getElementById('previewImg');
    const placeholder = document.getElementById('imagePlaceholder');
    if (img) { img.src = e.target.result; img.style.display = 'block'; }
    if (placeholder) placeholder.style.display = 'none';
    const clearBtn = document.getElementById('clearBtn');
    if (clearBtn) clearBtn.style.display = 'inline-block';
  };
  reader.readAsDataURL(file);
}

function clearImage() {
  const input = document.getElementById('imageInput');
  const img = document.getElementById('previewImg');
  const placeholder = document.getElementById('imagePlaceholder');
  const clearBtn = document.getElementById('clearBtn');
  if (input) input.value = '';
  if (img) { img.src = ''; img.style.display = 'none'; }
  if (placeholder) placeholder.style.display = 'flex';
  if (clearBtn) clearBtn.style.display = 'none';
}

// Character counters
function updateCount(inputId, countId, max) {
  const el = document.getElementById(inputId);
  const counter = document.getElementById(countId);
  if (!el || !counter) return;
  const len = el.value.length;
  counter.textContent = len + ' / ' + max;
  counter.style.color = len > max * 0.9 ? '#e74c3c' : 'var(--text-light)';
}
