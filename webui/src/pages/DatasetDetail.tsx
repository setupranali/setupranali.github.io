import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  Database, 
  ArrowLeft, 
  RefreshCw, 
  Loader2, 
  XCircle,
  Table2,
  Hash,
  Calendar,
  Type,
  ToggleLeft,
  Play,
  Copy,
  Check,
  FileText,
  Shield,
  Clock,
  Tag
} from 'lucide-react';
import axios from 'axios';
import { useState } from 'react';

const API_BASE = 'http://localhost:8080';

interface DatasetSource {
  engine: string;
  type: string;
  reference: string;
}

interface DatasetField {
  name: string;
  type: string;
  semanticType?: string;
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

interface DatasetDetail {
  id: string;
  name: string;
  description?: string;
  defaultTimezone?: string;
  tags?: string[];
  source: DatasetSource;
  fields: DatasetField[];
  dimensions?: DatasetDimension[];
  metrics?: DatasetMetric[];
  rls?: {
    enabled: boolean;
    column: string;
    mode: string;
    allowAdminBypass: boolean;
  };
  incremental?: {
    enabled: boolean;
    column: string;
    type: string;
    mode: string;
    maxWindowDays: number;
  };
}

export default function DatasetDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [copiedField, setCopiedField] = useState<string | null>(null);

  // Fetch dataset details
  const datasetQuery = useQuery({
    queryKey: ['dataset-detail', id],
    queryFn: async () => {
      const response = await axios.get<DatasetDetail>(`${API_BASE}/v1/datasets/${id}`);
      return response.data;
    },
    enabled: !!id,
  });

