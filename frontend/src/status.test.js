import test from 'node:test'
import assert from 'node:assert/strict'
import { statusInfo } from './status.js'

test('overdue excludes completed and cancelled appointments', () => {
  assert.equal(statusInfo('planowany', '2026-09-28', '2026-09-29').tone, 'overdue')
  assert.equal(statusInfo('wykonany', '2026-09-28', '2026-09-29').tone, 'done')
  assert.equal(statusInfo('anulowany', '2026-09-28', '2026-09-29').tone, 'neutral')
  assert.equal(statusInfo('planowany', '2026-09-29', '2026-09-29').tone, 'planned')
  assert.equal(statusInfo('planowany', null, '2026-09-29').tone, 'planned')
})
test('existing statuses use a shared vocabulary while custom statuses are retained', () => {
  assert.equal(statusInfo('w realizacji').label, 'W trakcie')
  assert.equal(statusInfo('gotowy').label, 'Zakończone')
  assert.equal(statusInfo('Do odbioru').label, 'Do odbioru')
})
