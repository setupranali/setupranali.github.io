/**
 * ERD Canvas (Entity Relationship Diagram Builder)
 * 
 * Canvas-based ERD editor using React Flow.
 * Features:
 * - Drag tables from schema panel
 * - Create relationships by connecting columns
 * - Pan and zoom
 * - Relationship properties (cardinality, join type)
 */

import React, { useCallback, useMemo, useState, useRef, useEffect } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Panel,
  useNodesState,
  useEdgesState,
  Connection,
  Edge,
  Node,
  NodeTypes,
  MarkerType,
  Handle,
  Position,
  ConnectionLineType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  Table2,
  Key,
  Link,
  ChevronDown,
  ChevronRight,
  X,
  Trash2,
  Maximize2,
  RotateCcw,
  Loader2,
} from 'lucide-react';
import { useModelingStore } from '../../store/modeling';
import { modelingApi } from '../../lib/modeling-api';
import type {
  TableNode as TableNodeType,
  RelationshipEdge,
  Cardinality,
  JoinType,
} from '../../types/modeling';
import { cn } from '../../lib/utils';

// ============================================================================
// CUSTOM TABLE NODE
// ============================================================================

interface TableNodeData extends Record<string, unknown> {
  schemaName: string;
  tableName: string;
  columns: Array<{
    name: string;
    type: string;
    isPrimaryKey: boolean;
    isForeignKey: boolean;
  }>;
  isCollapsed: boolean;
  isLoading?: boolean;
  color?: string;
  nodeId: string;
}

interface TableNodeComponentProps {
  id: string;
  data: TableNodeData;
  selected?: boolean;
}

function TableNodeComponent({ id, data, selected }: TableNodeComponentProps) {
  const [hoveredColumn, setHoveredColumn] = useState<string | null>(null);
  const { updateERDNode, removeERDNode } = useModelingStore();

  const handleToggleCollapse = useCallback(() => {
    updateERDNode(id, { isCollapsed: !data.isCollapsed });
  }, [id, data.isCollapsed, updateERDNode]);

  const handleRemove = useCallback(() => {
    removeERDNode(id);
  }, [id, removeERDNode]);

  return (
    <div
      className={cn(
        'bg-slate-800 rounded-lg border-2 shadow-xl min-w-[220px] max-w-[300px] transition-all',
        selected
          ? 'border-indigo-500 shadow-indigo-500/20'
          : 'border-slate-600 hover:border-slate-500'
      )}
      style={data.color ? { borderColor: data.color } : undefined}
    >
      {/* Table Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-slate-700/50 rounded-t-lg border-b border-slate-600">
        <div className="flex items-center gap-2 min-w-0">
          <Table2 className="w-4 h-4 text-blue-400 flex-shrink-0" />
          <div className="min-w-0">
            <div className="text-sm font-medium text-white truncate">{data.tableName}</div>
            <div className="text-xs text-slate-500 truncate">{data.schemaName}</div>
          </div>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleToggleCollapse();
            }}
            className="p-1 hover:bg-slate-600 rounded transition-colors"
          >
            {data.isCollapsed ? (
              <ChevronRight className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            )}
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleRemove();
            }}
            className="p-1 hover:bg-red-500/20 rounded transition-colors"
          >
            <X className="w-4 h-4 text-slate-400 hover:text-red-400" />
          </button>
        </div>
      </div>

      {/* Columns */}
      {!data.isCollapsed && (
        <div className="py-1 max-h-[300px] overflow-y-auto">
          {data.isLoading ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="w-5 h-5 text-slate-400 animate-spin" />
              <span className="ml-2 text-sm text-slate-400">Loading columns...</span>
            </div>
          ) : data.columns.length === 0 ? (
            <div className="text-center py-4 text-sm text-slate-500">
              No columns found
            </div>
          ) : (
            data.columns.map((column) => (
              <div
                key={column.name}
                className={cn(
                  'relative flex items-center gap-2 px-4 py-2 text-sm transition-colors group',
                  hoveredColumn === column.name && 'bg-slate-700/50'
                )}
                onMouseEnter={() => setHoveredColumn(column.name)}
                onMouseLeave={() => setHoveredColumn(null)}
              >
                {/* Left Handle (for incoming connections) */}
                <Handle
                  type="target"
                  position={Position.Left}
                  id={`${column.name}-target`}
                  isConnectable={true}
                  className="!w-4 !h-4 !bg-indigo-500/50 !border-2 !border-indigo-400 hover:!bg-indigo-500 hover:!border-indigo-300 !cursor-crosshair transition-all"
                  style={{ 
                    left: -8,
                    top: '50%',
                    transform: 'translateY(-50%)',
                  }}
                />

                {/* Column Icon */}
                {column.isPrimaryKey ? (
                  <Key className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
                ) : column.isForeignKey ? (
                  <Link className="w-3.5 h-3.5 text-green-400 flex-shrink-0" />
                ) : (
                  <div className="w-3 h-3 rounded-full bg-slate-600 flex-shrink-0" />
                )}

                {/* Column Name */}
                <span className="text-slate-300 flex-1 truncate" title={column.name}>
                  {column.name}
                </span>

                {/* Column Type */}
                <span className="text-xs text-slate-500 font-mono flex-shrink-0" title={column.type}>
                  {column.type.length > 10 ? column.type.substring(0, 10) + '...' : column.type}
                </span>

                {/* Right Handle (for outgoing connections) */}
                <Handle
                  type="source"
                  position={Position.Right}
                  id={`${column.name}-source`}
                  isConnectable={true}
                  className="!w-4 !h-4 !bg-green-500/50 !border-2 !border-green-400 hover:!bg-green-500 hover:!border-green-300 !cursor-crosshair transition-all"
                  style={{ 
                    right: -8,
                    top: '50%',
                    transform: 'translateY(-50%)',
                  }}
                />
              </div>
            ))
          )}
        </div>
      )}

      {/* Column Count Footer */}
      {data.isCollapsed && data.columns.length > 0 && (
        <div className="px-3 py-1.5 text-xs text-slate-500 border-t border-slate-700">
          {data.columns.length} columns
        </div>
      )}
    </div>
  );
}

