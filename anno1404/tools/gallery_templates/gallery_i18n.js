/* Offline gallery localisation. Resources and this runtime are embedded in HTML. */
(() => {
  'use strict';
  const resources = JSON.parse(document.getElementById('gallery-language-resources').textContent);
  const storageKey = 'annotools.gallery.language';
  let language = 'de';
  const namedParameters = new Set(['region', 'label']);
  const reverse = new Map(Object.entries(resources.de).filter(([, value]) => !value.includes('{')).map(([key, value]) => [value, key]));

  function value(text, locale = language) {
    const key = reverse.get(String(text));
    return key ? (resources[locale][key] ?? resources.de[key]) : String(text);
  }

  function translate(locale, key, params = {}) {
    if (key === 'map.summary') {
      return ['seeds', 'variants', 'saves'].map(unit => translate(locale, 'summary.' + unit, {count: params[unit]})).join(' · ');
    }
    const count = params.total ?? params.count;
    if (Number(count) === 1 && Object.hasOwn(resources.de, key + '.one')) key += '.one';
    const message = resources[locale][key] ?? resources.de[key] ?? key;
    return message.replace(/\{([a-zA-Z]+)\}/g, (_, name) => {
      const parameter = params[name] ?? '';
      return namedParameters.has(name) ? value(parameter, locale) : String(parameter);
    });
  }

  const t = (key, params = {}) => translate(language, key, params);
  const searchCache = new WeakMap();
  function searchText(element) {
    if (!searchCache.has(element)) {
      const translations = [...element.querySelectorAll('[data-i18n]')].flatMap(node =>
        ['de', 'en'].map(locale => translate(locale, node.getAttribute('data-i18n'), parameters(node, ''))));
      searchCache.set(element, [element.textContent, ...translations].join(' '));
    }
    return searchCache.get(element);
  }

  function parameters(element, suffix) {
    return JSON.parse(element.getAttribute('data-i18n' + suffix + '-params') || '{}');
  }

  function apply() {
    document.documentElement.lang = language === 'de' ? 'de-CH' : 'en';
    for (const element of document.querySelectorAll('[data-i18n]')) {
      element.textContent = t(element.getAttribute('data-i18n'), parameters(element, ''));
    }
    for (const attribute of ['placeholder', 'aria-label', 'title', 'alt', 'content']) {
      for (const element of document.querySelectorAll('[data-i18n-' + attribute + ']')) {
        element.setAttribute(attribute, t(element.getAttribute('data-i18n-' + attribute), parameters(element, '-' + attribute)));
      }
    }
    for (const button of document.querySelectorAll('[data-gallery-language]')) {
      button.setAttribute('aria-pressed', String(button.dataset.galleryLanguage === language));
    }
  }

  function setLanguage(next) {
    if (!Object.hasOwn(resources, next)) return;
    language = next;
    try { localStorage.setItem(storageKey, next); } catch { /* Local files or storage disabled. */ }
    apply();
    document.dispatchEvent(new CustomEvent('gallerylanguagechange', {detail: {language}}));
  }

  window.galleryI18n = {t, value, searchText, setLanguage, get language() { return language; }};
  for (const button of document.querySelectorAll('[data-gallery-language]')) {
    button.addEventListener('click', () => setLanguage(button.dataset.galleryLanguage));
  }
  try {
    const stored = localStorage.getItem(storageKey);
    if (Object.hasOwn(resources, stored)) language = stored;
  } catch { /* German remains usable when storage is unavailable. */ }
  apply();
})();
