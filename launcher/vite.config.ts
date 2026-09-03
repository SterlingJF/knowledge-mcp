// File: launcher/vite.config.ts
/// <reference types="vitest/config" />

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import tailwindcss from '@tailwindcss/vite'
import viteReact from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

/** Fixed dev port named by shell CSP (tauri.conf.json). */
const DEV_SERVER_PORT = 1420

const APP_VERSION = JSON.parse(
  readFileSync(resolve(__dirname, 'package.json'), 'utf8'),
).version as string

export default defineConfig({
  define: {
    __KM_VERSION__: JSON.stringify(APP_VERSION),
  },

  plugins: [viteReact(), tailwindcss()],

  // Shell diagnostics share this terminal.
  clearScreen: false,

  server: {
    port: DEV_SERVER_PORT,
    strictPort: true,
  },

  build: {
    // Production window is a system WebKit view.
    target: 'safari13',
    sourcemap: true,
  },

  test: {
    globals: true,
    environment: 'jsdom',
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
  },

  resolve: {
    alias: [{ find: '@', replacement: resolve(__dirname, './src') }],
  },
})
