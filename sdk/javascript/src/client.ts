/**
 * SetuPranali JavaScript/TypeScript Client
 */

import {
  ClientConfig,
  Dataset,
  DatasetSummary,
  QueryResult,
  QueryOptions,
  HealthStatus,
  GraphQLResponse,
} from './types';

import {
  SetuPranaliError,
  AuthenticationError,
  DatasetNotFoundError,
  QueryError,
  RateLimitError,
  ConnectionError,
} from './errors';

export class SetuPranali {
  private readonly url: string;
  private readonly apiKey?: string;
  private readonly timeout: number;
  private readonly headers: Record<string, string>;

  /**
   * Create a new SetuPranali client.
   *
   * @example
   * ```typescript
   * const client = new SetuPranali({
   *   url: 'http://localhost:8080',
   *   apiKey: 'your-api-key'
   * });
   * ```
   */
  constructor(config: ClientConfig) {
    this.url = config.url.replace(/\/$/, '');
    this.apiKey = config.apiKey;
    this.timeout = config.timeout ?? 30000;
    this.headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...config.headers,
    };

    if (this.apiKey) {
      this.headers['X-API-Key'] = this.apiKey;
    }
  }

  /**
   * Make an HTTP request to the API.
   */
  private async request<T>(
    method: 'GET' | 'POST',
    path: string,
    body?: unknown
  ): Promise<T> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(`${this.url}${path}`, {
        method,
        headers: this.headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      return await this.handleResponse<T>(response);
    } catch (error) {
      clearTimeout(timeoutId);
      
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new SetuPranaliError(`Request timed out after ${this.timeout}ms`);
        }
        if (error.message.includes('fetch')) {
          throw new ConnectionError(`Failed to connect to ${this.url}: ${error.message}`);
        }
      }
      throw error;
    }
  }

  /**
   * Handle HTTP response and throw appropriate errors.
   */
  private async handleResponse<T>(response: Response): Promise<T> {
    if (response.ok) {
      return response.json();
    }

    let message: string;
    try {
      const errorData = await response.json();
      message = errorData.detail || JSON.stringify(errorData);
    } catch {
      message = response.statusText || `HTTP ${response.status}`;
    }

    switch (response.status) {
      case 401:
      case 403:
        throw new AuthenticationError(message);
      case 404:
        throw new DatasetNotFoundError();
      case 400:
        throw new QueryError(message);
      case 429:
        const retryAfter = response.headers.get('Retry-After');
        throw new RateLimitError(message, retryAfter ? parseInt(retryAfter) : undefined);
      default:
        throw new SetuPranaliError(message, response.status);
    }
  }

  // ===========================================================================
  // API Methods
  // ===========================================================================

  /**
   * Check server health.
   *
   * @example
   * ```typescript
   * const health = await client.health();
   * console.log(health.status); // 'ok'
   * ```
   */
  async health(): Promise<HealthStatus> {
    return this.request<HealthStatus>('GET', '/v1/health');
  }

  /**
   * List all available datasets.
   *
   * @example
   * ```typescript
   * const datasets = await client.datasets();
   * datasets.forEach(ds => console.log(ds.name));
   * ```
   */
  async datasets(): Promise<DatasetSummary[]> {
    const response = await this.request<{ items: DatasetSummary[] }>('GET', '/v1/datasets');
    return response.items || response as unknown as DatasetSummary[];
  }

  /**
   * Get a specific dataset by ID.
   *
   * @example
   * ```typescript
   * const dataset = await client.dataset('orders');
   * console.log(dataset.dimensions);
   * ```
   */
  async dataset(datasetId: string): Promise<Dataset> {
    return this.request<Dataset>('GET', `/v1/datasets/${datasetId}`);
  }

  /**
   * Execute a semantic query.
   *
   * @example
   * ```typescript
   * const result = await client.query({
   *   dataset: 'orders',
   *   dimensions: ['city', 'product'],
   *   metrics: ['total_revenue', 'order_count'],
   *   filters: [
   *     { field: 'order_date', operator: 'gte', value: '2024-01-01' }
   *   ],
   *   orderBy: [{ field: 'total_revenue', direction: 'desc' }],
   *   limit: 100
   * });
   *
   * console.log(result.data);
   * ```
   */
  async query<T = Record<string, unknown>>(options: QueryOptions): Promise<QueryResult<T>> {
    const payload = {
      dataset: options.dataset,
      dimensions: options.dimensions?.map(name => ({ name })) || [],
      metrics: options.metrics?.map(name => ({ name })) || [],
      filters: options.filters,
      orderBy: options.orderBy,
      limit: options.limit ?? 1000,
      offset: options.offset ?? 0,
    };

    return this.request<QueryResult<T>>('POST', '/v1/query', payload);
  }

  /**
   * Execute a GraphQL query.
   *
   * @example
   * ```typescript
   * const result = await client.graphql(`
   *   query {
   *     datasets {
   *       id
   *       name
   *     }
   *   }
   * `);
   * ```
   */
  async graphql<T = unknown>(
    query: string,
    variables?: Record<string, unknown>
  ): Promise<T> {
    const response = await this.request<GraphQLResponse<T>>('POST', '/v1/graphql', {
      query,
      variables,
    });

    if (response.errors?.length) {
      throw new QueryError(
        response.errors.map(e => e.message).join(', '),
        { errors: response.errors }
      );
    }

    return response.data as T;
  }
}

/**
 * Create a SetuPranali client instance.
 *
 * @example
 * ```typescript
 * const client = createClient({
 *   url: 'http://localhost:8080',
 *   apiKey: 'your-api-key'
 * });
 * ```
 */
export function createClient(config: ClientConfig): SetuPranali {
  return new SetuPranali(config);
}

