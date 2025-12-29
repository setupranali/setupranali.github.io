/**
 * SetuPranali SDK Types
 */

export interface Dimension {
  name: string;
  label?: string;
  type?: string;
  description?: string;
}

export interface Metric {
  name: string;
  label?: string;
  type?: string;
  sql?: string;
  description?: string;
}

export interface Dataset {
  id: string;
  name: string;
  description?: string;
  source?: string;
  tags: string[];
  dimensions: Dimension[];
  metrics: Metric[];
  defaultTimezone?: string;
}

export interface DatasetSummary {
  id: string;
  name: string;
  description?: string;
  tags: string[];
}

export interface Column {
  name: string;
  type: string;
}

export interface QueryResult<T = Record<string, unknown>> {
  columns: Column[];
  data: T[];
  rowCount: number;
  cached: boolean;
  executionTimeMs?: number;
  queryId?: string;
}

export interface HealthStatus {
  status: string;
  version: string;
  time: string;
  cache: {
    enabled: boolean;
    redis_available: boolean;
    cached_queries?: number;
  };
}

export interface Filter {
  field: string;
  operator: 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte' | 'in' | 'between' | 'like';
  value: unknown;
}

export interface OrderBy {
  field: string;
  direction?: 'asc' | 'desc';
}

export interface QueryOptions {
  dataset: string;
  dimensions?: string[];
  metrics?: string[];
  filters?: Filter[];
  orderBy?: OrderBy[];
  limit?: number;
  offset?: number;
}

export interface ClientConfig {
  url: string;
  apiKey?: string;
  timeout?: number;
  headers?: Record<string, string>;
}

export interface GraphQLResponse<T = unknown> {
  data?: T;
  errors?: Array<{
    message: string;
    locations?: Array<{ line: number; column: number }>;
    path?: string[];
  }>;
}

