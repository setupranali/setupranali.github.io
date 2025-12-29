import {
  DataQueryRequest,
  DataQueryResponse,
  DataSourceApi,
  DataSourceInstanceSettings,
  MutableDataFrame,
  FieldType,
  MetricFindValue,
} from '@grafana/data';
import { getBackendSrv, getTemplateSrv } from '@grafana/runtime';
import { lastValueFrom } from 'rxjs';

import {
  SetuPranaliQuery,
  SetuPranaliOptions,
  Dataset,
  QueryResponse,
  defaultQuery,
} from './types';

export class SetuPranaliDataSource extends DataSourceApi<SetuPranaliQuery, SetuPranaliOptions> {
  url?: string;
  defaultDataset?: string;

  constructor(instanceSettings: DataSourceInstanceSettings<SetuPranaliOptions>) {
    super(instanceSettings);
    this.url = instanceSettings.url;
    this.defaultDataset = instanceSettings.jsonData?.defaultDataset;
  }

  /**
   * Execute queries and return data frames
   */
  async query(options: DataQueryRequest<SetuPranaliQuery>): Promise<DataQueryResponse> {
    const { range } = options;
    const from = range?.from.valueOf();
    const to = range?.to.valueOf();

    const promises = options.targets
      .filter((target) => !target.hide && target.dataset)
      .map(async (target) => {
        const query = this.applyTemplateVariables(target, options.scopedVars);
        
        try {
          const response = await this.executeQuery(query, from, to);
          return this.transformResponse(response, query);
        } catch (error) {
          console.error('Query error:', error);
          throw error;
        }
      });

    const data = await Promise.all(promises);
    return { data: data.flat() };
  }

  /**
   * Execute a single query against SetuPranali API
   */
  private async executeQuery(
    query: SetuPranaliQuery,
    from?: number,
    to?: number
  ): Promise<QueryResponse> {
    const endpoint = query.queryType === 'sql' ? '/v1/sql' : '/v1/query';
    
    let body: any;
    
    if (query.queryType === 'sql') {
      body = {
        sql: query.rawSql,
        dataset: query.dataset,
      };
    } else {
      body = {
        dataset: query.dataset,
        dimensions: query.dimensions || [],
        metrics: query.metrics || [],
        filters: query.filters || [],
        limit: query.limit || 1000,
        orderBy: query.orderBy,
      };
      
      // Add time filter if time dimension is set
      if (query.timeDimension && from && to) {
        body.filters = [
          ...(body.filters || []),
          {
            dimension: query.timeDimension,
            operator: 'gte',
            value: new Date(from).toISOString(),
          },
          {
            dimension: query.timeDimension,
            operator: 'lte',
            value: new Date(to).toISOString(),
          },
        ];
        
        // Add time dimension to dimensions if not present
        if (query.timeGranularity && !body.dimensions.includes(query.timeDimension)) {
          body.dimensions = [query.timeDimension, ...body.dimensions];
        }
      }
    }

    const response = await lastValueFrom(
      getBackendSrv().fetch<QueryResponse>({
        url: `${this.url}${endpoint}`,
        method: 'POST',
        data: body,
      })
    );

    return response.data;
  }

  /**
   * Transform API response to Grafana data frames
   */
  private transformResponse(response: QueryResponse, query: SetuPranaliQuery): MutableDataFrame[] {
    const frame = new MutableDataFrame({
      refId: query.refId,
      fields: [],
    });

    if (!response.rows || response.rows.length === 0) {
      return [frame];
    }

    // Determine field types from first row
    const firstRow = response.rows[0];
    const columns = response.columns || Object.keys(firstRow);

    columns.forEach((col) => {
      const value = firstRow[col];
      let fieldType = FieldType.string;

      if (typeof value === 'number') {
        fieldType = FieldType.number;
      } else if (value instanceof Date || this.isDateString(value)) {
        fieldType = FieldType.time;
      } else if (typeof value === 'boolean') {
        fieldType = FieldType.boolean;
      }

      frame.addField({
        name: col,
        type: fieldType,
        values: [],
      });
    });

    // Add values
    response.rows.forEach((row) => {
      columns.forEach((col, index) => {
        let value = row[col];
        
        // Convert date strings to timestamps
        if (frame.fields[index].type === FieldType.time && typeof value === 'string') {
          value = new Date(value).getTime();
        }
        
        frame.fields[index].values.push(value);
      });
    });

    return [frame];
  }

