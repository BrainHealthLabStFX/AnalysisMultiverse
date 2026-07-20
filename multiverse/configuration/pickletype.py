# Use this script to identify the data type of the pickled object in a pickle
# file.
# Run on command line with the following:
# `python pickletype.py <pickle file to identify>

import sys
import pickle

file_name = sys.argv[1]
with open(file_name, "rb") as pickle_file:
    config = pickle.load(pickle_file)
print(type(config))
print(config)
