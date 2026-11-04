import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { getApiProxyTarget, getRuntimeMode, getUiPort, getWsProxyTarget } from './src/config/runtime.js'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const runtimeMode = getRuntimeMode(env.VITE_APP_RUNTIME_MODE)
  const serverPort = Number(env.VITE_UI_PORT || getUiPort(runtimeMode))
  const apiTarget = env.VITE_API_PROXY_TARGET || getApiProxyTarget(runtimeMode)
  const wsTarget = env.VITE_WS_PROXY_TARGET || getWsProxyTarget(runtimeMode)

  return {
    plugins: [react()],
    server: {
      port: serverPort,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/ws': {
          target: wsTarget,
          ws: true,
          rewrite: path => path.replace(/^\/ws/, ''),
        },
      },
    },
  }
})
