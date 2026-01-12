/**
 * Types for the BI Modeling UI
 */

// =============================================================================
// CONNECTION & SOURCE TYPES
// =============================================================================

export interface ConnectionConfig {
  engine: string;
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;
  ssl: boolean;
  catalog?: string;  // For StarRocks/Doris catalog selection
  extra?: Record<string, unknown>;
}

export interface DataSource {
  id: string;
  name: string;
  description?: string;
  engine: string;
  status: 'active' | 'inactive' | 'error';
  createdAt: string;
  updatedAt: string;
}

export interface ConnectionTestResult {
  success: boolean;
  message: string;
  latencyMs?: number;
  serverVersion?: string;
}

export interface SupportedEngine {
  id: string;
  name: string;
  supportsSchemas: boolean;
}

// =============================================================================
// SCHEMA INTROSPECTION TYPES
// =============================================================================

export interface SchemaInfo {
  name: string;
  tables?: TableInfo[];
}

export interface TableInfo {
  schemaName: string;
  tableName: string;
  fullName: string;
  tableType: 'TABLE' | 'VIEW' | 'MATERIALIZED VIEW';
  rowCount?: number;
  comment?: string;
  primaryKey?: string[];
  columns?: ColumnInfo[];
}

export interface ColumnInfo {
  name: string;
  dataType: string;
  normalizedType: NormalizedColumnType;
  nullable: boolean;
  isPrimaryKey: boolean;
  isForeignKey: boolean;
  foreignKeyRef?: string;
  defaultValue?: string;
  comment?: string;
  ordinalPosition: number;
  maxLength?: number;
  precision?: number;
  scale?: number;
}

export type NormalizedColumnType =
  | 'string'
  | 'integer'
  | 'bigint'
  | 'float'
  | 'double'
  | 'decimal'
  | 'boolean'
  | 'date'
  | 'datetime'
  | 'timestamp'
  | 'time'
  | 'binary'
  | 'json'
  | 'array'
  | 'unknown';

// =============================================================================
// ERD TYPES
// =============================================================================

export interface Position {
  x: number;
  y: number;
}

export interface TableNode {
  id: string;
  schemaName: string;
  tableName: string;
  fullName: string;
  position: Position;
  columns: string[];
  isCollapsed: boolean;
  isVisible: boolean;
  color?: string;
  alias?: string;
  metadata?: Record<string, unknown>;
}

export interface RelationshipEdge {
  id: string;
  sourceNodeId: string;
  sourceColumn: string;
  targetNodeId: string;
  targetColumn: string;
  cardinality: Cardinality;
  joinType: JoinType;
  isActive: boolean;
  name?: string;
  description?: string;
  metadata?: Record<string, unknown>;
}

export type Cardinality = '1:1' | '1:N' | 'N:1' | 'N:N';
export type JoinType = 'inner' | 'left' | 'right' | 'full' | 'cross';

export interface ERDModel {
  id: string;
  name: string;
  description?: string;
  sourceId: string;
  nodes: TableNode[];
  edges: RelationshipEdge[];
  createdAt: string;
  updatedAt: string;
  version: number;
  metadata?: Record<string, unknown>;
}

// =============================================================================
// SEMANTIC MODEL TYPES
// =============================================================================

export interface Dimension {
  id: string;
  name: string;
  sourceColumn: string;
  sourceTable: string;
  description?: string;
  dimensionType: DimensionType;
  hierarchyLevel: number;
  parentDimensionId?: string;
  defaultFormat: FormatType;
  isVisible: boolean;
  synonyms: string[];
  metadata?: Record<string, unknown>;
}

export type DimensionType = 'categorical' | 'time' | 'geo' | 'hierarchical';

export interface Measure {
  id: string;
  name: string;
  expression: string;
  aggregation: AggregationType;
  sourceTable?: string;
  description?: string;
  formatString: string;
  formatType: FormatType;
  isVisible: boolean;
  isAdditive: boolean;
  dependsOn: string[];
  filters: MeasureFilter[];
  synonyms: string[];
  metadata?: Record<string, unknown>;
}

export type AggregationType =
  | 'SUM'
  | 'COUNT'
  | 'COUNT_DISTINCT'
  | 'AVG'
  | 'MIN'
  | 'MAX'
  | 'MEDIAN'
  | 'STDDEV'
  | 'VARIANCE'
  | 'FIRST'
  | 'LAST'
  | 'NONE';

export type FormatType =
  | 'number'
  | 'currency'
  | 'percent'
  | 'date'
  | 'datetime'
  | 'text'
  | 'boolean';

