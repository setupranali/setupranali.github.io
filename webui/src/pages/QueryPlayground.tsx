import { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  Play, 
  Code, 
  Database,
  Table2,
  Clock,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Download,
  Copy,
  Check,
  Key,
  ChevronDown,
  ChevronRight,
  Server,
  Layers,
  Eye
} from 'lucide-react';
import axios from 'axios';
import Editor from '@monaco-editor/react';
import { cn } from '../lib/utils';

const API_BASE = 'http://localhost:8080';

interface QueryResult {
  columns?: Array<{ name: string; type: string }>;
  data?: Record<string, any>[];
  rows?: Record<string, any>[];
  row_count?: number;
  rowCount?: number;
  executionTimeMs?: number;
  execution_time_ms?: number;
  sql?: string;
  error?: string;
}

interface Dataset {
  id: string;
  name: string;
  description?: string;
  fields?: Array<{ name: string; type: string }>;
}

interface Source {
  id: string;
  name: string;
  type: string;
  status: string;
}

interface SchemaInfo {
  name: string;
}

interface TableInfo {
  schemaName: string;
  tableName: string;
  fullName: string;
  tableType: string;
}

interface ColumnInfo {
  name: string;
  dataType: string;
  nullable: boolean;
  isPrimaryKey: boolean;
}

type QueryMode = 'dataset' | 'source';

