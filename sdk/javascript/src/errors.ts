/**
 * SetuPranali SDK Errors
 */

export class SetuPranaliError extends Error {
  public statusCode?: number;
  public details?: Record<string, unknown>;

  constructor(message: string, statusCode?: number, details?: Record<string, unknown>) {
    super(message);
    this.name = 'SetuPranaliError';
    this.statusCode = statusCode;
    this.details = details;
  }
}

export class AuthenticationError extends SetuPranaliError {
  constructor(message: string = 'Authentication failed') {
    super(message, 401);
    this.name = 'AuthenticationError';
  }
}

export class DatasetNotFoundError extends SetuPranaliError {
  constructor(datasetId?: string) {
    super(datasetId ? `Dataset '${datasetId}' not found` : 'Dataset not found', 404);
    this.name = 'DatasetNotFoundError';
  }
}

export class QueryError extends SetuPranaliError {
  constructor(message: string, details?: Record<string, unknown>) {
    super(message, 400, details);
    this.name = 'QueryError';
  }
}

export class ValidationError extends SetuPranaliError {
  constructor(message: string) {
    super(message, 400);
    this.name = 'ValidationError';
  }
}

export class RateLimitError extends SetuPranaliError {
  public retryAfter?: number;

  constructor(message: string = 'Rate limit exceeded', retryAfter?: number) {
    super(message, 429);
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
  }
}

export class ConnectionError extends SetuPranaliError {
  constructor(message: string) {
    super(message);
    this.name = 'ConnectionError';
  }
}

export class TimeoutError extends SetuPranaliError {
  constructor(message: string = 'Request timed out') {
    super(message);
    this.name = 'TimeoutError';
  }
}

