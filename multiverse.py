#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# To read through this code file, start at line 398
"""
Created on Mon Nov  1 14:45:59 2021

@author: grahamseasons
"""
# StdLib Imports:
import argparse
import json
import os
import pickle
import re
import subprocess
import sys
import time
# Specific Imports:
from math import ceil
from os.path import join as opj
# OG Comment from GSeasons: from multiverse.gui.gui import MultiverseConfig #Mah#since we are not using GUI this needs to be commented out otherwise i get a error on a library that is not installed originally on my cluster
# OG Comment from GSeasons: import numpy as np

# Identify the directory path of this module file:
dir = os.path.dirname(os.path.abspath(__file__))

# TODO: Line 28 - parse function
def parse(start):
    """
    This function converts arguments given on the command line using an
    ArgumentParser object, so `args` essentially becomes a list of the 
    command line flag options [c='', r='', rr='', d='', o=''] and the 
    arguments that match these flags from the list of command line
    arguments are saved to the list. If the flag options are not given
    on the comand line, the defaults are saved instead, as provided 
    here:
    [c=False, r=False, rr=False, d=None, o=None]
    """
    # Store the output from ArgumentParser's `parse_args` method:
    args = start.parse_args()
    # `run_now` default is set to False:
    run_now = False
    # OG Comment from GSeasons: process_mode = 'MultiProc' #(this needs to be 
    # changed to SLURM in cluster)
    # `process_mode` default is set to 'SLURM':
    process_mode = 'SLURM' #OG Comment from MSoleymani: Mah
    # Check to see if `--config` flag OR `--run` flag has been given on 
    # the command line:
    if args.config or args.run:
        # Run some checks!
        # If a data directory has not been provided AND `--config` has 
        # not been flagged:
        if args.data == None and not args.config:
            # Essentially throw an error and exit after notifying the 
            # user that either a valid data directory must be set, or 
            # they must run the program in `--config` mode:
            print('Either -d must be set, or -c must be used')
            sys.exit()
        # If a data directory HAS been provided AND `--run` HAS been 
        # flagged, check to see if the given data directory actually 
        # exists:
        elif args.data != None and args.run and not os.path.isdir(args.data):
            # Essentially throw an error and exit after notifying the 
            # user that the data directory does not exist:
            print('The specified data path does not exist')
            sys.exit()

        # Now check to see if there is no output directory given AND
        # `--config` has NOT been flagged:
        if args.out == None and not args.config:
            # Essentially throw an error and exit after notifying the 
            # user that either a valid output directory must be set, or they 
            # must run the program in `--config` mode:
            print('Either -o must be set, or -c must be used')
            sys.exit()
        # If an outdput directory HAS been provided AND `--run` has been 
        # flagged, check to see if the given output directory exists:
        elif args.out != None and args.run and not os.path.isdir(args.out):
            # Notify the user that the given output directory does not
            # exist, but that it will be created:
            print('The specified data path does not exist')
            print('Creating directory at specified path')
            os.makedirs(args.out)

        # If we made it past the checks, check to see if `--run` was 
        # flagged:
        if args.run:
            # Check to see if there is a `multiverse/configuration`
            # directory in the current code file's directory:
            if os.path.isdir(os.path.join(dir, 'multiverse', 'configuration')):
                # Check to see if the general_configuration.pkl and
                # multiverse_configuration.pkl files exist in this
                # directory:
                if os.path.isfile(os.path.join(dir, 'multiverse', 'configuration', 'multiverse_configuration.pkl')) and os.path.isfile(os.path.join(dir, 'multiverse', 'configuration', 'general_configuration.pkl')):
                    # The program is now ready to run, so update 
                    # `run_now` to True:
                    run_now = True

                    # Note: general_configuration.pkl is simply a 
                    # dictionary of configuration values.
                    # Open the general_configuration.pkl file and load
                    # it into the `configure` variable:
                    with open(opj(dir, 'multiverse', 'configuration', 'general_configuration.pkl'), 'rb') as f:
                        configure = pickle.load(f)

                    # Update `process_mode` to the configured processing
                    # mode:
                    process_mode = configure['processing']
                    # Notify the user that the pickle file was found
                    # and the general configuration settings have been
                    # loaded:
                    print('Using previously defined configuration file')

            # If something is missing and `run_now` has not been updated
            # yet:
            if not run_now:
                # Notify the user that the configuration pickle files are
                # missing:
                print('Configuration files missing, running configure')
                # Launch configuration module instead, with the provided 
                # rerun, data directory, and output directory options
                # and store in `config`:
                config = MultiverseConfig(args.rerun, args.data, args.out)
                # Update `run_now` with the new `config` object:
                run_now = config.run_now
                # Update `process_mode` with the new `config` object:
                process_mode = config.configure['processing']
                # Update `configure` with the new `config` object:
                configure = config.configure
                
        # If the `--config` option was flagged:
        if args.config:
            # Launch configuration module with the provided rerun, data 
            # directory, and output directory options, and store in 
            # `config`:
            config = MultiverseConfig(args.rerun, args.data, args.out)
            # Update `run_now` with the new `config` object:
            run_now = config.run_now
            # Update `process_mode` with the new `config` object:
            process_mode = config.configure['processing']
            # Update `configure` with the new `config` object:
            configure = config.configure
    else:
        # User did not specify `--run` OR `--config`, and at least one 
        # must be set. Notify the user of the mistake, print the help 
        # options from the `start` ArgumentParser object, and exit:
        print('Either the --run (-r) or --config (-c) flag must be specified\n')
        start.print_help()
        sys.exit()

    # Return `run_now` (boolean), `args` (list of provided arguments), 
    # `process_mode` (string), and `configure` (dictionary of options): 
    return run_now, args, process_mode, configure
    # TODO: Return to line 176

