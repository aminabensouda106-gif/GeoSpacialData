import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { searchDatasets, getAllDatasets, type Dataset } from "../api";

const SOURCE_TYPES = ["api", "file", "gee"];
const MODALITIES = ["tabular", "vector", "raster"];

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

  return (
    <span style={{
      display: "inline-block",
      padding: "2px 8px",
      borderRadius: 12,
      fontSize: 12,
      fontWeight: 600,
      color: "#fff",
      background: colors[level],
    }}>
      {level}
    </span>
  );
}

function DatasetCard({ ds }: { ds: Dataset }) {
  return (
    <Link to={`/datasets/${ds.id}`} style={{ textDecoration: "none", color: "inherit" }}>
      <div style={{
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius)",
        padding: 16,
        boxShadow: "var(--shadow)",
        transition: "box-shadow 0.15s",
      }}
        onMouseEnter={(e) => e.currentTarget.style.boxShadow = "0 4px 12px rgba(0,0,0,0.12)"}
        onMouseLeave={(e) => e.currentTarget.style.boxShadow = "var(--shadow)"}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: 8 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>{ds.title}</h3>
          <TrustBadge ds={ds} />
        </div>
        <p style={{ fontSize: 14, color: "var(--color-text-secondary)", marginBottom: 12, lineHeight: 1.4 }}>
          {ds.description?.slice(0, 160)}{ds.description?.length > 160 ? "..." : ""}
        </p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Tag label={ds.source_type} />
          <Tag label={ds.modality} />
          {ds.format && <Tag label={ds.format} />}
        </div>
      </div>
    </Link>
  );
}

function Tag({ label }: { label: string }) {
  return (
    <span style={{
      fontSize: 11,
      padding: "2px 8px",
      borderRadius: 4,
      background: "#e5e7eb",
      color: "#374151",
      fontWeight: 500,
    }}>
      {label}
    </span>
  );
}

export default function Discovery() {
  const [query, setQuery] = useState("");
  const [sourceFilter, setSourceFilter] = useState<string | null>(null);
  const [modalityFilter, setModalityFilter] = useState<string | null>(null);

  const { data: datasets = [], isLoading } = useQuery({
    queryKey: ["datasets", query],
    queryFn: () => (query.trim() ? searchDatasets(query) : getAllDatasets()),
  });

  const filtered = datasets.filter((ds) => {
    if (sourceFilter && ds.source_type !== sourceFilter) return false;
    if (modalityFilter && ds.modality !== modalityFilter) return false;
    return true;
  });

  return (
    <div>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 16 }}>Discover Datasets</h1>

      <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
        <input
          type="text"
          placeholder="Search datasets..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{
            flex: 1,
            minWidth: 240,
            padding: "8px 14px",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius)",
            fontSize: 14,
            outline: "none",
          }}
        />
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 20, flexWrap: "wrap" }}>
        <span style={{ fontSize: 13, color: "var(--color-text-secondary)", paddingTop: 4 }}>Source:</span>
        <FilterChip label="All" active={sourceFilter === null} onClick={() => setSourceFilter(null)} />
        {SOURCE_TYPES.map((t) => (
          <FilterChip key={t} label={t} active={sourceFilter === t} onClick={() => setSourceFilter(t)} />
        ))}

        <span style={{ fontSize: 13, color: "var(--color-text-secondary)", paddingTop: 4, marginLeft: 12 }}>Type:</span>
        <FilterChip label="All" active={modalityFilter === null} onClick={() => setModalityFilter(null)} />
        {MODALITIES.map((m) => (
          <FilterChip key={m} label={m} active={modalityFilter === m} onClick={() => setModalityFilter(m)} />
        ))}
      </div>

      {isLoading ? (
        <p style={{ color: "var(--color-text-secondary)" }}>Loading...</p>
      ) : filtered.length === 0 ? (
        <p style={{ color: "var(--color-text-secondary)" }}>No datasets found.</p>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: 16 }}>
          {filtered.map((ds) => (
            <DatasetCard key={ds.id} ds={ds} />
          ))}
        </div>
      )}
    </div>
  );
}

function FilterChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "4px 12px",
        borderRadius: 16,
        border: "1px solid",
        borderColor: active ? "var(--color-primary)" : "var(--color-border)",
        background: active ? "var(--color-primary)" : "transparent",
        color: active ? "#fff" : "var(--color-text-secondary)",
        fontSize: 13,
        fontWeight: 500,
        transition: "all 0.15s",
      }}
    >
      {label}
    </button>
  );
}
