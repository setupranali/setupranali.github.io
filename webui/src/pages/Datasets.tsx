import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  Database, 
  Plus, 
  RefreshCw, 
  Loader2,
  XCircle,
  Layers,
  Table2,
  FileText,
  ChevronRight,
  ChevronDown,
  Server,
  Eye,
  Columns,
  Play,
  Boxes,
  Edit3
} from 'lucide-react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import { modelingApi } from '../lib/modeling-api';

const API_BASE = 'http://localhost:8080';

interface DatasetSource {
  engine: string;
  type: string;
  reference: string;
}

interface DatasetDimension {
  name: string;
  field: string;
  label: string;
}

interface DatasetMetric {
  name: string;
  label: string;
  expression: any;
  returnType: string;
  format?: string;
}

interface Dataset {
  id: string;
  name: string;
  description?: string;
  source?: DatasetSource;
  tags?: string[];
  fields?: Array<{
    name: string;
    type: string;
    semanticType?: string;
  }>;
  dimensions?: DatasetDimension[];
  metrics?: DatasetMetric[];
}

interface Source {
  id: string;
  name: string;
  type: string;
  created_at?: string;
}

interface SchemaInfo {
  name: string;
  tableCount?: number;
}

interface TableInfo {
  tableName: string;
  tableType: string;
  schema?: string;
}

interface ColumnInfo {
  columnName: string;
  dataType: string;
  isNullable: boolean;
  isPrimaryKey?: boolean;
}

type ViewMode = 'semantic' | 'models' | 'sources';

interface SemanticModelDataset {
  id: string;
  name: string;
  description?: string;
  sourceId: string;
  erdModelId?: string;
  dimensions: Array<{
    id: string;
    name: string;
    type?: string;
    dimensionType?: string;
    sourceTable?: string;
    sourceColumn?: string;
  }>;
  measures: Array<{
    id: string;
    name: string;
    aggregation?: string;
    expression?: string;
  }>;
  calculatedFields: Array<{
    id: string;
    name: string;
    expression: string;
  }>;
  createdAt?: string;
  updatedAt?: string;
}

