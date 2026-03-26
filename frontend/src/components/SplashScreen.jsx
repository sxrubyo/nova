import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { NovaLogo } from '@/components/brand/NovaLogo'

function SplashScreen({ onFinish }) {
  const [visible, setVisible] = useState(true)

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setVisible(false)
      window.setTimeout(onFinish, 260)
    }, 1450)
    return () => window.clearTimeout(timer)
  }, [onFinish])

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-[#07080c]"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <div className="relative flex flex-col items-center">
            <motion.div
              className="absolute h-40 w-40 rounded-full bg-nova-accent/18 blur-3xl"
              animate={{ scale: [0.82, 1.12, 0.96], opacity: [0.4, 0.8, 0.4] }}
              transition={{ duration: 1.6, repeat: Infinity }}
            />
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.35 }}>
              <NovaLogo />
            </motion.div>
            <motion.div
              className="mt-6 h-1 w-44 overflow-hidden rounded-full bg-white/8"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <motion.div
                className="h-full rounded-full bg-gradient-to-r from-nova-accent via-nova-accent-glow to-nova-accent-2"
                initial={{ x: '-100%' }}
                animate={{ x: '0%' }}
                transition={{ duration: 1.15, ease: [0.16, 1, 0.3, 1] }}
              />
            </motion.div>
            <motion.div
              className="mt-4 text-[11px] uppercase tracking-[0.28em] text-nova-text-secondary"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
            >
              Powering governance control
            </motion.div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

export default SplashScreen
