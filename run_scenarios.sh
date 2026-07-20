#!/bin/bash
#
# Runs all scenarios as a batch.
# Each scenario writes to results/scenario_XX/ (log + processed CSVs + charts).

declare -a scenarios=(
    "scenario_01"
    "scenario_02"
    "scenario_03"
    "scenario_04"
    "scenario_05"
    "scenario_06"
)

for s in "${scenarios[@]}"; do
    out_dir="results/${s}"
    mkdir -p "${out_dir}"
    log="${out_dir}/${s}_log.csv"
    ./bin/campus_evacuation -i "input_data/parking_lot_schedules/${s}.csv" -o "${log}"
    python analysis/data_analysis.py "${log}"
    python analysis/visualize_processed.py "${out_dir}"
done

# Scenario 07: P3 Bronson exit + P4 emergency link r28
s="scenario_07"
out_dir="results/${s}"
mkdir -p "${out_dir}"
log="${out_dir}/${s}_log.csv"
./bin/campus_evacuation --scenario scenario_07 -o "${log}"
python analysis/data_analysis.py "${log}" --scenario-manifest input_data/scenarios/scenario_07.json
python analysis/visualize_processed.py "${out_dir}"
