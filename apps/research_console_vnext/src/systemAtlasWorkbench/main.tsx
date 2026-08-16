import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { AtlasWorkbench } from "./AtlasWorkbench";
import "./system-atlas-workbench.css";

createRoot(document.getElementById("root")!).render(<StrictMode><AtlasWorkbench /></StrictMode>);
