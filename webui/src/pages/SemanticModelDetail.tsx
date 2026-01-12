/**
 * Semantic Model Detail Page
 * 
 * Shows full details of a semantic model created in Modeling Studio.
 */

import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  Boxes, 
  ArrowLeft, 
  RefreshCw, 
  Loader2, 
  XCircle,
  Hash,
  Calendar,
  Type,
  ToggleLeft,
  Play,
  Copy,
  Check,
  FileText,
  Edit3,
  Tag,
  Ruler,
  Calculator,
  ChevronDown,
  ChevronRight,
  Server,
  Layers
} from 'lucide-react';
import { useState } from 'react';
import { modelingApi } from '../lib/modeling-api';

interface Dimension {
  id: string;
  name: string;
  type?: string;
  dimensionType?: string;
  sourceTable?: string;
  sourceColumn?: string;
  description?: string;
}

interface Measure {
  id: string;
  name: string;
  aggregation?: string;
  expression?: string;
  sourceTable?: string;
  sourceColumn?: string;
  description?: string;
}

interface CalculatedField {
  id: string;
  name: string;
  expression: string;
  returnType?: string;
  description?: string;
}

interface SemanticModel {
  id: string;
  name: string;
  description?: string;
  sourceId?: string;
  erdModelId?: string;
  dimensions: Dimension[];
  measures: Measure[];
  calculatedFields: CalculatedField[];
  createdAt?: string;
  updatedAt?: string;
}

