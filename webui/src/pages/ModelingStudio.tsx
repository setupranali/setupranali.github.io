/**
 * Modeling Studio
 * 
 * Main BI Modeling UI that combines:
 * - Schema Discovery Panel (left)
 * - ERD Canvas (center)
 * - Semantic Model Panel (right)
 * - Query Workbench (bottom)
 */

import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Panel,
  PanelGroup,
  PanelResizeHandle,
} from 'react-resizable-panels';
import {
  Database,
  GitBranch,
  Columns,
  Plus,
  Save,
  Download,
  Upload,
  Trash2,
  ChevronLeft,
  ChevronRight,
  PanelLeftClose,
  PanelRightClose,
  Maximize2,
  Minimize2,
  Code,
} from 'lucide-react';
import { modelingApi } from '../lib/modeling-api';
import { useModelingStore } from '../store/modeling';
import { SchemaPanel } from '../components/modeling/SchemaPanel';
import { ERDCanvas } from '../components/modeling/ERDCanvas';
import { SemanticModelPanel } from '../components/modeling/SemanticModelPanel';
import { QueryWorkbench } from '../components/modeling/QueryWorkbench';
import { SourceConnectionDialog } from '../components/modeling/SourceConnectionDialog';
import type { ConnectionConfig } from '../types/modeling';

