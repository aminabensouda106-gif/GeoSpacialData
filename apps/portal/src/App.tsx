import { useState } from "react";
import { Routes, Route, Link, useLocation } from "react-router-dom";
import Discovery from "./pages/Discovery";
import DatasetPage from "./pages/DatasetPage";
import Workbench from "./pages/Workbench";
import Dashboard from "./pages/Dashboard";
import { geocode } from "./api";
import { emitFlyTo } from "./locationBus";

function LocationSearch() {
  const [q, setQ] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSearch() {
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await geocode(q);
      emitFlyTo({ lat: result.lat, lon: result.lon, label: result.display_name });
    } catch {
      setError("Lieu introuvable.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, marginLeft: "auto" }}>
      <input
        type="text"
        placeholder="Rechercher un lieu..."
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") handleSearch();
        }}
        style={{
          padding: "6px 10px",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius)",
          fontSize: 13,
          outline: "none",
          width: 200,
        }}
      />
      {error && <span style={{ fontSize: 12, color: "#dc2626" }}>{error}</span>}
      {loading && <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>...</span>}
    </div>
  );
}

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
      <LocationSearch />
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
