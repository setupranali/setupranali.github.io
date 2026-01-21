import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  Key, 
  Plus, 
  RefreshCw, 
  Loader2,
  XCircle,
  Trash2,
  Copy,
  Check,
  AlertTriangle
} from 'lucide-react';
import { api } from '../lib/api';

interface ApiKey {
  key_id: string;
  name: string;
  tenant: string;
  role: string;
  status: string;
  created_at: string | null;
  last_used_at: string | null;
}

interface NewApiKeyResponse extends ApiKey {
  api_key: string;
  warning: string;
}

export default function ApiKeys() {
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyTenant, setNewKeyTenant] = useState('default');
  const [newKeyRole, setNewKeyRole] = useState('user');
  const [createdKey, setCreatedKey] = useState<NewApiKeyResponse | null>(null);
  const [copiedKey, setCopiedKey] = useState(false);
  const queryClient = useQueryClient();

  // Fetch API keys
  const keysQuery = useQuery({
    queryKey: ['api-keys'],
    queryFn: async () => {
      const data = await api.getApiKeys();
      return data.items || [];
    },
    refetchOnMount: 'always',
    staleTime: 0,
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: async () => {
      const data = await api.createApiKey({
        name: newKeyName,
        tenant: newKeyTenant,
        role: newKeyRole,
      });
      return data;
    },
    onSuccess: (data) => {
      setCreatedKey(data);
      // Invalidate and refetch the keys list
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      // Also refetch immediately
      setTimeout(() => {
        keysQuery.refetch();
      }, 500);
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (keyId: string) => {
      await api.deleteApiKey(keyId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      // Also refetch immediately
      setTimeout(() => {
        keysQuery.refetch();
      }, 500);
    },
  });

  const handleCreate = () => {
    if (!newKeyName.trim()) return;
    createMutation.mutate();
  };

  const handleCopyKey = () => {
    if (createdKey?.api_key) {
      navigator.clipboard.writeText(createdKey.api_key);
      setCopiedKey(true);
      setTimeout(() => setCopiedKey(false), 2000);
    }
  };

  const handleCloseCreatedKey = () => {
    setCreatedKey(null);
    setShowCreateDialog(false);
    setNewKeyName('');
    setNewKeyTenant('default');
    setNewKeyRole('user');
  };

  const handleDelete = (keyId: string, name: string) => {
    if (confirm(`Are you sure you want to revoke "${name}"?`)) {
      deleteMutation.mutate(keyId);
    }
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'admin':
        return 'text-amber-400 bg-amber-400/10';
      case 'internal_admin':
        return 'text-red-400 bg-red-400/10';
      default:
        return 'text-slate-400 bg-slate-400/10';
    }
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-white">API Keys</h1>
          <p className="text-slate-400">Manage API access credentials</p>
        </div>
        <div className="flex items-center gap-2">
          <button 
            onClick={() => keysQuery.refetch()}
            disabled={keysQuery.isFetching}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <RefreshCw className={`w-5 h-5 text-slate-400 ${keysQuery.isFetching ? 'animate-spin' : ''}`} />
          </button>
          <button 
            onClick={() => setShowCreateDialog(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            Generate Key
          </button>
        </div>
      </div>

      {/* Create Dialog */}
      {showCreateDialog && !createdKey && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-semibold text-white mb-4">Generate New API Key</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Name</label>
                <input
                  type="text"
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  placeholder="My API Key"
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Tenant</label>
                <input
                  type="text"
                  value={newKeyTenant}
                  onChange={(e) => setNewKeyTenant(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Role</label>
                <select
                  value={newKeyRole}
                  onChange={(e) => setNewKeyRole(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowCreateDialog(false)}
                className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={!newKeyName.trim() || createMutation.isPending}
                className="px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-colors disabled:opacity-50"
              >
                {createMutation.isPending ? 'Creating...' : 'Generate'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Created Key Dialog */}
      {createdKey && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 w-full max-w-lg">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-emerald-500/20 rounded-lg flex items-center justify-center">
                <Check className="w-5 h-5 text-emerald-400" />
              </div>
              <h2 className="text-lg font-semibold text-white">API Key Created</h2>
            </div>

            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 mb-4">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-400 mt-0.5" />
                <p className="text-sm text-amber-300">
                  Copy this API key now. You won't be able to see it again!
                </p>
              </div>
            </div>

            <div className="bg-slate-900 rounded-lg p-3 mb-4">
              <div className="flex items-center justify-between">
                <code className="text-sm text-emerald-400 font-mono break-all">
                  {createdKey.api_key}
                </code>
                <button
                  onClick={handleCopyKey}
                  className="ml-3 p-2 hover:bg-slate-700 rounded-lg transition-colors"
                >
                  {copiedKey ? (
                    <Check className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <Copy className="w-4 h-4 text-slate-400" />
                  )}
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm mb-6">
              <div>
                <span className="text-slate-500">Name:</span>
                <span className="ml-2 text-white">{createdKey.name}</span>
              </div>
              <div>
                <span className="text-slate-500">Tenant:</span>
                <span className="ml-2 text-white">{createdKey.tenant}</span>
              </div>
              <div>
                <span className="text-slate-500">Role:</span>
                <span className="ml-2 text-white">{createdKey.role}</span>
              </div>
              <div>
                <span className="text-slate-500">Key ID:</span>
                <span className="ml-2 text-white font-mono text-xs">{createdKey.key_id}</span>
              </div>
            </div>

            <button
              onClick={handleCloseCreatedKey}
              className="w-full px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-colors"
            >
              Done
            </button>
          </div>
        </div>
      )}

      {/* Loading State */}
      {keysQuery.isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
        </div>
      )}

      {/* Error State */}
      {keysQuery.isError && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-center">
          <XCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-red-400 mb-2">Failed to Load API Keys</h3>
          <p className="text-sm text-slate-400 mb-4">
            {(keysQuery.error as Error)?.message || 'An error occurred'}
          </p>
          <button
            onClick={() => keysQuery.refetch()}
            className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Empty State */}
      {keysQuery.isSuccess && keysQuery.data.length === 0 && (
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-12 text-center">
          <Key className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-slate-400 mb-2">No API Keys</h3>
          <p className="text-sm text-slate-500 mb-6">
            Generate an API key to authenticate requests
          </p>
          <button 
            onClick={() => setShowCreateDialog(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            Generate Your First Key
          </button>
        </div>
      )}

      {/* Keys List */}
      {keysQuery.isSuccess && keysQuery.data.length > 0 && (
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-700">
                <th className="text-left text-xs font-medium text-slate-400 uppercase px-4 py-3">Name</th>
                <th className="text-left text-xs font-medium text-slate-400 uppercase px-4 py-3">Key ID</th>
                <th className="text-left text-xs font-medium text-slate-400 uppercase px-4 py-3">Tenant</th>
                <th className="text-left text-xs font-medium text-slate-400 uppercase px-4 py-3">Role</th>
                <th className="text-left text-xs font-medium text-slate-400 uppercase px-4 py-3">Status</th>
                <th className="text-left text-xs font-medium text-slate-400 uppercase px-4 py-3">Last Used</th>
                <th className="text-right text-xs font-medium text-slate-400 uppercase px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {keysQuery.data.map((key: ApiKey) => (
                <tr key={key.key_id} className="border-b border-slate-700/50 hover:bg-slate-800/50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Key className="w-4 h-4 text-indigo-400" />
                      <span className="text-white font-medium">{key.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <code className="text-xs text-slate-400 font-mono">{key.key_id}</code>
                  </td>
                  <td className="px-4 py-3 text-slate-300">{key.tenant}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs ${getRoleColor(key.role)}`}>
                      {key.role}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs ${
                      key.status === 'active' 
                        ? 'text-emerald-400 bg-emerald-400/10' 
                        : 'text-red-400 bg-red-400/10'
                    }`}>
                      {key.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-400">
                    {key.last_used_at 
                      ? new Date(key.last_used_at).toLocaleDateString()
                      : 'Never'
                    }
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleDelete(key.key_id, key.name)}
                      disabled={deleteMutation.isPending || key.status === 'revoked'}
                      className="p-1.5 hover:bg-red-500/20 rounded-lg transition-colors disabled:opacity-50"
                      title="Revoke key"
                    >
                      <Trash2 className="w-4 h-4 text-red-400" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
