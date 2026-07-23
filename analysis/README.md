# Analysis pipeline (DEVS / Cadmium)

Charts match the MARS CarletonDrivingBox set where Cadmium logs support them.

## Packages

```bash
pip install numpy pandas matplotlib geopandas shapely pyproj fiona
```

## One scenario (from repo root)

```bash
mkdir -p results/scenario_01
./bin/campus_evacuation \
  -i input_data/parking_lot_schedules/scenario_01.csv \
  -o results/scenario_01/scenario_01_log.csv

python analysis/data_analysis.py results/scenario_01/scenario_01_log.csv
python analysis/visualize_processed.py results/scenario_01
```

`data_analysis.py` infers the schedule from `scenario_XX` in the log path when `--schedule` is omitted.

## Charts written to `results/scenario_XX/`

| File | Title |
|------|--------|
| `summary.png` | Deployment vs completion |
| `evac_curve.png` | Evacuation curve — cars that have not yet left campus |
| `trip_time_stats.png` | Travel-time summary |
| `trip_time_hist.png` | Travel-time distribution (to leave campus, not destination) |
| `clearance_by_lot.png` | Clearance time by lot (last car to leave university) |
| `completion_by_lot.png` | Per-lot completion (scheduled vs campus exits detected) |
| `exit_usage.png` | Campus exit usage |
| `heatmap_matrix.png` | Campus Evacuation Heatmap |

Also: `summary.csv`, `summary.txt`, `evac_curve.csv`, `heatmap_matrix.csv`, `campus_exits.csv`, `lot_exit_stats.csv`, `exit_usage.csv`, `metrics.json`.

## Notebook

Open `analyze_scenario.ipynb`, set `SCENARIO` to 1–10, optionally `RUN_SIMULATION = True`, then run all cells. Scenarios 7–10 automatically pass `--scenario`.

## Scenario 07 (Raven emergency)

```bash
mkdir -p results/scenario_07
./bin/campus_evacuation --scenario scenario_07 \
  -o results/scenario_07/scenario_07_log.csv

python analysis/data_analysis.py results/scenario_07/scenario_07_log.csv
python analysis/visualize_processed.py results/scenario_07
```

Uses `carleton_university_campus_scenario_07.hpp` (adds `r28`), `scenario_07_bronson.csv` OD, and `scenario_07_routing_overrides.csv` so P3/P4 prefer the Raven→Bronson emergency gate. Exit usage labels that gate as **Raven Rd emergency**.

## Scenario 08 (Bronson UD blocked)

```bash
mkdir -p results/scenario_08
./bin/campus_evacuation --scenario scenario_08 \
  -o results/scenario_08/scenario_08_log.csv

python analysis/data_analysis.py results/scenario_08/scenario_08_log.csv
python analysis/visualize_processed.py results/scenario_08
```

Uses `carleton_university_campus_scenario_08.hpp` (no `r24` Roundabout→Bronson UD; Stadium Way open; no `r28`), `scenario_08_colonel_by.csv` OD, and `scenario_08.json` exit list (Colonel By + Stadium Way + P3 Raven→Bronson; no Bronson UD / r28).

## Scenario 09 (s08 + Raven emergency)

```bash
mkdir -p results/scenario_09
./bin/campus_evacuation --scenario scenario_09 \
  -o results/scenario_09/scenario_09_log.csv

python analysis/data_analysis.py results/scenario_09/scenario_09_log.csv
python analysis/visualize_processed.py results/scenario_09
```

Uses `carleton_university_campus_scenario_09.hpp` (s08 topology: no `r24`; plus s07 `r28` + `IntersectionWithOverrides` at Raven), `scenario_09_emergency_stadium.csv` OD (s08 base + P3/P4 Raven preference), and `scenario_09_routing_overrides.csv`. Exits: emergency + Stadium Way + Colonel By (no Bronson UD).

## Scenario 10 (baseline + P6 → Colonel By)

```bash
mkdir -p results/scenario_10
./bin/campus_evacuation --scenario scenario_10 \
  -o results/scenario_10/scenario_10_log.csv

python analysis/data_analysis.py results/scenario_10/scenario_10_log.csv
python analysis/visualize_processed.py results/scenario_10
```

Uses baseline `carleton_university_campus.hpp` topology and schedule pattern (immediate dump like s01). Only change: `scenario_10_p6_colonel_by.csv` sends all P6 FLOW toward Library Rd / Colonel By (not NE/Stadium). Does not edit `simple_poll_results.csv`.

## Batch

```bash
bash run_scenarios.sh
```

Runs scenarios 01–10 (07–10 via `--scenario`).
