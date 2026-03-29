// Emoji selection
function selectEmoji(emoji, btn) {
  document.querySelectorAll('.emoji-btn').forEach(b => b.classList.remove('selected'));
  btn.classList.add('selected');
  document.getElementById('iconInput').value = emoji;
  document.getElementById('selectedEmojiDisplay').textContent = emoji;
}

// Set first emoji as selected on load
window.addEventListener('DOMContentLoaded', () => {
  const first = document.querySelector('.emoji-btn');
  if (first) first.classList.add('selected');
});

// Color selection
function selectColor(color, btn) {
  document.querySelectorAll('.color-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('colorInput').value = color;
}

// Image preview
function previewImage(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    const img = document.getElementById('previewImg');
    const placeholder = document.getElementById('imagePlaceholder');
    img.src = e.target.result;
    img.style.display = 'block';
    placeholder.style.display = 'none';
    document.getElementById('clearBtn').style.display = 'inline-block';
  };
  reader.readAsDataURL(file);
}

// Clear image
function clearImage() {
  document.getElementById('imageInput').value = '';
  const img = document.getElementById('previewImg');
  img.src = ''; img.style.display = 'none';
  document.getElementById('imagePlaceholder').style.display = 'flex';
  document.getElementById('clearBtn').style.display = 'none';
}

// Character counters
function updateNameCount() {
  const val = document.getElementById('name').value.length;
  const counter = document.getElementById('nameCount');
  counter.textContent = val + ' / 50';
  counter.style.color = val > 40 ? '#e74c3c' : 'var(--text-light)';
}

function updateDescCount() {
  const val = document.getElementById('description').value.length;
  const counter = document.getElementById('descCount');
  counter.textContent = val + ' / 300';
  counter.style.color = val > 260 ? '#e74c3c' : 'var(--text-light)';
}
