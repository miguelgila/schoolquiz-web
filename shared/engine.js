// Quiz engine. QuizCore is pure logic (no DOM), loadable in node for tools/engine.test.mjs.
const QuizCore = {
  // Fisher-Yates on a copy; the input array is left untouched.
  shuffle(arr, rng = Math.random) {
    const out = arr.slice();
    for (let i = out.length - 1; i > 0; i--) {
      const j = Math.floor(rng() * (i + 1));
      const tmp = out[i];
      out[i] = out[j];
      out[j] = tmp;
    }
    return out;
  },

  // n questions from one deck, or an equal share per deck for 'all' (topped up from the
  // larger decks when the small ones cannot fill their share).
  // Each question is a shallow copy tagged with the id of its deck.
  sampleRound(quiz, deckId, n, rng = Math.random) {
    const tag = (deck) => deck.questions.map((q) => Object.assign({}, q, { deck: deck.id }));
    if (deckId === 'all') {
      const decks = quiz.decks;
      if (n === Infinity) {
        return QuizCore.shuffle([].concat(...decks.map(tag)), rng);
      }
      const share = Math.ceil(n / decks.length);
      const shuffled = decks.map((d) => QuizCore.shuffle(tag(d), rng));
      let picked = [].concat(...shuffled.map((qs) => qs.slice(0, share)));
      // small decks leave the round short: top up from what the larger decks have left
      if (picked.length < n) {
        const rest = QuizCore.shuffle([].concat(...shuffled.map((qs) => qs.slice(share))), rng);
        picked = picked.concat(rest.slice(0, n - picked.length));
      }
      return QuizCore.shuffle(picked, rng).slice(0, n);
    }
    const deck = quiz.decks.find((d) => d.id === deckId);
    if (!deck) return [];
    return QuizCore.shuffle(tag(deck), rng).slice(0, Math.min(n, deck.questions.length));
  },

  // Shuffled view of a question for display; idx always points to the original position.
  prepare(q, rng = Math.random) {
    const indexed = (texts) => texts.map((text, idx) => ({ text, idx }));
    switch (q.type) {
      case 'mc':
        return { options: QuizCore.shuffle(indexed(q.options), rng) };
      case 'match':
        return {
          lefts: indexed(q.pairs.map((p) => p[0])),
          rights: QuizCore.shuffle(indexed(q.pairs.map((p) => p[1])), rng),
        };
      case 'order': {
        const base = indexed(q.items);
        let items = QuizCore.shuffle(base, rng);
        // Never start in the solved order; capped so identical items cannot loop forever.
        for (let tries = 0; base.length >= 2 && tries < 50 && items.every((it, i) => it.idx === i); tries++) {
          items = QuizCore.shuffle(base, rng);
        }
        return { items };
      }
      default:
        return {};
    }
  },

  // response: mc original index, tf boolean, match {leftIdx: rightIdx}, order array of original indices.
  // mc and order responses must be numbers (compared strictly); match values may be numeric strings.
  // correctText for tf is 'true'/'false'; the UI translates it.
  grade(q, response) {
    switch (q.type) {
      case 'mc':
        return { ok: response === q.answer, correctText: q.options[q.answer] };
      case 'tf':
        return { ok: response === q.answer, correctText: String(q.answer) };
      case 'match': {
        const r = response || {};
        // select values may be strings; an extra mapping beyond the pairs is wrong
        const ok = Object.keys(r).length === q.pairs.length &&
          q.pairs.every((_, i) => String(r[i]) === String(i));
        return { ok, correctText: q.pairs.map((p) => p[0] + ' → ' + p[1]).join(' · ') };
      }
      case 'order': {
        const ok = Array.isArray(response) && response.length === q.items.length &&
          response.every((v, i) => v === i);
        return { ok, correctText: q.items.join(' → ') };
      }
      default:
        return { ok: false, correctText: '' };
    }
  },

  // Best score from storage (e.g. localStorage); null when missing, invalid or unavailable.
  readBest(storage, key) {
    if (!storage) return null;
    let raw;
    try {
      raw = storage.getItem(key);
    } catch (e) {
      return null;
    }
    if (typeof raw !== 'string' || !/^\d+$/.test(raw)) return null;
    const value = Number(raw);
    return Number.isSafeInteger(value) ? value : null;
  },

  // Store value only when it beats the stored best; storage errors are ignored.
  writeBest(storage, key, value) {
    if (!Number.isFinite(value)) return;
    try {
      const best = QuizCore.readBest(storage, key);
      if (best === null || best < value) storage.setItem(key, String(value));
    } catch (e) {
      // storage unavailable (private mode, quota, null): keep playing without a record
    }
  },
};

