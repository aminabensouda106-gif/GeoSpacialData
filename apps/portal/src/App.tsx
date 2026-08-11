import { Routes, Route, Link, useLocation } from "react-router-dom";
import Discovery from "./pages/Discovery";
import DatasetPage from "./pages/DatasetPage";
import Workbench from "./pages/Workbench";
import Dashboard from "./pages/Dashboard";

function NavBar() {
  const { pathname } = useLocation();
  return (
    <nav style={{
      display: "flex",
      alignItems: "center",
      gap: 24,
      padding: "0 24px",
      height: 56,
      background: "var(--color-surface)",
      borderBottom: "1px solid var(--color-border)",
      boxShadow: "var(--shadow)",
    }}>
      <Link to="/" style={{ fontWeight: 700, fontSize: 18, color: "var(--color-primary)" }}>
        GeoData
      </Link>
      <Link to="/" style={{
        fontWeight: pathname === "/" ? 600 : 400,
        color: pathname === "/" ? "var(--color-primary)" : "var(--color-text-secondary)",
      }}>
        Discovery
      </Link>
      <Link to="/workbench" style={{
        fontWeight: pathname.startsWith("/workbench") ? 600 : 400,
        color: pathname.startsWith("/workbench") ? "var(--color-primary)" : "var(--color-text-secondary)",
      }}>
        Workbench
      </Link>
      <Link to="/dashboard" style={{
        fontWeight: pathname === "/dashboard" ? 600 : 400,
        color: pathname === "/dashboard" ? "var(--color-primary)" : "var(--color-text-secondary)",
      }}>
        Dashboard
      </Link>
    </nav>
  );
}

export default function App() {
  return (
    <>
      <NavBar />
      <main style={{ padding: 24, maxWidth: 1400, margin: "0 auto" }}>
        <Routes>
          <Route path="/" element={<Discovery />} />
          <Route path="/datasets/:id" element={<DatasetPage />} />
          <Route path="/workbench" element={<Workbench />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </main>
    </>
  );
}
