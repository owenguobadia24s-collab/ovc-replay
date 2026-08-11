import { Navigate, createBrowserRouter } from "react-router-dom";
import { AppShell } from "./AppShell";
import { WorkspaceFrame } from "../workspace/WorkspaceFrame";
import { ProductionConsole } from "../production/ProductionConsole";
import "../production/productionResponsive.css";
import "../production/productionResponsiveSemantics.css";
import "../production/productionResponsivePolish.css";

export const router=createBrowserRouter([
  {path:"/",element:<Navigate to="/structure" replace/>},
  {path:"/market",element:<AppShell/>,children:[{index:true,element:<WorkspaceFrame/>}]},
  {path:"/structure",element:<ProductionConsole/>},
  {path:"/research",element:<ProductionConsole/>},
  {path:"/evidence",element:<ProductionConsole/>},
  {path:"/control",element:<ProductionConsole/>},
]);
