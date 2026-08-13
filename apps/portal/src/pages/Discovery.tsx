import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { searchDatasets, getAllDatasets, nearbyDatasets, type Dataset } from "../api";

const SOURCE_TYPES = [
  { id: "api", label: "API" },
  { id: "file", label: "Fichier" },
  { id: "gee", label: "Google Earth Engine" },
];
const MODALITIES = [
  { id: "tabular", label: "Tabulaire" },
  { id: "vector", label: "Vecteur" },
  { id: "raster", label: "Raster" },
];

function IconSearch() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
      <circle cx="11" cy="11" r="7" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function IconPin() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
      <path d="M21 10c0 7-9 12-9 12s-9-5-9-12a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  );
}

function IconEmpty() {
  return (
    <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="11" cy="11" r="7" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

const MODALITY_ICON: Record<string, React.ReactNode> = {
  tabular: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <line x1="3" y1="9" x2="21" y2="9" />
      <line x1="3" y1="15" x2="21" y2="15" />
      <line x1="9" y1="3" x2="9" y2="21" />
    </svg>
  ),
  vector: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polygon points="12 3 21 9 18 20 6 20 3 9" />
    </svg>
  ),
  raster: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="3" width="7" height="7" />
      <rect x="14" y="3" width="7" height="7" />
      <rect x="3" y="14" width="7" height="7" />
      <rect x="14" y="14" width="7" height="7" />
    </svg>
  ),
};

function TrustBadge({ ds }: { ds: Dataset }) {
  const checks = ds.quality_checks?.length ?? 0;
  const hasGov = ds.owner && ds.license;
  let level: "gold" | "silver" | "bronze" = "bronze";
  if (checks >= 2 && hasGov) level = "gold";
  else if (checks >= 1 || hasGov) level = "silver";

  const colors = {
    gold: "var(--color-badge-gold)",
    silver: "var(--color-badge-silver)",
    bronze: "var(--color-badge-bronze)",
  };
  const titles = { gold: "Or — vérifié & documenté", silver: "Argent — partiellement vérifié", bronze: "Bronze — non vérifié" };

  return (
    <span className="badge" style={{ background: colors[level] }} title={titles[level]}>
      {level}
    </span>
  );
}

function DatasetCard({ ds }: { ds: Dataset }) {
  return (
    <Link to={`/datasets/${ds.id}`} style={{ textDecoration: "none", color: "inherit" }}>
      <div className="card card-hover card-pad" style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 10, marginBottom: 10 }}>
          <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
            <div style={{
              width: 32, height: 32, borderRadius: 8, background: "var(--color-primary-soft)",
              color: "var(--color-primary)", display: "flex", alignItems: "center", justifyContent: "center",
              flexShrink: 0, marginTop: 1,
            }}>
              {MODALITY_ICON[ds.modality] ?? MODALITY_ICON.tabular}
            </div>
            <h3 style={{ fontSize: 15, fontWeight: 700, lineHeight: 1.3 }}>{ds.title}</h3>
          </div>
          <TrustBadge ds={ds} />
        </div>
        <p style={{ fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 14, lineHeight: 1.5, flex: 1 }}>
          {ds.description?.slice(0, 150)}{ds.description?.length > 150 ? "…" : ""}
        </p>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          <span className="tag">{ds.source_type.replace("_source", "")}</span>
          <span className="tag">{ds.modality}</span>
          {ds.format && <span className="tag">{ds.format}</span>}
        </div>
      </div>
    </Link>
  );
}

function FilterSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 22 }}>
      <div className="section-title">{title}</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>{children}</div>
    </div>
  );
}

function FilterOption({ label, count, active, onClick }: { label: string; count?: number; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "6px 8px", borderRadius: "var(--radius-sm)", border: "none",
        background: active ? "var(--color-primary-soft)" : "transparent",
        color: active ? "var(--color-primary)" : "var(--color-text-secondary)",
        fontSize: 13, fontWeight: active ? 600 : 500, textAlign: "left", width: "100%",
      }}
    >
      <span>{label}</span>
      {count !== undefined && <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>{count}</span>}
    </button>
  );
}

