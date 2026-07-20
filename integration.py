import os.path
import subprocess
import csv
import sys

from dotenv import load_dotenv
from paramiko import SSHClient
from scp import SCPClient

PARKING_LOT_SCHEDULES_DIR = 'input_data/parking_lot_schedules/'
DEFAULT_PARKING_LOT_SCHEDULE = PARKING_LOT_SCHEDULES_DIR + 'default.csv'
RESULTS_DIR = 'results/'
PARKING_LOT_ID_INDEX = 0
DELAY_INDEX = 1
YES = 'y'

def name_scenario():
    name = input('What would you like to name the scenario?\n')
    name = name.replace(' ', '_')
    name = name.lower()
    return name

def configure_scenario(scenario_name):
    with open(DEFAULT_PARKING_LOT_SCHEDULE, newline='') as f:
        default_config = csv.reader(f, delimiter=',') 
        parking_lot_ids = list()
        col_names = list()
        config = list()
        for row in default_config:
            if len(col_names) == 0:
                col_names.append(row)
            else:
                parking_lot_ids.append(row[PARKING_LOT_ID_INDEX])
                config.append(row)

    cmd = YES
    while (cmd == YES):
        # Display current configuration
        config_header = '\t\t'.join(['ID', 'Delay', 'Period', 'Capacity'])
        print(config_header)
        for row in config:
            print('\t\t'.join(row))

        cmd = input(f'\nWould you like to change the configuration? [{YES}/n]\n')
        if cmd == YES:
            parking_lot_id = input(f'Which parking lot configuration would you like to change? {parking_lot_ids}\n')
            parking_lot_id = parking_lot_id.upper()
            if parking_lot_id in parking_lot_ids:
                delay_in_seconds = input(f'For {parking_lot_id}, how much should the evacuation be delayed? (seconds)\n')
                for row in config:
                    if row[PARKING_LOT_ID_INDEX] == parking_lot_id:
                        row[DELAY_INDEX] = delay_in_seconds
            else:
                print('Invalid parking lot ID')
        os.system('clear')

    config_filepath = PARKING_LOT_SCHEDULES_DIR + scenario_name +'.csv'
    with open(config_filepath, 'w', newline='') as f:
        writer = csv.writer(f, delimiter=',')
        writer.writerow(col_names[0])
        for row in config:
            writer.writerow(row)
        print(f'Configuration saved: {config_filepath}\n')

def run_scenario(scenario_name):
    cmd = input(f'Would you like to run a simulation of your scenario? [{YES}/n]\n')
    if cmd == YES:
        parking_lot_schedule_fp = PARKING_LOT_SCHEDULES_DIR + scenario_name + '.csv'
        out_dir = RESULTS_DIR + scenario_name + '/'
        os.makedirs(out_dir, exist_ok=True)
        log_fp = out_dir + scenario_name + '_log.csv'
        sim_model_fp = '/bin/campus_evacuation'

        if os.path.isfile(sim_model_fp):
            # Run simulation locally
            args = (f'.{sim_model_fp}', '-i', parking_lot_schedule_fp, '-o', log_fp)
            p = subprocess.run(args) 
            p.check_returncode() # Throws error if return code non-zero
        else:
            # Run simulation remotely
            #
            # Setup remote env
            username = os.getenv('REMOTE_SIM_USERNAME')
            hostname = os.getenv('REMOTE_SIM_HOSTNAME')
            cadmium = os.getenv('REMOTE_SIM_CADMIUM')
            remote_project_fp = os.getenv('REMOTE_SIM_PROJECT_FP')
            env = {'CADMIUM': cadmium}
            remote_parking_lot_schedule_fp = f'{remote_project_fp}/{parking_lot_schedule_fp}'
            remote_log_fp = f'{remote_project_fp}/{log_fp}'

            ssh = SSHClient()
            ssh.load_system_host_keys()
            ssh.connect(hostname, username=username)

            # Define progress callback that prints the current percentage completed for the file
            def progress(filename, size, sent):
                sys.stdout.write("%s's progress: %.2f%%   \r" % (filename, float(sent)/float(size)*100) )
            scp = SCPClient(ssh.get_transport(), progress=progress)

            # Copy files and run simulation remotely
            scp.put(parking_lot_schedule_fp, remote_parking_lot_schedule_fp)
            stdin, stdout, stderr = ssh.exec_command(f'cd {remote_project_fp} && .{sim_model_fp} -i {parking_lot_schedule_fp} -o {log_fp}', environment=env)
            assert stderr.channel.recv_exit_status() == 0, 'Remote simulation failed'
            scp.get(remote_log_fp, log_fp)

            # Cleanup remote server
            stdin, stdout, stderr = ssh.exec_command(f'rm {remote_parking_lot_schedule_fp}')
            assert stderr.channel.recv_exit_status() == 0, f'Cleanup failed: {stderr.readlines()}'
            stdin, stdout, stderr = ssh.exec_command(f'rm {remote_log_fp}')
            assert stderr.channel.recv_exit_status() == 0, f'Cleanup failed: {stderr.readlines()}'


        print(f'Simulation complete: {log_fp}\n')

        analyze_scenario(scenario_name)

def analyze_scenario(scenario_name):
    out_dir = RESULTS_DIR + scenario_name + '/'
    log_fp = out_dir + scenario_name + '_log.csv'
    heatmap_fp = out_dir + 'heatmap_matrix.png'

    args = ('python', 'analysis/data_analysis.py', log_fp)
    p = subprocess.run(args)
    p.check_returncode()

    args = ('python', 'analysis/visualize_processed.py', out_dir)
    p = subprocess.run(args)
    p.check_returncode()

    import webbrowser, os
    webbrowser.open('file://' + os.path.realpath(heatmap_fp)) 

    """
    cmd = input(f'Would you like to create an animation of your simulation? [{YES}/n]\n')
    if cmd == YES:
        print('Creating animation...')
        args = ('python', 'analysis/create_heatmap_animation.py', '-i', scenario_name + '_heatmap_matrix.csv')
        p = subprocess.run(args) 
    """

def execute_script():
    load_dotenv()
    cmd = YES
    while(cmd == YES):
        os.system('clear')
        name = name_scenario()
        configure_scenario(name)
        run_scenario(name)
        cmd = input(f'Would you like to create another scenario? [{YES}/n]')

if __name__ == '__main__':
    execute_script()
