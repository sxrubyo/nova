import React, { createContext, useState, useEffect } from 'react'
import { api } from '../utils/api'

export const AuthContext = createContext()
const GENERIC_NAMES = new Set(['Admin User', 'User', 'Operator'])
const DEFAULT_USER = {
  name: 'Admin User',
  email: 'admin@nova-os.com',
  avatar: null,
  preferredName: '',
  roleTitle: '',
  birthDate: '',
  defaultAssistant: 'both',
  onboardingCompletedAt: null,
  ownerName: '',
  workspaceName: '',
  plan: 'trial',
}

function normalizeUser(user) {
  return {
    ...DEFAULT_USER,
    ...(user || {}),
  }
}

function resolveDisplayName(currentUser, fallbackName, fallbackEmail) {
  if (currentUser?.preferredName) {
    return currentUser.preferredName
  }
  if (currentUser?.name && !GENERIC_NAMES.has(currentUser.name)) {
    return currentUser.name
  }
  if (fallbackName) {
    return fallbackName
  }
  if (fallbackEmail) {
    return fallbackEmail.split('@')[0]
  }
  return 'Admin User'
}

function extractWorkspaceEnvelope(payload, usingApiKey = false) {
  if (!payload) return null
  return usingApiKey ? payload : payload.workspace
}

function workspaceToUser(currentUser, workspace) {
  if (!workspace) return normalizeUser(currentUser)

  const profile = workspace.profile || {}
  const ownerName = workspace.owner_name || profile.owner_name || ''
  const preferredName = profile.preferred_name || ''
  const roleTitle = profile.role_title || ''
  const birthDate = profile.birth_date || ''
  const defaultAssistant = profile.default_assistant || 'both'
  const onboardingCompletedAt = profile.onboarding_completed_at || null

  return normalizeUser({
    ...currentUser,
    name: resolveDisplayName({ ...currentUser, preferredName }, ownerName || workspace.name, workspace.email),
    email: workspace.email || currentUser?.email,
    ownerName,
    workspaceName: workspace.name || currentUser?.workspaceName,
    preferredName,
    roleTitle,
    birthDate,
    defaultAssistant,
    onboardingCompletedAt,
    plan: workspace.plan || currentUser?.plan || 'trial',
  })
}

export function AuthProvider({ children }) {
  const [apiKey, setApiKey] = useState(localStorage.getItem('nova_api_key') || '')
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isAuthLoading, setIsAuthLoading] = useState(true)
  const [user, setUserState] = useState(() => {
    const saved = localStorage.getItem('nova_user')
    return normalizeUser(saved ? JSON.parse(saved) : null)
  })

  const setUser = (value) => {
    setUserState((previous) => {
      const nextValue = typeof value === 'function' ? value(previous) : value
      return normalizeUser(nextValue)
    })
  }

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

  const refreshSession = async ({ apiKeyValue = apiKey } = {}) => {
    const usingApiKey = Boolean(apiKeyValue)
    const authPayload = usingApiKey
      ? await api.get('/workspaces/me', {
        headers: apiKeyValue ? { 'x-api-key': apiKeyValue } : {},
      })
      : await api.get('/auth/session')

    const workspace = extractWorkspaceEnvelope(authPayload, usingApiKey)
    if (!workspace || (!usingApiKey && !authPayload.authenticated)) {
      throw new Error('No active session')
    }

    const nextUser = workspaceToUser(user, workspace)
    setIsAuthenticated(true)
    setUser((previous) => workspaceToUser(previous, workspace))
    return nextUser
  }

  useEffect(() => {
    const bootstrapAuth = async () => {
      try {
        await refreshSession({ apiKeyValue: apiKey })
      } catch (err) {
        setIsAuthenticated(false)
        setUser((prev) => ({
          ...normalizeUser(prev),
          name: prev.name || 'Admin User',
          email: prev.email || 'admin@nova-os.com',
        }))
      } finally {
        setIsAuthLoading(false)
      }
    }

    bootstrapAuth()
  }, [apiKey])

  const updateProfile = async (data) => {
    const payload = {
      owner_name: data.ownerName,
      preferred_name: data.preferredName,
      role_title: data.roleTitle,
      birth_date: data.birthDate || null,
      default_assistant: data.defaultAssistant,
      complete_onboarding: Boolean(data.completeOnboarding),
    }

    const workspace = await api.patch('/workspaces/me/profile', payload)
    const nextUser = workspaceToUser(user, workspace)
    setUser(nextUser)
    return nextUser
  }

  const completeOnboarding = async (data = {}) => {
    const nextUser = await updateProfile({
      ownerName: data.ownerName || user.ownerName || data.preferredName || user.name,
      preferredName: data.preferredName ?? user.preferredName,
      roleTitle: data.roleTitle ?? user.roleTitle,
      birthDate: data.birthDate ?? user.birthDate,
      defaultAssistant: data.defaultAssistant ?? user.defaultAssistant ?? 'both',
      completeOnboarding: true,
    })
    return nextUser
  }

  const resetOnboarding = async () => {
    const workspace = await api.patch('/workspaces/me/profile', {
      owner_name: user.ownerName || user.name,
      preferred_name: user.preferredName,
      role_title: user.roleTitle,
      birth_date: user.birthDate || null,
      default_assistant: user.defaultAssistant || 'both',
      reopen_onboarding: true,
    })
    setUser((prev) => normalizeUser({
      ...workspaceToUser(prev, workspace),
      onboardingCompletedAt: null,
    }))
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
      updateProfile,
      completeOnboarding,
      resetOnboarding,
      refreshSession,
    }}>
      {children}
    </AuthContext.Provider>
  )
}
