#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch processing script for running individual workflow batches in the Analysis Multiverse pipeline.
This script is designed to execute pre-built Nipype workflows in parallel, with each batch
running independently using the IPython plugin for distributed execution.

Created on Fri Mar 18 13:58:49 2022
@author: grahamseasons
"""
import pickle
import sys
import shutil
import os
import glob
from nipype import config

# Define the base directory where processed data and reproducibility checkpoints are stored
processed = '/scratch_dir/processed'

# Extract command-line arguments: batch ID, task name, and IPython profile for parallel execution
if len(sys.argv) > 3:
    batch = sys.argv[1]
    task = sys.argv[2]
    profile = sys.argv[3]

# Create and configure the checkpoint directory for storing crash dumps and execution logs
# This directory tracks the progress of each batch and stores error information if execution fails
save_dir = processed + '/reproducibility/checkpoints_' + task + '_batch_' + str(batch)
if not os.path.exists(save_dir):
    os.makedirs(save_dir, exist_ok=True)

# Configure Nipype to write crash dumps to the checkpoint directory for debugging and reproducibility
config.set("execution", "crashdump_dir", save_dir)

# Load the general configuration settings from a pickled file to determine runtime behavior
with open('/code/multiverse/configuration/general_configuration.pkl', 'rb') as f:
    configuration = pickle.load(f)

# Configure Nipype to automatically remove intermediate node directories after successful execution
# This optimization is only applied when not in debug mode to reduce storage usage
if not configuration['debug']:
    config.set("execution", "remove_node_directories", "true")

# Define the working directory path where Nipype will store intermediate files during execution
working_dir = '/scratch_dir/{task}_working_dir_{batch}'.format(task=task, batch=batch)

# Load the pre-built Nipype workflow object that was serialized and saved during workflow construction
with open(processed + '/reproducibility/' + task + '_workflow_' + batch + '.pkl', 'rb') as wf:
    workflow = pickle.load(wf)

# Execute the workflow using the IPython plugin for parallel/distributed execution
# The profile, task, and batch parameters are passed to the execution engine for resource management
workflow.run(plugin='IPython', plugin_args={'profile': profile, 'task': task, 'batch': batch})

# Rename the checkpoint directory to indicate successful completion (appends '_done' suffix)
# Only renames if no crash files were generated during execution, signaling clean completion
if os.path.exists(save_dir) and not glob.glob(save_dir + '/crash-*'):
    os.rename(save_dir, save_dir + '_done')

# Clean up the working directory to reclaim storage space after successful completion
# Deletion is skipped if debug mode is enabled or if crash files are present, preserving data for analysis
if os.path.exists(working_dir) and not configuration['debug'] and not glob.glob(save_dir + '/crash-*'):
    shutil.rmtree(working_dir)