export default function Datasets() {
  const [viewMode, setViewMode] = useState<ViewMode>('models');
  const [selectedDataset, setSelectedDataset] = useState<string | null>(null);
  const [selectedModelId, setSelectedModelId] = useState<string | null>(null);
  const [selectedSource, setSelectedSource] = useState<string | null>(null);
  const [expandedSchemas, setExpandedSchemas] = useState<Set<string>>(new Set());
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());
  const [tableColumns, setTableColumns] = useState<Record<string, ColumnInfo[]>>({});

  // Fetch semantic datasets from catalog YAML
  const datasetsQuery = useQuery({
    queryKey: ['datasets'],
    queryFn: async () => {
      const response = await axios.get<{ items: Dataset[] }>(`${API_BASE}/v1/datasets`);
      return response.data.items;
    },
    enabled: viewMode === 'semantic',
    refetchOnMount: 'always',
    staleTime: 0,
  });

  // Fetch all semantic models from Modeling Studio
  const semanticModelsQuery = useQuery({
    queryKey: ['all-semantic-models-datasets'],
    queryFn: async () => {
      const allModels: SemanticModelDataset[] = [];

      
      // Fetch from demo source
      try {
        const demoModels = await modelingApi.listSemanticModels('demo');
        for (const model of demoModels) {
          const fullModel = await modelingApi.getSemanticModel(model.id);
          allModels.push({
            id: fullModel.id,
            name: fullModel.name,
            description: fullModel.description,
            sourceId: 'demo',
            erdModelId: fullModel.erdModelId,
            dimensions: (fullModel.dimensions || []).map((d: any) => ({
              id: d.id,
              name: d.name,
              type: d.type || d.dimensionType,
              dimensionType: d.dimensionType,
              sourceTable: d.sourceTable,
              sourceColumn: d.sourceColumn,
            })),
            measures: (fullModel.measures || []).map((m: any) => ({
              id: m.id,
              name: m.name,
              aggregation: m.aggregation,
              expression: m.expression,
            })),
            calculatedFields: (fullModel.calculatedFields || []).map((cf: any) => ({
              id: cf.id,
              name: cf.name,
              expression: cf.expression,
            })),
            createdAt: fullModel.createdAt,
            updatedAt: fullModel.updatedAt,
          });
        }
      } catch (e) {
        console.log('No demo models');
      }
      
      // Fetch sources and their models
      try {
        const sources = await modelingApi.listSources();
        for (const source of sources) {
          try {
            const models = await modelingApi.listSemanticModels(source.id);
            for (const model of models) {
              const fullModel = await modelingApi.getSemanticModel(model.id);
              allModels.push({
                id: fullModel.id,
                name: fullModel.name,
                description: fullModel.description,
                sourceId: source.id,
                erdModelId: fullModel.erdModelId,
                dimensions: (fullModel.dimensions || []).map((d: any) => ({
                  id: d.id,
                  name: d.name,
                  type: d.type || d.dimensionType,
                  dimensionType: d.dimensionType,
                  sourceTable: d.sourceTable,
                  sourceColumn: d.sourceColumn,
                })),
                measures: (fullModel.measures || []).map((m: any) => ({
                  id: m.id,
                  name: m.name,
                  aggregation: m.aggregation,
                  expression: m.expression,
                })),
                calculatedFields: (fullModel.calculatedFields || []).map((cf: any) => ({
                  id: cf.id,
                  name: cf.name,
                  expression: cf.expression,
                })),
                createdAt: fullModel.createdAt,
                updatedAt: fullModel.updatedAt,
              });
            }
          } catch (e) {
            console.log(`No models for source ${source.id}`);
          }
        }
      } catch (e) {
        console.log('Failed to fetch sources');
      }
      
      return allModels;
    },
    enabled: viewMode === 'models',
    refetchOnMount: 'always',
    staleTime: 0,
  });

  // Fetch connected sources
  const sourcesQuery = useQuery({
    queryKey: ['sources'],
    queryFn: async () => {
      const response = await axios.get<{ items: Source[] }>(`${API_BASE}/v1/sources`);
      return response.data.items || [];
    },
    enabled: viewMode === 'sources',
    refetchOnMount: 'always',
    staleTime: 0,
  });

  // Fetch schemas for selected source
  const schemasQuery = useQuery({
    queryKey: ['source-schemas', selectedSource],
    queryFn: async () => {
      const response = await axios.get<{ schemas: SchemaInfo[] }>(
        `${API_BASE}/v1/modeling/sources/${selectedSource}/schemas`
      );
      return response.data.schemas;
    },
    enabled: viewMode === 'sources' && !!selectedSource,
  });

  // Fetch tables for expanded schemas
  const fetchTablesForSchema = async (schemaName: string) => {
    if (!selectedSource) return [];
    const response = await axios.get<{ tables: TableInfo[] }>(
      `${API_BASE}/v1/modeling/sources/${selectedSource}/schemas/${schemaName}/tables`
    );
    return response.data.tables;
  };

  // Fetch columns for a table
  const fetchColumnsForTable = async (schemaName: string, tableName: string) => {
    if (!selectedSource) return [];
    const response = await axios.get<{ columns: ColumnInfo[] }>(
      `${API_BASE}/v1/modeling/sources/${selectedSource}/schemas/${schemaName}/tables/${tableName}/columns`
    );
    return response.data.columns;
  };

  // State for schema tables
  const [schemaTables, setSchemaTables] = useState<Record<string, TableInfo[]>>({});
  const [loadingSchemas, setLoadingSchemas] = useState<Set<string>>(new Set());
  const [loadingTables, setLoadingTables] = useState<Set<string>>(new Set());

  // Auto-select first source when sources load
  useEffect(() => {
    if (viewMode === 'sources' && sourcesQuery.data && sourcesQuery.data.length > 0 && !selectedSource) {
      setSelectedSource(sourcesQuery.data[0].id);
    }
  }, [viewMode, sourcesQuery.data, selectedSource]);

  // Toggle schema expansion
  const toggleSchema = async (schemaName: string) => {
    const newExpanded = new Set(expandedSchemas);
    if (newExpanded.has(schemaName)) {
      newExpanded.delete(schemaName);
    } else {
      newExpanded.add(schemaName);
      // Fetch tables if not already loaded
      if (!schemaTables[schemaName]) {
        setLoadingSchemas(prev => new Set(prev).add(schemaName));
        try {
          const tables = await fetchTablesForSchema(schemaName);
          setSchemaTables(prev => ({ ...prev, [schemaName]: tables }));
        } catch (error) {
          console.error('Failed to fetch tables:', error);
        } finally {
          setLoadingSchemas(prev => {
            const newSet = new Set(prev);
            newSet.delete(schemaName);
            return newSet;
          });
        }
      }
    }
    setExpandedSchemas(newExpanded);
  };

  // Toggle table expansion
  const toggleTable = async (schemaName: string, tableName: string) => {
    const key = `${schemaName}.${tableName}`;
    const newExpanded = new Set(expandedTables);
    if (newExpanded.has(key)) {
      newExpanded.delete(key);
    } else {
      newExpanded.add(key);
      // Fetch columns if not already loaded
      if (!tableColumns[key]) {
        setLoadingTables(prev => new Set(prev).add(key));
        try {
          const columns = await fetchColumnsForTable(schemaName, tableName);
          setTableColumns(prev => ({ ...prev, [key]: columns }));
        } catch (error) {
          console.error('Failed to fetch columns:', error);
        } finally {
          setLoadingTables(prev => {
            const newSet = new Set(prev);
            newSet.delete(key);
            return newSet;
          });
        }
      }
    }
    setExpandedTables(newExpanded);
  };

  // Reset state when switching sources
  useEffect(() => {
    setSchemaTables({});
    setTableColumns({});
    setExpandedSchemas(new Set());
    setExpandedTables(new Set());
  }, [selectedSource]);

  // Fetch selected dataset details
  const datasetDetailQuery = useQuery({
    queryKey: ['dataset-detail', selectedDataset],
    queryFn: async () => {
      if (!selectedDataset) return null;
      const response = await axios.get<Dataset>(`${API_BASE}/v1/datasets/${selectedDataset}`);
      return response.data;
    },
    enabled: viewMode === 'semantic' && !!selectedDataset,
  });

  const handleRefresh = () => {
    if (viewMode === 'semantic') {
      datasetsQuery.refetch();
    } else if (viewMode === 'models') {
      semanticModelsQuery.refetch();
    } else {
      sourcesQuery.refetch();
      schemasQuery.refetch();
    }
  };

  const isLoading = viewMode === 'semantic' 
    ? datasetsQuery.isLoading 
    : viewMode === 'models' 
      ? semanticModelsQuery.isLoading 
      : sourcesQuery.isLoading;
  const isFetching = viewMode === 'semantic' 
    ? datasetsQuery.isFetching 
    : viewMode === 'models' 
      ? semanticModelsQuery.isFetching 
      : (sourcesQuery.isFetching || schemasQuery.isFetching);

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-white">Datasets</h1>
          <p className="text-slate-400">
            {viewMode === 'semantic' ? 'Semantic datasets from catalog' : 'Tables from connected data sources'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button 
            onClick={handleRefresh}
            disabled={isFetching}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <RefreshCw className={`w-5 h-5 text-slate-400 ${isFetching ? 'animate-spin' : ''}`} />
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-colors">
            <Plus className="w-4 h-4" />
            New Dataset
          </button>
        </div>
      </div>

      {/* View Mode Tabs */}
      <div className="flex items-center gap-2 mb-6">
        <div className="flex bg-slate-800 rounded-lg p-1">
          <button
            onClick={() => setViewMode('models')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              viewMode === 'models'
                ? 'bg-indigo-600 text-white'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Boxes className="w-4 h-4" />
            Semantic Models
          </button>
          <button
            onClick={() => setViewMode('semantic')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              viewMode === 'semantic'
                ? 'bg-indigo-600 text-white'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Layers className="w-4 h-4" />
            Catalog Datasets
          </button>
          <button
            onClick={() => setViewMode('sources')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              viewMode === 'sources'
                ? 'bg-indigo-600 text-white'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Server className="w-4 h-4" />
            Source Tables
          </button>
        </div>

        {/* Source selector when in sources mode */}
        {viewMode === 'sources' && sourcesQuery.data && sourcesQuery.data.length > 0 && (
          <select
            value={selectedSource || ''}
            onChange={(e) => setSelectedSource(e.target.value)}
            className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {sourcesQuery.data.map((source) => (
              <option key={source.id} value={source.id}>
                {source.name} ({source.type})
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
        </div>
      )}

      {/* Semantic Models View (from Modeling Studio) */}
      {viewMode === 'models' && !isLoading && (
        <>
          {/* Empty State */}
          {semanticModelsQuery.isSuccess && (!semanticModelsQuery.data || semanticModelsQuery.data.length === 0) && (
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-12 text-center">
              <Boxes className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-400 mb-2">No Semantic Models</h3>
              <p className="text-sm text-slate-500 mb-6">
                Create semantic models in the Modeling Studio to see them here.
              </p>
              <Link
                to="/modeling"
                className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-colors"
              >
                <Plus className="w-4 h-4" />
                Open Modeling Studio
              </Link>
            </div>
          )}

          {/* Models Grid */}
          {semanticModelsQuery.isSuccess && semanticModelsQuery.data && semanticModelsQuery.data.length > 0 && (
            <div className="flex gap-6">
              {/* Models List */}
              <div className="flex-1 space-y-3">
                {semanticModelsQuery.data.map((model) => (
                  <div
                    key={model.id}
                    onClick={() => setSelectedModelId(model.id)}
                    className={`bg-slate-800/50 border rounded-xl p-4 cursor-pointer transition-all ${
                      selectedModelId === model.id
                        ? 'border-indigo-500 ring-1 ring-indigo-500/30'
                        : 'border-slate-700 hover:border-slate-600'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-purple-500/20 rounded-lg flex items-center justify-center">
                          <Boxes className="w-5 h-5 text-purple-400" />
                        </div>
                        <div>
                          <h3 className="font-medium text-white">{model.name}</h3>
                          <p className="text-xs text-slate-500">
                            Source: {model.sourceId} · Created in Modeling Studio
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <p className="text-sm text-slate-300">
                            {model.dimensions?.length || 0} dims · {model.measures?.length || 0} measures
                          </p>
                          {model.calculatedFields && model.calculatedFields.length > 0 && (
                            <p className="text-xs text-slate-500">
                              {model.calculatedFields.length} calculated fields
                            </p>
                          )}
                        </div>
                        <ChevronRight className={`w-5 h-5 transition-transform ${
                          selectedModelId === model.id ? 'text-indigo-400 rotate-90' : 'text-slate-500'
                        }`} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Model Detail Panel */}
              <div className="w-96 flex-shrink-0 bg-slate-800/50 border border-slate-700 rounded-xl p-4">
                {!selectedModelId ? (
                  <div className="text-center py-12">
                    <Boxes className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                    <p className="text-slate-500">Select a model to view details</p>
                  </div>
                ) : (() => {
                  const model = semanticModelsQuery.data?.find(m => m.id === selectedModelId);
                  if (!model) return null;
                  return (
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="font-medium text-white">{model.name}</h3>
                        <Link
                          to="/modeling"
                          className="p-1.5 hover:bg-slate-700 rounded transition-colors"
                          title="Edit in Modeling Studio"
                        >
                          <Edit3 className="w-4 h-4 text-slate-400" />
                        </Link>
                      </div>
                      {model.description && (
                        <p className="text-xs text-slate-500 mb-4">{model.description}</p>
                      )}
                      
                      <div className="text-xs text-slate-500 mb-4">
                        Source: <span className="text-slate-300">{model.sourceId}</span>
                      </div>
                      
                      {/* Dimensions */}
                      {model.dimensions && model.dimensions.length > 0 && (
                        <div className="mb-4">
                          <h4 className="text-xs font-medium text-slate-400 uppercase mb-2">
                            Dimensions ({model.dimensions.length})
                          </h4>
                          <div className="space-y-1 max-h-32 overflow-y-auto">
                            {model.dimensions.map((dim) => (
                              <div key={dim.id} className="flex items-center justify-between py-1 px-2 bg-slate-900/50 rounded">
                                <span className="text-sm text-blue-300">{dim.name}</span>
                                <span className="text-xs text-slate-500 font-mono">{dim.type || dim.dimensionType || 'string'}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Measures */}
                      {model.measures && model.measures.length > 0 && (
                        <div className="mb-4">
                          <h4 className="text-xs font-medium text-slate-400 uppercase mb-2">
                            Measures ({model.measures.length})
                          </h4>
                          <div className="space-y-1 max-h-32 overflow-y-auto">
                            {model.measures.map((m) => (
                              <div key={m.id} className="flex items-center justify-between py-1 px-2 bg-slate-900/50 rounded">
                                <span className="text-sm text-emerald-300">{m.name}</span>
                                <span className="text-xs text-slate-500 font-mono">{m.aggregation || 'calc'}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Calculated Fields */}
                      {model.calculatedFields && model.calculatedFields.length > 0 && (
                        <div className="mb-4">
                          <h4 className="text-xs font-medium text-slate-400 uppercase mb-2">
                            Calculated Fields ({model.calculatedFields.length})
                          </h4>
                          <div className="space-y-1 max-h-32 overflow-y-auto">
                            {model.calculatedFields.map((cf) => (
                              <div key={cf.id} className="py-1 px-2 bg-slate-900/50 rounded">
                                <span className="text-sm text-orange-300">{cf.name}</span>
                                <p className="text-xs text-slate-500 font-mono truncate">{cf.expression}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="mt-4 pt-4 border-t border-slate-700 space-y-2">
                        <Link
                          to={`/models/${model.id}`}
                          className="block w-full text-center px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-colors"
                        >
                          View Full Details
                        </Link>
                        <Link
                          to="/contracts"
                          className="block w-full text-center px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
                        >
                          View/Edit Contract
                        </Link>
                        <Link
                          to="/modeling"
                          className="block w-full text-center px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
                        >
                          Open in Modeling Studio
                        </Link>
                      </div>
                    </div>
                  );
                })()}
              </div>
            </div>
          )}
        </>
      )}

      {/* Catalog Datasets View (from YAML) */}
      {viewMode === 'semantic' && !isLoading && (
        <>
          {/* Error State */}
          {datasetsQuery.isError && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-center">
              <XCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-red-400 mb-2">Failed to Load Datasets</h3>
              <p className="text-sm text-slate-400 mb-4">
                {(datasetsQuery.error as Error)?.message || 'An error occurred'}
              </p>
              <button
                onClick={() => datasetsQuery.refetch()}
                className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-colors"
              >
                Retry
              </button>
            </div>
          )}

          {/* Empty State */}
          {datasetsQuery.isSuccess && datasetsQuery.data.length === 0 && (
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-12 text-center">
              <Database className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-400 mb-2">No Semantic Datasets</h3>
              <p className="text-sm text-slate-500 mb-6">
                Semantic datasets are defined in YAML catalog files. Try checking the "Source Tables" tab to browse tables from connected sources.
              </p>
              <button
                onClick={() => setViewMode('sources')}
                className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-colors"
              >
                <Server className="w-4 h-4" />
                View Source Tables
              </button>
            </div>
          )}

          {/* Datasets Grid */}
          {datasetsQuery.isSuccess && datasetsQuery.data.length > 0 && (
            <div className="flex gap-6">
              {/* Datasets List */}
              <div className="flex-1 space-y-3">
                {datasetsQuery.data.map((dataset) => (
                  <div
                    key={dataset.id}
                    onClick={() => setSelectedDataset(dataset.id)}
                    className={`bg-slate-800/50 border rounded-xl p-4 cursor-pointer transition-all ${
                      selectedDataset === dataset.id
                        ? 'border-indigo-500 ring-1 ring-indigo-500/30'
                        : 'border-slate-700 hover:border-slate-600'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-indigo-500/20 rounded-lg flex items-center justify-center">
                          <Layers className="w-5 h-5 text-indigo-400" />
                        </div>
                        <div>
                          <h3 className="font-medium text-white">{dataset.name}</h3>
                          <p className="text-xs text-slate-500">
                            {dataset.source?.engine || 'duckdb'} · {dataset.source?.reference || dataset.id}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <p className="text-sm text-slate-300">{dataset.fields?.length || 0} fields</p>
                          {dataset.tags && dataset.tags.length > 0 && (
                            <p className="text-xs text-slate-500">{dataset.tags.join(', ')}</p>
                          )}
                        </div>
                        <ChevronRight className={`w-5 h-5 transition-transform ${
                          selectedDataset === dataset.id ? 'text-indigo-400 rotate-90' : 'text-slate-500'
                        }`} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Dataset Detail Panel */}
              <div className="w-96 flex-shrink-0 bg-slate-800/50 border border-slate-700 rounded-xl p-4">
                {!selectedDataset ? (
                  <div className="text-center py-12">
                    <FileText className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                    <p className="text-slate-500">Select a dataset to view details</p>
                  </div>
                ) : datasetDetailQuery.isLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
                  </div>
                ) : datasetDetailQuery.data ? (
                  <div>
                    <h3 className="font-medium text-white mb-2">{datasetDetailQuery.data.name}</h3>
                    {datasetDetailQuery.data.description && (
                      <p className="text-xs text-slate-500 mb-4">{datasetDetailQuery.data.description}</p>
                    )}
                    
                    {/* Fields */}
                    <div className="mb-4">
                      <h4 className="text-xs font-medium text-slate-400 uppercase mb-2">
                        Fields ({datasetDetailQuery.data.fields?.length || 0})
                      </h4>
                      <div className="space-y-1 max-h-48 overflow-y-auto">
                        {datasetDetailQuery.data.fields?.slice(0, 10).map((field, i) => (
                          <div key={i} className="flex items-center justify-between py-1 px-2 bg-slate-900/50 rounded">
                            <span className="text-sm text-slate-300">{field.name}</span>
                            <span className="text-xs text-slate-500 font-mono">{field.type}</span>
                          </div>
                        ))}
                        {(datasetDetailQuery.data.fields?.length || 0) > 10 && (
                          <p className="text-xs text-slate-500 text-center py-1">
                            +{(datasetDetailQuery.data.fields?.length || 0) - 10} more fields
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Dimensions */}
                    {datasetDetailQuery.data.dimensions && datasetDetailQuery.data.dimensions.length > 0 && (
                      <div className="mb-4">
                        <h4 className="text-xs font-medium text-slate-400 uppercase mb-2">Dimensions</h4>
                        <div className="flex flex-wrap gap-1">
                          {datasetDetailQuery.data.dimensions.map((dim, i) => (
                            <span key={i} className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded">
                              {dim.label}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Metrics */}
                    {datasetDetailQuery.data.metrics && datasetDetailQuery.data.metrics.length > 0 && (
                      <div>
                        <h4 className="text-xs font-medium text-slate-400 uppercase mb-2">Metrics</h4>
                        <div className="flex flex-wrap gap-1">
                          {datasetDetailQuery.data.metrics.map((metric, i) => (
                            <span key={i} className="px-2 py-1 bg-emerald-500/20 text-emerald-400 text-xs rounded">
                              {metric.label}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="mt-4 pt-4 border-t border-slate-700">
                      <Link
                        to={`/datasets/${selectedDataset}`}
                        className="block w-full text-center px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-colors"
                      >
                        View Full Details
                      </Link>
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          )}
        </>
      )}

      {/* Source Tables View */}
      {viewMode === 'sources' && !isLoading && (
        <>
          {/* No sources connected */}
          {sourcesQuery.isSuccess && sourcesQuery.data.length === 0 && (
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-12 text-center">
              <Server className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-400 mb-2">No Data Sources Connected</h3>
              <p className="text-sm text-slate-500 mb-6">
                Connect a data source to browse its tables and views.
              </p>
              <Link
                to="/sources"
                className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-colors"
              >
                <Plus className="w-4 h-4" />
                Add Data Source
              </Link>
            </div>
          )}

          {/* Source tables browser */}
          {sourcesQuery.isSuccess && sourcesQuery.data.length > 0 && selectedSource && (
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden">
              {/* Schema loading */}
              {schemasQuery.isLoading && (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
                </div>
              )}

              {/* Schema tree */}
              {schemasQuery.isSuccess && schemasQuery.data && (
                <div className="divide-y divide-slate-700">
                  {schemasQuery.data.map((schema) => (
                    <div key={schema.name}>
                      {/* Schema header */}
                      <div
                        onClick={() => toggleSchema(schema.name)}
                        className="flex items-center gap-3 px-4 py-3 hover:bg-slate-700/50 cursor-pointer"
                      >
                        {loadingSchemas.has(schema.name) ? (
                          <Loader2 className="w-4 h-4 text-slate-400 animate-spin" />
                        ) : expandedSchemas.has(schema.name) ? (
                          <ChevronDown className="w-4 h-4 text-slate-400" />
                        ) : (
                          <ChevronRight className="w-4 h-4 text-slate-400" />
                        )}
                        <Database className="w-5 h-5 text-blue-400" />
                        <span className="font-medium text-white">{schema.name}</span>
                        {schema.tableCount !== undefined && (
                          <span className="text-xs text-slate-500">({schema.tableCount} tables)</span>
                        )}
                      </div>

                      {/* Tables in schema */}
                      {expandedSchemas.has(schema.name) && schemaTables[schema.name] && (
                        <div className="bg-slate-900/30">
                          {schemaTables[schema.name].map((table) => {
                            const tableKey = `${schema.name}.${table.tableName}`;
                            return (
                              <div key={tableKey}>
                                {/* Table header */}
                                <div
                                  onClick={() => toggleTable(schema.name, table.tableName)}
                                  className="flex items-center gap-3 pl-10 pr-4 py-2 hover:bg-slate-700/30 cursor-pointer"
                                >
                                  {loadingTables.has(tableKey) ? (
                                    <Loader2 className="w-4 h-4 text-slate-400 animate-spin" />
                                  ) : expandedTables.has(tableKey) ? (
                                    <ChevronDown className="w-4 h-4 text-slate-400" />
                                  ) : (
                                    <ChevronRight className="w-4 h-4 text-slate-400" />
                                  )}
                                  {table.tableType === 'VIEW' ? (
                                    <Eye className="w-4 h-4 text-purple-400" />
                                  ) : (
                                    <Table2 className="w-4 h-4 text-emerald-400" />
                                  )}
                                  <span className="text-slate-300">{table.tableName}</span>
                                  <span className="text-xs text-slate-500">
                                    {table.tableType === 'VIEW' ? 'view' : 'table'}
                                  </span>
                                  <Link
                                    to={`/playground?source=${selectedSource}&table=${schema.name}.${table.tableName}`}
                                    onClick={(e) => e.stopPropagation()}
                                    className="ml-auto flex items-center gap-1 px-2 py-1 text-xs bg-indigo-500/20 text-indigo-400 rounded hover:bg-indigo-500/30 transition-colors"
                                  >
                                    <Play className="w-3 h-3" />
                                    Query
                                  </Link>
                                </div>

                                {/* Columns */}
                                {expandedTables.has(tableKey) && tableColumns[tableKey] && (
                                  <div className="bg-slate-900/50 pl-16 pr-4 py-2">
                                    <div className="space-y-1">
                                      {tableColumns[tableKey].map((column) => (
                                        <div
                                          key={column.columnName}
                                          className="flex items-center justify-between py-1 px-2 hover:bg-slate-800/50 rounded"
                                        >
                                          <div className="flex items-center gap-2">
                                            <Columns className="w-3 h-3 text-slate-500" />
                                            <span className="text-sm text-slate-300">{column.columnName}</span>
                                            {column.isPrimaryKey && (
                                              <span className="text-xs px-1 bg-yellow-500/20 text-yellow-400 rounded">PK</span>
                                            )}
                                          </div>
                                          <span className="text-xs text-slate-500 font-mono">{column.dataType}</span>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* No schemas */}
              {schemasQuery.isSuccess && (!schemasQuery.data || schemasQuery.data.length === 0) && (
                <div className="text-center py-12">
                  <Database className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                  <p className="text-slate-500">No schemas found in this source</p>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
