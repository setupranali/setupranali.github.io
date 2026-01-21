/**
 * Schema Discovery Panel
 * 
 * Tree view for exploring database schemas, tables, and columns.
 * Supports:
 * - Collapsible tree structure
 * - Search/filtering
 * - Lazy loading of columns
 * - Drag to ERD canvas
 */

import React, { useCallback, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Database,
  Table2,
  Columns,
  ChevronRight,
  ChevronDown,
  Search,
  Key,
  Link,
  Hash,
  Type,
  Calendar,
  ToggleLeft,
  Loader2,
  GripVertical,
  RefreshCw,
} from 'lucide-react';
import { modelingApi } from '../../lib/modeling-api';
import { useModelingStore } from '../../store/modeling';
import type { ColumnInfo, NormalizedColumnType } from '../../types/modeling';
import { cn } from '../../lib/utils';

// Column type icons
const TYPE_ICONS: Record<NormalizedColumnType, typeof Hash> = {
  string: Type,
  integer: Hash,
  bigint: Hash,
  float: Hash,
  double: Hash,
  decimal: Hash,
  boolean: ToggleLeft,
  date: Calendar,
  datetime: Calendar,
  timestamp: Calendar,
  time: Calendar,
  binary: Database,
  json: Columns,
  array: Columns,
  unknown: Type,
};

interface SchemaPanelProps {
  sourceId: string;
  onTableDragStart?: (schemaName: string, tableName: string) => void;
  onTableSelect?: (schemaName: string, tableName: string) => void;
  onColumnSelect?: (schemaName: string, tableName: string, column: ColumnInfo) => void;
}