export default function SemanticModelDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['dimensions', 'measures', 'calculated'])
  );

  // Fetch semantic model details
  const modelQuery = useQuery({
    queryKey: ['semantic-model-detail', id],
    queryFn: async () => {
      if (!id) throw new Error('Model ID required');
      const model = await modelingApi.getSemanticModel(id);
      return model as SemanticModel;
    },
    enabled: !!id,
  });

  // Fetch source info if available
  const sourceQuery = useQuery({
    queryKey: ['source-info', modelQuery.data?.sourceId],
    queryFn: async () => {
      if (!modelQuery.data?.sourceId || modelQuery.data.sourceId === 'demo') {
        return { name: 'Demo Source', type: 'duckdb' };
      }
      const sources = await modelingApi.listSources();
      return sources.find(s => s.id === modelQuery.data?.sourceId) || null;
    },
    enabled: !!modelQuery.data?.sourceId,
  });

  const copyFieldName = (fieldName: string) => {
    navigator.clipboard.writeText(fieldName);
    setCopiedField(fieldName);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
  };

  const getDimensionIcon = (type?: string) => {
    const typeLower = (type || 'string').toLowerCase();
    if (typeLower.includes('number') || typeLower.includes('int') || typeLower.includes('float')) {
      return <Hash className="w-4 h-4 text-blue-400" />;
    }
    if (typeLower.includes('time') || typeLower.includes('date')) {
      return <Calendar className="w-4 h-4 text-purple-400" />;
    }
    if (typeLower.includes('bool')) {
      return <ToggleLeft className="w-4 h-4 text-orange-400" />;
    }
    return <Type className="w-4 h-4 text-blue-400" />;
  };

  const getDimensionTypeBadge = (type?: string) => {
    const badges: Record<string, { bg: string; text: string }> = {
      string: { bg: 'bg-blue-500/20', text: 'text-blue-400' },
      number: { bg: 'bg-emerald-500/20', text: 'text-emerald-400' },
      time: { bg: 'bg-purple-500/20', text: 'text-purple-400' },
      date: { bg: 'bg-purple-500/20', text: 'text-purple-400' },
      boolean: { bg: 'bg-orange-500/20', text: 'text-orange-400' },
      geo: { bg: 'bg-pink-500/20', text: 'text-pink-400' },
    };
    const displayType = type || 'string';
    const style = badges[displayType.toLowerCase()] || badges.string;
    return (
      <span className={`px-1.5 py-0.5 ${style.bg} ${style.text} text-xs rounded`}>
        {displayType}
      </span>
    );
  };

  const getAggregationBadge = (agg?: string) => {
    const badges: Record<string, { bg: string; text: string }> = {
      sum: { bg: 'bg-emerald-500/20', text: 'text-emerald-400' },
      avg: { bg: 'bg-blue-500/20', text: 'text-blue-400' },
      count: { bg: 'bg-purple-500/20', text: 'text-purple-400' },
      min: { bg: 'bg-orange-500/20', text: 'text-orange-400' },
      max: { bg: 'bg-red-500/20', text: 'text-red-400' },
      count_distinct: { bg: 'bg-pink-500/20', text: 'text-pink-400' },
    };
    const displayAgg = agg || 'custom';
    const style = badges[displayAgg.toLowerCase()] || { bg: 'bg-slate-500/20', text: 'text-slate-400' };
    return (
      <span className={`px-1.5 py-0.5 ${style.bg} ${style.text} text-xs rounded uppercase`}>
        {displayAgg}
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
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-purple-500/20 rounded-xl flex items-center justify-center">
              <Boxes className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-white">
                {modelQuery.data?.name || 'Semantic Model'}
              </h1>
              <p className="text-slate-400">
                {modelQuery.data?.description || 'Created in Modeling Studio'}
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button 
            onClick={() => modelQuery.refetch()}
            disabled={modelQuery.isFetching}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <RefreshCw className={`w-5 h-5 text-slate-400 ${modelQuery.isFetching ? 'animate-spin' : ''}`} />
          </button>
          <Link
            to="/modeling"
            className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          >
            <Edit3 className="w-4 h-4" />
            Edit in Studio
          </Link>
          <Link
            to={`/contracts`}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-colors"
          >
            <FileText className="w-4 h-4" />
            View Contract
          </Link>
        </div>
      </div>

      {/* Loading State */}
      {modelQuery.isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
        </div>
      )}

      {/* Error State */}
      {modelQuery.isError && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-center">
          <XCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-red-400 mb-2">Failed to Load Model</h3>
          <p className="text-sm text-slate-400 mb-4">
            {(modelQuery.error as Error)?.message || 'Model not found'}
          </p>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={() => modelQuery.refetch()}
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

      {/* Model Content */}
      {modelQuery.isSuccess && modelQuery.data && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Overview Card */}
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
              <h2 className="text-lg font-medium text-white mb-4 flex items-center gap-2">
                <Layers className="w-5 h-5 text-indigo-400" />
                Overview
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 text-center">
                  <p className="text-3xl font-bold text-blue-400">{modelQuery.data.dimensions?.length || 0}</p>
                  <p className="text-xs text-blue-300 uppercase mt-1">Dimensions</p>
                </div>
                <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-4 text-center">
                  <p className="text-3xl font-bold text-emerald-400">{modelQuery.data.measures?.length || 0}</p>
                  <p className="text-xs text-emerald-300 uppercase mt-1">Measures</p>
                </div>
                <div className="bg-orange-500/10 border border-orange-500/20 rounded-lg p-4 text-center">
                  <p className="text-3xl font-bold text-orange-400">{modelQuery.data.calculatedFields?.length || 0}</p>
                  <p className="text-xs text-orange-300 uppercase mt-1">Calculated</p>
                </div>
                <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-4 text-center">
                  <p className="text-3xl font-bold text-purple-400">
                    {(modelQuery.data.dimensions?.length || 0) + 
                     (modelQuery.data.measures?.length || 0) + 
                     (modelQuery.data.calculatedFields?.length || 0)}
                  </p>
                  <p className="text-xs text-purple-300 uppercase mt-1">Total Fields</p>
                </div>
              </div>
            </div>

            {/* Dimensions Section */}
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden">
              <button
                onClick={() => toggleSection('dimensions')}
                className="w-full flex items-center justify-between p-4 hover:bg-slate-700/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Ruler className="w-5 h-5 text-blue-400" />
                  <h2 className="text-lg font-medium text-white">
                    Dimensions ({modelQuery.data.dimensions?.length || 0})
                  </h2>
                </div>
                {expandedSections.has('dimensions') ? (
                  <ChevronDown className="w-5 h-5 text-slate-400" />
                ) : (
                  <ChevronRight className="w-5 h-5 text-slate-400" />
                )}
              </button>
              {expandedSections.has('dimensions') && modelQuery.data.dimensions && modelQuery.data.dimensions.length > 0 && (
                <div className="border-t border-slate-700">
                  <table className="w-full">
                    <thead className="bg-slate-900/50">
                      <tr>
                        <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase">Name</th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase">Type</th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase">Source</th>
                        <th className="px-4 py-3 w-10"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-700/50">
                      {modelQuery.data.dimensions.map((dim) => (
                        <tr key={dim.id} className="hover:bg-slate-800/50">
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              {getDimensionIcon(dim.type || dim.dimensionType)}
                              <span className="text-slate-200">{dim.name}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            {getDimensionTypeBadge(dim.type || dim.dimensionType)}
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-slate-400 font-mono text-sm">
                              {dim.sourceTable && dim.sourceColumn 
                                ? `${dim.sourceTable}.${dim.sourceColumn}`
                                : dim.sourceColumn || '-'}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <button
                              onClick={() => copyFieldName(dim.name)}
                              className="p-1 hover:bg-slate-700 rounded transition-colors"
                              title="Copy name"
                            >
                              {copiedField === dim.name ? (
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
              )}
              {expandedSections.has('dimensions') && (!modelQuery.data.dimensions || modelQuery.data.dimensions.length === 0) && (
                <div className="p-8 text-center text-slate-500 border-t border-slate-700">
                  No dimensions defined
                </div>
              )}
            </div>

            {/* Measures Section */}
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden">
              <button
                onClick={() => toggleSection('measures')}
                className="w-full flex items-center justify-between p-4 hover:bg-slate-700/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Hash className="w-5 h-5 text-emerald-400" />
                  <h2 className="text-lg font-medium text-white">
                    Measures ({modelQuery.data.measures?.length || 0})
                  </h2>
                </div>
                {expandedSections.has('measures') ? (
                  <ChevronDown className="w-5 h-5 text-slate-400" />
                ) : (
                  <ChevronRight className="w-5 h-5 text-slate-400" />
                )}
              </button>
              {expandedSections.has('measures') && modelQuery.data.measures && modelQuery.data.measures.length > 0 && (
                <div className="border-t border-slate-700">
                  <table className="w-full">
                    <thead className="bg-slate-900/50">
                      <tr>
                        <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase">Name</th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase">Aggregation</th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase">Expression</th>
                        <th className="px-4 py-3 w-10"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-700/50">
                      {modelQuery.data.measures.map((measure) => (
                        <tr key={measure.id} className="hover:bg-slate-800/50">
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <Hash className="w-4 h-4 text-emerald-400" />
                              <span className="text-slate-200">{measure.name}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            {getAggregationBadge(measure.aggregation)}
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-slate-400 font-mono text-sm truncate max-w-xs block">
                              {measure.expression || 
                               (measure.sourceTable && measure.sourceColumn 
                                ? `${measure.aggregation}(${measure.sourceTable}.${measure.sourceColumn})`
                                : measure.sourceColumn 
                                  ? `${measure.aggregation}(${measure.sourceColumn})`
                                  : '-')}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <button
                              onClick={() => copyFieldName(measure.name)}
                              className="p-1 hover:bg-slate-700 rounded transition-colors"
                              title="Copy name"
                            >
                              {copiedField === measure.name ? (
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
              )}
              {expandedSections.has('measures') && (!modelQuery.data.measures || modelQuery.data.measures.length === 0) && (
                <div className="p-8 text-center text-slate-500 border-t border-slate-700">
                  No measures defined
                </div>
              )}
            </div>

            {/* Calculated Fields Section */}
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden">
              <button
                onClick={() => toggleSection('calculated')}
                className="w-full flex items-center justify-between p-4 hover:bg-slate-700/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Calculator className="w-5 h-5 text-orange-400" />
                  <h2 className="text-lg font-medium text-white">
                    Calculated Fields ({modelQuery.data.calculatedFields?.length || 0})
                  </h2>
                </div>
                {expandedSections.has('calculated') ? (
                  <ChevronDown className="w-5 h-5 text-slate-400" />
                ) : (
                  <ChevronRight className="w-5 h-5 text-slate-400" />
                )}
              </button>
              {expandedSections.has('calculated') && modelQuery.data.calculatedFields && modelQuery.data.calculatedFields.length > 0 && (
                <div className="border-t border-slate-700">
                  <table className="w-full">
                    <thead className="bg-slate-900/50">
                      <tr>
                        <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase">Name</th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase">Expression</th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase">Return Type</th>
                        <th className="px-4 py-3 w-10"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-700/50">
                      {modelQuery.data.calculatedFields.map((cf) => (
                        <tr key={cf.id} className="hover:bg-slate-800/50">
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <Calculator className="w-4 h-4 text-orange-400" />
                              <span className="text-slate-200">{cf.name}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <code className="text-orange-300 font-mono text-sm bg-slate-900/50 px-2 py-1 rounded block truncate max-w-md">
                              {cf.expression}
                            </code>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-slate-400 text-sm">{cf.returnType || 'auto'}</span>
                          </td>
                          <td className="px-4 py-3">
                            <button
                              onClick={() => copyFieldName(cf.name)}
                              className="p-1 hover:bg-slate-700 rounded transition-colors"
                              title="Copy name"
                            >
                              {copiedField === cf.name ? (
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
              )}
              {expandedSections.has('calculated') && (!modelQuery.data.calculatedFields || modelQuery.data.calculatedFields.length === 0) && (
                <div className="p-8 text-center text-slate-500 border-t border-slate-700">
                  No calculated fields defined
                </div>
              )}
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Source Info */}
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
              <h3 className="text-sm font-medium text-slate-400 uppercase mb-3 flex items-center gap-2">
                <Server className="w-4 h-4" />
                Data Source
              </h3>
              <div className="space-y-3">
                <div>
                  <p className="text-xs text-slate-500">Source Name</p>
                  <p className="text-slate-200">{sourceQuery.data?.name || modelQuery.data.sourceId || 'Unknown'}</p>
                </div>
                {sourceQuery.data?.type && (
                  <div>
                    <p className="text-xs text-slate-500">Type</p>
                    <p className="text-slate-200 uppercase">{sourceQuery.data.type}</p>
                  </div>
                )}
                {modelQuery.data.erdModelId && (
                  <div>
                    <p className="text-xs text-slate-500">ERD Model</p>
                    <p className="text-slate-400 font-mono text-xs truncate">{modelQuery.data.erdModelId}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Metadata */}
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
              <h3 className="text-sm font-medium text-slate-400 uppercase mb-3 flex items-center gap-2">
                <Tag className="w-4 h-4" />
                Metadata
              </h3>
              <div className="space-y-3">
                <div>
                  <p className="text-xs text-slate-500">Model ID</p>
                  <p className="text-slate-400 font-mono text-xs break-all">{modelQuery.data.id}</p>
                </div>
                {modelQuery.data.createdAt && (
                  <div>
                    <p className="text-xs text-slate-500">Created</p>
                    <p className="text-slate-200">{new Date(modelQuery.data.createdAt).toLocaleString()}</p>
                  </div>
                )}
                {modelQuery.data.updatedAt && (
                  <div>
                    <p className="text-xs text-slate-500">Updated</p>
                    <p className="text-slate-200">{new Date(modelQuery.data.updatedAt).toLocaleString()}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Quick Actions */}
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
              <h3 className="text-sm font-medium text-slate-400 uppercase mb-3">Quick Actions</h3>
              <div className="space-y-2">
                <Link
                  to="/modeling"
                  className="flex items-center gap-2 w-full px-3 py-2 bg-purple-500/20 hover:bg-purple-500/30 text-purple-400 rounded-lg transition-colors text-sm"
                >
                  <Edit3 className="w-4 h-4" />
                  Edit in Modeling Studio
                </Link>
                <Link
                  to="/contracts"
                  className="flex items-center gap-2 w-full px-3 py-2 bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-400 rounded-lg transition-colors text-sm"
                >
                  <FileText className="w-4 h-4" />
                  View/Edit Contract
                </Link>
                <Link
                  to="/modeling"
                  className="flex items-center gap-2 w-full px-3 py-2 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 rounded-lg transition-colors text-sm"
                >
                  <Play className="w-4 h-4" />
                  Run Query
                </Link>
              </div>
            </div>

            {/* Field Summary */}
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
              <h3 className="text-sm font-medium text-slate-400 uppercase mb-3">Field Summary</h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">String dimensions</span>
                  <span className="text-slate-200">
                    {modelQuery.data.dimensions?.filter(d => 
                      (d.type || d.dimensionType || 'string').toLowerCase() === 'string'
                    ).length || 0}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">Time dimensions</span>
                  <span className="text-slate-200">
                    {modelQuery.data.dimensions?.filter(d => 
                      ['time', 'date'].includes((d.type || d.dimensionType || '').toLowerCase())
                    ).length || 0}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">Numeric dimensions</span>
                  <span className="text-slate-200">
                    {modelQuery.data.dimensions?.filter(d => 
                      (d.type || d.dimensionType || '').toLowerCase() === 'number'
                    ).length || 0}
                  </span>
                </div>
                <hr className="border-slate-700" />
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">SUM measures</span>
                  <span className="text-slate-200">
                    {modelQuery.data.measures?.filter(m => 
                      (m.aggregation || '').toLowerCase() === 'sum'
                    ).length || 0}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">COUNT measures</span>
                  <span className="text-slate-200">
                    {modelQuery.data.measures?.filter(m => 
                      (m.aggregation || '').toLowerCase().includes('count')
                    ).length || 0}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">AVG measures</span>
                  <span className="text-slate-200">
                    {modelQuery.data.measures?.filter(m => 
                      (m.aggregation || '').toLowerCase() === 'avg'
                    ).length || 0}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

