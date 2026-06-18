# This script creates a new general_configuration.pkl file for test runs

# Make sure to open the current general_configuration.pkl file first to
# establish what all the current values are, and what needs to change!

# This code is currently set-up to create a general_configuration_new.pkl
# file so that you have one last chance to check the old pickle file before 
# deleting it and renaming the new one

import pickle

config_file = "general_configuration_new.pkl"

configuration = {
    'split_half': False,
    'debug': True,
    'rerun': True,
    'networks': 1,
    'nodes': '1',
    'ntasks': '32',
    'cpu_node': '32',
    'batches': 8,
    'account': 'rrg-emazerol',
    'mem': '6',
    'time': '00-03:00:00',
    'processing': 'SLURM',
    'storage': 20000.0,
    'pipelines': 1
}

with open(config_file, "wb") as pickle_file:
    pickle.dump(configuration, pickle_file)