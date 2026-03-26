# Nova OS Frontend

Dashboard enterprise para Nova OS - Sistema de Gobernanza para Agentes de IA

## Stack Tecnológico

- **React 19** con Vite
- **TailwindCSS** para estilos
- **React Router** para navegación

## Desarrollo

```bash
# Instalar dependencias
npm install

# Iniciar servidor de desarrollo
npm run dev

# Build para producción
npm run build

# Preview del build
npm run preview
```

## Estructura

```
src/
├── components/     # Componentes reutilizables
├── pages/          # Vistas principales
│   ├── Dashboard   # Métricas en tiempo real
│   ├── Ledger      # Historial de validaciones
│   ├── Agents      # Gestión de agentes
│   ├── Skills      # Integraciones
│   └── Settings    # Configuración
├── hooks/          # Custom hooks
├── utils/          # Utilidades
└── styles/         # Estilos globales
```

## Endpoints API

El frontend se conecta al backend en `http://localhost:8000`:

- `GET /api/ledger` - Obtener historial de validaciones
- `GET /api/agents` - Listar agentes activos
- `POST /api/validate` - Validar acción
- `GET /api/metrics` - Métricas del sistema
- `GET /api/skills` - Integraciones disponibles

## Producción

El build genera archivos estáticos en `dist/` que son servidos por Nginx en el puerto 3005.
