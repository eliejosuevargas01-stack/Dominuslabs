import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

function mockBackend() {
  return {
    name: 'mock-backend',
    configureServer(server: any) {
      server.middlewares.use((req: any, res: any, next: any) => {
        if (req.url.startsWith('/api')) {
          res.setHeader('Content-Type', 'application/json');
          
          if (req.url.includes('/auth/login')) {
            res.end(JSON.stringify({
              access_token: 'mock-token',
              refresh_token: 'mock-refresh',
            }));
            return;
          }
          if (req.url.includes('/projects') && req.method === 'GET') {
            res.end(JSON.stringify([]));
            return;
          }
          if (req.url.includes('/company-settings')) {
            res.end(JSON.stringify({ tenant_id: 'default', company_name: 'Mock Company' }));
            return;
          }
          if (req.url.includes('/whatsapp/sessions')) {
            res.end(JSON.stringify([]));
            return;
          }
          if (req.url.includes('/crm/contacts')) {
            res.end(JSON.stringify([]));
            return;
          }
          if (req.url.includes('/crm/conversations')) {
            res.end(JSON.stringify([]));
            return;
          }
          if (req.url.includes('/products')) {
            res.end(JSON.stringify([]));
            return;
          }
          if (req.url.includes('/auth/refresh')) {
            res.end(JSON.stringify({ access_token: 'mock-token' }));
            return;
          }
          
          res.statusCode = 501;
          res.end(JSON.stringify({ error: 'Not yet migrated' }));
          return;
        }
        next();
      });
    }
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss(), mockBackend()],
  test: {
    environment: 'jsdom',
    globals: true,
    exclude: ['**/node_modules/**', '**/dist/**', '**/test-integration/**'],
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    allowedHosts: 'all',
  }
} as any)
// verified-isolated-workspace
