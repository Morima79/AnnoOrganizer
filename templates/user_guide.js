// Keep the manual language and screenshots together, including direct app links.
(() => {
  'use strict';
  function showLanguage() {
    for (const section of document.querySelectorAll('[data-guide-language]')) {
      section.hidden = section.dataset.guideLanguage !== galleryI18n.language;
    }
  }
  document.addEventListener('gallerylanguagechange', showLanguage);
  const requested = new URLSearchParams(location.search).get('lang');
  if (requested === 'de' || requested === 'en') galleryI18n.setLanguage(requested);
  showLanguage();
})();
