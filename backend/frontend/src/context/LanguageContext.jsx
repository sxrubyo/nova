import React, { createContext, useContext, useState, useEffect } from 'react'

const translations = {
  en: {
    // Sidebar
    dashboard: 'Dashboard',
    ledger: 'Ledger',
    agents: 'Agents',
    skills: 'Skills & MCPs',
    settings: 'Settings',
    
    // Header
    search_placeholder: 'Search agents, nodes, skills...',
    network_status: 'Network Operational',
    sync_node: 'Sync Node',
    
    // Dashboard Page
    operational_overview: 'Operational Overview',
    initialize_node: 'Initialize Node',
    total_actions: 'Total Actions',
    security_blocks: 'Security Blocks',
    active_nodes: 'Active Nodes',
    sync_latency: 'Sync Latency',
    recent_activity: 'Recent Activity',
    system_health: 'System Health',
    
    // Agents Page
    autonomous_agents: 'Autonomous Agents',
    manage_agents_desc: 'Manage and monitor live agent entities across your infrastructure.',
    register_agent: 'Register Agent',
    compliance: 'Compliance',
    avg_fidelity: 'Avg Fidelity',
    anomalies: 'Anomalies',
    agent_identity: 'Agent Identity',
    version: 'Version',
    operational_status: 'Operational Status',
    intent_volume: 'Intent Volume',
    management: 'Management',

    // Create Agent Modal
    initialize_agent: 'Initialize New Agent',
    deployment_step: 'Deployment Step',
    agent_identifier: 'Agent Identifier',
    operational_purpose: 'Operational Purpose',
    neural_backbone: 'Neural Backbone Model',
    configure_model: 'Configure Model',
    deploy_protocol: 'Deploy Protocol',
    deploying: 'Deploying...',
    back: 'Back',

  },
  es: {
    // Sidebar
    dashboard: 'Panel Control',
    ledger: 'Registros',
    agents: 'Agentes',
    skills: 'Habilidades',
    settings: 'Configuración',

    // Header
    search_placeholder: 'Buscar agentes, nodos, skills...',
    network_status: 'Red Operacional',
    sync_node: 'Sincronizar Nodo',

    // Dashboard Page
    operational_overview: 'Vista Operacional',
    initialize_node: 'Inicializar Nodo',
    total_actions: 'Acciones Totales',
    security_blocks: 'Bloqueos de Seguridad',
    active_nodes: 'Nodos Activos',
    sync_latency: 'Latencia de Sinc.',
    recent_activity: 'Actividad Reciente',
    system_health: 'Salud del Sistema',
    
    // Agents Page
    autonomous_agents: 'Agentes Autónomos',
    manage_agents_desc: 'Administra y monitorea entidades de agentes en tu infraestructura.',
    register_agent: 'Registrar Agente',
    compliance: 'Cumplimiento',
    avg_fidelity: 'Fidelidad Promedio',
    anomalies: 'Anomalías',
    agent_identity: 'Identidad del Agente',
    version: 'Versión',
    operational_status: 'Estado Operacional',
    intent_volume: 'Volumen de Intenciones',
    management: 'Gestión',

    // Create Agent Modal
    initialize_agent: 'Inicializar Nuevo Agente',
    deployment_step: 'Paso de Despliegue',
    agent_identifier: 'Identificador del Agente',
    operational_purpose: 'Propósito Operacional',
    neural_backbone: 'Modelo de Red Neuronal',
    configure_model: 'Configurar Modelo',
    deploy_protocol: 'Desplegar Protocolo',
    deploying: 'Desplegando...',
    back: 'Atrás',
  }
}

const LanguageContext = createContext()

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(localStorage.getItem('nova_lang') || 'en')

  useEffect(() => {
    localStorage.setItem('nova_lang', lang)
  }, [lang])

  const t = (key) => {
    return translations[lang]?.[key] || translations['en'][key] || key
  }

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  )
}

export const useLanguage = () => useContext(LanguageContext)