# TODO: line 157 - main method
def main():
    # Create and ArgumentParser object and assign to `start` to accept
    # command line arguments:
    start = argparse.ArgumentParser()
    # Add the specific command line flags `-c`, `-r`, `-rr`, `-d`, and
    # `-o` and the actions they trigger:
    start.add_argument('-c', '--config', action='store_true', help='configure multiverse parameter file')
    start.add_argument('-r', '--run', action='store_true', help='run multiverse analysis')
    start.add_argument('-rr', '--rerun', action='store_true', help='re-run multiverse analysis using saved population files')
    start.add_argument('-d', '--data', type=str, metavar="DATA_DIR", action='store', help='path to BIDS formatted data directory')
    start.add_argument('-o', '--out', type=str, metavar="OUT_DIR", action='store', help='path to store outputs')

    # Variables `run_now`, `args`, `process_mode`, and `config` are set 
    # using a call to the `parse` function. 
    # TODO: Jump to line 28 - parse function
    run_now, args, process_mode, config = parse(start)

    # TODO: Line 176
    # If running:
    if run_now:
        # Create the code directory path from the current file's 
        # directory, concatenated with 'multiverse':
        code_dir = os.path.join(dir, 'multiverse')

        # OG Comment from GSeasons: IF TEMPLATE FLOW FAILS, UNCOMMENT LINES 82-84, AND COMMENT LINES 79-80
        # Note: This comment does not make sense anymore in the current 
        # context of the code. The original code file lines "82-84" refers
        # to the OG comment lines themselves, and "79-80" would have 
        # referred to what is now line 175 above, with `if run_now:`.
        
