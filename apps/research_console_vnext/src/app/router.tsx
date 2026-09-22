import { Navigate, createBrowserRouter } from "react-router-dom";
import { AppShell } from "./AppShell";
import { WorkspaceFrame } from "../workspace/WorkspaceFrame";
import { ProductionConsole } from "../production/ProductionConsole";
import { RepresentationWorkbench } from "../production/RepresentationWorkbench";
import { DMRPWorkbench } from "../production/DMRPWorkbench";
import "../production/productionResponsive.css";
import "../production/productionResponsiveSemantics.css";
import "../production/productionResponsivePolish.css";

export const router=createBrowserRouter([
  {path:"/",element:<Navigate to="/structure" replace/>},
  {path:"/market",element:<AppShell/>,children:[{index:true,element:<WorkspaceFrame/>}]},
  {path:"/structure",element:<ProductionConsole/>},
  {path:"/research",element:<ProductionConsole/>},
  {path:"/research/representations",element:<RepresentationWorkbench/>},
  {path:"/research/dmrp",element:<DMRPWorkbench/>},
  {path:"/evidence",element:<ProductionConsole/>},
  {path:"/control",element:<ProductionConsole/>},
]);