export function SchemaPanel({
  sourceId,
  onTableDragStart,
  onTableSelect,
  onColumnSelect,
}: SchemaPanelProps) {
  const queryClient = useQueryClient();
  const {
    schemas,
    tables,
    columns,
    schemaTree,
    setSchemas,
    setTables,
    setColumns,
    clearSchemaCache,
    toggleSchemaExpanded,
    toggleTableExpanded,
    setSelectedTable,
    setSchemaSearchQuery,
  } = useModelingStore();

  // Fetch schemas
  const schemasQuery = useQuery({
    queryKey: ['schemas', sourceId],
    queryFn: async () => {
      try {
        console.log('Fetching schemas for source:', sourceId);
        const data = await modelingApi.getSchemas(sourceId);
        console.log('Schemas fetched:', data);
        setSchemas(data);
        return data;
      } catch (error: any) {
        // If source not found (404), don't retry and show user-friendly message
        if (error?.response?.status === 404 || error?.message?.includes('not found')) {
          console.warn(`Source ${sourceId} not found - it may have been deleted`);
          throw new Error(`Source not found. It may have been deleted. Please select a different source.`);
        }
        console.error('Failed to fetch schemas:', error);
        throw error;
      }
    },
    enabled: !!sourceId,
    retry: (failureCount, error: any) => {
      // Don't retry on 404 errors (source not found)
      if (error?.response?.status === 404 || error?.message?.includes('not found')) {
        return false;
      }
      // Retry once for other errors
      return failureCount < 1;
    },
  });

  // Handle full refresh - clears all cached data and refetches
  const handleRefresh = useCallback(() => {
    // Clear local state cache
    clearSchemaCache();
    
    // Invalidate all React Query caches for this source
    queryClient.invalidateQueries({ queryKey: ['schemas', sourceId] });
    queryClient.invalidateQueries({ queryKey: ['tables', sourceId] });
    queryClient.invalidateQueries({ queryKey: ['columns', sourceId] });
    
    // Trigger refetch
    schemasQuery.refetch();
  }, [queryClient, sourceId, clearSchemaCache, schemasQuery]);

  // Filter schemas and tables based on search
  const filteredSchemas = useMemo(() => {
    if (!schemaTree.searchQuery) return schemas;
    
    const query = schemaTree.searchQuery.toLowerCase();
    return schemas.filter((schema) => {
      if (schema.name.toLowerCase().includes(query)) return true;
      const schemaTables = tables[schema.name] || [];
      return schemaTables.some((t) => t.tableName.toLowerCase().includes(query));
    });
  }, [schemas, tables, schemaTree.searchQuery]);

  return (
    <div className="h-full flex flex-col bg-slate-900 border-r border-slate-700">
      {/* Header */}
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-indigo-400" />
            <h3 className="font-semibold text-white">Schema Browser</h3>
          </div>
          <button
            onClick={handleRefresh}
            disabled={schemasQuery.isFetching}
            className="p-1.5 hover:bg-slate-800 rounded transition-colors"
            title="Refresh schemas and tables"
          >
            <RefreshCw
              className={cn(
                'w-4 h-4 text-slate-400',
                schemasQuery.isFetching && 'animate-spin'
              )}
            />
          </button>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search tables..."
            value={schemaTree.searchQuery}
            onChange={(e) => setSchemaSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-600 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
      </div>

      {/* Tree View */}
      <div className="flex-1 overflow-y-auto p-2">
        {schemasQuery.isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
          </div>
        ) : schemasQuery.isError ? (
          <div className="text-center py-8 px-4">
            <div className="text-red-400 mb-2">Failed to load schemas</div>
            <div className="text-xs text-slate-500">
              {schemasQuery.error instanceof Error 
                ? schemasQuery.error.message 
                : 'Unknown error'}
            </div>
            <button
              onClick={() => schemasQuery.refetch()}
              className="mt-4 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded text-sm"
            >
              Retry
            </button>
          </div>
        ) : filteredSchemas.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            {schemaTree.searchQuery
              ? 'No tables match your search'
              : sourceId 
                ? 'No schemas found. Make sure the source is connected and accessible.'
                : 'No source selected'}
          </div>
        ) : (
          <div className="space-y-1">
            {filteredSchemas.map((schema, index) => (
              <SchemaNode
                key={`${schema.name}-${index}`}
                sourceId={sourceId}
                schemaName={schema.name}
                tables={tables[schema.name]}
                columns={columns}
                isExpanded={schemaTree.expandedSchemas.has(schema.name)}
                expandedTables={schemaTree.expandedTables}
                selectedTable={schemaTree.selectedTable}
                searchQuery={schemaTree.searchQuery}
                onToggle={() => toggleSchemaExpanded(schema.name)}
                onTableToggle={toggleTableExpanded}
                onTableSelect={(tableName) => {
                  setSelectedTable(`${schema.name}.${tableName}`);
                  onTableSelect?.(schema.name, tableName);
                }}
                onTableDragStart={onTableDragStart}
                onColumnSelect={onColumnSelect}
                setTables={setTables}
                setColumns={setColumns}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Schema Node Component
interface SchemaNodeProps {
  sourceId: string;
  schemaName: string;
  tables?: { tableName: string; tableType: string }[];
  columns: Record<string, ColumnInfo[]>;
  isExpanded: boolean;
  expandedTables: Set<string>;
  selectedTable: string | null;
  searchQuery: string;
  onToggle: () => void;
  onTableToggle: (fullName: string) => void;
  onTableSelect: (tableName: string) => void;
  onTableDragStart?: (schemaName: string, tableName: string) => void;
  onColumnSelect?: (schemaName: string, tableName: string, column: ColumnInfo) => void;
  setTables: (schemaName: string, tables: any[]) => void;
  setColumns: (fullName: string, columns: ColumnInfo[]) => void;
}

function SchemaNode({
  sourceId,
  schemaName,
  tables,
  columns,
  isExpanded,
  expandedTables,
  selectedTable,
  searchQuery,
  onToggle,
  onTableToggle,
  onTableSelect,
  onTableDragStart,
  onColumnSelect,
  setTables,
  setColumns,
}: SchemaNodeProps) {
  // Fetch tables when schema is expanded
  const tablesQuery = useQuery({
    queryKey: ['tables', sourceId, schemaName],
    queryFn: async () => {
      const data = await modelingApi.getTables(sourceId, schemaName);
      setTables(schemaName, data);
      return data;
    },
    enabled: isExpanded,
    staleTime: 30000, // Consider data fresh for 30 seconds
  });

  const filteredTables = useMemo(() => {
    if (!tables) return [];
    if (!searchQuery) return tables;
    return tables.filter((t) =>
      t.tableName.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [tables, searchQuery]);

  return (
    <div>
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-2 py-1.5 hover:bg-slate-800 rounded-lg transition-colors group"
      >
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-slate-400" />
        ) : (
          <ChevronRight className="w-4 h-4 text-slate-400" />
        )}
        <Database className="w-4 h-4 text-amber-400" />
        <span className="text-sm text-slate-300 group-hover:text-white flex-1 text-left">
          {schemaName}
        </span>
        {tables && (
          <span className="text-xs text-slate-500">{tables.length}</span>
        )}
      </button>

      {isExpanded && (
        <div className="ml-4 pl-2 border-l border-slate-700">
          {tablesQuery.isLoading ? (
            <div className="flex items-center gap-2 px-2 py-1.5 text-slate-500">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm">Loading...</span>
            </div>
          ) : (
            filteredTables.map((table) => (
              <TableNode
                key={table.tableName}
                sourceId={sourceId}
                schemaName={schemaName}
                tableName={table.tableName}
                tableType={table.tableType}
                columns={columns[`${schemaName}.${table.tableName}`]}
                isExpanded={expandedTables.has(`${schemaName}.${table.tableName}`)}
                isSelected={selectedTable === `${schemaName}.${table.tableName}`}
                onToggle={() => onTableToggle(`${schemaName}.${table.tableName}`)}
                onSelect={() => onTableSelect(table.tableName)}
                onDragStart={() => onTableDragStart?.(schemaName, table.tableName)}
                onColumnSelect={(col) => onColumnSelect?.(schemaName, table.tableName, col)}
                setColumns={setColumns}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}

// Table Node Component
interface TableNodeProps {
  sourceId: string;
  schemaName: string;
  tableName: string;
  tableType: string;
  columns?: ColumnInfo[];
  isExpanded: boolean;
  isSelected: boolean;
  onToggle: () => void;
  onSelect: () => void;
  onDragStart: () => void;
  onColumnSelect?: (column: ColumnInfo) => void;
  setColumns: (fullName: string, columns: ColumnInfo[]) => void;
}

function TableNode({
  sourceId,
  schemaName,
  tableName,
  tableType,
  columns,
  isExpanded,
  isSelected,
  onToggle,
  onSelect,
  onDragStart,
  onColumnSelect,
  setColumns,
}: TableNodeProps) {
  const fullName = `${schemaName}.${tableName}`;

  // Fetch columns when table is expanded
  const columnsQuery = useQuery({
    queryKey: ['columns', sourceId, schemaName, tableName],
    queryFn: async () => {
      const data = await modelingApi.getColumns(sourceId, schemaName, tableName);
      setColumns(fullName, data);
      return data;
    },
    enabled: isExpanded,
    staleTime: 30000, // Consider data fresh for 30 seconds
  });

  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData(
      'application/json',
      JSON.stringify({ schemaName, tableName })
    );
    e.dataTransfer.effectAllowed = 'copy';
    onDragStart();
  };

  return (
    <div>
      <div
        className={cn(
          'flex items-center gap-1 px-2 py-1.5 rounded-lg transition-colors cursor-pointer group',
          isSelected ? 'bg-indigo-500/20' : 'hover:bg-slate-800'
        )}
        draggable
        onDragStart={handleDragStart}
        onClick={onSelect}
      >
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggle();
          }}
          className="p-0.5"
        >
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-slate-400" />
          )}
        </button>
        
        <GripVertical className="w-3 h-3 text-slate-600 opacity-0 group-hover:opacity-100 cursor-grab" />
        
        <Table2
          className={cn(
            'w-4 h-4',
            tableType === 'VIEW' ? 'text-purple-400' : 'text-blue-400'
          )}
        />
        
        <span
          className={cn(
            'text-sm flex-1 text-left truncate min-w-0',
            isSelected ? 'text-white' : 'text-slate-300 group-hover:text-white'
          )}
          title={tableName}
        >
          {tableName}
        </span>
        
        {tableType === 'VIEW' && (
          <span className="text-xs text-purple-400 px-1.5 py-0.5 bg-purple-400/10 rounded">
            View
          </span>
        )}
      </div>

      {isExpanded && (
        <div className="ml-6 pl-2 border-l border-slate-700/50">
          {columnsQuery.isLoading ? (
            <div className="flex items-center gap-2 px-2 py-1 text-slate-500">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span className="text-xs">Loading columns...</span>
            </div>
          ) : (
            columns?.map((column) => (
              <ColumnNode
                key={column.name}
                column={column}
                schemaName={schemaName}
                tableName={tableName}
                onClick={() => onColumnSelect?.(column)}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}

// Column Node Component
interface ColumnNodeProps {
  column: ColumnInfo;
  schemaName: string;
  tableName: string;
  onClick?: () => void;
}

function ColumnNode({ column, schemaName, tableName, onClick }: ColumnNodeProps) {
  const TypeIcon = TYPE_ICONS[column.normalizedType] || Type;

  // Handle drag start for column - can be dropped to create dimension/measure
  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData('application/json', JSON.stringify({
      type: 'column',
      schemaName,
      tableName,
      columnName: column.name,
      dataType: column.dataType,
      normalizedType: column.normalizedType,
      isPrimaryKey: column.isPrimaryKey,
      isForeignKey: column.isForeignKey,
    }));
    e.dataTransfer.effectAllowed = 'copy';
  };

  return (
    <div
      draggable
      onDragStart={handleDragStart}
      onClick={onClick}
      className="w-full flex items-center gap-2 px-2 py-1 hover:bg-slate-800/50 rounded transition-colors group cursor-grab active:cursor-grabbing"
      title={`Drag "${column.name}" to Dimensions or Measures panel`}
    >
      {column.isPrimaryKey ? (
        <Key className="w-3 h-3 text-amber-400" />
      ) : column.isForeignKey ? (
        <Link className="w-3 h-3 text-green-400" />
      ) : (
        <TypeIcon className="w-3 h-3 text-slate-500" />
      )}
      
      <span className="text-xs text-slate-400 group-hover:text-slate-300 flex-1 text-left truncate">
        {column.name}
      </span>
      
      <span className="text-xs text-slate-600 font-mono">
        {column.dataType}
      </span>
      
      {!column.nullable && (
        <span className="text-xs text-red-400" title="Not Null">*</span>
      )}
    </div>
  );
}

