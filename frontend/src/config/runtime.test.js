import { describe, expect, it } from 'vitest'

import {
  buildApiBaseUrl,
  getApiProxyTarget,
  buildWebSocketUrl,
  getRuntimeMode,
  getUiPort,
} from './runtime'

describe('runtime config', () => {
  it('defaults to standalone mode when no mode is provided', () => {
    expect(getRuntimeMode(undefined)).toBe('standalone')
  })

  it('uses relative api path in integration mode', () => {
    expect(buildApiBaseUrl({ mode: 'integration' })).toBe('')
  })

  it('uses explicit standalone api base url when provided', () => {
    expect(
      buildApiBaseUrl({
        mode: 'standalone',
        apiBaseUrl: 'http://127.0.0.1:8000',
      }),
    ).toBe('http://127.0.0.1:8000')
  })

  it('uses same-origin api path in standalone mode by default', () => {
    expect(buildApiBaseUrl({ mode: 'standalone' })).toBe('')
  })

  it('builds websocket url from current host in integration mode', () => {
    expect(
      buildWebSocketUrl({
        mode: 'integration',
        protocol: 'http:',
        host: '127.0.0.1:6101',
      }),
    ).toBe('ws://127.0.0.1:6101/ws/api/agents/ws')
  })

  it('builds websocket url from current host in standalone mode by default', () => {
    expect(
      buildWebSocketUrl({
        mode: 'standalone',
        protocol: 'http:',
        host: '127.0.0.2:3000',
      }),
    ).toBe('ws://127.0.0.2:3000/ws/api/agents/ws')
  })

  it('uses standalone ports by default', () => {
    expect(getUiPort(undefined)).toBe(3000)
    expect(getApiProxyTarget(undefined)).toBe('http://127.0.0.1:8000')
  })

  it('uses integration ports in integration mode', () => {
    expect(getUiPort('integration')).toBe(6101)
    expect(getApiProxyTarget('integration')).toBe('http://127.0.0.1:6102')
  })
})
