import { test } from 'node:test'
import assert from 'node:assert/strict'
import { dateKey, monthDays } from './calendar.js'

test('month grid starts on Monday and includes adjacent months', () => {
  const days = monthDays(new Date(2026, 8, 1))
  assert.equal(days.length, 42)
  assert.equal(days[0].key, '2026-08-31')
  assert.equal(days[0].outside, true)
  assert.equal(days[1].outside, false)
  assert.equal(days[41].key, '2026-10-11')
  assert.equal(new Set(days.map(day => day.key)).size, 42)
})

test('leap years, Monday starts and year boundaries', () => {
  assert.equal(monthDays(new Date(2024, 1, 1)).filter(day => !day.outside).length, 29)
  assert.equal(monthDays(new Date(2027, 1, 1))[0].key, '2027-02-01')
  assert.equal(monthDays(new Date(2027, 0, 1))[0].key, '2026-12-28')
})

test('date keys preserve the local day across daylight saving changes', () => {
  assert.equal(dateKey(new Date(2026, 9, 25)), '2026-10-25')
  assert.equal(dateKey(new Date(2026, 2, 29)), '2026-03-29')
})
