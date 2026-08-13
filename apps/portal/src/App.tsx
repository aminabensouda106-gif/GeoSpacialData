import { useState } from "react";
import { Routes, Route, Link, useLocation } from "react-router-dom";
import Discovery from "./pages/Discovery";
import DatasetPage from "./pages/DatasetPage";
import Workbench from "./pages/Workbench";
import Dashboard from "./pages/Dashboard";
import { geocode } from "./api";
import { emitFlyTo } from "./locationBus";

function IconSearch() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
      <circle cx="11" cy="11" r="7" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function IconLayers() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polygon points="12 2 2 7 12 12 22 7 12 2" />
      <polyline points="2 17 12 22 22 17" />
      <polyline points="2 12 12 17 22 12" />
    </svg>
  );
}

function IconTable() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <line x1="3" y1="9" x2="21" y2="9" />
      <line x1="3" y1="15" x2="21" y2="15" />
      <line x1="9" y1="3" x2="9" y2="21" />
    </svg>
  );
}

function IconChart() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  );
}

function IconSurveyMark() {
  // A crosshair/benchmark mark — the symbol survey sheets use to pin a
  // reference point — rather than a generic globe or gradient blob.
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#eef0e6" strokeWidth="1.6">
      <circle cx="12" cy="12" r="3.2" />
      <line x1="12" y1="1.5" x2="12" y2="7" />
      <line x1="12" y1="17" x2="12" y2="22.5" />
      <line x1="1.5" y1="12" x2="7" y2="12" />
      <line x1="17" y1="12" x2="22.5" y2="12" />
    </svg>
  );
}

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
    <div style={{ position: "relative" }}>
      <div className="topbar-search">
        <IconSearch />
        <input
          type="text"
          placeholder="Rechercher un lieu..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSearch();
          }}
        />
        {loading && <div className="spinner" style={{ width: 12, height: 12 }} />}
      </div>
      {error && (
        <span style={{
          position: "absolute", top: "calc(100% + 6px)", right: 0, fontSize: 11.5,
          color: "#fca5b1", whiteSpace: "nowrap",
        }}>
          {error}
        </span>
      )}
    </div>
  );
}

function NavBar() {
  const { pathname } = useLocation();
  const links = [
    { to: "/", label: "Discovery", match: (p: string) => p === "/" || p.startsWith("/datasets"), icon: <IconLayers /> },
    { to: "/workbench", label: "Workbench", match: (p: string) => p.startsWith("/workbench"), icon: <IconTable /> },
    { to: "/dashboard", label: "Dashboard", match: (p: string) => p === "/dashboard", icon: <IconChart /> },
  ];

  return (
    <header className="topbar">
      <Link to="/" className="topbar-brand">
        <span className="topbar-brand-mark">
          <IconSurveyMark />
        </span>
        <span>
          GeoData Platform
          <span className="topbar-brand-sub">Commune Field Survey</span>
        </span>
      </Link>

      <nav className="topbar-nav">
        {links.map((l) => (
          <Link key={l.to} to={l.to} className={"topbar-link" + (l.match(pathname) ? " active" : "")}>
            {l.icon}
            <span className="link-label">{l.label}</span>
          </Link>
        ))}
      </nav>

      <div className="topbar-spacer" />
      <LocationSearch />
    </header>
  );
}

function Footer() {
  return (
    <footer className="footer">
      <span>GeoData Platform &mdash; unified access to satellite, field &amp; sensor data.</span>
      <div className="footer-links">
        <a href="#">Documentation</a>
        <a href="#">API</a>
        <a href="#">Status</a>
      </div>
    </footer>
  );
}

export default function App() {
  return (
    <div className="app-shell">
      <NavBar />
      <Routes>
        <Route path="/" element={<Discovery />} />
        <Route path="/datasets/:id" element={<PageWrap><DatasetPage /></PageWrap>} />
        <Route path="/workbench" element={<PageWrap wide><Workbench /></PageWrap>} />
        <Route path="/dashboard" element={<PageWrap><Dashboard /></PageWrap>} />
      </Routes>
      <Footer />
    </div>
  );
}

function PageWrap({ children, wide }: { children: React.ReactNode; wide?: boolean }) {
  return <main className={"page-container" + (wide ? " page-container--full" : "")}>{children}</main>;
}
