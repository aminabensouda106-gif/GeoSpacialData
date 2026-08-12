import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getCubeMeta, cubeExport, type CubeMember } from "../api";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { Protocol } from "pmtiles";

type ViewMode = "table" | "chart" | "map";

function encodeState(s: WorkbenchState): string {
  return btoa(JSON.stringify(s));
}

function decodeState(encoded: string): WorkbenchState | null {
  try {
    return JSON.parse(atob(encoded));
  } catch {
    return null;
  }
}

interface WorkbenchState {
  cube: string;
  measures: string[];
  dimensions: string[];
  view: ViewMode;
}

export default function Workbench() {
  const [searchParams, setSearchParams] = useSearchParams();

  const initialState = useMemo(() => {
    const s = searchParams.get("s");
    if (s) {
      const decoded = decodeState(s);
      if (decoded) return decoded;
    }
    return {
      cube: searchParams.get("cube") || "",
      measures: [] as string[],
      dimensions: [] as string[],
      view: "table" as ViewMode,
    };
  }, []);

  const [selectedCube, setSelectedCube] = useState(initialState.cube);
  const [selectedMeasures, setSelectedMeasures] = useState<string[]>(initialState.measures);
  const [selectedDimensions, setSelectedDimensions] = useState<string[]>(initialState.dimensions);
  const [viewMode, setViewMode] = useState<ViewMode>(initialState.view);

  const { data: meta } = useQuery({
    queryKey: ["cube-meta"],
    queryFn: getCubeMeta,
  });

  const cubes = meta?.cubes ?? [];
  const activeCube = cubes.find((c) => c.name === selectedCube);

  const cubeQuery = useMemo(() => {
    if (!selectedCube || selectedMeasures.length === 0) return null;
    return {
      measures: selectedMeasures,
      dimensions: selectedDimensions,
    };
  }, [selectedCube, selectedMeasures, selectedDimensions]);

  const { data: queryResult, isLoading: queryLoading } = useQuery({
    queryKey: ["cube-query", cubeQuery],
    queryFn: () => cubeExport(cubeQuery!),
    enabled: !!cubeQuery,
  });

  const rows = queryResult?.data ?? [];

  const updateUrl = useCallback(() => {
    const state: WorkbenchState = {
      cube: selectedCube,
      measures: selectedMeasures,
      dimensions: selectedDimensions,
      view: viewMode,
    };
    setSearchParams({ s: encodeState(state) }, { replace: true });
  }, [selectedCube, selectedMeasures, selectedDimensions, viewMode, setSearchParams]);

  useEffect(() => {
    if (selectedCube) updateUrl();
  }, [selectedCube, selectedMeasures, selectedDimensions, viewMode, updateUrl]);

  const geoJoinDim = activeCube?.dimensions.find(
    (d) => d.meta?.geo_join
  );
  const hasGeoJoin = !!geoJoinDim && selectedDimensions.includes(geoJoinDim.name);

  function toggleMeasure(name: string) {
    setSelectedMeasures((prev) =>
      prev.includes(name) ? prev.filter((m) => m !== name) : [...prev, name]
    );
  }

  function toggleDimension(name: string) {
    setSelectedDimensions((prev) =>
      prev.includes(name) ? prev.filter((d) => d !== name) : [...prev, name]
    );
  }

  const shareUrl = typeof window !== "undefined" ? window.location.href : "";

  return (
    <div style={{ display: "flex", gap: 20, minHeight: "calc(100vh - 120px)" }}>
      {/* Sidebar: cube & member picker */}
      <div style={{
        width: 280,
        flexShrink: 0,
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius)",
        padding: 16,
        boxShadow: "var(--shadow)",
        overflowY: "auto",
        maxHeight: "calc(100vh - 120px)",
      }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Cube</h3>
        <select
          value={selectedCube}
          onChange={(e) => {
            setSelectedCube(e.target.value);
            setSelectedMeasures([]);
            setSelectedDimensions([]);
          }}
          style={{
            width: "100%",
            padding: "6px 8px",
            borderRadius: "var(--radius)",
            border: "1px solid var(--color-border)",
            fontSize: 13,
            marginBottom: 16,
          }}
        >
          <option value="">Select a cube...</option>
          {cubes.map((c) => (
            <option key={c.name} value={c.name}>{c.title}</option>
          ))}
        </select>

        {activeCube && (
          <>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Measures</h3>
            {activeCube.measures.filter(m => m.isVisible).map((m) => (
              <MemberCheckbox
                key={m.name}
                member={m}
                checked={selectedMeasures.includes(m.name)}
                onChange={() => toggleMeasure(m.name)}
              />
            ))}

            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, marginTop: 16 }}>Dimensions</h3>
            {activeCube.dimensions.filter(d => d.isVisible).map((d) => (
              <MemberCheckbox
                key={d.name}
                member={d}
                checked={selectedDimensions.includes(d.name)}
                onChange={() => toggleDimension(d.name)}
              />
            ))}
          </>
        )}
      </div>

      {/* Main content area */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {/* View mode tabs + share */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <div style={{ display: "flex", gap: 4 }}>
            {(["table", "chart", "map"] as ViewMode[]).map((mode) => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                disabled={mode === "map" && !hasGeoJoin}
                style={{
                  padding: "6px 16px",
                  borderRadius: "var(--radius)",
                  border: "1px solid",
                  borderColor: viewMode === mode ? "var(--color-primary)" : "var(--color-border)",
                  background: viewMode === mode ? "var(--color-primary)" : "transparent",
                  color: viewMode === mode ? "#fff" : "var(--color-text-secondary)",
                  fontSize: 13,
                  fontWeight: 500,
                  opacity: mode === "map" && !hasGeoJoin ? 0.4 : 1,
                }}
              >
                {mode.charAt(0).toUpperCase() + mode.slice(1)}
              </button>
            ))}
          </div>
          <button
            onClick={() => navigator.clipboard.writeText(shareUrl)}
            style={{
              padding: "6px 14px",
              borderRadius: "var(--radius)",
              border: "1px solid var(--color-border)",
              background: "transparent",
              fontSize: 13,
              color: "var(--color-text-secondary)",
            }}
          >
            Copy Share URL
          </button>
        </div>

        {/* Caveat banners */}
        {activeCube && selectedMeasures.length > 0 && (
          <CaveatBanners measures={activeCube.measures} selected={selectedMeasures} />
        )}

        {/* Content */}
        {!selectedCube && (
          <EmptyState text="Select a cube from the sidebar to start exploring." />
        )}
        {selectedCube && selectedMeasures.length === 0 && (
          <EmptyState text="Select at least one measure to query data." />
        )}
        {queryLoading && <p style={{ color: "var(--color-text-secondary)" }}>Querying Cube...</p>}
        {rows.length > 0 && viewMode === "table" && (
          <DataTable rows={rows} measures={selectedMeasures} dimensions={selectedDimensions} />
        )}
        {rows.length > 0 && viewMode === "chart" && (
          <BarChart rows={rows} measures={selectedMeasures} dimensions={selectedDimensions} />
        )}
        {rows.length > 0 && viewMode === "map" && geoJoinDim && (
          <ChoroplethMap rows={rows} geoJoinDim={geoJoinDim.name} measure={selectedMeasures[0]} />
        )}
      </div>
    </div>
  );
}

