"""Render MARS-aligned charts from processed DEVS scenario CSVs."""
from __future__ import annotations

import argparse
import csv
import os

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

LOT_ORDER = ["P1", "P2", "P3", "P4", "P5", "P6", "P7"]
LOT_MARKER_COLORS = {
    "P1": "#e41a1c",
    "P2": "#377eb8",
    "P3": "#4daf4a",
    "P4": "#984ea3",
    "P5": "#ff7f00",
    "P6": "#a65628",
    "P7": "#f781bf",
}
CAMPUS_EXIT_ORDER = [
    "Colonel By",
    "Bronson Ave & University Dr",
    "Stadium Way",
    "Raven Rd emergency",
    "other",
]
BASELINE_TARGET = 3200


def read_summary_csv(path: str) -> dict:
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        row = next(reader, None)
        return row or {}


def read_curve_csv(path: str):
    times, occ, spawned, exited = [], [], [], []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        # Support legacy (time, cars_on_campus) and MARS (time_s, ...)
        t_key = "time_s" if "time_s" in fields else "time"
        for row in reader:
            times.append(float(row[t_key]))
            occ.append(float(row["cars_on_campus"]))
            if "cumulative_spawned" in row and row["cumulative_spawned"] != "":
                spawned.append(int(float(row["cumulative_spawned"])))
            if "cumulative_exited" in row and row["cumulative_exited"] != "":
                exited.append(int(float(row["cumulative_exited"])))
    return (
        np.array(times),
        np.array(occ),
        np.array(spawned) if spawned else None,
        np.array(exited) if exited else None,
    )


def read_heatmap_csv(path: str):
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        roads = header[1:]
        times = []
        cars_per_100_m = []
        for row in reader:
            times.append(float(row[0]))
            cars_per_100_m.append([float(x) for x in row[1:]])
    return np.array(times), roads, np.array(cars_per_100_m)


