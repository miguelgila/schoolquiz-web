// Labelling board: put every name in its slot on a drawing, then Verifica.
// DiagramCore is pure logic (no DOM), loadable in node for tools/diagram.test.mjs.
// The page also loads shared/engine.js first, for QuizCore.shuffle/readBest/writeBest.
const DiagramCore = {
  // Puts cardId in slotId and takes it out of any other slot; cardId null empties the slot.
  // Returns a new {slotId: cardId} map; the input is left untouched.
  place(placed, slotId, cardId) {
    const out = {};
    Object.keys(placed).forEach((slot) => {
      if (slot !== slotId && placed[slot] !== cardId) out[slot] = placed[slot];
    });
    if (cardId != null) out[slotId] = cardId;
    return out;
  },

  // Cards are the deck's own targets. A slot is right when its card has the slot's name,
  // so two cards with the same name (Falangi of the hand and of the foot) fit either slot.
  // status: 'ok', 'bad' (wrong card) or 'none' (empty).
  grade(deck, placed) {
    const byId = {};
    deck.targets.forEach((tg) => { byId[tg.id] = tg; });
    const slots = deck.targets.map((tg) => {
      const card = placed[tg.id] != null ? byId[placed[tg.id]] || null : null;
      const status = !card ? 'none' : (card.name === tg.name ? 'ok' : 'bad');
      return { target: tg, card, status };
    });
    return { ok: slots.filter((s) => s.status === 'ok').length, total: slots.length, slots };
  },
};

(typeof window !== 'undefined' ? window : globalThis).DiagramCore = DiagramCore;

