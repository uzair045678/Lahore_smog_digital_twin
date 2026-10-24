import "./data/schema";
import { startDataPolling } from "./data/polling";

const status = document.getElementById("status")!;
const stationList = document.getElementById("stations")!;

startDataPolling({
  onUpdate: (snapshot) => {
    status.textContent = `Live data: ${snapshot.latest.stations.length} stations, version ${snapshot.manifest.data_version}, observed ${snapshot.latest.stations[0]?.observed_at ?? "unknown"}`;
    stationList.innerHTML = snapshot.latest.stations
      .map((station) => {
        const air = snapshot.latest.measurements[station.id]?.find((r) => r.pollutant === "pm25")?.concentration;
        return `<div class="station"><strong>${station.name}</strong> — PM2.5 ${air ?? "n/a"} µg/m³ — AQI ${station.aqi ?? "n/a"} (${station.aqi_category ?? "uncategorised"})</div>`;
      })
      .join("");
  },
  onError: (error) => {
    status.textContent = `Data unavailable: ${error instanceof Error ? error.message : String(error)}`;
  },
});
