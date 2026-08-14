import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getDataset, getLineage, type Dataset, type LineageRun } from "../api";

function IconBack() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="15 18 9 12 15 6" />
    </svg>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 28 }}>
      <h2 style={{ fontSize: 13, fontWeight: 700, marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--color-text-muted)" }}>
        {title}
      </h2>
      {children}
    </div>
  );
}

function ProvenanceGrid({ ds }: { ds: Dataset }) {
  const rows: [string, string | null][] = [
    ["Classe de source", ds.source_class],
    ["Propriétaire", ds.owner],
    ["Licence", ds.license],
    ["Classification", ds.classification],
  ].filter((r) => r[1]) as [string, string][];

  if (rows.length === 0) return <p style={{ fontSize: 13.5, color: "var(--color-text-secondary)" }}>Aucune information de provenance disponible.</p>;

  return (
    <dl style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 16 }}>
      {rows.map(([label, value]) => (
        <div key={label}>
          <dt style={{ fontSize: 11, color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.03em", marginBottom: 2 }}>{label}</dt>
          <dd style={{ fontSize: 13.5, fontWeight: 500 }}>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function LineageTable({ runs }: { runs: LineageRun[] }) {
  if (runs.length === 0) {
    return <p style={{ fontSize: 13.5, color: "var(--color-text-secondary)" }}>Aucune exécution de pipeline enregistrée pour le moment.</p>;
  }
  return (
    <div className="card" style={{ overflowX: "auto" }}>
      <table className="data-table">
        <thead>
          <tr>
            <th>Run ID</th>
            <th>Statut</th>
            <th>Démarré</th>
            <th>Terminé</th>
            <th style={{ textAlign: "right" }}>Lignes</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((r) => (
            <tr key={r.run_id}>
              <td style={{ fontFamily: "var(--font-mono)" }}>{r.run_id?.slice(0, 8)}</td>
              <td>
                <span className="badge" style={{ background: r.status === "SUCCESS" ? "var(--color-success)" : "var(--color-warning)" }}>
                  {r.status}
                </span>
              </td>
              <td>{r.started_at}</td>
              <td>{r.finished_at}</td>
              <td style={{ textAlign: "right" }}>{r.row_count?.toLocaleString()}</td>
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

  if (isLoading) return <div className="state-loading"><div className="spinner" /> Chargement du jeu de données…</div>;
  if (error || !ds) return <div className="empty-state">Jeu de données introuvable.</div>;

  return (
    <div>
      <Link to="/" style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 12.5, color: "var(--color-text-secondary)", fontWeight: 600, marginBottom: 16 }}>
        <IconBack /> Retour au catalogue
      </Link>

      <div style={{ display: "flex", gap: 24, alignItems: "flex-start", flexWrap: "wrap" }}>
        <div style={{ flex: 1, minWidth: 320 }}>
          <div className="card card-pad">
            <div style={{ marginBottom: 18, paddingBottom: 16, borderBottom: "1px solid var(--line)" }}>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.03em", marginBottom: 6 }}>
                {ds.id}
              </div>
              <h1 style={{ fontSize: 26, fontWeight: 700, marginBottom: 10 }}>{ds.title}</h1>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                <span className="tag">{ds.source_type.replace("_source", "")}</span>
                <span className="tag">{ds.modality}</span>
                {ds.format && <span className="tag">{ds.format}</span>}
              </div>
            </div>

            <Section title="Description">
              <p style={{ fontSize: 14, lineHeight: 1.65, color: "var(--color-text)" }}>{ds.description}</p>
            </Section>

            {ds.caveats && (
              <Section title="Limitations">
                <div className="banner banner-warning">{ds.caveats}</div>
              </Section>
            )}

            <Section title="Provenance">
              <ProvenanceGrid ds={ds} />
              {ds.citation && (
                <p style={{ fontSize: 12.5, color: "var(--color-text-secondary)", marginTop: 10 }}>
                  Citation : {ds.citation}
                </p>
              )}
            </Section>

            <Section title="Traçabilité (exécutions du pipeline)">
              <LineageTable runs={lineage} />
            </Section>
          </div>
        </div>

        <aside style={{ width: 280, flexShrink: 0, position: "sticky", top: 76 }}>
          <div className="card card-pad" style={{ marginBottom: 16 }}>
            <div className="section-title">Actions</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {ds.modality === "tabular" && (
                <Link to="/workbench?cube=commune_overview" style={{ textDecoration: "none" }}>
                  <button className="btn btn-primary" style={{ width: "100%" }}>Ouvrir dans le Workbench</button>
                </Link>
              )}
              <a
                href={`/terria/#start=${encodeURIComponent(JSON.stringify({ initSources: [{ workbench: [ds.id === "ndvi_composite" ? "ndvi_zonal_stats" : ds.id] }] }))}`}
                target="_blank"
                rel="noopener noreferrer"
                style={{ textDecoration: "none" }}
              >
                <button className="btn btn-accent" style={{ width: "100%" }}>Ouvrir sur la carte</button>
              </a>
            </div>
          </div>

          <div className="card card-pad">
            <div className="section-title">Détails</div>
            <dl style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div>
                <dt style={{ fontSize: 11, color: "var(--color-text-muted)", marginBottom: 2 }}>Type de source</dt>
                <dd style={{ fontSize: 13, fontWeight: 500 }}>{ds.source_type}</dd>
              </div>
              <div>
                <dt style={{ fontSize: 11, color: "var(--color-text-muted)", marginBottom: 2 }}>Modalité</dt>
                <dd style={{ fontSize: 13, fontWeight: 500 }}>{ds.modality}</dd>
              </div>
              {ds.stac_collection && (
                <div>
                  <dt style={{ fontSize: 11, color: "var(--color-text-muted)", marginBottom: 2 }}>Collection STAC</dt>
                  <dd style={{ fontSize: 13, fontWeight: 500 }}>{ds.stac_collection}</dd>
                </div>
              )}
              <div>
                <dt style={{ fontSize: 11, color: "var(--color-text-muted)", marginBottom: 2 }}>Contrôles qualité</dt>
                <dd style={{ fontSize: 13, fontWeight: 500 }}>{ds.quality_checks?.length ?? 0}</dd>
              </div>
            </dl>
          </div>
        </aside>
      </div>
    </div>
  );
}
