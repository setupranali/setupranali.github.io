/**
 * Contract Editor
 * 
 * Edit semantic model data contracts (YAML specifications).
 * Auto-generates contracts from Semantic Models created in Modeling Studio.
 */

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  FileCode, 
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
  Check,
  FileText,
  ChevronDown,
  Plus,
  ArrowRight,
  ArrowLeft,
} from 'lucide-react';
import Editor from '@monaco-editor/react';
import axios from 'axios';
import { modelingApi } from '../lib/modeling-api';

const API_BASE = 'http://localhost:8080';
const CONTRACT_STORAGE_PREFIX = 'contract:';

interface ContractData {
  content: string;
  lastModified?: string;
}

interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

interface SemanticModelOption {
  id: string;
  name: string;
  sourceId: string;
}

// Generate YAML contract from semantic model
function generateContractYaml(model: any): string {
  const dimensions = model.dimensions || [];
  const measures = model.measures || [];
  const calculatedFields = model.calculatedFields || [];

  // Build fields from dimensions
  const fields = dimensions.map((dim: any) => ({
    name: dim.sourceColumn || dim.name.toLowerCase().replace(/\s+/g, '_'),
    type: mapDimensionTypeToDataType(dim.type),
    semanticType: mapDimensionTypeToSemanticType(dim.type),
  }));

  // Build dimensions section
  const dimensionDefs = dimensions.map((dim: any) => ({
    name: dim.name.toLowerCase().replace(/\s+/g, '_'),
    field: dim.sourceColumn || dim.name.toLowerCase().replace(/\s+/g, '_'),
    label: dim.name,
  }));

  // Build metrics section
  const metricDefs = measures.map((m: any) => ({
    name: m.name.toLowerCase().replace(/\s+/g, '_'),
    label: m.name,
    expression: {
      type: 'aggregation',
      agg: m.aggregation || 'sum',
      field: m.sourceColumn || m.expression || m.name.toLowerCase().replace(/\s+/g, '_'),
    },
    returnType: 'double',
  }));

  // Add calculated fields as metrics
  calculatedFields.forEach((cf: any) => {
    metricDefs.push({
      name: cf.name.toLowerCase().replace(/\s+/g, '_'),
      label: cf.name,
      expression: {
        type: 'calculated',
        formula: cf.expression,
      },
      returnType: cf.returnType || 'double',
    });
  });

  // Get source table from first dimension
  const sourceTable = dimensions[0]?.sourceTable || 'unknown_table';

  const yaml = `# Data Contract: ${model.name}
# Auto-generated from Semantic Model
# Last updated: ${new Date().toISOString()}

datasets:
  - id: ${model.name.toLowerCase().replace(/\s+/g, '_')}
    name: ${model.name}
    description: ${model.description || `Semantic model for ${model.name}`}
    tags:
      - semantic-model
      - auto-generated
    defaultTimezone: "UTC"
    
    source:
      engine: auto  # Will use source from ERD model
      type: table
      reference: ${sourceTable}
    
    # Row-Level Security (configure as needed)
    rls:
      enabled: false
      # column: tenant_id
      # mode: equals
      # allowAdminBypass: true
    
    # Incremental refresh (configure as needed)
    incremental:
      enabled: false
      # column: updated_at
      # type: timestamp
      # mode: append
    
    # Field definitions
    fields:
${fields.map((f: any) => `      - name: ${f.name}
        type: ${f.type}
        semanticType: ${f.semanticType}`).join('\n')}
    
    # Dimension definitions
    dimensions:
${dimensionDefs.map((d: any) => `      - name: ${d.name}
        field: ${d.field}
        label: "${d.label}"`).join('\n')}
    
    # Metric definitions
    metrics:
${metricDefs.map((m: any) => `      - name: ${m.name}
        label: "${m.label}"
        expression:
          type: ${m.expression.type}
          ${m.expression.type === 'aggregation' ? `agg: ${m.expression.agg}\n          field: ${m.expression.field}` : `formula: "${m.expression.formula}"`}
        returnType: ${m.returnType}`).join('\n')}
`;

  return yaml;
}

