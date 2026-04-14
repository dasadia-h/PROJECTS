# Flood Water Harvesting System – Simulation

A Python-based simulation that models the behavior of the Arduino flood water harvesting system. It replicates the exact sensor logic and pump control from `flood_water_system.ino` and visualizes how water levels in underground and overhead tanks respond to different rainfall scenarios.

## How the Simulation Works

The simulation mirrors the Arduino sketch's `managePump()` logic:

| Sensor Condition | Simulated Behavior |
|---|---|
| Underground level ≥ 90% capacity (high sensor submerged) | `undergroundHasWater = true` |
| Underground level < 10% capacity (low sensor exposed) | `undergroundIsLow = true` |
| Overhead level ≥ 90% capacity (high sensor submerged) | `overheadIsFull = true` |
| Overhead level < 10% capacity (low sensor exposed) | `overheadNeedsWater = true` |

**Pump turns ON** when: underground has water AND overhead needs water AND overhead is not full  
**Pump turns OFF** when: underground is empty OR overhead is full

### Physical Model

| Parameter | Value |
|---|---|
| Underground tank capacity | 1000 L |
| Overhead tank capacity | 500 L |
| Pump transfer rate | 2 L/s |
| Household consumption | 0.3 L/s (varies ±20% per building) |
| Simulation duration | 1 hour (1-second time steps) |

## Rainfall Scenarios

1. **Light Steady Rain** – Constant 0.5 L/s inflow for the full hour
2. **Heavy Downpour (20 min)** – 4.0 L/s for the first 20 minutes, then stops
3. **Intermittent Storms** – Three storm bursts (3.0, 5.0, 2.5 L/s) with dry gaps

## Running the Simulation

```bash
pip install matplotlib numpy
python simulation/flood_simulation.py
```

Output plots and logs are saved to `simulation/output/`.

## Output Files

| File | Description |
|---|---|
| `levels_light_steady_rain.png` | Per-building water levels under light rain |
| `levels_heavy_downpour_20_min.png` | Per-building water levels under heavy downpour |
| `levels_intermittent_storms.png` | Per-building water levels during storm bursts |
| `dashboard.png` | Combined 3×2 dashboard (underground + overhead per scenario) |
| `rainfall_vs_response.png` | Total harvested water vs rainfall input |
| `serial_log.txt` | Full pump decision log (mirrors Arduino Serial Monitor) |