// ============================================================================
// ERD CANVAS COMPONENT
// ============================================================================

interface ERDCanvasProps {
  erdModelId: string;
  sourceId: string;
  onNodeSelect?: (nodeId: string | null) => void;
  onEdgeSelect?: (edgeId: string | null) => void;
}

export function ERDCanvas({
  sourceId,
  onNodeSelect,
  onEdgeSelect,
}: ERDCanvasProps) {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [selectedEdge, setSelectedEdge] = useState<string | null>(null);
  const [showRelationshipDialog, setShowRelationshipDialog] = useState(false);
  const [pendingConnection, setPendingConnection] = useState<Connection | null>(null);
  const [loadingNodes, setLoadingNodes] = useState<Set<string>>(new Set());

  const {
    getActiveERD,
    updateERDNode,
    addERDNode,
    addERDEdge,
    removeERDEdge,
  } = useModelingStore();

  const erdModel = getActiveERD();

  const [nodes, setNodes, onNodesChange] = useNodesState<Node<TableNodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // Sync nodes with ERD model
  useEffect(() => {
    if (!erdModel) {
      setNodes([]);
      return;
    }

    const newNodes: Node<TableNodeData>[] = erdModel.nodes.map((node) => {
      const columns = node.columns.map((c) => ({
        name: c,
        type: 'unknown',
        isPrimaryKey: false,
        isForeignKey: false,
      }));

      return {
        id: node.id,
        type: 'tableNode',
        position: { x: node.position.x, y: node.position.y },
        data: {
          schemaName: node.schemaName,
          tableName: node.tableName,
          columns,
          isCollapsed: node.isCollapsed,
          isLoading: loadingNodes.has(node.id),
          color: node.color,
          nodeId: node.id,
        },
      };
    });

    setNodes(newNodes);
  }, [erdModel, loadingNodes, setNodes]);

  // Sync edges with ERD model
  useEffect(() => {
    if (!erdModel) {
      setEdges([]);
      return;
    }

    const newEdges: Edge[] = erdModel.edges.map((edge) => ({
      id: edge.id,
      source: edge.sourceNodeId,
      target: edge.targetNodeId,
      sourceHandle: `${edge.sourceColumn}-source`,
      targetHandle: `${edge.targetColumn}-target`,
      type: 'smoothstep',
      animated: edge.isActive,
      style: {
        stroke: edge.isActive ? '#6366f1' : '#475569',
        strokeWidth: 2,
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: edge.isActive ? '#6366f1' : '#475569',
      },
      label: `${edge.cardinality} (${edge.joinType})`,
      labelStyle: {
        fill: '#94a3b8',
        fontSize: 10,
        fontWeight: 500,
      },
      labelBgStyle: {
        fill: '#1e293b',
        fillOpacity: 0.9,
      },
      labelBgPadding: [4, 4] as [number, number],
    }));

    setEdges(newEdges);
  }, [erdModel, setEdges]);

  // Handle node position changes
  const handleNodeDragStop = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      updateERDNode(node.id, {
        position: { x: node.position.x, y: node.position.y },
      });
    },
    [updateERDNode]
  );

  // Handle new connection
  const handleConnect = useCallback(
    (connection: Connection) => {
      if (!connection.source || !connection.target) return;
      
      // Prevent self-connections
      if (connection.source === connection.target) return;

      setPendingConnection(connection);
      setShowRelationshipDialog(true);
    },
    []
  );

  // Fetch columns for a table
  const fetchColumns = useCallback(async (nodeId: string, schemaName: string, tableName: string) => {
    setLoadingNodes(prev => new Set(prev).add(nodeId));
    
    try {
      const columns = await modelingApi.getColumns(sourceId, schemaName, tableName);
      
      // Update the ERD node with column names
      const columnNames = columns.map(c => c.name);
      updateERDNode(nodeId, { columns: columnNames });

      // Update the React Flow node data with full column info
      setNodes(nds => nds.map(n => {
        if (n.id === nodeId) {
          return {
            ...n,
            data: {
              ...n.data,
              columns: columns.map(c => ({
                name: c.name,
                type: c.dataType || 'unknown',
                isPrimaryKey: c.isPrimaryKey || false,
                isForeignKey: c.isForeignKey || false,
              })),
              isLoading: false,
            },
          };
        }
        return n;
      }));
    } catch (error) {
      console.error('Failed to fetch columns:', error);
      setNodes(nds => nds.map(n => {
        if (n.id === nodeId) {
          return {
            ...n,
            data: {
              ...n.data,
              isLoading: false,
            },
          };
        }
        return n;
      }));
    } finally {
      setLoadingNodes(prev => {
        const next = new Set(prev);
        next.delete(nodeId);
        return next;
      });
    }
  }, [sourceId, updateERDNode, setNodes]);

  // Handle drop from schema panel
  const handleDrop = useCallback(
    async (event: React.DragEvent) => {
      event.preventDefault();

      const data = event.dataTransfer.getData('application/json');
      if (!data) return;

      const { schemaName, tableName } = JSON.parse(data);

      if (!reactFlowWrapper.current) return;

      const bounds = reactFlowWrapper.current.getBoundingClientRect();
      const position = {
        x: event.clientX - bounds.left - 110,
        y: event.clientY - bounds.top - 50,
      };

      const nodeId = `${schemaName}-${tableName}-${Date.now()}`;

      // Add node to ERD model
      const newNode: TableNodeType = {
        id: nodeId,
        schemaName,
        tableName,
        fullName: `${schemaName}.${tableName}`,
        position,
        columns: [],
        isCollapsed: false,
        isVisible: true,
      };

      addERDNode(newNode);

      // Fetch columns for the newly added table
      await fetchColumns(nodeId, schemaName, tableName);
    },
    [addERDNode, fetchColumns]
  );

  const handleDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'copy';
  }, []);

  // Node types
  const nodeTypes: NodeTypes = useMemo(
    () => ({
      tableNode: TableNodeComponent as unknown as NodeTypes['tableNode'],
    }),
    []
  );

  // Create relationship with selected options
  const createRelationship = useCallback(
    (cardinality: Cardinality, joinType: JoinType) => {
      if (!pendingConnection?.source || !pendingConnection?.target) return;

      const sourceColumn = pendingConnection.sourceHandle?.replace('-source', '') || '';
      const targetColumn = pendingConnection.targetHandle?.replace('-target', '') || '';

      const newEdge: RelationshipEdge = {
        id: `edge-${Date.now()}`,
        sourceNodeId: pendingConnection.source,
        sourceColumn,
        targetNodeId: pendingConnection.target,
        targetColumn,
        cardinality,
        joinType,
        isActive: true,
      };

      addERDEdge(newEdge);
      setShowRelationshipDialog(false);
      setPendingConnection(null);
    },
    [pendingConnection, addERDEdge]
  );

  // Handle edge click to show properties
  const handleEdgeClick = useCallback((_event: React.MouseEvent, edge: Edge) => {
    setSelectedEdge(edge.id);
    onEdgeSelect?.(edge.id);
  }, [onEdgeSelect]);

  // Handle node click
  const handleNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    onNodeSelect?.(node.id);
  }, [onNodeSelect]);

  return (
    <div ref={reactFlowWrapper} className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={handleConnect}
        onNodeDragStop={handleNodeDragStop}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onEdgeClick={handleEdgeClick}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        fitView
        snapToGrid
        snapGrid={[15, 15]}
        connectOnClick={true}
        connectionRadius={20}
        defaultEdgeOptions={{
          type: 'smoothstep',
          animated: true,
          style: { stroke: '#6366f1', strokeWidth: 2 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#6366f1',
          },
        }}
        connectionLineStyle={{ stroke: '#6366f1', strokeWidth: 2 }}
        connectionLineType={ConnectionLineType.SmoothStep}
        className="bg-slate-950"
      >
        <Background color="#334155" gap={20} size={1} />
        <Controls
          className="!bg-slate-800 !border-slate-700 !rounded-lg !shadow-xl"
          showZoom
          showFitView
          showInteractive={false}
        />
        <MiniMap
          className="!bg-slate-800 !border-slate-700 !rounded-lg"
          nodeColor="#475569"
          maskColor="rgba(0, 0, 0, 0.5)"
        />

        {/* Toolbar Panel */}
        <Panel position="top-right" className="flex gap-2">
          <button
            className="p-2 bg-slate-800 hover:bg-slate-700 border border-slate-600 rounded-lg transition-colors"
            title="Reset View"
          >
            <RotateCcw className="w-4 h-4 text-slate-400" />
          </button>
          <button
            className="p-2 bg-slate-800 hover:bg-slate-700 border border-slate-600 rounded-lg transition-colors"
            title="Fit to Screen"
          >
            <Maximize2 className="w-4 h-4 text-slate-400" />
          </button>
        </Panel>

        {/* Drop Zone Hint - only show when no nodes */}
        {nodes.length === 0 && (
          <Panel position="bottom-center" className="pointer-events-none">
            <div className="px-4 py-2 bg-slate-800/80 backdrop-blur-sm border border-slate-700 rounded-lg text-sm text-slate-400">
              Drag tables from the schema panel to add them to the canvas
            </div>
          </Panel>
        )}

        {/* Instructions when nodes exist */}
        {nodes.length > 0 && (
          <Panel position="bottom-center" className="pointer-events-none">
            <div className="px-3 py-1.5 bg-slate-800/60 backdrop-blur-sm border border-slate-700 rounded-lg text-xs text-slate-500">
              Drag from column handles to create relationships
            </div>
          </Panel>
        )}
      </ReactFlow>

      {/* Relationship Dialog */}
      {showRelationshipDialog && pendingConnection && (
        <RelationshipDialog
          sourceColumn={pendingConnection.sourceHandle?.replace('-source', '') || ''}
          targetColumn={pendingConnection.targetHandle?.replace('-target', '') || ''}
          onClose={() => {
            setShowRelationshipDialog(false);
            setPendingConnection(null);
          }}
          onCreate={createRelationship}
        />
      )}

      {/* Selected Edge Properties */}
      {selectedEdge && erdModel && (
        <EdgePropertiesPanel
          edge={erdModel.edges.find(e => e.id === selectedEdge)}
          onClose={() => setSelectedEdge(null)}
          onUpdate={(updates) => {
            // Update edge in ERD model
            const edge = erdModel.edges.find(e => e.id === selectedEdge);
            if (edge) {
              removeERDEdge(selectedEdge);
              addERDEdge({ ...edge, ...updates });
            }
          }}
          onDelete={() => {
            removeERDEdge(selectedEdge);
            setSelectedEdge(null);
          }}
        />
      )}
    </div>
  );
}

