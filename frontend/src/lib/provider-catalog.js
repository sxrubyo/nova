export const providerCatalog = [
  {
    key: 'openrouter',
    label: 'OpenRouter',
    logo: '/llm-brands/openrouter.svg',
    accent: '#94A3B8',
    description: 'Route across premium and preview frontier models with one key.',
    defaultModel: 'openai/gpt-4o-mini',
    models: [
      { id: 'openai/gpt-4o-mini', label: 'GPT-4o mini', family: 'GPT', status: 'default' },
      { id: 'openai/gpt-4o', label: 'GPT-4o', family: 'GPT', status: 'stable' },
      { id: 'openai/o3', label: 'o3', family: 'Reasoning', status: 'reasoning' },
      { id: 'anthropic/claude-sonnet-4', label: 'Claude Sonnet 4', family: 'Claude', status: 'recommended' },
      { id: 'anthropic/claude-opus-4.1', label: 'Claude Opus 4.1', family: 'Claude', status: 'premium' },
      { id: 'google/gemini-2.5-pro', label: 'Gemini 2.5 Pro', family: 'Gemini', status: 'stable' },
      { id: 'x-ai/grok-4.1-fast', label: 'Grok 4.1 Fast', family: 'Grok', status: 'fast' },
      { id: 'openrouter/auto', label: 'Auto Router', family: 'Router', status: 'adaptive' },
    ],
  },
  {
    key: 'anthropic',
    label: 'Anthropic',
    logo: '/llm-brands/anthropic.svg',
    accent: '#D4A373',
    description: 'Direct Claude access for high-quality reasoning and writing.',
    defaultModel: 'claude-sonnet-4-20250514',
    models: [
      { id: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 4', family: 'Claude', status: 'default' },
      { id: 'claude-opus-4-1-20250805', label: 'Claude Opus 4.1', family: 'Claude', status: 'premium' },
      { id: 'claude-3-5-haiku-latest', label: 'Claude Haiku 3.5', family: 'Claude', status: 'fast' },
    ],
  },
  {
    key: 'gemini',
    label: 'Google Gemini',
    logo: '/llm-brands/gemini.svg',
    accent: '#8E75B2',
    description: 'Direct Gemini access for long context and fast operator help.',
    defaultModel: 'gemini-2.0-flash',
    models: [
      { id: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash', family: 'Gemini', status: 'default' },
      { id: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro', family: 'Gemini', status: 'stable' },
      { id: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash', family: 'Gemini', status: 'fast' },
    ],
  },
  {
    key: 'openai',
    label: 'OpenAI',
    logo: '/llm-brands/openai.svg',
    accent: '#101010',
    description: 'Direct GPT and o-series access for operator workflows.',
    defaultModel: 'gpt-4o-mini',
    models: [
      { id: 'gpt-4o-mini', label: 'GPT-4o mini', family: 'GPT', status: 'default' },
      { id: 'gpt-4o', label: 'GPT-4o', family: 'GPT', status: 'stable' },
      { id: 'o3', label: 'o3', family: 'Reasoning', status: 'reasoning' },
    ],
  },
  {
    key: 'groq',
    label: 'Groq',
    logo: '/llm-brands/groq.svg',
    accent: '#F43E01',
    description: 'Ultra-fast inference for operator chats and short reasoning loops.',
    defaultModel: 'llama-3.3-70b-versatile',
    models: [
      { id: 'llama-3.3-70b-versatile', label: 'Llama 3.3 70B Versatile', family: 'Llama', status: 'default' },
      { id: 'llama-3.1-8b-instant', label: 'Llama 3.1 8B Instant', family: 'Llama', status: 'economy' },
      { id: 'openai/gpt-oss-120b', label: 'GPT-OSS 120B', family: 'Open', status: 'open' },
    ],
  },
  {
    key: 'xai',
    label: 'xAI',
    logo: '/llm-brands/xai.svg',
    accent: '#111111',
    description: 'Direct Grok access for fast conversational analysis.',
    defaultModel: 'grok-3',
    models: [
      { id: 'grok-3', label: 'Grok 3', family: 'Grok', status: 'default' },
      { id: 'grok-3-mini', label: 'Grok 3 Mini', family: 'Grok', status: 'fast' },
      { id: 'grok-4', label: 'Grok 4', family: 'Grok', status: 'premium' },
    ],
  },
  {
    key: 'mistral',
    label: 'Mistral',
    logo: '/llm-brands/mistral.svg',
    accent: '#FA520F',
    description: 'Direct Mistral access for compact multilingual assistance.',
    defaultModel: 'mistral-small-latest',
    models: [
      { id: 'mistral-small-latest', label: 'Mistral Small', family: 'Mistral', status: 'default' },
      { id: 'mistral-medium-latest', label: 'Mistral Medium', family: 'Mistral', status: 'premium' },
      { id: 'ministral-8b-latest', label: 'Ministral 8B', family: 'Mistral', status: 'fast' },
    ],
  },
  {
    key: 'deepseek',
    label: 'DeepSeek',
    logo: '/llm-brands/deepseek.svg',
    accent: '#4A90E2',
    description: 'Reasoning-heavy DeepSeek models for low-cost analysis.',
    defaultModel: 'deepseek-chat',
    models: [
      { id: 'deepseek-chat', label: 'DeepSeek Chat', family: 'DeepSeek', status: 'default' },
      { id: 'deepseek-reasoner', label: 'DeepSeek Reasoner', family: 'Reasoning', status: 'reasoning' },
    ],
  },
  {
    key: 'cohere',
    label: 'Cohere',
    logo: '/llm-brands/cohere.svg',
    accent: '#355146',
    description: 'Command-family models for retrieval and concise operator help.',
    defaultModel: 'command-r-plus-08-2024',
    models: [
      { id: 'command-r-plus-08-2024', label: 'Command R+', family: 'Command', status: 'default' },
      { id: 'command-r-08-2024', label: 'Command R', family: 'Command', status: 'fast' },
      { id: 'command-a-03-2025', label: 'Command A', family: 'Command', status: 'premium' },
    ],
  },
]

export function getProviderMeta(value) {
  const normalized = String(value || '')
    .toLowerCase()
    .replace(/\s+/g, '')
    .replace(/googlegemini/g, 'gemini')

  return (
    providerCatalog.find((provider) => provider.key === normalized) ||
    providerCatalog.find((provider) => provider.label.toLowerCase().replace(/\s+/g, '') === normalized) ||
    null
  )
}
