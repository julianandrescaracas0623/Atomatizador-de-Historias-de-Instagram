import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { AppThemeProvider } from "@/components/AppThemeProvider";
import { Toaster } from "@/components/ui/sonner";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AppThemeProvider>
      <BrowserRouter>
        <App />
        <Toaster position="bottom-center" richColors closeButton />
      </BrowserRouter>
    </AppThemeProvider>
  </StrictMode>,
);
