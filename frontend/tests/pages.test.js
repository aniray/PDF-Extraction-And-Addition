import test from 'node:test';
import assert from 'node:assert/strict';
import { parseRange, movePage } from '../src/services/pages.js';

test('blank range selects every page', () => assert.deepEqual(parseRange('', 3), [1, 2, 3]));
test('ranges preserve selection order and deduplicate overlap', () => assert.deepEqual(parseRange('5, 1-3, 2', 5), [5, 1, 2, 3]));
test('invalid and out-of-bounds ranges fail', () => {
  for (const value of ['0', '-1', '4', '3-1', '1,', 'a', '1.5', '1-999999999']) assert.throws(() => parseRange(value, 3));
});
test('moving in either direction preserves all entries without mutating input', () => {
  const source = ['a', 'b', 'c'];
  assert.deepEqual(movePage(source, 0, 2), ['b', 'c', 'a']);
  assert.deepEqual(movePage(source, 2, 0), ['c', 'a', 'b']);
  assert.deepEqual(movePage(source, 0, -1), source);
  assert.deepEqual(source, ['a', 'b', 'c']);
});
