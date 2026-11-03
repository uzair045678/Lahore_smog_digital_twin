from pipeline.fetch_epa import extract_forecast, extract_history, extract_stations


def test_epa_snapshot_extracts_station_history_and_forecast():
    snapshot = {
        "station": {
            "station_id": 12,
            "station_name": "Barki Road",
            "latitude": "31.5359",
            "longitude": "74.4352",
            "pm25": "21.4",
            "co": "0.3",
            "aqi": 67,
            "aqi_range": [{"range": "51-100", "health_index": "Satisfactory"}],
            "pollutant_flags": [{"pm10": "M"}],
            "timestamp": ["2026-10-24T20:00:00+05:00", {}],
        },
        "history": {
            "station_names": ["Barki Road"],
            "datetime": "2026-10-24T19:00:00+05:00",
            "aqi": 70,
            "aqi_range": [{"range": "51-100"}],
            "pm25": "22.0",
        },
        "forecast": {
            "datetime": "2026-10-24T21:00:00+05:00",
            "aqi": 65,
            "aqi_health_index": "Satisfactory",
            "precipitation_probability": 0,
        },
    }

    stations = extract_stations(snapshot)
    history = extract_history(snapshot)
    forecast = extract_forecast(snapshot)

    assert len(stations) == 1
    assert stations[0]["lat"] == 31.5359
    assert stations[0]["pollutants"]["co"] == 0.3
    assert stations[0]["pollutant_flags"] == {"pm10": "M"}
    assert history[0]["pollutants"]["pm25"] == 22.0
    assert forecast[0]["aqi"] == 65
