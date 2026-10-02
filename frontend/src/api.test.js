import test from 'node:test'
import assert from 'node:assert/strict'
import { formatApiError } from './api.js'

test('SMTP validation names the invalid field without including submitted secrets', () => {
  const message = formatApiError([
    { loc: ['body', 'host'], type: 'string_pattern_mismatch', input: 'private-input' },
    { loc: ['body', 'public_url'], type: 'value_error', msg: 'Value error, Podaj adres HTTPS panelu', input: 'private-input' },
    { loc: ['body', 'password'], type: 'string_too_long', input: 'secret-password' },
  ])
  assert.match(message, /Serwer poczty:.*smtp.gmail.com/)
  assert.match(message, /Adres panelu: Podaj adres HTTPS panelu/)
  assert.match(message, /Hasło: Wartość jest za długa/)
  assert.doesNotMatch(message, /private-input|secret-password/)
})

test('permission and connection errors keep a usable message', () => {
  assert.equal(formatApiError('Ta operacja wymaga uprawnień administratora'), 'Ta operacja wymaga uprawnień administratora')
  assert.match(formatApiError(undefined), /Nie udało się/)
  assert.match(formatApiError([{ loc: ['body', 'port'], type: 'less_than_equal' }]), /65535/)
})
