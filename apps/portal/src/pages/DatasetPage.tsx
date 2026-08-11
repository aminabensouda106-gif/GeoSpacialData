import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getDataset, getLineage, type Dataset, type LineageRun } from "../api";

function Badge({ label, color }: { label: string; color: string }) {
  return (
    <span style={{
      display: "inline-block",
      padding: "2px 10px",
      borderRadius: 12,
      fontSize: 12,
      fontWeight: 600,
      background: color,
      color: "#fff",
    }}>
      {label}
    </span>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 24 }}>
      <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: "var(--color-text)" }}>{title}</h2>
      {children}
    </div>
  );
}

function ProvenanceSentence({ ds }: { ds: Dataset }) {
  const parts: string[] = [];
  if (ds.source_class) parts.push(`Source class: ${ds.source_class}`);
  if (ds.owner) parts.push(`owned by ${ds.owner}`);
  if (ds.license) parts.push(`licensed under ${ds.license}`);
  if (ds.classification) parts.push(`classification: ${ds.classification}`);
  if (parts.length === 0) return null;
  return <p style={{ fontSize: 14, color: "var(--color-text-secondary)" }}>{parts.join(" | ")}</p>;
}

function LineageTable({ runs }: { runs: LineageRun[] }) {
  if (runs.length === 0) {
    return <p style={{ fontSize: 14, color: "var(--color-text-secondary)" }}>No pipeline runs recorded yet.</p>;
  }
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: "2px solid var(--color-border)" }}>
            <th style={{ textAlign: "left", padding: "6px 8px" }}>Run ID</th>
            <th style={{ textAlign: "left", padding: "6px 8px" }}>Status</th>
            <th style={{ textAlign: "left", padding: "6px 8px" }}>Started</th>
            <th style={{ textAlign: "left", padding: "6px 8px" }}>Finished</th>
            <th style={{ textAlign: "right", padding: "6px 8px" }}>Rows</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((r) => (
            <tr key={r.run_id} style={{ borderBottom: "1px solid var(--color-border)" }}>
              <td style={{ padding: "6px 8px", fontFamily: "monospace" }}>{r.run_id?.slice(0, 8)}</td>
              <td style={{ padding: "6px 8px" }}>
                <Badge label={r.status} color={r.status === "SUCCESS" ? "var(--color-success)" : "var(--color-warning)"} />
              </td>
              <td style={{ padding: "6px 8px" }}>{r.started_at}</td>
              <td style={{ padding: "6px 8px" }}>{r.finished_at}</td>
              <td style={{ padding: "6px 8px", textAlign: "right" }}>{r.row_count?.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function DatasetPage() {
  const { id } = useParams<{ id: string }>();

  const { data: ds, isLoading, error } = useQuery({
    queryKey: ["dataset", id],
    queryFn: () => getDataset(id!),
    enabled: !!id,
  });

  const { data: lineage = [] } = useQuery({
    queryKey: ["lineage", id],
    queryFn: () => getLineage(id!),
    enabled: !!id,
  });

  if (isLoading) return <p>Loading...</p>;
  if (error || !ds) return <p>Dataset not found.</p>;

  return (
    <div>
      <Link to="/" style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>Back to Discovery</Link>

      <div style={{
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius)",
        padding: 24,
        marginTop: 12,
        boxShadow: "var(--shadow)",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: 16 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700 }}>{ds.title}</h1>
          <div style={{ display: "flex", gap: 8 }}>
            <Badge label={ds.source_type} color="#6366f1" />
            <Badge label={ds.modality} color="#0891b2" />
          </div>
        </div>

        <Section title="Description">
          <p style={{ fontSize: 14, lineHeight: 1.6 }}>{ds.description}</p>
        </Section>

        {ds.caveats && (
          <Section title="Limitations">
            <div style={{
              padding: 12,
              background: "#fef3c7",
              borderRadius: "var(--radius)",
              border: "1px solid #fcd34d",
              fontSize: 13,
              color: "#92400e",
            }}>
              {ds.caveats}
            </div>
          </Section>
        )}

        <Section title="Provenance">
          <ProvenanceSentence ds={ds} />
          {ds.citation && (
            <p style={{ fontSize: 13, color: "var(--color-text-secondary)", marginTop: 4 }}>
              Citation: {ds.citation}
            </p>
          )}
        </Section>

        <Section title="Lineage (Pipeline Runs)">
          <LineageTable runs={lineage} />
        </Section>

        <div style={{ display: "flex", gap: 12, marginTop: 16 }}>
          {ds.modality === "tabular" && (
            <Link to={`/workbench?cube=commune_overview`}>
              <button style={{
                padding: "8px 16px",
                borderRadius: "var(--radius)",
                background: "var(--color-primary)",
                color: "#fff",
                border: "none",
                fontSize: 14,
                fontWeight: 500,
              }}>
                Open in Workbench
              </button>
            </Link>
          )}
          <a
            href={`http://localhost:3001/#start=${encodeURIComponent(JSON.stringify({ initSources: [{ workbench: [ds.id] }] }))}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            <button style={{
              padding: "8px 16px",
              borderRadius: "var(--radius)",
              background: "#059669",
              color: "#fff",
              border: "none",
              fontSize: 14,
              fontWeight: 500,
            }}>
              Open in Map
            </button>
          </a>
        </div>
      </div>
    </div>
  );
}
