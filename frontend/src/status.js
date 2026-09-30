export function statusInfo(value, dueDate = null, today = null) {
  const key = String(value || '').trim().toLocaleLowerCase('pl-PL')
  if (['wykonany', 'zakończony', 'zakończona', 'gotowy', 'wydany'].includes(key)) return { label: 'Zakończone', tone: 'done' }
  if (['anulowany', 'anulowana'].includes(key)) return { label: 'Anulowane', tone: 'neutral' }
  const now = new Date()
  const current = today || `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
  if (dueDate && dueDate < current) return { label: 'Zaległe', tone: 'overdue' }
  if (['w trakcie', 'w realizacji'].includes(key)) return { label: 'W trakcie', tone: 'active' }
  if (['nowy', 'planowany', 'planowana', ''].includes(key)) return { label: 'Planowane', tone: 'planned' }
  return { label: value, tone: 'neutral' }
}
