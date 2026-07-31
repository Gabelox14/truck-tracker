import { lazy, Suspense } from "react";
import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";

import { ProtectedRoute } from "./components/ProtectedRoute";
import { useAuth } from "./context/AuthContext";
import { AuthProvider } from "./context/AuthContext";
import { ToastProvider } from "./context/ToastContext";
import LoginPage from "./pages/LoginPage";
import PendingAccessPage from "./pages/PendingAccessPage";
import VerifiedPage from "./pages/VerifiedPage";

const AdminPage = lazy(() => import("./pages/AdminPage"));
const DriverPage = lazy(() => import("./pages/DriverPage"));

function RouteFallback() {
  return <div className="flex min-h-screen items-center justify-center text-slate-500">Cargando...</div>;
}

function HomeRedirect() {
  const { profile } = useAuth();
  if (profile?.role === "admin" || profile?.role === "dispatcher") {
    return <Navigate to="/admin" replace />;
  }
  if (profile?.is_assigned) {
    return <Navigate to="/driver" replace />;
  }
  return <Navigate to="/pending" replace />;
}

function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <Router>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/verified" element={<VerifiedPage />} />
            <Route
              path="/pending"
              element={
                <ProtectedRoute>
                  <PendingAccessPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <HomeRedirect />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin"
              element={
                <ProtectedRoute allowedRoles={["admin", "dispatcher"]}>
                  <Suspense fallback={<RouteFallback />}>
                    <AdminPage />
                  </Suspense>
                </ProtectedRoute>
              }
            />
            <Route
              path="/driver"
              element={
                <ProtectedRoute requireAssigned>
                  <Suspense fallback={<RouteFallback />}>
                    <DriverPage />
                  </Suspense>
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Router>
      </AuthProvider>
    </ToastProvider>
  );
}

export default App;