def read_lot_exit_stats(path: str) -> list[dict]:
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_exit_usage(path: str) -> dict[str, int]:
    usage = {name: 0 for name in CAMPUS_EXIT_ORDER}
    if not os.path.isfile(path):
        return usage
    with open(path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            name = row.get("exit_gate") or ""
            try:
                usage[name] = int(float(row.get("count") or 0))
            except ValueError:
                usage[name] = 0
    return usage


def read_travel_times(campus_exits_csv: str) -> list[float]:
    times: list[float] = []
    if not os.path.isfile(campus_exits_csv):
        return times
    with open(campus_exits_csv, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            val = row.get("drive_s")
            if val is None or val == "":
                continue
            try:
                times.append(float(val))
            except ValueError:
                continue
    return times


def write_summary_txt(summary_dict: dict, out_path: str):
    def g(k):
        return summary_dict.get(k, "")

    lines = [
        "=== Simulation Summary ===",
        f"Total sim time: {g('total_sim_time')}",
        f"Vehicles exited campus: {g('exited_count')}",
        f"Vehicles with lot-based time: {g('lot_based_count')}",
        f"Expected (schedule): {g('expected')}",
        f"Baseline target: {g('baseline_target')}",
        f"Avg evac from t=0: {g('avg_from_t0')}",
        f"Avg evac from leaving lot: {g('avg_from_lot')}",
        f"Median evac from t=0: {g('median_from_t0')}",
        f"Median evac from leaving lot: {g('median_from_lot')}",
        f"Cars/min exiting campus: {g('cars_per_min')}",
    ]
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _lot_clearance_items(lot_rows: list[dict]) -> list[tuple[str, float]]:
    items: list[tuple[str, float]] = []
    by_lot = {r.get("lot"): r for r in lot_rows}
    for lot in LOT_ORDER:
        row = by_lot.get(lot) or {}
        val = row.get("clearance_s")
        if val is None or val == "":
            continue
        try:
            t = float(val)
        except ValueError:
            continue
        if t > 0:
            items.append((lot, t))
    items.sort(key=lambda x: x[1])
    return items


def annotate_lot_clearances(ax, lot_rows: list[dict]) -> None:
    items = _lot_clearance_items(lot_rows)
    if not items:
        return
    ymin, ymax = ax.get_ylim()
    x0, x1 = ax.get_xlim()
    x_span = max(x1 - x0, 1.0)
    cluster_thresh = 0.035 * x_span
    level = 0
    prev_t: float | None = None
    for lot, t in items:
        if prev_t is not None and abs(t - prev_t) < cluster_thresh:
            level = (level + 1) % 4
        else:
            level = 0
        prev_t = t
        color = LOT_MARKER_COLORS.get(lot, "#555555")
        ax.axvline(t, color=color, linestyle="--", linewidth=1.0, alpha=0.8, zorder=3)
        y = ymin + (ymax - ymin) * (0.96 - 0.10 * level)
        ax.text(
            t,
            y,
            f"{lot} cleared",
            rotation=90,
            va="top",
            ha="right",
            fontsize=7,
            color=color,
            clip_on=True,
            zorder=4,
        )


def plot_summary(summary: dict, out_path: str):
    expected = int(float(summary.get("expected") or 0)) or BASELINE_TARGET
    baseline = int(float(summary.get("baseline_target") or BASELINE_TARGET))
    completed = int(float(summary.get("exited_count") or 0))
    plt.figure(figsize=(6, 4))
    plt.bar(
        ["Expected\n(schedule)", "Baseline\ntarget", "Completed\n(trips)"],
        [expected, baseline, completed],
        color=["#4c72b0", "#8172b2", "#c44e52"],
    )
    plt.ylabel("Vehicles")
    plt.title("Deployment vs completion")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def plot_evac_curve(times, occ, summary: dict, lot_rows: list[dict], out_path: str):
    if len(times) == 0:
        return
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.plot(times, occ, label="Left to evacuate", color="#4c72b0", linewidth=1.5)
    start_n = int(occ[0]) if len(occ) else 0
    end_n = int(occ[-1]) if len(occ) else 0
    baseline = int(float(summary.get("baseline_target") or BASELINE_TARGET))
    ax.set_ylim(0, max(baseline, start_n) * 1.02)
    annotate_lot_clearances(ax, lot_rows)

    avg_all = float(np.mean(occ)) if len(occ) else 0.0
    early = occ[times <= 60] if len(times) else occ
    avg_early = float(np.mean(early)) if len(early) else 0.0

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Cars left to evacuate")
    ax.set_title("Evacuation curve — cars that have not yet left campus")
    subtitle = (
        f"Start={start_n} (N0={baseline})   End={end_n}   "
        f"Avg (t≤60s)={avg_early:.2f}   Avg (all)={avg_all:.2f}"
        "   |   Dashed: lot cleared (last campus exit)"
    )
    fig.suptitle(subtitle, fontsize=8, y=0.98)
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def plot_trip_time_charts(summary: dict, travel_times: list[float], lot_rows: list[dict], out_dir: str):
    mean_drive = float(summary.get("avg_from_lot") or 0)
    median_drive = float(summary.get("median_from_lot") or 0)
    mean_t0 = float(summary.get("avg_from_t0") or 0)
    median_t0 = float(summary.get("median_from_t0") or 0)

    if travel_times:
        values = [mean_drive, median_drive, mean_t0, median_t0]
        colors = ["#4c72b0", "#4c72b0", "#55a868", "#55a868"]
        bar_labels = [
            "Mean\ndrive to exit",
            "Median\ndrive to exit",
            "Mean\ncampus exit",
            "Median\ncampus exit",
        ]
        plt.figure(figsize=(8, 4.8))
        bars = plt.bar(bar_labels, values, color=colors)
        plt.ylabel("Seconds")
        plt.title("Travel-time summary")
        plt.legend(
            handles=[
                Patch(
                    facecolor="#4c72b0",
                    label="Blue = drive time (spawn → leave university)",
                ),
                Patch(
                    facecolor="#55a868",
                    label="Green = leave-campus time (sim t=0 → leave university)",
                ),
            ],
            loc="upper left",
            fontsize=8,
        )
        for bar, val in zip(bars, values):
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{val:.0f}s",
                ha="center",
                va="bottom",
                fontsize=8,
            )
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "trip_time_stats.png"), dpi=200)
        plt.close()

        plt.figure(figsize=(8, 4.5))
        plt.hist(travel_times, bins=40, color="#4c72b0", edgecolor="white", linewidth=0.4)
        plt.axvline(
            mean_drive,
            color="#c44e52",
            linestyle="--",
            linewidth=1.5,
            label=f"Mean {mean_drive:.0f}s",
        )
        plt.axvline(
            median_drive,
            color="#8172b2",
            linestyle="-",
            linewidth=1.5,
            label=f"Median {median_drive:.0f}s",
        )
        plt.xlabel("Trip duration (s) — spawn to leave university")
        plt.ylabel("Trips")
        plt.title("Travel-time distribution (to leave campus, not destination)")
        plt.legend()
        plt.grid(True, axis="y", alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "trip_time_hist.png"), dpi=200)
        plt.close()

    clearance = []
    for lot in LOT_ORDER:
        row = next((r for r in lot_rows if r.get("lot") == lot), {})
        val = row.get("clearance_s")
        try:
            clearance.append(float(val) if val not in (None, "") else 0.0)
        except ValueError:
            clearance.append(0.0)
    plt.figure(figsize=(7, 4.2))
    bars = plt.bar(LOT_ORDER, clearance, color="#dd8452")
    plt.ylabel("Clearance time (s from t=0)")
    plt.xlabel("Parking lot")
    plt.title("Clearance time by lot (last car to leave university)")
    for bar, val in zip(bars, clearance):
        if val:
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{int(val)}",
                ha="center",
                va="bottom",
                fontsize=8,
            )
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "clearance_by_lot.png"), dpi=200)
    plt.close()


