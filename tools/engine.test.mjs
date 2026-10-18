// Tests for QuizCore in shared/engine.js. Run from the repo root: node --test tools/
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

vm.runInThisContext(fs.readFileSync('shared/engine.js', 'utf8'));
const Q = globalThis.QuizCore;

function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function tfQuestions(prefix, count) {
  const out = [];
  for (let i = 0; i < count; i++) {
    out.push({ id: prefix + i, type: 'tf', q: 'Q ' + prefix + i, answer: i % 2 === 0, why: 'w', src: 's' });
  }
  return out;
}

function makeQuiz(sizes) {
  return {
    id: 'quiz',
    title: 'T',
    subtitle: 'S',
    decks: sizes.map((size, i) => ({ id: 'd' + i, label: 'D' + i, questions: tfQuestions('d' + i + '-', size) })),
  };
}

const MC = { id: 'mc1', type: 'mc', q: 'Capitale?', options: ['Roma', 'Milano', 'Napoli', 'Torino'], answer: 0, why: 'w', src: 's' };
const TF = { id: 'tf1', type: 'tf', q: 'Vero?', answer: false, why: 'w', src: 's' };
const MATCH = { id: 'm1', type: 'match', q: 'Abbina', pairs: [['A', '1'], ['B', '2'], ['C', '3']], why: 'w', src: 's' };
const ORDER = { id: 'o1', type: 'order', q: 'Ordina', items: ['primo', 'secondo', 'terzo'], why: 'w', src: 's' };

test('shuffle keeps elements and does not mutate', () => {
  const input = [1, 2, 3, 4, 5, 6, 7, 8];
  const copy = input.slice();
  const out = Q.shuffle(input, mulberry32(1));
  assert.deepEqual(input, copy);
  assert.notEqual(out, input);
  assert.deepEqual(out.slice().sort((a, b) => a - b), copy);
  assert.deepEqual(Q.shuffle([], mulberry32(1)), []);
});

test('sampleRound returns min(n, size) without duplicates', () => {
  const quiz = makeQuiz([7, 12]);
  const out = Q.sampleRound(quiz, 'd0', 10, mulberry32(2));
  assert.equal(out.length, 7);
  assert.equal(new Set(out.map((q) => q.id)).size, 7);
  assert.ok(out.every((q) => q.deck === 'd0'));
  const five = Q.sampleRound(quiz, 'd1', 5, mulberry32(3));
  assert.equal(five.length, 5);
  assert.equal(new Set(five.map((q) => q.id)).size, 5);
  assert.ok(five.every((q) => q.id.startsWith('d1-') && q.deck === 'd1'));
  // shallow copies: the source data is untouched
  assert.ok(!('deck' in quiz.decks[0].questions[0]));
});

test('sampleRound all shares across decks and respects n', () => {
  const quiz = makeQuiz([12, 12, 3]);
  for (let seed = 1; seed <= 50; seed++) {
    const out = Q.sampleRound(quiz, 'all', 10, mulberry32(seed));
    assert.equal(out.length, 10);
    assert.equal(new Set(out.map((q) => q.id)).size, 10);
    const small = out.filter((q) => q.deck === 'd2');
    assert.ok(small.length <= 3);
    assert.ok(out.every((q) => q.id.startsWith(q.deck + '-')));
  }
});

test('sampleRound with Infinity returns everything', () => {
  const quiz = makeQuiz([12, 12, 3]);
  const all = Q.sampleRound(quiz, 'all', Infinity, mulberry32(4));
  assert.equal(all.length, 27);
  assert.equal(new Set(all.map((q) => q.id)).size, 27);
  const one = Q.sampleRound(quiz, 'd1', Infinity, mulberry32(5));
  assert.equal(one.length, 12);
  assert.equal(new Set(one.map((q) => q.id)).size, 12);
});

test('prepare order never returns the identity permutation', () => {
  for (let seed = 1; seed <= 200; seed++) {
    const len = 3 + (seed % 3);
    const items = [];
    for (let i = 0; i < len; i++) items.push('item' + i);
    const view = Q.prepare({ id: 'o', type: 'order', q: 'q', items, why: 'w', src: 's' }, mulberry32(seed));
    const idx = view.items.map((i) => i.idx);
    assert.notDeepEqual(idx, idx.slice().sort((a, b) => a - b));
    assert.deepEqual(idx.slice().sort((a, b) => a - b), [...Array(len).keys()]);
    assert.ok(view.items.every((i) => i.text === items[i.idx]));
  }
  // identical items cannot be "unsorted" by text but must still terminate
  const same = Q.prepare({ id: 'o', type: 'order', q: 'q', items: ['x', 'x', 'x'], why: 'w', src: 's' }, () => 0.99);
  assert.equal(same.items.length, 3);
});

