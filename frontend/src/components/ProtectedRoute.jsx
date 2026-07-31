import { Navigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

export function ProtectedRoute({ children, allowedRoles, requireAssigned }) {
  const { session, profile, loading } = useAuth();

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center text-slate-500">Cargando...</div>;
  }
  if (!session) {
    return <Navigate to="/login" replace />;
  }
  if (allowedRoles && !allowedRoles.includes(profile?.role)) {
    return <Navigate to="/" replace />;
  }
  const isStaff = profile?.role === "admin" || profile?.role === "dispatcher";
  if (requireAssigned && !isStaff && !profile?.is_assigned) {
    return <Navigate to="/pending" replace />;
  }
  return children;
}
