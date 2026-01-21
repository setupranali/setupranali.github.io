/**
 * Semantic Model Panel
 * 
 * UI for managing dimensions and measures:
 * - Mark columns as dimensions or measures
 * - Configure aggregations
 * - Create calculated fields
 * - Define time intelligence
 */

import React, { useState, useCallback, useEffect } from 'react';
import { GripVertical } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';
import {
  Columns,
  Hash,
  Calculator,
  Plus,
  Trash2,
  Edit2,
  Eye,
  EyeOff,
  ChevronDown,
  ChevronRight,
  Calendar,
  Globe,
  Layers,
  Sigma,
  Percent,
  DollarSign,
  AlertCircle,
  CheckCircle2,
  Loader2,
} from 'lucide-react';
import { modelingApi } from '../../lib/modeling-api';
import { useModelingStore } from '../../store/modeling';
import type {
  Dimension,
  Measure,
  CalculatedField,
  AggregationType,
  DimensionType,
  FormatType,
} from '../../types/modeling';
import { cn } from '../../lib/utils';

// ============================================================================
// CONSTANTS
// ============================================================================

const AGGREGATION_OPTIONS: { value: AggregationType; label: string; icon: typeof Sigma }[] = [
  { value: 'SUM', label: 'Sum', icon: Sigma },
  { value: 'COUNT', label: 'Count', icon: Hash },
  { value: 'COUNT_DISTINCT', label: 'Count Distinct', icon: Hash },
  { value: 'AVG', label: 'Average', icon: Sigma },
  { value: 'MIN', label: 'Min', icon: Sigma },
  { value: 'MAX', label: 'Max', icon: Sigma },
];

const DIMENSION_TYPES: { value: DimensionType; label: string; icon: typeof Columns }[] = [
  { value: 'categorical', label: 'Categorical', icon: Columns },
  { value: 'time', label: 'Time', icon: Calendar },
  { value: 'geo', label: 'Geographic', icon: Globe },
  { value: 'hierarchical', label: 'Hierarchical', icon: Layers },
];

const FORMAT_OPTIONS: { value: FormatType; label: string; icon: typeof Hash }[] = [
  { value: 'number', label: 'Number', icon: Hash },
  { value: 'currency', label: 'Currency', icon: DollarSign },
  { value: 'percent', label: 'Percent', icon: Percent },
  { value: 'text', label: 'Text', icon: Columns },
  { value: 'date', label: 'Date', icon: Calendar },
];

// ============================================================================
// MAIN COMPONENT
// ============================================================================

interface SemanticModelPanelProps {
  semanticModelId: string;
  onDimensionSelect?: (dimension: Dimension) => void;
  onMeasureSelect?: (measure: Measure) => void;
}

