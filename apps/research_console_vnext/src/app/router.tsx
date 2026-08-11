import { Navigate, createBrowserRouter } from "react-router-dom";
import { AppShell } from "./AppShell";
import { WorkbenchFrame } from "../researchNative/WorkbenchFrame";
import { ProductionConsole } from "../production/ProductionConsole";
import "../production/productionResponsive.css";

export const router=createBrowserRouter([
  {path:"/",element:<Navigate to="/structure" replace/>},
  {path:"/market",element:<AppShell/>,children:[{index:true,element:<WorkbenchFrame/>}]},
  {path:"/structure",element:<ProductionConsole/>},
  {path:"/research",element:<ProductionConsole/>},
  {path:"/evidence",element:<ProductionConsole/>},
  {path:"/control",element:<ProductionConsole/>},
]);
