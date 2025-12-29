import { DataQuery, DataSourceJsonData } from '@grafana/data';

/**
 * SetuPranali Query interface
 */
export interface SetuPranaliQuery extends DataQuery {
  // Dataset to query
  dataset: string;
  
  // Dimensions to group by
  dimensions: string[];
  
  // Metrics to aggregate
  metrics: string[];
  
  // Filters to apply
  filters?: QueryFilter[];
  
  // Time dimension for time series
  timeDimension?: string;
  
  // Time granularity (hour, day, week, month)
  timeGranularity?: string;
  
  // Result limit
  limit?: number;
  
  // Order by
  orderBy?: OrderBy[];
  
  // Raw SQL mode
  rawSql?: string;
  
  // Query type
  queryType: 'semantic' | 'sql';
}

export interface QueryFilter {
  dimension: string;
  operator: 'eq' | 'neq' | 'gt' | 'gte' | 'lt' | 'lte' | 'in' | 'contains';
  value: string | number | string[];
}

export interface OrderBy {
  field: string;
  direction: 'asc' | 'desc';
}

/**
 * Default query values
 */
export const defaultQuery: Partial<SetuPranaliQuery> = {
  dataset: '',
  dimensions: [],
  metrics: [],
  filters: [],
  queryType: 'semantic',
  limit: 1000,
};

/**
 * Data source configuration options
 */
export interface SetuPranaliOptions extends DataSourceJsonData {
  // SetuPranali server URL
  url?: string;
  
  // Default dataset
  defaultDataset?: string;
  
  // Enable caching
  cacheEnabled?: boolean;
  
  // Cache TTL in seconds
  cacheTTL?: number;
}

/**
 * Secure configuration (stored encrypted)
 */
export interface SetuPranaliSecureOptions {
  // API Key for authentication
  apiKey?: string;
}

/**
 * Dataset metadata
 */
export interface Dataset {
  id: string;
  name: string;
  description?: string;
  dimensions: Dimension[];
  metrics: Metric[];
}

export interface Dimension {
  name: string;
  type: 'string' | 'number' | 'date' | 'timestamp' | 'boolean';
  description?: string;
}

export interface Metric {
  name: string;
  type: 'number';
  description?: string;
  aggregation?: string;
}

/**
 * Query response
 */
export interface QueryResponse {
  columns: string[];
  rows: Record<string, any>[];
  metadata?: {
    executionTime?: number;
    rowCount?: number;
  };
}

