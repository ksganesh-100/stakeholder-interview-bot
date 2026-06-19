import { Routes, Route, Navigate } from "react-router-dom";
import Landing from "./pages/Landing.jsx";
import Admin from "./pages/Admin.jsx";
import ProjectDetail from "./pages/ProjectDetail.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/p/:publicId" element={<Landing />} />
      <Route path="/admin" element={<Admin />} />
      <Route path="/admin/p/:publicId" element={<ProjectDetail />} />
      <Route path="*" element={<Navigate to="/admin" replace />} />
    </Routes>
  );
}
