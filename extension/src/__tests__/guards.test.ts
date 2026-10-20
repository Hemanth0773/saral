import test from 'node:test';
import assert from 'node:assert/strict';

import { createInFlightGuard } from '../popup/guards.ts';

test('the first action is allowed to start', () => {
  const guard = createInFlightGuard();
  assert.equal(guard.tryStart(), true);
  assert.equal(guard.isRunning, true);
});

test('a second action is rejected while one is running', () => {
  const guard = createInFlightGuard();
  guard.tryStart();
  assert.equal(guard.tryStart(), false);
  assert.equal(guard.isRunning, true);
});

test('the action can start again once it finished', () => {
  const guard = createInFlightGuard();
  guard.tryStart();
  guard.finish();
  assert.equal(guard.isRunning, false);
  assert.equal(guard.tryStart(), true);
});

test('two clicks in the same tick only start one request', () => {
  const guard = createInFlightGuard();
  const started = [guard.tryStart(), guard.tryStart()];
  assert.deepEqual(started, [true, false]);
});
