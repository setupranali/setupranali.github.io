# SetuPranali Web UI

Admin dashboard for SetuPranali - the semantic layer for BI tools.

## Features

- **Dashboard** - Overview of system status, queries, and metrics
- **Datasets** - Browse and manage semantic datasets
- **Data Sources** - Configure database connections
- **API Keys** - Manage authentication keys
- **Query Playground** - Test queries interactively
- **Catalog Editor** - Visual YAML catalog editor with validation
- **Analytics** - Query patterns and performance insights
- **Settings** - System configuration

## Getting Started

### Development

```bash
# Install dependencies
npm install

# Start dev server
npm run dev
```

Open http://localhost:5173

### Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

### Configuration

Set the API URL via environment variable:

```bash
VITE_API_URL=http://localhost:8080 npm run dev
```

Or create a `.env` file:

```env
VITE_API_URL=http://localhost:8080
```

## Technology Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **React Query** - Server state management
- **Zustand** - Client state management
- **Recharts** - Charts and visualizations
- **Monaco Editor** - Code editing
- **Lucide** - Icons

## Project Structure

```
src/
├── components/     # Reusable UI components
├── pages/          # Page components
├── lib/            # Utilities and API client
├── store/          # Zustand stores
├── hooks/          # Custom React hooks
├── types/          # TypeScript types
└── main.tsx        # Entry point
```

## Pages

| Page | Description |
|------|-------------|
| Dashboard | System overview and metrics |
| Datasets | List and manage datasets |
| Dataset Detail | Dataset dimensions, metrics, and sample queries |
| Sources | Database connection management |
| API Keys | Key management with permissions |
| Query Playground | Interactive query testing |
| Catalog Editor | Visual catalog.yaml editor |
| Analytics | Query analytics dashboard |
| Settings | System configuration |

## Deployment

### Docker

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

### Nginx Configuration

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://setupranali:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## License

Apache 2.0 - see [LICENSE](../LICENSE).

