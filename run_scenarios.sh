# !/bin/sh
#
# Runs all scenarios as a batch.

declare -a scenarios=(
    "scenario_01"
    "scenario_02"
    "scenario_03"
    "scenario_04"
    "scenario_05"
    "scenario_06"
)   

for s in "${scenarios[@]}"; do
    ./bin/campus_evacuation -i input_data/parking_lot_schedules/${s}.csv -o output_data/raw/${s}_log.csv
    python analysis/data_analysis.py output_data/raw/${s}_log.csv
    cp -v output_data/processed/heatmap_matrix.csv output_data/processed/${s}_heatmap_matrix.csv
    python analysis/visualize_processed.py output_data/processed
    cp -v output_data/processed/heatmap_matrix.png output_data/processed/${s}_heatmap.png
    done
