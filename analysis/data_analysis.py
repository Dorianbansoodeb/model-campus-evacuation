import re
import argparse
import json
import os
import csv
from collections import defaultdict
from math import ceil

import geopandas as gpd
from collections import defaultdict

gdf = gpd.read_file("data_creation/carleton_campus_car_roads.geojson")
gdf_m = gdf.to_crs(epsg=32618)
gdf["seg_len_m"] = gdf_m.geometry.length

road_length_m = defaultdict(float)

for row in gdf.itertuples(index=False):
    sim_roads = getattr(row, "sim_roads", None)
    if sim_roads is None or isinstance(sim_roads, float) or len(sim_roads) == 0:
        continue
    for sr in sim_roads:
        road_length_m[sr.strip()] += float(row.seg_len_m)

# Regular expressions to extract vehicle ID and destination from message
VEH_RE = re.compile(r"id=(\d+)")
DEST_RE = re.compile(r"dest=([^}]*)")


def parse_line(line: str):
    """
    Parses: time,model_id,model_name,port_name,data
    Returns: (t, model_id, model_name, port_name, vehicle_id, dest)
    """
    line = line.strip()
    if not line:
        return None

    # Skip Excel hint row
    if line.startswith("sep="):
        return None
    
    # Skip header
    if line.startswith("time,"):
        return None
    
    parts = [part.strip() for part in line.split(",", 4)]
    if len(parts) < 5:
        return None
    
    # Turn time into a float
    t = float(parts[0])
    model_id = int(parts[1])
    model_name = parts[2]
    port_name = parts[3]
    msg = parts[4]

    # Extract vehicle ID and destination using regex
    m = VEH_RE.search(msg)
    vehicle_id = int(m.group(1)) if m else None

    # Extract destination
    d = DEST_RE.search(msg)
    dest = d.group(1).strip() if d else ""  # dest can be empty

    return t, model_id, model_name, port_name, vehicle_id, dest, msg

def is_parking_lot(name: str) -> bool:
    """
    Determine if a component name corresponds to a parking lot.
    """
    return name.startswith("P") and len(name) <= 3

def analyze_log(path: str, exit_models = None, dt_sample: float = 1.0):
    """
    exit_models: set of model names that represent campus exits
    """
    if exit_models is None:
        exit_models = set()
    
    lot_depart_time = {} # vid -> first time vehicle exited parking lot
    campus_exit_time = {} # vid -> first time vehicle exited campus
    
    # For evac curve
    evac_events = [] # (t, delta)

    # For road heatmap
    roads_seen = set()
    road_events= [] # (t, road, delta)

    all_times = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            parsed = parse_line(line)
            if not parsed:
                continue

            t, model_id, model_name, port_name, vid, dest, msg= parsed
            all_times.append(t)

            if vid is None:
                continue

            # (1) lot departure time: first time the vehicle exits a parking lot
            if is_parking_lot(model_name) and port_name == "exit":
                if vid not in lot_depart_time or t < lot_depart_time[vid]:
                    lot_depart_time[vid] = t
            
            # (2) campus exit time: first time the vehicle exits campus
            if model_name in exit_models:
                if vid not in campus_exit_time or t < campus_exit_time[vid]:
                    campus_exit_time[vid] = t

            # (3) road occupancy events
            if port_name.startswith("out") and dest:
                road = dest
                roads_seen.add(road)
                road_events.append((t, road, +1))
            
            if port_name == "exit" and " to " in model_name:
                road = model_name
                roads_seen.add(road)
                road_events.append((t, road, -1))
            
    # Compute metrics
    total_sim_time = max(all_times) if all_times else 0.0

    exited_vids = sorted(campus_exit_time.keys())

    # Avg from t=0 is just avg(exit_time)
    avg_from_t0 = (
        sum(campus_exit_time[v] for v in exited_vids) / len(exited_vids)
        if exited_vids else None
    )

    # Avg from leaving lot is avg(exit_time - lot_depart_time)
    lot_based_times = []
    for v in exited_vids:
        if v in lot_depart_time:
            lot_based_times.append(campus_exit_time[v] - lot_depart_time[v])

    avg_from_lot = (sum(lot_based_times) / len(lot_based_times)
        if lot_based_times else None
    )

    cars_per_min = (len(exited_vids) / total_sim_time) * 60.0

    # Evacuation curve
    # Treating "lot exit" as entering campus, and "campus exit" as leaving campus
    for v, st in lot_depart_time.items():
        evac_events.append((st, +1))
    for v, et in campus_exit_time.items():
        evac_events.append((et, -1))
    evac_events.sort()

    t_min = 0.0
    t_max = total_sim_time
    n = int(ceil((t_max - t_min) / dt_sample)) + 1
    sample_times = [t_min + i * dt_sample for i in range(n)]

    curve = []
    occ = 0
    i = 0
    for t in sample_times:
        while i < len(evac_events) and evac_events[i][0] <= t:
            occ += evac_events[i][1]
            i += 1
        curve.append((t, occ))

    # Heatmap data
    roads = sorted(roads_seen)
    road_events.sort()

    road_occ = defaultdict(int)
    heat = {road: [] for road in roads}

    j = 0
    for t in sample_times:
        while j < len(road_events) and road_events[j][0] <= t:
            _, road, delta = road_events[j]
            road_occ[road] += delta
            j += 1

        EPS = 1e-9
        for road in roads:
            L = max(road_length_m.get(road, 0.0), EPS)  # meters
            cars_per_100m = road_occ[road] / (L / 100.0)
            heat[road].append(cars_per_100m)

    return {
        "total_sim_time": total_sim_time,
        "avg_from_t0": avg_from_t0,
        "avg_from_lot": avg_from_lot,
        "cars_per_min": cars_per_min,
        "curve": curve,      # list[(t, cars_on_campus)]
        "roads": roads,      # ordered road list for heat columns
        "heat": heat,        # dict road -> list[occupancy]
        "exited_count": len(exited_vids),
        "lot_based_count": len(lot_based_times),
    }