function mapDimensionTypeToDataType(dimType: string): string {
  const mapping: Record<string, string> = {
    string: 'string',
    number: 'double',
    time: 'timestamp',
    date: 'date',
    boolean: 'boolean',
    geo: 'string',
  };
  return mapping[dimType] || 'string';
}

function mapDimensionTypeToSemanticType(dimType: string): string {
  const mapping: Record<string, string> = {
    string: 'dimension',
    number: 'metric',
    time: 'time',
    date: 'time',
    boolean: 'dimension',
    geo: 'geo_city',
  };
  return mapping[dimType] || 'dimension';
}

export default function ContractEditor() {
  const queryClient = useQueryClient();
  const [content, setContent] = useState<string>('');
  const [hasChanges, setHasChanges] = useState(false);
  const [viewMode, setViewMode] = useState<'edit' | 'preview'>('edit');
  const [copied, setCopied] = useState(false);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [selectedModelId, setSelectedModelId] = useState<string>('');
  const [showModelDropdown, setShowModelDropdown] = useState(false);
  const [syncMessage, setSyncMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Fetch all sources to get semantic models
  const sourcesQuery = useQuery({
    queryKey: ['sources'],
    queryFn: () => modelingApi.listSources(),
    refetchOnMount: 'always',
    staleTime: 0,
  });

  // Fetch semantic models from all sources
  const semanticModelsQuery = useQuery({
    queryKey: ['all-semantic-models'],
    queryFn: async () => {
      const sources = sourcesQuery.data || [];
      const allModels: SemanticModelOption[] = [];
      
      // Add demo source
      try {
        const demoModels = await modelingApi.listSemanticModels('demo');
        demoModels.forEach(m => {
          allModels.push({ id: m.id, name: m.name, sourceId: 'demo' });
        });
      } catch (e) {
        console.log('No demo models');
      }
      
      // Add models from each source
      for (const source of sources) {
        try {
          const models = await modelingApi.listSemanticModels(source.id);
          models.forEach(m => {
            allModels.push({ id: m.id, name: m.name, sourceId: source.id });
          });
        } catch (e) {
          console.log(`No models for source ${source.id}`);
        }
      }
      
      return allModels;
    },
    enabled: !!sourcesQuery.data,
    refetchOnMount: 'always',
    staleTime: 0,
  });

  // Fetch selected semantic model details
  const selectedModelQuery = useQuery({
    queryKey: ['semantic-model-details', selectedModelId],
    queryFn: async () => {
      if (!selectedModelId) return null;
      const model = semanticModelsQuery.data?.find(m => m.id === selectedModelId);
      if (!model) return null;
      
      // Fetch full model details
      const fullModel = await modelingApi.getSemanticModel(selectedModelId);
      return fullModel;
    },
    enabled: !!selectedModelId,
  });

  // Fetch contract content for selected model
  const contractQuery = useQuery({
    queryKey: ['contract', selectedModelId],
    queryFn: async () => {
      if (!selectedModelId) {
        return getDefaultContract();
      }
      const storedContract = getStoredContract(selectedModelId);
      if (storedContract) {
        return storedContract;
      }

      try {
        const response = await axios.get<ContractData>(
          `${API_BASE}/v1/modeling/semantic/${selectedModelId}/yaml`
        );
        return response.data;
      } catch (error) {
        // If no saved contract, generate from semantic model
        if (selectedModelQuery.data) {
          return {
            content: generateContractYaml(selectedModelQuery.data),
            lastModified: new Date().toISOString(),
          };
        }
        return getDefaultContract();
      }
    },
    enabled: true,
  });

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: async (yamlContent: string) => {
      const payload: ContractData = {
        content: yamlContent,
        lastModified: new Date().toISOString(),
      };
      if (selectedModelId) {
        localStorage.setItem(
          `${CONTRACT_STORAGE_PREFIX}${selectedModelId}`,
          JSON.stringify(payload)
        );
      }
      return payload;
    },
    onSuccess: () => {
      setHasChanges(false);
      queryClient.invalidateQueries({ queryKey: ['contract', selectedModelId] });
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
    onError: () => {
      setHasChanges(false);
    },
  });

  // Validate mutation
  const validateMutation = useMutation({
    mutationFn: async (yamlContent: string) => {
      const result: ValidationResult = { valid: true, errors: [], warnings: [] };

      if (!yamlContent.includes('datasets:')) {
        result.valid = false;
        result.errors.push('Missing "datasets:" section');
      }

      const lines = yamlContent.split('\n');
      lines.forEach((line, index) => {
        if (line.includes('\t')) {
          result.warnings.push(`Line ${index + 1}: Tab characters detected. Use spaces for YAML indentation.`);
        }
      });

      return result;
    },
    onSuccess: (data) => {
      setValidationResult(data);
    },
  });

  // Sync contract to semantic model mutation
  const syncToModelMutation = useMutation({
    mutationFn: async (yamlContent: string) => {
      if (!selectedModelId) {
        throw new Error('No model selected');
      }
      const response = await axios.put(
        `${API_BASE}/v1/modeling/semantic/${selectedModelId}/from-yaml`,
        { content: yamlContent }
      );
      return response.data;
    },
    onSuccess: (data) => {
      setSyncMessage({ type: 'success', text: data.message || 'Contract synced to semantic model successfully!' });
      setHasChanges(false);
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['semantic-model-details', selectedModelId] });
      queryClient.invalidateQueries({ queryKey: ['all-semantic-models'] });
      queryClient.invalidateQueries({ queryKey: ['all-semantic-models-datasets'] });
      // Auto-clear message after 5 seconds
      setTimeout(() => setSyncMessage(null), 5000);
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || error.message || 'Failed to sync contract to model';
      setSyncMessage({ type: 'error', text: message });
      // Auto-clear message after 8 seconds
      setTimeout(() => setSyncMessage(null), 8000);
    },
  });

  // Initialize content when model or contract changes
  useEffect(() => {
    if (selectedModelQuery.data && !contractQuery.data?.content) {
      // Generate contract from semantic model
      const generated = generateContractYaml(selectedModelQuery.data);
      setContent(generated);
      setHasChanges(false);
    } else if (contractQuery.data?.content) {
      setContent(contractQuery.data.content);
      setHasChanges(false);
    }
  }, [selectedModelQuery.data, contractQuery.data]);

  // Auto-select first model if available
  useEffect(() => {
    if (semanticModelsQuery.data?.length && !selectedModelId) {
      setSelectedModelId(semanticModelsQuery.data[0].id);
    }
  }, [semanticModelsQuery.data, selectedModelId]);

  const handleEditorChange = (value: string | undefined) => {
    if (value !== undefined) {
      setContent(value);
      setHasChanges(true);
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
    if (contractQuery.data?.content) {
      setContent(contractQuery.data.content);
    } else if (selectedModelQuery.data) {
      setContent(generateContractYaml(selectedModelQuery.data));
    }
    setHasChanges(false);
    setValidationResult(null);
  };

  const handleRegenerate = () => {
    if (selectedModelQuery.data) {
      setContent(generateContractYaml(selectedModelQuery.data));
      setHasChanges(true);
      setSyncMessage(null);
    }
  };

  const handleSyncToModel = () => {
    if (!selectedModelId) {
      setSyncMessage({ type: 'error', text: 'Please select a semantic model first' });
      return;
    }
    if (!content.includes('datasets:')) {
      setSyncMessage({ type: 'error', text: 'Invalid contract: missing "datasets:" section' });
      return;
    }
    syncToModelMutation.mutate(content);
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const modelName = semanticModelsQuery.data?.find(m => m.id === selectedModelId)?.name || 'contract';
    const blob = new Blob([content], { type: 'text/yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${modelName.toLowerCase().replace(/\s+/g, '-')}-contract.yaml`;
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

  const selectedModel = semanticModelsQuery.data?.find(m => m.id === selectedModelId);

  return (
    <div className="p-6 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-semibold text-white flex items-center gap-3">
            <FileText className="w-7 h-7 text-indigo-400" />
            Contract Editor
          </h1>
          <p className="text-slate-400">
            Define data contracts for your semantic models
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              queryClient.invalidateQueries({ queryKey: ['all-semantic-models'] });
              queryClient.invalidateQueries({ queryKey: ['contract', selectedModelId] });
            }}
            disabled={contractQuery.isFetching}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-5 h-5 text-slate-400 ${contractQuery.isFetching ? 'animate-spin' : ''}`} />
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
            Save Contract
          </button>
        </div>
      </div>

      {/* Model Selector */}
      <div className="mb-4 flex items-center gap-4">
        <div className="relative">
          <button
            onClick={() => setShowModelDropdown(!showModelDropdown)}
            className="flex items-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-600 rounded-lg transition-colors min-w-[280px]"
          >
            <FileCode className="w-4 h-4 text-indigo-400" />
            <span className="text-white flex-1 text-left">
              {selectedModel?.name || 'Select Semantic Model...'}
            </span>
            <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${showModelDropdown ? 'rotate-180' : ''}`} />
          </button>
          
          {showModelDropdown && (
            <div className="absolute top-full left-0 mt-1 w-full bg-slate-800 border border-slate-600 rounded-lg shadow-xl z-50 max-h-64 overflow-auto">
              {semanticModelsQuery.isLoading ? (
                <div className="p-4 text-center">
                  <Loader2 className="w-5 h-5 text-indigo-400 animate-spin mx-auto" />
                </div>
              ) : semanticModelsQuery.data?.length === 0 ? (
                <div className="p-4 text-center text-slate-400 text-sm">
                  No semantic models found.<br />
                  Create one in Modeling Studio first.
                </div>
              ) : (
                semanticModelsQuery.data?.map((model) => (
                  <button
                    key={model.id}
                    onClick={() => {
                      setSelectedModelId(model.id);
                      setShowModelDropdown(false);
                    }}
                    className={`w-full flex items-center gap-3 px-4 py-2.5 hover:bg-slate-700 transition-colors text-left ${
                      model.id === selectedModelId ? 'bg-indigo-500/20' : ''
                    }`}
                  >
                    <FileCode className={`w-4 h-4 ${model.id === selectedModelId ? 'text-indigo-400' : 'text-slate-500'}`} />
                    <div>
                      <div className="text-white text-sm">{model.name}</div>
                      <div className="text-slate-500 text-xs">Source: {model.sourceId}</div>
                    </div>
                    {model.id === selectedModelId && (
                      <Check className="w-4 h-4 text-indigo-400 ml-auto" />
                    )}
                  </button>
                ))
              )}
            </div>
          )}
        </div>

        {selectedModelId && (
          <div className="flex items-center gap-2 bg-slate-800/50 rounded-lg p-1">
            {/* Sync Model → Contract */}
            <button
              onClick={handleRegenerate}
              disabled={selectedModelQuery.isLoading}
              className="flex items-center gap-2 px-3 py-2 text-emerald-400 hover:text-emerald-300 hover:bg-slate-700 rounded-lg transition-colors"
              title="Pull changes from Semantic Model to Contract (Model → Contract)"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm">Pull from Model</span>
            </button>
            
            <div className="h-6 w-px bg-slate-600" />
            
            {/* Sync Contract → Model */}
            <button
              onClick={handleSyncToModel}
              disabled={syncToModelMutation.isPending || !content.includes('datasets:')}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                content.includes('datasets:') && !syncToModelMutation.isPending
                  ? 'text-amber-400 hover:text-amber-300 hover:bg-slate-700'
                  : 'text-slate-500 cursor-not-allowed'
              }`}
              title="Push contract to Semantic Model (Contract → Model)"
            >
              {syncToModelMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <ArrowRight className="w-4 h-4" />
              )}
              <span className="text-sm">Push to Model</span>
            </button>
          </div>
        )}
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
                <span className="font-medium text-emerald-400">Valid Contract</span>
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
          <span className="text-sm text-emerald-400">Contract saved successfully!</span>
        </div>
      )}

      {/* Sync Message */}
      {syncMessage && (
        <div className={`mb-4 p-3 rounded-lg flex items-center justify-between ${
          syncMessage.type === 'success'
            ? 'bg-emerald-500/10 border border-emerald-500/30'
            : 'bg-red-500/10 border border-red-500/30'
        }`}>
          <div className="flex items-center gap-2">
            {syncMessage.type === 'success' ? (
              <CheckCircle className="w-4 h-4 text-emerald-400" />
            ) : (
              <AlertCircle className="w-4 h-4 text-red-400" />
            )}
            <span className={`text-sm ${syncMessage.type === 'success' ? 'text-emerald-400' : 'text-red-400'}`}>
              {syncMessage.text}
            </span>
          </div>
          <button
            onClick={() => setSyncMessage(null)}
            className="text-slate-400 hover:text-white"
          >
            ×
          </button>
        </div>
      )}

      {/* No Model Selected */}
      {!selectedModelId && semanticModelsQuery.data?.length === 0 && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <FileCode className="w-16 h-16 text-slate-700 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-slate-400 mb-2">No Semantic Models Found</h3>
            <p className="text-sm text-slate-500 mb-4">
              Create a semantic model in the Modeling Studio first,<br />
              then come back here to edit its data contract.
            </p>
            <a
              href="/modeling"
              className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
              Go to Modeling Studio
            </a>
          </div>
        </div>
      )}

      {/* Loading State */}
      {(contractQuery.isLoading || selectedModelQuery.isLoading) && selectedModelId && (
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
        </div>
      )}

      {/* Editor */}
      {!contractQuery.isLoading && !selectedModelQuery.isLoading && (
        <div className="flex-1 bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden" style={{ minHeight: '500px' }}>
          {viewMode === 'edit' ? (
            <Editor
              key={`editor-${selectedModelId}`}
              height="500px"
              language="yaml"
              theme="vs-dark"
              value={content || '# Loading...'}
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
                {content || '# No content'}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Footer Info */}
      <div className="mt-4 flex items-center justify-between text-xs text-slate-500">
        <div className="flex items-center gap-4">
          {hasChanges && (
            <span className="text-yellow-400 flex items-center gap-1">
              <AlertCircle className="w-3 h-3" />
              Unsaved changes
            </span>
          )}
          {selectedModel && (
            <span>
              Model: <span className="text-slate-300">{selectedModel.name}</span>
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

function getDefaultContract(): ContractData {
  return {
    content: `# Universal BI Data Contract
# Select a semantic model from the dropdown above to generate a contract

# Contract Structure:
# - datasets: Define your data models
#   - source: Where the data comes from
#   - fields: Column definitions with types
#   - dimensions: Grouping/filtering attributes
#   - metrics: Aggregations and calculations
#   - rls: Row-level security rules
#   - incremental: Refresh configuration

datasets: []
`,
    lastModified: new Date().toISOString(),
  };
}

function getStoredContract(modelId: string): ContractData | null {
  const stored = localStorage.getItem(`${CONTRACT_STORAGE_PREFIX}${modelId}`);
  if (!stored) {
    return null;
  }
  try {
    return JSON.parse(stored) as ContractData;
  } catch (error) {
    return null;
  }
}
