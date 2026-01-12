import { Settings as SettingsIcon, Moon, Sun, Bell, Shield } from 'lucide-react';

export default function Settings() {
  return (
    <div className="p-6 max-w-3xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-white">Settings</h1>
        <p className="text-slate-400">Configure your preferences</p>
      </div>
      
      <div className="space-y-6">
        {/* Appearance */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <Moon className="w-5 h-5 text-indigo-400" />
            <h2 className="text-lg font-medium text-white">Appearance</h2>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-300">Dark Mode</p>
              <p className="text-sm text-slate-500">Use dark theme</p>
            </div>
            <div className="w-12 h-6 bg-indigo-500 rounded-full relative cursor-pointer">
              <span className="absolute right-1 top-1 w-4 h-4 bg-white rounded-full" />
            </div>
          </div>
        </div>
        
        {/* Notifications */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <Bell className="w-5 h-5 text-amber-400" />
            <h2 className="text-lg font-medium text-white">Notifications</h2>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-300">Query Alerts</p>
              <p className="text-sm text-slate-500">Get notified on slow queries</p>
            </div>
            <div className="w-12 h-6 bg-slate-600 rounded-full relative cursor-pointer">
              <span className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full" />
            </div>
          </div>
        </div>
        
        {/* Security */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <Shield className="w-5 h-5 text-green-400" />
            <h2 className="text-lg font-medium text-white">Security</h2>
          </div>
          <div className="space-y-4">
            <div>
              <p className="text-slate-300 mb-1">Session Timeout</p>
              <select className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm">
                <option>15 minutes</option>
                <option>30 minutes</option>
                <option>1 hour</option>
                <option>Never</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

