// Tab switching
function switchTab(tab, btn) {
  document.querySelectorAll('.tab-section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + tab).classList.add('active');
  btn.classList.add('active');
}

// Search / filter
function filterCommunities() {
  const query = document.getElementById('searchInput').value.toLowerCase();
  document.querySelectorAll('#communityGrid .community-card').forEach(card => {
    const name = card.getAttribute('data-name') || '';
    card.style.display = name.includes(query) ? '' : 'none';
  });
}