export default function Discovery() {
  const [query, setQuery] = useState("");
  const [sourceFilter, setSourceFilter] = useState<string | null>(null);
  const [modalityFilter, setModalityFilter] = useState<string | null>(null);
  const [nearMe, setNearMe] = useState(false);
  const [geoError, setGeoError] = useState<string | null>(null);

  const { data: datasets = [], isLoading } = useQuery({
    queryKey: ["datasets", query],
    queryFn: () => (query.trim() ? searchDatasets(query) : getAllDatasets()),
  });

  const { data: nearbyIds, error: nearbyError } = useQuery({
    queryKey: ["nearby", nearMe],
    queryFn: async () => {
      const pos = await new Promise<GeolocationPosition>((resolve, reject) =>
        navigator.geolocation.getCurrentPosition(resolve, reject, { enableHighAccuracy: true })
      );
      const results = await nearbyDatasets(pos.coords.latitude, pos.coords.longitude);
      return new Set(results.map((r) => r.id));
    },
    enabled: nearMe,
    retry: false,
  });

  const nearMeError = geoError ?? (nearbyError ? "Impossible d'obtenir votre position. Vérifiez les autorisations de localisation." : null);

  function toggleNearMe() {
    if (nearMe) {
      setNearMe(false);
      setGeoError(null);
      return;
    }
    if (!("geolocation" in navigator)) {
      setGeoError("La géolocalisation n'est pas disponible dans ce navigateur.");
      return;
    }
    setGeoError(null);
    setNearMe(true);
  }

  const filtered = datasets.filter((ds) => {
    // ds.source_type holds the full connector-type string ("file_source",
    // "gee_source", "api_source"); the filter chips use the short form.
    if (sourceFilter && ds.source_type !== `${sourceFilter}_source`) return false;
    if (modalityFilter && ds.modality !== modalityFilter) return false;
    if (nearMe && nearbyIds && !nearbyIds.has(ds.id)) return false;
    return true;
  });

  const sourceCounts = Object.fromEntries(
    SOURCE_TYPES.map((t) => [t.id, datasets.filter((d) => d.source_type === `${t.id}_source`).length])
  );
  const modalityCounts = Object.fromEntries(
    MODALITIES.map((m) => [m.id, datasets.filter((d) => d.modality === m.id).length])
  );

  return (
    <div>
      <div className="hero">
        <div className="hero-inner">
          <div className="hero-eyebrow">Catalogue de données géospatiales</div>
          <h1>Explorez toutes les données du territoire</h1>
          <p>
            Imagerie satellite, indicateurs climatiques, sols, cultures et données de terrain — recherchez,
            comparez et ouvrez n'importe quel jeu de données directement dans le Workbench ou la carte.
          </p>
          <div className="hero-search">
            <IconSearch />
            <input
              type="text"
              placeholder="Rechercher un jeu de données (ex : NDVI, précipitations, sols)…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button className="btn btn-accent" style={{ margin: 2 }}>Rechercher</button>
          </div>
          <div className="hero-stats">
            <div>
              <div className="hero-stat-value">{datasets.length}</div>
              <div className="hero-stat-label">Jeux de données</div>
            </div>
            <div>
              <div className="hero-stat-value">{SOURCE_TYPES.length}</div>
              <div className="hero-stat-label">Sources connectées</div>
            </div>
            <div>
              <div className="hero-stat-value">{MODALITIES.length}</div>
              <div className="hero-stat-label">Types de données</div>
            </div>
          </div>
        </div>
      </div>

      <div className="page-container" style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
        <aside className="card card-pad" style={{ width: 240, flexShrink: 0, position: "sticky", top: 76 }}>
          <FilterSection title="Source">
            <FilterOption label="Toutes les sources" count={datasets.length} active={sourceFilter === null} onClick={() => setSourceFilter(null)} />
            {SOURCE_TYPES.map((t) => (
              <FilterOption key={t.id} label={t.label} count={sourceCounts[t.id]} active={sourceFilter === t.id} onClick={() => setSourceFilter(t.id)} />
            ))}
          </FilterSection>

          <FilterSection title="Type de données">
            <FilterOption label="Tous les types" count={datasets.length} active={modalityFilter === null} onClick={() => setModalityFilter(null)} />
            {MODALITIES.map((m) => (
              <FilterOption key={m.id} label={m.label} count={modalityCounts[m.id]} active={modalityFilter === m.id} onClick={() => setModalityFilter(m.id)} />
            ))}
          </FilterSection>

          <FilterSection title="Localisation">
            <button
              onClick={toggleNearMe}
              className={"chip" + (nearMe ? " active" : "")}
              style={{ display: "inline-flex", alignItems: "center", gap: 6, width: "fit-content" }}
            >
              <IconPin /> Près de moi
            </button>
            {nearMeError && <p className="banner banner-danger" style={{ marginTop: 8 }}>{nearMeError}</p>}
          </FilterSection>
        </aside>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <span style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
              {isLoading ? "Recherche…" : `${filtered.length} résultat${filtered.length !== 1 ? "s" : ""}`}
            </span>
          </div>

          {isLoading ? (
            <div className="state-loading"><div className="spinner" /> Chargement du catalogue…</div>
          ) : filtered.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon" style={{ display: "flex", justifyContent: "center" }}><IconEmpty /></div>
              <p style={{ fontWeight: 600, marginBottom: 4 }}>Aucun jeu de données trouvé</p>
              <p style={{ fontSize: 13 }}>Essayez d'ajuster votre recherche ou vos filtres.</p>
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 16 }}>
              {filtered.map((ds) => (
                <DatasetCard key={ds.id} ds={ds} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
