import { Routes, Route, Navigate } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';

// Lazy load pages for better performance
const Datasets = lazy(() => import('./pages/Datasets'));
const DatasetDetail = lazy(() => import('./pages/DatasetDetail'));
const SemanticModelDetail = lazy(() => import('./pages/SemanticModelDetail'));
const Sources = lazy(() => import('./pages/Sources'));
const ApiKeys = lazy(() => import('./pages/ApiKeys'));
const QueryPlayground = lazy(() => import('./pages/QueryPlayground'));
const ContractEditor = lazy(() => import('./pages/ContractEditor'));
const Analytics = lazy(() => import('./pages/Analytics'));
const Settings = lazy(() => import('./pages/Settings'));
const ModelingStudio = lazy(() => import('./pages/ModelingStudio'));

// Loading fallback
const PageLoader = () => (
  <div className="h-full flex items-center justify-center">
    <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
  </div>
);

function App() {
  return (
    <Routes>
      {/* Modeling Studio - Full screen, no layout */}
      <Route
        path="/modeling"
        element={
          <Suspense fallback={<PageLoader />}>
            <ModelingStudio />
          </Suspense>
        }
      />
      
      {/* Standard Layout Routes */}
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route
          path="datasets"
          element={
            <Suspense fallback={<PageLoader />}>
              <Datasets />
            </Suspense>
          }
        />
        <Route
          path="datasets/:id"
          element={
            <Suspense fallback={<PageLoader />}>
              <DatasetDetail />
            </Suspense>
          }
        />
        <Route
          path="models/:id"
          element={
            <Suspense fallback={<PageLoader />}>
              <SemanticModelDetail />
            </Suspense>
          }
        />
        <Route
          path="sources"
          element={
            <Suspense fallback={<PageLoader />}>
              <Sources />
            </Suspense>
          }
        />
        <Route
          path="api-keys"
          element={
            <Suspense fallback={<PageLoader />}>
              <ApiKeys />
            </Suspense>
          }
        />
        <Route
          path="playground"
          element={
            <Suspense fallback={<PageLoader />}>
              <QueryPlayground />
            </Suspense>
          }
        />
        <Route
          path="contracts"
          element={
            <Suspense fallback={<PageLoader />}>
              <ContractEditor />
            </Suspense>
          }
        />
        <Route
          path="analytics"
          element={
            <Suspense fallback={<PageLoader />}>
              <Analytics />
            </Suspense>
          }
        />
        <Route
          path="settings"
          element={
            <Suspense fallback={<PageLoader />}>
              <Settings />
            </Suspense>
          }
        />
      </Route>
    </Routes>
  );
}

export default App;