  /**
   * Check if a string is a date
   */
  private isDateString(value: any): boolean {
    if (typeof value !== 'string') {
      return false;
    }
    const date = new Date(value);
    return !isNaN(date.getTime()) && value.includes('-');
  }

  /**
   * Apply template variables to query
   */
  private applyTemplateVariables(
    query: SetuPranaliQuery,
    scopedVars: any
  ): SetuPranaliQuery {
    const templateSrv = getTemplateSrv();
    
    return {
      ...query,
      dataset: templateSrv.replace(query.dataset, scopedVars),
      rawSql: query.rawSql ? templateSrv.replace(query.rawSql, scopedVars) : undefined,
      dimensions: query.dimensions?.map((d) => templateSrv.replace(d, scopedVars)),
      metrics: query.metrics?.map((m) => templateSrv.replace(m, scopedVars)),
    };
  }

  /**
   * Test data source connection
   */
  async testDatasource(): Promise<{ status: string; message: string }> {
    try {
      const response = await lastValueFrom(
        getBackendSrv().fetch({
          url: `${this.url}/v1/health`,
          method: 'GET',
        })
      );

      if (response.status === 200) {
        return {
          status: 'success',
          message: 'Successfully connected to SetuPranali',
        };
      }
      
      return {
        status: 'error',
        message: `Unexpected response: ${response.status}`,
      };
    } catch (error: any) {
      return {
        status: 'error',
        message: `Connection failed: ${error.message || 'Unknown error'}`,
      };
    }
  }

  /**
   * Get available datasets for variable queries
   */
  async metricFindQuery(query: string, options?: any): Promise<MetricFindValue[]> {
    // Support different query types
    if (query.startsWith('datasets')) {
      return this.getDatasets();
    }
    
    if (query.startsWith('dimensions(')) {
      const match = query.match(/dimensions\(([^)]+)\)/);
      if (match) {
        return this.getDimensions(match[1]);
      }
    }
    
    if (query.startsWith('metrics(')) {
      const match = query.match(/metrics\(([^)]+)\)/);
      if (match) {
        return this.getMetrics(match[1]);
      }
    }

    return [];
  }

  /**
   * Get list of datasets
   */
  async getDatasets(): Promise<MetricFindValue[]> {
    try {
      const response = await lastValueFrom(
        getBackendSrv().fetch<{ items: Dataset[] }>({
          url: `${this.url}/v1/introspection/datasets`,
          method: 'GET',
        })
      );

      return (response.data.items || []).map((dataset) => ({
        text: dataset.name || dataset.id,
        value: dataset.id,
      }));
    } catch (error) {
      console.error('Failed to fetch datasets:', error);
      return [];
    }
  }

  /**
   * Get dimensions for a dataset
   */
  async getDimensions(datasetId: string): Promise<MetricFindValue[]> {
    try {
      const response = await lastValueFrom(
        getBackendSrv().fetch<Dataset>({
          url: `${this.url}/v1/introspection/datasets/${datasetId}`,
          method: 'GET',
        })
      );

      return (response.data.dimensions || []).map((dim) => ({
        text: dim.name,
        value: dim.name,
      }));
    } catch (error) {
      console.error('Failed to fetch dimensions:', error);
      return [];
    }
  }

  /**
   * Get metrics for a dataset
   */
  async getMetrics(datasetId: string): Promise<MetricFindValue[]> {
    try {
      const response = await lastValueFrom(
        getBackendSrv().fetch<Dataset>({
          url: `${this.url}/v1/introspection/datasets/${datasetId}`,
          method: 'GET',
        })
      );

      return (response.data.metrics || []).map((metric) => ({
        text: metric.name,
        value: metric.name,
      }));
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
      return [];
    }
  }

  /**
   * Get default query
   */
  getDefaultQuery(): Partial<SetuPranaliQuery> {
    return {
      ...defaultQuery,
      dataset: this.defaultDataset || '',
    };
  }
}

