/**
 * @setupranali/looker-studio
 * 
 * Looker Studio (Google Data Studio) connector for SetuPranali semantic layer.
 * 
 * This package provides:
 * 1. Google Apps Script code for the Looker Studio connector
 * 2. TypeScript utilities for building custom connectors
 * 3. Schema generation helpers
 * 
 * @example
 * ```typescript
 * import { SetuPranaliConnector, createSchema } from '@setupranali/looker-studio';
 * 
 * const connector = new SetuPranaliConnector({
 *   url: 'https://your-server.com',
 *   apiKey: 'your-api-key'
 * });
 * 
 * const schema = await connector.getSchema('orders');
 * const data = await connector.getData('orders', ['region'], ['revenue']);
 * ```
 */

export interface ConnectorConfig {
  /** SetuPranali server URL */
  url: string;
  /** API key for authentication */
  apiKey: string;
  /** Request timeout in milliseconds (default: 30000) */
  timeout?: number;
}

export interface SchemaField {
  name: string;
  label: string;
  dataType: 'STRING' | 'NUMBER' | 'BOOLEAN' | 'DATE' | 'DATETIME';
  semantics?: {
    conceptType: 'DIMENSION' | 'METRIC';
    semanticType?: string;
    semanticGroup?: string;
  };
  description?: string;
  isDefault?: boolean;
}

export interface QueryRequest {
  dataset: string;
  dimensions: string[];
  metrics: string[];
  filters?: QueryFilter[];
  limit?: number;
}

export interface QueryFilter {
  dimension: string;
  operator: 'eq' | 'neq' | 'gt' | 'gte' | 'lt' | 'lte' | 'in' | 'contains';
  value: string | number | string[];
}

export interface QueryResponse {
  columns: string[];
  rows: Record<string, any>[];
  metadata?: {
    executionTime?: number;
    rowCount?: number;
  };
}

export interface DatasetInfo {
  id: string;
  name: string;
  description?: string;
  dimensions: Array<{
    name: string;
    type: string;
    description?: string;
  }>;
  metrics: Array<{
    name: string;
    type: string;
    description?: string;
  }>;
}

/**
 * SetuPranali Connector for Looker Studio
 */
export class SetuPranaliConnector {
  private config: Required<ConnectorConfig>;

  constructor(config: ConnectorConfig) {
    this.config = {
      url: config.url.replace(/\/$/, ''),
      apiKey: config.apiKey,
      timeout: config.timeout ?? 30000,
    };
  }

  /**
   * Test connection to SetuPranali server
   */
  async testConnection(): Promise<boolean> {
    try {
      const response = await this.fetch('/v1/health');
      return response.status === 'healthy';
    } catch {
      return false;
    }
  }

  /**
   * Get list of available datasets
   */
  async getDatasets(): Promise<DatasetInfo[]> {
    const response = await this.fetch('/v1/introspection/datasets');
    return response.items || [];
  }

  /**
   * Get dataset details including dimensions and metrics
   */
  async getDatasetInfo(datasetId: string): Promise<DatasetInfo> {
    return this.fetch(`/v1/introspection/datasets/${datasetId}`);
  }

  /**
   * Get Looker Studio schema for a dataset
   */
  async getSchema(datasetId: string): Promise<SchemaField[]> {
    const dataset = await this.getDatasetInfo(datasetId);
    return this.datasetToSchema(dataset);
  }

  /**
   * Convert dataset info to Looker Studio schema
   */
  datasetToSchema(dataset: DatasetInfo): SchemaField[] {
    const fields: SchemaField[] = [];

    // Add dimensions
    for (const dim of dataset.dimensions || []) {
      fields.push({
        name: dim.name,
        label: this.formatLabel(dim.name),
        dataType: this.mapDataType(dim.type),
        semantics: {
          conceptType: 'DIMENSION',
        },
        description: dim.description,
      });
    }

    // Add metrics
    for (const metric of dataset.metrics || []) {
      fields.push({
        name: metric.name,
        label: this.formatLabel(metric.name),
        dataType: 'NUMBER',
        semantics: {
          conceptType: 'METRIC',
        },
        description: metric.description,
      });
    }

    return fields;
  }

