(() => {
  'use strict';
  const viewer = document.querySelector('#viewer');
  if (!viewer) return;
  const previews = [...document.querySelectorAll('.preview, [data-map-preview]')];
  const historyKey = viewer.dataset?.historyKey || 'annoStampViewer';
  let restoring = false;

  function savedViewer() {
    try { return window.history.state?.[historyKey]; }
    catch { return null; }
  }

  for (const preview of previews) {
    // The exporter opens the dialog first; this adds navigation without changing its UI.
    preview.addEventListener('click', () => {
      if (restoring || !viewer.open) return;
      try {
        window.history.pushState({...window.history.state, [historyKey]: {
          version: 1, source: preview.dataset.full, name: preview.dataset.name
        }}, '');
      } catch { /* The existing dialog remains usable with blocked history access. */ }
    });
  }

  viewer.addEventListener('close', () => {
    if (!viewer.open && savedViewer()?.version === 1) {
      try { window.history.back(); }
      catch { /* Closing the dialog must still work when navigation is blocked. */ }
    }
  });

  function restoreViewer() {
    const saved = savedViewer();
    const preview = saved?.version === 1 && previews.find(button =>
      button.dataset.full === saved.source && button.dataset.name === saved.name);
    if (preview) {
      if (viewer.open) return;
      restoring = true;
      try { preview.click(); }
      finally { restoring = false; }
    } else if (viewer.open) {
      viewer.close();
    }
  }

  window.addEventListener('popstate', restoreViewer);
  window.addEventListener('pageshow', restoreViewer);
  restoreViewer();
})();
