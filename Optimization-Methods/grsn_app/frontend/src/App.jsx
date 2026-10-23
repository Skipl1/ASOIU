import { lazy, Suspense } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Layout from "./components/Layout.jsx";
import { Loading } from "./components/ui.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";

const Profile = lazy(() => import("./pages/Profile.jsx"));
const Restrictions = lazy(() => import("./pages/Restrictions.jsx"));
const Ingredients = lazy(() => import("./pages/Ingredients.jsx"));
const Generate = lazy(() => import("./pages/Generate.jsx"));
const History = lazy(() => import("./pages/History.jsx"));
const Reports = lazy(() => import("./pages/Reports.jsx"));
const Analysis = lazy(() => import("./pages/Analysis.jsx"));
const Admin = lazy(() => import("./pages/Admin.jsx"));

function RequireAuth({ children, admin = false }) {
  const { session, isAdmin } = useAuth();
  const location = useLocation();
  if (!session) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (admin && !isAdmin) return <Navigate to="/profile" replace />;
  return children;
}

function GuestOnly({ children }) {
  const { session } = useAuth();
  return session ? <Navigate to="/profile" replace /> : children;
}

export default function App() {
  return (
    <Suspense fallback={<div className="page-loading"><Loading /></div>}>
      <Routes>
        <Route path="/login" element={<GuestOnly><Login /></GuestOnly>} />
        <Route path="/register" element={<GuestOnly><Register /></GuestOnly>} />
        <Route element={<RequireAuth><Layout /></RequireAuth>}>
          <Route path="/profile" element={<Profile />} />
          <Route path="/restrictions" element={<Restrictions />} />
          <Route path="/ingredients" element={<Ingredients />} />
          <Route path="/generate" element={<Generate />} />
          <Route path="/history" element={<History />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/analysis" element={<Analysis />} />
          <Route path="/admin" element={<RequireAuth admin><Admin /></RequireAuth>} />
        </Route>
        <Route path="*" element={<Navigate to="/profile" replace />} />
      </Routes>
    </Suspense>
  );
}
