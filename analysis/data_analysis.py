"""Process Cadmium evacuation logs into MARS-aligned metrics and CSVs."""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
from collections import Counter, defaultdict
from math import ceil
from pathlib import Path
from statistics import mean, median

import geopandas as gpd

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)

gdf = gpd.read_file("data_creation/carleton_campus_car_roads.geojson")
gdf_m = gdf.to_crs(epsg=32618)
gdf["seg_len_m"] = gdf_m.geometry.length

road_length_m: dict[str, float] = defaultdict(float)
for row in gdf.itertuples(index=False):
    sim_roads = getattr(row, "sim_roads", None)
    if sim_roads is None or isinstance(sim_roads, float) or len(sim_roads) == 0:
        continue
    for sr in sim_roads:
        road_length_m[sr.strip()] += float(row.seg_len_m)

# Fallback lengths when geojson sim_roads naming drifts.
sim_road_length_m: dict[str, float] = {}
sim_len_path = "data_creation/sim_road_lengths.csv"
if os.path.exists(sim_len_path):
    with open(sim_len_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            road = (row.get("ROAD") or "").strip()
            if not road:
                continue
            try:
                sim_road_length_m[road] = float(row.get("LENGTH_M", 0.0))
            except ValueError:
                continue

VEH_RE = re.compile(r"id=(\d+)")
DEST_RE = re.compile(r"dest=([^}]*)")

LOT_ORDER = ["P1", "P2", "P3", "P4", "P5", "P6", "P7"]
BASELINE_TARGET = 3200

# DEVS exit road model names → MARS gate labels (same chart labels).
# r28 (Raven→Bronson emergency) exists in scenario_07/09 topology; listing it
# here is safe for 1–6/08/10 because that road model never appears in those logs.
DEFAULT_EXIT_MODELS = {
    "P3 & Raven Rd to Bronson Ave & Raven Rd",
    "Raven Rd & University Dr to Bronson Ave & Raven Rd",
    "Library Rd & University Dr to Colonel By Dr & University Dr",
    "P5 & Stadium Way to Bronson Ave & Stadium Way",
    "Roundabout to Bronson Ave & University Dr",
}

EXIT_GATE_MAP = {
    "Library Rd & University Dr to Colonel By Dr & University Dr": "Colonel By",
    "Roundabout to Bronson Ave & University Dr": "Bronson Ave & University Dr",
    "P5 & Stadium Way to Bronson Ave & Stadium Way": "Stadium Way",
    "P3 & Raven Rd to Bronson Ave & Raven Rd": "Raven Rd emergency",
    "Raven Rd & University Dr to Bronson Ave & Raven Rd": "Raven Rd emergency",
}

CAMPUS_EXIT_ORDER = [
    "Colonel By",
    "Bronson Ave & University Dr",
    "Stadium Way",
    "Raven Rd emergency",
    "other",
]


def parse_line(line: str):
    """
    Parses: time,model_id,model_name,port_name,data
    Returns: (t, model_id, model_name, port_name, vehicle_id, dest, msg)
    """
    line = line.strip()
    if not line or line.startswith("sep=") or line.startswith("time,"):
        return None

    parts = [part.strip() for part in line.split(",", 4)]
    if len(parts) < 5:
        return None

    t = float(parts[0])
    model_id = int(parts[1])
    model_name = parts[2]
    port_name = parts[3]
    msg = parts[4]

    m = VEH_RE.search(msg)
    vehicle_id = int(m.group(1)) if m else None
    d = DEST_RE.search(msg)
    dest = d.group(1).strip() if d else ""
    return t, model_id, model_name, port_name, vehicle_id, dest, msg


def is_parking_lot(name: str) -> bool:
    return name.startswith("P") and len(name) <= 3


def read_schedule(path: str | None) -> tuple[int, dict[str, int]]:
    """Return (expected_total, per_lot counts) from a parking-lot schedule CSV."""
    per_lot = {lot: 0 for lot in LOT_ORDER}
    if not path or not os.path.isfile(path):
        return 0, per_lot
    with open(path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            lot = (row.get("id") or "").strip()
            if lot not in per_lot:
                continue
            try:
                per_lot[lot] = int(float(row.get("totalEvents") or 0))
            except ValueError:
                per_lot[lot] = 0
    return sum(per_lot.values()), per_lot


def analyze_log(path: str, exit_models=None, dt_sample: float = 1.0):
    """
    exit_models: set of model names that represent campus exits
    """
    if exit_models is None:
        exit_models = set(DEFAULT_EXIT_MODELS)

    lot_depart_time: dict[int, float] = {}
    lot_of_origin: dict[int, str] = {}
    campus_exit_time: dict[int, float] = {}
    campus_exit_road: dict[int, str] = {}

    roads_seen: set[str] = set()
    road_events: list[tuple[float, str, int]] = []
    all_times: list[float] = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            parsed = parse_line(line)
            if not parsed:
                continue

            t, _model_id, model_name, port_name, vid, dest, _msg = parsed
            all_times.append(t)
            if vid is None:
                continue

            if is_parking_lot(model_name) and port_name == "exit":
                if vid not in lot_depart_time or t < lot_depart_time[vid]:
                    lot_depart_time[vid] = t
                    lot_of_origin[vid] = model_name

            if model_name in exit_models:
                if vid not in campus_exit_time or t < campus_exit_time[vid]:
                    campus_exit_time[vid] = t
                    campus_exit_road[vid] = model_name

            if port_name.startswith("out") and dest:
                roads_seen.add(dest)
                road_events.append((t, dest, +1))

            if port_name == "exit" and " to " in model_name:
                roads_seen.add(model_name)
                road_events.append((t, model_name, -1))

    total_sim_time = max(all_times) if all_times else 0.0
    exited_vids = sorted(campus_exit_time.keys())

    drive_times: list[float] = []
    exit_from_t0: list[float] = []
    records: list[dict] = []
    completed_by_lot: Counter = Counter()
    clearance_by_lot: dict[str, float] = {}
    exit_usage: Counter = Counter()

    for vid in exited_vids:
        et = campus_exit_time[vid]
        exit_from_t0.append(et)
        lot = lot_of_origin.get(vid, "")
        st = lot_depart_time.get(vid)
        drive = (et - st) if st is not None else None
        if drive is not None:
            drive_times.append(drive)
        if lot in LOT_ORDER:
            completed_by_lot[lot] += 1
            prev = clearance_by_lot.get(lot)
            if prev is None or et > prev:
                clearance_by_lot[lot] = et
        road = campus_exit_road.get(vid, "")
        gate = EXIT_GATE_MAP.get(road, "other")
        exit_usage[gate] += 1
        records.append(
            {
                "vehicle_id": vid,
                "lot": lot,
                "lot_depart_s": st if st is not None else "",
                "campus_exit_s": et,
                "drive_s": drive if drive is not None else "",
                "exit_road": road,
                "exit_gate": gate,
            }
        )

    avg_from_t0 = mean(exit_from_t0) if exit_from_t0 else None
    avg_from_lot = mean(drive_times) if drive_times else None
    cars_per_min = (len(exited_vids) / total_sim_time) * 60.0 if total_sim_time else 0.0

    # Occupancy curve (cars driving on campus): lot exit +1, campus exit -1
    occ_events = [(st, +1) for st in lot_depart_time.values()]
    occ_events += [(et, -1) for et in campus_exit_time.values()]
    occ_events.sort()

    # Remaining-to-evacuate curve uses cumulative campus exits (MARS style).
    exit_events = sorted(campus_exit_time.values())
    spawn_events = sorted(lot_depart_time.values())

    t_min = 0.0
    t_max = total_sim_time
    n = int(ceil((t_max - t_min) / dt_sample)) + 1 if t_max >= t_min else 1
    sample_times = [t_min + i * dt_sample for i in range(n)]

    driving_curve: list[tuple[float, int]] = []
    remaining_curve: list[tuple[float, int]] = []
    spawn_curve: list[tuple[float, int]] = []
    depart_curve: list[tuple[float, int]] = []

    occ = 0
    i_occ = 0
    i_exit = 0
    i_spawn = 0
    for t in sample_times:
        while i_occ < len(occ_events) and occ_events[i_occ][0] <= t:
            occ += occ_events[i_occ][1]
            i_occ += 1
        while i_exit < len(exit_events) and exit_events[i_exit] <= t:
            i_exit += 1
        while i_spawn < len(spawn_events) and spawn_events[i_spawn] <= t:
            i_spawn += 1
        driving_curve.append((t, occ))
        remaining_curve.append((t, max(0, BASELINE_TARGET - i_exit)))
        spawn_curve.append((t, i_spawn))
        depart_curve.append((t, i_exit))

    roads = sorted(roads_seen)
    road_events.sort()
    road_occ: dict[str, int] = defaultdict(int)
    heat = {road: [] for road in roads}
    j = 0
    for t in sample_times:
        while j < len(road_events) and road_events[j][0] <= t:
            _, road, delta = road_events[j]
            road_occ[road] += delta
            j += 1
        for road in roads:
            L_geo = road_length_m.get(road, 0.0)
            L_sim = sim_road_length_m.get(road, 0.0)
            L = L_geo if L_geo > 0.0 else L_sim
            if L <= 0.0:
                cars_per_100m = 0.0
            else:
                cars_per_100m = road_occ[road] / (L / 100.0)
            heat[road].append(cars_per_100m)

    return {
        "total_sim_time": total_sim_time,
        "avg_from_t0": avg_from_t0,
        "avg_from_lot": avg_from_lot,
        "median_from_t0": median(exit_from_t0) if exit_from_t0 else None,
        "median_from_lot": median(drive_times) if drive_times else None,
        "cars_per_min": cars_per_min,
        "curve": remaining_curve,  # MARS: cars left to evacuate
        "driving_curve": driving_curve,
        "spawn_curve": spawn_curve,
        "depart_curve": depart_curve,
        "roads": roads,
        "heat": heat,
        "exited_count": len(exited_vids),
        "lot_based_count": len(drive_times),
        "travel_times": drive_times,
        "exit_from_t0_times": exit_from_t0,
        "clearance_by_lot_s": {lot: clearance_by_lot.get(lot) for lot in LOT_ORDER},
        "completed_by_lot": {lot: int(completed_by_lot.get(lot, 0)) for lot in LOT_ORDER},
        "exit_usage": {name: int(exit_usage.get(name, 0)) for name in CAMPUS_EXIT_ORDER},
        "records": records,
        "baseline_target": BASELINE_TARGET,
    }


def write_processed_outputs(
    results: dict,
    processed_dir: str,
    *,
    expected: int = 0,
    per_lot: dict[str, int] | None = None,
    scenario_id: str | None = None,
):
    """Write processed CSVs / metrics next to the log (MARS-aligned names)."""
    os.makedirs(processed_dir, exist_ok=True)
    per_lot = per_lot or {lot: 0 for lot in LOT_ORDER}
    if not expected:
        expected = sum(per_lot.values()) or BASELINE_TARGET

    summary_path = os.path.join(processed_dir, "summary.csv")
    summary_fields = [
        "total_sim_time",
        "exited_count",
        "lot_based_count",
        "avg_from_t0",
        "avg_from_lot",
        "median_from_t0",
        "median_from_lot",
        "cars_per_min",
        "expected",
        "baseline_target",
    ]
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()
        row = {field: results.get(field, "") for field in summary_fields}
        row["expected"] = expected
        row["baseline_target"] = results.get("baseline_target", BASELINE_TARGET)
        writer.writerow(row)

    # MARS-style evacuation curve CSV
    curve_path = os.path.join(processed_dir, "evac_curve.csv")
    spawn_by_t = dict(results["spawn_curve"])
    depart_by_t = dict(results["depart_curve"])
    campus_by_t = dict(results["curve"])
    with open(curve_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["time_s", "cars_on_campus", "cumulative_spawned", "cumulative_exited"]
        )
        for t, _ in results["curve"]:
            writer.writerow(
                [
                    t,
                    campus_by_t.get(t, ""),
                    spawn_by_t.get(t, ""),
                    depart_by_t.get(t, ""),
                ]
            )

    # Keep occupancy series available for debugging / legacy heat tooling
    driving_path = os.path.join(processed_dir, "driving_occupancy.csv")
    with open(driving_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["time", "cars_driving"])
        for t, occ in results["driving_curve"]:
            writer.writerow([t, occ])

    heatmap_path = os.path.join(processed_dir, "heatmap_matrix.csv")
    roads = results["roads"]
    heat = results["heat"]
    times = [t for (t, _) in results["curve"]]
    with open(heatmap_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["time"] + roads)
        for i, t in enumerate(times):
            writer.writerow([t] + [heat[road][i] for road in roads])

    # Per-trip leave-campus table (MARS: campus_exits.csv)
    exits_path = os.path.join(processed_dir, "campus_exits.csv")
    with open(exits_path, "w", newline="", encoding="utf-8") as f:
        fields = [
            "vehicle_id",
            "lot",
            "lot_depart_s",
            "campus_exit_s",
            "drive_s",
            "exit_road",
            "exit_gate",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for rec in results["records"]:
            writer.writerow(rec)

    # Lot / exit aggregates for plotting without re-parsing the log
    lots_path = os.path.join(processed_dir, "lot_exit_stats.csv")
    with open(lots_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["lot", "scheduled", "completed", "clearance_s"]
        )
        clearance = results.get("clearance_by_lot_s") or {}
        completed = results.get("completed_by_lot") or {}
        for lot in LOT_ORDER:
            writer.writerow(
                [
                    lot,
                    int(per_lot.get(lot, 0)),
                    int(completed.get(lot, 0)),
                    clearance.get(lot) if clearance.get(lot) is not None else "",
                ]
            )

    usage_path = os.path.join(processed_dir, "exit_usage.csv")
    with open(usage_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["exit_gate", "count"])
        usage = results.get("exit_usage") or {}
        for name in CAMPUS_EXIT_ORDER:
            writer.writerow([name, int(usage.get(name, 0))])

    trips = int(results.get("exited_count") or 0)
    rate = round((trips / expected * 100.0), 2) if expected else None
    metrics = {
        "schema_version": 2,
        "framework": "DEVS",
        "scenario_id": scenario_id,
        "expected": int(expected),
        "baseline_target": int(results.get("baseline_target") or BASELINE_TARGET),
        "completed": trips,
        "completion_rate_pct": rate,
        "total_sim_time_s": results.get("total_sim_time"),
        "mean_drive_to_exit_s": results.get("avg_from_lot"),
        "median_drive_to_exit_s": results.get("median_from_lot"),
        "mean_exit_from_t0_s": results.get("avg_from_t0"),
        "median_exit_from_t0_s": results.get("median_from_t0"),
        "cars_per_min": results.get("cars_per_min"),
        "clearance_by_lot_s": results.get("clearance_by_lot_s"),
        "completed_by_lot": results.get("completed_by_lot"),
        "scheduled_by_lot": {lot: int(per_lot.get(lot, 0)) for lot in LOT_ORDER},
        "exit_usage": results.get("exit_usage"),
    }
    with open(os.path.join(processed_dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)


def scenario_id_from_path(path: str) -> str | None:
    m = re.search(r"scenario_(\d+)", path.replace("\\", "/"))
    return m.group(1) if m else None


def default_schedule_for_log(log_csv: str) -> str | None:
    sid = scenario_id_from_path(log_csv)
    if not sid:
        return None
    candidate = ROOT / "input_data" / "parking_lot_schedules" / f"scenario_{sid}.csv"
    return str(candidate) if candidate.is_file() else None


def default_manifest_for_log(log_csv: str) -> str | None:
    sid = scenario_id_from_path(log_csv)
    if not sid:
        return None
    candidate = ROOT / "input_data" / "scenarios" / f"scenario_{sid}.json"
    return str(candidate) if candidate.is_file() else None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("log_csv", help="Path to scenario log CSV")
    parser.add_argument("--dt", type=float, default=1.0, help="Sampling interval for curve/heatmap")
    parser.add_argument(
        "--output-dir",
        help="Folder for summary/curve/heatmap CSVs (default: same folder as log_csv)",
    )
    parser.add_argument("--scenario-manifest", help="Path to scenario JSON manifest for campus exits")
    parser.add_argument(
        "--schedule",
        help="Parking-lot schedule CSV (default: inferred from scenario_XX in log path)",
    )
    args = parser.parse_args()

    exits = set(DEFAULT_EXIT_MODELS)
    manifest_path = args.scenario_manifest or default_manifest_for_log(args.log_csv)
    if manifest_path:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        exits = set(manifest["campus_exits"])

    results = analyze_log(args.log_csv, exit_models=exits, dt_sample=args.dt)

    schedule_path = args.schedule or default_schedule_for_log(args.log_csv)
    expected, per_lot = read_schedule(schedule_path)

    print("=== Summary ===")
    print("Total sim time:", results["total_sim_time"])
    print("Vehicles exited campus:", results["exited_count"])
    print("Vehicles with lot-based time:", results["lot_based_count"])
    print("Avg evac from t=0:", results["avg_from_t0"])
    print("Avg evac from leaving lot:", results["avg_from_lot"])
    print("Cars/min exiting campus:", results["cars_per_min"])
    if schedule_path:
        print("Schedule:", schedule_path, f"(expected={expected})")
    print("Exit usage:", results["exit_usage"])

    processed_dir = args.output_dir or os.path.dirname(os.path.abspath(args.log_csv))
    write_processed_outputs(
        results,
        processed_dir,
        expected=expected,
        per_lot=per_lot,
        scenario_id=scenario_id_from_path(args.log_csv) or scenario_id_from_path(processed_dir),
    )
    print("Wrote processed outputs to:", processed_dir)
