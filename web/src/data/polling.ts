import type { LatestData, Manifest } from "./schema";
import { loadSnapshot, POLL_INTERVAL_MS } from "./loader";

export interface Snapshot {
  manifest: Manifest;
  latest: LatestData;
}

export interface PollingController {
  stop: () => void;
}

export function startDataPolling(options: {
  onUpdate: (snapshot: Snapshot) => void;
  onError?: (error: unknown) => void;
  intervalMs?: number;
}): PollingController {
  const interval = options.intervalMs ?? POLL_INTERVAL_MS;
  let active = true;
  let timer: ReturnType<typeof setInterval> | undefined;

  const tick = async () => {
    try {
      const snapshot = await loadSnapshot();
      if (active) options.onUpdate(snapshot);
    } catch (error) {
      if (active && options.onError) options.onError(error);
    }
  };

  void tick();
  timer = setInterval(() => {
    void tick();
  }, interval);

  return {
    stop: () => {
      active = false;
      if (timer) clearInterval(timer);
    },
  };
}