/**
 * Query Workbench
 * 
 * SQL and Semantic Query interface:
 * - Raw SQL Editor with syntax highlighting
 * - Semantic Query Builder (select dimensions + measures)
 * - Results table and chart visualization
 * - Query history and execution stats
 */

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import Editor from '@monaco-editor/react';
import {
  Play,
  Code,
  Columns,
  Table2,
  BarChart3,
  Clock,
  AlertCircle,
  CheckCircle2,
  Loader2,
  ChevronDown,
  ChevronRight,
  ChevronLeft,
  X,
  Download,
  Copy,
  Hash,
  Type,
  Sigma,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { modelingApi } from '../../lib/modeling-api';
import { useModelingStore } from '../../store/modeling';
import type { QueryResult, SemanticQuery } from '../../types/modeling';
import { cn } from '../../lib/utils';

// ============================================================================
// MAIN COMPONENT
// ============================================================================

interface QueryWorkbenchProps {
  erdModelId: string;
  semanticModelId: string;
  sourceId: string;
}

export function QueryWorkbench({
  erdModelId,
  semanticModelId,
  sourceId,
}: QueryWorkbenchProps) {
  const {
    queryWorkbench,
    queryResult,
    isQueryRunning,
    queryError,
    getActiveSemantic,
    setQueryMode,
    setSqlText,
    setSelectedQueryDimensions,
    setSelectedQueryMeasures,
    setQueryActiveTab,
    setQueryResult,
    setQueryRunning,
    setQueryError,
    addToQueryHistory,
  } = useModelingStore();

  const [isQueryBuilderCollapsed, setIsQueryBuilderCollapsed] = useState(false);
  const semanticModel = getActiveSemantic();

  // Execute semantic query
  const semanticQueryMutation = useMutation({
    mutationFn: async () => {
      const dims = queryWorkbench.selectedDimensions || [];
      const meas = queryWorkbench.selectedMeasures || [];
      const query: SemanticQuery = {
        dimensions: dims,
        measures: meas,
        filters: [],
        sorts: [],
      };
      return modelingApi.executeSemanticQuery(erdModelId, semanticModelId, query);
    },
    onMutate: () => {
      setQueryRunning(true);
      setQueryError(null);
    },
    onSuccess: (result) => {
      setQueryResult(result);
      setQueryRunning(false);
      const dims = queryWorkbench.selectedDimensions || [];
      const meas = queryWorkbench.selectedMeasures || [];
      addToQueryHistory(
        `Semantic: ${dims.join(', ')} | ${meas.join(', ')}`,
        result.executionTimeMs
      );
    },
    onError: (error: Error) => {
      setQueryError(error.message);
      setQueryRunning(false);
    },
  });

  // Execute SQL query
  const sqlQueryMutation = useMutation({
    mutationFn: async () => {
      return modelingApi.executeRawSQL({
        sql: queryWorkbench.sqlText,
        sourceId,
      });
    },
    onMutate: () => {
      setQueryRunning(true);
      setQueryError(null);
    },
    onSuccess: (result) => {
      setQueryResult(result);
      setQueryRunning(false);
      addToQueryHistory(queryWorkbench.sqlText, result.executionTimeMs);
    },
    onError: (error: Error) => {
      setQueryError(error.message);
      setQueryRunning(false);
    },
  });

  const handleRun = () => {
    // Clear previous errors
    setQueryError(null);
    
    // Safe access to selectedDimensions and selectedMeasures
    const dims = queryWorkbench.selectedDimensions || [];
    const measures = queryWorkbench.selectedMeasures || [];
    
    if (queryWorkbench.mode === 'semantic') {
      // Validate semantic query requirements
      if (!erdModelId) {
        setQueryError('No ERD model selected. Please select an ERD model first.');
        return;
      }
      if (!semanticModelId) {
        setQueryError('No Semantic model selected. Please select a Semantic model first.');
        return;
      }
      if (dims.length === 0 && measures.length === 0) {
        setQueryError('Please select at least one dimension or measure to query.');
        return;
      }
      semanticQueryMutation.mutate();
    } else {
      // Validate SQL query
      if (!queryWorkbench.sqlText?.trim()) {
        setQueryError('Please enter a SQL query to execute.');
        return;
      }
      sqlQueryMutation.mutate();
    }
  };

  // Count selected items for display
  const selectedDims = queryWorkbench.selectedDimensions || [];
  const selectedMeas = queryWorkbench.selectedMeasures || [];

  return (
    <div className="h-full flex bg-slate-900 overflow-hidden">
      {/* LEFT PANEL: Query Builder (Dimensions/Measures or SQL Editor) */}
      {!isQueryBuilderCollapsed ? (
        <div className="w-64 flex-shrink-0 flex flex-col border-r border-slate-700 bg-slate-900">
          {/* Panel Header */}
          <div className="flex-shrink-0 flex items-center justify-between px-3 py-2 border-b border-slate-700 bg-slate-800/50">
            <div className="flex items-center gap-2">
              {/* Mode Toggle */}
              <div className="flex bg-slate-700/50 rounded p-0.5">
                <button
                  onClick={() => setQueryMode('semantic')}
                  className={cn(
                    'flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium transition-all',
                    queryWorkbench.mode === 'semantic'
                      ? 'bg-indigo-500 text-white'
                      : 'text-slate-400 hover:text-white'
                  )}
                >
                  <Columns className="w-3 h-3" />
                  Semantic
                </button>
                <button
                  onClick={() => setQueryMode('sql')}
                  className={cn(
                    'flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium transition-all',
                    queryWorkbench.mode === 'sql'
                      ? 'bg-indigo-500 text-white'
                      : 'text-slate-400 hover:text-white'
                  )}
                >
                  <Code className="w-3 h-3" />
                  SQL
                </button>
              </div>
            </div>
            <button
              onClick={() => setIsQueryBuilderCollapsed(true)}
              className="p-1 hover:bg-slate-700 rounded text-slate-400 hover:text-white transition-colors"
              title="Collapse Panel"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          </div>

          {/* Query Builder Content */}
          <div className="flex-1 overflow-auto">
            {queryWorkbench.mode === 'semantic' ? (
              <SemanticQueryBuilderVertical
                dimensions={semanticModel?.dimensions || []}
                measures={semanticModel?.measures || []}
                selectedDimensions={selectedDims}
                selectedMeasures={selectedMeas}
                onDimensionsChange={setSelectedQueryDimensions}
                onMeasuresChange={setSelectedQueryMeasures}
              />
            ) : (
              <SQLEditorPanel
                value={queryWorkbench.sqlText}
                onChange={setSqlText}
              />
            )}
          </div>

          {/* Run Button */}
          <div className="flex-shrink-0 p-2 border-t border-slate-700">
            <button
              onClick={handleRun}
              disabled={isQueryRunning}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
            >
              {isQueryRunning ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              Run Query
            </button>
          </div>
        </div>
      ) : (
        /* Collapsed Panel Toggle */
        <div className="w-10 flex-shrink-0 flex flex-col items-center py-2 border-r border-slate-700 bg-slate-900">
          <button
            onClick={() => setIsQueryBuilderCollapsed(false)}
            className="p-1.5 hover:bg-slate-700 rounded text-slate-400 hover:text-white transition-colors"
            title="Expand Query Builder"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
          <span className="text-xs text-slate-500 mt-2 [writing-mode:vertical-rl] rotate-180">
            Query
          </span>
          {(selectedDims.length > 0 || selectedMeas.length > 0) && (
            <div className="mt-2 flex flex-col items-center gap-1">
              {selectedDims.length > 0 && (
                <span className="w-5 h-5 flex items-center justify-center bg-blue-500/30 text-blue-300 rounded text-xs">
                  {selectedDims.length}
                </span>
              )}
              {selectedMeas.length > 0 && (
                <span className="w-5 h-5 flex items-center justify-center bg-indigo-500/30 text-indigo-300 rounded text-xs">
                  {selectedMeas.length}
                </span>
              )}
            </div>
          )}
        </div>
      )}

      {/* RIGHT PANEL: Results */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Results Header */}
        <div className="flex-shrink-0 flex items-center justify-between px-3 py-1.5 border-b border-slate-700 bg-slate-800/50">
          <div className="flex items-center gap-2">
            {queryResult && (
              <>
                <button
                  onClick={() => setQueryActiveTab('results')}
                  className={cn(
                    'flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-all',
                    queryWorkbench.activeTab === 'results'
                      ? 'bg-slate-700 text-white'
                      : 'text-slate-400 hover:text-white'
                  )}
                >
                  <Table2 className="w-3.5 h-3.5" />
                  Results
                </button>
                <button
                  onClick={() => setQueryActiveTab('chart')}
                  className={cn(
                    'flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-all',
                    queryWorkbench.activeTab === 'chart'
                      ? 'bg-slate-700 text-white'
                      : 'text-slate-400 hover:text-white'
                  )}
                >
                  <BarChart3 className="w-3.5 h-3.5" />
                  Chart
                </button>
                {queryResult.sql && (
                  <button
                    onClick={() => setQueryActiveTab('sql')}
                    className={cn(
                      'flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-all',
                      queryWorkbench.activeTab === 'sql'
                        ? 'bg-slate-700 text-white'
                        : 'text-slate-400 hover:text-white'
                    )}
                  >
                    <Code className="w-3.5 h-3.5" />
                    SQL
                  </button>
                )}
              </>
            )}
          </div>

          {/* Stats & Actions */}
          <div className="flex items-center gap-3">
            {queryResult && (
              <>
                <span className="text-xs text-slate-400 flex items-center gap-1">
                  <Table2 className="w-3.5 h-3.5" />
                  {queryResult.rowCount.toLocaleString()} rows
                </span>
                <span className="text-xs text-slate-400 flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  {queryResult.executionTimeMs.toFixed(0)}ms
                </span>
                <div className="flex items-center gap-1 border-l border-slate-600 pl-2">
                  <button
                    onClick={() => {
                      const csv = [
                        queryResult.columns.join(','),
                        ...queryResult.rows.map(row => 
                          queryResult.columns.map(col => JSON.stringify(row[col] ?? '')).join(',')
                        )
                      ].join('\n');
                      navigator.clipboard.writeText(csv);
                    }}
                    className="p-1 text-slate-400 hover:text-white hover:bg-slate-700 rounded transition-colors"
                    title="Copy as CSV"
                  >
                    <Copy className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => {
                      const csv = [
                        queryResult.columns.join(','),
                        ...queryResult.rows.map(row => 
                          queryResult.columns.map(col => JSON.stringify(row[col] ?? '')).join(',')
                        )
                      ].join('\n');
                      const blob = new Blob([csv], { type: 'text/csv' });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = 'query-results.csv';
                      a.click();
                    }}
                    className="p-1 text-slate-400 hover:text-white hover:bg-slate-700 rounded transition-colors"
                    title="Download CSV"
                  >
                    <Download className="w-3.5 h-3.5" />
                  </button>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Error Display */}
        {queryError && (
          <div className="flex-shrink-0 px-3 py-2 bg-red-500/10 border-b border-red-500/30 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
            <span className="text-xs text-red-400 break-all flex-1">{queryError}</span>
            <button 
              onClick={() => setQueryError(null)}
              className="text-red-400 hover:text-red-300"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Results Content */}
        <div className="flex-1 overflow-auto">
          {queryResult ? (
            <>
              {queryWorkbench.activeTab === 'results' && (
                <ResultsTable result={queryResult} />
              )}
              {queryWorkbench.activeTab === 'chart' && (
                <ResultsChart result={queryResult} />
              )}
              {queryWorkbench.activeTab === 'sql' && queryResult.sql && (
                <div className="p-3">
                  <pre className="p-3 bg-slate-800 rounded-lg text-xs text-slate-300 overflow-x-auto whitespace-pre-wrap">
                    {queryResult.sql}
                  </pre>
                </div>
              )}
            </>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-500">
              <div className="text-center">
                <Play className="w-10 h-10 mx-auto mb-3 opacity-30" />
                <p className="text-sm">Run a query to see results</p>
                <p className="text-xs text-slate-600 mt-1">
                  Select dimensions and measures, then click Run Query
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// VERTICAL SEMANTIC QUERY BUILDER (for left panel)
// ============================================================================

interface SemanticQueryBuilderVerticalProps {
  dimensions: { id: string; name: string }[];
  measures: { id: string; name: string }[];
  selectedDimensions: string[];
  selectedMeasures: string[];
  onDimensionsChange: (dims: string[]) => void;
  onMeasuresChange: (measures: string[]) => void;
}

function SemanticQueryBuilderVertical({
  dimensions,
  measures,
  selectedDimensions,
  selectedMeasures,
  onDimensionsChange,
  onMeasuresChange,
}: SemanticQueryBuilderVerticalProps) {
  const [expandDimensions, setExpandDimensions] = useState(true);
  const [expandMeasures, setExpandMeasures] = useState(true);
  
  const safeDimensions = selectedDimensions || [];
  const safeMeasures = selectedMeasures || [];
  
  const toggleDimension = (name: string) => {
    if (safeDimensions.includes(name)) {
      onDimensionsChange(safeDimensions.filter((d) => d !== name));
    } else {
      onDimensionsChange([...safeDimensions, name]);
    }
  };

  const toggleMeasure = (name: string) => {
    if (safeMeasures.includes(name)) {
      onMeasuresChange(safeMeasures.filter((m) => m !== name));
    } else {
      onMeasuresChange([...safeMeasures, name]);
    }
  };

  return (
    <div className="p-2 space-y-2">
      {/* Dimensions Section */}
      <div className="bg-slate-800/50 rounded-lg overflow-hidden">
        <button
          onClick={() => setExpandDimensions(!expandDimensions)}
          className="w-full flex items-center justify-between px-3 py-2 hover:bg-slate-700/50 transition-colors"
        >
          <span className="flex items-center gap-2 text-xs font-medium text-slate-300">
            <Columns className="w-3.5 h-3.5 text-blue-400" />
            Dimensions
            {safeDimensions.length > 0 && (
              <span className="px-1.5 py-0.5 bg-blue-500/30 text-blue-300 rounded text-xs">
                {safeDimensions.length}
              </span>
            )}
          </span>
          <ChevronDown className={cn(
            "w-4 h-4 text-slate-400 transition-transform",
            !expandDimensions && "-rotate-90"
          )} />
        </button>
        
        {expandDimensions && (
          <div className="px-2 pb-2 space-y-1 max-h-40 overflow-y-auto">
            {dimensions.map((dim) => (
              <button
                key={dim.id}
                onClick={() => toggleDimension(dim.name)}
                className={cn(
                  'w-full flex items-center gap-2 px-2 py-1.5 rounded text-xs transition-all text-left',
                  safeDimensions.includes(dim.name)
                    ? 'bg-blue-500/20 text-blue-200 ring-1 ring-blue-500/40'
                    : 'hover:bg-slate-700/50 text-slate-400 hover:text-slate-200'
                )}
              >
                <div className={cn(
                  'w-3 h-3 rounded-sm border flex items-center justify-center flex-shrink-0',
                  safeDimensions.includes(dim.name)
                    ? 'bg-blue-500 border-blue-500'
                    : 'border-slate-600'
                )}>
                  {safeDimensions.includes(dim.name) && (
                    <CheckCircle2 className="w-2 h-2 text-white" />
                  )}
                </div>
                <Type className="w-3 h-3 text-slate-500 flex-shrink-0" />
                <span className="truncate">{dim.name}</span>
              </button>
            ))}
            {dimensions.length === 0 && (
              <p className="text-xs text-slate-500 text-center py-2">No dimensions</p>
            )}
          </div>
        )}
      </div>

      {/* Measures Section */}
      <div className="bg-slate-800/50 rounded-lg overflow-hidden">
        <button
          onClick={() => setExpandMeasures(!expandMeasures)}
          className="w-full flex items-center justify-between px-3 py-2 hover:bg-slate-700/50 transition-colors"
        >
          <span className="flex items-center gap-2 text-xs font-medium text-slate-300">
            <Sigma className="w-3.5 h-3.5 text-indigo-400" />
            Measures
            {safeMeasures.length > 0 && (
              <span className="px-1.5 py-0.5 bg-indigo-500/30 text-indigo-300 rounded text-xs">
                {safeMeasures.length}
              </span>
            )}
          </span>
          <ChevronDown className={cn(
            "w-4 h-4 text-slate-400 transition-transform",
            !expandMeasures && "-rotate-90"
          )} />
        </button>
        
        {expandMeasures && (
          <div className="px-2 pb-2 space-y-1 max-h-40 overflow-y-auto">
            {measures.map((measure) => (
              <button
                key={measure.id}
                onClick={() => toggleMeasure(measure.name)}
                className={cn(
                  'w-full flex items-center gap-2 px-2 py-1.5 rounded text-xs transition-all text-left',
                  safeMeasures.includes(measure.name)
                    ? 'bg-indigo-500/20 text-indigo-200 ring-1 ring-indigo-500/40'
                    : 'hover:bg-slate-700/50 text-slate-400 hover:text-slate-200'
                )}
              >
                <div className={cn(
                  'w-3 h-3 rounded-sm border flex items-center justify-center flex-shrink-0',
                  safeMeasures.includes(measure.name)
                    ? 'bg-indigo-500 border-indigo-500'
                    : 'border-slate-600'
                )}>
                  {safeMeasures.includes(measure.name) && (
                    <CheckCircle2 className="w-2 h-2 text-white" />
                  )}
                </div>
                <Hash className="w-3 h-3 text-slate-500 flex-shrink-0" />
                <span className="truncate">{measure.name}</span>
              </button>
            ))}
            {measures.length === 0 && (
              <p className="text-xs text-slate-500 text-center py-2">No measures</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// SQL EDITOR PANEL (for left panel)
// ============================================================================

interface SQLEditorPanelProps {
  value: string;
  onChange: (value: string) => void;
}

function SQLEditorPanel({ value, onChange }: SQLEditorPanelProps) {
  return (
    <div className="h-full">
      <Editor
        height="100%"
        language="sql"
        value={value}
        onChange={(v) => onChange(v || '')}
        theme="vs-dark"
        options={{
          minimap: { enabled: false },
          fontSize: 12,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          wordWrap: 'on',
          padding: { top: 8, bottom: 8 },
          suggestOnTriggerCharacters: true,
          lineHeight: 18,
          folding: false,
          glyphMargin: false,
          lineDecorationsWidth: 0,
          lineNumbersMinChars: 3,
        }}
      />
    </div>
  );
}


// ============================================================================
// RESULTS TABLE
// ============================================================================

interface ResultsTableProps {
  result: QueryResult;
}

function ResultsTable({ result }: ResultsTableProps) {
  const [copiedRow, setCopiedRow] = useState<number | null>(null);

  const copyRow = (index: number) => {
    const row = result.rows[index];
    navigator.clipboard.writeText(JSON.stringify(row, null, 2));
    setCopiedRow(index);
    setTimeout(() => setCopiedRow(null), 1500);
  };

  if (result.rows.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-slate-500 text-sm">
        No results returned
      </div>
    );
  }

  return (
    <div className="overflow-auto h-full">
      <table className="w-full text-xs">
        <thead className="bg-slate-800/80 sticky top-0 z-10">
          <tr>
            <th className="px-2 py-1.5 text-left font-medium text-slate-400 w-8 border-b border-slate-700">#</th>
            {result.columns.map((col) => (
              <th
                key={col}
                className="px-2 py-1.5 text-left font-medium text-slate-400 border-b border-slate-700 whitespace-nowrap"
              >
                {col}
              </th>
            ))}
            <th className="px-2 py-1.5 w-8 border-b border-slate-700"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {result.rows.map((row, i) => (
            <tr
              key={i}
              className="hover:bg-slate-800/50 transition-colors"
            >
              <td className="px-2 py-1 text-slate-500 font-mono">{i + 1}</td>
              {result.columns.map((col) => (
                <td key={col} className="px-2 py-1 text-slate-300 max-w-[200px] truncate" title={String(row[col] ?? '')}>
                  {formatCellValue(row[col])}
                </td>
              ))}
              <td className="px-2 py-1">
                <button
                  onClick={() => copyRow(i)}
                  className="p-0.5 hover:bg-slate-700 rounded opacity-40 hover:opacity-100 transition-opacity"
                  title="Copy row as JSON"
                >
                  {copiedRow === i ? (
                    <CheckCircle2 className="w-3 h-3 text-green-400" />
                  ) : (
                    <Copy className="w-3 h-3 text-slate-400" />
                  )}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ============================================================================
// RESULTS CHART
// ============================================================================

interface ResultsChartProps {
  result: QueryResult;
}

function ResultsChart({ result }: ResultsChartProps) {
  const [chartType, setChartType] = useState<'bar' | 'line'>('bar');

  // Determine dimension and measure columns
  const dimensionCols = result.columns.filter(
    (col) => typeof result.rows[0]?.[col] === 'string'
  );
  const measureCols = result.columns.filter(
    (col) => typeof result.rows[0]?.[col] === 'number'
  );

  const xAxisKey = dimensionCols[0] || result.columns[0];

  if (measureCols.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-slate-500 text-sm">
        No numeric data to chart
      </div>
    );
  }

  const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

  return (
    <div className="p-3 h-full flex flex-col">
      {/* Chart Type Toggle - Compact */}
      <div className="flex justify-end mb-2 flex-shrink-0">
        <div className="flex bg-slate-800 rounded p-0.5">
          <button
            onClick={() => setChartType('bar')}
            className={cn(
              'px-2 py-0.5 rounded text-xs',
              chartType === 'bar' ? 'bg-slate-700 text-white' : 'text-slate-400'
            )}
          >
            Bar
          </button>
          <button
            onClick={() => setChartType('line')}
            className={cn(
              'px-2 py-0.5 rounded text-xs',
              chartType === 'line' ? 'bg-slate-700 text-white' : 'text-slate-400'
            )}
          >
            Line
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          {chartType === 'bar' ? (
            <BarChart data={result.rows} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                dataKey={xAxisKey}
                stroke="#94a3b8"
                tick={{ fill: '#94a3b8', fontSize: 10 }}
                tickLine={{ stroke: '#475569' }}
              />
              <YAxis 
                stroke="#94a3b8" 
                tick={{ fill: '#94a3b8', fontSize: 10 }}
                tickLine={{ stroke: '#475569' }}
                width={50}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '6px',
                  fontSize: '11px',
                  padding: '6px 10px',
                }}
                labelStyle={{ color: '#fff', marginBottom: '4px' }}
              />
              <Legend 
                wrapperStyle={{ fontSize: '11px' }}
                iconSize={10}
              />
              {measureCols.map((col, i) => (
                <Bar
                  key={col}
                  dataKey={col}
                  fill={COLORS[i % COLORS.length]}
                  radius={[3, 3, 0, 0]}
                />
              ))}
            </BarChart>
          ) : (
            <LineChart data={result.rows} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                dataKey={xAxisKey}
                stroke="#94a3b8"
                tick={{ fill: '#94a3b8', fontSize: 10 }}
                tickLine={{ stroke: '#475569' }}
              />
              <YAxis 
                stroke="#94a3b8" 
                tick={{ fill: '#94a3b8', fontSize: 10 }}
                tickLine={{ stroke: '#475569' }}
                width={50}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '6px',
                  fontSize: '11px',
                  padding: '6px 10px',
                }}
                labelStyle={{ color: '#fff', marginBottom: '4px' }}
              />
              <Legend 
                wrapperStyle={{ fontSize: '11px' }}
                iconSize={10}
              />
              {measureCols.map((col, i) => (
                <Line
                  key={col}
                  type="monotone"
                  dataKey={col}
                  stroke={COLORS[i % COLORS.length]}
                  strokeWidth={2}
                  dot={{ fill: COLORS[i % COLORS.length], r: 3 }}
                />
              ))}
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ============================================================================
// HELPERS
// ============================================================================

function formatCellValue(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'number') {
    return value.toLocaleString();
  }
  if (typeof value === 'boolean') {
    return value ? '✓' : '✗';
  }
  return String(value);
}

