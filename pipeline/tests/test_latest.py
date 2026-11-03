import json
from pathlib import Path

import pytest

from pipeline import build_latest, fetch_epa, fetch_openmeteo
from pipeline.schema import validate_history, validate_latest, validate_manifest


def test_checked_in_local_snapshots_validate():
    root = Path(__file__).resolve().parents[2]
    latest = json.loads((root / "out" / "latest.json").read_text(encoding="utf-8"))
    history = json.loads((root / "out" / "history.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "out" / "manifest.json").read_text(encoding="utf-8"))

    validate_latest(latest)
    validate_history(history)
    validate_manifest(manifest)
    assert latest["stations"]
    assert history["records"]


def test_measured_readings_keep_source_units():
    station = {
        "id": "epa-1",
        "pollutants": {"pm25": 12.0, "co": 0.4},
        "measured": True,
        "observed_at": "2026-10-24T20:00:00+05:00",
        "source": "epa",
    }
    readings = build_latest._readings(station)
    assert {item["pollutant"]: item["units"] for item in readings} == {
        "pm25": "µg/m³",
        "co": "mg/m³",
    }


def test_open_meteo_fallback_is_labelled_and_uses_model_units(monkeypatch):
    def fail_epa():
        raise RuntimeError("EPA unavailable")

    monkeypatch.setattr(fetch_epa, "fetch_lahore", fail_epa)
    monkeypatch.setattr(
        fetch_openmeteo,
        "fetch_city_fallback",
        lambda lat, lon: {
            "timestamp": "2026-10-24T20:00:00+05:00",
            "pollutants": {
                "pm25": {"concentration": 10.0},
                "co": {"concentration": 100.0},
            },
        },
    )
    monkeypatch.setattr(fetch_openmeteo, "fetch_wind_grid", lambda: [])

    latest = build_latest.assemble_latest()

    assert latest["source_health"]["open_meteo"]["role"] == "fallback"
    assert latest["stations"][0]["measured"] is False
    co = next(item for item in latest["measurements"]["city-center"] if item["pollutant"] == "co")
    assert co["source"] == "open_meteo"
    assert co["units"] == "µg/m³"


def test_open_meteo_failure_is_not_silently_converted_to_data(monkeypatch):
    monkeypatch.setattr(fetch_epa, "fetch_lahore", lambda: (_ for _ in ()).throw(RuntimeError("EPA unavailable")))
    monkeypatch.setattr(fetch_openmeteo, "fetch_city_fallback", lambda lat, lon: (_ for _ in ()).throw(RuntimeError("model unavailable")))
    with pytest.raises(RuntimeError, match="model unavailable"):
        build_latest.assemble_latest()
