"""
Flood Water Harvesting System – Python Simulation
===================================================
Replicates the Arduino sketch logic for 3 buildings, each with an underground
tank and an overhead tank. Dual float sensors per tank drive pump control.

The simulation models:
  - Rainfall filling underground tanks (via road-border grills & filtration)
  - Pump transfers from underground → overhead tanks (Arduino logic)
  - Household consumption draining overhead tanks
  - Three scenarios: light rain, heavy downpour, and intermittent storms

Outputs:
  - Per-building water level time-series plots
  - Combined dashboard with pump state annotations
  - Console log mirroring the Arduino Serial Monitor
"""

import os
import numpy as np
import matplotlib

matplotlib.use("Agg")  # headless backend
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# ── Tank parameters (litres) ──────────────────────────────────────────────────
UNDERGROUND_CAPACITY = 1000.0  # max litres in underground tank
OVERHEAD_CAPACITY = 500.0  # max litres in overhead tank

# Sensor thresholds (fraction of tank capacity)
LOW_THRESHOLD = 0.10  # "low" sensor triggers below this
HIGH_THRESHOLD = 0.90  # "high" sensor triggers above this

# Flow rates (litres per second)
PUMP_RATE = 2.0  # pump transfer rate underground → overhead
CONSUMPTION_RATE = 0.3  # household water consumption from overhead

# Simulation timing
DT = 1.0  # time step in seconds (matches Arduino 1 s loop)
DURATION = 3600  # total simulation time in seconds (1 hour)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── Rainfall profiles ────────────────────────────────────────────────────────
def light_rain(t: float) -> float:
    """Steady light rain – 0.5 L/s inflow."""
    return 0.5


def heavy_downpour(t: float) -> float:
    """Heavy downpour for first 20 min, then stops."""
    return 4.0 if t < 1200 else 0.0


def intermittent_storms(t: float) -> float:
    """Three storm bursts with dry gaps in between."""
    if 0 <= t < 600:
        return 3.0
    elif 900 <= t < 1500:
        return 5.0
    elif 2100 <= t < 2700:
        return 2.5
    return 0.0


SCENARIOS = {
    "Light Steady Rain": light_rain,
    "Heavy Downpour (20 min)": heavy_downpour,
    "Intermittent Storms": intermittent_storms,
}


# ── Arduino logic (mirrors managePump) ───────────────────────────────────────
def read_sensors(level: float, capacity: float):
    """Return simulated float-sensor booleans matching INPUT_PULLUP wiring.

    LOW sensor reads HIGH (not submerged) when level < LOW_THRESHOLD.
    HIGH sensor reads LOW (submerged) when level >= HIGH_THRESHOLD.
    """
    is_low = level / capacity < LOW_THRESHOLD
    is_high = level / capacity >= HIGH_THRESHOLD
    return is_low, is_high


def manage_pump(
    ug_level: float,
    oh_level: float,
    pump_on: bool,
    building: str,
    log: list[str],
    t: float,
) -> bool:
    """Replicate Arduino managePump logic. Returns new pump state."""
    ug_low, ug_high = read_sensors(ug_level, UNDERGROUND_CAPACITY)
    oh_low, oh_high = read_sensors(oh_level, OVERHEAD_CAPACITY)

    underground_has_water = ug_high  # high sensor submerged
    underground_is_low = ug_low  # low sensor NOT submerged
    overhead_is_full = oh_high  # high sensor submerged
    overhead_needs_water = oh_low  # low sensor NOT submerged (tank nearly empty)

    new_state = pump_on
    if underground_has_water and overhead_needs_water and not overhead_is_full:
        if not pump_on:
            log.append(f"[{t:6.0f}s] {building}: pump ON")
        new_state = True
    elif underground_is_low or overhead_is_full:
        if pump_on:
            log.append(f"[{t:6.0f}s] {building}: pump OFF")
        new_state = False
    return new_state