export interface MeasureFilter {
  field: string;
  operator: string;
  value: unknown;
}

export interface CalculatedField {
  id: string;
  name: string;
  expression: string;
  resultType: string;
  description?: string;
  formatString: string;
  formatType: FormatType;
  isVisible: boolean;
  referencedFields: string[];
  metadata?: Record<string, unknown>;
}

export interface TimeIntelligence {
  dimensionId: string;
  dateColumn: string;
  fiscalYearStartMonth: number;
  weekStartDay: number;
  enabledCalculations: string[];
}

export interface SemanticModel {
  id: string;
  name: string;
  sourceId: string;
  erdModelId?: string;
  dimensions: Dimension[];
  measures: Measure[];
  calculatedFields: CalculatedField[];
  timeIntelligence: TimeIntelligence[];
  description?: string;
  createdAt: string;
  updatedAt: string;
  version: number;
  metadata?: Record<string, unknown>;
}

// =============================================================================
// QUERY TYPES
// =============================================================================

export interface QueryFilter {
  field: string;
  operator: FilterOperator;
  value: unknown;
  secondValue?: unknown;
}

export type FilterOperator =
  | '='
  | '!='
  | '>'
  | '>='
  | '<'
  | '<='
  | 'LIKE'
  | 'NOT LIKE'
  | 'IN'
  | 'NOT IN'
  | 'IS NULL'
  | 'IS NOT NULL'
  | 'BETWEEN';

export interface QuerySort {
  field: string;
  direction: 'ASC' | 'DESC';
}

export interface SemanticQuery {
  dimensions: string[];
  measures: string[];
  filters: QueryFilter[];
  sorts: QuerySort[];
  limit?: number;
  offset?: number;
}

export interface QueryResult {
  rows: Record<string, unknown>[];
  columns: string[];
  rowCount: number;
  executionTimeMs: number;
  sql?: string;
  tablesUsed?: string[];
  warnings?: string[];
}

export interface QueryExplanation {
  sql: string;
  tablesUsed: string[];
  joinsUsed: string[];
  warnings: string[];
  dimensions: Array<{ name: string; resolved: boolean }>;
  measures: Array<{ name: string; resolved: boolean }>;
  filterCount: number;
  hasLimit: boolean;
}

export interface ExpressionValidation {
  valid: boolean;
  errors: string[];
  referencedFields: string[];
}

// =============================================================================
// UI STATE TYPES
// =============================================================================

export interface ModelingState {
  // Current selections
  activeSourceId: string | null;
  activeERDId: string | null;
  activeSemanticId: string | null;
  
  // UI state
  schemaPanelWidth: number;
  propertiesPanelWidth: number;
  bottomPanelHeight: number;
  
  // ERD canvas state
  erdZoom: number;
  erdPan: Position;
  selectedNodeIds: string[];
  selectedEdgeIds: string[];
  
  // Semantic builder state
  selectedDimensionId: string | null;
  selectedMeasureId: string | null;
  
  // Query workbench state
  queryMode: 'semantic' | 'sql';
  activeTab: 'results' | 'chart' | 'sql';
}

// =============================================================================
// API REQUEST/RESPONSE TYPES
// =============================================================================

export interface CreateERDRequest {
  name: string;
  sourceId: string;
  description?: string;
}

export interface AddTableNodeRequest {
  schemaName: string;
  tableName: string;
  position?: Position;
  columns?: string[];
}

export interface CreateRelationshipRequest {
  sourceNodeId: string;
  sourceColumn: string;
  targetNodeId: string;
  targetColumn: string;
  cardinality?: Cardinality;
  joinType?: JoinType;
  name?: string;
}

export interface CreateSemanticModelRequest {
  name: string;
  sourceId: string;
  erdModelId?: string;
  description?: string;
}

export interface CreateDimensionRequest {
  name: string;
  sourceColumn: string;
  sourceTable: string;
  description?: string;
  dimensionType?: DimensionType;
  format?: FormatType;
}

export interface CreateMeasureRequest {
  name: string;
  expression: string;
  aggregation?: AggregationType;
  sourceTable?: string;
  description?: string;
  formatString?: string;
}

export interface CreateCalculatedFieldRequest {
  name: string;
  expression: string;
  description?: string;
  resultType?: string;
}

export interface SemanticQueryRequest {
  erdModelId: string;
  semanticModelId: string;
  query: SemanticQuery;
}

export interface RawQueryRequest {
  sql: string;
  sourceId: string;
  params?: unknown[];
}

