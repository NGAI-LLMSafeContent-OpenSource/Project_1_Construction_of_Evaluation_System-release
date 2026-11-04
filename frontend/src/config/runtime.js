const STANDALONE_MODE = 'standalone'
const INTEGRATION_MODE = 'integration'

export function getRuntimeMode(mode) {
  return mode === INTEGRATION_MODE ? INTEGRATION_MODE : STANDALONE_MODE
}

export function getUiPort(mode) {
  return getRuntimeMode(mode) === INTEGRATION_MODE ? 6101 : 3000
}

export function getApiProxyTarget(mode) {
  return getRuntimeMode(mode) === INTEGRATION_MODE
    ? 'http://127.0.0.1:6102'
    : 'http://127.0.0.1:8000'
}

export function getWsProxyTarget(mode) {
  return getRuntimeMode(mode) === INTEGRATION_MODE
    ? 'ws://127.0.0.1:6102'
    : 'ws://127.0.0.1:8000'
}

export function buildApiBaseUrl({ mode, apiBaseUrl } = {}) {
  if (apiBaseUrl) {
    return apiBaseUrl
  }
  return ''
}

export function buildWebSocketUrl({ mode, protocol, host, wsBaseUrl } = {}) {
  if (wsBaseUrl) {
    return `${wsBaseUrl.replace(/\/$/, '')}/api/agents/ws`
  }

  const wsProtocol = protocol === 'https:' ? 'wss:' : 'ws:'
  const runtimeMode = getRuntimeMode(mode)

  if (host) {
    return `${wsProtocol}//${host}/ws/api/agents/ws`
  }

  const fallbackTarget = getWsProxyTarget(runtimeMode).replace(/^ws/, wsProtocol.replace(':', ''))
  return `${fallbackTarget}/api/agents/ws`
}

export function getRuntimeConfig(env = import.meta.env, location = window.location) {
  const mode = getRuntimeMode(env.VITE_APP_RUNTIME_MODE)
  return {
    mode,
    apiBaseUrl: buildApiBaseUrl({
      mode,
      apiBaseUrl: env.VITE_API_BASE_URL,
    }),
    webSocketUrl: buildWebSocketUrl({
      mode,
      protocol: location?.protocol,
      host: location?.host,
      wsBaseUrl: env.VITE_WS_BASE_URL,
    }),
  }
}