export function SemanticModelPanel({
  semanticModelId,
  onDimensionSelect,
  onMeasureSelect,
}: SemanticModelPanelProps) {
  const [activeSection, setActiveSection] = useState<'dimensions' | 'measures' | 'calculated'>('dimensions');
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [editItem, setEditItem] = useState<Dimension | Measure | CalculatedField | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const {
    activeSourceId,
    getActiveSemantic,
    selectedDimensionId,
    selectedMeasureId,
    setSelectedDimension,
    setSelectedMeasure,
    addDimension,
    removeDimension,
    updateDimension,
    addMeasure,
    removeMeasure,
    updateMeasure,
    addCalculatedField,
    removeCalculatedField,
    updateCalculatedField,
  } = useModelingStore();

  const semanticModel = getActiveSemantic();

  // API mutations - defined before handleDrop to ensure they're available
  const addDimensionMutation = useMutation({
    mutationFn: (data: Parameters<typeof modelingApi.addDimension>[1]) =>
      modelingApi.addDimension(semanticModelId, data),
    onSuccess: (dimension) => {
      // Already added locally, just close dialog if open
      setShowAddDialog(false);
    },
    onError: (error) => {
      console.error('Failed to add dimension to API:', error);
    },
  });

  const addMeasureMutation = useMutation({
    mutationFn: (data: Parameters<typeof modelingApi.addMeasure>[1]) =>
      modelingApi.addMeasure(semanticModelId, data),
    onSuccess: (measure) => {
      // Already added locally, just close dialog if open
      setShowAddDialog(false);
      // Note: ID replacement is handled in the drop handler if needed
    },
    onError: (error) => {
      console.error('Failed to add measure to API:', error);
    },
  });

  const addCalculatedFieldMutation = useMutation({
    mutationFn: async (data: Parameters<typeof modelingApi.addCalculatedField>[1]) => {
      console.log('Mutation function called with:', { semanticModelId, data });
      try {
        const result = await modelingApi.addCalculatedField(semanticModelId, data);
        console.log('API response received:', result);
        return result;
      } catch (error: any) {
        console.error('API call failed:', error);
        throw error;
      }
    },
    onSuccess: (calc) => {
      console.log('Calculated field added successfully:', calc);
      console.log('Adding to store, current semanticModelId:', semanticModelId);
      try {
        // Add to local store
        addCalculatedField(calc);
        console.log('Added to store successfully');
        setShowAddDialog(false);
      } catch (storeError) {
        console.error('Failed to add to store:', storeError);
        alert('Field was created but failed to update UI. Please refresh the page.');
      }
    },
    onError: (error: any) => {
      console.error('Failed to add calculated field:', error);
      console.error('Error details:', {
        message: error?.message,
        response: error?.response,
        data: error?.response?.data,
      });
      const errorMessage = error?.message || error?.response?.data?.detail || 'Unknown error';
      alert(`Failed to add calculated field: ${errorMessage}`);
    },
  });

  // Handle drop from schema browser columns
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const data = e.dataTransfer.getData('application/json');
    if (!data) {
      console.log('No data in drop event');
      return;
    }
    
    try {
      const dropData = JSON.parse(data);
      console.log('Drop data received:', dropData);
      
      // Only handle column drops
      if (dropData.type !== 'column') {
        console.log('Not a column drop, ignoring');
        return;
      }
      
      const { schemaName, tableName, columnName, dataType, normalizedType, isPrimaryKey } = dropData;
      
      // Auto-detect dimension type based on data type
      let dimensionType: DimensionType = 'categorical';
      if (normalizedType === 'timestamp' || normalizedType === 'date') {
        dimensionType = 'time';
      }
      
      if (activeSection === 'dimensions') {
        // Create dimension with auto-generated properties
        const newDimension: Dimension = {
          id: `dim-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          name: columnName.charAt(0).toUpperCase() + columnName.slice(1).replace(/_/g, ' '),
          sourceTable: `${schemaName}.${tableName}`,
          sourceColumn: columnName,
          dimensionType,
          description: isPrimaryKey ? 'Primary key field' : `${dataType} column from ${tableName}`,
          isVisible: true,
          hierarchyLevel: 0,
          defaultFormat: 'text',
          synonyms: [],
        };
        
        console.log('Adding dimension:', newDimension);
        
        // Add to local store immediately for instant feedback
        addDimension(newDimension);
        
        // Optionally sync to API in background (ignore errors for local-first approach)
        addDimensionMutation.mutate(newDimension);
      } else if (activeSection === 'measures') {
        // For measures, determine aggregation based on data type
        let aggregation: AggregationType = 'COUNT';
        if (['integer', 'decimal', 'number'].includes(normalizedType || '')) {
          aggregation = 'SUM';
        }
        
        // Create measure with all required properties
        const newMeasure: Measure = {
          id: `msr-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          name: `Total ${columnName.charAt(0).toUpperCase() + columnName.slice(1).replace(/_/g, ' ')}`,
          expression: columnName,
          aggregation,
          sourceTable: `${schemaName}.${tableName}`,
          description: `${aggregation} of ${columnName} from ${tableName}`,
          formatType: 'number',
          formatString: '#,##0',
          isVisible: true,
          isAdditive: aggregation === 'SUM' || aggregation === 'COUNT',
          dependsOn: [],
          filters: [],
          synonyms: [],
        };
        
        console.log('Adding measure:', newMeasure);
        
        // Store the local ID temporarily
        const localMeasureId = newMeasure.id;
        
        // Add to local store immediately for instant feedback
        addMeasure(newMeasure);
        
        // Sync to API and update with backend ID when it returns
        addMeasureMutation.mutate(newMeasure, {
          onSuccess: (backendMeasure) => {
            // Replace local measure with backend measure (which has the correct ID)
            if (backendMeasure.id !== localMeasureId) {
              // Remove the local measure with temporary ID
              removeMeasure(localMeasureId);
              // Add the backend measure with correct ID
              addMeasure(backendMeasure);
            }
          },
        });
      }
    } catch (error) {
      console.error('Failed to parse drop data:', error);
    }
  }, [activeSection, addDimension, addMeasure, removeMeasure, addDimensionMutation, addMeasureMutation]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  // Update mutations
  const updateDimensionMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      modelingApi.updateDimension(semanticModelId, id, data),
    onSuccess: (updatedDimension, { id, data }) => {
      // Update local store
      updateDimension(id, data);
      setEditItem(null);
      setShowAddDialog(false);
    },
    onError: (error) => {
      console.error('Failed to update dimension:', error);
      alert('Failed to update dimension. Please try again.');
    },
  });

  const updateMeasureMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      modelingApi.updateMeasure(semanticModelId, id, data),
    onSuccess: (updatedMeasure, { id, data }) => {
      // Update local store
      updateMeasure(id, data);
      setEditItem(null);
      setShowAddDialog(false);
    },
    onError: (error) => {
      console.error('Failed to update measure:', error);
      alert('Failed to update measure. Please try again.');
    },
  });

  // Update calculated field mutation
  const updateCalculatedFieldMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      modelingApi.updateCalculatedField(semanticModelId, id, data),
    onSuccess: (updated, { id, data }) => {
      updateCalculatedField(id, data);
      setEditItem(null);
      setShowAddDialog(false);
    },
    onError: (error) => {
      console.error('Failed to update calculated field:', error);
      alert('Failed to update calculated field. Please try again.');
    },
  });

  const removeDimensionMutation = useMutation({
    mutationFn: (id: string) => modelingApi.removeDimension(semanticModelId, id),
    onSuccess: (_, id) => removeDimension(id),
  });

  const removeMeasureMutation = useMutation({
    mutationFn: (id: string) => modelingApi.removeMeasure(semanticModelId, id),
    onSuccess: (_, id) => removeMeasure(id),
  });

  if (!semanticModel) {
    return (
      <div 
        className={cn(
          "h-full flex flex-col items-center justify-center text-slate-500 border-l border-slate-700 bg-slate-900 transition-all",
          isDragOver && "bg-indigo-500/10 border-2 border-dashed border-indigo-500/50"
        )}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragOver(false);
          
          const data = e.dataTransfer.getData('application/json');
          if (!data) return;
          
          try {
            const dropData = JSON.parse(data);
            if (dropData.type === 'column') {
              // Create a dimension and add to store directly
              const { schemaName, tableName, columnName, dataType, normalizedType, isPrimaryKey } = dropData;
              
              let dimensionType: DimensionType = 'categorical';
              if (normalizedType === 'timestamp' || normalizedType === 'date') {
                dimensionType = 'time';
              }
              
              const newDimension: Dimension = {
                id: `dim-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                name: columnName.charAt(0).toUpperCase() + columnName.slice(1).replace(/_/g, ' '),
                sourceTable: `${schemaName}.${tableName}`,
                sourceColumn: columnName,
                dimensionType,
                description: isPrimaryKey ? 'Primary key field' : `${dataType} column from ${tableName}`,
                isVisible: true,
                hierarchyLevel: 0,
                defaultFormat: 'text',
                synonyms: [],
              };
              
              console.log('Adding dimension (no semantic model):', newDimension);
              addDimension(newDimension);
            }
          } catch (error) {
            console.error('Failed to parse drop data:', error);
          }
        }}
        onDragOver={(e) => {
          e.preventDefault();
          e.dataTransfer.dropEffect = 'copy';
          setIsDragOver(true);
        }}
        onDragLeave={(e) => {
          e.preventDefault();
          setIsDragOver(false);
        }}
      >
        {isDragOver ? (
          <>
            <GripVertical className="w-8 h-8 mb-2 text-indigo-400" />
            <p className="text-sm text-indigo-300">Drop here to create a Dimension</p>
          </>
        ) : (
          <>
            <p className="text-sm">Select a semantic model to view</p>
            <p className="text-xs mt-2 text-slate-600">or drag columns here to create dimensions</p>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-slate-900 border-l border-slate-700">
      {/* Header */}
      <div className="p-4 border-b border-slate-700">
        <h3 className="font-semibold text-white mb-1">{semanticModel.name}</h3>
        <p className="text-sm text-slate-500">Semantic Model</p>
      </div>

      {/* Section Tabs */}
      <div className="flex border-b border-slate-700">
        <button
          onClick={() => setActiveSection('dimensions')}
          className={cn(
            'flex-1 px-4 py-3 text-sm font-medium transition-colors',
            activeSection === 'dimensions'
              ? 'text-indigo-400 border-b-2 border-indigo-400'
              : 'text-slate-400 hover:text-white'
          )}
        >
          Dimensions ({semanticModel.dimensions.length})
        </button>
        <button
          onClick={() => setActiveSection('measures')}
          className={cn(
            'flex-1 px-4 py-3 text-sm font-medium transition-colors',
            activeSection === 'measures'
              ? 'text-indigo-400 border-b-2 border-indigo-400'
              : 'text-slate-400 hover:text-white'
          )}
        >
          Measures ({semanticModel.measures.length})
        </button>
        <button
          onClick={() => setActiveSection('calculated')}
          className={cn(
            'flex-1 px-4 py-3 text-sm font-medium transition-colors',
            activeSection === 'calculated'
              ? 'text-indigo-400 border-b-2 border-indigo-400'
              : 'text-slate-400 hover:text-white'
          )}
        >
          Calculated ({semanticModel.calculatedFields.length})
        </button>
      </div>

      {/* Content - Drop Zone */}
      <div 
        className={cn(
          "flex-1 overflow-y-auto p-4 transition-all",
          isDragOver && "bg-indigo-500/10 border-2 border-dashed border-indigo-500/50"
        )}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        {/* Drop Zone Hint */}
        {isDragOver && (
          <div className="mb-4 p-4 bg-indigo-500/20 border border-indigo-500/30 rounded-lg text-center">
            <GripVertical className="w-6 h-6 mx-auto mb-2 text-indigo-400" />
            <p className="text-sm text-indigo-300">
              Drop column here to create a{' '}
              <span className="font-semibold">
                {activeSection === 'dimensions' ? 'Dimension' : activeSection === 'measures' ? 'Measure' : 'Field'}
              </span>
            </p>
          </div>
        )}

        {activeSection === 'dimensions' && (
          <DimensionsList
            dimensions={semanticModel.dimensions}
            selectedId={selectedDimensionId}
            onSelect={(dim) => {
              setSelectedDimension(dim.id);
              onDimensionSelect?.(dim);
            }}
            onDelete={(id) => removeDimensionMutation.mutate(id)}
            onEdit={setEditItem}
          />
        )}

        {activeSection === 'measures' && (
          <MeasuresList
            measures={semanticModel.measures}
            selectedId={selectedMeasureId}
            onSelect={(measure) => {
              setSelectedMeasure(measure.id);
              onMeasureSelect?.(measure);
            }}
            onDelete={(id) => removeMeasureMutation.mutate(id)}
            onEdit={setEditItem}
          />
        )}

        {activeSection === 'calculated' && (
          <CalculatedFieldsList
            fields={semanticModel.calculatedFields}
            onDelete={(id) => removeCalculatedField(id)}
            onEdit={setEditItem}
          />
        )}
      </div>

      {/* Add Button */}
      <div className="p-4 border-t border-slate-700">
        <button
          onClick={() => setShowAddDialog(true)}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add {activeSection === 'dimensions' ? 'Dimension' : activeSection === 'measures' ? 'Measure' : 'Calculated Field'}
        </button>
      </div>

      {/* Add/Edit Dialog */}
      {(showAddDialog || editItem) && (
        <AddFieldDialog
          type={activeSection}
          onClose={() => {
            setShowAddDialog(false);
            setEditItem(null);
          }}
          onAdd={(data) => {
            console.log('onAdd called with:', { activeSection, data });
            if (activeSection === 'dimensions') {
              addDimensionMutation.mutate(data as any);
            } else if (activeSection === 'measures') {
              addMeasureMutation.mutate(data as any);
            } else if (activeSection === 'calculated') {
              console.log('Adding calculated field with data:', data);
              addCalculatedFieldMutation.mutate(data as any);
            } else {
              console.error('Unknown section type:', activeSection);
            }
          }}
          onUpdate={(id, data) => {
            if (activeSection === 'dimensions') {
              updateDimensionMutation.mutate({ id, data });
            } else if (activeSection === 'measures') {
              updateMeasureMutation.mutate({ id, data });
            } else if (activeSection === 'calculated') {
              updateCalculatedFieldMutation.mutate({ id, data });
            }
          }}
          editItem={editItem}
          sourceId={activeSourceId || undefined}
          existingDimensions={semanticModel.dimensions}
          existingMeasures={semanticModel.measures}
          isLoading={
            addDimensionMutation.isPending || 
            addMeasureMutation.isPending ||
            addCalculatedFieldMutation.isPending ||
            updateDimensionMutation.isPending ||
            updateMeasureMutation.isPending ||
            updateCalculatedFieldMutation.isPending
          }
        />
      )}
    </div>
  );
}

// ============================================================================
// DIMENSIONS LIST
// ============================================================================

interface DimensionsListProps {
  dimensions: Dimension[];
  selectedId: string | null;
  onSelect: (dimension: Dimension) => void;
  onDelete: (id: string) => void;
  onEdit: (dimension: Dimension) => void;
}

function DimensionsList({
  dimensions,
  selectedId,
  onSelect,
  onDelete,
  onEdit,
}: DimensionsListProps) {
  // Handle drag start for dimension
  const handleDragStart = (e: React.DragEvent, dim: Dimension) => {
    e.dataTransfer.setData('application/json', JSON.stringify({
      type: 'dimension',
      id: dim.id,
      name: dim.name,
      sourceTable: dim.sourceTable,
      sourceColumn: dim.sourceColumn,
      dimensionType: dim.dimensionType,
    }));
    e.dataTransfer.effectAllowed = 'copy';
  };

  if (dimensions.length === 0) {
    return (
      <div className="text-center py-8 text-slate-500 border-2 border-dashed border-slate-700 rounded-lg">
        <Columns className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No dimensions defined</p>
        <p className="text-xs mt-1">Drag columns from Schema Browser to create dimensions</p>
        <p className="text-xs text-slate-600 mt-2">or click "Add Dimension" below</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-slate-500 mb-3 flex items-center gap-1">
        <span className="inline-block w-4 h-4 bg-slate-700 rounded text-[10px] flex items-center justify-center">↔</span>
        Drag dimensions to use in queries
      </p>
      {dimensions.map((dim) => (
        <div
          key={dim.id}
          draggable
          onDragStart={(e) => handleDragStart(e, dim)}
          onClick={() => onSelect(dim)}
          className={cn(
            'p-3 rounded-lg border cursor-grab active:cursor-grabbing transition-all group',
            selectedId === dim.id
              ? 'bg-indigo-500/10 border-indigo-500/50'
              : 'bg-slate-800/50 border-slate-700 hover:border-slate-600 hover:bg-slate-800'
          )}
          title={`Drag "${dim.name}" to use in query`}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              {dim.dimensionType === 'time' ? (
                <Calendar className="w-4 h-4 text-amber-400" />
              ) : dim.dimensionType === 'geo' ? (
                <Globe className="w-4 h-4 text-green-400" />
              ) : dim.dimensionType === 'hierarchical' ? (
                <Layers className="w-4 h-4 text-purple-400" />
              ) : (
                <Columns className="w-4 h-4 text-blue-400" />
              )}
              <div>
                <div className="text-sm font-medium text-white">{dim.name}</div>
                <div className="text-xs text-slate-500">
                  {dim.sourceTable}.{dim.sourceColumn}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onEdit(dim);
                }}
                className="p-1 hover:bg-slate-700 rounded"
              >
                <Edit2 className="w-3.5 h-3.5 text-slate-400" />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(dim.id);
                }}
                className="p-1 hover:bg-red-500/20 rounded"
              >
                <Trash2 className="w-3.5 h-3.5 text-slate-400 hover:text-red-400" />
              </button>
            </div>
          </div>
          {dim.description && (
            <p className="text-xs text-slate-500 mt-2">{dim.description}</p>
          )}
        </div>
      ))}
    </div>
  );
}

// ============================================================================
// MEASURES LIST
// ============================================================================

interface MeasuresListProps {
  measures: Measure[];
  selectedId: string | null;
  onSelect: (measure: Measure) => void;
  onDelete: (id: string) => void;
  onEdit: (measure: Measure) => void;
}

function MeasuresList({
  measures,
  selectedId,
  onSelect,
  onDelete,
  onEdit,
}: MeasuresListProps) {
  // Handle drag start for measure
  const handleDragStart = (e: React.DragEvent, measure: Measure) => {
    e.dataTransfer.setData('application/json', JSON.stringify({
      type: 'measure',
      id: measure.id,
      name: measure.name,
      aggregation: measure.aggregation,
      expression: measure.expression,
      formatType: measure.formatType,
    }));
    e.dataTransfer.effectAllowed = 'copy';
  };

  if (measures.length === 0) {
    return (
      <div className="text-center py-8 text-slate-500 border-2 border-dashed border-slate-700 rounded-lg">
        <Sigma className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No measures defined</p>
        <p className="text-xs mt-1">Drag numeric columns from Schema Browser to create measures</p>
        <p className="text-xs text-slate-600 mt-2">or click "Add Measure" below</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-slate-500 mb-3 flex items-center gap-1">
        <span className="inline-block w-4 h-4 bg-slate-700 rounded text-[10px] flex items-center justify-center">↔</span>
        Drag measures to use in queries
      </p>
      {measures.map((measure) => (
        <div
          key={measure.id}
          draggable
          onDragStart={(e) => handleDragStart(e, measure)}
          onClick={() => onSelect(measure)}
          className={cn(
            'p-3 rounded-lg border cursor-grab active:cursor-grabbing transition-all group',
            selectedId === measure.id
              ? 'bg-indigo-500/10 border-indigo-500/50'
              : 'bg-slate-800/50 border-slate-700 hover:border-slate-600 hover:bg-slate-800'
          )}
          title={`Drag "${measure.name}" to use in query`}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              {measure.formatType === 'currency' ? (
                <DollarSign className="w-4 h-4 text-green-400" />
              ) : measure.formatType === 'percent' ? (
                <Percent className="w-4 h-4 text-amber-400" />
              ) : (
                <Sigma className="w-4 h-4 text-indigo-400" />
              )}
              <div>
                <div className="text-sm font-medium text-white">{measure.name}</div>
                <div className="text-xs text-slate-500 font-mono">
                  {measure.aggregation}({measure.expression})
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onEdit(measure);
                }}
                className="p-1 hover:bg-slate-700 rounded"
              >
                <Edit2 className="w-3.5 h-3.5 text-slate-400" />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(measure.id);
                }}
                className="p-1 hover:bg-red-500/20 rounded"
              >
                <Trash2 className="w-3.5 h-3.5 text-slate-400 hover:text-red-400" />
              </button>
            </div>
          </div>
          {measure.description && (
            <p className="text-xs text-slate-500 mt-2">{measure.description}</p>
          )}
        </div>
      ))}
    </div>
  );
}

// ============================================================================
// CALCULATED FIELDS LIST
// ============================================================================

interface CalculatedFieldsListProps {
  fields: CalculatedField[];
  onDelete: (id: string) => void;
  onEdit: (field: CalculatedField) => void;
}

function CalculatedFieldsList({
  fields,
  onDelete,
  onEdit,
}: CalculatedFieldsListProps) {
  if (fields.length === 0) {
    return (
      <div className="text-center py-8 text-slate-500">
        <Calculator className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No calculated fields</p>
        <p className="text-xs mt-1">Create expressions that derive from other fields</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {fields.map((field) => (
        <div
          key={field.id}
          className="p-3 rounded-lg border bg-slate-800/50 border-slate-700 hover:border-slate-600 transition-all group"
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <Calculator className="w-4 h-4 text-purple-400" />
              <div>
                <div className="text-sm font-medium text-white">{field.name}</div>
                <div className="text-xs text-slate-500 font-mono truncate max-w-[200px]">
                  {field.expression}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={() => onEdit(field)}
                className="p-1 hover:bg-slate-700 rounded"
              >
                <Edit2 className="w-3.5 h-3.5 text-slate-400" />
              </button>
              <button
                onClick={() => onDelete(field.id)}
                className="p-1 hover:bg-red-500/20 rounded"
              >
                <Trash2 className="w-3.5 h-3.5 text-slate-400 hover:text-red-400" />
              </button>
            </div>
          </div>
          {field.referencedFields.length > 0 && (
            <div className="flex gap-1 mt-2">
              {field.referencedFields.map((ref) => (
                <span
                  key={ref}
                  className="text-xs px-1.5 py-0.5 bg-slate-700 rounded text-slate-400"
                >
                  {ref}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ============================================================================
// ADD FIELD DIALOG
// ============================================================================

interface AddFieldDialogProps {
  type: 'dimensions' | 'measures' | 'calculated';
  onClose: () => void;
  onAdd: (data: any) => void;
  onUpdate?: (id: string, data: any) => void;
  editItem?: Dimension | Measure | CalculatedField | null;
  isLoading?: boolean;
  sourceId?: string;
  existingDimensions?: Dimension[];
  existingMeasures?: Measure[];
}

// Measure example hints
const MEASURE_HINTS = [
  { name: 'Total Revenue', aggregation: 'SUM', expression: 'amount', hint: 'Sum all values' },
  { name: 'Order Count', aggregation: 'COUNT', expression: 'order_id', hint: 'Count all rows' },
  { name: 'Unique Customers', aggregation: 'COUNT_DISTINCT', expression: 'customer_id', hint: 'Count unique values' },
  { name: 'Average Order Value', aggregation: 'AVG', expression: 'amount', hint: 'Calculate average' },
  { name: 'Highest Sale', aggregation: 'MAX', expression: 'amount', hint: 'Find maximum value' },
];

// Dimension type compatibility with data types
const DIMENSION_TYPE_COMPATIBILITY: Record<DimensionType, string[]> = {
  categorical: ['string', 'varchar', 'char', 'text', 'integer', 'int', 'bigint', 'smallint', 'boolean', 'bool'],
  time: ['date', 'datetime', 'timestamp', 'time', 'timestamptz'],
  geo: ['string', 'varchar', 'char', 'text'],
  hierarchical: ['string', 'varchar', 'char', 'text', 'integer', 'int', 'bigint'],
};

// Get compatible dimension types for a data type
const getCompatibleDimensionTypes = (dataType: string): DimensionType[] => {
  const normalizedType = dataType.toLowerCase().replace(/\(.*\)/, '').trim();
  const compatible: DimensionType[] = [];
  
  for (const [dimType, compatibleTypes] of Object.entries(DIMENSION_TYPE_COMPATIBILITY)) {
    if (compatibleTypes.some(t => normalizedType.includes(t))) {
      compatible.push(dimType as DimensionType);
    }
  }
  
  // Default to categorical if no match
  return compatible.length > 0 ? compatible : ['categorical'];
};

interface TableInfo {
  schemaName: string;
  tableName: string;
  fullName: string;
}

interface ColumnInfo {
  name: string;
  dataType: string;
  normalizedType?: string;
}

function AddFieldDialog({ 
  type, 
  onClose, 
  onAdd, 
  onUpdate, 
  editItem, 
  isLoading,
  sourceId,
  existingDimensions = [],
  existingMeasures = [],
}: AddFieldDialogProps) {
  const isEditing = !!editItem;
  
  // Initialize state from editItem if editing
  const [name, setName] = useState(editItem?.name || '');
  const [sourceColumn, setSourceColumn] = useState(
    (editItem as Dimension)?.sourceColumn || ''
  );
  const [sourceTable, setSourceTable] = useState(
    (editItem as Dimension | Measure)?.sourceTable || ''
  );
  const [expression, setExpression] = useState(
    (editItem as Measure | CalculatedField)?.expression || ''
  );
  const [aggregation, setAggregation] = useState<AggregationType>(
    (editItem as Measure)?.aggregation || 'SUM'
  );
  const [dimensionType, setDimensionType] = useState<DimensionType>(
    (editItem as Dimension)?.dimensionType || 'categorical'
  );
  const [description, setDescription] = useState(editItem?.description || '');
  const [validationResult, setValidationResult] = useState<{ valid: boolean; errors: string[] } | null>(null);
  const [showHints, setShowHints] = useState(!isEditing);

  // Autocomplete state
  const [availableTables, setAvailableTables] = useState<TableInfo[]>([]);
  const [availableColumns, setAvailableColumns] = useState<ColumnInfo[]>([]);
  const [filteredTables, setFilteredTables] = useState<TableInfo[]>([]);
  const [filteredColumns, setFilteredColumns] = useState<ColumnInfo[]>([]);
  const [showTableSuggestions, setShowTableSuggestions] = useState(false);
  const [showColumnSuggestions, setShowColumnSuggestions] = useState(false);
  const [selectedColumnDataType, setSelectedColumnDataType] = useState<string>('');
  const [compatibleDimensionTypes, setCompatibleDimensionTypes] = useState<DimensionType[]>(['categorical', 'time', 'geo', 'hierarchical']);

  // Loading state
  const [isLoadingTables, setIsLoadingTables] = useState(false);
  const [isLoadingColumns, setIsLoadingColumns] = useState(false);

  // Validation state
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  // Fetch available tables when sourceId changes
  useEffect(() => {
    if (!sourceId) {
      setAvailableTables([]);
      return;
    }
    
    const fetchTables = async () => {
      setIsLoadingTables(true);
      try {
        const schemas = await modelingApi.getSchemas(sourceId);
        const allTables: TableInfo[] = [];
        
        for (const schema of schemas) {
          try {
            const tables = await modelingApi.getTables(sourceId, schema.name);
            tables.forEach(t => {
              allTables.push({
                schemaName: schema.name,
                tableName: t.tableName,
                fullName: `${schema.name}.${t.tableName}`,
              });
            });
          } catch (e) {
            console.warn(`Failed to fetch tables for schema ${schema.name}:`, e);
          }
        }
        
        setAvailableTables(allTables);
      } catch (e) {
        console.warn('Failed to fetch schemas:', e);
      } finally {
        setIsLoadingTables(false);
      }
    };
    
    fetchTables();
  }, [sourceId]);

  // Fetch columns when source table changes
  useEffect(() => {
    if (!sourceId || !sourceTable) {
      setAvailableColumns([]);
      setSelectedColumnDataType('');
      return;
    }
    
    const parts = sourceTable.split('.');
    if (parts.length !== 2) {
      setAvailableColumns([]);
      return;
    }
    
    const [schemaName, tableName] = parts;
    
    const fetchColumns = async () => {
      setIsLoadingColumns(true);
      try {
        const columns = await modelingApi.getColumns(sourceId, schemaName, tableName);
        setAvailableColumns(columns.map(c => ({
          name: c.name,
          dataType: c.dataType,
          normalizedType: c.normalizedType,
        })));
      } catch (e) {
        console.warn('Failed to fetch columns:', e);
        setAvailableColumns([]);
      } finally {
        setIsLoadingColumns(false);
      }
    };
    
    fetchColumns();
  }, [sourceId, sourceTable]);

  // Filter tables based on input (3+ characters)
  useEffect(() => {
    if (sourceTable.length >= 3) {
      const filtered = availableTables.filter(t => 
        t.fullName.toLowerCase().includes(sourceTable.toLowerCase()) ||
        t.tableName.toLowerCase().includes(sourceTable.toLowerCase())
      );
      setFilteredTables(filtered);
      setShowTableSuggestions(filtered.length > 0);
    } else {
      setFilteredTables([]);
      setShowTableSuggestions(false);
    }
  }, [sourceTable, availableTables]);

  // Filter columns based on input (3+ characters)
  useEffect(() => {
    if (sourceColumn.length >= 3) {
      const filtered = availableColumns.filter(c => 
        c.name.toLowerCase().includes(sourceColumn.toLowerCase())
      );
      setFilteredColumns(filtered);
      setShowColumnSuggestions(filtered.length > 0);
    } else {
      setFilteredColumns([]);
      setShowColumnSuggestions(false);
    }
  }, [sourceColumn, availableColumns]);

  // Update compatible dimension types when column is selected
  useEffect(() => {
    if (selectedColumnDataType) {
      const compatible = getCompatibleDimensionTypes(selectedColumnDataType);
      setCompatibleDimensionTypes(compatible);
      
      // If current dimension type is not compatible, switch to first compatible
      if (!compatible.includes(dimensionType)) {
        setDimensionType(compatible[0]);
      }
    } else {
      setCompatibleDimensionTypes(['categorical', 'time', 'geo', 'hierarchical']);
    }
  }, [selectedColumnDataType]);

  // Validate on change
  useEffect(() => {
    const errors: string[] = [];
    
    // Check for duplicate dimension/measure name
    if (type === 'dimensions' && !isEditing) {
      const isDuplicate = existingDimensions.some(d => 
        d.name.toLowerCase() === name.toLowerCase() ||
        (d.sourceTable === sourceTable && d.sourceColumn === sourceColumn && sourceColumn)
      );
      if (isDuplicate && name) {
        errors.push('A dimension with this name or source column already exists');
      }
    }
    
    if (type === 'measures' && !isEditing) {
      const isDuplicate = existingMeasures.some(m => 
        m.name.toLowerCase() === name.toLowerCase()
      );
      if (isDuplicate && name) {
        errors.push('A measure with this name already exists');
      }
    }
    
    // ==================== DIMENSION VALIDATION ====================
    if (type === 'dimensions') {
      // Require source table and column
      if (!sourceTable) {
        errors.push('Source table is required for dimensions');
      }
      if (!sourceColumn) {
        errors.push('Source column is required for dimensions');
      }
      
      // Validate source table exists (only if tables are loaded)
      if (sourceTable && availableTables.length > 0) {
        const tableExists = availableTables.some(t => t.fullName === sourceTable);
        if (!tableExists) {
          errors.push(`Source table "${sourceTable}" does not exist. Please select from suggestions.`);
        }
      }
      
      // Validate source column exists (only if columns are loaded)
      if (sourceColumn && availableColumns.length > 0) {
        const columnExists = availableColumns.some(c => c.name === sourceColumn);
        if (!columnExists) {
          errors.push(`Source column "${sourceColumn}" does not exist in table "${sourceTable}".`);
        }
      }
      
      // Show warning if schema data hasn't loaded yet
      if (sourceId && !isLoadingTables && availableTables.length === 0) {
        errors.push('Schema data not available. Please wait for tables to load.');
      }
      
      // Show warning if columns haven't loaded for selected table
      if (sourceTable && !isLoadingColumns && availableColumns.length === 0 && availableTables.some(t => t.fullName === sourceTable)) {
        errors.push('Column data not available. Please wait for columns to load.');
      }
      
      // Validate dimension type compatibility
      if (selectedColumnDataType && !compatibleDimensionTypes.includes(dimensionType)) {
        errors.push(`"${dimensionType}" is not compatible with "${selectedColumnDataType}". Use: ${compatibleDimensionTypes.join(', ')}`);
      }
    }
    
    // ==================== MEASURE VALIDATION ====================
    if (type === 'measures') {
      // Require expression
      if (!expression && !sourceColumn) {
        errors.push('Expression or source column is required for measures');
      }
      
      // Validate source table if provided
      if (sourceTable && availableTables.length > 0) {
        const tableExists = availableTables.some(t => t.fullName === sourceTable);
        if (!tableExists) {
          errors.push(`Source table "${sourceTable}" does not exist. Please select from suggestions.`);
        }
      }
      
      // Validate column reference in expression (basic check)
      if (expression && sourceTable && availableColumns.length > 0) {
        // Extract column references from expression (simple check for single column name)
        const simpleColumnMatch = expression.match(/^[a-zA-Z_][a-zA-Z0-9_]*$/);
        if (simpleColumnMatch) {
          const columnExists = availableColumns.some(c => c.name.toLowerCase() === expression.toLowerCase());
          if (!columnExists) {
            errors.push(`Column "${expression}" not found in table "${sourceTable}".`);
          }
        }
      }
      
      // Validate aggregation is selected
      if (!aggregation) {
        errors.push('Aggregation type is required for measures');
      }
    }
    
    // ==================== CALCULATED FIELD VALIDATION ====================
    if (type === 'calculated') {
      // Require expression
      if (!expression) {
        errors.push('Expression is required for calculated fields');
      }
      
      // Basic expression syntax validation
      if (expression) {
        // Check for basic syntax errors (unbalanced brackets, etc.)
        const openBrackets = (expression.match(/\[/g) || []).length;
        const closeBrackets = (expression.match(/\]/g) || []).length;
        if (openBrackets !== closeBrackets) {
          errors.push('Expression has unbalanced brackets [ ]');
        }
        
        const openParens = (expression.match(/\(/g) || []).length;
        const closeParens = (expression.match(/\)/g) || []).length;
        if (openParens !== closeParens) {
          errors.push('Expression has unbalanced parentheses ( )');
        }
      }
    }
    
    setValidationErrors(errors);
  }, [name, sourceTable, sourceColumn, expression, aggregation, dimensionType, selectedColumnDataType, type, isEditing, existingDimensions, existingMeasures, compatibleDimensionTypes, availableTables, availableColumns, isLoadingTables, isLoadingColumns, sourceId]);

  const handleSelectTable = (table: TableInfo) => {
    setSourceTable(table.fullName);
    setShowTableSuggestions(false);
    setSourceColumn(''); // Reset column when table changes
    setAvailableColumns([]); // Will be refetched
    setSelectedColumnDataType('');
  };

  const handleSelectColumn = (column: ColumnInfo) => {
    setSourceColumn(column.name);
    setSelectedColumnDataType(column.dataType);
    setShowColumnSuggestions(false);
    
    // Auto-suggest dimension type based on data type
    const compatible = getCompatibleDimensionTypes(column.dataType);
    if (compatible.length > 0 && !compatible.includes(dimensionType)) {
      setDimensionType(compatible[0]);
    }
  };

  // Validate column when manually typed (on blur)
  const handleColumnBlur = () => {
    if (sourceColumn && availableColumns.length > 0) {
      const matchingCol = availableColumns.find(c => c.name.toLowerCase() === sourceColumn.toLowerCase());
      if (matchingCol) {
        // Auto-correct case if needed
        setSourceColumn(matchingCol.name);
        setSelectedColumnDataType(matchingCol.dataType);
        
        // Update compatible dimension types
        const compatible = getCompatibleDimensionTypes(matchingCol.dataType);
        setCompatibleDimensionTypes(compatible);
        if (!compatible.includes(dimensionType)) {
          setDimensionType(compatible[0]);
        }
      } else {
        // Column not found - clear data type
        setSelectedColumnDataType('');
      }
    }
  };

  const validateExpression = async () => {
    if (!expression) return;
    try {
      const result = await modelingApi.validateExpression(expression);
      setValidationResult(result);
    } catch (e) {
      setValidationResult({ valid: false, errors: ['Validation failed'] });
    }
  };

  const applyMeasureHint = (hint: typeof MEASURE_HINTS[0]) => {
    setName(hint.name);
    setAggregation(hint.aggregation as AggregationType);
    setExpression(hint.expression);
    setShowHints(false);
  };

  const canSubmit = name && validationErrors.length === 0;

  const handleSubmit = () => {
    if (!canSubmit) return;
    
    const data = type === 'dimensions' 
      ? {
          name,
          sourceColumn,
          sourceTable,
          description,
          dimensionType,
        }
      : type === 'measures'
      ? {
          name,
          expression: expression || sourceColumn,
          aggregation,
          sourceTable,
          description,
        }
      : {
          name,
          expression,
          description,
          resultType: 'number', // Default result type for calculated fields
        };

    if (isEditing && editItem && onUpdate) {
      onUpdate(editItem.id, data);
    } else {
      onAdd(data);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-slate-800 border border-slate-600 rounded-xl shadow-2xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-semibold text-white mb-4">
          {isEditing ? 'Edit' : 'Add'} {type === 'dimensions' ? 'Dimension' : type === 'measures' ? 'Measure' : 'Calculated Field'}
        </h3>

        {/* Measure Hints */}
        {type === 'measures' && showHints && (
          <div className="mb-4 p-3 bg-slate-700/50 border border-slate-600 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-slate-400">💡 Quick Start Examples</span>
              <button
                onClick={() => setShowHints(false)}
                className="text-xs text-slate-500 hover:text-slate-300"
              >
                Hide
              </button>
            </div>
            <div className="grid grid-cols-1 gap-1">
              {MEASURE_HINTS.map((hint) => (
                <button
                  key={hint.name}
                  onClick={() => applyMeasureHint(hint)}
                  className="flex items-center justify-between px-2 py-1.5 text-left rounded hover:bg-slate-600 transition-colors group"
                >
                  <span className="text-xs text-slate-300 group-hover:text-white">{hint.name}</span>
                  <span className="text-[10px] text-slate-500 group-hover:text-slate-400">
                    {hint.aggregation}({hint.expression})
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-4">
          {/* Name */}
          <div>
            <label className="text-sm font-medium text-slate-300 mb-1 block">
              Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={type === 'dimensions' ? 'e.g., Customer Region' : 'e.g., Total Revenue'}
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* Source Table & Column (for dimensions and measures) */}
          {type !== 'calculated' && (
            <div className="grid grid-cols-2 gap-4">
              {/* Source Table with Autocomplete */}
              <div className="relative">
                <label className="text-sm font-medium text-slate-300 mb-1 block">
                  Source Table {type === 'dimensions' && <span className="text-red-400">*</span>}
                  {isLoadingTables && <span className="text-xs text-slate-500 ml-2">(loading...)</span>}
                </label>
                <input
                  type="text"
                  value={sourceTable}
                  onChange={(e) => setSourceTable(e.target.value)}
                  onFocus={() => sourceTable.length >= 3 && setShowTableSuggestions(filteredTables.length > 0)}
                  onBlur={() => setTimeout(() => setShowTableSuggestions(false), 200)}
                  placeholder={isLoadingTables ? "Loading tables..." : "Type 3+ chars to search..."}
                  disabled={isLoadingTables}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
                />
                {showTableSuggestions && filteredTables.length > 0 && (
                  <div className="absolute z-10 w-full mt-1 bg-slate-700 border border-slate-600 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                    {filteredTables.map((table) => (
                      <button
                        key={table.fullName}
                        type="button"
                        onClick={() => handleSelectTable(table)}
                        className="w-full px-3 py-2 text-left text-sm text-slate-300 hover:bg-slate-600 hover:text-white transition-colors"
                      >
                        <span className="font-medium">{table.tableName}</span>
                        <span className="text-slate-500 ml-1">({table.schemaName})</span>
                      </button>
                    ))}
                  </div>
                )}
                {sourceTable && availableTables.length > 0 && !availableTables.some(t => t.fullName === sourceTable) && (
                  <p className="text-xs text-amber-500 mt-1">⚠ Table not found in schema</p>
                )}
              </div>

              {/* Source Column with Autocomplete */}
              <div className="relative">
                <label className="text-sm font-medium text-slate-300 mb-1 block">
                  Source Column {type === 'dimensions' && <span className="text-red-400">*</span>}
                  {isLoadingColumns && <span className="text-xs text-slate-500 ml-2">(loading...)</span>}
                </label>
                <input
                  type="text"
                  value={sourceColumn}
                  onChange={(e) => {
                    setSourceColumn(e.target.value);
                    // Clear selected column data type when manually typing
                    const matchingCol = availableColumns.find(c => c.name === e.target.value);
                    setSelectedColumnDataType(matchingCol?.dataType || '');
                  }}
                  onFocus={() => sourceColumn.length >= 3 && setShowColumnSuggestions(filteredColumns.length > 0)}
                  onBlur={() => {
                    setTimeout(() => setShowColumnSuggestions(false), 200);
                    handleColumnBlur();
                  }}
                  placeholder={!sourceTable ? "Select table first" : isLoadingColumns ? "Loading columns..." : "Type 3+ chars to search..."}
                  disabled={!sourceTable || isLoadingColumns}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
                />
                {showColumnSuggestions && filteredColumns.length > 0 && (
                  <div className="absolute z-10 w-full mt-1 bg-slate-700 border border-slate-600 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                    {filteredColumns.map((column) => (
                      <button
                        key={column.name}
                        type="button"
                        onClick={() => handleSelectColumn(column)}
                        className="w-full px-3 py-2 text-left text-sm text-slate-300 hover:bg-slate-600 hover:text-white transition-colors flex justify-between items-center"
                      >
                        <span className="font-medium">{column.name}</span>
                        <span className="text-xs text-slate-500 bg-slate-800 px-2 py-0.5 rounded">{column.dataType}</span>
                      </button>
                    ))}
                  </div>
                )}
                {selectedColumnDataType && (
                  <p className="text-xs text-slate-400 mt-1">
                    Type: <span className="text-indigo-400">{selectedColumnDataType}</span>
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Dimension Type (for dimensions) */}
          {type === 'dimensions' && (
            <div>
              <label className="text-sm font-medium text-slate-300 mb-2 block">
                Dimension Type
                {selectedColumnDataType && (
                  <span className="text-xs font-normal text-slate-500 ml-2">
                    (based on {selectedColumnDataType} column)
                  </span>
                )}
              </label>
              <div className="grid grid-cols-4 gap-2">
                {DIMENSION_TYPES.map((dt) => {
                  const isCompatible = compatibleDimensionTypes.includes(dt.value);
                  return (
                    <button
                      key={dt.value}
                      onClick={() => isCompatible && setDimensionType(dt.value)}
                      disabled={!isCompatible && !!selectedColumnDataType}
                      title={
                        !isCompatible && selectedColumnDataType
                          ? `Not compatible with ${selectedColumnDataType} type`
                          : dt.value === 'categorical' ? 'For text/category data'
                          : dt.value === 'time' ? 'For date/timestamp data'
                          : dt.value === 'geo' ? 'For location/region data'
                          : 'For hierarchical data'
                      }
                      className={cn(
                        'px-3 py-2 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-1',
                        dimensionType === dt.value
                          ? 'bg-indigo-500 text-white'
                          : !isCompatible && selectedColumnDataType
                          ? 'bg-slate-800 text-slate-500 cursor-not-allowed opacity-50'
                          : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                      )}
                    >
                      <dt.icon className="w-3.5 h-3.5" />
                      {dt.label}
                    </button>
                  );
                })}
              </div>
              {selectedColumnDataType && (
                <p className="text-xs text-slate-500 mt-2">
                  💡 Compatible types highlighted based on column data type
                </p>
              )}
            </div>
          )}

          {/* Aggregation (for measures) */}
          {type === 'measures' && (
            <div>
              <label className="text-sm font-medium text-slate-300 mb-2 block">
                Aggregation
              </label>
              <div className="grid grid-cols-3 gap-2">
                {AGGREGATION_OPTIONS.map((agg) => (
                  <button
                    key={agg.value}
                    onClick={() => setAggregation(agg.value)}
                    title={
                      agg.value === 'SUM' ? 'Add up all values (e.g., total revenue)' :
                      agg.value === 'COUNT' ? 'Count all rows (e.g., number of orders)' :
                      agg.value === 'COUNT_DISTINCT' ? 'Count unique values (e.g., unique customers)' :
                      agg.value === 'AVG' ? 'Calculate average (e.g., average order value)' :
                      agg.value === 'MIN' ? 'Find minimum value (e.g., lowest price)' :
                      agg.value === 'MAX' ? 'Find maximum value (e.g., highest sale)' : ''
                    }
                    className={cn(
                      'px-3 py-2 rounded-lg text-sm font-medium transition-all',
                      aggregation === agg.value
                        ? 'bg-indigo-500 text-white'
                        : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                    )}
                  >
                    {agg.label}
                  </button>
                ))}
              </div>
              <p className="text-xs text-slate-500 mt-2">
                💡 Hover over options for descriptions
              </p>
            </div>
          )}

          {/* Expression (for measures and calculated) */}
          {(type === 'measures' || type === 'calculated') && (
            <div>
              <label className="text-sm font-medium text-slate-300 mb-1 block">
                Expression
              </label>
              <textarea
                value={expression}
                onChange={(e) => setExpression(e.target.value)}
                onBlur={validateExpression}
                placeholder={type === 'calculated' ? '[Revenue] / [Orders]' : 'column_name or expression'}
                rows={3}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono text-sm"
              />
              {/* Expression hints for measures */}
              {type === 'measures' && !expression && (
                <div className="mt-2 text-xs text-slate-500 space-y-1">
                  <p>💡 <strong>Tip:</strong> Enter a column name like <code className="px-1 bg-slate-700 rounded">amount</code> or <code className="px-1 bg-slate-700 rounded">price * quantity</code></p>
                  <p>Common patterns:</p>
                  <ul className="pl-4 list-disc space-y-0.5">
                    <li>Simple column: <code className="px-1 bg-slate-700 rounded">revenue</code></li>
                    <li>Math expression: <code className="px-1 bg-slate-700 rounded">price * quantity</code></li>
                    <li>Conditional: <code className="px-1 bg-slate-700 rounded">CASE WHEN status='paid' THEN amount ELSE 0 END</code></li>
                  </ul>
                </div>
              )}
              {/* Expression hints for calculated */}
              {type === 'calculated' && !expression && (
                <div className="mt-2 text-xs text-slate-500 space-y-1">
                  <p>💡 <strong>Tip:</strong> Reference other fields using square brackets</p>
                  <p>Examples:</p>
                  <ul className="pl-4 list-disc space-y-0.5">
                    <li>Ratio: <code className="px-1 bg-slate-700 rounded">[Revenue] / [Orders]</code></li>
                    <li>Percent: <code className="px-1 bg-slate-700 rounded">[Revenue] / [Total Revenue] * 100</code></li>
                    <li>Growth: <code className="px-1 bg-slate-700 rounded">([Current] - [Previous]) / [Previous]</code></li>
                  </ul>
                </div>
              )}
              {validationResult && (
                <div
                  className={cn(
                    'mt-2 flex items-center gap-2 text-sm',
                    validationResult.valid ? 'text-green-400' : 'text-red-400'
                  )}
                >
                  {validationResult.valid ? (
                    <CheckCircle2 className="w-4 h-4" />
                  ) : (
                    <AlertCircle className="w-4 h-4" />
                  )}
                  {validationResult.valid
                    ? 'Expression is valid'
                    : validationResult.errors.join(', ')}
                </div>
              )}
            </div>
          )}

          {/* Description */}
          <div>
            <label className="text-sm font-medium text-slate-300 mb-1 block">
              Description (optional)
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description..."
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-slate-300 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!canSubmit || isLoading}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
            {isEditing ? 'Update' : 'Add'} {type === 'dimensions' ? 'Dimension' : type === 'measures' ? 'Measure' : 'Field'}
          </button>
        </div>

        {/* Validation Errors */}
        {validationErrors.length > 0 && (
          <div className="mt-4 p-3 bg-red-900/30 border border-red-800 rounded-lg">
            <p className="text-sm font-medium text-red-400 mb-1">⚠ Validation Errors</p>
            <ul className="list-disc list-inside text-sm text-red-300 space-y-1">
              {validationErrors.map((error, i) => (
                <li key={i}>{error}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