# ── Simulation engine ────────────────────────────────────────────────────────
def run_scenario(name: str, rain_fn):
    """Simulate one rainfall scenario for all 3 buildings and return results."""
    steps = int(DURATION / DT)
    time = np.arange(steps) * DT

    # State arrays per building (3 buildings)
    ug = np.zeros((3, steps))  # underground level
    oh = np.zeros((3, steps))  # overhead level
    pump = np.zeros((3, steps), dtype=bool)
    rain = np.zeros(steps)

    # Initial conditions – underground empty, overhead half-full
    ug[:, 0] = 0.0
    oh[:, 0] = OVERHEAD_CAPACITY * 0.5

    # Slightly different consumption rates per building for realism
    consumption = [CONSUMPTION_RATE, CONSUMPTION_RATE * 1.2, CONSUMPTION_RATE * 0.8]

    log: list[str] = [f"--- Scenario: {name} ---", "flood water system ready"]

    for k in range(1, steps):
        t = time[k]
        r = rain_fn(t)
        rain[k] = r

        for b in range(3):
            # Rainfall fills underground tank (split equally among 3 buildings)
            inflow = r * DT / 3.0
            new_ug = ug[b, k - 1] + inflow

            # Pump transfer
            p = manage_pump(
                ug[b, k - 1],
                oh[b, k - 1],
                pump[b, k - 1],
                f"building {b + 1}",
                log,
                t,
            )
            pump[b, k] = p
            transfer = PUMP_RATE * DT if p else 0.0
            transfer = min(transfer, new_ug)  # can't pump more than available
            transfer = min(
                transfer, OVERHEAD_CAPACITY - oh[b, k - 1]
            )  # can't overfill

            new_ug -= transfer
            new_oh = oh[b, k - 1] + transfer - consumption[b] * DT

            # Clamp
            ug[b, k] = np.clip(new_ug, 0, UNDERGROUND_CAPACITY)
            oh[b, k] = np.clip(new_oh, 0, OVERHEAD_CAPACITY)

    return {
        "name": name,
        "time": time,
        "ug": ug,
        "oh": oh,
        "pump": pump,
        "rain": rain,
        "log": log,
    }


# ── Plotting helpers ─────────────────────────────────────────────────────────
COLORS = ["#2196F3", "#4CAF50", "#FF9800"]  # blue, green, orange per building


def plot_building_levels(result: dict, filename: str):
    """One figure with 3 subplots (one per building) showing UG + OH levels."""
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    fig.suptitle(f"Water Levels – {result['name']}", fontsize=15, fontweight="bold")
    t_min = result["time"] / 60  # convert to minutes

    for b, ax in enumerate(axes):
        ax.fill_between(
            t_min,
            result["ug"][b],
            alpha=0.35,
            color=COLORS[b],
            label="Underground",
        )
        ax.plot(t_min, result["oh"][b], color=COLORS[b], lw=2, label="Overhead")

        # Shade pump-ON regions
        pump_on = result["pump"][b].astype(float)
        ax.fill_between(
            t_min,
            0,
            UNDERGROUND_CAPACITY * 0.05,
            where=pump_on > 0,
            color="red",
            alpha=0.25,
            label="Pump ON",
        )

        ax.set_ylabel("Litres", fontsize=11)
        ax.set_title(f"Building {b + 1}", fontsize=12)
        ax.legend(loc="upper right", fontsize=9)
        ax.set_ylim(0, max(UNDERGROUND_CAPACITY, OVERHEAD_CAPACITY) * 1.1)
        ax.axhline(
            UNDERGROUND_CAPACITY * HIGH_THRESHOLD,
            ls="--",
            color="grey",
            lw=0.7,
            label="High sensor",
        )
        ax.axhline(
            UNDERGROUND_CAPACITY * LOW_THRESHOLD,
            ls=":",
            color="grey",
            lw=0.7,
            label="Low sensor",
        )
        ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel("Time (minutes)", fontsize=12)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  saved → {path}")
    return path


