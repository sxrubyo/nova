import { useEffect, useRef, useState } from 'react'

export function useIntersectionObserver(options) {
  const ref = useRef(null)
  const [isIntersecting, setIsIntersecting] = useState(false)

  useEffect(() => {
    if (!ref.current) return undefined
    const observer = new IntersectionObserver(([entry]) => {
      setIsIntersecting(entry.isIntersecting)
    }, options)

    observer.observe(ref.current)
    return () => observer.disconnect()
  }, [options])

  return { ref, isIntersecting }
}
