import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { 
  Database, 
  Server, 
  Key, 
  Activity,
  Clock,
  AlertTriangle,
  CheckCircle
} from 'lucide-react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts';
import { api } from '../lib/api';

export default function Dashboard() {
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: api.getHealth,
    refetchInterval: 30000,
    refetchOnMount: 'always',
    staleTime: 0,
  });

  const { data: datasets } = useQuery({
    queryKey: ['datasets'],
    queryFn: api.getDatasets,
    refetchOnMount: 'always',
    staleTime: 0,
  });

  const { data: sources } = useQuery({
    queryKey: ['sources'],
    queryFn: api.getSources,
    refetchOnMount: 'always',
    staleTime: 0,
  });

  const { data: apiKeys } = useQuery({
    queryKey: ['apiKeys'],
    queryFn: api.getApiKeys,
    refetchOnMount: 'always',
    staleTime: 0,
  });

  // Fetch real analytics data
  const { data: analytics, error: analyticsError } = useQuery({
    queryKey: ['analytics'],
    queryFn: () => api.getAnalytics(24), // Pass hours as number, not object
    refetchInterval: 60000, // Refresh every minute
    refetchOnMount: 'always',
    staleTime: 0,
  });

  // Debug: Log analytics data
  useEffect(() => {
    if (analyticsError) {
      console.error('❌ Analytics API Error:', analyticsError);
    } else if (analytics) {
      console.log('✅ Analytics data received:', {
        hasQueryVolume: !!analytics.query_volume,
        queryVolumeLength: analytics.query_volume?.length || 0,
        hasLatency: !!analytics.latency,
        hasRecentQueries: !!analytics.recent_queries,
        recentQueriesLength: analytics.recent_queries?.length || 0,
        stats: analytics.stats,
      });
    } else {
      console.log('⏳ Analytics data is loading...');
    }
  }, [analytics, analyticsError]);

  const stats = [
    {
      name: 'Datasets',
      value: datasets?.items?.length || 0,
      icon: Database,
      color: 'text-blue-600 bg-blue-100 dark:bg-blue-900/50',
    },
    {
      name: 'Data Sources',
      value: sources?.items?.length || 0,
      icon: Server,
      color: 'text-green-600 bg-green-100 dark:bg-green-900/50',
    },
    {
      name: 'API Keys',
      value: apiKeys?.items?.length || 0,
      icon: Key,
      color: 'text-purple-600 bg-purple-100 dark:bg-purple-900/50',
    },
    {
      name: 'Cache Hit Rate',
      value: analytics?.stats?.cache_hit_rate 
        ? `${(analytics.stats.cache_hit_rate * 100).toFixed(1)}%` 
        : (health?.cache?.enabled ? 'N/A' : 'Disabled'),
      icon: Activity,
      color: 'text-orange-600 bg-orange-100 dark:bg-orange-900/50',
    },
  ];

  // Use real analytics data or fallback to empty arrays
  const queryVolumeData = analytics?.query_volume || [];
  const latencyData = analytics?.latency || [];
  const recentQueries = analytics?.recent_queries || [];

  // Debug: Log data being used for charts
  useEffect(() => {
    console.log('📊 Chart Data:', {
      queryVolumeDataLength: queryVolumeData.length,
      latencyDataLength: latencyData.length,
      recentQueriesLength: recentQueries.length,
      firstQueryVolumeItem: queryVolumeData[0],
      hasNonZeroQueries: queryVolumeData.some((v: any) => v.queries > 0),
    });
  }, [queryVolumeData, latencyData, recentQueries]);

  // Show error message if analytics failed to load
  if (analyticsError) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Overview of your SetuPranali instance
          </p>
        </div>
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-red-800 dark:text-red-200">
            <strong>Error loading analytics:</strong> {analyticsError instanceof Error ? analyticsError.message : 'Unknown error'}
          </p>
          <p className="text-sm text-red-600 dark:text-red-400 mt-2">
            Please check the browser console for more details.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Overview of your SetuPranali instance
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <div
            key={stat.name}
            className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6"
          >
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-lg ${stat.color}`}>
                <stat.icon className="h-6 w-6" />
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">{stat.name}</p>
                <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                  {stat.value}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Queries Chart */}
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Query Volume
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Last 24 hours
              </p>
            </div>
            <div className="flex items-center gap-4 text-sm">
              <span className="flex items-center gap-2">
                <span className="h-3 w-3 rounded-full bg-indigo-500" />
                Queries
              </span>
              <span className="flex items-center gap-2">
                <span className="h-3 w-3 rounded-full bg-red-500" />
                Errors
              </span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={queryVolumeData.length > 0 ? queryVolumeData : [{ time: '00:00', queries: 0, errors: 0 }]}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
              <XAxis dataKey="time" stroke="#9CA3AF" fontSize={12} />
              <YAxis stroke="#9CA3AF" fontSize={12} />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#1F2937', 
                  border: 'none',
                  borderRadius: '8px',
                  color: '#fff'
                }} 
              />
              <Area 
                type="monotone" 
                dataKey="queries" 
                stroke="#6366F1" 
                fill="#6366F1" 
                fillOpacity={0.2} 
              />
              <Area 
                type="monotone" 
                dataKey="errors" 
                stroke="#EF4444" 
                fill="#EF4444" 
                fillOpacity={0.2} 
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Latency Chart */}
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Query Latency
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Response time percentiles
              </p>
            </div>
            <div className="flex items-center gap-4 text-sm">
              <span className="flex items-center gap-2">
                <span className="h-3 w-3 rounded-full bg-green-500" />
                p50
              </span>
              <span className="flex items-center gap-2">
                <span className="h-3 w-3 rounded-full bg-yellow-500" />
                p95
              </span>
              <span className="flex items-center gap-2">
                <span className="h-3 w-3 rounded-full bg-red-500" />
                p99
              </span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={latencyData.length > 0 ? latencyData : [{ time: '00:00', p50: 0, p95: 0, p99: 0 }]}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
              <XAxis dataKey="time" stroke="#9CA3AF" fontSize={12} />
              <YAxis stroke="#9CA3AF" fontSize={12} unit="ms" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#1F2937', 
                  border: 'none',
                  borderRadius: '8px',
                  color: '#fff'
                }} 
              />
              <Line type="monotone" dataKey="p50" stroke="#22C55E" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="p95" stroke="#EAB308" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="p99" stroke="#EF4444" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent Queries */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Recent Queries
          </h3>
        </div>
        <div className="divide-y divide-gray-200 dark:divide-gray-800">
          {recentQueries.length > 0 ? (
            recentQueries.map((query: any, i: number) => (
            <div key={i} className="px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-4">
                {query.status === 'success' && (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                )}
                {query.status === 'warning' && (
                  <AlertTriangle className="h-5 w-5 text-yellow-500" />
                )}
                {query.status === 'error' && (
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                )}
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">
                    {query.dataset}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {query.metrics && query.metrics.length > 0 
                      ? query.metrics.join(', ')
                      : (query.dimensions && query.dimensions.length > 0
                          ? `Columns: ${query.dimensions.join(', ')}`
                          : 'No metrics or dimensions')}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                <Clock className="h-4 w-4" />
                {query.duration}
              </div>
            </div>
          ))
          ) : (
            <div className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
              No queries yet. Execute some queries to see analytics here.
            </div>
          )}
        </div>
      </div>

      {/* System Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="h-3 w-3 rounded-full bg-green-500 animate-pulse" />
            <h3 className="font-semibold text-gray-900 dark:text-white">API Status</h3>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            All systems operational
          </p>
          <div className="mt-4 text-sm">
            <div className="flex justify-between py-1">
              <span className="text-gray-500 dark:text-gray-400">Uptime</span>
              <span className="text-gray-900 dark:text-white">99.99%</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-gray-500 dark:text-gray-400">Avg Response</span>
              <span className="text-gray-900 dark:text-white">
                {analytics?.stats?.avg_duration_ms 
                  ? `${Math.round(analytics.stats.avg_duration_ms)}ms` 
                  : 'N/A'}
              </span>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className={`h-3 w-3 rounded-full ${health?.cache?.enabled ? 'bg-green-500' : 'bg-gray-400'}`} />
            <h3 className="font-semibold text-gray-900 dark:text-white">Cache Status</h3>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {health?.cache?.enabled ? 'Redis connected' : 'Cache disabled'}
          </p>
          {health?.cache?.enabled && (
            <div className="mt-4 text-sm">
              <div className="flex justify-between py-1">
                <span className="text-gray-500 dark:text-gray-400">Hit Rate</span>
                <span className="text-gray-900 dark:text-white">
                  {analytics?.stats?.cache_hit_rate 
                    ? `${(analytics.stats.cache_hit_rate * 100).toFixed(1)}%` 
                    : 'N/A'}
                </span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-gray-500 dark:text-gray-400">Size</span>
                <span className="text-gray-900 dark:text-white">256 MB</span>
              </div>
            </div>
          )}
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className={`h-3 w-3 rounded-full ${health?.encryption?.configured ? 'bg-green-500' : 'bg-yellow-500'}`} />
            <h3 className="font-semibold text-gray-900 dark:text-white">Security</h3>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {health?.encryption?.configured ? 'Encryption enabled' : 'Configure encryption'}
          </p>
          <div className="mt-4 text-sm">
            <div className="flex justify-between py-1">
              <span className="text-gray-500 dark:text-gray-400">RLS</span>
              <span className="text-green-500">Active</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-gray-500 dark:text-gray-400">Rate Limiting</span>
              <span className="text-green-500">Active</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

