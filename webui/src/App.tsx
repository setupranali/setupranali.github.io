import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Datasets from './pages/Datasets';
import DatasetDetail from './pages/DatasetDetail';
import Sources from './pages/Sources';
import ApiKeys from './pages/ApiKeys';
import QueryPlayground from './pages/QueryPlayground';
import CatalogEditor from './pages/CatalogEditor';
import Analytics from './pages/Analytics';
import Settings from './pages/Settings';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="datasets" element={<Datasets />} />
        <Route path="datasets/:id" element={<DatasetDetail />} />
        <Route path="sources" element={<Sources />} />
        <Route path="api-keys" element={<ApiKeys />} />
        <Route path="playground" element={<QueryPlayground />} />
        <Route path="catalog" element={<CatalogEditor />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}

export default App;