  const copyFieldName = (fieldName: string) => {
    navigator.clipboard.writeText(fieldName);
    setCopiedField(fieldName);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const getFieldIcon = (type: string) => {
    const typeLower = type.toLowerCase();
    if (typeLower.includes('int') || typeLower.includes('float') || typeLower.includes('double') || typeLower.includes('decimal') || typeLower.includes('number')) {
      return <Hash className="w-4 h-4 text-blue-400" />;
    }
    if (typeLower.includes('date') || typeLower.includes('time')) {
      return <Calendar className="w-4 h-4 text-purple-400" />;
    }
    if (typeLower.includes('bool')) {
      return <ToggleLeft className="w-4 h-4 text-orange-400" />;
    }
    return <Type className="w-4 h-4 text-emerald-400" />;
  };

  const getSemanticBadge = (semanticType?: string) => {
    if (!semanticType) return null;
    const badges: Record<string, { bg: string; text: string }> = {
      identifier: { bg: 'bg-yellow-500/20', text: 'text-yellow-400' },
      dimension: { bg: 'bg-blue-500/20', text: 'text-blue-400' },
      metric: { bg: 'bg-emerald-500/20', text: 'text-emerald-400' },
      time: { bg: 'bg-purple-500/20', text: 'text-purple-400' },
      geo_city: { bg: 'bg-pink-500/20', text: 'text-pink-400' },
    };
    const style = badges[semanticType] || { bg: 'bg-slate-500/20', text: 'text-slate-400' };
    return (
      <span className={`px-1.5 py-0.5 ${style.bg} ${style.text} text-xs rounded`}>
        {semanticType}
      </span>
    );
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/datasets')}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-slate-400" />
          </button>
          <div>
            <h1 className="text-2xl font-semibold text-white">
              {datasetQuery.data?.name || 'Dataset Details'}
            </h1>
            <p className="text-slate-400">
              {datasetQuery.data?.description || `Dataset ID: ${id}`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button 
            onClick={() => datasetQuery.refetch()}
            disabled={datasetQuery.isFetching}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <RefreshCw className={`w-5 h-5 text-slate-400 ${datasetQuery.isFetching ? 'animate-spin' : ''}`} />
          </button>
          <Link
            to={`/playground?dataset=${id}`}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-colors"
          >
            <Play className="w-4 h-4" />
            Query in Playground
          </Link>
        </div>
      </div>

      {/* Loading State */}
      {datasetQuery.isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
        </div>
      )}

      {/* Error State */}
      {datasetQuery.isError && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-center">
          <XCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-red-400 mb-2">Failed to Load Dataset</h3>
          <p className="text-sm text-slate-400 mb-4">
            {(datasetQuery.error as Error)?.message || 'Dataset not found'}
          </p>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={() => datasetQuery.refetch()}
              className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-colors"
            >
              Retry
            </button>
            <button
              onClick={() => navigate('/datasets')}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
            >
              Back to Datasets
            </button>
          </div>
        </div>
      )}

      {/* Dataset Content */}
      {datasetQuery.isSuccess && datasetQuery.data && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Info */}
          <div className="lg:col-span-2 space-y-6">
            {/* Overview Card */}
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
              <h2 className="text-lg font-medium text-white mb-4 flex items-center gap-2">
                <Database className="w-5 h-5 text-indigo-400" />
                Overview
              </h2>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-slate-500 uppercase mb-1">Source Engine</p>
                  <p className="text-slate-300">{datasetQuery.data.source?.engine || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 uppercase mb-1">Source Table</p>
                  <p className="text-slate-300 font-mono text-sm">{datasetQuery.data.source?.reference || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 uppercase mb-1">Total Fields</p>
                  <p className="text-slate-300">{datasetQuery.data.fields?.length || 0}</p>
                </div>
                {datasetQuery.data.defaultTimezone && (
                  <div>
                    <p className="text-xs text-slate-500 uppercase mb-1">Timezone</p>
                    <p className="text-slate-300">{datasetQuery.data.defaultTimezone}</p>
                  </div>
                )}
                {datasetQuery.data.tags && datasetQuery.data.tags.length > 0 && (
                  <div className="col-span-2">
                    <p className="text-xs text-slate-500 uppercase mb-1">Tags</p>
                    <div className="flex flex-wrap gap-1">
                      {datasetQuery.data.tags.map((tag, i) => (
                        <span key={i} className="px-2 py-1 bg-slate-700 text-slate-300 text-xs rounded flex items-center gap-1">
                          <Tag className="w-3 h-3" />
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* RLS Info */}
            {datasetQuery.data.rls?.enabled && (
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4">
                <div className="flex items-center gap-2 text-amber-400 mb-2">
                  <Shield className="w-5 h-5" />
                  <span className="font-medium">Row-Level Security Enabled</span>
                </div>
                <p className="text-sm text-slate-400">
                  Filter column: <code className="bg-slate-800 px-1 rounded">{datasetQuery.data.rls.column}</code> | 
                  Mode: {datasetQuery.data.rls.mode}
                </p>
              </div>
            )}

            {/* Incremental Info */}
            {datasetQuery.data.incremental?.enabled && (
              <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
                <div className="flex items-center gap-2 text-blue-400 mb-2">
                  <Clock className="w-5 h-5" />
                  <span className="font-medium">Incremental Refresh</span>
                </div>
                <p className="text-sm text-slate-400">
                  Column: <code className="bg-slate-800 px-1 rounded">{datasetQuery.data.incremental.column}</code> | 
                  Mode: {datasetQuery.data.incremental.mode} | 
                  Window: {datasetQuery.data.incremental.maxWindowDays} days
                </p>
              </div>
            )}

            {/* Fields Table */}
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden">
              <div className="p-4 border-b border-slate-700">
                <h2 className="text-lg font-medium text-white flex items-center gap-2">
                  <Table2 className="w-5 h-5 text-indigo-400" />
                  Fields ({datasetQuery.data.fields?.length || 0})
                </h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-900/50">
                    <tr>
                      <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase">Name</th>
                      <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase">Type</th>
                      <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase">Semantic</th>
                      <th className="px-4 py-3 w-10"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700/50">
                    {datasetQuery.data.fields?.map((field, i) => (
                      <tr key={i} className="hover:bg-slate-800/50">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            {getFieldIcon(field.type)}
                            <span className="text-slate-200 font-mono text-sm">{field.name}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-slate-400 font-mono text-sm">{field.type}</span>
                        </td>
                        <td className="px-4 py-3">
                          {getSemanticBadge(field.semanticType)}
                        </td>
                        <td className="px-4 py-3">
                          <button
                            onClick={() => copyFieldName(field.name)}
                            className="p-1 hover:bg-slate-700 rounded transition-colors"
                            title="Copy field name"
                          >
                            {copiedField === field.name ? (
                              <Check className="w-4 h-4 text-emerald-400" />
                            ) : (
                              <Copy className="w-4 h-4 text-slate-500" />
                            )}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Dimensions */}
            {datasetQuery.data.dimensions && datasetQuery.data.dimensions.length > 0 && (
              <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
                <h3 className="text-sm font-medium text-slate-400 uppercase mb-3">
                  Dimensions ({datasetQuery.data.dimensions.length})
                </h3>
                <div className="space-y-1">
                  {datasetQuery.data.dimensions.map((dim, i) => (
                    <div key={i} className="flex items-center gap-2 py-1.5 px-2 bg-blue-500/10 rounded">
                      <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
                      <div className="flex-1">
                        <span className="text-sm text-blue-300">{dim.label}</span>
                        <span className="text-xs text-blue-400/60 ml-2 font-mono">{dim.field}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Metrics */}
            {datasetQuery.data.metrics && datasetQuery.data.metrics.length > 0 && (
              <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
                <h3 className="text-sm font-medium text-slate-400 uppercase mb-3">
                  Metrics ({datasetQuery.data.metrics.length})
                </h3>
                <div className="space-y-1">
                  {datasetQuery.data.metrics.map((metric, i) => (
                    <div key={i} className="flex items-center gap-2 py-1.5 px-2 bg-emerald-500/10 rounded">
                      <div className="w-2 h-2 bg-emerald-400 rounded-full"></div>
                      <div className="flex-1">
                        <span className="text-sm text-emerald-300">{metric.label}</span>
                        {metric.format && (
                          <span className="text-xs text-emerald-400/60 ml-2">({metric.format})</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Quick Actions */}
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
              <h3 className="text-sm font-medium text-slate-400 uppercase mb-3">Quick Actions</h3>
              <div className="space-y-2">
                <Link
                  to={`/playground?dataset=${id}`}
                  className="flex items-center gap-2 w-full px-3 py-2 bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-400 rounded-lg transition-colors text-sm"
                >
                  <Play className="w-4 h-4" />
                  Query Dataset
                </Link>
                <button className="flex items-center gap-2 w-full px-3 py-2 bg-slate-700/50 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors text-sm">
                  <FileText className="w-4 h-4" />
                  View Documentation
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
