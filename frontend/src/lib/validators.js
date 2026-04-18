export function validateEmail(value) {
  if (!value) return 'Email is required'
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailPattern.test(value) ? '' : 'Use a valid email address'
}

export function validateRequired(value, label) {
  return value ? '' : `${label} is required`
}

export function validatePassword(value) {
  if (!value) return 'Password is required'
  if (value.length < 8) return 'Password must be at least 8 characters'
  return ''
}
