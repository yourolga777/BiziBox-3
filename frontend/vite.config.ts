/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      selfDestroying: false,
      devOptions: { enabled: false },
      includeAssets: ['favicon.ico', 'icons/*.png', 'apple-touch-icon.png'],
      manifest: {
        name: 'BiziBox',
        short_name: 'BiziBox',
        description: 'BiziBox - messages and tasks in one window',
        theme_color: '#6366f1',
        background_color: '#ffffff',
        display: 'standalone',
        icons: [
          {
            src: '/icons/icon-192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: '/icons/icon-512.png',
            sizes: '512x512',
            type: 'image/png',
          },
        ],
      },
      workbox: {
        // Не кэшируем /api и не делаем navigateFallback: в десктоп-сборке это
        // ломает API-запросы (SW отдаёт index.html/пустоту вместо JSON).
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2,json}'],
        navigateFallbackDenylist: [/\/api\//],
        runtimeCaching: [
          {
            urlPattern: /\.(?:js|css|html|json|ico|svg|png|jpg|jpeg|webp|woff2?)$/,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'static-assets',
              expiration: { maxEntries: 200, maxAgeSeconds: 60 * 60 * 24 * 30 },
            },
          },
        ],
      },
    }),
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom', 'react-router-dom'],
          tanstack: ['@tanstack/react-query', '@tanstack/react-query-persist-client', '@tanstack/query-sync-storage-persister', '@tanstack/react-query-devtools'],
        },
      },
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:7910',
        changeOrigin: true,
      },
    },
  },
})
