import os
import csv
import argparse
import numpy as np
import matplotlib.pyplot as plt

def read_summary_csv(path: str) -> dict:
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        row = next(reader, None)
        return row or {}

def read_curve_csv(path: str):
    times, occ = [], []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            times.append(float(row["time"]))
            occ.append(int(float(row["cars_on_campus"])))
    return np.array(times), np.array(occ)

def read_heatmap_csv(path: str):
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)  # ["time", road1, road2, ...]
        roads = header[1:]
        times = []
        cars_per_100_m = []
        for row in reader:
            times.append(float(row[0]))
            cars_per_100_m.append([float(x) for x in row[1:]])
            #for i in range(len(cars_per_100_m[0])):
             #   if cars_per_100_m[0][i] > MAX_CARS_PER_100_M:
              #      cars_per_100_m[0][i] = MAX_CARS_PER_100_M
            #for i in cars_per_100_m[0]:
             #   assert i <= MAX_CARS_PER_100_M, f"Value {i} exceeds max {MAX_CARS_PER_100_M}"
    M = np.array(cars_per_100_m)
    return np.array(times), roads, M

def write_summary_txt(summary_dict: dict, out_path: str):
    def g(k): return summary_dict.get(k, "")
    lines = [
        "=== Simulation Summary ===",
        f"Total sim time: {g('total_sim_time')}",
        f"Vehicles exited campus: {g('exited_count')}",
        f"Vehicles with lot-based time: {g('lot_based_count')}",
        f"Avg evac from t=0: {g('avg_from_t0')}",
        f"Avg evac from leaving lot: {g('avg_from_lot')}",
        f"Cars/min exiting campus: {g('cars_per_min')}",
    ]
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

def plot_evac_curve(times, occ, summary_dict, out_path: str):
    plt.figure()
    plt.plot(times, occ)
    plt.xlabel("Time (s)")
    plt.ylabel("Total Cars Driving on Campus")
    title = "Evacuation Curve"

    avg0 = summary_dict.get("avg_from_t0", "")
    avglot = summary_dict.get("avg_from_lot", "")
    if avg0 or avglot:
        title += f"\nAvg(t=0)={avg0}  Avg(from lot)={avglot}"
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()

def plot_heatmap(times, roads, M, out_path: str):
    # M is (T, R); roads on Y (rows), time on X (cols) by transposing.
    # Scale figure height so every road label has ~0.35 inches of space.
    fig_h = max(6, len(roads) * 0.35)
    plt.figure(figsize=(12, fig_h))
    plt.imshow(M.T, aspect="auto", origin="lower", cmap="plasma", vmax=20)

    plt.xlabel("Time (s)")
    plt.ylabel("Roads")
    plt.title("Campus Evacuation Heatmap")
    plt.colorbar(label="Vehicles per 100 m")

    plt.yticks(range(len(roads)), roads, fontsize=7)

    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("processed_dir", help="Path to scenario results folder (e.g. results/scenario_01)")
    ap.add_argument("--summary", default="summary.csv")
    ap.add_argument("--curve", default="evac_curve.csv")
    ap.add_argument("--heat", default="heatmap_matrix.csv")
    args = ap.parse_args()

    processed_dir = args.processed_dir
    summary_csv = os.path.join(processed_dir, args.summary)
    curve_csv = os.path.join(processed_dir, args.curve)
    heat_csv = os.path.join(processed_dir, args.heat)

    if not os.path.exists(summary_csv):
        raise FileNotFoundError(summary_csv)
    if not os.path.exists(curve_csv):
        raise FileNotFoundError(curve_csv)
    if not os.path.exists(heat_csv):
        raise FileNotFoundError(heat_csv)

    summary = read_summary_csv(summary_csv)
    times, occ = read_curve_csv(curve_csv)
    ht_times, roads, M = read_heatmap_csv(heat_csv)

    # Outputs
    summary_txt = os.path.join(processed_dir, "summary.txt")
    evac_png = os.path.join(processed_dir, "evac_curve.png")
    heat_png = os.path.join(processed_dir, "heatmap_matrix.png")

    write_summary_txt(summary, summary_txt)
    plot_evac_curve(times, occ, summary, evac_png)
    plot_heatmap(ht_times, roads, M, heat_png)

    print("Wrote:")
    print(" -", summary_txt)
    print(" -", evac_png)
    print(" -", heat_png)

if __name__ == "__main__":
    main()
