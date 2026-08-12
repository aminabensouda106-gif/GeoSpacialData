const bus = new EventTarget();

export interface FlyToLocation {
  lat: number;
  lon: number;
  label: string;
}

export function emitFlyTo(loc: FlyToLocation) {
  bus.dispatchEvent(new CustomEvent<FlyToLocation>("flyto", { detail: loc }));
}

export function onFlyTo(handler: (loc: FlyToLocation) => void): () => void {
  const listener = (e: Event) => handler((e as CustomEvent<FlyToLocation>).detail);
  bus.addEventListener("flyto", listener);
  return () => bus.removeEventListener("flyto", listener);
}
