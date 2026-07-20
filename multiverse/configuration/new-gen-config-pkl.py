# This script creates a new general_configuration.pkl file for test runs.

# Make sure to open the current general_configuration.pkl file first to
# establish what all the current values are, and what needs to change!

# This code is currently set-up to create a general_configuration_new.pkl
# file so that you have one last chance to check the old pickle file before 
# deleting it and renaming the new one.

# Create the new pickle file using:
# `nano -l new-gen-config-pkl.py`
# -> Make your required edits
# -> Use `ctrl-o` to save your changes
# -> Use `ctrl-x` to exit the Nano editor
# `python new-gen-config-pkl.py`
# -> This creates the new "general_configuration_new.pkl" file
# Rename the old pickle file:
# `mv general_configuration.pkl general_configuration_old.pkl`
# Rename the new pickle file so it can be found by the software:
# `mv general_configuration_new.pkl general_configuration.pkl`

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

# Save the configuration dictionary as a pickle file with the 
# config_file name
with open(config_file, "wb") as pickle_file:
    pickle.dump(configuration, pickle_file)
