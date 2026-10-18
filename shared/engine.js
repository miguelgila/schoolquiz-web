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

  // n questions from one deck, or an equal share per deck for 'all'.
  // Each question is a shallow copy tagged with the id of its deck.
  sampleRound(quiz, deckId, n, rng = Math.random) {
    const tag = (deck) => deck.questions.map((q) => Object.assign({}, q, { deck: deck.id }));
    if (deckId === 'all') {
      const decks = quiz.decks;
      if (n === Infinity) {
        return QuizCore.shuffle([].concat(...decks.map(tag)), rng);
      }
      const share = Math.ceil(n / decks.length);
      const picked = [].concat(...decks.map((d) => QuizCore.shuffle(tag(d), rng).slice(0, share)));
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