def write_processed_outputs(results: dict, processed_dir: str):
    """
    Write processed outputs (curve CSV, heatmap CSV) to processed_dir.
    """
    os.makedirs(processed_dir, exist_ok=True)

    # summary.csv
    summary_path = os.path.join(processed_dir, "summary.csv")
    summary_fields = [
        "total_sim_time",
        "exited_count",
        "lot_based_count",
        "avg_from_t0",
        "avg_from_lot",
        "cars_per_min",
    ]

    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerow({field: results[field] for field in summary_fields})

    # curve.csv
    curve_path = os.path.join(processed_dir, "evac_curve.csv")
    with open(curve_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["time", "cars_on_campus"])
        for t, occ in results["curve"]:
            writer.writerow([t, occ])

    # heatmap.csv
    heatmap_path = os.path.join(processed_dir, "heatmap_matrix.csv")
    roads = results["roads"]
    heat = results["heat"] # dict road -> list of occupancy aligned with sample times
    times = [t for (t, _) in results["curve"]]

    with open(heatmap_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["time"] + roads)
        for i, t in enumerate(times):
            row = [t] + [heat[road][i] for road in roads]
            writer.writerow(row)
            
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("log_csv", help="Path to scenario log CSV")
    parser.add_argument("--dt", type=float, default=1.0, help="Sampling interval for curve/heatmap")
    parser.add_argument("--scenario-manifest", help="Path to scenario JSON manifest for campus exits")
    args = parser.parse_args()

    # Due to how logging is done, exit time = when the vehicle finished the last road segment that connect to outiside
    exits = {
        "P3 & Raven Rd to Bronson Ave & Raven Rd",
        "Library Rd & University Dr to Colonel By Dr & University Dr",
        "P5 & Stadium Way to Bronson Ave & Stadium Way",
        "Roundabout to Bronson Ave & University Dr"
    }

    if args.scenario_manifest:
        with open(args.scenario_manifest, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        exits = set(manifest["campus_exits"])

    results = analyze_log(args.log_csv, exit_models=exits, dt_sample=args.dt)

    print("=== Summary ===")
    print("Total sim time:", results["total_sim_time"])
    print("Vehicles exited campus:", results["exited_count"])
    print("Vehicles with lot-based time:", results["lot_based_count"])
    print("Avg evac from t=0:", results["avg_from_t0"])
    print("Avg evac from leaving lot:", results["avg_from_lot"])
    print("Cars/min exiting campus:", results["cars_per_min"])
    print("Curve sample:", results["curve"][:10])

    processed_dir = "output_data/processed"
    write_processed_outputs(results, processed_dir)