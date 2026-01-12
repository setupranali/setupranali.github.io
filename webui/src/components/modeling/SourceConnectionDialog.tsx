/**
 * Source Connection Dialog
 * 
 * Modal for adding/editing/testing data source connections.
 */

import React, { useState, useCallback } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Database,
  Server,
  Lock,
  Globe,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Eye,
  EyeOff,
} from 'lucide-react';
import { modelingApi } from '../../lib/modeling-api';
import type { ConnectionConfig, ConnectionTestResult } from '../../types/modeling';
import { cn } from '../../lib/utils';

interface SourceConnectionDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (config: ConnectionConfig, name: string) => void;
  initialConfig?: ConnectionConfig;
  initialName?: string;
}

const DEFAULT_PORTS: Record<string, number> = {
  postgres: 5432,
  mysql: 3306,
  starrocks: 9030,  // StarRocks MySQL port
  doris: 9030,      // Apache Doris MySQL port
  snowflake: 443,
  bigquery: 443,
  redshift: 5439,
  clickhouse: 9000,
  duckdb: 0,
  sqlite: 0,
  sqlserver: 1433,
  oracle: 1521,
  databricks: 443,
  trino: 8080,
  presto: 8080,
  mariadb: 3306,
};

export function SourceConnectionDialog({
  isOpen,
  onClose,
  onSave,
  initialConfig,
  initialName,
}: SourceConnectionDialogProps) {
  const [name, setName] = useState(initialName || '');
  const [config, setConfig] = useState<ConnectionConfig>(
    initialConfig || {
      engine: 'postgres',
      host: '',
      port: 5432,
      database: '',
      username: '',
      password: '',
      ssl: false,
      catalog: '',
      extra: {},
    }
  );
  
  // Engines that support catalogs (StarRocks, Doris, Trino, etc.)
  const supportsCatalog = ['starrocks', 'doris', 'trino', 'presto'].includes(config.engine);
  const [showPassword, setShowPassword] = useState(false);
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null);

  // Fetch supported engines
  const { data: engines } = useQuery({
    queryKey: ['engines'],
    queryFn: () => modelingApi.getEngines(),
  });

  // Test connection mutation
  const testMutation = useMutation({
    mutationFn: () => modelingApi.testConnection(config),
    onSuccess: (result) => setTestResult(result),
    onError: (error: Error) =>
      setTestResult({ success: false, message: error.message }),
  });

  const handleEngineChange = useCallback((engine: string) => {
    setConfig((prev) => ({
      ...prev,
      engine,
      port: DEFAULT_PORTS[engine] || prev.port,
    }));
    setTestResult(null);
  }, []);

  const handleInputChange = useCallback(
    (field: keyof ConnectionConfig, value: string | number | boolean) => {
      setConfig((prev) => ({ ...prev, [field]: value }));
      setTestResult(null);
    },
    []
  );

  const handleTest = () => {
    testMutation.mutate();
  };

  const handleSave = () => {
    if (!name.trim()) {
      alert('Please enter a connection name');
      return;
    }
    // For editing, allow save if test was successful OR if editing mode (has initialConfig)
    // This allows updating name without re-testing if config hasn't changed
    if (!testResult?.success && !initialConfig) {
      alert('Please test the connection before saving');
      return;
    }
    onSave(config, name);
  };

  const isEditMode = !!initialConfig;

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Dialog */}
      <div className="relative bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-500/20 rounded-lg">
              <Database className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">
                {initialConfig ? 'Edit Connection' : 'New Connection'}
              </h2>
              <p className="text-sm text-slate-400">
                Configure your data source connection
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <XCircle className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-6 overflow-y-auto max-h-[calc(90vh-180px)]">
          {/* Connection Name */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300">
              Connection Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My PostgreSQL Database"
              className="w-full px-4 py-2.5 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>

          {/* Engine Selection */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300">
              Database Engine
            </label>
            <div className="grid grid-cols-4 gap-2">
              {engines?.map((engine) => (
                <button
                  key={engine.id}
                  onClick={() => handleEngineChange(engine.id)}
                  className={cn(
                    'px-3 py-2 rounded-lg text-sm font-medium transition-all',
                    config.engine === engine.id
                      ? 'bg-indigo-500 text-white'
                      : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  )}
                >
                  {engine.name}
                </button>
              ))}
            </div>
          </div>

          {/* Connection Details */}
          <div className="grid grid-cols-2 gap-4">
            {/* Host */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                <Server className="w-4 h-4" />
                Host
              </label>
              <input
                type="text"
                value={config.host}
                onChange={(e) => handleInputChange('host', e.target.value)}
                placeholder="localhost"
                className="w-full px-4 py-2.5 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {/* Port */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300">Port</label>
              <input
                type="number"
                value={config.port}
                onChange={(e) => handleInputChange('port', parseInt(e.target.value))}
                className="w-full px-4 py-2.5 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {/* Database */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                <Database className="w-4 h-4" />
                Database
              </label>
              <input
                type="text"
                value={config.database}
                onChange={(e) => handleInputChange('database', e.target.value)}
                placeholder="my_database"
                className="w-full px-4 py-2.5 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {/* Username */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300">Username</label>
              <input
                type="text"
                value={config.username}
                onChange={(e) => handleInputChange('username', e.target.value)}
                placeholder="admin"
                className="w-full px-4 py-2.5 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          {/* Catalog - Only for StarRocks, Doris, Trino, Presto */}
          {supportsCatalog && (
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                <Database className="w-4 h-4" />
                Catalog
                <span className="text-xs text-slate-500">(optional)</span>
              </label>
              <input
                type="text"
                value={config.catalog || ''}
                onChange={(e) => handleInputChange('catalog', e.target.value)}
                placeholder="e.g., iceberg_catalog, hive_catalog"
                className="w-full px-4 py-2.5 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <p className="text-xs text-slate-500">
                Specify a catalog name to access external data sources like Iceberg, Hive, or other catalogs.
                Leave empty to use the default catalog.
              </p>
            </div>
          )}

          {/* Password */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
              <Lock className="w-4 h-4" />
              Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={config.password}
                onChange={(e) => handleInputChange('password', e.target.value)}
                placeholder="••••••••"
                className="w-full px-4 py-2.5 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 pr-12"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-300"
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>

          {/* SSL Toggle */}
          <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg">
            <div className="flex items-center gap-3">
              <Globe className="w-5 h-5 text-slate-400" />
              <div>
                <p className="text-sm font-medium text-white">Use SSL/TLS</p>
                <p className="text-xs text-slate-400">
                  Encrypt connection to the database
                </p>
              </div>
            </div>
            <button
              onClick={() => handleInputChange('ssl', !config.ssl)}
              className={cn(
                'relative w-12 h-6 rounded-full transition-colors',
                config.ssl ? 'bg-indigo-500' : 'bg-slate-600'
              )}
            >
              <span
                className={cn(
                  'absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform',
                  config.ssl && 'translate-x-6'
                )}
              />
            </button>
          </div>

          {/* Test Result */}
          {testResult && (
            <div
              className={cn(
                'p-4 rounded-lg flex items-start gap-3',
                testResult.success
                  ? 'bg-emerald-500/10 border border-emerald-500/30'
                  : 'bg-red-500/10 border border-red-500/30'
              )}
            >
              {testResult.success ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
              ) : (
                <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              )}
              <div>
                <p
                  className={cn(
                    'text-sm font-medium',
                    testResult.success ? 'text-emerald-300' : 'text-red-300'
                  )}
                >
                  {testResult.success ? 'Connection Successful' : 'Connection Failed'}
                </p>
                <p className="text-xs text-slate-400 mt-1">{testResult.message}</p>
                {testResult.latencyMs && (
                  <p className="text-xs text-slate-500 mt-1">
                    Latency: {testResult.latencyMs}ms
                    {testResult.serverVersion && ` • ${testResult.serverVersion}`}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-700 bg-slate-800/50">
          <button
            onClick={handleTest}
            disabled={testMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors disabled:opacity-50"
          >
            {testMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Database className="w-4 h-4" />
            )}
            Test Connection
          </button>

          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-slate-300 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!testResult?.success && !isEditMode}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <CheckCircle2 className="w-4 h-4" />
              {isEditMode ? 'Update Connection' : 'Save Connection'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

