(() => {
  'use strict';
  const query = document.querySelector('#query');
  const mode = document.querySelector('#mode');
  const sort = document.querySelector('#sort');
  const count = document.querySelector('#count');
  const variants = document.querySelector('#variants');
  const cards = [...variants.querySelectorAll('article')];
  // Profiles are data, independent of whether the optional fallback paragraph exists.
  const profiles = new Map(cards.map(card => [card, JSON.parse(card.dataset.profiles)]));
  const backButtons = document.querySelectorAll('[data-back-to-profiles]');
  const ranking = document.querySelector('#profile-ranking');
  const controls = document.querySelector('#variant-filters');
  let selectedProfile = null;
  let returnLink = null;

  // Keep state on this history entry, including when opening a PNG replaces the page.
  function restoreState() {
    try {
      const saved = window.history.state?.annoMapCatalog;
      if (!saved || saved.version !== 1) return;
      if (typeof saved.query === 'string') query.value = saved.query;
      if (typeof saved.mode === 'string') mode.value = saved.mode;
      if (['latest', 'variant', 'first', 'totalTime'].includes(saved.sort)) sort.value = saved.sort;
      selectedProfile = typeof saved.profile === 'string' &&
        cards.some(card => profiles.get(card).includes(saved.profile)) ? saved.profile : null;
      returnLink = [...document.querySelectorAll('[data-profile-filter]')]
        .find(link => link.dataset.profileFilter === selectedProfile) || null;
    } catch { /* History access may be blocked for local files. */ }
  }

  function saveState() {
    try {
      window.history.replaceState({...window.history.state, annoMapCatalog: {
        version: 1, query: query.value, mode: mode.value, sort: sort.value, profile: selectedProfile
      }}, '');
    } catch { /* Filtering also works when history storage is unavailable. */ }
  }

  function refresh() {
    const search = query.value.trim().toLocaleLowerCase('de-CH');
    let shown = 0;
    for (const card of cards) {
      const names = profiles.get(card);
      const hit = selectedProfile !== null ? names.includes(selectedProfile) :
        /^\d+$/.test(search) ? card.dataset.seed === search :
        names.some(name => name.toLocaleLowerCase('de-CH').includes(search)) || search === '';
      card.hidden = !hit || Boolean(mode.value && card.dataset.mode !== mode.value);
      if (!card.hidden) shown++;
    }
    const key = sort.value;
    const direction = key === 'variant' || key === 'first' ? 1 : -1;
    variants.append(...[...cards].sort((a, b) => key === 'variant'
      ? Number(a.dataset.seed) - Number(b.dataset.seed) || Number(a.dataset.variant) - Number(b.dataset.variant)
      : direction * (Number(a.dataset[key]) - Number(b.dataset[key])) || Number(a.dataset.variant) - Number(b.dataset.variant)));
    for (const button of backButtons) button.hidden = selectedProfile === null;
    count.textContent = galleryI18n.t('map.count', {shown, total: cards.length});
    saveState();
  }

  function showCards() {
    refresh();
    query.focus({preventScroll: true});
    controls.scrollIntoView({block: 'start'});
  }

  query.addEventListener('input', () => { selectedProfile = null; refresh(); });
  mode.addEventListener('change', refresh);
  sort.addEventListener('change', refresh);
  for (const link of document.querySelectorAll('[data-profile-filter]')) {
    link.addEventListener('click', event => {
      event.preventDefault();
      selectedProfile = link.dataset.profileFilter;
      returnLink = link;
      query.value = selectedProfile;
      mode.value = '';
      showCards();
    });
  }
  for (const button of backButtons) {
    button.addEventListener('click', () => {
      selectedProfile = null;
      query.value = '';
      mode.value = '';
      refresh();
      ranking.open = true;
      (returnLink || ranking.querySelector('summary')).focus({preventScroll: true});
      ranking.scrollIntoView({block: 'start'});
      returnLink = null;
    });
  }
  for (const button of document.querySelectorAll('[data-filter]')) {
    button.addEventListener('click', () => {
      selectedProfile = null;
      query.value = button.dataset.filter;
      mode.value = '';
      showCards();
    });
  }
  document.addEventListener('gallerylanguagechange', refresh);
  window.addEventListener('pageshow', () => { restoreState(); refresh(); });
  restoreState();
  refresh();
})();
