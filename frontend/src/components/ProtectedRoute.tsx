import { Navigate } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "../context/AuthContext";

const ProtectedRoute = ({ children }: { children: ReactNode }) => {
  const { user, loading } = useAuth();

  // Still checking localStorage/validating the token with the backend —
  // don't redirect yet, or you'd bounce a legit logged-in user to /login
  // for a split second on every page refresh.
  if (loading) {
    return <p style={{ padding: 50 }}>Loading...</p>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;