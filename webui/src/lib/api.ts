import axios from 'axios';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8080',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth interceptor
client.interceptors.request.use((config) => {
  const apiKey = localStorage.getItem('apiKey');
  if (apiKey) {
    config.headers.Authorization = `Bearer ${apiKey}`;
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
  getAnalytics: async () => {
    const { data } = await client.get('/v1/analytics');
    return data;
  },

  // Catalog validation
  validateCatalog: async (catalog: any) => {
    const { data } = await client.post('/v1/catalog/validate', catalog);
    return data;
  },
};

