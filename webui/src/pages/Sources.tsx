import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  Server, 
  Plus, 
  Trash2, 
  RefreshCw, 
  CheckCircle2, 
  XCircle, 
  Loader2,
  Edit,
  Plug,
  Settings
} from 'lucide-react';
import { modelingApi, DataSource } from '../lib/modeling-api';
import { SourceConnectionDialog } from '../components/modeling/SourceConnectionDialog';
import type { ConnectionConfig } from '../types/modeling';

export default function Sources() {
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [editingSource, setEditingSource] = useState<DataSource | null>(null);
  const queryClient = useQueryClient();

  // Fetch sources from API
  const sourcesQuery = useQuery({
    queryKey: ['sources'],
    queryFn: () => modelingApi.listSources(),
    refetchOnMount: 'always', // Always refetch when component mounts
    staleTime: 0, // Consider data always stale
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => modelingApi.deleteSource(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources'] });
    },
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: ({ name, config }: { name: string; config: any }) => 
      modelingApi.createSource(name, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources'] });
      setShowAddDialog(false);
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, name, config }: { id: string; name: string; config: any }) => 
      modelingApi.updateSource(id, {
        name,
        type: config.engine || 'postgres',
        config: {
          host: config.host,
          port: config.port,
          database: config.database,
          user: config.username,
          password: config.password,
          ssl: config.ssl,
          ...(config.catalog ? { catalog: config.catalog } : {}),
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources'] });
      setEditingSource(null);
    },
  });

  // Convert DataSource to ConnectionConfig for editing
  const getConnectionConfig = (source: DataSource): ConnectionConfig => {
    const cfg = source.config || {};
    return {
      engine: source.type || 'postgres',
      host: cfg.host || '',
      port: cfg.port || 5432,
      database: cfg.database || '',
      username: cfg.user || '',
      password: cfg.password || '',
      ssl: cfg.ssl || false,
      catalog: cfg.catalog || '',
      extra: {},
    };
  };

  const handleEdit = (source: DataSource) => {
    setEditingSource(source);
  };

  const handleDelete = async (id: string, name: string) => {
    if (confirm(`Are you sure you want to delete "${name}"?`)) {
      deleteMutation.mutate(id);
    }
  };

  const getSourceIcon = (type: string) => {
    switch (type) {
      case 'mysql':
        return '🐬';
      case 'postgres':
        return '🐘';
      case 'sqlite':
        return '📦';
      case 'duckdb':
        return '🦆';
      default:
        return '💾';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'text-emerald-400';
      case 'inactive':
        return 'text-slate-400';
      case 'error':
        return 'text-red-400';
      default:
        return 'text-slate-400';
    }
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-white">Data Sources</h1>
          <p className="text-slate-400">Manage database connections</p>
        </div>
        <div className="flex items-center gap-2">
          <button 
            onClick={() => sourcesQuery.refetch()}
            disabled={sourcesQuery.isFetching}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <RefreshCw className={`w-5 h-5 text-slate-400 ${sourcesQuery.isFetching ? 'animate-spin' : ''}`} />
          </button>
          <button 
            onClick={() => setShowAddDialog(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Source
          </button>
        </div>
      </div>

      {/* Loading State */}
      {sourcesQuery.isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
        </div>
      )}

      {/* Error State */}
      {sourcesQuery.isError && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-center">
          <XCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-red-400 mb-2">Failed to Load Sources</h3>
          <p className="text-sm text-slate-400 mb-4">
            {(sourcesQuery.error as Error)?.message || 'An error occurred'}
          </p>
          <button
            onClick={() => sourcesQuery.refetch()}
            className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Empty State */}
      {sourcesQuery.isSuccess && sourcesQuery.data.length === 0 && (
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-12 text-center">
          <Server className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-slate-400 mb-2">No Sources Connected</h3>
          <p className="text-sm text-slate-500 mb-6">
            Add a data source to start querying your databases
          </p>
          <button 
            onClick={() => setShowAddDialog(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Your First Source
          </button>
        </div>
      )}

      {/* Sources Grid */}
      {sourcesQuery.isSuccess && sourcesQuery.data.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sourcesQuery.data.map((source) => (
            <div
              key={source.id}
              className="bg-slate-800/50 border border-slate-700 rounded-xl p-5 hover:border-slate-600 transition-colors group"
            >
              {/* Source Header */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-slate-700 rounded-lg flex items-center justify-center text-xl">
                    {getSourceIcon(source.type)}
                  </div>
                  <div>
                    <h3 className="font-medium text-white">{source.name}</h3>
                    <p className="text-xs text-slate-500 capitalize">{source.type}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => handleEdit(source)}
                    className="p-1.5 hover:bg-slate-600 rounded-lg transition-colors"
                    title="Edit source"
                  >
                    <Edit className="w-4 h-4 text-slate-400 hover:text-white" />
                  </button>
                  <button
                    onClick={() => handleDelete(source.id, source.name)}
                    disabled={deleteMutation.isPending}
                    className="p-1.5 hover:bg-red-500/20 rounded-lg transition-colors"
                    title="Delete source"
                  >
                    <Trash2 className="w-4 h-4 text-red-400" />
                  </button>
                </div>
              </div>

              {/* Connection Details */}
              {source.config && (
                <div className="mb-3 space-y-1 text-xs">
                  {source.config.host && (
                    <div className="flex items-center gap-2 text-slate-400">
                      <Server className="w-3 h-3" />
                      <span>{source.config.host}{source.config.port ? `:${source.config.port}` : ''}</span>
                    </div>
                  )}
                  {source.config.database && (
                    <div className="flex items-center gap-2 text-slate-400">
                      <Settings className="w-3 h-3" />
                      <span>{source.config.database}</span>
                    </div>
                  )}
                </div>
              )}

              {/* Status */}
              <div className="flex items-center gap-2 text-sm">
                {source.status === 'active' ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : (
                  <XCircle className="w-4 h-4 text-slate-400" />
                )}
                <span className={getStatusColor(source.status)}>
                  {source.status === 'active' ? 'Connected' : source.status}
                </span>
              </div>

              {/* Actions & Meta */}
              <div className="mt-4 pt-4 border-t border-slate-700 flex items-center justify-between">
                <span className="text-xs text-slate-500">
                  {new Date(source.created_at).toLocaleDateString()}
                </span>
                <button
                  onClick={() => handleEdit(source)}
                  className="flex items-center gap-1.5 px-2.5 py-1 text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg transition-colors"
                >
                  <Plug className="w-3 h-3" />
                  Configure
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Source Dialog */}
      {showAddDialog && (
        <SourceConnectionDialog
          isOpen={showAddDialog}
          onClose={() => setShowAddDialog(false)}
          onSave={(config, name) => {
            createMutation.mutate({ name, config });
          }}
        />
      )}

      {/* Edit Source Dialog */}
      {editingSource && (
        <SourceConnectionDialog
          isOpen={true}
          onClose={() => setEditingSource(null)}
          onSave={(config, name) => {
            updateMutation.mutate({ id: editingSource.id, name, config });
          }}
          initialConfig={getConnectionConfig(editingSource)}
          initialName={editingSource.name}
        />
      )}
    </div>
  );
}
