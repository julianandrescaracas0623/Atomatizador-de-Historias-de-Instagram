import type { ReactNode } from "react";
import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { AppLayout } from "./AppLayout";
import { getToken } from "./api";
import { HistoryPage } from "./HistoryPage";
import { LoginPage } from "./LoginPage";
import { QueuePage } from "./QueuePage";
import { StoryProvider } from "./StoryProvider";

function RequireAuth({ children }: { children: ReactNode }) {
  if (!getToken()) return <Navigate to="/login" replace />;
  return children;
}

function AuthedShell() {
  return (
    <RequireAuth>
      <StoryProvider>
        <AppLayout>
          <Outlet />
        </AppLayout>
      </StoryProvider>
    </RequireAuth>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<AuthedShell />}>
        <Route path="/" element={<QueuePage />} />
        <Route path="/historial" element={<HistoryPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
