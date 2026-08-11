import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { cubeExport } from "../api";

interface Row {
  "commune_overview.commune_code": string;
  "commune_overview.period": string;
  "commune_overview.mean_ndvi": string;
}

function useDashboardData() {
  return useQuery({
    queryKey: ["dashboard-ndvi"],
    queryFn: () =>
      cubeExport({
        measures: ["commune_overview.mean_ndvi"],
        dimensions: ["commune_overview.commune_code", "commune_overview.period"],
      }),
  });
}

function KpiCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{
      flex: 1,
      minWidth: 160,
      background: "var(--color-surface)",
      border: "1px solid var(--color-border)",
      borderRadius: "var(--radius)",
      padding: "20px 24px",
      boxShadow: "var(--shadow)",
    }}>
      <div style={{ fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color }}>{value}</div>
    </div>
  );
}

function ndviColor(v: number): string {
  if (v < 0.3) return "#d73027";
  if (v < 0.4) return "#fc8d59";
  if (v < 0.5) return "#fee08b";
  if (v < 0.6) return "#d9ef8b";
  if (v < 0.7) return "#66bd63";
  return "#1a9850";
}

function LineChart({ data }: { data: Row[] }) {
  const periods = [...new Set(data.map((r) => r["commune_overview.period"]))].sort();
  const communes = [...new Set(data.map((r) => r["commune_overview.commune_code"]))].sort();

  const byCommune = useMemo(() => {
    const m = new Map<string, Map<string, number>>();
    for (const r of data) {
      const cc = r["commune_overview.commune_code"];
      const p = r["commune_overview.period"];
      const v = parseFloat(r["commune_overview.mean_ndvi"]);
      if (!m.has(cc)) m.set(cc, new Map());
      m.get(cc)!.set(p, v);
    }
    return m;
  }, [data]);

  const W = 600, H = 300, PL = 50, PR = 20, PT = 20, PB = 40;
  const chartW = W - PL - PR;
  const chartH = H - PT - PB;

  const allVals = data.map((r) => parseFloat(r["commune_overview.mean_ndvi"]));
  const minV = Math.min(...allVals) - 0.05;
  const maxV = Math.max(...allVals) + 0.05;

  const xScale = (i: number) => PL + (i / (periods.length - 1)) * chartW;
  const yScale = (v: number) => PT + chartH - ((v - minV) / (maxV - minV)) * chartH;

  const colors = ["#2563eb", "#dc2626", "#059669", "#d97706", "#7c3aed", "#0891b2", "#be185d", "#65a30d", "#0d9488"];

  return (
    <div style={{
      background: "var(--color-surface)",
      border: "1px solid var(--color-border)",
      borderRadius: "var(--radius)",
      padding: 20,
      boxShadow: "var(--shadow)",
    }}>
      <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>NDVI moyen par commune et par mois</h3>
      <div style={{ overflowX: "auto" }}>
        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", maxWidth: W, height: "auto" }}>
          {[0, 0.25, 0.5, 0.75, 1].map((t) => {
            const v = minV + t * (maxV - minV);
            const y = yScale(v);
            return (
              <g key={t}>
                <line x1={PL} x2={W - PR} y1={y} y2={y} stroke="#e5e7eb" strokeWidth={1} />
                <text x={PL - 8} y={y + 4} textAnchor="end" fontSize={11} fill="#6b7280">{v.toFixed(2)}</text>
              </g>
            );
          })}

          {periods.map((p, i) => (
            <text key={p} x={xScale(i)} y={H - 8} textAnchor="middle" fontSize={11} fill="#6b7280">{p}</text>
          ))}

          {communes.map((cc, ci) => {
            const points = periods
              .map((p, i) => {
                const v = byCommune.get(cc)?.get(p);
                return v !== undefined ? `${xScale(i)},${yScale(v)}` : null;
              })
              .filter(Boolean)
              .join(" ");
            return (
              <g key={cc}>
                <polyline points={points} fill="none" stroke={colors[ci % colors.length]} strokeWidth={2} />
                {periods.map((p, i) => {
                  const v = byCommune.get(cc)?.get(p);
                  if (v === undefined) return null;
                  return <circle key={p} cx={xScale(i)} cy={yScale(v)} r={3} fill={colors[ci % colors.length]} />;
                })}
              </g>
            );
          })}
        </svg>
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 12 }}>
        {communes.map((cc, ci) => (
          <div key={cc} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12 }}>
            <div style={{ width: 12, height: 3, background: colors[ci % colors.length], borderRadius: 1 }} />
            <span style={{ color: "var(--color-text-secondary)" }}>{cc}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function BarChartByCommune({ data }: { data: Row[] }) {
  const periods = [...new Set(data.map((r) => r["commune_overview.period"]))].sort();
  const latestPeriod = periods[periods.length - 1];

  const latest = data
    .filter((r) => r["commune_overview.period"] === latestPeriod)
    .map((r) => ({
      commune: r["commune_overview.commune_code"],
      ndvi: parseFloat(r["commune_overview.mean_ndvi"]),
    }))
    .sort((a, b) => b.ndvi - a.ndvi);

  const W = 600, H = 260, PL = 70, PR = 50, PT = 10, PB = 30;
  const barH = Math.min(28, (H - PT - PB) / latest.length - 4);
  const totalH = PT + latest.length * (barH + 4) + PB;
  const chartW = W - PL - PR;
  const maxVal = Math.max(...latest.map((r) => r.ndvi), 0.01);

  return (
    <div style={{
      background: "var(--color-surface)",
      border: "1px solid var(--color-border)",
      borderRadius: "var(--radius)",
      padding: 20,
      boxShadow: "var(--shadow)",
    }}>
      <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>NDVI par commune — {latestPeriod}</h3>
      <p style={{ fontSize: 12, color: "var(--color-text-secondary)", marginBottom: 12 }}>Classement du dernier mois disponible</p>
      <svg viewBox={`0 0 ${W} ${totalH}`} style={{ width: "100%", maxWidth: W, height: "auto" }}>
        {latest.map((r, i) => {
          const y = PT + i * (barH + 4);
          const w = (r.ndvi / maxVal) * chartW;
          return (
            <g key={r.commune}>
              <text x={PL - 8} y={y + barH / 2 + 4} textAnchor="end" fontSize={12} fill="#374151">{r.commune}</text>
              <rect x={PL} y={y} width={w} height={barH} rx={3} fill={ndviColor(r.ndvi)} />
              <text x={PL + w + 6} y={y + barH / 2 + 4} fontSize={12} fill="#6b7280">{r.ndvi.toFixed(3)}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function HeatmapTable({ data }: { data: Row[] }) {
  const periods = [...new Set(data.map((r) => r["commune_overview.period"]))].sort();
  const communes = [...new Set(data.map((r) => r["commune_overview.commune_code"]))].sort();

  const lookup = useMemo(() => {
    const m = new Map<string, number>();
    for (const r of data) {
      m.set(`${r["commune_overview.commune_code"]}|${r["commune_overview.period"]}`, parseFloat(r["commune_overview.mean_ndvi"]));
    }
    return m;
  }, [data]);

  return (
    <div style={{
      background: "var(--color-surface)",
      border: "1px solid var(--color-border)",
      borderRadius: "var(--radius)",
      padding: 20,
      boxShadow: "var(--shadow)",
    }}>
      <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 12 }}>Matrice NDVI — Commune x Mois</h3>
      <div style={{ overflowX: "auto" }}>
        <table style={{ borderCollapse: "collapse", fontSize: 13, width: "100%" }}>
          <thead>
            <tr>
              <th style={{ padding: "8px 12px", textAlign: "left", borderBottom: "2px solid var(--color-border)", fontWeight: 600 }}>Commune</th>
              {periods.map((p) => (
                <th key={p} style={{ padding: "8px 12px", textAlign: "center", borderBottom: "2px solid var(--color-border)", fontWeight: 600 }}>{p}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {communes.map((cc) => (
              <tr key={cc} style={{ borderBottom: "1px solid var(--color-border)" }}>
                <td style={{ padding: "6px 12px", fontWeight: 500, fontFamily: "monospace" }}>{cc}</td>
                {periods.map((p) => {
                  const v = lookup.get(`${cc}|${p}`);
                  return (
                    <td key={p} style={{
                      padding: "6px 12px",
                      textAlign: "center",
                      background: v !== undefined ? ndviColor(v) + "33" : "transparent",
                      fontFamily: "monospace",
                    }}>
                      {v !== undefined ? (
                        <span style={{ color: ndviColor(v), fontWeight: 600 }}>{v.toFixed(3)}</span>
                      ) : "—"}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 12, fontSize: 12, color: "var(--color-text-secondary)" }}>
        <span>Echelle :</span>
        {[
          { label: "< 0.3", color: "#d73027" },
          { label: "0.3-0.5", color: "#fee08b" },
          { label: "0.5-0.7", color: "#66bd63" },
          { label: "> 0.7", color: "#1a9850" },
        ].map((s) => (
          <div key={s.label} style={{ display: "flex", alignItems: "center", gap: 3 }}>
            <div style={{ width: 14, height: 14, borderRadius: 2, background: s.color }} />
            <span>{s.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { data: result, isLoading, error } = useDashboardData();
  const rows = (result?.data ?? []) as unknown as Row[];

  const stats = useMemo(() => {
    if (rows.length === 0) return null;
    const values = rows.map((r) => parseFloat(r["commune_overview.mean_ndvi"]));
    const communes = new Set(rows.map((r) => r["commune_overview.commune_code"]));
    const periods = new Set(rows.map((r) => r["commune_overview.period"]));
    const avg = values.reduce((a, b) => a + b, 0) / values.length;
    return {
      avg,
      min: Math.min(...values),
      max: Math.max(...values),
      communeCount: communes.size,
      periodCount: periods.size,
    };
  }, [rows]);

  if (isLoading) return <p style={{ color: "var(--color-text-secondary)" }}>Chargement du dashboard...</p>;
  if (error) return <p style={{ color: "#dc2626" }}>Erreur de chargement des donnees.</p>;
  if (!stats) return <p style={{ color: "var(--color-text-secondary)" }}>Aucune donnee disponible.</p>;

  return (
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 20 }}>Dashboard NDVI</h1>

      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 24 }}>
        <KpiCard label="NDVI moyen global" value={stats.avg.toFixed(3)} color="#2563eb" />
        <KpiCard label="NDVI minimum" value={stats.min.toFixed(3)} color="#dc2626" />
        <KpiCard label="NDVI maximum" value={stats.max.toFixed(3)} color="#059669" />
        <KpiCard label="Communes" value={String(stats.communeCount)} color="#7c3aed" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 }}>
        <LineChart data={rows} />
        <BarChartByCommune data={rows} />
      </div>

      <HeatmapTable data={rows} />
    </div>
  );
}
