import axios from 'axios';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8080',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth interceptor
client.interceptors.request.use((config) => {
  let apiKey = localStorage.getItem('apiKey');
  
  // If no API key is set, use default development key
  if (!apiKey && import.meta.env.DEV) {
    apiKey = 'dev-key-123';
    localStorage.setItem('apiKey', apiKey);
    console.log('Using default development API key: dev-key-123');
  }
  
  if (apiKey) {
    // SetuPranali uses X-API-Key header, not Authorization Bearer
    config.headers['X-API-Key'] = apiKey;
  }
  return config;
});

export const api = {
  // Health
  getHealth: async () => {
    const { data } = await client.get('/v1/health');
    return data;
  },

  // Datasets
  getDatasets: async () => {
    const { data } = await client.get('/v1/datasets');
    return data;
  },

  getDataset: async (id: string) => {
    const { data } = await client.get(`/v1/datasets/${id}`);
    return data;
  },

  // Sources
  getSources: async () => {
    const { data } = await client.get('/v1/sources');
    return data;
  },

  // API Keys
  getApiKeys: async () => {
    const { data } = await client.get('/v1/api-keys');
    return data;
  },

  createApiKey: async (keyData: { name: string; tenant: string; role: string }) => {
    const { data } = await client.post('/v1/api-keys', keyData);
    return data;
  },

  deleteApiKey: async (keyId: string) => {
    await client.delete(`/v1/api-keys/${keyId}`);
  },

  createSource: async (source: any) => {
    const { data } = await client.post('/v1/sources', source);
    return data;
  },

  testSource: async (source: any) => {
    const { data } = await client.post('/v1/sources/test', source);
    return data;
  },

  // Query
  query: async (request: any) => {
    const { data } = await client.post('/v1/query', request);
    return data;
  },

  // SQL
  sql: async (query: string) => {
    const { data } = await client.post('/v1/sql', { query });
    return data;
  },

  // NLQ
  nlq: async (question: string, dataset?: string) => {
    const { data } = await client.post('/v1/nlq', { question, dataset });
    return data;
  },

  // GraphQL
  graphql: async (query: string, variables?: Record<string, any>) => {
    const { data } = await client.post('/v1/graphql', { query, variables });
    return data;
  },

  // Introspection
  introspect: async () => {
    const { data } = await client.get('/v1/introspection/datasets');
    return data;
  },

  // Cache
  getCacheStats: async () => {
    const { data } = await client.get('/v1/advanced/cache/stats');
    return data;
  },

  invalidateCache: async (dataset?: string) => {
    const { data } = await client.post('/v1/advanced/cache/invalidate', { dataset });
    return data;
  },

  // Analytics
  getAnalytics: async (hours: number = 24) => {
    const { data } = await client.get(`/v1/analytics?hours=${hours}`);
    return data;
  },

  // Recent Queries
  getRecentQueries: async (limit: number = 10, dataset?: string) => {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (dataset) params.append('dataset', dataset);
    const { data } = await client.get(`/v1/analytics/recent-queries?${params}`);
    return data;
  },

  // Catalog validation
  validateCatalog: async (catalog: any) => {
    const { data } = await client.post('/v1/catalog/validate', catalog);
    return data;
  },
};

