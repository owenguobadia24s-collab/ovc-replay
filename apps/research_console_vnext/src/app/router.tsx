import { Navigate, createBrowserRouter } from "react-router-dom";
import { AppShell } from "./AppShell";
import { FoundationWorkspace } from "./FoundationWorkspace";
export const router = createBrowserRouter([{ path: "/", element: <AppShell />, children: [{ index: true, element: <Navigate to="/market" replace /> }, { path: "market", element: <FoundationWorkspace /> }, { path: "structure", element: <FoundationWorkspace /> }, { path: "research", element: <FoundationWorkspace /> }, { path: "evidence", element: <FoundationWorkspace /> }, { path: "control", element: <FoundationWorkspace /> }] }]);
