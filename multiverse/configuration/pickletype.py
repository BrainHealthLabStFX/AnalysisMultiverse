import sys
import pickle

file_name = sys.argv[1]
with open(file_name, "rb") as pickle_file:
    config = pickle.load(pickle_file)
print(type(config))
print(config)