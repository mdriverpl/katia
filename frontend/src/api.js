export const api = import.meta.env?.VITE_API_URL || '/api'

export function formatApiError(detail) {
  if (typeof detail === 'string') return detail
  if (!Array.isArray(detail)) return 'Nie udało się zapisać lub pobrać danych. Spróbuj ponownie.'
  const labels = { host: 'Serwer poczty', port: 'Port', security: 'Szyfrowanie', username: 'Login', password: 'Hasło', sender: 'E-mail nadawcy', public_url: 'Adres panelu', sender_filter: 'Filtr nadawcy', attachment_prefix: 'Prefiks załączników' }
  const messages = {
    string_pattern_mismatch: 'Nieprawidłowy format.',
    missing: 'Uzupełnij to pole.',
    string_too_short: 'Wartość jest za krótka.',
    string_too_long: 'Wartość jest za długa.',
    int_parsing: 'Wpisz liczbę całkowitą.',
    int_type: 'Wpisz liczbę całkowitą.',
    literal_error: 'Wybierz jedną z dostępnych opcji.',
    greater_than_equal: 'Wartość jest za mała.',
    less_than_equal: 'Wartość jest za duża.',
  }
  return detail.map(item => {
    const field = item.loc?.filter(part => part !== 'body').join('.') || 'Formularz'
    let message = messages[item.type] || 'Sprawdź poprawność tego pola.'
    if (item.type === 'value_error' && typeof item.msg === 'string') message = item.msg.replace(/^Value error, /, '')
    if (field === 'host' && item.type === 'string_pattern_mismatch') message = 'Podaj samą nazwę serwera, np. smtp.gmail.com, bez https:// i numeru portu.'
    if (field === 'port' && ['greater_than_equal', 'less_than_equal'].includes(item.type)) message = 'Podaj port od 1 do 65535.'
    return `${labels[field] || field}: ${message}`
  }).join(' ') || 'Sprawdź poprawność wprowadzonych danych.'
}