function MemberCheckbox({ member, checked, onChange }: { member: CubeMember; checked: boolean; onChange: () => void }) {
  return (
    <label style={{
      display: "flex",
      alignItems: "start",
      gap: 6,
      marginBottom: 6,
      fontSize: 13,
      cursor: "pointer",
    }}>
      <input type="checkbox" checked={checked} onChange={onChange} style={{ marginTop: 3 }} />
      <div>
        <div style={{ fontWeight: 500 }}>{member.shortTitle}</div>
        {member.meta?.caveat && (
          <div style={{ fontSize: 11, color: "var(--color-warning)" }} title={member.meta.caveat}>
            caveat
          </div>
        )}
      </div>
    </label>
  );
}

function CaveatBanners({ measures, selected }: { measures: CubeMember[]; selected: string[] }) {
  const caveats = measures
    .filter((m) => selected.includes(m.name) && m.meta?.caveat)
    .map((m) => m.meta!.caveat!);
  const unique = [...new Set(caveats)];
  if (unique.length === 0) return null;
  return (
    <div style={{ marginBottom: 12 }}>
      {unique.map((c, i) => (
        <div key={i} style={{
          padding: "8px 12px",
          background: "#fef3c7",
          border: "1px solid #fcd34d",
          borderRadius: "var(--radius)",
          fontSize: 12,
          color: "#92400e",
          marginBottom: 4,
        }}>
          {c}
        </div>
      ))}
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div style={{
      padding: 40,
      textAlign: "center",
      color: "var(--color-text-secondary)",
      background: "var(--color-surface)",
      border: "1px solid var(--color-border)",
      borderRadius: "var(--radius)",
    }}>
      {text}
    </div>
  );
}

