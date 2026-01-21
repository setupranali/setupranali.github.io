import { useState, useEffect } from 'react';
import { Moon, Sun, Bell, Shield } from 'lucide-react';
import { useThemeStore } from '../store/theme';

export default function Settings() {
  const { isDark, toggle: toggleTheme } = useThemeStore();
  const [queryAlerts, setQueryAlerts] = useState(() => {
    const saved = localStorage.getItem('queryAlerts');
    return saved ? JSON.parse(saved) : false;
  });
  const [sessionTimeout, setSessionTimeout] = useState(() => {
    return localStorage.getItem('sessionTimeout') || '1 hour';
  });

  // Save query alerts to localStorage
  useEffect(() => {
    localStorage.setItem('queryAlerts', JSON.stringify(queryAlerts));
  }, [queryAlerts]);

  // Save session timeout to localStorage
  useEffect(() => {
    localStorage.setItem('sessionTimeout', sessionTimeout);
  }, [sessionTimeout]);

  const handleToggleTheme = () => {
    toggleTheme();
  };

  const handleToggleQueryAlerts = () => {
    setQueryAlerts(!queryAlerts);
  };

  const handleSessionTimeoutChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSessionTimeout(e.target.value);
  };

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
            {isDark ? (
              <Moon className="w-5 h-5 text-indigo-400" />
            ) : (
              <Sun className="w-5 h-5 text-indigo-400" />
            )}
            <h2 className="text-lg font-medium text-white">Appearance</h2>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-300">Dark Mode</p>
              <p className="text-sm text-slate-500">Use dark theme</p>
            </div>
            <button
              onClick={handleToggleTheme}
              className={`w-12 h-6 rounded-full relative cursor-pointer transition-colors ${
                isDark ? 'bg-indigo-500' : 'bg-slate-600'
              }`}
              aria-label="Toggle dark mode"
            >
              <span
                className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                  isDark ? 'right-1' : 'left-1'
                }`}
              />
            </button>
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
            <button
              onClick={handleToggleQueryAlerts}
              className={`w-12 h-6 rounded-full relative cursor-pointer transition-colors ${
                queryAlerts ? 'bg-indigo-500' : 'bg-slate-600'
              }`}
              aria-label="Toggle query alerts"
            >
              <span
                className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                  queryAlerts ? 'right-1' : 'left-1'
                }`}
              />
            </button>
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
              <select
                value={sessionTimeout}
                onChange={handleSessionTimeoutChange}
                className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="15 minutes">15 minutes</option>
                <option value="30 minutes">30 minutes</option>
                <option value="1 hour">1 hour</option>
                <option value="Never">Never</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

