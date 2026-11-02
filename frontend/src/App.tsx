import { Routes, Route } from "react-router-dom";
import LandingPage   from "./pages/LandingPage";
import Dashboard     from "./pages/Dashboard";
import Discovery     from "./pages/Discovery";
import Graphs        from "./pages/Graphs";
import Agent         from "./pages/Agent";
import Analysis      from "./pages/Analysis";
import RunDetailPage from "./pages/RunDetailPage";
import TargetGraphPage from "./pages/TargetGraphPage";
import DrugGraphPage from "./pages/DrugGraphPage";
import Library from "./pages/Library";
import CompoundProfile from "./pages/CompoundProfile";

export default function App() {
  return (
    <Routes>
      <Route path="/"            element={<LandingPage />} />
      <Route path="/dashboard"   element={<Dashboard />} />
      <Route path="/discovery"   element={<Discovery />} />
      <Route path="/graphs"      element={<Graphs />} />
      <Route path="/agent"       element={<Agent />} />
      <Route path="/analysis"    element={<Analysis />} />
      <Route path="/library"     element={<Library />} />
      <Route path="/library/:compoundId" element={<CompoundProfile />} />
      <Route path="/runs/:runId" element={<RunDetailPage />} />
      <Route path="/graph/target/:targetId" element={<TargetGraphPage />} />
      <Route path="/graph/drug/:drugName"   element={<DrugGraphPage />} />
    </Routes>
  );
}