/**
 * Modeling Store
 * 
 * Global state management for the BI Modeling UI using Zustand.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  DataSource,
  SchemaInfo,
  TableInfo,
  ColumnInfo,
  ERDModel,
  TableNode,
  RelationshipEdge,
  SemanticModel,
  Dimension,
  Measure,
  CalculatedField,
  QueryResult,
  Position,
} from '../types/modeling';

// ============================================================================
// TYPES
// ============================================================================

interface SchemaTreeState {
  expandedSchemas: Set<string>;
  expandedTables: Set<string>;
  selectedTable: string | null;
  searchQuery: string;
}

interface ERDCanvasState {
  zoom: number;
  pan: Position;
  selectedNodeIds: Set<string>;
  selectedEdgeIds: Set<string>;
  isDragging: boolean;
  isConnecting: boolean;
  connectionSource: { nodeId: string; column: string } | null;
}

interface QueryWorkbenchState {
  mode: 'semantic' | 'sql';
  sqlText: string;
  selectedDimensions: string[];
  selectedMeasures: string[];
  activeTab: 'results' | 'chart' | 'sql';
  queryHistory: Array<{
    timestamp: number;
    query: string;
    executionTime: number;
  }>;
}

interface ModelingStore {
  // =========================================================================
  // DATA SOURCES
  // =========================================================================
  sources: DataSource[];
  activeSourceId: string | null;
  setSources: (sources: DataSource[]) => void;
  setActiveSource: (sourceId: string | null) => void;
  
  // =========================================================================
  // SCHEMA TREE
  // =========================================================================
  schemas: SchemaInfo[];
  tables: Record<string, TableInfo[]>; // schemaName -> tables
  columns: Record<string, ColumnInfo[]>; // fullTableName -> columns
  schemaTree: SchemaTreeState;
  setSchemas: (schemas: SchemaInfo[]) => void;
  setTables: (schemaName: string, tables: TableInfo[]) => void;
  setColumns: (fullTableName: string, columns: ColumnInfo[]) => void;
  toggleSchemaExpanded: (schemaName: string) => void;
  toggleTableExpanded: (fullTableName: string) => void;
  setSelectedTable: (fullTableName: string | null) => void;
  setSchemaSearchQuery: (query: string) => void;
  clearSchemaCache: () => void;
  
  // =========================================================================
  // ERD MODEL
  // =========================================================================
  erdModels: ERDModel[];
  activeERDId: string | null;
  erdCanvas: ERDCanvasState;
  setERDModels: (models: ERDModel[]) => void;
  setActiveERD: (modelId: string | null) => void;
  getActiveERD: () => ERDModel | null;
  addLocalERDModel: (model: ERDModel) => void;
  updateERDNode: (nodeId: string, updates: Partial<TableNode>) => void;
  addERDNode: (node: TableNode) => void;
  removeERDNode: (nodeId: string) => void;
  addERDEdge: (edge: RelationshipEdge) => void;
  removeERDEdge: (edgeId: string) => void;
  setERDZoom: (zoom: number) => void;
  setERDPan: (pan: Position) => void;
  selectNodes: (nodeIds: string[]) => void;
  selectEdges: (edgeIds: string[]) => void;
  clearSelection: () => void;
  startConnection: (nodeId: string, column: string) => void;
  endConnection: () => void;
  
  // =========================================================================
  // SEMANTIC MODEL
  // =========================================================================
  semanticModels: SemanticModel[];
  activeSemanticId: string | null;
  selectedDimensionId: string | null;
  selectedMeasureId: string | null;
  setSemanticModels: (models: SemanticModel[]) => void;
  setActiveSemantic: (modelId: string | null) => void;
  getActiveSemantic: () => SemanticModel | null;
  addLocalSemanticModel: (model: SemanticModel) => void;
  addDimension: (dimension: Dimension) => void;
  removeDimension: (dimensionId: string) => void;
  updateDimension: (dimensionId: string, updates: Partial<Dimension>) => void;
  addMeasure: (measure: Measure) => void;
  removeMeasure: (measureId: string) => void;
  updateMeasure: (measureId: string, updates: Partial<Measure>) => void;
  addCalculatedField: (calc: CalculatedField) => void;
  removeCalculatedField: (calcId: string) => void;
  updateCalculatedField: (calcId: string, updates: Partial<CalculatedField>) => void;
  setSelectedDimension: (dimensionId: string | null) => void;
  setSelectedMeasure: (measureId: string | null) => void;
  
  // =========================================================================
  // QUERY WORKBENCH
  // =========================================================================
  queryWorkbench: QueryWorkbenchState;
  queryResult: QueryResult | null;
  isQueryRunning: boolean;
  queryError: string | null;
  setQueryMode: (mode: 'semantic' | 'sql') => void;
  setSqlText: (sql: string) => void;
  setSelectedQueryDimensions: (dimensions: string[]) => void;
  setSelectedQueryMeasures: (measures: string[]) => void;
  setQueryActiveTab: (tab: 'results' | 'chart' | 'sql') => void;
  setQueryResult: (result: QueryResult | null) => void;
  setQueryRunning: (running: boolean) => void;
  setQueryError: (error: string | null) => void;
  addToQueryHistory: (query: string, executionTime: number) => void;
  
  // =========================================================================
  // UI STATE
  // =========================================================================
  schemaPanelWidth: number;
  propertiesPanelWidth: number;
  bottomPanelHeight: number;
  setSchemaPanelWidth: (width: number) => void;
  setPropertiesPanelWidth: (width: number) => void;
  setBottomPanelHeight: (height: number) => void;
  
  // =========================================================================
  // RESET
  // =========================================================================
  reset: () => void;
}

// ============================================================================
// INITIAL STATE
// ============================================================================

const initialSchemaTree: SchemaTreeState = {
  expandedSchemas: new Set(),
  expandedTables: new Set(),
  selectedTable: null,
  searchQuery: '',
};

const initialERDCanvas: ERDCanvasState = {
  zoom: 1,
  pan: { x: 0, y: 0 },
  selectedNodeIds: new Set(),
  selectedEdgeIds: new Set(),
  isDragging: false,
  isConnecting: false,
  connectionSource: null,
};

const initialQueryWorkbench: QueryWorkbenchState = {
  mode: 'semantic',
  sqlText: '',
  selectedDimensions: [],
  selectedMeasures: [],
  activeTab: 'results',
  queryHistory: [],
};

// ============================================================================
// STORE
// ============================================================================

export const useModelingStore = create<ModelingStore>()(
  persist(
    (set, get) => ({
      // =========================================================================
      // DATA SOURCES
      // =========================================================================
      sources: [],
      activeSourceId: null,
      setSources: (sources) => set({ sources }),
      setActiveSource: (activeSourceId) => set({ activeSourceId }),
      
      // =========================================================================
      // SCHEMA TREE
      // =========================================================================
      schemas: [],
      tables: {},
      columns: {},
      schemaTree: initialSchemaTree,
      
      setSchemas: (schemas) => set({ schemas }),
      
      setTables: (schemaName, tables) =>
        set((state) => ({
          tables: { ...state.tables, [schemaName]: tables },
        })),
      
      setColumns: (fullTableName, columns) =>
        set((state) => ({
          columns: { ...state.columns, [fullTableName]: columns },
        })),
      
      toggleSchemaExpanded: (schemaName) =>
        set((state) => {
          const newSet = new Set(state.schemaTree.expandedSchemas);
          if (newSet.has(schemaName)) {
            newSet.delete(schemaName);
          } else {
            newSet.add(schemaName);
          }
          return { schemaTree: { ...state.schemaTree, expandedSchemas: newSet } };
        }),
      
      toggleTableExpanded: (fullTableName) =>
        set((state) => {
          const newSet = new Set(state.schemaTree.expandedTables);
          if (newSet.has(fullTableName)) {
            newSet.delete(fullTableName);
          } else {
            newSet.add(fullTableName);
          }
          return { schemaTree: { ...state.schemaTree, expandedTables: newSet } };
        }),
      
      setSelectedTable: (fullTableName) =>
        set((state) => ({
          schemaTree: { ...state.schemaTree, selectedTable: fullTableName },
        })),
      
      setSchemaSearchQuery: (query) =>
        set((state) => ({
          schemaTree: { ...state.schemaTree, searchQuery: query },
        })),
      
      clearSchemaCache: () =>
        set({
          schemas: [],
          tables: {},
          columns: {},
          schemaTree: {
            ...initialSchemaTree,
            expandedSchemas: new Set(),
            expandedTables: new Set(),
          },
        }),
      
      // =========================================================================
      // ERD MODEL
      // =========================================================================
      erdModels: [],
      activeERDId: null,
      erdCanvas: initialERDCanvas,
      
      setERDModels: (erdModels) => set({ erdModels }),
      setActiveERD: (activeERDId) => set({ activeERDId }),
      
      getActiveERD: () => {
        const { erdModels, activeERDId } = get();
        return erdModels.find((m) => m.id === activeERDId) || null;
      },
      
      addLocalERDModel: (model) =>
        set((state) => ({
          erdModels: [...state.erdModels, model],
        })),
      
      updateERDNode: (nodeId, updates) =>
        set((state) => ({
          erdModels: state.erdModels.map((model) =>
            model.id === state.activeERDId
              ? {
                  ...model,
                  nodes: model.nodes.map((node) =>
                    node.id === nodeId ? { ...node, ...updates } : node
                  ),
                }
              : model
          ),
        })),
      
      addERDNode: (node) =>
        set((state) => ({
          erdModels: state.erdModels.map((model) =>
            model.id === state.activeERDId
              ? { ...model, nodes: [...model.nodes, node] }
              : model
          ),
        })),
      
      removeERDNode: (nodeId) =>
        set((state) => ({
          erdModels: state.erdModels.map((model) =>
            model.id === state.activeERDId
              ? {
                  ...model,
                  nodes: model.nodes.filter((n) => n.id !== nodeId),
                  edges: model.edges.filter(
                    (e) => e.sourceNodeId !== nodeId && e.targetNodeId !== nodeId
                  ),
                }
              : model
          ),
        })),
      
      addERDEdge: (edge) =>
        set((state) => ({
          erdModels: state.erdModels.map((model) =>
            model.id === state.activeERDId
              ? { ...model, edges: [...model.edges, edge] }
              : model
          ),
        })),
      
      removeERDEdge: (edgeId) =>
        set((state) => ({
          erdModels: state.erdModels.map((model) =>
            model.id === state.activeERDId
              ? { ...model, edges: model.edges.filter((e) => e.id !== edgeId) }
              : model
          ),
        })),
      
      setERDZoom: (zoom) =>
        set((state) => ({
          erdCanvas: { ...state.erdCanvas, zoom },
        })),
      
      setERDPan: (pan) =>
        set((state) => ({
          erdCanvas: { ...state.erdCanvas, pan },
        })),
      
      selectNodes: (nodeIds) =>
        set((state) => ({
          erdCanvas: { ...state.erdCanvas, selectedNodeIds: new Set(nodeIds) },
        })),
      
      selectEdges: (edgeIds) =>
        set((state) => ({
          erdCanvas: { ...state.erdCanvas, selectedEdgeIds: new Set(edgeIds) },
        })),
      
      clearSelection: () =>
        set((state) => ({
          erdCanvas: {
            ...state.erdCanvas,
            selectedNodeIds: new Set(),
            selectedEdgeIds: new Set(),
          },
        })),
      
      startConnection: (nodeId, column) =>
        set((state) => ({
          erdCanvas: {
            ...state.erdCanvas,
            isConnecting: true,
            connectionSource: { nodeId, column },
          },
        })),
      
      endConnection: () =>
        set((state) => ({
          erdCanvas: {
            ...state.erdCanvas,
            isConnecting: false,
            connectionSource: null,
          },
        })),
      
      // =========================================================================
      // SEMANTIC MODEL
      // =========================================================================
      semanticModels: [],
      activeSemanticId: null,
      selectedDimensionId: null,
      selectedMeasureId: null,
      
      setSemanticModels: (semanticModels) => set({ semanticModels }),
      setActiveSemantic: (activeSemanticId) => set({ activeSemanticId }),
      
      getActiveSemantic: () => {
        const { semanticModels, activeSemanticId } = get();
        return semanticModels.find((m) => m.id === activeSemanticId) || null;
      },
      
      addLocalSemanticModel: (model) =>
        set((state) => ({
          semanticModels: [...state.semanticModels, model],
        })),
      
      addDimension: (dimension) =>
        set((state) => {
          // If no active semantic model, create one first
          if (!state.activeSemanticId || !state.semanticModels.find(m => m.id === state.activeSemanticId)) {
            const newModel: SemanticModel = {
              id: `semantic-${Date.now()}`,
              name: 'Default Semantic Model',
              sourceId: state.activeSourceId || 'default',
              dimensions: [dimension],
              measures: [],
              calculatedFields: [],
              timeIntelligence: [],
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
              version: 1,
            };
            return {
              semanticModels: [...state.semanticModels, newModel],
              activeSemanticId: newModel.id,
            };
          }
          
          // Add to existing model
          return {
            semanticModels: state.semanticModels.map((model) =>
              model.id === state.activeSemanticId
                ? { ...model, dimensions: [...model.dimensions, dimension] }
                : model
            ),
          };
        }),
      
      removeDimension: (dimensionId) =>
        set((state) => ({
          semanticModels: state.semanticModels.map((model) =>
            model.id === state.activeSemanticId
              ? {
                  ...model,
                  dimensions: model.dimensions.filter((d) => d.id !== dimensionId),
                }
              : model
          ),
        })),
      
      updateDimension: (dimensionId, updates) =>
        set((state) => ({
          semanticModels: state.semanticModels.map((model) =>
            model.id === state.activeSemanticId
              ? {
                  ...model,
                  dimensions: model.dimensions.map((d) =>
                    d.id === dimensionId ? { ...d, ...updates } : d
                  ),
                }
              : model
          ),
        })),
      
      addMeasure: (measure) =>
        set((state) => {
          // If no active semantic model, create one first
          if (!state.activeSemanticId || !state.semanticModels.find(m => m.id === state.activeSemanticId)) {
            const newModel: SemanticModel = {
              id: `semantic-${Date.now()}`,
              name: 'Default Semantic Model',
              sourceId: state.activeSourceId || 'default',
              dimensions: [],
              measures: [measure],
              calculatedFields: [],
              timeIntelligence: [],
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
              version: 1,
            };
            return {
              semanticModels: [...state.semanticModels, newModel],
              activeSemanticId: newModel.id,
            };
          }
          
          // Add to existing model
          return {
            semanticModels: state.semanticModels.map((model) =>
              model.id === state.activeSemanticId
                ? { ...model, measures: [...model.measures, measure] }
                : model
            ),
          };
        }),
      
      removeMeasure: (measureId) =>
        set((state) => ({
          semanticModels: state.semanticModels.map((model) =>
            model.id === state.activeSemanticId
              ? {
                  ...model,
                  measures: model.measures.filter((m) => m.id !== measureId),
                }
              : model
          ),
        })),
      
      updateMeasure: (measureId, updates) =>
        set((state) => ({
          semanticModels: state.semanticModels.map((model) =>
            model.id === state.activeSemanticId
              ? {
                  ...model,
                  measures: model.measures.map((m) =>
                    m.id === measureId ? { ...m, ...updates } : m
                  ),
                }
              : model
          ),
        })),
      
      addCalculatedField: (calc) =>
        set((state) => ({
          semanticModels: state.semanticModels.map((model) =>
            model.id === state.activeSemanticId
              ? { ...model, calculatedFields: [...model.calculatedFields, calc] }
              : model
          ),
        })),
      
      removeCalculatedField: (calcId) =>
        set((state) => ({
          semanticModels: state.semanticModels.map((model) =>
            model.id === state.activeSemanticId
              ? {
                  ...model,
                  calculatedFields: model.calculatedFields.filter((c) => c.id !== calcId),
                }
              : model
          ),
        })),
      
      updateCalculatedField: (calcId, updates) =>
        set((state) => ({
          semanticModels: state.semanticModels.map((model) =>
            model.id === state.activeSemanticId
              ? {
                  ...model,
                  calculatedFields: model.calculatedFields.map((c) =>
                    c.id === calcId ? { ...c, ...updates } : c
                  ),
                }
              : model
          ),
        })),
      
      setSelectedDimension: (selectedDimensionId) => set({ selectedDimensionId }),
      setSelectedMeasure: (selectedMeasureId) => set({ selectedMeasureId }),
      
      // =========================================================================
      // QUERY WORKBENCH
      // =========================================================================
      queryWorkbench: initialQueryWorkbench,
      queryResult: null,
      isQueryRunning: false,
      queryError: null,
      
      setQueryMode: (mode) =>
        set((state) => ({
          queryWorkbench: { ...state.queryWorkbench, mode },
        })),
      
      setSqlText: (sqlText) =>
        set((state) => ({
          queryWorkbench: { ...state.queryWorkbench, sqlText },
        })),
      
      setSelectedQueryDimensions: (selectedDimensions) =>
        set((state) => ({
          queryWorkbench: { ...state.queryWorkbench, selectedDimensions },
        })),
      
      setSelectedQueryMeasures: (selectedMeasures) =>
        set((state) => ({
          queryWorkbench: { ...state.queryWorkbench, selectedMeasures },
        })),
      
      setQueryActiveTab: (activeTab) =>
        set((state) => ({
          queryWorkbench: { ...state.queryWorkbench, activeTab },
        })),
      
      setQueryResult: (queryResult) => set({ queryResult }),
      setQueryRunning: (isQueryRunning) => set({ isQueryRunning }),
      setQueryError: (queryError) => set({ queryError }),
      
      addToQueryHistory: (query, executionTime) =>
        set((state) => ({
          queryWorkbench: {
            ...state.queryWorkbench,
            queryHistory: [
              { timestamp: Date.now(), query, executionTime },
              ...state.queryWorkbench.queryHistory.slice(0, 49), // Keep last 50
            ],
          },
        })),
      
      // =========================================================================
      // UI STATE
      // =========================================================================
      schemaPanelWidth: 280,
      propertiesPanelWidth: 320,
      bottomPanelHeight: 300,
      setSchemaPanelWidth: (schemaPanelWidth) => set({ schemaPanelWidth }),
      setPropertiesPanelWidth: (propertiesPanelWidth) => set({ propertiesPanelWidth }),
      setBottomPanelHeight: (bottomPanelHeight) => set({ bottomPanelHeight }),
      
      // =========================================================================
      // RESET
      // =========================================================================
      reset: () =>
        set({
          sources: [],
          activeSourceId: null,
          schemas: [],
          tables: {},
          columns: {},
          schemaTree: initialSchemaTree,
          erdModels: [],
          activeERDId: null,
          erdCanvas: initialERDCanvas,
          semanticModels: [],
          activeSemanticId: null,
          selectedDimensionId: null,
          selectedMeasureId: null,
          queryWorkbench: initialQueryWorkbench,
          queryResult: null,
          isQueryRunning: false,
          queryError: null,
        }),
    }),
    {
      name: 'setupranali-modeling',
      partialize: (state) => ({
        // Only persist certain state
        activeSourceId: state.activeSourceId,
        activeERDId: state.activeERDId,
        activeSemanticId: state.activeSemanticId,
        schemaPanelWidth: state.schemaPanelWidth,
        propertiesPanelWidth: state.propertiesPanelWidth,
        bottomPanelHeight: state.bottomPanelHeight,
        queryWorkbench: {
          mode: state.queryWorkbench.mode,
          sqlText: state.queryWorkbench.sqlText,
          activeTab: state.queryWorkbench.activeTab,
          queryHistory: state.queryWorkbench.queryHistory,
        },
      }),
    }
  )
);

