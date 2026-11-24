(() => {
  'use strict';
  const viewer = document.querySelector('#viewer');
  if (!viewer || typeof viewer.showModal !== 'function') return;
  const full = document.querySelector('#full');
  const title = document.querySelector('#modalname');
  const download = document.querySelector('#download');
  const zoom = document.querySelector('#zoom');
  let current = null;

  function updateLabels() {
    if (current) {
      full.alt = current.querySelector('img').alt;
      title.textContent = full.alt;
    }
    const key = full.classList.contains('zoomed') ? 'viewer.fit' : 'viewer.originalSize';
    zoom.dataset.i18n = key;
    zoom.textContent = galleryI18n.t(key);
    zoom.setAttribute('aria-pressed', String(full.classList.contains('zoomed')));
  }

  for (const link of document.querySelectorAll('article a[href]')) {
    if (!link.querySelector('img')) continue;
    const source = link.getAttribute('href');
    link.dataset.mapPreview = '';
    link.dataset.full = source;
    link.dataset.name = source;
    link.addEventListener('click', event => {
      // Preserve native open-in-new-tab actions and the no-dialog PNG fallback.
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button > 0) return;
      event.preventDefault();
      current = link;
      full.src = source;
      full.classList.remove('zoomed');
      download.href = source;
      download.download = source.split(/[\\/]/).pop();
      updateLabels();
      viewer.showModal();
      full.parentElement.scrollTop = 0;
      full.parentElement.scrollLeft = 0;
    });
  }
  function toggleZoom() {
    full.classList.toggle('zoomed');
    updateLabels();
  }
  zoom.addEventListener('click', toggleZoom);
  full.addEventListener('click', toggleZoom);
  document.querySelector('#close').addEventListener('click', () => viewer.close());
  viewer.addEventListener('click', event => { if (event.target === viewer) viewer.close(); });
  document.addEventListener('gallerylanguagechange', updateLabels);
})();