test('prepare mc keeps original indices', () => {
  const view = Q.prepare(MC, mulberry32(6));
  assert.equal(view.options.length, 4);
  assert.ok(view.options.every((o) => o.text === MC.options[o.idx]));
  assert.deepEqual(view.options.map((o) => o.idx).sort(), [0, 1, 2, 3]);
  assert.deepEqual(Q.prepare(TF, mulberry32(6)), {});
  const m = Q.prepare(MATCH, mulberry32(7));
  assert.deepEqual(m.lefts, [{ text: 'A', idx: 0 }, { text: 'B', idx: 1 }, { text: 'C', idx: 2 }]);
  assert.ok(m.rights.every((r) => r.text === MATCH.pairs[r.idx][1]));
  assert.deepEqual(m.rights.map((r) => r.idx).sort(), [0, 1, 2]);
});

test('grade mc / tf / match / order right and wrong cases', () => {
  assert.equal(Q.grade(MC, 0).ok, true);
  assert.equal(Q.grade(MC, 2).ok, false);
  assert.equal(Q.grade(MC, undefined).ok, false);
  assert.equal(Q.grade(TF, false).ok, true);
  assert.equal(Q.grade(TF, true).ok, false);
  assert.equal(Q.grade(TF, 'false').ok, false);
  assert.equal(Q.grade(MATCH, { 0: 0, 1: 1, 2: 2 }).ok, true);
  assert.equal(Q.grade(MATCH, { 0: 1, 1: 0, 2: 2 }).ok, false);
  assert.equal(Q.grade(MATCH, { 0: 0, 1: 1 }).ok, false);
  assert.equal(Q.grade(MATCH, {}).ok, false);
  assert.equal(Q.grade(ORDER, [0, 1, 2]).ok, true);
  assert.equal(Q.grade(ORDER, [1, 0, 2]).ok, false);
  assert.equal(Q.grade(ORDER, [0, 1]).ok, false);
  assert.equal(Q.grade(ORDER, null).ok, false);
});

test('grade correctText formats', () => {
  assert.equal(Q.grade(MC, 3).correctText, 'Roma');
  assert.equal(Q.grade(TF, true).correctText, 'false');
  assert.equal(Q.grade({ ...TF, answer: true }, true).correctText, 'true');
  assert.equal(Q.grade(MATCH, {}).correctText, 'A → 1 · B → 2 · C → 3');
  assert.equal(Q.grade(ORDER, []).correctText, 'primo → secondo → terzo');
});

test('readBest ignores garbage and throwing storage; writeBest keeps the max', () => {
  const mem = () => {
    const data = {};
    return {
      data,
      getItem: (k) => (k in data ? data[k] : null),
      setItem: (k, v) => { data[k] = String(v); },
    };
  };
  const throwing = {
    getItem() { throw new Error('denied'); },
    setItem() { throw new Error('denied'); },
  };
  const s = mem();
  assert.equal(Q.readBest(s, 'k'), null);
  assert.equal(Q.readBest(null, 'k'), null);
  assert.equal(Q.readBest(undefined, 'k'), null);
  assert.equal(Q.readBest(throwing, 'k'), null);
  for (const bad of ['abc', '', '-1', '1.5', 'NaN', 'Infinity']) {
    s.data.k = bad;
    assert.equal(Q.readBest(s, 'k'), null, 'value ' + JSON.stringify(bad));
  }
  s.data.k = '7';
  assert.equal(Q.readBest(s, 'k'), 7);

  const w = mem();
  Q.writeBest(w, 'b', 5);
  assert.equal(w.data.b, '5');
  Q.writeBest(w, 'b', 3);
  assert.equal(w.data.b, '5');
  Q.writeBest(w, 'b', 8);
  assert.equal(w.data.b, '8');
  w.data.b = 'garbage';
  Q.writeBest(w, 'b', 0);
  assert.equal(w.data.b, '0');
  assert.doesNotThrow(() => Q.writeBest(throwing, 'b', 4));
  assert.doesNotThrow(() => Q.writeBest(null, 'b', 4));
});
