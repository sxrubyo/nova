import React, { createContext, useState, useEffect } from 'react'
import { api } from '../utils/api'

export const AuthContext = createContext()

export function AuthProvider({ children }) {
  const [apiKey, setApiKey] = useState(localStorage.getItem('nova_api_key') || '')
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isAuthLoading, setIsAuthLoading] = useState(true)
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('nova_user')
    return saved ? JSON.parse(saved) : { 
      name: 'Admin User', 
      email: 'admin@nova-os.com',
      avatar: null 
    }
  })

  useEffect(() => {
    localStorage.setItem('nova_user', JSON.stringify(user))
  }, [user])

  useEffect(() => {
    if (apiKey) {
      localStorage.setItem('nova_api_key', apiKey)
    } else {
      localStorage.removeItem('nova_api_key')
    }
  }, [apiKey])

  useEffect(() => {
    const bootstrapAuth = async () => {
      try {
        const workspace = await api.get('/workspaces/me')
        setIsAuthenticated(true)
        setUser((prev) => ({
          ...prev,
          name: workspace.name || prev.name,
          email: workspace.email || prev.email,
        }))
      } catch (err) {
        setIsAuthenticated(false)
        if (!apiKey) {
          setUser((prev) => ({
            ...prev,
            name: prev.name || 'Admin User',
            email: prev.email || 'admin@nova-os.com',
          }))
        }
      } finally {
        setIsAuthLoading(false)
      }
    }

    bootstrapAuth()
  }, [apiKey])

  const updateProfile = (data) => {
    setUser(prev => ({ ...prev, ...data }))
  }

  return (
    <AuthContext.Provider value={{ 
      isAuthenticated, 
      isAuthLoading,
      setIsAuthenticated, 
      user, 
      setUser, 
      apiKey, 
      setApiKey,
      updateProfile 
    }}>
      {children}
    </AuthContext.Provider>
  )
}
