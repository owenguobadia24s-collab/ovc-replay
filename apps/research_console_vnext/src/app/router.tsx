import { Navigate, createBrowserRouter } from "react-router-dom";
import { AppShell } from "./AppShell";
import { WorkbenchFrame } from "../researchNative/WorkbenchFrame";
export const router=createBrowserRouter([{path:"/",element:<AppShell/>,children:[{index:true,element:<Navigate to="/market" replace/>},{path:"market",element:<WorkbenchFrame/>},{path:"structure",element:<WorkbenchFrame/>},{path:"research",element:<WorkbenchFrame/>},{path:"evidence",element:<WorkbenchFrame/>},{path:"control",element:<WorkbenchFrame/>}]}]);
