import { useMemo, useState, type CSSProperties } from "react";
import { useQuery } from "@tanstack/react-query";
import { cubeExport } from "../api";
import { downloadCsv } from "../csv";

type Row = Record<string, string>;

const TABS = [
  { id: "ndvi", label: "NDVI" },
  { id: "vegetation", label: "Indices de Végétation" },
  { id: "soil", label: "Sol" },
  { id: "climate", label: "Climat" },
  { id: "water", label: "Eau" },
  { id: "crops", label: "Cultures" },
] as const;

type TabId = (typeof TABS)[number]["id"];

function useCubeQuery(key: string, measures: string[], dimensions: string[]) {
  return useQuery({
    queryKey: ["dashboard", key],
    queryFn: () => cubeExport({ measures, dimensions }),
  });
}

function num(row: Row, key: string): number {
  return parseFloat(row[key] ?? "0");
}

function KpiCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="stat-block">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value" style={{ color }}>{value}</div>
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

const CARD_STYLE: CSSProperties = {
  background: "var(--color-surface)",
  border: "1px solid var(--color-border)",
  borderRadius: "var(--radius)",
  padding: 20,
  boxShadow: "var(--shadow)",
};

function LineChart({ data, communeKey, periodKey, valueKey, title }: {
  data: Row[]; communeKey: string; periodKey: string; valueKey: string; title: string;
}) {
  const periods = [...new Set(data.map((r) => r[periodKey]))].sort();
  const communes = [...new Set(data.map((r) => r[communeKey]))].sort();

  const byCommune = useMemo(() => {
    const m = new Map<string, Map<string, number>>();
    for (const r of data) {
      const cc = r[communeKey];
      const p = r[periodKey];
      const v = num(r, valueKey);
      if (!m.has(cc)) m.set(cc, new Map());
      m.get(cc)!.set(p, v);
    }
    return m;
  }, [data, communeKey, periodKey, valueKey]);

  const W = 600, H = 300, PL = 50, PR = 20, PT = 20, PB = 40;
  const chartW = W - PL - PR;
  const chartH = H - PT - PB;

  const allVals = data.map((r) => num(r, valueKey));
  const minV = allVals.length ? Math.min(...allVals) - 0.05 : 0;
  const maxV = allVals.length ? Math.max(...allVals) + 0.05 : 1;

  const xScale = (i: number) => PL + (i / Math.max(1, periods.length - 1)) * chartW;
  const yScale = (v: number) => PT + chartH - ((v - minV) / (maxV - minV || 1)) * chartH;

  const colors = ["#2563eb", "#dc2626", "#059669", "#d97706", "#7c3aed", "#0891b2", "#be185d", "#65a30d", "#0d9488"];

  return (
    <div style={CARD_STYLE}>
      <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>{title}</h3>
      <div style={{ overflowX: "auto" }}>
        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", maxWidth: W, height: "auto" }}>
          {[0, 0.25, 0.5, 0.75, 1].map((t) => {
            const v = minV + t * (maxV - minV);
            const y = yScale(v);
            return (
              <g key={t}>
                <line x1={PL} x2={W - PR} y1={y} y2={y} stroke="var(--line)" strokeWidth={1} />
                <text x={PL - 8} y={y + 4} textAnchor="end" fontSize={11} fill="var(--text-muted)">{v.toFixed(2)}</text>
              </g>
            );
          })}

          {periods.map((p, i) => (
            <text key={p} x={xScale(i)} y={H - 8} textAnchor="middle" fontSize={11} fill="var(--text-muted)">{p}</text>
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

function MultiMetricLineChart({ data, periodKey, metrics, title }: {
  data: Row[]; periodKey: string; metrics: { key: string; label: string; color: string }[]; title: string;
}) {
  const periods = [...new Set(data.map((r) => r[periodKey]))].sort();

  const avgByPeriod = useMemo(() => {
    const result = new Map<string, Map<string, number>>();
    for (const m of metrics) {
      const byPeriod = new Map<string, number[]>();
      for (const r of data) {
        const p = r[periodKey];
        const v = num(r, m.key);
        if (!byPeriod.has(p)) byPeriod.set(p, []);
        byPeriod.get(p)!.push(v);
      }
      const avgs = new Map<string, number>();
      for (const [p, vals] of byPeriod) avgs.set(p, vals.reduce((a, b) => a + b, 0) / vals.length);
      result.set(m.key, avgs);
    }
    return result;
  }, [data, periodKey, metrics]);

  const W = 600, H = 300, PL = 50, PR = 20, PT = 20, PB = 40;
  const chartW = W - PL - PR;
  const chartH = H - PT - PB;

  const allVals = metrics.flatMap((m) => [...(avgByPeriod.get(m.key)?.values() ?? [])]);
  const minV = allVals.length ? Math.min(...allVals, 0) - 0.05 : 0;
  const maxV = allVals.length ? Math.max(...allVals) + 0.05 : 1;

  const xScale = (i: number) => PL + (i / Math.max(1, periods.length - 1)) * chartW;
  const yScale = (v: number) => PT + chartH - ((v - minV) / (maxV - minV || 1)) * chartH;

  return (
    <div style={CARD_STYLE}>
      <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>{title}</h3>
      <div style={{ overflowX: "auto" }}>
        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", maxWidth: W, height: "auto" }}>
          {[0, 0.25, 0.5, 0.75, 1].map((t) => {
            const v = minV + t * (maxV - minV);
            const y = yScale(v);
            return (
              <g key={t}>
                <line x1={PL} x2={W - PR} y1={y} y2={y} stroke="var(--line)" strokeWidth={1} />
                <text x={PL - 8} y={y + 4} textAnchor="end" fontSize={11} fill="var(--text-muted)">{v.toFixed(2)}</text>
              </g>
            );
          })}
          {periods.map((p, i) => (
            <text key={p} x={xScale(i)} y={H - 8} textAnchor="middle" fontSize={11} fill="var(--text-muted)">{p}</text>
          ))}
          {metrics.map((m) => {
            const avgs = avgByPeriod.get(m.key)!;
            const points = periods
              .map((p, i) => (avgs.has(p) ? `${xScale(i)},${yScale(avgs.get(p)!)}` : null))
              .filter(Boolean)
              .join(" ");
            return (
              <g key={m.key}>
                <polyline points={points} fill="none" stroke={m.color} strokeWidth={2} />
                {periods.map((p, i) =>
                  avgs.has(p) ? <circle key={p} cx={xScale(i)} cy={yScale(avgs.get(p)!)} r={3} fill={m.color} /> : null
                )}
              </g>
            );
          })}
        </svg>
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 12 }}>
        {metrics.map((m) => (
          <div key={m.key} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12 }}>
            <div style={{ width: 12, height: 3, background: m.color, borderRadius: 1 }} />
            <span style={{ color: "var(--color-text-secondary)" }}>{m.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function BarChartByCommune({ data, communeKey, periodKey, valueKey, title, subtitle, colorFn, useLatestPeriod = true }: {
  data: Row[]; communeKey: string; periodKey?: string; valueKey: string; title: string; subtitle?: string;
  colorFn?: (v: number) => string; useLatestPeriod?: boolean;
}) {
  let latestPeriod: string | null = null;
  let latest: { commune: string; value: number }[];

  if (periodKey && useLatestPeriod) {
    const periods = [...new Set(data.map((r) => r[periodKey]))].sort();
    latestPeriod = periods[periods.length - 1] ?? null;
    latest = data
      .filter((r) => r[periodKey] === latestPeriod)
      .map((r) => ({ commune: r[communeKey], value: num(r, valueKey) }));
  } else if (periodKey) {
    // One row per (commune, period) in `data` — sum across periods per commune
    // rather than plotting every row as its own bar.
    const totals = new Map<string, number>();
    for (const r of data) totals.set(r[communeKey], (totals.get(r[communeKey]) ?? 0) + num(r, valueKey));
    latest = [...totals.entries()].map(([commune, value]) => ({ commune, value }));
  } else {
    latest = data.map((r) => ({ commune: r[communeKey], value: num(r, valueKey) }));
  }

  latest = latest.sort((a, b) => b.value - a.value);

  const W = 600, H = 260, PL = 70, PR = 50, PT = 10, PB = 30;
  const barH = latest.length ? Math.min(28, (H - PT - PB) / latest.length - 4) : 20;
  const totalH = PT + latest.length * (barH + 4) + PB;
  const chartW = W - PL - PR;
  const maxVal = Math.max(...latest.map((r) => r.value), 0.01);

  return (
    <div style={CARD_STYLE}>
      <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>
        {title}{latestPeriod ? ` — ${latestPeriod}` : ""}
      </h3>
      {subtitle && <p style={{ fontSize: 12, color: "var(--color-text-secondary)", marginBottom: 12 }}>{subtitle}</p>}
      <svg viewBox={`0 0 ${W} ${totalH}`} style={{ width: "100%", maxWidth: W, height: "auto" }}>
        {latest.map((r, i) => {
          const y = PT + i * (barH + 4);
          const w = (r.value / maxVal) * chartW;
          return (
            <g key={r.commune}>
              <text x={PL - 8} y={y + barH / 2 + 4} textAnchor="end" fontSize={12} fill="var(--text)">{r.commune}</text>
              <rect x={PL} y={y} width={w} height={barH} rx={3} fill={colorFn ? colorFn(r.value) : "var(--color-primary)"} />
              <text x={PL + w + 6} y={y + barH / 2 + 4} fontSize={12} fill="var(--text-muted)">{r.value.toFixed(1)}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function HeatmapTable({ data, communeKey, periodKey, valueKey, title, colorFn, decimals = 3 }: {
  data: Row[]; communeKey: string; periodKey: string; valueKey: string; title: string;
  colorFn: (v: number) => string; decimals?: number;
}) {
  const periods = [...new Set(data.map((r) => r[periodKey]))].sort();
  const communes = [...new Set(data.map((r) => r[communeKey]))].sort();

  const lookup = useMemo(() => {
    const m = new Map<string, number>();
    for (const r of data) m.set(`${r[communeKey]}|${r[periodKey]}`, num(r, valueKey));
    return m;
  }, [data, communeKey, periodKey, valueKey]);

  return (
    <div style={CARD_STYLE}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h3 style={{ fontSize: 15, fontWeight: 600 }}>{title}</h3>
        <button
          onClick={() =>
            downloadCsv(
              `${title}.csv`,
              ["Commune", ...periods],
              communes.map((cc) => [cc, ...periods.map((p) => lookup.get(`${cc}|${p}`)?.toFixed(decimals) ?? "")])
            )
          }
          className="btn btn-outline btn-sm"
        >
          Export CSV
        </button>
      </div>
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
                      background: v !== undefined ? colorFn(v) + "33" : "transparent",
                      fontFamily: "monospace",
                    }}>
                      {v !== undefined ? <span style={{ color: colorFn(v), fontWeight: 600 }}>{v.toFixed(decimals)}</span> : "—"}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RadarChart({ data, communeKey, axes, title }: {
  data: Row[]; communeKey: string; axes: { key: string; label: string; max: number }[]; title: string;
}) {
  const communes = [...new Set(data.map((r) => r[communeKey]))].sort();
  const colors = ["#2563eb", "#dc2626", "#059669", "#d97706", "#7c3aed", "#0891b2", "#be185d", "#65a30d", "#0d9488", "#4b5563"];

  const avgByCommune = useMemo(() => {
    const m = new Map<string, Map<string, number>>();
    for (const cc of communes) {
      const rows = data.filter((r) => r[communeKey] === cc);
      const axisAvgs = new Map<string, number>();
      for (const axis of axes) {
        const vals = rows.map((r) => num(r, axis.key));
        axisAvgs.set(axis.key, vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0);
      }
      m.set(cc, axisAvgs);
    }
    return m;
  }, [data, communes, communeKey, axes]);

  const size = 320, center = size / 2, radius = size / 2 - 50;
  const angleFor = (i: number) => (i / axes.length) * 2 * Math.PI - Math.PI / 2;
  const pointFor = (i: number, ratio: number) => {
    const a = angleFor(i);
    const r = radius * Math.min(1, Math.max(0, ratio));
    return [center + r * Math.cos(a), center + r * Math.sin(a)];
  };

  return (
    <div style={CARD_STYLE}>
      <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>{title}</h3>
      <div style={{ overflowX: "auto" }}>
        <svg viewBox={`0 0 ${size} ${size}`} style={{ width: "100%", maxWidth: size, height: "auto" }}>
          {[0.25, 0.5, 0.75, 1].map((t) => (
            <polygon
              key={t}
              points={axes.map((_, i) => pointFor(i, t).join(",")).join(" ")}
              fill="none"
              stroke="var(--line)"
              strokeWidth={1}
            />
          ))}
          {axes.map((axis, i) => {
            const [x, y] = pointFor(i, 1.12);
            return (
              <text key={axis.key} x={x} y={y} textAnchor="middle" fontSize={10} fill="var(--text-muted)">
                {axis.label}
              </text>
            );
          })}
          {communes.map((cc, ci) => {
            const axisAvgs = avgByCommune.get(cc)!;
            const points = axes.map((axis, i) => pointFor(i, axisAvgs.get(axis.key)! / axis.max).join(",")).join(" ");
            return (
              <polygon
                key={cc}
                points={points}
                fill={colors[ci % colors.length]}
                fillOpacity={0.08}
                stroke={colors[ci % colors.length]}
                strokeWidth={1.5}
              />
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

function NdviTab() {
  const { data: result, isLoading, error } = useCubeQuery(
    "ndvi",
    ["commune_overview.mean_ndvi"],
    ["commune_overview.commune_code", "commune_overview.period"]
  );
  const rows = (result?.data ?? []) as Row[];

  const stats = useMemo(() => {
    if (rows.length === 0) return null;
    const values = rows.map((r) => num(r, "commune_overview.mean_ndvi"));
    const communes = new Set(rows.map((r) => r["commune_overview.commune_code"]));
    const avg = values.reduce((a, b) => a + b, 0) / values.length;
    return { avg, min: Math.min(...values), max: Math.max(...values), communeCount: communes.size };
  }, [rows]);

  if (isLoading) return <div className="state-loading"><div className="spinner" /> Chargement...</div>;
  if (error) return <div className="banner banner-danger">Erreur de chargement des données.</div>;
  if (!stats) return <div className="empty-state">Aucune donnée disponible.</div>;

  return (
    <div>
      <div className="stat-row" style={{ marginBottom: 24 }}>
        <KpiCard label="NDVI moyen global" value={stats.avg.toFixed(3)} color="var(--ink-soft)" />
        <KpiCard label="NDVI minimum" value={stats.min.toFixed(3)} color="var(--flag)" />
        <KpiCard label="NDVI maximum" value={stats.max.toFixed(3)} color="var(--field)" />
        <KpiCard label="Communes" value={String(stats.communeCount)} color="var(--soil)" />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 }}>
        <LineChart data={rows} communeKey="commune_overview.commune_code" periodKey="commune_overview.period"
          valueKey="commune_overview.mean_ndvi" title="NDVI moyen par commune et par mois" />
        <BarChartByCommune data={rows} communeKey="commune_overview.commune_code" periodKey="commune_overview.period"
          valueKey="commune_overview.mean_ndvi" title="NDVI par commune" subtitle="Classement du dernier mois disponible"
          colorFn={ndviColor} />
      </div>
      <HeatmapTable data={rows} communeKey="commune_overview.commune_code" periodKey="commune_overview.period"
        valueKey="commune_overview.mean_ndvi" title="Matrice NDVI — Commune x Mois" colorFn={ndviColor} />
    </div>
  );
}

function VegetationTab() {
  const measures = ["vegetation_indices.mean_ndvi", "vegetation_indices.mean_evi", "vegetation_indices.mean_savi", "vegetation_indices.mean_lai"];
  const { data: result, isLoading, error } = useCubeQuery(
    "vegetation",
    measures,
    ["vegetation_indices.commune_code", "vegetation_indices.period"]
  );
  const rows = (result?.data ?? []) as Row[];
  // LAI runs 0–4 while NDVI/EVI/SAVI run 0–1 — scale it down so all four
  // series share a readable y-axis instead of LAI dwarfing the others.
  const scaledRows = useMemo(
    () => rows.map((r) => ({ ...r, "vegetation_indices.mean_lai_scaled": String(num(r, "vegetation_indices.mean_lai") / 4) })),
    [rows]
  );

  if (isLoading) return <div className="state-loading"><div className="spinner" /> Chargement...</div>;
  if (error) return <div className="banner banner-danger">Erreur de chargement des données.</div>;
  if (rows.length === 0) return <div className="empty-state">Aucune donnée disponible.</div>;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
      <MultiMetricLineChart
        data={scaledRows}
        periodKey="vegetation_indices.period"
        title="NDVI vs EVI vs SAVI vs LAI (moyenne des communes)"
        metrics={[
          { key: "vegetation_indices.mean_ndvi", label: "NDVI", color: "#2563eb" },
          { key: "vegetation_indices.mean_evi", label: "EVI", color: "#dc2626" },
          { key: "vegetation_indices.mean_savi", label: "SAVI", color: "#059669" },
          { key: "vegetation_indices.mean_lai_scaled", label: "LAI (÷4)", color: "#d97706" },
        ]}
      />
      <LineChart data={rows} communeKey="vegetation_indices.commune_code" periodKey="vegetation_indices.period"
        valueKey="vegetation_indices.mean_ndvi" title="NDVI par commune et par mois" />
    </div>
  );
}

function SoilTab() {
  const measures = ["soil_properties.avg_ph", "soil_properties.avg_organic_matter", "soil_properties.avg_nitrogen",
    "soil_properties.avg_phosphorus", "soil_properties.avg_potassium", "soil_properties.avg_water_retention"];
  const { data: result, isLoading, error } = useCubeQuery(
    "soil",
    measures,
    ["soil_properties.commune_code"]
  );
  const rows = (result?.data ?? []) as Row[];

  if (isLoading) return <div className="state-loading"><div className="spinner" /> Chargement...</div>;
  if (error) return <div className="banner banner-danger">Erreur de chargement des données.</div>;
  if (rows.length === 0) return <div className="empty-state">Aucune donnée disponible.</div>;

  return (
    <div>
      <RadarChart
        data={rows}
        communeKey="soil_properties.commune_code"
        title="Propriétés du sol par commune (moyenne annuelle, normalisée)"
        axes={[
          { key: "soil_properties.avg_ph", label: "pH", max: 9 },
          { key: "soil_properties.avg_organic_matter", label: "Mat. organique", max: 4 },
          { key: "soil_properties.avg_nitrogen", label: "Azote", max: 130 },
          { key: "soil_properties.avg_phosphorus", label: "Phosphore", max: 50 },
          { key: "soil_properties.avg_potassium", label: "Potassium", max: 450 },
          { key: "soil_properties.avg_water_retention", label: "Rétention eau", max: 190 },
        ]}
      />
    </div>
  );
}

function ClimateTab() {
  const measures = ["climate_indicators.avg_temp", "climate_indicators.total_precipitation", "climate_indicators.frost_days"];
  const { data: result, isLoading, error } = useCubeQuery(
    "climate",
    measures,
    ["climate_indicators.commune_code", "climate_indicators.period"]
  );
  const rows = (result?.data ?? []) as Row[];

  if (isLoading) return <div className="state-loading"><div className="spinner" /> Chargement...</div>;
  if (error) return <div className="banner banner-danger">Erreur de chargement des données.</div>;
  if (rows.length === 0) return <div className="empty-state">Aucune donnée disponible.</div>;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
      <LineChart data={rows} communeKey="climate_indicators.commune_code" periodKey="climate_indicators.period"
        valueKey="climate_indicators.avg_temp" title="Température moyenne (°C) par commune et par mois" />
      <BarChartByCommune data={rows} communeKey="climate_indicators.commune_code" periodKey="climate_indicators.period"
        useLatestPeriod={false} valueKey="climate_indicators.total_precipitation"
        title="Précipitations cumulées (mm) par commune" subtitle="Total sur les 12 mois" />
    </div>
  );
}

function WaterTab() {
  const measures = ["water_resources.avg_groundwater_level", "water_resources.avg_dam_fill_rate", "water_resources.total_irrigated_area"];
  const { data: result, isLoading, error } = useCubeQuery(
    "water",
    measures,
    ["water_resources.commune_code", "water_resources.period"]
  );
  const rows = (result?.data ?? []) as Row[];

  if (isLoading) return <div className="state-loading"><div className="spinner" /> Chargement...</div>;
  if (error) return <div className="banner banner-danger">Erreur de chargement des données.</div>;
  if (rows.length === 0) return <div className="empty-state">Aucune donnée disponible.</div>;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
      <BarChartByCommune data={rows} communeKey="water_resources.commune_code" periodKey="water_resources.period"
        valueKey="water_resources.avg_dam_fill_rate" title="Taux de remplissage des barrages (%)" />
      <HeatmapTable data={rows} communeKey="water_resources.commune_code" periodKey="water_resources.period"
        valueKey="water_resources.avg_groundwater_level" title="Niveau des nappes phréatiques (m) — Commune x Mois"
        colorFn={(v) => (v < 20 ? "#1a9850" : v < 45 ? "#fee08b" : "#d73027")} decimals={1} />
    </div>
  );
}

function CropsTab() {
  const measures = ["crop_calendar.avg_yield", "crop_calendar.total_cultivated_area", "crop_calendar.avg_water_stress_index"];
  const dimensions = ["crop_calendar.commune_code", "crop_calendar.season", "crop_calendar.crop_type", "crop_calendar.irrigation_type"];
  const { data: result, isLoading, error } = useCubeQuery("crops", measures, dimensions);
  const rows = (result?.data ?? []) as Row[];

  if (isLoading) return <div className="state-loading"><div className="spinner" /> Chargement...</div>;
  if (error) return <div className="banner banner-danger">Erreur de chargement des données.</div>;
  if (rows.length === 0) return <div className="empty-state">Aucune donnée disponible.</div>;

  return (
    <div style={CARD_STYLE}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h3 style={{ fontSize: 15, fontWeight: 600 }}>Calendrier cultural par commune</h3>
        <button
          onClick={() =>
            downloadCsv(
              "calendrier_cultural.csv",
              ["Commune", "Saison", "Culture", "Irrigation", "Rendement (q/ha)", "Surface (ha)", "Stress hydrique"],
              rows.map((r) => [
                r["crop_calendar.commune_code"],
                r["crop_calendar.season"],
                r["crop_calendar.crop_type"],
                r["crop_calendar.irrigation_type"],
                num(r, "crop_calendar.avg_yield").toFixed(1),
                num(r, "crop_calendar.total_cultivated_area").toFixed(0),
                num(r, "crop_calendar.avg_water_stress_index").toFixed(2),
              ])
            )
          }
          className="btn btn-outline btn-sm"
        >
          Export CSV
        </button>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ borderCollapse: "collapse", fontSize: 13, width: "100%" }}>
          <thead>
            <tr>
              {["Commune", "Saison", "Culture", "Irrigation", "Rendement (q/ha)", "Surface (ha)", "Stress hydrique"].map((h) => (
                <th key={h} style={{ padding: "8px 12px", textAlign: "left", borderBottom: "2px solid var(--color-border)", fontWeight: 600 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} style={{ borderBottom: "1px solid var(--color-border)" }}>
                <td style={{ padding: "6px 12px", fontFamily: "monospace" }}>{r["crop_calendar.commune_code"]}</td>
                <td style={{ padding: "6px 12px" }}>{r["crop_calendar.season"]}</td>
                <td style={{ padding: "6px 12px" }}>{r["crop_calendar.crop_type"]}</td>
                <td style={{ padding: "6px 12px" }}>{r["crop_calendar.irrigation_type"]}</td>
                <td style={{ padding: "6px 12px" }}>{num(r, "crop_calendar.avg_yield").toFixed(1)}</td>
                <td style={{ padding: "6px 12px" }}>{num(r, "crop_calendar.total_cultivated_area").toFixed(0)}</td>
                <td style={{ padding: "6px 12px" }}>{num(r, "crop_calendar.avg_water_stress_index").toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [tab, setTab] = useState<TabId>("ndvi");

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="eyebrow">Analytics</div>
          <h1>Dashboard</h1>
          <p>Indicateurs agricoles et environnementaux par commune, mis à jour à partir du pipeline de données.</p>
        </div>
      </div>

      <div className="tabs" style={{ marginBottom: 24, flexWrap: "wrap" }}>
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={"tab" + (tab === t.id ? " active" : "")}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "ndvi" && <NdviTab />}
      {tab === "vegetation" && <VegetationTab />}
      {tab === "soil" && <SoilTab />}
      {tab === "climate" && <ClimateTab />}
      {tab === "water" && <WaterTab />}
      {tab === "crops" && <CropsTab />}
    </div>
  );
}