export default function QueryPlayground() {
  const [query, setQuery] = useState(`SELECT 
  city,
  COUNT(*) as order_count,
  SUM(revenue) as total_revenue
FROM orders
GROUP BY city
ORDER BY total_revenue DESC
LIMIT 10`);
  const [apiKey, setApiKey] = useState('dev-key-123');
  const [queryMode, setQueryMode] = useState<QueryMode>('dataset');
  const [selectedDataset, setSelectedDataset] = useState('orders');
  const [selectedSource, setSelectedSource] = useState<string>('');
  const [selectedSchema, setSelectedSchema] = useState<string>('');
  const [expandedSchemas, setExpandedSchemas] = useState<Set<string>>(new Set());
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());
  const [result, setResult] = useState<QueryResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [executionTime, setExecutionTime] = useState<number | null>(null);
  const [copiedSql, setCopiedSql] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);

  // Fetch datasets list
  const datasetsQuery = useQuery({
    queryKey: ['datasets'],
    queryFn: async () => {
      try {
        const response = await axios.get<{ items: Dataset[] }>(`${API_BASE}/v1/datasets`);
        // Handle both { items: [...] } and direct array responses
        const data = response.data;
        if (Array.isArray(data)) {
          return data;
        }
        if (data && Array.isArray(data.items)) {
          return data.items;
        }
        return [];
      } catch (error) {
        console.error('Failed to fetch datasets:', error);
        return [];
      }
    },
    refetchOnMount: 'always',
    staleTime: 0,
  });

  // Fetch sources list
  const sourcesQuery = useQuery({
    queryKey: ['sources'],
    queryFn: async () => {
      const response = await axios.get<{ items: Source[] }>(`${API_BASE}/v1/sources`);
      return response.data.items || [];
    },
    refetchOnMount: 'always',
    staleTime: 0,
  });

  // Fetch dataset schema
  const schemaQuery = useQuery({
    queryKey: ['dataset-schema', selectedDataset],
    queryFn: async () => {
      const response = await axios.get<Dataset>(`${API_BASE}/v1/datasets/${selectedDataset}`);
      return response.data;
    },
    enabled: queryMode === 'dataset' && !!selectedDataset,
  });

  // Fetch schemas for selected source
  const sourceSchemasQuery = useQuery({
    queryKey: ['source-schemas', selectedSource],
    queryFn: async () => {
      try {
        const response = await axios.get<{ schemas: SchemaInfo[] }>(`${API_BASE}/v1/modeling/sources/${selectedSource}/schemas`);
        // Handle both { schemas: [...] } and direct array responses
        const data = response.data;
        let schemas: SchemaInfo[] = [];
        if (Array.isArray(data)) {
          schemas = data;
        } else if (data && Array.isArray(data.schemas)) {
          schemas = data.schemas;
        }
        // Deduplicate schemas
        const uniqueSchemas = [...new Map(schemas.map(s => [s.name, s])).values()];
        return uniqueSchemas;
      } catch (error: any) {
        // If it's a decryption error, provide helpful message
        if (error.response?.status === 500 && error.response?.data?.detail?.includes('cannot be decrypted')) {
          throw new Error(`Source credentials cannot be decrypted. Please re-register this source with the current encryption key. Error: ${error.response.data.detail}`);
        }
        throw error;
      }
    },
    enabled: queryMode === 'source' && !!selectedSource,
  });

  // Fetch tables for selected schema
  const sourceTablesQueries = useQuery({
    queryKey: ['source-tables', selectedSource, selectedSchema],
    queryFn: async () => {
      const response = await axios.get<{ tables: TableInfo[] }>(`${API_BASE}/v1/modeling/sources/${selectedSource}/schemas/${selectedSchema}/tables`);
      return response.data.tables;
    },
    enabled: queryMode === 'source' && !!selectedSource && !!selectedSchema,
  });

  // Store tables per schema
  const [schemaTablesCache, setSchemaTablesCache] = useState<Record<string, TableInfo[]>>({});
  const [tableColumnsCache, setTableColumnsCache] = useState<Record<string, ColumnInfo[]>>({});

  const fetchTablesForSchema = async (schemaName: string) => {
    if (schemaTablesCache[schemaName]) return;
    try {
      const response = await axios.get<{ tables: TableInfo[] }>(
        `${API_BASE}/v1/modeling/sources/${selectedSource}/schemas/${schemaName}/tables`
      );
      setSchemaTablesCache(prev => ({ ...prev, [schemaName]: response.data.tables }));
    } catch (err) {
      console.error('Failed to fetch tables:', err);
    }
  };

  const fetchColumnsForTable = async (schemaName: string, tableName: string) => {
    const key = `${schemaName}.${tableName}`;
    if (tableColumnsCache[key]) return;
    try {
      const response = await axios.get<{ columns: ColumnInfo[] }>(
        `${API_BASE}/v1/modeling/sources/${selectedSource}/schemas/${schemaName}/tables/${tableName}/columns`
      );
      setTableColumnsCache(prev => ({ ...prev, [key]: response.data.columns }));
    } catch (err) {
      console.error('Failed to fetch columns:', err);
    }
  };

  const toggleSchema = (schemaName: string) => {
    const newExpanded = new Set(expandedSchemas);
    if (newExpanded.has(schemaName)) {
      newExpanded.delete(schemaName);
    } else {
      newExpanded.add(schemaName);
      fetchTablesForSchema(schemaName);
    }
    setExpandedSchemas(newExpanded);
  };

  const toggleTable = (fullTableName: string, schemaName: string, tableName: string) => {
    const newExpanded = new Set(expandedTables);
    if (newExpanded.has(fullTableName)) {
      newExpanded.delete(fullTableName);
    } else {
      newExpanded.add(fullTableName);
      fetchColumnsForTable(schemaName, tableName);
    }
    setExpandedTables(newExpanded);
  };

  const runQuery = useCallback(async () => {
    if (!query.trim()) return;
    
    // Validate source is selected when in source mode
    if (queryMode === 'source' && !selectedSource) {
      setError('Please select a data source');
      return;
    }
    
    setIsRunning(true);
    setError(null);
    setResult(null);
    
    const startTime = performance.now();
    
    try {
      let response;
      
      if (queryMode === 'source' && selectedSource) {
        // Query against connected source (MySQL, PostgreSQL, etc.)
        response = await axios.post<QueryResult>(
          `${API_BASE}/v1/modeling/sources/${selectedSource}/query`,
          {
            sql: query,
            source_id: selectedSource,
          },
          {
            headers: {
              'Content-Type': 'application/json',
              'X-API-Key': apiKey
            }
          }
        );
      } else {
        // Query against semantic dataset (uses DuckDB demo data)
        response = await axios.post<QueryResult>(
          `${API_BASE}/v1/sql`,
          {
            sql: query,
            dataset: selectedDataset
          },
          {
            headers: {
              'Content-Type': 'application/json',
              'X-API-Key': apiKey
            }
          }
        );
      }
      
      const endTime = performance.now();
      setExecutionTime(Math.round(endTime - startTime));
      setResult(response.data);
    } catch (err: any) {
      const endTime = performance.now();
      setExecutionTime(Math.round(endTime - startTime));
      
      if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        if (typeof detail === 'string') {
          setError(detail);
        } else if (detail.message) {
          setError(detail.message);
        } else {
          setError(JSON.stringify(detail));
        }
      } else {
        setError(err.message || 'Query execution failed');
      }
    } finally {
      setIsRunning(false);
    }
  }, [query, selectedDataset, selectedSource, apiKey, queryMode]);

  // Get rows from either data or rows field
  const resultRows = result?.data || result?.rows || [];
  
  // Get column names - handle both string[] and {name, type}[] formats
  const getColumnNames = (): string[] => {
    if (!result?.columns?.length) {
      return resultRows.length > 0 ? Object.keys(resultRows[0]) : [];
    }
    if (typeof result.columns[0] === 'object' && 'name' in result.columns[0]) {
      return result.columns.map((c: any) => c.name);
    }
    return result.columns as unknown as string[];
  };

  const handleCopySql = () => {
    navigator.clipboard.writeText(query);
    setCopiedSql(true);
    setTimeout(() => setCopiedSql(false), 2000);
  };

  const handleDownloadCsv = () => {
    if (!resultRows.length) return;
    
    const headers = getColumnNames();
    const csvContent = [
      headers.join(','),
      ...resultRows.map(row => 
        headers.map(h => {
          const val = row[h];
          if (val === null || val === undefined) return '';
          if (typeof val === 'string' && val.includes(',')) return `"${val}"`;
          return val;
        }).join(',')
      )
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `query-results-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const rowCount = result?.row_count || result?.rowCount || resultRows.length || 0;
  const execTime = result?.executionTimeMs || result?.execution_time_ms || executionTime;

  const insertTableName = (tableName: string) => {
    setQuery(prev => prev + ` ${tableName}`);
  };

  const insertColumnName = (columnName: string) => {
    setQuery(prev => prev + ` ${columnName}`);
  };

  return (
    <div className="h-full flex flex-col bg-slate-900">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-700">
        <div className="flex items-center gap-4">
          <div>
            <h1 className="text-xl font-semibold text-white">Query Playground</h1>
            <p className="text-sm text-slate-400">Test SQL queries against your datasets & sources</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Mode Selector */}
          <div className="flex rounded-lg overflow-hidden border border-slate-600">
            <button
              onClick={() => setQueryMode('dataset')}
              className={cn(
                "px-3 py-1.5 text-sm flex items-center gap-1 transition-colors",
                queryMode === 'dataset' 
                  ? "bg-indigo-600 text-white" 
                  : "bg-slate-800 text-slate-400 hover:text-white"
              )}
            >
              <Layers className="w-4 h-4" />
              Datasets
            </button>
            <button
              onClick={() => setQueryMode('source')}
              className={cn(
                "px-3 py-1.5 text-sm flex items-center gap-1 transition-colors",
                queryMode === 'source' 
                  ? "bg-indigo-600 text-white" 
                  : "bg-slate-800 text-slate-400 hover:text-white"
              )}
            >
              <Server className="w-4 h-4" />
              Sources
            </button>
          </div>

          {/* Dataset/Source Selector */}
          {queryMode === 'dataset' ? (
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-slate-400" />
              <select
                value={selectedDataset}
                onChange={(e) => setSelectedDataset(e.target.value)}
                className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {Array.isArray(datasetsQuery.data) ? datasetsQuery.data.map((ds) => (
                  <option key={ds.id} value={ds.id}>
                    {ds.name}
                  </option>
                )) : null}
              </select>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-slate-400" />
              <select
                value={selectedSource}
                onChange={(e) => {
                  setSelectedSource(e.target.value);
                  setSchemaTablesCache({});
                  setTableColumnsCache({});
                  setExpandedSchemas(new Set());
                  setExpandedTables(new Set());
                }}
                className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Select Source...</option>
                {Array.isArray(sourcesQuery.data) ? sourcesQuery.data.map((src) => (
                  <option key={src.id} value={src.id}>
                    {src.name} ({src.type})
                  </option>
                )) : null}
              </select>
            </div>
          )}
          
          {/* API Key Input */}
          <div className="flex items-center gap-2">
            <Key className="w-4 h-4 text-slate-400" />
            <div className="relative">
              <input
                type={showApiKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="API Key"
                className="w-40 bg-slate-800 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <button
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
              >
                {showApiKey ? '🙈' : '👁️'}
              </button>
            </div>
          </div>
          
          {/* Run Button */}
          <button
            onClick={runQuery}
            disabled={isRunning || !query.trim()}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
          >
            {isRunning ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            {isRunning ? 'Running...' : 'Run Query'}
          </button>
        </div>
      </div>
      
      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Editor Panel - Fixed width */}
        <div className="w-[600px] min-w-[400px] flex flex-col border-r border-slate-700">
          {/* Editor Toolbar */}
          <div className="flex items-center justify-between px-4 py-2 border-b border-slate-700 bg-slate-800/50">
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <Code className="w-4 h-4" />
              SQL Editor
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleCopySql}
                className="p-1.5 hover:bg-slate-700 rounded transition-colors"
                title="Copy SQL"
              >
                {copiedSql ? (
                  <Check className="w-4 h-4 text-emerald-400" />
                ) : (
                  <Copy className="w-4 h-4 text-slate-400" />
                )}
              </button>
            </div>
          </div>
          
          {/* Monaco Editor */}
          <div className="flex-1">
            <Editor
              height="100%"
              defaultLanguage="sql"
              theme="vs-dark"
              value={query}
              onChange={(value) => setQuery(value || '')}
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                automaticLayout: true,
                padding: { top: 12 },
                tabSize: 2,
                wordWrap: 'on',
              }}
            />
          </div>
        </div>
        
        {/* Schema Panel - Fixed width */}
        <div className="w-80 min-w-[280px] bg-slate-800/50 overflow-y-auto flex-shrink-0">
          <div className="p-4 border-b border-slate-700">
            <h3 className="font-medium text-white flex items-center gap-2">
              <Table2 className="w-4 h-4 text-indigo-400" />
              {queryMode === 'dataset' ? 'Schema' : 'Tables & Views'}
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              {queryMode === 'dataset' ? selectedDataset : (
                (sourcesQuery.data || []).find(s => s.id === selectedSource)?.name || 'Select a source'
              )}
            </p>
          </div>
          
          <div className="p-2">
            {queryMode === 'dataset' ? (
              // Dataset fields view
              schemaQuery.isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-5 h-5 text-slate-400 animate-spin" />
                </div>
              ) : schemaQuery.data?.fields ? (
                <div className="space-y-1">
                  {Array.isArray(schemaQuery.data.fields) ? schemaQuery.data.fields.map((field, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between py-1.5 px-2 hover:bg-slate-700/50 rounded cursor-pointer group"
                      onClick={() => insertColumnName(field.name)}
                    >
                      <span className="text-sm text-slate-300 group-hover:text-white">
                        {field.name}
                      </span>
                      <span className="text-xs text-slate-500 font-mono">
                        {field.type}
                      </span>
                    </div>
                  )) : null}
                </div>
              ) : (
                <p className="text-sm text-slate-500 text-center py-4">No schema available</p>
              )
            ) : (
              // Source tables/views view
              !selectedSource ? (
                <p className="text-sm text-slate-500 text-center py-4">Select a source to see tables</p>
              ) : sourceSchemasQuery.isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-5 h-5 text-slate-400 animate-spin" />
                </div>
              ) : sourceSchemasQuery.error ? (
                <div className="flex items-center justify-center py-8">
                  <div className="text-center max-w-md px-4">
                    <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
                    <p className="text-red-400 font-medium mb-1">Error Loading Schemas</p>
                    <p className="text-sm text-slate-400">{sourceSchemasQuery.error instanceof Error ? sourceSchemasQuery.error.message : 'Failed to load schemas'}</p>
                    <p className="text-xs text-slate-500 mt-2">Please re-register this source from the Sources page.</p>
                  </div>
                </div>
              ) : sourceSchemasQuery.data?.length ? (
                <div className="space-y-1">
                  {Array.isArray(sourceSchemasQuery.data) ? sourceSchemasQuery.data.map((schema) => (
                    <div key={schema.name}>
                      {/* Schema header */}
                      <div
                        className="flex items-center gap-2 py-1.5 px-2 hover:bg-slate-700/50 rounded cursor-pointer"
                        onClick={() => toggleSchema(schema.name)}
                      >
                        {expandedSchemas.has(schema.name) ? (
                          <ChevronDown className="w-4 h-4 text-slate-400" />
                        ) : (
                          <ChevronRight className="w-4 h-4 text-slate-400" />
                        )}
                        <Database className="w-4 h-4 text-indigo-400" />
                        <span className="text-sm text-slate-300">{schema.name}</span>
                      </div>
                      
                      {/* Tables in schema */}
                      {expandedSchemas.has(schema.name) && (
                        <div className="ml-4 pl-2 border-l border-slate-700">
                          {Array.isArray(schemaTablesCache[schema.name]) ? schemaTablesCache[schema.name].map((table) => (
                            <div key={table.fullName}>
                              {/* Table header */}
                              <div
                                className="flex items-center gap-2 py-1.5 px-2 hover:bg-slate-700/50 rounded cursor-pointer group"
                                onClick={() => toggleTable(table.fullName, schema.name, table.tableName)}
                              >
                                {expandedTables.has(table.fullName) ? (
                                  <ChevronDown className="w-3 h-3 text-slate-400" />
                                ) : (
                                  <ChevronRight className="w-3 h-3 text-slate-400" />
                                )}
                                {table.tableType === 'VIEW' ? (
                                  <Eye className="w-4 h-4 text-purple-400" />
                                ) : (
                                  <Table2 className="w-4 h-4 text-emerald-400" />
                                )}
                                <span 
                                  className="text-sm text-slate-300 group-hover:text-white flex-1"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    insertTableName(table.fullName);
                                  }}
                                >
                                  {table.tableName}
                                </span>
                                <span className="text-xs text-slate-500">
                                  {table.tableType}
                                </span>
                              </div>
                              
                              {/* Columns in table */}
                              {expandedTables.has(table.fullName) && tableColumnsCache[table.fullName] && (
                                <div className="ml-6 pl-2 border-l border-slate-700/50">
                                  {Array.isArray(tableColumnsCache[table.fullName]) ? tableColumnsCache[table.fullName].map((col, i) => (
                                    <div
                                      key={i}
                                      className="flex items-center justify-between py-1 px-2 hover:bg-slate-700/50 rounded cursor-pointer group"
                                      onClick={() => insertColumnName(col.name)}
                                    >
                                      <span className="text-xs text-slate-400 group-hover:text-white">
                                        {col.name}
                                        {col.isPrimaryKey && <span className="ml-1 text-yellow-400">🔑</span>}
                                      </span>
                                      <span className="text-xs text-slate-600 font-mono">
                                        {col.dataType}
                                      </span>
                                    </div>
                                  )) : null}
                                </div>
                              )}
                            </div>
                          )) : (
                            <div className="flex items-center justify-center py-4">
                              <Loader2 className="w-4 h-4 text-slate-500 animate-spin" />
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )) : null}
                </div>
              ) : (
                <p className="text-sm text-slate-500 text-center py-4">No schemas found</p>
              )
            )}
          </div>
        </div>
      </div>
      
      {/* Results Panel */}
      <div className="h-80 border-t border-slate-700 flex flex-col">
        {/* Results Header */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-slate-700 bg-slate-800/50">
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium text-white">Results</span>
            {execTime !== null && (
              <span className="flex items-center gap-1 text-xs text-slate-400">
                <Clock className="w-3 h-3" />
                {execTime}ms
              </span>
            )}
            {rowCount > 0 && (
              <span className="text-xs text-slate-400">
                {rowCount} row{rowCount !== 1 ? 's' : ''}
              </span>
            )}
          </div>
          
          {resultRows.length > 0 ? (
            <button
              onClick={handleDownloadCsv}
              className="flex items-center gap-1 px-2 py-1 text-xs text-slate-400 hover:text-white hover:bg-slate-700 rounded transition-colors"
            >
              <Download className="w-3 h-3" />
              Export CSV
            </button>
          ) : null}
        </div>
        
        {/* Results Content */}
        <div className="flex-1 overflow-auto">
          {isRunning ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center max-w-md">
                <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-3" />
                <p className="text-red-400 font-medium mb-2">Query Error</p>
                <p className="text-sm text-slate-400">{error}</p>
              </div>
            </div>
          ) : resultRows.length > 0 ? (
            <table className="w-full text-sm">
              <thead className="bg-slate-800 sticky top-0">
                <tr>
                  {getColumnNames().map((col, i) => (
                    <th key={i} className="text-left px-4 py-2 text-slate-300 font-medium border-b border-slate-700">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {resultRows.map((row, i) => (
                  <tr key={i} className="hover:bg-slate-800/50 border-b border-slate-700/50">
                    {getColumnNames().map((col, j) => (
                      <td key={j} className="px-4 py-2 text-slate-300">
                        {row[col] !== null && row[col] !== undefined ? String(row[col]) : <span className="text-slate-500">NULL</span>}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          ) : result ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
                <p className="text-emerald-400 font-medium">Query executed successfully</p>
                <p className="text-sm text-slate-400 mt-1">No rows returned</p>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <Code className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-400">Run a query to see results</p>
                <p className="text-xs text-slate-500 mt-1">Press the Run Query button or Ctrl+Enter</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