// ---------- DOM layer: one board per deck ----------
// Expects the page shell (see scienze-ossa/index.html) and window.I18N / window.DIAGRAM / QuizCore loaded first.
(function () {
  if (typeof document === 'undefined') return;

  const I = window.I18N;
  const QUIZ = window.DIAGRAM;
  const SVGNS = 'http://www.w3.org/2000/svg';
  const el = (id) => document.getElementById(id);
  let L = I.langs[0][0];

  // t(key, ...args): UI string with {0}, {1} replaced; falls back to Italian, then to the key itself.
  const t = (key, ...args) => {
    const u = I.ui[L] || {};
    const s = u[key] != null ? u[key] : (I.ui.it[key] != null ? I.ui.it[key] : key);
    return s.replace(/\{(\d)\}/g, (m, i) => (args[i] != null ? String(args[i]) : m));
  };

  // Strings of the static shell (data-i18n / data-i18n-aria), spelled as literal t() calls
  // so tools/test_i18n.py sees them; any other data-i18n key falls back to t(key).
  const shellText = () => ({
    back: t('back'),
    decksAria: t('decksAria'),
    boardAria: t('boardAria'),
    trayAria: t('trayAria'),
    trayTitle: t('trayTitle'),
    trayEmpty: t('trayEmpty'),
    check: t('check'),
    restart: t('restart'),
    footImages: t('footImages'),
    imgSkeleton: t('imgSkeleton'),
    imgSkull: t('imgSkull'),
    footCode: t('footCode'),
    footLicence: t('footLicence'),
    coffeeQ: t('coffeeQ'),
    coffee: t('coffee'),
    langAria: t('langAria'),
  });

  // ---------- storage (every access may throw: private mode, blocked cookies) ----------
  let store = null;
  try {
    store = window.localStorage;
  } catch (e) {
    store = null;
  }
  const bestKey = (deckId) => 'schoolquiz.' + QUIZ.id + '.' + deckId + '.best';

  // ---------- state ----------
  const S = {
    deck: QUIZ.decks[0].id,
    order: [],
    card: null,
    slot: null,
    placed: {},
    checked: false,
  };
  const deck = () => QUIZ.decks.find((d) => d.id === S.deck);
  let byId = {};
  let nodes = {};

  // ---------- small DOM helpers ----------
  function mk(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function button(cls, text, onClick) {
    const b = mk('button', cls, text);
    b.type = 'button';
    b.addEventListener('click', onClick);
    return b;
  }
  function svg(tag, attrs, cls) {
    const n = document.createElementNS(SVGNS, tag);
    Object.keys(attrs).forEach((k) => n.setAttribute(k, attrs[k]));
    if (cls) n.setAttribute('class', cls);
    return n;
  }

  // ---------- shell ----------
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
    document.title = QUIZ.title + ' · ' + t('siteTitle');
    el('qTitle').textContent = QUIZ.title;
    el('qSub').textContent = QUIZ.subtitle || '';
  }

  function buildLang() {
    const sel = el('langSel');
    if (!sel) return;
    sel.innerHTML = '';
    I.langs.forEach(([code, name]) => {
      const o = mk('option', null, name);
      o.value = code;
      sel.appendChild(o);
    });
    sel.value = L;
    sel.hidden = I.langs.length === 1;
    sel.onchange = () => {
      L = sel.value;
      translateShell();
      setDeck(S.deck);
    };
  }

  function buildDecks() {
    const nav = el('decks');
    nav.innerHTML = '';
    QUIZ.decks.forEach((d) => {
      const b = button(null, null, () => setDeck(d.id));
      b.appendChild(mk('span', null, d.label));
      const best = QuizCore.readBest(store, bestKey(d.id));
      if (best !== null) b.appendChild(mk('span', 'badge', t('best', best, d.targets.length)));
      b.setAttribute('aria-pressed', String(d.id === S.deck));
      nav.appendChild(b);
    });
  }

  // ---------- board (built once per deck) ----------
  // The drawing, a leader line from each point to its slot's column, and one slot button per target.
  // Slots sit in the side columns (cw wide), anchored to the outer edge so long names grow inwards.
  function buildBoard() {
    const d = deck();
    const box = el('board');
    box.innerHTML = '';
    box.style.aspectRatio = d.w + ' / ' + d.h;
    nodes = { leads: {}, dots: {}, slots: {} };
    const pic = svg('svg', { viewBox: '0 0 ' + d.w + ' ' + d.h, 'aria-hidden': 'true' });
    pic.appendChild(svg('image', { href: d.img.src, x: d.img.x, y: d.img.y, width: d.img.w, height: d.img.h }));
    d.targets.forEach((tg) => {
      const inner = tg.side === 'l' ? d.cw : d.w - d.cw;
      const edge = tg.side === 'l' ? 0 : d.w;
      const lead = svg('polyline', { points: [tg.x, tg.y, inner, tg.ly, edge, tg.ly].join(' ') }, 'lead');
      pic.appendChild(lead);
      nodes.leads[tg.id] = lead;
    });
    d.targets.forEach((tg) => {
      const dot = svg('circle', { cx: tg.x, cy: tg.y, r: 4 }, 'pt');
      pic.appendChild(dot);
      nodes.dots[tg.id] = dot;
    });
    box.appendChild(pic);
    d.targets.forEach((tg) => {
      const b = button('slot ' + tg.side, null, () => pickSlot(tg.id));
      b.style.top = (tg.ly / d.h * 100).toFixed(2) + '%';
      box.appendChild(b);
      nodes.slots[tg.id] = b;
    });
  }

  // ---------- game actions ----------
  function setDeck(id) {
    S.deck = id;
    buildDecks();
    fresh();
    buildBoard();
    render();
  }

  function fresh() {
    const d = deck();
    byId = {};
    d.targets.forEach((tg) => { byId[tg.id] = tg; });
    S.order = QuizCore.shuffle(d.targets.map((tg) => tg.id));
    S.card = null;
    S.slot = null;
    S.placed = {};
    S.checked = false;
  }

  function pickCard(id) {
    if (S.checked) return;
    if (S.slot) {
      S.placed = DiagramCore.place(S.placed, S.slot, id);
      S.slot = null;
      S.card = null;
    } else {
      S.card = S.card === id ? null : id;
    }
    render();
  }

  // With a card chosen the slot takes it; a filled slot gives its card back; an empty one is chosen.
  function pickSlot(id) {
    if (S.checked) return;
    if (S.card) {
      S.placed = DiagramCore.place(S.placed, id, S.card);
      S.card = null;
    } else if (S.placed[id]) {
      S.placed = DiagramCore.place(S.placed, id, null);
      S.slot = null;
    } else {
      S.slot = S.slot === id ? null : id;
    }
    render();
  }

  function check() {
    if (S.checked) return;
    S.checked = true;
    S.card = null;
    S.slot = null;
    const g = DiagramCore.grade(deck(), S.placed);
    QuizCore.writeBest(store, bestKey(S.deck), g.ok);
    buildDecks();
    render();
    el('result').scrollIntoView({ block: 'nearest' });
  }

  function restart() {
    fresh();
    render();
  }

  // ---------- render ----------
  function render() {
    const d = deck();
    const g = DiagramCore.grade(d, S.placed);
    g.slots.forEach((s) => {
      const id = s.target.id;
      const b = nodes.slots[id];
      const status = S.checked ? s.status : (s.card ? 'filled' : 'empty');
      b.className = 'slot ' + s.target.side + ' ' + status + (S.slot === id ? ' sel' : '');
      b.textContent = '';
      if (!S.checked) {
        b.textContent = s.card ? s.card.name : t('slotEmpty');
      } else if (s.status === 'bad') {
        b.appendChild(mk('s', null, s.card.name));
        b.appendChild(document.createTextNode(' ' + s.target.name));
      } else {
        b.textContent = s.target.name;
      }
      b.disabled = S.checked;
      b.setAttribute('aria-label', t('slotAria', d.targets.indexOf(s.target) + 1, s.card ? s.card.name : t('slotEmpty')));
      const lit = S.slot === id || (S.checked && s.status !== 'ok');
      nodes.leads[id].setAttribute('class', 'lead s-' + status + (lit ? ' lit' : ''));
      nodes.dots[id].setAttribute('class', 'pt s-' + status + (S.slot === id ? ' lit' : ''));
    });

    // tray: the cards still to place, in the shuffled order; none once checked
    const used = new Set(Object.values(S.placed));
    const left = S.checked ? [] : S.order.filter((id) => !used.has(id));
    const cards = el('cards');
    cards.innerHTML = '';
    left.forEach((id) => {
      const b = button('tag', byId[id].name, () => pickCard(id));
      b.setAttribute('aria-pressed', String(S.card === id));
      cards.appendChild(b);
    });
    el('trayCount').textContent = S.checked ? '' : t('trayLeft', left.length);
    el('trayEmpty').hidden = left.length > 0 || S.checked;
    el('trayHelp').textContent = S.checked ? t('boardHelpChecked')
      : (S.card ? t('boardHelpCard', byId[S.card].name) : (S.slot ? t('boardHelpSlot') : t('boardHelp')));
    el('checkBtn').hidden = S.checked;

    renderResult(g);
  }

  function renderResult(g) {
    const res = el('result');
    res.innerHTML = '';
    res.classList.toggle('show', S.checked);
    if (!S.checked) return;
    res.appendChild(mk('div', 'score', t('score', g.ok, g.total)));
    res.appendChild(mk('p', null, g.ok === g.total ? t('perfect') : t('retry')));
    const missed = g.slots.filter((s) => s.status !== 'ok');
    if (missed.length) {
      res.appendChild(mk('h2', null, t('review')));
      const ul = mk('ul', 'review');
      missed.forEach((s) => {
        const li = mk('li');
        li.appendChild(mk('b', null, s.target.name));
        li.appendChild(mk('span', null, s.card ? t('youPut', s.card.name) : t('notPlaced')));
        ul.appendChild(li);
      });
      res.appendChild(ul);
    }
  }

  // ---------- keyboard ----------
  // Escape drops the chosen card or slot.
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape' || (!S.card && !S.slot)) return;
    S.card = null;
    S.slot = null;
    render();
  });

  // ---------- start ----------
  el('checkBtn').addEventListener('click', check);
  el('resetBtn').addEventListener('click', restart);
  translateShell();
  buildLang();
  setDeck(S.deck);
})();
