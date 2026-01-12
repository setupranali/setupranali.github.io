import { BarChart3, TrendingUp } from 'lucide-react';

export default function Analytics() {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-white">Analytics</h1>
        <p className="text-slate-400">Usage metrics and insights</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-2">
            <BarChart3 className="w-5 h-5 text-indigo-400" />
            <span className="text-slate-400 text-sm">Total Queries</span>
          </div>
          <p className="text-3xl font-semibold text-white">0</p>
        </div>
        
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-2">
            <TrendingUp className="w-5 h-5 text-green-400" />
            <span className="text-slate-400 text-sm">Avg Response Time</span>
          </div>
          <p className="text-3xl font-semibold text-white">--</p>
        </div>
        
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-2">
            <BarChart3 className="w-5 h-5 text-amber-400" />
            <span className="text-slate-400 text-sm">Active Sources</span>
          </div>
          <p className="text-3xl font-semibold text-white">0</p>
        </div>
      </div>
      
      <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-12 text-center">
        <BarChart3 className="w-12 h-12 text-slate-600 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-slate-400 mb-2">No Data Yet</h3>
        <p className="text-sm text-slate-500">
          Analytics will appear once you start running queries
        </p>
      </div>
    </div>
  );
}

