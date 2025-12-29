/**
 * SetuPranali JavaScript/TypeScript SDK
 *
 * @example
 * ```typescript
 * import { SetuPranali, createClient } from '@setupranali/client';
 *
 * const client = new SetuPranali({
 *   url: 'http://localhost:8080',
 *   apiKey: 'your-api-key'
 * });
 *
 * // List datasets
 * const datasets = await client.datasets();
 *
 * // Query data
 * const result = await client.query({
 *   dataset: 'orders',
 *   dimensions: ['city'],
 *   metrics: ['total_revenue']
 * });
 *
 * console.log(result.data);
 * ```
 */

export { SetuPranali, createClient } from './client';

export type {
  ClientConfig,
  Dataset,
  DatasetSummary,
  Dimension,
  Metric,
  Column,
  QueryResult,
  QueryOptions,
  Filter,
  OrderBy,
  HealthStatus,
  GraphQLResponse,
} from './types';

export {
  SetuPranaliError,
  AuthenticationError,
  DatasetNotFoundError,
  QueryError,
  ValidationError,
  RateLimitError,
  ConnectionError,
  TimeoutError,
} from './errors';

