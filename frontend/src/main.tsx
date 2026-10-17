import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import "./index.css";
import Layout from "./components/Layout";
import { ToastProvider } from "./components/Toast";
import { PassportProvider } from "./lib/store";
import Dashboard from "./pages/Dashboard";
import Analyze from "./pages/Analyze";
import PassportPage from "./pages/PassportPage";
import Trust from "./pages/Trust";
import JobMatchPage from "./pages/JobMatchPage";
import RoadmapPage from "./pages/RoadmapPage";
import SharePage from "./pages/SharePage";
import PublicPassportPage from "./pages/PublicPassportPage";
import NotFound from "./pages/NotFound";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ToastProvider>
      <PassportProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/p/:publicId" element={<PublicPassportPage />} />
            <Route element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route path="analyze" element={<Analyze />} />
              <Route path="passport" element={<PassportPage />} />
              <Route path="trust" element={<Trust />} />
              <Route path="job-match" element={<JobMatchPage />} />
              <Route path="roadmap" element={<RoadmapPage />} />
              <Route path="share" element={<SharePage />} />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </PassportProvider>
    </ToastProvider>
  </React.StrictMode>,
);
