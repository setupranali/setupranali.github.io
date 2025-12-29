import { useQuery } from '@tanstack/react-query';
import { 
  Database, 
  Server, 
  Key, 
  Activity,
  TrendingUp,
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

// Mock data for demo
const mockQueryData = [
  { time: '00:00', queries: 120, errors: 2 },
  { time: '04:00', queries: 80, errors: 1 },
  { time: '08:00', queries: 350, errors: 5 },
  { time: '12:00', queries: 520, errors: 8 },
  { time: '16:00', queries: 480, errors: 6 },
  { time: '20:00', queries: 280, errors: 3 },
];

const mockLatencyData = [
  { time: '00:00', p50: 45, p95: 120, p99: 250 },
  { time: '04:00', p50: 42, p95: 110, p99: 230 },
  { time: '08:00', p50: 58, p95: 180, p99: 380 },
  { time: '12:00', p50: 62, p95: 200, p99: 420 },
  { time: '16:00', p50: 55, p95: 170, p99: 350 },
  { time: '20:00', p50: 48, p95: 130, p99: 280 },
];

export default function Dashboard() {
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: api.getHealth,
    refetchInterval: 30000,
  });

  const { data: datasets } = useQuery({
    queryKey: ['datasets'],
    queryFn: api.getDatasets,
  });

  const stats = [
    {
      name: 'Datasets',
      value: datasets?.items?.length || 0,
      icon: Database,
      color: 'text-blue-600 bg-blue-100 dark:bg-blue-900/50',
    },
    {
      name: 'Data Sources',
      value: 3,
      icon: Server,
      color: 'text-green-600 bg-green-100 dark:bg-green-900/50',
    },
    {
      name: 'API Keys',
      value: 5,
      icon: Key,
      color: 'text-purple-600 bg-purple-100 dark:bg-purple-900/50',
    },
    {
      name: 'Cache Hit Rate',
      value: health?.cache?.enabled ? '94.5%' : 'N/A',
      icon: Activity,
      color: 'text-orange-600 bg-orange-100 dark:bg-orange-900/50',
    },
  ];

  const recentQueries = [
    { dataset: 'orders', metrics: ['revenue', 'count'], duration: '45ms', status: 'success' },
    { dataset: 'customers', metrics: ['lifetime_value'], duration: '120ms', status: 'success' },
    { dataset: 'products', metrics: ['inventory'], duration: '380ms', status: 'warning' },
    { dataset: 'orders', metrics: ['aov'], duration: '52ms', status: 'success' },
    { dataset: 'sessions', metrics: ['bounce_rate'], duration: '890ms', status: 'error' },
  ];

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
            <AreaChart data={mockQueryData}>
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
            <LineChart data={mockLatencyData}>
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
          {recentQueries.map((query, i) => (
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
                    {query.metrics.join(', ')}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                <Clock className="h-4 w-4" />
                {query.duration}
              </div>
            </div>
          ))}
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
              <span className="text-gray-900 dark:text-white">48ms</span>
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
                <span className="text-gray-900 dark:text-white">94.5%</span>
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

