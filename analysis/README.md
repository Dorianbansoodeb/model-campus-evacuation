# General python package installations
pip install numpy pandas matplotlib geopandas shapely pyproj fiona contextily


# Summary in the Terminal
To get the summary output manually, run
python analysis/data_analysis.py results/scenario_01/scenario_01_log.csv
in the terminal.

Processed CSVs are written next to the log file (same folder).

# Generate Visuals
To get the final visuals for a scenario, run
python analysis/visualize_processed.py results/scenario_01
in the terminal.

# Generate mp4
Ensure you are in the analysis folder (cd analysis)

Install ffmpeg:
sudo apt update
sudo apt install -y ffmpeg

run 
pyhton map_roads.py
in the terminal.
