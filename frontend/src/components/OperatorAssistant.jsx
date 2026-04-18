import React, { useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  ChevronLeft,
  ChevronRight,
  Copy,
  Eye,
  EyeOff,
  KeyRound,
  Loader2,
  Play,
  RefreshCcw,
  Send,
  Sparkles,
  Maximize2,
  Minimize2,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useTheme } from '../context/ThemeContext'
import { api } from '../utils/api'
import ProviderMark from './brand/ProviderMark'

const starterPrompts = [
  'What should I do next in this workspace?',
  'Summarize current risk and pending alerts.',
  'How do I create a governed agent?',
  'Which commands should I run first?',
]

const PROVIDER_KEYS_STORAGE = 'nova_assistant_provider_keys'

function loadProviderKeys() {
  try {
    return JSON.parse(localStorage.getItem(PROVIDER_KEYS_STORAGE) || '{}')
  } catch {
    return {}
  }
}

function OperatorAssistant({ onCreateAgent, onRefresh, workspaceName = 'workspace' }) {
  const navigate = useNavigate()
  const { theme } = useTheme()
  const [isOpen, setIsOpen] = useState(true)
  const [isFullScreen, setIsFullScreen] = useState(false)
  const [showModelLane, setShowModelLane] = useState(false)
  const [showApiKey, setShowApiKey] = useState(false)
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [catalogLoading, setCatalogLoading] = useState(true)
  const [providers, setProviders] = useState([])
  const [selectedProvider, setSelectedProvider] = useState('')
  const [selectedModel, setSelectedModel] = useState('')
  const [providerKeys, setProviderKeys] = useState(() => loadProviderKeys())
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: `Your assistant is live for ${workspaceName}. Ask about alerts, risk, agent setup, commands, or how to operate this workspace.`,
      suggestedCommands: ['nova status', 'nova discover', 'nova agents'],
      actions: [
        { type: 'refresh', label: 'Refresh runtime', value: 'refresh' },
        { type: 'modal', label: 'Create agent', value: 'create_agent' },
      ],
      meta: 'workspace-aware',
    },
  ])

  useEffect(() => {
    localStorage.setItem(PROVIDER_KEYS_STORAGE, JSON.stringify(providerKeys))
  }, [providerKeys])

  useEffect(() => {
    let cancelled = false

    const loadCatalog = async () => {
      try {
        const response = await api.get('/assistant/models')
        if (cancelled) return

        const resolvedProviders = response.providers || []
        setProviders(resolvedProviders)

        const defaultProvider = response.default_provider || resolvedProviders[0]?.key || ''
        const providerMeta = resolvedProviders.find((provider) => provider.key === defaultProvider) || resolvedProviders[0]
        const defaultModel =
          response.default_model || providerMeta?.default_model || providerMeta?.models?.[0]?.id || ''

        setSelectedProvider(providerMeta?.key || '')
        setSelectedModel(defaultModel)
      } catch {
        if (!cancelled) {
          setProviders([])
        }
      } finally {
        if (!cancelled) {
          setCatalogLoading(false)
        }
      }
    }

    loadCatalog()
    return () => {
      cancelled = true
    }
  }, [])

  const currentProvider = useMemo(
    () => providers.find((provider) => provider.key === selectedProvider) || null,
    [providers, selectedProvider],
  )

  const availableModels = currentProvider?.models || []
  const selectedModelMeta = availableModels.find((model) => model.id === selectedModel) || null
  const latestAssistant = useMemo(
    () => [...messages].reverse().find((message) => message.role === 'assistant'),
    [messages],
  )
  const currentApiKey = providerKeys[selectedProvider] || ''
  const currentProviderReady = Boolean(currentProvider && (currentProvider.available || currentApiKey))

  const isDark = theme === 'dark'
  const canSend = input.trim().length > 0 && !isLoading

  const ui = isDark
    ? {
        toggle: 'border-white/10 bg-[#11151b] text-white hover:bg-[#171c22]',
        shell: 'border-white/10 bg-[#0f1318]/96 text-white shadow-[0_40px_120px_-48px_rgba(0,0,0,0.82)]',
        line: 'border-white/8',
        hint: 'text-white/42',
        subtext: 'text-white/72',
        muted: 'text-white/58',
        chip: 'border-white/8 bg-white/[0.05] text-white/74 hover:border-white/14 hover:bg-white/[0.09] hover:text-white',
        provider: 'border-white/8 bg-white/[0.03] hover:border-white/14 hover:bg-white/[0.06]',
        providerActive: 'border-[#79d9ab]/30 bg-[#79d9ab]/12 text-white shadow-[0_18px_35px_-26px_rgba(121,217,171,0.85)]',
        model: 'border-white/8 bg-black/18 hover:border-white/12 hover:bg-black/24',
        modelActive: 'border-[#79d9ab]/30 bg-[#79d9ab]/10 text-white',
        providerLogo: 'bg-white',
        assistantBubble: 'bg-white/[0.06] text-white',
        userBubble: 'bg-[#79d9ab] text-[#062817]',
        command: 'bg-black/20 text-white/78 hover:bg-black/28',
        action: 'border-white/10 bg-white/[0.05] text-white/78 hover:border-white/16 hover:bg-white/[0.1] hover:text-white',
        textareaWrap: 'bg-white/[0.05]',
        textarea: 'text-white placeholder:text-white/30',
        footerMeta: 'text-white/38',
        button: 'bg-white text-[#111111] hover:bg-[#f3f3f3]',
        utilityButton: 'bg-white/6 text-white/72 hover:bg-white/10 hover:text-white',
        keyWrap: 'border-white/8 bg-white/[0.04]',
        keyInput: 'text-white placeholder:text-white/28',
      }
    : {
        toggle: 'border-black/8 bg-[#f4efe4] text-[#161616] hover:bg-white',
        shell: 'border-black/8 bg-[#fbf7ef]/96 text-[#111111] shadow-[0_40px_120px_-52px_rgba(0,0,0,0.22)]',
        line: 'border-black/8',
        hint: 'text-black/42',
        subtext: 'text-black/72',
        muted: 'text-black/56',
        chip: 'border-black/8 bg-black/[0.03] text-black/68 hover:border-black/12 hover:bg-black/[0.05] hover:text-black',
        provider: 'border-black/8 bg-[#f6f1e6] hover:border-black/14 hover:bg-white',
        providerActive: 'border-[#3ecf8e]/25 bg-[#ecfbf3] text-[#111111] shadow-[0_18px_35px_-26px_rgba(62,207,142,0.45)]',
        model: 'border-black/8 bg-white/80 hover:border-black/12 hover:bg-white',
        modelActive: 'border-[#111111]/12 bg-[#111111] text-white',
        providerLogo: 'bg-white',
        assistantBubble: 'bg-white text-[#111111]',
        userBubble: 'bg-[#111111] text-white',
        command: 'bg-[#f4efe4] text-[#111111] hover:bg-[#ece4d4]',
        action: 'border-black/10 bg-black/[0.03] text-black/72 hover:border-black/14 hover:bg-black/[0.06] hover:text-black',
        textareaWrap: 'bg-black/[0.03]',
        textarea: 'text-[#111111] placeholder:text-black/34',
        footerMeta: 'text-black/36',
        button: 'bg-[#111111] text-white hover:bg-[#222222]',
        utilityButton: 'bg-black/[0.04] text-black/64 hover:bg-black/[0.08] hover:text-black',
        keyWrap: 'border-black/8 bg-black/[0.03]',
        keyInput: 'text-[#111111] placeholder:text-black/28',
      }

  const handleAction = async (action) => {
    if (action.type === 'copy_command' && action.value) {
      await navigator.clipboard.writeText(action.value)
      return
    }
    if (action.type === 'route' && action.value) {
      navigate(action.value)
      return
    }
    if (action.type === 'modal' && action.value === 'create_agent') {
      onCreateAgent?.()
      return
    }
    if (action.type === 'refresh') {
      onRefresh?.()
    }
  }

  const runCommand = async (command) => {
    if (isLoading) return
    setIsLoading(true)

    setMessages((prev) => [
      ...prev,
      {
        id: `user-cmd-${Date.now()}`,
        role: 'user',
        content: `Run: ${command}`,
      },
    ])

    try {
      const response = await api.post('/assistant/execute', { command })
      const displayOutput =
        response.display_output ||
        (response.success
          ? `Nova ejecutó \`${command}\` correctamente.`
          : `Nova no pudo completar \`${command}\`.`)

      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-cmd-${Date.now()}`,
          role: 'assistant',
          content: displayOutput,
          meta: response.success ? 'terminal-output' : 'terminal-error',
        },
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-cmd-error-${Date.now()}`,
          role: 'assistant',
          content: err.message || 'Failed to connect to terminal.',
          meta: 'terminal-error',
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const handleProviderSelect = (providerKey) => {
    const providerMeta = providers.find((provider) => provider.key === providerKey)
    setSelectedProvider(providerKey)
    setSelectedModel(providerMeta?.default_model || providerMeta?.models?.[0]?.id || '')
  }

  const updateProviderKey = (value) => {
    setProviderKeys((prev) => ({
      ...prev,
      [selectedProvider]: value,
    }))
  }

  const sendMessage = async (promptText) => {
    const message = promptText.trim()
    if (!message) return

    setMessages((prev) => [
      ...prev,
      {
        id: `user-${Date.now()}`,
        role: 'user',
        content: message,
      },
    ])
    setInput('')
    setIsLoading(true)

    try {
      const response = await api.post('/assistant/chat', {
        message,
        page: 'dashboard',
        provider: selectedProvider || undefined,
        model: selectedModel || undefined,
        api_key: currentApiKey || undefined,
      })

      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: response.message,
          suggestedCommands: response.suggested_commands || [],
          actions: response.actions || [],
          meta: `${response.provider} · ${response.model}`,
        },
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-error-${Date.now()}`,
          role: 'assistant',
          content: err.message || 'Assistant failed to respond.',
          suggestedCommands: [],
          actions: [],
          meta: 'error',
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className={`pointer-events-none fixed z-[80] ${isFullScreen ? 'inset-0 bg-background' : 'inset-y-0 right-0 p-3 md:p-5'}`}>
      <div className={`pointer-events-auto flex items-start gap-3 ${isFullScreen ? 'mx-auto h-full w-full max-w-4xl p-5' : ''}`}>
        {!isFullScreen && (
          <button
            type="button"
            onClick={() => setIsOpen((current) => !current)}
            className={`mt-16 inline-flex h-12 w-12 items-center justify-center rounded-2xl border shadow-[0_24px_60px_-32px_rgba(0,0,0,0.35)] transition ${ui.toggle}`}
          >
            {isOpen ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </button>
        )}

        <AnimatePresence initial={false}>
          {isOpen && (
            <motion.aside
              initial={isFullScreen ? { opacity: 0 } : { x: 28, opacity: 0 }}
              animate={isFullScreen ? { opacity: 1 } : { x: 0, opacity: 1 }}
              exit={isFullScreen ? { opacity: 0 } : { x: 28, opacity: 0 }}
              transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
              className={`flex flex-col overflow-hidden rounded-[32px] border ${
                isFullScreen 
                  ? `fixed inset-0 z-[100] h-full w-full rounded-none border-none ${isDark ? 'bg-[#0f1318]' : 'bg-[#fbf7ef]'} text-${isDark ? 'white' : '[#111111]'}` 
                  : `h-[calc(100vh-2.5rem)] w-[460px] max-w-[calc(100vw-4.75rem)] backdrop-blur-xl ${ui.shell}`
              }`}
            >
              <div className={`border-b px-5 py-4 ${ui.line}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.26em] text-[#79d9ab]">Talk with your agent</p>
                    <h2 className="mt-1 text-lg font-semibold tracking-[-0.03em]">Workspace assistant</h2>
                    <p className={`mt-2 text-sm ${ui.subtext}`}>
                      Ask about alerts, risk, agent setup, commands, and workspace operations.
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setIsFullScreen((current) => !current)}
                      className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl transition ${ui.utilityButton}`}
                    >
                      {isFullScreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                    </button>
                    <button
                      type="button"
                      onClick={onRefresh}
                      className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl transition ${ui.utilityButton}`}
                    >
                      <RefreshCcw className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className={`text-[10px] font-semibold uppercase tracking-[0.18em] ${ui.hint}`}>Current model</p>
                    <p className="mt-1 truncate text-sm font-semibold">
                      {currentProvider?.label || 'No provider'} · {selectedModelMeta?.label || 'No model'}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowModelLane((current) => !current)}
                    className={`rounded-full border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.2em] transition ${ui.chip}`}
                  >
                    {showModelLane ? 'Hide models' : 'Change model'}
                  </button>
                </div>

                <AnimatePresence initial={false}>
                  {showModelLane && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
                      className="overflow-hidden"
                    >
                      <div className="mt-4 space-y-3">
                        <div className="grid max-h-[220px] gap-2 overflow-y-auto pr-1 sm:grid-cols-2">
                          {catalogLoading ? (
                            <div className={`col-span-full flex items-center gap-2 rounded-[22px] border px-3 py-3 text-xs ${ui.chip}`}>
                              <Loader2 className="h-3.5 w-3.5 animate-spin text-[#79d9ab]" />
                              Loading providers
                            </div>
                          ) : (
                            providers.map((provider) => {
                              const active = provider.key === selectedProvider
                              return (
                                <button
                                  key={provider.key}
                                  type="button"
                                  onClick={() => handleProviderSelect(provider.key)}
                                  className={`group rounded-[22px] border px-3 py-3 text-left transition ${
                                    active ? ui.providerActive : ui.provider
                                  }`}
                                >
                                  <div className="flex items-center gap-2.5">
                                    <ProviderMark
                                      src={provider.logo}
                                      alt={provider.label}
                                      frameClassName={`h-11 w-11 rounded-2xl p-2 ${ui.providerLogo}`}
                                      imageClassName="max-h-5 max-w-5"
                                    />
                                    <div className="min-w-0">
                                      <p className="truncate text-sm font-semibold">{provider.label}</p>
                                      <p className={`truncate text-[10px] uppercase tracking-[0.18em] ${ui.hint}`}>
                                        {provider.available ? 'server key' : 'use your key'}
                                      </p>
                                    </div>
                                  </div>
                                </button>
                              )
                            })
                          )}
                        </div>

                        {currentProvider && (
                          <>
                            <div className={`rounded-[22px] border p-3 ${ui.keyWrap}`}>
                              <div className="flex items-center justify-between gap-3">
                                <div className="min-w-0">
                                  <p className="text-sm font-semibold">Provider access</p>
                                  <p className={`mt-1 text-xs ${ui.muted}`}>
                                    {currentProvider.available
                                      ? 'Server key detected. You can still override it with your own.'
                                      : 'No server key for this provider. Paste your own API key to use it.'}
                                  </p>
                                </div>
                                <button
                                  type="button"
                                  onClick={() => setShowApiKey((current) => !current)}
                                  className={`inline-flex h-9 w-9 items-center justify-center rounded-2xl transition ${ui.utilityButton}`}
                                >
                                  {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                </button>
                              </div>

                              <div className="mt-3 flex items-center gap-2 rounded-[18px] border border-inherit px-3 py-2">
                                <KeyRound className="h-4 w-4 shrink-0 text-[#79d9ab]" />
                                <input
                                  type={showApiKey ? 'text' : 'password'}
                                  value={currentApiKey}
                                  onChange={(event) => updateProviderKey(event.target.value)}
                                  placeholder={`Paste ${currentProvider.label} API key`}
                                  className={`w-full bg-transparent text-sm outline-none ${ui.keyInput}`}
                                />
                              </div>
                            </div>

                            <div className="grid gap-2">
                              {availableModels.map((model) => {
                                const active = model.id === selectedModel
                                return (
                                  <button
                                    key={model.id}
                                    type="button"
                                    onClick={() => setSelectedModel(model.id)}
                                    className={`rounded-[20px] border px-3 py-3 text-left transition ${
                                      active ? ui.modelActive : ui.model
                                    }`}
                                  >
                                    <div className="flex items-center justify-between gap-3">
                                      <div className="min-w-0">
                                        <p className="truncate text-sm font-semibold">{model.label}</p>
                                        <p className={`mt-1 text-[11px] uppercase tracking-[0.16em] ${active && !isDark ? 'text-white/58' : ui.hint}`}>
                                          {model.family}
                                        </p>
                                      </div>
                                      <span
                                        className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${
                                          active
                                            ? 'bg-[#79d9ab]/14 text-[#1e8a5c] dark:text-[#a5ecc7]'
                                            : isDark
                                              ? 'bg-white/[0.06] text-white/52'
                                              : 'bg-black/[0.05] text-black/50'
                                        }`}
                                      >
                                        {model.status}
                                      </span>
                                    </div>
                                  </button>
                                )
                              })}
                            </div>
                          </>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                <div className="mt-4 flex flex-wrap gap-2">
                  {starterPrompts.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => sendMessage(prompt)}
                      className={`rounded-full border px-3 py-1.5 text-left text-[11px] leading-5 transition ${ui.chip}`}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
                {messages.map((message) => (
                  <div key={message.id} className={message.role === 'assistant' ? 'pr-6' : 'pl-10'}>
                    <div
                      className={`rounded-[24px] px-4 py-3 shadow-[0_18px_40px_-34px_rgba(0,0,0,0.8)] ${
                        message.role === 'assistant' ? ui.assistantBubble : ui.userBubble
                      }`}
                    >
                      <div className="whitespace-pre-wrap break-words text-sm leading-7">{message.content}</div>

                      {message.role === 'assistant' && message.suggestedCommands?.length > 0 && (
                        <div className="mt-4 space-y-2">
                          <p className={`text-[10px] font-semibold uppercase tracking-[0.2em] ${ui.hint}`}>Suggested commands</p>
                          {message.suggestedCommands.map((command) => (
                            <div key={command} className={`flex items-center gap-1 rounded-2xl p-1 transition ${ui.command}`}>
                              <button
                                type="button"
                                onClick={() => runCommand(command)}
                                className="flex flex-1 items-center gap-2 truncate px-2 py-1.5 text-left font-mono text-[11px]"
                              >
                                <Play className="h-3 w-3 shrink-0 text-[#79d9ab]" />
                                <span className="truncate">{command}</span>
                              </button>
                              <button
                                type="button"
                                onClick={() => navigator.clipboard.writeText(command)}
                                className={`flex h-7 w-7 items-center justify-center rounded-xl transition hover:bg-black/10 ${isDark ? 'text-white/44' : 'text-black/34'}`}
                                title="Copy command"
                              >
                                <Copy className="h-3.5 w-3.5" />
                              </button>
                            </div>
                          ))}
                        </div>
                      )}

                      {message.role === 'assistant' && message.actions?.length > 0 && (
                        <div className="mt-4 flex flex-wrap gap-2">
                          {message.actions.map((action) => (
                            <button
                              key={`${message.id}-${action.label}`}
                              type="button"
                              onClick={() => handleAction(action)}
                              className={`rounded-full border px-3 py-1.5 text-[11px] font-semibold transition ${ui.action}`}
                            >
                              {action.label}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                    {message.role === 'assistant' && message.meta && (
                      <p className={`mt-2 px-2 text-[10px] font-semibold uppercase tracking-[0.18em] ${ui.footerMeta}`}>
                        {message.meta}
                      </p>
                    )}
                  </div>
                ))}

                {isLoading && (
                  <div className="pr-6">
                    <div className={`rounded-[24px] px-4 py-4 ${ui.assistantBubble}`}>
                      <div className={`flex items-center gap-3 text-sm ${ui.muted}`}>
                        <Loader2 className="h-4 w-4 animate-spin text-[#79d9ab]" />
                        Assistant is thinking
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className={`border-t px-4 py-4 ${ui.line}`}>
                <form
                  onSubmit={(event) => {
                    event.preventDefault()
                    sendMessage(input)
                  }}
                  className="space-y-3"
                >
                  {!currentProviderReady && (
                    <div className={`rounded-[20px] border px-3 py-2 text-xs ${ui.keyWrap}`}>
                      Add an API key for {currentProvider?.label || 'this provider'} or switch to one already configured on the server.
                    </div>
                  )}

                  <div className={`rounded-[24px] p-3 ${ui.textareaWrap}`}>
                    <textarea
                      value={input}
                      onChange={(event) => setInput(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' && !event.shiftKey) {
                          event.preventDefault()
                          sendMessage(input)
                        }
                      }}
                      rows={3}
                      placeholder="Ask about alerts, policies, runtime status, or the next command to run."
                      className={`w-full resize-none bg-transparent text-sm leading-6 outline-none ${ui.textarea}`}
                    />
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <div className={`inline-flex min-w-0 items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] ${ui.footerMeta}`}>
                      <Sparkles className="h-3.5 w-3.5 shrink-0 text-[#79d9ab]" />
                      <span className="truncate">{latestAssistant?.meta || 'Workspace-aware assistant'}</span>
                    </div>
                    <button
                      type="submit"
                      disabled={!canSend || !currentProviderReady}
                      className={`inline-flex items-center gap-2 rounded-2xl px-4 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-45 ${ui.button}`}
                    >
                      <Send className="h-4 w-4" />
                      Send
                    </button>
                  </div>
                </form>
              </div>
            </motion.aside>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

export default OperatorAssistant
