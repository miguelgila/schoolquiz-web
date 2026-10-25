// Tests for DiagramCore in shared/diagram.js. Run from the repo root: node --test tools/
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

vm.runInThisContext(fs.readFileSync('shared/engine.js', 'utf8'));
vm.runInThisContext(fs.readFileSync('shared/diagram.js', 'utf8'));
const D = globalThis.DiagramCore;

const DECK = {
  id: 'd',
  label: 'Mazzo',
  w: 400,
  h: 300,
  cw: 100,
  img: { src: 'img/d.svg', x: 100, y: 0, w: 200, h: 300 },
  targets: [
    { id: 'cranio', name: 'Cranio', x: 200, y: 20, side: 'l', ly: 20 },
    { id: 'femore', name: 'Femore', x: 200, y: 150, side: 'l', ly: 150 },
    { id: 'falangi-m', name: 'Falangi', x: 150, y: 140, side: 'r', ly: 140 },
    { id: 'falangi-p', name: 'Falangi', x: 220, y: 290, side: 'r', ly: 290 },
  ],
};

const status = (result) => Object.fromEntries(result.slots.map((s) => [s.target.id, s.status]));

test('place puts a card in an empty slot', () => {
  assert.deepEqual(D.place({}, 'cranio', 'cranio'), { cranio: 'cranio' });
});

test('place moves a card out of its old slot', () => {
  const out = D.place({ cranio: 'femore', femore: 'cranio' }, 'femore', 'femore');
  assert.deepEqual(out, { femore: 'femore' });
});

test("place replaces a slot's card, which goes back to the tray", () => {
  const out = D.place({ cranio: 'femore', tibia: 'tibia' }, 'cranio', 'cranio');
  assert.deepEqual(out, { cranio: 'cranio', tibia: 'tibia' });
});

test('place with null empties the slot', () => {
  assert.deepEqual(D.place({ cranio: 'cranio', femore: 'femore' }, 'cranio', null), { femore: 'femore' });
  assert.deepEqual(D.place({}, 'cranio', null), {});
});

test('place leaves the input untouched', () => {
  const placed = { cranio: 'femore', femore: 'cranio' };
  const copy = { ...placed };
  const out = D.place(placed, 'cranio', 'cranio');
  assert.deepEqual(placed, copy);
  assert.notEqual(out, placed);
});

test('grade marks ok, bad and none and counts the right slots', () => {
  const result = D.grade(DECK, { cranio: 'cranio', femore: 'falangi-m' });
  assert.equal(result.total, 4);
  assert.equal(result.ok, 1);
  assert.deepEqual(status(result), { cranio: 'ok', femore: 'bad', 'falangi-m': 'none', 'falangi-p': 'none' });
  const bad = result.slots.find((s) => s.target.id === 'femore');
  assert.equal(bad.card.id, 'falangi-m');
  assert.equal(result.slots.find((s) => s.target.id === 'falangi-p').card, null);
});

test('grade treats cards with the same name as interchangeable', () => {
  const result = D.grade(DECK, { cranio: 'cranio', femore: 'femore', 'falangi-m': 'falangi-p', 'falangi-p': 'falangi-m' });
  assert.equal(result.ok, 4);
  assert.ok(result.slots.every((s) => s.status === 'ok'));
});

test('grade counts an unknown card id as an empty slot', () => {
  const result = D.grade(DECK, { cranio: 'nope', femore: 'femore' });
  assert.equal(result.ok, 1);
  assert.equal(status(result).cranio, 'none');
  assert.equal(result.slots.find((s) => s.target.id === 'cranio').card, null);
});

test('grade of an empty board is all none', () => {
  const result = D.grade(DECK, {});
  assert.equal(result.ok, 0);
  assert.ok(result.slots.every((s) => s.status === 'none'));
});
