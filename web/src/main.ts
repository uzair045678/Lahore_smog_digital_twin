import { CityScene } from "./scene/CityScene.js";
import { type Pollutant } from "./scene/CityScene.js";
import { startDataPolling } from "./data/polling.js";
import type { LatestData } from "./data/schema.js";

const canvas = document.getElementById("scene") as HTMLCanvasElement;
const status = document.getElementById("status")!;
const stationList = document.getElementById("stationList")!;
const pollutantSelect = document.getElementById("pollutant") as HTMLSelectElement;

const scene = new CityScene(canvas);
let selectedPollutant: Pollutant = "pm25";

function description(latest: LatestData): string {
  const observed = latest.stations.map((station) => station.observed_at ?? "").sort().pop() ?? "unknown";
  return `Live: ${latest.stations.length} stations · version ${latest.data_version} · observed ${observed}`;
}

void scene.ready.then(async () => {
  let latest: LatestData | null = null;
  const controller = startDataPolling({
    onUpdate: (snapshot) => {
      latest = snapshot.latest;
      scene.setSnapshot(snapshot.latest, selectedPollutant);
      status.textContent = description(snapshot.latest);
      stationList.textContent = snapshot.latest.stations
        .map((station) => {
          const air = snapshot.latest.measurements[station.id]?.find((r) => r.pollutant === selectedPollutant)?.concentration;
          const aqi = selectedPollutant === "pm25" ? station.aqi : null;
          return `${station.name}: ${air == null ? "n/a" : air.toFixed(1)} (${aqi ?? "n/a"})`;
        })
        .join(" · ");
    },
    onError: (error) => {
      status.textContent = `Data unavailable: ${error instanceof Error ? error.message : String(error)}`;
    },
  });

  pollutantSelect.addEventListener("change", () => {
    selectedPollutant = pollutantSelect.value as Pollutant;
    if (latest) scene.setSnapshot(latest, selectedPollutant);
  });

  window.addEventListener("beforeunload", () => controller.stop());
}).catch((error: unknown) => {
  status.textContent = `Scene failed to initialise: ${error instanceof Error ? error.message : String(error)}`;
});