(typeof window !== 'undefined' ? window : globalThis).QuizCore = QuizCore;

// ---------- DOM layer: one question at a time ----------
// Expects the page shell (see tools/fixture/index.html) and window.I18N / window.QUIZ loaded first.
(function () {
  if (typeof document === 'undefined') return;

  const I = window.I18N;
  const QUIZ = window.QUIZ;
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
    roundLen: t('roundLen'),
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
  const lsGet = (key) => {
    try {
      return store ? store.getItem(key) : null;
    } catch (e) {
      return null;
    }
  };
  const lsSet = (key, value) => {
    try {
      if (store) store.setItem(key, value);
    } catch (e) {
      // keep playing without persisting
    }
  };
  const nKey = 'schoolquiz.' + QUIZ.id + '.n';
  const bestKey = (deckId) => 'schoolquiz.' + QUIZ.id + '.' + deckId + '.best';
  // Best scores are recorded only for 10-question rounds (S.n === 10), so every badge
  // compares like with like and always reads "best / 10".
  const BEST_ROUND = 10;

  // ---------- state ----------
  const savedN = lsGet(nKey);
  const S = {
    deck: 'all',
    n: savedN === 'all' ? Infinity : (savedN === '20' ? 20 : 10),
    round: [],
    i: 0,
    view: null,
    response: null,
    answered: false,
    results: [],
  };
  const current = () => S.round[S.i];

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
      buildRoundLen();
      setDeck(S.deck);
    };
  }

  function buildDecks() {
    const nav = el('decks');
    nav.innerHTML = '';
    const decks = [{ id: 'all', label: t('deckAll') }].concat(QUIZ.decks.map((d) => ({ id: d.id, label: d.label })));
    decks.forEach((d) => {
      const b = button(null, null, () => setDeck(d.id));
      b.appendChild(mk('span', null, d.label));
      const best = QuizCore.readBest(store, bestKey(d.id));
      if (best !== null) b.appendChild(mk('span', 'badge', t('best', best, BEST_ROUND)));
      b.setAttribute('aria-pressed', String(d.id === S.deck));
      nav.appendChild(b);
    });
  }

  function buildRoundLen() {
    const sel = el('roundLen');
    sel.innerHTML = '';
    [['10', '10'], ['20', '20'], ['all', t('roundAll')]].forEach(([value, text]) => {
      const o = mk('option', null, text);
      o.value = value;
      sel.appendChild(o);
    });
    sel.value = S.n === Infinity ? 'all' : String(S.n);
    sel.onchange = () => {
      S.n = sel.value === 'all' ? Infinity : Number(sel.value);
      lsSet(nKey, sel.value);
      fresh();
      render();
    };
  }

  // ---------- round flow ----------
  function setDeck(id) {
    S.deck = id;
    buildDecks();
    fresh();
    render();
  }

  function fresh() {
    S.round = QuizCore.sampleRound(QUIZ, S.deck, S.n);
    S.i = 0;
    S.view = null;
    S.response = null;
    S.answered = false;
    S.results = [];
    el('card').hidden = false;
    el('result').classList.remove('show');
    el('result').innerHTML = '';
  }

  function render(focus) {
    const q = current();
    const card = el('card');
    card.classList.add('card');
    card.innerHTML = '';
    if (!q) {
      el('progress').textContent = '';
      return;
    }
    S.view = QuizCore.prepare(q);
    S.response = null;
    S.answered = false;
    el('progress').textContent = t('progress', S.i + 1, S.round.length);

    const prompt = mk('h2', 'q', q.q);
    prompt.tabIndex = -1;
    card.appendChild(prompt);
    if (q.type === 'mc') renderMc(card);
    else if (q.type === 'tf') renderTf(card);
    else if (q.type === 'match') renderMatch(card, q);
    else if (q.type === 'order') renderOrder(card);
    if (focus) prompt.focus();
  }

  function renderMc(card) {
    const box = mk('div', 'options');
    S.view.options.forEach((opt, n) => {
      const b = button(null, null, () => answer(opt.idx));
      b.dataset.value = String(opt.idx);
      b.appendChild(mk('span', 'key', String(n + 1)));
      b.appendChild(mk('span', null, opt.text));
      box.appendChild(b);
    });
    card.appendChild(box);
  }

  function renderTf(card) {
    const box = mk('div', 'options tf');
    [[true, t('true')], [false, t('false')]].forEach(([value, text]) => {
      const b = button(null, text, () => answer(value));
      b.dataset.value = String(value);
      box.appendChild(b);
    });
    card.appendChild(box);
  }

  function checkButton(card, enabled) {
    const actions = mk('div', 'actions');
    const b = button('btn primary', t('check'), () => {
      if (!b.disabled) answer(S.response);
    });
    b.id = 'checkBtn';
    b.disabled = !enabled;
    actions.appendChild(b);
    card.appendChild(actions);
    return b;
  }

  function renderMatch(card, q) {
    card.appendChild(mk('p', 'help', t('matchHelp')));
    S.response = {};
    const box = mk('div', 'match');
    const check = { btn: null };
    S.view.lefts.forEach((left) => {
      const row = mk('div', 'pair');
      row.dataset.left = String(left.idx);
      const id = 'pick-' + left.idx;
      const label = mk('label', null, left.text);
      label.htmlFor = id;
      const sel = mk('select');
      sel.id = id;
      const ph = mk('option', null, t('pick'));
      ph.value = '';
      sel.appendChild(ph);
      S.view.rights.forEach((right) => {
        const o = mk('option', null, right.text);
        o.value = String(right.idx);
        sel.appendChild(o);
      });
      sel.addEventListener('change', () => {
        if (sel.value === '') delete S.response[left.idx];
        else S.response[left.idx] = sel.value;
        check.btn.disabled = Object.keys(S.response).length !== q.pairs.length;
      });
      row.appendChild(label);
      row.appendChild(sel);
      box.appendChild(row);
    });
    card.appendChild(box);
    check.btn = checkButton(card, false);
  }

  function renderOrder(card) {
    card.appendChild(mk('p', 'help', t('orderHelp')));
    S.response = S.view.items.map((it) => it.idx);
    const list = mk('ol', 'order');
    card.appendChild(list);
    drawOrder(list);
    checkButton(card, true);
  }

  // Redraws the order list from S.response; refocus keeps keyboard users on the moved row.
  function drawOrder(list, refocus) {
    const byIdx = {};
    S.view.items.forEach((it) => { byIdx[it.idx] = it.text; });
    list.innerHTML = '';
    S.response.forEach((idx, pos) => {
      const li = mk('li');
      li.dataset.pos = String(pos);
      li.appendChild(mk('span', 'num', String(pos + 1)));
      li.appendChild(mk('span', 'txt', byIdx[idx]));
      const up = button('btn icon', '▲', () => move(list, pos, -1));
      up.setAttribute('aria-label', t('moveUp'));
      up.dataset.dir = 'up';
      up.disabled = pos === 0;
      const down = button('btn icon', '▼', () => move(list, pos, 1));
      down.setAttribute('aria-label', t('moveDown'));
      down.dataset.dir = 'down';
      down.disabled = pos === S.response.length - 1;
      li.appendChild(up);
      li.appendChild(down);
      list.appendChild(li);
    });
    if (refocus) {
      const li = list.children[refocus.pos];
      const target = li && li.querySelector('[data-dir="' + refocus.dir + '"]:not(:disabled)');
      (target || (li && li.querySelector('button:not(:disabled)')) || list).focus();
    }
  }

  function move(list, pos, delta) {
    if (S.answered) return;
    const to = pos + delta;
    if (to < 0 || to >= S.response.length) return;
    const r = S.response;
    const tmp = r[pos];
    r[pos] = r[to];
    r[to] = tmp;
    drawOrder(list, { pos: to, dir: delta < 0 ? 'up' : 'down' });
  }

  // ---------- answering ----------
  function answer(response) {
    if (S.answered) return;
    const q = current();
    const g = QuizCore.grade(q, response);
    S.answered = true;
    S.response = response;
    const correctText = q.type === 'tf' ? (g.correctText === 'true' ? t('true') : t('false')) : g.correctText;
    S.results.push({ q, ok: g.ok, correctText });
    markAnswer(q, response);
    showFeedback(q, g.ok, correctText);
  }

  function markAnswer(q, response) {
    const card = el('card');
    if (q.type === 'mc' || q.type === 'tf') {
      card.querySelectorAll('.options button').forEach((b) => {
        const value = q.type === 'mc' ? Number(b.dataset.value) : b.dataset.value === 'true';
        if (value === q.answer) b.classList.add('ok');
        else if (value === response) b.classList.add('bad');
        else b.classList.add('dim');
        b.disabled = true;
      });
    } else if (q.type === 'match') {
      card.querySelectorAll('.match .pair').forEach((row) => {
        const left = row.dataset.left;
        row.classList.add(String(response[left]) === left ? 'ok' : 'bad');
        row.querySelector('select').disabled = true;
      });
    } else if (q.type === 'order') {
      card.querySelectorAll('.order li').forEach((li) => {
        const pos = Number(li.dataset.pos);
        li.classList.add(response[pos] === pos ? 'ok' : 'bad');
        li.querySelectorAll('button').forEach((b) => { b.disabled = true; });
      });
    }
    const check = el('checkBtn');
    if (check) check.parentNode.remove();
  }

  function showFeedback(q, ok, correctText) {
    const card = el('card');
    const box = mk('div', 'feedback ' + (ok ? 'ok' : 'bad'));
    box.setAttribute('role', 'status');
    box.appendChild(mk('h2', null, ok ? t('ok') : t('bad')));
    // on a right answer the highlighted option already shows it
    if (!ok) box.appendChild(mk('p', 'correct', t('correctWas', correctText)));
    if (q.why) box.appendChild(mk('p', 'why', q.why));
    if (q.src) box.appendChild(mk('p', 'src', q.src));
    card.appendChild(box);
    const last = S.i === S.round.length - 1;
    const actions = mk('div', 'actions');
    const next = button('btn primary', last ? t('finish') : t('next'), goNext);
    next.id = 'nextBtn';
    actions.appendChild(next);
    card.appendChild(actions);
    next.focus({ preventScroll: true });
    // bring the feedback and the Avanti row below it into view
    actions.scrollIntoView({ block: 'nearest' });
  }

  function goNext() {
    if (!S.answered) return;
    S.i++;
    if (S.i >= S.round.length) finish();
    else render(true);
  }

  // ---------- end screen ----------
  function finish() {
    const ok = S.results.filter((r) => r.ok).length;
    const total = S.results.length;
    if (S.n === BEST_ROUND) QuizCore.writeBest(store, bestKey(S.deck), ok);
    buildDecks();
    el('progress').textContent = '';
    el('card').hidden = true;
    const res = el('result');
    res.innerHTML = '';
    res.appendChild(mk('div', 'score', t('score', ok, total)));
    res.appendChild(mk('p', null, ok === total ? t('perfect') : t('retry')));
    const missed = S.results.filter((r) => !r.ok);
    if (missed.length) {
      res.appendChild(mk('h2', null, t('review')));
      const ul = mk('ul', 'review');
      missed.forEach((r) => {
        const li = mk('li');
        li.appendChild(mk('b', null, r.q.q));
        li.appendChild(mk('span', null, t('correctWas', r.correctText)));
        ul.appendChild(li);
      });
      res.appendChild(ul);
    }
    const actions = mk('div', 'actions');
    const again = button('btn primary', t('restart'), () => {
      fresh();
      render(true);
    });
    actions.appendChild(again);
    res.appendChild(actions);
    res.classList.add('show');
    again.focus({ preventScroll: true });
    res.scrollIntoView({ block: 'nearest' });
  }

  // ---------- keyboard ----------
  document.addEventListener('keydown', (e) => {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    const tag = e.target && e.target.tagName;
    const q = current();
    if (!q || el('card').hidden) return;
    if (e.key === 'Enter') {
      // a focused button or link already activates itself on Enter;
      // inside a select Enter belongs to the select, not to the quiz
      if (tag === 'BUTTON' || tag === 'A' || tag === 'SELECT') return;
      if (S.answered) {
        e.preventDefault();
        goNext();
        return;
      }
      const check = el('checkBtn');
      if (check && !check.disabled) {
        e.preventDefault();
        answer(S.response);
      }
      return;
    }
    if (S.answered || tag === 'SELECT' || tag === 'INPUT' || tag === 'TEXTAREA') return;
    const n = Number(e.key);
    if (!Number.isInteger(n) || n < 1) return;
    if (q.type === 'mc' && n <= S.view.options.length && n <= 4) {
      e.preventDefault();
      answer(S.view.options[n - 1].idx);
    } else if (q.type === 'tf' && n <= 2) {
      e.preventDefault();
      answer(n === 1);
    }
  });

  // ---------- start ----------
  translateShell();
  buildLang();
  buildRoundLen();
  setDeck('all');
})();
