#!/bin/bash
#
# Runs the configured DEVS scenarios as a batch.
# Each scenario writes to results/scenario_XX/ (log + processed CSVs + charts).
# Scenarios 07–10 use --scenario (dedicated coupled model and/or OD).
# Scenarios 01–06 keep the baseline model + simple_poll_results.csv.

declare -a scenarios=(
    "scenario_01"
    "scenario_02"
    "scenario_03"
    "scenario_04"
    "scenario_05"
    "scenario_06"
    "scenario_07"
    "scenario_08"
    "scenario_09"
    "scenario_10"
)

for s in "${scenarios[@]}"; do
    out_dir="results/${s}"
    mkdir -p "${out_dir}"
    log="${out_dir}/${s}_log.csv"
    if [ "${s}" = "scenario_07" ] || [ "${s}" = "scenario_08" ] || \
       [ "${s}" = "scenario_09" ] || [ "${s}" = "scenario_10" ]; then
        ./bin/campus_evacuation --scenario "${s}" -o "${log}"
    else
        ./bin/campus_evacuation -i "input_data/parking_lot_schedules/${s}.csv" -o "${log}"
    fi
    python analysis/data_analysis.py "${log}" --schedule "input_data/parking_lot_schedules/${s}.csv"
    python analysis/visualize_processed.py "${out_dir}"
done