def plot_lot_completion_and_exits(lot_rows: list[dict], usage: dict[str, int], out_dir: str):
    scheduled = []
    completed = []
    for lot in LOT_ORDER:
        row = next((r for r in lot_rows if r.get("lot") == lot), {})
        scheduled.append(int(float(row.get("scheduled") or 0)))
        completed.append(int(float(row.get("completed") or 0)))

    x = list(range(len(LOT_ORDER)))
    width = 0.38
    plt.figure(figsize=(8, 4.5))
    b1 = plt.bar([i - width / 2 for i in x], scheduled, width, color="#4c72b0", label="Scheduled")
    b2 = plt.bar([i + width / 2 for i in x], completed, width, color="#c44e52", label="Completed")
    plt.xticks(x, LOT_ORDER)
    plt.ylabel("Vehicles")
    plt.xlabel("Parking lot")
    plt.title("Per-lot completion (scheduled vs campus exits detected)")
    plt.legend()
    for bars in (b1, b2):
        for bar in bars:
            h = bar.get_height()
            if h:
                plt.text(
                    bar.get_x() + bar.get_width() / 2,
                    h,
                    f"{int(h)}",
                    ha="center",
                    va="bottom",
                    fontsize=7,
                )
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "completion_by_lot.png"), dpi=200)
    plt.close()

    labels = [n for n in CAMPUS_EXIT_ORDER if n != "other"]
    if usage.get("other", 0):
        labels.append("other")
    values = [int(usage.get(name, 0)) for name in labels]
    short = {
        "Colonel By": "Colonel By",
        "Bronson Ave & University Dr": "Bronson\n(University Dr)",
        "Stadium Way": "Stadium Way",
        "Raven Rd emergency": "Raven Rd\nemergency",
        "other": "Other / unmatched",
    }
    plt.figure(figsize=(8, 4.5))
    bars = plt.bar([short.get(n, n) for n in labels], values, color="#8172b2")
    plt.ylabel("Campus exits")
    plt.title("Campus exit usage")
    for bar, val in zip(bars, values):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{val}",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "exit_usage.png"), dpi=200)
    plt.close()


def plot_heatmap(times, roads, M, out_path: str):
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
    lot_csv = os.path.join(processed_dir, "lot_exit_stats.csv")
    usage_csv = os.path.join(processed_dir, "exit_usage.csv")
    exits_csv = os.path.join(processed_dir, "campus_exits.csv")

    if not os.path.exists(summary_csv):
        raise FileNotFoundError(summary_csv)
    if not os.path.exists(curve_csv):
        raise FileNotFoundError(curve_csv)
    if not os.path.exists(heat_csv):
        raise FileNotFoundError(heat_csv)

    summary = read_summary_csv(summary_csv)
    times, occ, _spawned, _exited = read_curve_csv(curve_csv)
    ht_times, roads, M = read_heatmap_csv(heat_csv)
    lot_rows = read_lot_exit_stats(lot_csv)
    usage = read_exit_usage(usage_csv)
    travel_times = read_travel_times(exits_csv)

    write_summary_txt(summary, os.path.join(processed_dir, "summary.txt"))
    plot_summary(summary, os.path.join(processed_dir, "summary.png"))
    plot_evac_curve(times, occ, summary, lot_rows, os.path.join(processed_dir, "evac_curve.png"))
    plot_trip_time_charts(summary, travel_times, lot_rows, processed_dir)
    plot_lot_completion_and_exits(lot_rows, usage, processed_dir)
    plot_heatmap(ht_times, roads, M, os.path.join(processed_dir, "heatmap_matrix.png"))

    wrote = [
        "summary.txt",
        "summary.png",
        "evac_curve.png",
        "trip_time_stats.png",
        "trip_time_hist.png",
        "clearance_by_lot.png",
        "completion_by_lot.png",
        "exit_usage.png",
        "heatmap_matrix.png",
    ]
    print("Wrote:")
    for name in wrote:
        path = os.path.join(processed_dir, name)
        if os.path.isfile(path):
            print(" -", path)
        else:
            print(" - (skipped)", name)


if __name__ == "__main__":
    main()