function DataTable({ rows, measures, dimensions }: {
  rows: Record<string, unknown>[];
  measures: string[];
  dimensions: string[];
}) {
  const columns = [...dimensions, ...measures];
  const shortName = (col: string) => col.split(".").pop() ?? col;
  return (
    <div style={{ overflowX: "auto", background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "var(--radius)" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col} style={{
                textAlign: "left",
                padding: "8px 10px",
                borderBottom: "2px solid var(--color-border)",
                fontWeight: 600,
                whiteSpace: "nowrap",
              }}>
                {shortName(col)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 200).map((row, i) => (
            <tr key={i} style={{ borderBottom: "1px solid var(--color-border)" }}>
              {columns.map((col) => (
                <td key={col} style={{ padding: "6px 10px", whiteSpace: "nowrap" }}>
                  {String(row[col] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > 200 && (
        <p style={{ padding: 8, fontSize: 12, color: "var(--color-text-secondary)" }}>
          Showing 200 of {rows.length} rows
        </p>
      )}
    </div>
  );
}

function BarChart({ rows, measures, dimensions }: {
  rows: Record<string, unknown>[];
  measures: string[];
  dimensions: string[];
}) {
  const labelDim = dimensions[0];
  const measure = measures[0];
  if (!labelDim || !measure) return <EmptyState text="Need at least one dimension and one measure for a chart." />;

  const values = rows.map((r) => Number(r[measure] ?? 0));
  const maxVal = Math.max(...values, 1);
  const shortName = (col: string) => col.split(".").pop() ?? col;

  return (
    <div style={{
      background: "var(--color-surface)",
      border: "1px solid var(--color-border)",
      borderRadius: "var(--radius)",
      padding: 16,
    }}>
      <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>
        {shortName(measure)} by {shortName(labelDim)}
      </h3>
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {rows.slice(0, 30).map((row, i) => {
          const val = Number(row[measure] ?? 0);
          const pct = (val / maxVal) * 100;
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ width: 120, fontSize: 12, textAlign: "right", flexShrink: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {String(row[labelDim] ?? "")}
              </div>
              <div style={{ flex: 1, height: 20, background: "#e5e7eb", borderRadius: 4, overflow: "hidden" }}>
                <div style={{ width: `${pct}%`, height: "100%", background: "var(--color-primary)", borderRadius: 4, transition: "width 0.3s" }} />
              </div>
              <div style={{ width: 60, fontSize: 12, textAlign: "right" }}>
                {typeof val === "number" ? val.toLocaleString(undefined, { maximumFractionDigits: 2 }) : val}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ChoroplethMap({ rows, geoJoinDim, measure }: {
  rows: Record<string, unknown>[];
  geoJoinDim: string;
  measure: string;
}) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [tilted, setTilted] = useState(true);

  const valueMap = useMemo(() => {
    const m = new Map<string, number>();
    for (const row of rows) {
      const code = String(row[geoJoinDim] ?? "");
      const val = Number(row[measure] ?? 0);
      if (code) m.set(code, val);
    }
    return m;
  }, [rows, geoJoinDim, measure]);

  const values = [...valueMap.values()];
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);

  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;

    const protocol = new Protocol();
    maplibregl.addProtocol("pmtiles", protocol.tile);

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "&copy; OpenStreetMap contributors",
          },
        },
        layers: [{ id: "osm", type: "raster", source: "osm" }],
      },
      center: [-7.5, 33.5],
      zoom: 5,
      pitch: 45,
      bearing: -17.6,
    });

    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");

    map.on("load", () => {
      map.addSource("communes", {
        type: "vector",
        url: `pmtiles://${window.location.origin}/tiles/serving/pmtiles/communes_boundaries.pmtiles`,
      });

      const stops: [number, string][] = [
        [minVal, "#f7fbff"],
        [minVal + (maxVal - minVal) * 0.25, "#c6dbef"],
        [minVal + (maxVal - minVal) * 0.5, "#6baed6"],
        [minVal + (maxVal - minVal) * 0.75, "#2171b5"],
        [maxVal, "#08306b"],
      ];

      const matchExpr: maplibregl.ExpressionSpecification = [
        "match",
        ["get", "commune_code"],
        ...Array.from(valueMap.entries()).flatMap(([code, val]) => [code, val]),
        0,
      ] as unknown as maplibregl.ExpressionSpecification;

      map.addLayer({
        id: "communes-fill",
        type: "fill",
        source: "communes",
        "source-layer": "communes_boundaries",
        paint: {
          "fill-color": [
            "interpolate",
            ["linear"],
            matchExpr,
            ...stops.flat(),
          ] as unknown as maplibregl.ExpressionSpecification,
          "fill-opacity": 0.7,
        },
      });

      map.addLayer({
        id: "communes-outline",
        type: "line",
        source: "communes",
        "source-layer": "communes_boundaries",
        paint: {
          "line-color": "#333",
          "line-width": 0.5,
        },
      });
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
      maplibregl.removeProtocol("pmtiles");
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const stops: [number, string][] = [
      [minVal, "#f7fbff"],
      [minVal + (maxVal - minVal) * 0.25, "#c6dbef"],
      [minVal + (maxVal - minVal) * 0.5, "#6baed6"],
      [minVal + (maxVal - minVal) * 0.75, "#2171b5"],
      [maxVal, "#08306b"],
    ];

    const matchExpr: unknown = [
      "match",
      ["get", "commune_code"],
      ...Array.from(valueMap.entries()).flatMap(([code, val]) => [code, val]),
      0,
    ];

    try {
      map.setPaintProperty("communes-fill", "fill-color", [
        "interpolate",
        ["linear"],
        matchExpr,
        ...stops.flat(),
      ]);
    } catch {
      // layer may not exist yet
    }
  }, [valueMap, minVal, maxVal]);

  const shortName = (col: string) => col.split(".").pop() ?? col;

  return (
    <div style={{ position: "relative" }}>
      <div ref={mapContainer} style={{
        width: "100%",
        height: 500,
        borderRadius: "var(--radius)",
        border: "1px solid var(--color-border)",
      }} />
      <button
        onClick={() => {
          const map = mapRef.current;
          if (!map) return;
          const next = !tilted;
          map.easeTo({ pitch: next ? 45 : 0, bearing: next ? -17.6 : 0 });
          setTilted(next);
        }}
        style={{
          position: "absolute",
          top: 16,
          right: 16,
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius)",
          padding: "6px 12px",
          fontSize: 13,
          fontWeight: 500,
          boxShadow: "var(--shadow)",
          cursor: "pointer",
        }}
      >
        {tilted ? "Vue à plat" : "Vue inclinée"}
      </button>
      <div style={{
        position: "absolute",
        bottom: 16,
        right: 16,
        background: "rgba(255,255,255,0.9)",
        padding: "8px 12px",
        borderRadius: "var(--radius)",
        fontSize: 12,
        boxShadow: "var(--shadow)",
      }}>
        <div style={{ fontWeight: 600, marginBottom: 4 }}>{shortName(measure)}</div>
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span>{minVal.toFixed(1)}</span>
          <div style={{
            width: 100,
            height: 12,
            background: "linear-gradient(to right, #f7fbff, #c6dbef, #6baed6, #2171b5, #08306b)",
            borderRadius: 2,
          }} />
          <span>{maxVal.toFixed(1)}</span>
        </div>
      </div>
    </div>
  );
}
