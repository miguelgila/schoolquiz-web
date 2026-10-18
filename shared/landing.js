// Landing page: one card per entry of window.QUIZZES, plus the static shell strings.
// Expects index.html and window.I18N / window.QUIZZES loaded first.
(function () {
  const I = window.I18N;
  const QUIZZES = window.QUIZZES || [];
  const L = I.langs[0][0];

  // t(key, ...args): UI string with {0}, {1} replaced; falls back to Italian, then to the key itself.
  const t = (key, ...args) => {
    const u = I.ui[L] || {};
    const s = u[key] != null ? u[key] : (I.ui.it[key] != null ? I.ui.it[key] : key);
    return s.replace(/\{(\d)\}/g, (m, i) => (args[i] != null ? String(args[i]) : m));
  };

  // Strings of the static shell (data-i18n), spelled as literal t() calls
  // so tools/test_i18n.py sees them; any other data-i18n key falls back to t(key).
  const shellText = () => ({
    siteTitle: t('siteTitle'),
    siteSub: t('siteSub'),
    landingQuizzes: t('landingQuizzes'),
    landingOthers: t('landingOthers'),
    footCode: t('footCode'),
    footLicence: t('footLicence'),
    coffeeQ: t('coffeeQ'),
    coffee: t('coffee'),
  });

  function mk(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function translateShell() {
    const s = shellText();
    document.documentElement.lang = L;
    document.querySelectorAll('[data-i18n]').forEach((n) => {
      const k = n.dataset.i18n;
      n.textContent = s[k] != null ? s[k] : t(k);
    });
    document.querySelectorAll('[data-i18n-aria]').forEach((n) => {
      const k = n.dataset.i18nAria;
      n.setAttribute('aria-label', s[k] != null ? s[k] : t(k));
    });
    document.title = t('siteTitle');
    const desc = document.querySelector('meta[name="description"]');
    if (desc) desc.setAttribute('content', t('siteSub'));
  }

  function card(q) {
    const c = mk('article', 'panel quiz');
    c.appendChild(mk('h3', null, q.title));
    if (q.subtitle) c.appendChild(mk('p', 'sub', q.subtitle));
    c.appendChild(mk('p', 'count', t('landingDecks', q.decks, q.questions)));
    const a = mk('a', 'btn primary', t('start'));
    a.href = q.path;
    c.appendChild(a);
    return c;
  }

  function renderQuizzes() {
    const box = document.getElementById('quizzes');
    box.textContent = '';
    QUIZZES.forEach((q) => box.appendChild(card(q)));
  }

  translateShell();
  renderQuizzes();
})();
