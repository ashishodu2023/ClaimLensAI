import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],

  server: {
    port: 3000,
    proxy: {
      '/api':     { target: 'http://localhost:8000', changeOrigin: true },
      '/health':  { target: 'http://localhost:8000', changeOrigin: true },
      '/metrics': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },

  build: {
    outDir: 'dist',
    sourcemap: false,        // disable in prod for smaller bundle
    minify: 'esbuild',       // fastest minifier
    target: 'es2022',        // modern browsers — smaller output
    chunkSizeWarningLimit: 1000,

    rollupOptions: {
      output: {
        // Manual chunks: keep vendor code separate for aggressive CDN caching
        manualChunks: {
          'react-vendor':   ['react', 'react-dom', 'react-router-dom'],
          'ui-vendor':      ['lucide-react', 'react-hot-toast', 'react-dropzone'],
          'mermaid-vendor': ['mermaid'],
        },
        // Stable filenames so CDN cache stays warm across deploys
        entryFileNames:   'assets/[name].[hash].js',
        chunkFileNames:   'assets/[name].[hash].js',
        assetFileNames:   'assets/[name].[hash][extname]',
      },
    },
  },

  // Optimise deps pre-bundling — avoids re-bundling on every cold start
  optimizeDeps: {
    include: ['react', 'react-dom', 'axios', 'lucide-react', 'react-dropzone'],
    exclude: ['mermaid'], // large — lazy-load at runtime instead
  },
})