// ============================================================================
// RELATIONSHIP DIALOG
// ============================================================================

interface RelationshipDialogProps {
  sourceColumn: string;
  targetColumn: string;
  onClose: () => void;
  onCreate: (cardinality: Cardinality, joinType: JoinType) => void;
}

function RelationshipDialog({ sourceColumn, targetColumn, onClose, onCreate }: RelationshipDialogProps) {
  const [cardinality, setCardinality] = useState<Cardinality>('N:1');
  const [joinType, setJoinType] = useState<JoinType>('left');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-slate-800 border border-slate-600 rounded-xl shadow-2xl w-96 p-6">
        <h3 className="text-lg font-semibold text-white mb-2">
          Create Relationship
        </h3>
        
        <p className="text-sm text-slate-400 mb-4">
          Connecting <span className="text-indigo-400 font-mono">{sourceColumn}</span> → <span className="text-indigo-400 font-mono">{targetColumn}</span>
        </p>

        {/* Cardinality */}
        <div className="mb-4">
          <label className="text-sm font-medium text-slate-300 mb-2 block">
            Cardinality
          </label>
          <div className="grid grid-cols-4 gap-2">
            {(['1:1', '1:N', 'N:1', 'N:N'] as Cardinality[]).map((c) => (
              <button
                key={c}
                onClick={() => setCardinality(c)}
                className={cn(
                  'px-3 py-2 rounded-lg text-sm font-medium transition-all',
                  cardinality === c
                    ? 'bg-indigo-500 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                )}
              >
                {c}
              </button>
            ))}
          </div>
        </div>

        {/* Join Type */}
        <div className="mb-6">
          <label className="text-sm font-medium text-slate-300 mb-2 block">
            Join Type
          </label>
          <div className="grid grid-cols-4 gap-2">
            {(['inner', 'left', 'right', 'full'] as JoinType[]).map((j) => (
              <button
                key={j}
                onClick={() => setJoinType(j)}
                className={cn(
                  'px-3 py-2 rounded-lg text-sm font-medium transition-all capitalize',
                  joinType === j
                    ? 'bg-indigo-500 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                )}
              >
                {j}
              </button>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-slate-300 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onCreate(cardinality, joinType)}
            className="px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-colors"
          >
            Create Relationship
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// EDGE PROPERTIES PANEL
// ============================================================================

interface EdgePropertiesPanelProps {
  edge?: RelationshipEdge;
  onClose: () => void;
  onUpdate: (updates: Partial<RelationshipEdge>) => void;
  onDelete: () => void;
}

function EdgePropertiesPanel({ edge, onClose, onUpdate, onDelete }: EdgePropertiesPanelProps) {
  if (!edge) return null;

  return (
    <div className="absolute top-4 left-4 z-40 bg-slate-800 border border-slate-600 rounded-xl shadow-2xl w-72 p-4">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-sm font-semibold text-white">Relationship Properties</h4>
        <button onClick={onClose} className="p-1 hover:bg-slate-700 rounded transition-colors">
          <X className="w-4 h-4 text-slate-400" />
        </button>
      </div>

      <div className="space-y-3 text-sm">
        <div>
          <span className="text-slate-400">Source:</span>
          <span className="ml-2 text-slate-200 font-mono">{edge.sourceColumn}</span>
        </div>
        <div>
          <span className="text-slate-400">Target:</span>
          <span className="ml-2 text-slate-200 font-mono">{edge.targetColumn}</span>
        </div>
        <div>
          <span className="text-slate-400">Cardinality:</span>
          <span className="ml-2 text-slate-200">{edge.cardinality}</span>
        </div>
        <div>
          <span className="text-slate-400">Join Type:</span>
          <span className="ml-2 text-slate-200 capitalize">{edge.joinType}</span>
        </div>
        <div className="flex items-center">
          <span className="text-slate-400">Active:</span>
          <button
            onClick={() => onUpdate({ isActive: !edge.isActive })}
            className={cn(
              'ml-2 px-2 py-0.5 rounded text-xs transition-colors',
              edge.isActive
                ? 'bg-emerald-500/20 text-emerald-400'
                : 'bg-slate-700 text-slate-400'
            )}
          >
            {edge.isActive ? 'Yes' : 'No'}
          </button>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-slate-700">
        <button
          onClick={onDelete}
          className="flex items-center gap-2 w-full px-3 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors text-sm"
        >
          <Trash2 className="w-4 h-4" />
          Delete Relationship
        </button>
      </div>
    </div>
  );
}
