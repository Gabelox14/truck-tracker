import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";

import { ProtectedRoute } from "./components/ProtectedRoute";
import { useAuth } from "./context/AuthContext";
import { AuthProvider } from "./context/AuthContext";
import { ToastProvider } from "./context/ToastContext";
import AdminPage from "./pages/AdminPage";
import DriverPage from "./pages/DriverPage";
import LoginPage from "./pages/LoginPage";
import VerifiedPage from "./pages/VerifiedPage";

function HomeRedirect() {
  const { profile } = useAuth();
  if (profile?.role === "admin" || profile?.role === "dispatcher") {
    return <Navigate to="/admin" replace />;
  }
  return <Navigate to="/driver" replace />;
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
                  <AdminPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/driver"
              element={
                <ProtectedRoute>
                  <DriverPage />
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
