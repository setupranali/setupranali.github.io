import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  Save, 
  RefreshCw, 
  AlertCircle, 
  CheckCircle,
  Loader2,
  Eye,
  Code,
  Download,
  Upload,
  Copy,
  Check
} from 'lucide-react';
import Editor from '@monaco-editor/react';
import axios from 'axios';

const API_BASE = 'http://localhost:8080';

interface CatalogData {
  content: string;
  lastModified?: string;
}

interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export default function CatalogEditor() {
  const queryClient = useQueryClient();
  const [content, setContent] = useState<string>('');
  const [hasChanges, setHasChanges] = useState(false);
  const [viewMode, setViewMode] = useState<'edit' | 'preview'>('edit');
  const [copied, setCopied] = useState(false);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);

  // Fetch catalog content
  const catalogQuery = useQuery({
    queryKey: ['catalog'],
    queryFn: async () => {
      try {
        const response = await axios.get<CatalogData>(`${API_BASE}/v1/catalog`);
        return response.data;
      } catch (error) {
        // If endpoint doesn't exist, return default content
        return {
          content: `# Universal BI Catalog Configuration
# Define your semantic datasets here

datasets:
  - id: orders
    name: Orders
    description: Order-level facts
    tags:
      - sales
      - demo
    defaultTimezone: "Asia/Kolkata"
    
    source:
      engine: duckdb
      type: table
      reference: orders
    
    incremental:
      enabled: true
      column: order_date
      type: date
      mode: append
      maxWindowDays: 90
    
    rls:
      enabled: true
      column: tenant_id
      mode: equals
      allowAdminBypass: true
    
    fields:
      - name: order_id
        type: string
        semanticType: identifier
      - name: tenant_id
        type: string
        semanticType: dimension
      - name: order_date
        type: date
        semanticType: time
      - name: city
        type: string
        semanticType: geo_city
      - name: revenue
        type: double
        semanticType: metric
      - name: qty
        type: int64
        semanticType: metric
    
    dimensions:
      - name: order_date
        field: order_date
        label: Order Date
      - name: city
        field: city
        label: City
    
    metrics:
      - name: total_revenue
        label: Total Revenue
        expression:
          type: aggregation
          agg: sum
          field: revenue
        returnType: double
        format: currency
      - name: orders_count
        label: Orders
        expression:
          type: aggregation
          agg: count
          field: order_id
        returnType: int64
`,
          lastModified: new Date().toISOString()
        };
      }
    },
  });

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: async (yamlContent: string) => {
      const response = await axios.put(`${API_BASE}/v1/catalog`, { content: yamlContent });
      return response.data;
    },
    onSuccess: () => {
      setHasChanges(false);
      queryClient.invalidateQueries({ queryKey: ['catalog'] });
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
  });

  // Validate mutation
  const validateMutation = useMutation({
    mutationFn: async (yamlContent: string) => {
      try {
        const response = await axios.post<ValidationResult>(`${API_BASE}/v1/catalog/validate`, { content: yamlContent });
        return response.data;
      } catch (error) {
        // Simple client-side validation if endpoint doesn't exist
        const result: ValidationResult = { valid: true, errors: [], warnings: [] };
        
        // Check for basic YAML structure
        if (!yamlContent.includes('datasets:')) {
          result.valid = false;
          result.errors.push('Missing "datasets:" section');
        }
        
        // Check for common issues
        const lines = yamlContent.split('\n');
        lines.forEach((line, index) => {
          if (line.includes('\t')) {
            result.warnings.push(`Line ${index + 1}: Tab characters detected. Use spaces for YAML indentation.`);
          }
        });
        
        return result;
      }
    },
    onSuccess: (data) => {
      setValidationResult(data);
    },
  });

  // Initialize content from query
  useEffect(() => {
    if (catalogQuery.data?.content && !content) {
      setContent(catalogQuery.data.content);
    }
  }, [catalogQuery.data, content]);

  const handleEditorChange = (value: string | undefined) => {
    if (value !== undefined) {
      setContent(value);
      setHasChanges(value !== catalogQuery.data?.content);
      setValidationResult(null);
    }
  };

  const handleSave = () => {
    saveMutation.mutate(content);
  };

  const handleValidate = () => {
    validateMutation.mutate(content);
  };

  const handleReset = () => {
    if (catalogQuery.data?.content) {
      setContent(catalogQuery.data.content);
      setHasChanges(false);
      setValidationResult(null);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([content], { type: 'text/yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'catalog.yaml';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleUpload = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.yaml,.yml';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
          const text = e.target?.result as string;
          setContent(text);
          setHasChanges(true);
        };
        reader.readAsText(file);
      }
    };
    input.click();
  };

  return (
    <div className="p-6 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-semibold text-white">Catalog Editor</h1>
          <p className="text-slate-400">
            Edit semantic dataset definitions
            {catalogQuery.data?.lastModified && (
              <span className="ml-2 text-slate-500">
                · Last modified: {new Date(catalogQuery.data.lastModified).toLocaleString()}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => catalogQuery.refetch()}
            disabled={catalogQuery.isFetching}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-5 h-5 text-slate-400 ${catalogQuery.isFetching ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={handleValidate}
            disabled={validateMutation.isPending}
            className="flex items-center gap-2 px-3 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          >
            {validateMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <CheckCircle className="w-4 h-4" />
            )}
            Validate
          </button>
          <button
            onClick={handleSave}
            disabled={!hasChanges || saveMutation.isPending}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              hasChanges
                ? 'bg-indigo-500 hover:bg-indigo-600 text-white'
                : 'bg-slate-700 text-slate-400 cursor-not-allowed'
            }`}
          >
            {saveMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            Save Changes
          </button>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          {/* View Mode Toggle */}
          <div className="flex bg-slate-800 rounded-lg p-1">
            <button
              onClick={() => setViewMode('edit')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                viewMode === 'edit'
                  ? 'bg-slate-700 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Code className="w-4 h-4" />
              Edit
            </button>
            <button
              onClick={() => setViewMode('preview')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                viewMode === 'preview'
                  ? 'bg-slate-700 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Eye className="w-4 h-4" />
              Preview
            </button>
          </div>

          {hasChanges && (
            <button
              onClick={handleReset}
              className="text-sm text-slate-400 hover:text-white transition-colors"
            >
              Discard changes
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
            title="Copy to clipboard"
          >
            {copied ? (
              <Check className="w-4 h-4 text-emerald-400" />
            ) : (
              <Copy className="w-4 h-4 text-slate-400" />
            )}
          </button>
          <button
            onClick={handleDownload}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
            title="Download YAML"
          >
            <Download className="w-4 h-4 text-slate-400" />
          </button>
          <button
            onClick={handleUpload}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
            title="Upload YAML"
          >
            <Upload className="w-4 h-4 text-slate-400" />
          </button>
        </div>
      </div>

      {/* Validation Results */}
      {validationResult && (
        <div className={`mb-4 p-4 rounded-lg border ${
          validationResult.valid
            ? 'bg-emerald-500/10 border-emerald-500/30'
            : 'bg-red-500/10 border-red-500/30'
        }`}>
          <div className="flex items-center gap-2 mb-2">
            {validationResult.valid ? (
              <>
                <CheckCircle className="w-5 h-5 text-emerald-400" />
                <span className="font-medium text-emerald-400">Valid YAML Configuration</span>
              </>
            ) : (
              <>
                <AlertCircle className="w-5 h-5 text-red-400" />
                <span className="font-medium text-red-400">Validation Errors</span>
              </>
            )}
          </div>
          {validationResult.errors.length > 0 && (
            <ul className="list-disc list-inside text-sm text-red-300 space-y-1">
              {validationResult.errors.map((error, i) => (
                <li key={i}>{error}</li>
              ))}
            </ul>
          )}
          {validationResult.warnings.length > 0 && (
            <ul className="list-disc list-inside text-sm text-yellow-300 space-y-1 mt-2">
              {validationResult.warnings.map((warning, i) => (
                <li key={i}>{warning}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Save Status */}
      {saveMutation.isSuccess && (
        <div className="mb-4 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-emerald-400" />
          <span className="text-sm text-emerald-400">Catalog saved successfully!</span>
        </div>
      )}

      {saveMutation.isError && (
        <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-400" />
          <span className="text-sm text-red-400">
            Failed to save: {(saveMutation.error as Error)?.message || 'Unknown error'}
          </span>
        </div>
      )}

      {/* Loading State */}
      {catalogQuery.isLoading && (
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
        </div>
      )}

      {/* Editor */}
      {!catalogQuery.isLoading && (
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden" style={{ height: 'calc(100vh - 320px)', minHeight: '400px' }}>
          {viewMode === 'edit' ? (
            <Editor
              height="100%"
              defaultLanguage="yaml"
              theme="vs-dark"
              value={content}
              onChange={handleEditorChange}
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                automaticLayout: true,
                padding: { top: 16 },
                tabSize: 2,
                wordWrap: 'on',
                folding: true,
                foldingStrategy: 'indentation',
              }}
            />
          ) : (
            <div className="h-full overflow-auto p-6">
              <pre className="text-sm text-slate-300 font-mono whitespace-pre-wrap">
                {content}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Footer Info */}
      <div className="mt-4 flex items-center justify-between text-xs text-slate-500">
        <div>
          {hasChanges && (
            <span className="text-yellow-400 flex items-center gap-1">
              <AlertCircle className="w-3 h-3" />
              Unsaved changes
            </span>
          )}
        </div>
        <div className="flex items-center gap-4">
          <span>Lines: {content.split('\n').length}</span>
          <span>Characters: {content.length}</span>
        </div>
      </div>
    </div>
  );
}