  /**
   * Query data from SetuPranali
   */
  async getData(request: QueryRequest): Promise<QueryResponse> {
    return this.fetch('/v1/query', {
      method: 'POST',
      body: JSON.stringify({
        dataset: request.dataset,
        dimensions: request.dimensions,
        metrics: request.metrics,
        filters: request.filters || [],
        limit: request.limit || 10000,
      }),
    });
  }

  /**
   * Execute SQL query
   */
  async executeSql(sql: string, dataset: string): Promise<QueryResponse> {
    return this.fetch('/v1/sql', {
      method: 'POST',
      body: JSON.stringify({ sql, dataset }),
    });
  }

  /**
   * Format data for Looker Studio response
   */
  formatForLookerStudio(
    response: QueryResponse,
    schema: SchemaField[]
  ): any[][] {
    const rows: any[][] = [];
    const fieldNames = schema.map((f) => f.name);

    for (const row of response.rows) {
      const values: any[] = [];
      for (const fieldName of fieldNames) {
        let value = row[fieldName];
        
        // Convert null/undefined to empty
        if (value === null || value === undefined) {
          value = '';
        }
        
        values.push(value);
      }
      rows.push(values);
    }

    return rows;
  }

  /**
   * Map SetuPranali type to Looker Studio data type
   */
  private mapDataType(type: string): SchemaField['dataType'] {
    const typeMap: Record<string, SchemaField['dataType']> = {
      string: 'STRING',
      varchar: 'STRING',
      text: 'STRING',
      number: 'NUMBER',
      integer: 'NUMBER',
      int: 'NUMBER',
      bigint: 'NUMBER',
      float: 'NUMBER',
      double: 'NUMBER',
      decimal: 'NUMBER',
      numeric: 'NUMBER',
      boolean: 'BOOLEAN',
      bool: 'BOOLEAN',
      date: 'DATE',
      timestamp: 'DATETIME',
      datetime: 'DATETIME',
    };

    return typeMap[type.toLowerCase()] || 'STRING';
  }

  /**
   * Format field name as human-readable label
   */
  private formatLabel(name: string): string {
    return name
      .replace(/_/g, ' ')
      .replace(/([A-Z])/g, ' $1')
      .trim()
      .split(' ')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  }

  /**
   * Fetch from SetuPranali API
   */
  private async fetch(endpoint: string, options: RequestInit = {}): Promise<any> {
    const url = `${this.config.url}${endpoint}`;
    
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.config.apiKey,
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`SetuPranali API error: ${response.status} ${error}`);
    }

    return response.json();
  }
}

/**
 * Create a Looker Studio schema field
 */
export function createSchemaField(
  name: string,
  options: Partial<SchemaField> = {}
): SchemaField {
  return {
    name,
    label: options.label || name,
    dataType: options.dataType || 'STRING',
    semantics: options.semantics || { conceptType: 'DIMENSION' },
    description: options.description,
    isDefault: options.isDefault,
  };
}

/**
 * Create a dimension field
 */
export function createDimension(
  name: string,
  dataType: SchemaField['dataType'] = 'STRING',
  options: Partial<SchemaField> = {}
): SchemaField {
  return createSchemaField(name, {
    ...options,
    dataType,
    semantics: { conceptType: 'DIMENSION' },
  });
}

/**
 * Create a metric field
 */
export function createMetric(
  name: string,
  options: Partial<SchemaField> = {}
): SchemaField {
  return createSchemaField(name, {
    ...options,
    dataType: 'NUMBER',
    semantics: { conceptType: 'METRIC' },
  });
}

// Export types
export type { ConnectorConfig, SchemaField, QueryRequest, QueryFilter, QueryResponse, DatasetInfo };