export default function ModelingStudio() {
  const queryClient = useQueryClient();
  const [showSourceDialog, setShowSourceDialog] = useState(false);
  const [showCreateERD, setShowCreateERD] = useState(false);
  const [showCreateSemantic, setShowCreateSemantic] = useState(false);
  
  // Panel collapse states
  const [isSchemaCollapsed, setIsSchemaCollapsed] = useState(false);
  const [isSemanticCollapsed, setIsSemanticCollapsed] = useState(false);
  
  // Active view: 'designer' shows Model Designer expanded, 'query' shows Query Workbench expanded
  // Only one can be expanded at a time
  const [activeView, setActiveView] = useState<'designer' | 'query'>('designer');
  
  // Toggle between views
  const toggleToDesigner = () => setActiveView('designer');
  const toggleToQuery = () => setActiveView('query');

  const {
    activeSourceId,
    activeERDId,
    activeSemanticId,
    erdModels,
    semanticModels,
    setActiveSource,
    setActiveERD,
    setActiveSemantic,
    setERDModels,
    setSemanticModels,
  } = useModelingStore();

  // Fetch data sources
  const sourcesQuery = useQuery({
    queryKey: ['sources'],
    queryFn: () => modelingApi.listSources(),
  });

  // Create source mutation
  const createSourceMutation = useMutation({
    mutationFn: (data: { name: string; config: ConnectionConfig }) =>
      modelingApi.createSource(data.name, {
        engine: data.config.engine,
        host: data.config.host,
        port: data.config.port,
        database: data.config.database,
        username: data.config.username,
        password: data.config.password,
        ssl: data.config.ssl,
        catalog: data.config.catalog,
        ...data.config.extra,
      }),
    onSuccess: (newSource) => {
      // Invalidate sources query
      queryClient.invalidateQueries({ queryKey: ['sources'] });
      // Invalidate schema queries for the new source
      queryClient.invalidateQueries({ queryKey: ['schemas', newSource.id] });
      queryClient.invalidateQueries({ queryKey: ['tables', newSource.id] });
      queryClient.invalidateQueries({ queryKey: ['columns', newSource.id] });
      // Invalidate ERD and Semantic model queries for the new source
      queryClient.invalidateQueries({ queryKey: ['erd-models', newSource.id] });
      queryClient.invalidateQueries({ queryKey: ['semantic-models', newSource.id] });
      setActiveSource(newSource.id);
      setShowSourceDialog(false);
    },
  });

  // Use first available source or demo
  const sourceId = activeSourceId || sourcesQuery.data?.[0]?.id || 'demo';

  // Fetch ERD models from API
  const erdQuery = useQuery({
    queryKey: ['erd-models', sourceId],
    queryFn: async () => {
      const models = await modelingApi.listERDModels(sourceId);
      setERDModels(models);
      if (models.length > 0 && !activeERDId) {
        setActiveERD(models[0].id);
      }
      return models;
    },
    enabled: !!sourceId,
    staleTime: 30000,
  });

  // Fetch Semantic models from API
  const semanticQuery = useQuery({
    queryKey: ['semantic-models', sourceId],
    queryFn: async () => {
      const models = await modelingApi.listSemanticModels(sourceId);
      setSemanticModels(models);
      if (models.length > 0 && !activeSemanticId) {
        setActiveSemantic(models[0].id);
      }
      return models;
    },
    enabled: !!sourceId,
    staleTime: 30000,
  });

  const handleCreateERD = async (name: string) => {
    setShowCreateERD(false);
    
    try {
      // Create directly on API - no local model to avoid duplicates
      const apiModel = await modelingApi.createERDModel({ name, sourceId });
      console.log('ERD model created:', apiModel);
      setActiveERD(apiModel.id);
      // Refresh the list
      queryClient.invalidateQueries({ queryKey: ['erd-models', sourceId] });
    } catch (error) {
      console.error('Failed to create ERD model:', error);
      alert('Failed to create ERD model. Please try again.');
    }
  };

  const handleCreateSemantic = async (name: string) => {
    setShowCreateSemantic(false);
    
    try {
      // Create directly on API - no local model to avoid duplicates
      const apiModel = await modelingApi.createSemanticModel({ name, sourceId, erdModelId: activeERDId || undefined });
      console.log('Semantic model created:', apiModel);
      setActiveSemantic(apiModel.id);
      // Refresh the list
      queryClient.invalidateQueries({ queryKey: ['semantic-models', sourceId] });
    } catch (error) {
      console.error('Failed to create Semantic model:', error);
      alert('Failed to create Semantic model. Please try again.');
    }
  };

  // All available ERD models (from API + local)
  const allERDModels = erdQuery.data || erdModels.filter(m => m.sourceId === sourceId);
  const allSemanticModels = semanticQuery.data || semanticModels.filter(m => m.sourceId === sourceId);

  // Auto-select/fix ERD model selection
  useEffect(() => {
    if (!sourceId) return;
    
    if (allERDModels.length > 0) {
      // Check if current selection is valid
      const selectedModel = activeERDId ? allERDModels.find(m => m.id === activeERDId) : null;
      
      if (selectedModel) {
        // Valid selection, nothing to do
        return;
      }
      
      // If activeERDId starts with 'local-', try to find matching API model by name
      // (This handles the case where local model was synced to API but activeERDId wasn't updated)
      if (activeERDId?.startsWith('local-')) {
        const localModel = erdModels.find(m => m.id === activeERDId);
        if (localModel) {
          // Find API model with same name
          const apiModel = allERDModels.find(m => m.name === localModel.name && !m.id.startsWith('local-'));
          if (apiModel) {
            console.log('Switching from local to API model:', localModel.name, '->', apiModel.id);
            setActiveERD(apiModel.id);
            return;
          }
        }
      }
      
      // No valid selection - select first available model
      setActiveERD(allERDModels[0].id);
    }
    // NOTE: Removed auto-creation of Default ERD - users should create ERD models manually
  }, [sourceId, allERDModels, activeERDId, erdModels, setActiveERD]);

  // Handle ERD deletion
  const handleDeleteERD = useCallback(async (modelId: string) => {
    if (!modelId) return;
    
    const model = allERDModels.find(m => m.id === modelId);
    if (!model) return;
    
    const confirmed = window.confirm(`Are you sure you want to delete "${model.name}"? This cannot be undone.`);
    if (!confirmed) return;
    
    try {
      // If it's a local model, just remove from store
      if (modelId.startsWith('local-')) {
        // Remove from local store
        setERDModels(erdModels.filter(m => m.id !== modelId));
      } else {
        // Delete from API
        await modelingApi.deleteERDModel(modelId);
      }
      
      // Clear selection if deleted model was selected
      if (activeERDId === modelId) {
        const remaining = allERDModels.filter(m => m.id !== modelId);
        setActiveERD(remaining.length > 0 ? remaining[0].id : null);
      }
      
      // Invalidate query to refresh list
      queryClient.invalidateQueries({ queryKey: ['erd-models', sourceId] });
    } catch (error) {
      console.error('Failed to delete ERD model:', error);
      alert('Failed to delete ERD model. Please try again.');
    }
  }, [allERDModels, activeERDId, erdModels, sourceId, setActiveERD, setERDModels, queryClient]);

  // Handle Semantic Model deletion
  const handleDeleteSemantic = useCallback(async (modelId: string) => {
    if (!modelId) return;
    
    const model = allSemanticModels.find(m => m.id === modelId);
    if (!model) return;
    
    const confirmed = window.confirm(`Are you sure you want to delete "${model.name}"? This cannot be undone.`);
    if (!confirmed) return;
    
    try {
      // If it's a local model, just remove from store
      if (modelId.startsWith('local-')) {
        setSemanticModels(semanticModels.filter(m => m.id !== modelId));
      } else {
        // Delete from API
        await modelingApi.deleteSemanticModel(modelId);
      }
      
      // Clear selection if deleted model was selected
      if (activeSemanticId === modelId) {
        const remaining = allSemanticModels.filter(m => m.id !== modelId);
        setActiveSemantic(remaining.length > 0 ? remaining[0].id : null);
      }
      
      // Invalidate query to refresh list
      queryClient.invalidateQueries({ queryKey: ['semantic-models', sourceId] });
    } catch (error) {
      console.error('Failed to delete Semantic model:', error);
      alert('Failed to delete Semantic model. Please try again.');
    }
  }, [allSemanticModels, activeSemanticId, semanticModels, sourceId, setActiveSemantic, setSemanticModels, queryClient]);

  // State for save operation
  const [isSaving, setIsSaving] = useState(false);

  // Handle Save - saves current ERD model (nodes and edges) to API
  const handleSave = useCallback(async () => {
    if (!activeERDId) {
      alert('No ERD model selected. Please select or create an ERD model first.');
      return;
    }

    // Find the current ERD model from the store
    const currentERD = erdModels.find(m => m.id === activeERDId);
    if (!currentERD) {
      alert('ERD model not found. Please refresh the page.');
      return;
    }

    setIsSaving(true);
    try {
      // Update the ERD model with current nodes and edges
      await modelingApi.updateERDModel(activeERDId, {
        nodes: currentERD.nodes,
        edges: currentERD.edges,
      });
      
      console.log('ERD model saved successfully');
      
      // Also save the semantic model if one is selected
      if (activeSemanticId) {
        const currentSemantic = semanticModels.find(m => m.id === activeSemanticId);
        if (currentSemantic) {
          await modelingApi.updateSemanticModel(activeSemanticId, {
            dimensions: currentSemantic.dimensions,
            measures: currentSemantic.measures,
            calculatedFields: currentSemantic.calculatedFields,
          });
          console.log('Semantic model saved successfully');
        }
      }

      // Show success message
      alert('Saved successfully!');
      
      // Refresh queries
      queryClient.invalidateQueries({ queryKey: ['erd-models', sourceId] });
      queryClient.invalidateQueries({ queryKey: ['semantic-models', sourceId] });
    } catch (error) {
      console.error('Failed to save:', error);
      alert('Failed to save. Please try again.');
    } finally {
      setIsSaving(false);
    }
  }, [activeERDId, activeSemanticId, erdModels, semanticModels, sourceId, queryClient]);

  return (
    <div className="h-screen flex flex-col bg-slate-950">
      {/* Top Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800 bg-slate-900">
        <div className="flex items-center gap-4">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <Database className="w-6 h-6 text-indigo-400" />
            <span className="font-semibold text-white">Modeling Studio</span>
          </div>

          {/* Data Source Selector */}
          <div className="flex items-center gap-2 pl-4 border-l border-slate-700">
            <Database className="w-4 h-4 text-slate-500" />
            <select
              value={sourceId}
              onChange={(e) => setActiveSource(e.target.value || null)}
              className="px-3 py-1.5 bg-slate-800 border border-slate-600 rounded-lg text-sm text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="demo">Demo Source</option>
              {sourcesQuery.data?.map((source) => (
                <option key={source.id} value={source.id}>
                  {source.name} ({source.type})
                </option>
              ))}
            </select>
            <button
              onClick={() => setShowSourceDialog(true)}
              className="p-1.5 hover:bg-slate-800 rounded-lg transition-colors"
              title="Add New Source"
            >
              <Plus className="w-4 h-4 text-slate-400" />
            </button>
          </div>

          {/* ERD Model Selector */}
          <div className="flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-slate-500" />
            <select
              value={activeERDId || ''}
              onChange={(e) => setActiveERD(e.target.value || null)}
              className="px-3 py-1.5 bg-slate-800 border border-slate-600 rounded-lg text-sm text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 min-w-[160px]"
            >
              <option value="">Select ERD Model</option>
              {allERDModels.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name}
                </option>
              ))}
            </select>
            <button
              onClick={() => setShowCreateERD(true)}
              className="p-1.5 hover:bg-slate-800 rounded-lg transition-colors"
              title="New ERD Model"
            >
              <Plus className="w-4 h-4 text-slate-400" />
            </button>
            {activeERDId && (
              <button
                onClick={() => handleDeleteERD(activeERDId)}
                className="p-1.5 hover:bg-red-900/50 rounded-lg transition-colors"
                title="Delete ERD Model"
              >
                <Trash2 className="w-4 h-4 text-red-400 hover:text-red-300" />
              </button>
            )}
          </div>

          {/* Semantic Model Selector */}
          <div className="flex items-center gap-2">
            <Columns className="w-4 h-4 text-slate-500" />
            <select
              value={activeSemanticId || ''}
              onChange={(e) => setActiveSemantic(e.target.value || null)}
              className="px-3 py-1.5 bg-slate-800 border border-slate-600 rounded-lg text-sm text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 min-w-[160px]"
            >
              <option value="">Select Semantic Model</option>
              {allSemanticModels.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name}
                </option>
              ))}
            </select>
            <button
              onClick={() => setShowCreateSemantic(true)}
              className="p-1.5 hover:bg-slate-800 rounded-lg transition-colors"
              title="New Semantic Model"
            >
              <Plus className="w-4 h-4 text-slate-400" />
            </button>
            {activeSemanticId && (
              <button
                onClick={() => handleDeleteSemantic(activeSemanticId)}
                className="p-1.5 hover:bg-red-900/50 rounded-lg transition-colors"
                title="Delete Semantic Model"
              >
                <Trash2 className="w-4 h-4 text-red-400 hover:text-red-300" />
              </button>
            )}
          </div>
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-2 px-3 py-1.5 hover:bg-slate-800 rounded-lg text-sm text-slate-400 transition-colors">
            <Upload className="w-4 h-4" />
            Import
          </button>
          <button className="flex items-center gap-2 px-3 py-1.5 hover:bg-slate-800 rounded-lg text-sm text-slate-400 transition-colors">
            <Download className="w-4 h-4" />
            Export
          </button>
          <button 
            onClick={handleSave}
            disabled={isSaving || !activeERDId}
            className="flex items-center gap-2 px-3 py-1.5 bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-sm text-white transition-colors"
          >
            <Save className={`w-4 h-4 ${isSaving ? 'animate-pulse' : ''}`} />
            {isSaving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        <PanelGroup direction="vertical">
          {/* Top Section: Schema + ERD + Semantic - Only shown when designer view is active */}
          {activeView === 'designer' && (
            <>
              <Panel defaultSize={100} minSize={50}>
                <div className="h-full flex flex-col">
                  {/* Header with Switch to Query */}
                  <div className="flex-shrink-0 flex items-center justify-between px-3 py-1.5 bg-slate-800/50 border-b border-slate-700">
                    <span className="text-xs text-slate-400 uppercase tracking-wide flex items-center gap-2">
                      <GitBranch className="w-3.5 h-3.5" />
                      Model Designer
                    </span>
                    <button
                      onClick={toggleToQuery}
                      className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs text-slate-300 hover:text-white transition-colors"
                      title="Switch to Query Workbench"
                    >
                      <Maximize2 className="w-3.5 h-3.5" />
                      Query Workbench
                    </button>
                  </div>
                  
                  <div className="flex-1 overflow-hidden">
                      <PanelGroup direction="horizontal">
                        {/* Schema Panel with Collapse */}
                        {!isSchemaCollapsed && (
                          <>
                            <Panel defaultSize={18} minSize={12} maxSize={30}>
                              <div className="h-full flex flex-col">
                                <div className="flex-shrink-0 flex items-center justify-between px-2 py-1 bg-slate-900 border-b border-slate-700">
                                  <span className="text-xs text-slate-400 flex items-center gap-1.5">
                                    <Database className="w-3 h-3" />
                                    Schema
                                  </span>
                                  <button
                                    onClick={() => setIsSchemaCollapsed(true)}
                                    className="p-0.5 hover:bg-slate-700 rounded text-slate-500 hover:text-white transition-colors"
                                    title="Collapse Schema"
                                  >
                                    <PanelLeftClose className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                                <div className="flex-1 overflow-hidden">
                                  <SchemaPanel
                                    sourceId={sourceId}
                                    onTableSelect={(schema, table) => {
                                      console.log('Selected table:', schema, table);
                                    }}
                                  />
                                </div>
                              </div>
                            </Panel>
                            <PanelResizeHandle className="w-1 bg-slate-800 hover:bg-indigo-500 transition-colors" />
                          </>
                        )}

                        {/* Collapsed Schema Toggle */}
                        {isSchemaCollapsed && (
                          <div className="w-8 bg-slate-900 border-r border-slate-700 flex flex-col items-center py-2">
                            <button
                              onClick={() => setIsSchemaCollapsed(false)}
                              className="p-1.5 hover:bg-slate-700 rounded text-slate-400 hover:text-white transition-colors"
                              title="Expand Schema Browser"
                            >
                              <ChevronRight className="w-4 h-4" />
                            </button>
                            <span className="text-xs text-slate-500 mt-2 [writing-mode:vertical-rl] rotate-180">
                              Schema
                            </span>
                          </div>
                        )}

                        {/* ERD Canvas */}
                        <Panel defaultSize={isSemanticCollapsed ? 82 : 57} minSize={30}>
                          {activeERDId ? (
                            <ERDCanvas
                              erdModelId={activeERDId}
                              sourceId={sourceId}
                            />
                          ) : (
                            <div className="h-full flex items-center justify-center bg-slate-950">
                              <div className="text-center">
                                <GitBranch className="w-12 h-12 text-slate-700 mx-auto mb-4" />
                                <h3 className="text-lg font-medium text-slate-400 mb-2">
                                  No ERD Model Selected
                                </h3>
                                <p className="text-sm text-slate-600 mb-4">
                                  Create or select an ERD model to start building relationships
                                </p>
                                <button
                                  onClick={() => setShowCreateERD(true)}
                                  className="flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-colors mx-auto"
                                >
                                  <Plus className="w-4 h-4" />
                                  Create ERD Model
                                </button>
                              </div>
                            </div>
                          )}
                        </Panel>

                        {/* Collapsed Semantic Toggle */}
                        {isSemanticCollapsed && (
                          <div className="w-8 bg-slate-900 border-l border-slate-700 flex flex-col items-center py-2">
                            <button
                              onClick={() => setIsSemanticCollapsed(false)}
                              className="p-1.5 hover:bg-slate-700 rounded text-slate-400 hover:text-white transition-colors"
                              title="Expand Semantic Model"
                            >
                              <ChevronLeft className="w-4 h-4" />
                            </button>
                            <span className="text-xs text-slate-500 mt-2 [writing-mode:vertical-rl]">
                              Semantic
                            </span>
                          </div>
                        )}

                        {/* Semantic Model Panel with Collapse */}
                        {!isSemanticCollapsed && (
                          <>
                            <PanelResizeHandle className="w-1 bg-slate-800 hover:bg-indigo-500 transition-colors" />
                            <Panel defaultSize={25} minSize={15} maxSize={40}>
                              <div className="h-full flex flex-col">
                                <div className="flex-shrink-0 flex items-center justify-between px-2 py-1 bg-slate-900 border-b border-slate-700">
                                  <span className="text-xs text-slate-400 flex items-center gap-1.5">
                                    <Columns className="w-3 h-3" />
                                    Semantic Model
                                  </span>
                                  <button
                                    onClick={() => setIsSemanticCollapsed(true)}
                                    className="p-0.5 hover:bg-slate-700 rounded text-slate-500 hover:text-white transition-colors"
                                    title="Collapse Semantic Model"
                                  >
                                    <PanelRightClose className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                                <div className="flex-1 overflow-hidden">
                                  {activeSemanticId ? (
                                    <SemanticModelPanel
                                      semanticModelId={activeSemanticId}
                                    />
                                  ) : (
                                    <div className="h-full flex items-center justify-center bg-slate-900">
                                      <div className="text-center p-4">
                                        <Columns className="w-10 h-10 text-slate-700 mx-auto mb-3" />
                                        <h4 className="text-sm font-medium text-slate-400 mb-2">
                                          Select a semantic<br/>model to view
                                        </h4>
                                        <button
                                          onClick={() => setShowCreateSemantic(true)}
                                          className="text-sm text-indigo-400 hover:text-indigo-300"
                                        >
                                          Create Semantic Model
                                        </button>
                                      </div>
                                    </div>
                                  )}
                                </div>
                              </div>
                            </Panel>
                          </>
                        )}
                      </PanelGroup>
                    </div>
                </div>
              </Panel>
            </>
          )}

          {/* Query Workbench - Only shown when query view is active */}
          {activeView === 'query' && (
            <Panel defaultSize={100} minSize={50}>
              <div className="h-full flex flex-col bg-slate-900">
                {/* Query Section Header with Switch to Designer */}
                <div className="flex-shrink-0 flex items-center justify-between px-3 py-1.5 bg-slate-800/80 border-b border-slate-700">
                  <span className="text-xs text-slate-400 uppercase tracking-wide flex items-center gap-2">
                    <Code className="w-3.5 h-3.5" />
                    Query Workbench
                  </span>
                  <button
                    onClick={toggleToDesigner}
                    className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs text-slate-300 hover:text-white transition-colors"
                    title="Switch to Model Designer"
                  >
                    <Minimize2 className="w-3.5 h-3.5" />
                    Model Designer
                  </button>
                </div>
                
                {/* Query Content */}
                <div className="flex-1 overflow-hidden">
                  <QueryWorkbench
                    erdModelId={activeERDId || ''}
                    semanticModelId={activeSemanticId || ''}
                    sourceId={sourceId}
                  />
                </div>
              </div>
            </Panel>
          )}
        </PanelGroup>
      </div>

      {/* Source Connection Dialog */}
      {showSourceDialog && (
        <SourceConnectionDialog
          isOpen={showSourceDialog}
          onClose={() => setShowSourceDialog(false)}
          onSave={(config, name) => {
            createSourceMutation.mutate({ name, config });
          }}
        />
      )}

      {/* Create ERD Dialog */}
      {showCreateERD && (
        <CreateModelDialog
          title="Create ERD Model"
          placeholder="e.g., Sales Data Model"
          onClose={() => setShowCreateERD(false)}
          onCreate={handleCreateERD}
        />
      )}

      {/* Create Semantic Dialog */}
      {showCreateSemantic && (
        <CreateModelDialog
          title="Create Semantic Model"
          placeholder="e.g., Sales Metrics"
          onClose={() => setShowCreateSemantic(false)}
          onCreate={handleCreateSemantic}
        />
      )}
    </div>
  );
}

// ============================================================================
// CREATE MODEL DIALOG
// ============================================================================

interface CreateModelDialogProps {
  title: string;
  placeholder: string;
  onClose: () => void;
  onCreate: (name: string) => void;
}

function CreateModelDialog({
  title,
  placeholder,
  onClose,
  onCreate,
}: CreateModelDialogProps) {
  const [name, setName] = useState('');

  const handleCreate = () => {
    if (!name.trim()) return;
    onCreate(name.trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && name.trim()) {
      e.preventDefault();
      handleCreate();
    } else if (e.key === 'Escape') {
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-slate-800 border border-slate-600 rounded-xl shadow-2xl w-96 p-6">
        <h3 className="text-lg font-semibold text-white mb-4">{title}</h3>
        
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={placeholder}
          autoFocus
          className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 mb-4"
          onKeyDown={handleKeyDown}
        />

        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            type="button"
            className="px-4 py-2 text-slate-300 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            type="button"
            disabled={!name.trim()}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-colors disabled:opacity-50"
          >
            Create
          </button>
        </div>
      </div>
    </div>
  );
}