# =============================================================================
        # `volumes` is creating a list of directory paths for 
        #  bind-mounting in a container:
        #    * `code_dir` maps to `/code/multiverse` in the container 
        #    * `args.data` maps to `/data` in the container
        #    * `args.out` maps to `/scratch_dir` in the container
        #    * `code_dir/plugins_base.py' maps to `/opt/miniconda-latest/
        #       envs/multiverse/lib/python3.8/site-packages/nipype/
        #       pipeline/plugins/base.py`
        #    * `code_dir/templateflow` maps to `/home/multiverse/.cache/
        #       templateflow`
        volumes = ['{code}:/code/multiverse'.format(code=code_dir), '{data}:/data'.format(data=args.data), 
                   '{work_dir}:/scratch_dir'.format(work_dir=args.out), '{code}/plugins_base.py:/opt/miniconda-latest/envs/multiverse/lib/python3.8/site-packages/nipype/pipeline/plugins/base.py'.format(code=code_dir),
                   '{code}/templateflow:/home/multiverse/.cache/templateflow'.format(code=code_dir)]
        # If not using SLURM, assume use of local machine.
        if process_mode != 'SLURM':
            # Assume machine is Linux or Windows-based and import Docker:
            try:
                import docker
            except:
                # Note: `call` is a deprecated function and should be 
                # replaced by `run`.
                # If importing Docker doesn't work because it is not 
                # installed, run `pip install docker` and then re-attempt
                # to import Docker:
                subprocess.call(['pip', 'install', 'docker'])
                import docker
            # Try to start Docker:
            try:
                # Instantiate a Docker client for communicating with a 
                # Docker server:
                client = docker.from_env()
                # Parameters for docker.from_env() explained:
                # version(str): The version of the API to use. 
                #               Default: "1.35".
                # timeout(int): Default timeout for API calls, in seconds.
                # max_pool_size(int): The maximum number of connections
                #                     to save in the pool.
                # environment(dict): The environment to read environment
                #                    variables from.
                #                    Default: the value of os.environ.
                # credstore_env(dict): Override environment variables
                #                      when calling the credential store
                #                      process.
                # use_ssh_client(bool): If set to True, an ssh connection
                #                       is made via shelling out to the
                #                       ssh client. Ensure the ssh client
                #                       is installed and configured on
                #                       the host.
            except:
                # If that doesn't work, assume machine is macOS-based
                # and run 'open -a Docker'. This opens a Docker GUI
                # using a macOS call.
                subprocess.call(['open', '-a', 'Docker'])
                # Wait 30 seconds to see if the Docker Desktop GUI opens:
                sleeping = 0
                # Note: The double negatives in this `while` loop muddy the meaning.
                while not subprocess.call(['! docker info > /dev/null 2>&1'], shell=True) and sleeping < 30:
                    time.sleep(1)
                    sleeping += 1

                # Once `sleeping` reaches 30 seconds, notify user that
                # there is a problem and exit:
                if sleeping == 30:
                    print('Could not open Docker Desktop, please ensure it is installed and try again.')
                    exit()
                    
            # Once everything succeeds:
            try:
                # Notify the user that the container is starting:
                print('Running Container')
                # Use the instantiated client to create an object
                # (client.containers) for managing containers on the
                # server.
                # Parameters for
                # client.containers.run(image, command=None, **kwargs)
                # explained:
                #     'gseasons/multiverse:cluster': Use this image.
                #     detach=True: Run container in the background and
                #                  return a container object.
                #     tty=True: Allocate a pseudo-TTY.
                #     stdin_open=True: Keep STDIN open even if not
                #                      attached.
                #     working_dir='/scratch_dir': Path to the working
                #                                 directory.
                #     volumes=volumes: A list of strings from which each
                #                      one of its elements specifies a
                #                      mount volume.
                #     user='root': User or UID to run commands as inside
                #                  the container.
                container = client.containers.run('gseasons/multiverse:cluster', detach=True, tty=True, stdin_open=True, working_dir='/scratch_dir', volumes=volumes, user='root')
                # Start the container:
                container.start()
                # Run a bash terminal in the container.
                # Commands to run in said bash shell:
                #     source activate multiverse 
                #     (this is the name of the conda environment built 
                #      by the def file)
                #     python /code/multiverse/run_multiverse.py {0} 
                #     (run the run_multiverse.py script with the rerun 
                #      option inserted)
                container.exec_run('sudo /bin/bash -c "source activate multiverse ; python /code/multiverse/run_multiverse.py {0}"'.format(args.rerun))
                # Stop the container:
                container.stop()
                # Remove the container:
                container.remove()
                # Delete unused volumes and return a dictionary containing 
                # a list of the deleted volume names and the amount of 
                # disk space reclaimed in bytes:
                client.volumes.prune()

            # If the container image is not found:
            except docker.errors.ImageNotFound:
                print("Image not found, pulling from docker")
                # Parameters for client.api.pull() explained:
                # Pulls an image; similar to docker pull command.
                #     repository: 'gseasons/multiverse'
                #     stream: Stream the output as a generator. Make sure 
                #             to consume the generator, otherwise pull 
                #             might get cancelled.
                #     decode: Decode the JSON data from the server into 
                #             dicts. Only applies with stream=True.
                for line in client.api.pull('gseasons/multiverse', stream=True, decode=True):
                    # Print the status of pulling the image from Docker:
                    print(json.dumps(line, indent=4))

                # Run commands as detailed above once image is pulled:
                container = client.containers.run('gseasons/multiverse:cluster', detach=True, tty=True, stdin_open=True, working_dir='/scratch_dir', volumes=volumes)
                container.start()
                container.exec_run('/bin/bash -c "source activate multiverse ; python /code/multiverse/run_multiverse.py {0}"'.format(args.rerun))
                container.stop()
                container.remove()
                client.volumes.prune()
        # Else, i.e. if using 'SLURM':
        else:
            # If the account is set to 'def-' clear it.
            # Note: Unclear if this is to prevent a partial account from 
            # being submitted.
            if config['account'] == 'def-':
                config['account'] = ''

            # If 'SLURM' and `num_generations` not in the config file:
            if config['processing'] == 'SLURM' and 'num_generations' not in config:
                # Set nodes to 1 and take number of cpu_nodes and set as 
                # ntasks:
                config['nodes'] = '1'
                config['ntasks'] = config['cpu_node']

                # Calculate the time as total seconds to divide among 
                # CPUs:
                split_ = re.split('-|:', config['time'])
                time_s = 0
                for k, sp in enumerate(split_):
                    if not k:
                        time_s += int(sp) * 24 * 3600
                    elif k == 1:
                        time_s += int(sp) * 3600
                    elif k == 2:
                        time_s += int(sp) * 60
                    else:
                        time_s += int(sp)

                # Divide the total time in seconds by the total number 
                # of nodes, times the total number of batches, and
                # reassign to `time_s` in seconds:
                time_s = time_s / int(ceil(int(config['cpu_node']) * config['batches']))
                # Recalculate the days, hours, minutes, and seconds 
                # required based on this new time:
                days = int(time_s / (24 * 3600))
                hours = max(int(time_s / 3600) - days * 24, 0)
                minutes = max(int(time_s / 60) - days * 24 * 60 - hours * 60, 0)
                seconds = max(int(time_s) - days * 24 * 3600 - hours * 3600 - minutes * 60, 0)

                # Reset `config['time']` to this new amount:
                config['time'] =  str(days) + '-' + str(hours) + ':' + str(minutes) + ':' + str(seconds)
                # Calculate the memory required based on the requested
                # memory, multiplied by the number of cpu nodes
                # requested, and reset the `config['memory']` value:
                config['mem'] = str(int(ceil(float(config['mem']) * int(config['cpu_node'])))) + "G"

                # Notify the user of the new time:
                print("config['time']: ", config['time'])
                # Create a command to run the `intermediate.sh` file 
                # with the data directory path, the output directory path, 
                # the rerun flag, the number of nodes, ntasks, account, 
                # time, and memory as parameters:
                # (Remember that this is for a SLURM job!)
                cmd = [f"{code_dir}/configuration/intermediate.sh", args.data, args.out, str(args.rerun), config['nodes'], config['ntasks'], config['account'], config['time'], config['mem']]
                # Notify the user the command is running:
                print("Running command:", " ".join(cmd))
                # Try running the command as a subprocess; with 
                # `check=True`, a `CalledProcessError` will be raised
                # if the process exits with a non-zero exit code:
                try:
                    result = subprocess.run(cmd, check=True)
                    # Notify the user the script ran successfully:
                    print("Script ran successfully.")
                except subprocess.CalledProcessError as e:
                    # If an error was raised, provide the returncode to 
                    # the user:
                    print(f"Script failed with return code {e.returncode}")
            else:
                # It's a 'SLURM' job AND the `num_generations` was set in  
                # the configuration file.
                # Use `sbatch` to submit a job using the `multiverse.sh` 
                # script.
                # Run `sbatch` command, with --nodes, --ntasks, 
                # --account, --time, --mem, multiverse.sh, data path, 
                # output path, and rerun flag:
                subprocess.call(['sbatch', '--nodes={0}'.format(config['nodes']), '--ntasks={0}'.format([config['ntasks']]), '--account={0}'.format(config['account']), '--time={0}'.format(config['time']), '--mem={0}'.format(config['mem']), 'multiverse/configuration/multiverse.sh', args.data, args.out, str(args.rerun)])
            
# TODO: line 399 - Start here
if __name__ == "__main__":
    # TODO: Jump to line 157 - main method
    main()
