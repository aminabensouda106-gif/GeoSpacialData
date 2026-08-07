const BASE = "/api";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export interface Dataset {
  id: string;
  title: string;
  description: string;
  source_type: string;
  modality: string;
  format: string;
  owner: string | null;
  classification: string | null;
  source_class: string | null;
  license: string | null;
  citation: string | null;
  caveats: string | null;
  stac_collection: string | null;
  terria_group: string | null;
  has_pmtiles: boolean;
  quality_checks: string[];
}

export interface CubeMeta {
  cubes: CubeDescriptor[];
}

export interface CubeDescriptor {
  name: string;
  title: string;
  description: string;
  type: string;
  measures: CubeMember[];
  dimensions: CubeMember[];
}

export interface CubeMember {
  name: string;
  title: string;
  shortTitle: string;
  description: string;
  type: string;
  aggType?: string;
  meta?: Record<string, string>;
  isVisible: boolean;
}

export interface LineageRun {
  run_id: string;
  dataset_id: string;
  started_at: string;
  finished_at: string;
  status: string;
  row_count: number;
}

export function searchDatasets(q: string) {
  return fetchJson<Dataset[]>(`/search?q=${encodeURIComponent(q)}`);
}

export function getAllDatasets() {
  return fetchJson<Dataset[]>("/search?q=");
}

export function getDataset(id: string) {
  return fetchJson<Dataset>(`/datasets/${encodeURIComponent(id)}`);
}

export function getLineage(id: string) {
  return fetchJson<LineageRun[]>(`/datasets/${encodeURIComponent(id)}/lineage`);
}

export function getCubeMeta() {
  return fetchJson<CubeMeta>("/meta");
}

export function cubeExport(query: Record<string, unknown>) {
  return fetchJson<{ data: Record<string, unknown>[] }>("/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
}