def plot_combined_dashboard(results: list[dict], filename: str):
    """3×2 dashboard: one row per scenario, columns = underground / overhead."""
    fig, axes = plt.subplots(3, 2, figsize=(16, 12), sharex=True)
    fig.suptitle(
        "Flood Water Harvesting System – Simulation Dashboard",
        fontsize=16,
        fontweight="bold",
    )

    for row, res in enumerate(results):
        t_min = res["time"] / 60
        ax_ug = axes[row, 0]
        ax_oh = axes[row, 1]

        for b in range(3):
            ax_ug.plot(
                t_min,
                res["ug"][b],
                color=COLORS[b],
                lw=1.5,
                label=f"Bldg {b + 1}",
            )
            ax_oh.plot(
                t_min,
                res["oh"][b],
                color=COLORS[b],
                lw=1.5,
                label=f"Bldg {b + 1}",
            )

        # Rainfall overlay on underground chart
        ax_rain = ax_ug.twinx()
        ax_rain.fill_between(t_min, res["rain"], color="cyan", alpha=0.15)
        ax_rain.set_ylabel("Rain (L/s)", color="cyan", fontsize=9)
        ax_rain.set_ylim(0, 8)
        ax_rain.tick_params(axis="y", labelcolor="cyan")

        ax_ug.set_ylabel("Underground (L)", fontsize=10)
        ax_oh.set_ylabel("Overhead (L)", fontsize=10)
        ax_ug.set_title(f"{res['name']} – Underground Tanks", fontsize=11)
        ax_oh.set_title(f"{res['name']} – Overhead Tanks", fontsize=11)

        for ax in (ax_ug, ax_oh):
            ax.legend(loc="upper right", fontsize=8)
            ax.grid(True, alpha=0.3)

        ax_ug.set_ylim(0, UNDERGROUND_CAPACITY * 1.1)
        ax_oh.set_ylim(0, OVERHEAD_CAPACITY * 1.1)

    axes[-1, 0].set_xlabel("Time (minutes)", fontsize=11)
    axes[-1, 1].set_xlabel("Time (minutes)", fontsize=11)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  saved → {path}")
    return path


def plot_rainfall_vs_response(results: list[dict], filename: str):
    """Single figure showing rainfall input vs total harvested water."""
    fig, axes = plt.subplots(len(results), 1, figsize=(14, 10), sharex=True)
    fig.suptitle(
        "Rainfall Input vs. System Response",
        fontsize=15,
        fontweight="bold",
    )

    for i, res in enumerate(results):
        ax = axes[i]
        t_min = res["time"] / 60

        # Total water across all 3 buildings
        total_ug = res["ug"].sum(axis=0)
        total_oh = res["oh"].sum(axis=0)
        total_water = total_ug + total_oh

        ax.fill_between(
            t_min, total_ug, alpha=0.3, color="#2196F3", label="Total Underground"
        )
        ax.fill_between(
            t_min, total_oh, alpha=0.3, color="#4CAF50", label="Total Overhead"
        )
        ax.plot(t_min, total_water, color="black", lw=2, label="Total Stored Water")

        # Rainfall overlay
        ax2 = ax.twinx()
        ax2.bar(
            t_min[::60],
            res["rain"][::60],
            width=0.8,
            color="cyan",
            alpha=0.3,
            label="Rainfall",
        )
        ax2.set_ylabel("Rainfall (L/s)", color="cyan", fontsize=10)
        ax2.set_ylim(0, 8)

        ax.set_ylabel("Water (L)", fontsize=10)
        ax.set_title(res["name"], fontsize=12)
        ax.legend(loc="upper left", fontsize=9)
        ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel("Time (minutes)", fontsize=12)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  saved → {path}")
    return path


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  Flood Water Harvesting System – Simulation")
    print("=" * 60)

    results = []
    for name, rain_fn in SCENARIOS.items():
        print(f"\nRunning scenario: {name}")
        res = run_scenario(name, rain_fn)
        results.append(res)

        # Print Arduino-style serial log (first 30 lines + summary)
        for line in res["log"][:30]:
            print(f"  {line}")
        if len(res["log"]) > 30:
            print(f"  ... ({len(res['log']) - 30} more log entries)")

        # Summary stats
        for b in range(3):
            peak_ug = res["ug"][b].max()
            peak_oh = res["oh"][b].max()
            pump_pct = res["pump"][b].sum() / len(res["pump"][b]) * 100
            print(
                f"  Building {b+1}: peak UG={peak_ug:.0f}L, "
                f"peak OH={peak_oh:.0f}L, pump ON={pump_pct:.1f}%"
            )

    # Generate plots
    print("\nGenerating visualizations...")
    paths = []
    for res in results:
        safe_name = res["name"].lower().replace(" ", "_").replace("(", "").replace(")", "")
        p = plot_building_levels(res, f"levels_{safe_name}.png")
        paths.append(p)

    paths.append(plot_combined_dashboard(results, "dashboard.png"))
    paths.append(plot_rainfall_vs_response(results, "rainfall_vs_response.png"))

    # Save full logs
    log_path = os.path.join(OUTPUT_DIR, "serial_log.txt")
    with open(log_path, "w") as f:
        for res in results:
            for line in res["log"]:
                f.write(line + "\n")
            f.write("\n")
    print(f"  saved → {log_path}")

    print("\nSimulation complete! All outputs in:", OUTPUT_DIR)
    return paths


if __name__ == "__main__":
    main()
