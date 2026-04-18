import { useEffect } from 'react'

export function useKeyboardShortcut(keys, handler, enabled = true) {
  useEffect(() => {
    if (!enabled) return undefined
    const expected = Array.isArray(keys) ? keys : [keys]
    const onKeyDown = (event) => {
      const normalized = event.key.toLowerCase()
      if (expected.includes('mod+k')) {
        if ((event.metaKey || event.ctrlKey) && normalized === 'k') {
          event.preventDefault()
          handler(event)
        }
      }
      if (expected.includes(normalized)) {
        handler(event)
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [enabled, handler, keys])
}
