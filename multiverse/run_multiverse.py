#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct  5 11:41:49 2021

@author: grahamseasons

Multiverse Analysis Runner: Main orchestration script for executing multi-pipeline fMRI analysis
with genetic algorithm optimization. Constructs and executes Nipype workflows for various fMRI
processing combinations, evaluates fitness scores, and iteratively optimizes parameters across
multiple generations.
"""
import pygad as pg
import numpy as np
import os, math
from os.path import join as opj
from analysis_pipeline import analysis
from bids.layout import BIDSLayout
from functions import generate_dictionaries, organize, save, load
import pickle
from nipype import config as conf
import json
import sys
import glob
from pathlib import Path
import pandas as pd
import re

import shutil

from nipype.utils.profiler import log_nodes_cb

# ============================================================================
# CONFIGURATION AND PATH SETUP
# ============================================================================
# Define directory paths for data input and output locations
exp_dir = '/scratch_dir'
working_dir = 'working_dir'
data_dir = '/data'
out_dir = exp_dir + '/processed'
# Load the FSL standard brain template for anatomical normalization
mask = opj(os.getenv('FSLDIR'), 'data/standard/MNI152_T1_2mm.nii.gz')
# Get the directory containing this script for configuration file access
dir = os.path.dirname(os.path.abspath(__file__))

# ============================================================================
# WORKFLOW LINK CONFIGURATION FUNCTION
# ============================================================================
def fix_links(dic):
    """
    Transform workflow link configurations from JSON format into an internal dictionary format.
    
    Processes pipeline connection definitions to map workflow node connections, parameter
    verification checks, node additions, and node edits. Handles three types of link operations:
    - 'verify': Direct parameter verification mappings
    - 'node_to_add': Adding new nodes with optional conditional triggers (on_off flags)
    - 'node_to_edit': Modifying existing nodes with switch conditions
    
    Args:
        dic (dict): Dictionary of workflow configurations with link definitions
        
    Returns:
        dict: Reorganized links dictionary mapping node operations to their parameters
    """
    links = {}
    for key in dic:
        links[key] = {}
        for link in dic[key]:
            if 'verify' in link:
                links[key].update({link['verify']: link['values']})
            elif 'node_to_add' in link:
                if 'on_off' in link:
                    links[key].update({link['node_to_add']: [link['node_to_copy'], link['on_off']]})
                else: 
                    links[key].update({link['node_to_add']: link['node_to_copy']})
            elif 'node_to_edit' in link:
                links[key].update({link['node_to_edit']: [link['node_to_edit'], link['on_off'], link['switch']]})
    return links

# ============================================================================
# LOAD CONFIGURATION FILES AND INITIALIZE WORKFLOW PARAMETERS
# ============================================================================

with open(opj(dir, 'configuration', 'multiverse_configuration.pkl'), 'rb') as f:
    # Load genetic algorithm gene configurations (optimization parameters to search across)
    genes = pickle.load(f)
    
    break_ = False
    # Resolve FSL environment variable references in custom gene configurations
    # Ensures FSL objects (.flobs files) have correct absolute paths to FSL installation
    for gene in genes:
        if 'l1d_bases' in gene.keys():
            for key in gene:
                if isinstance(gene[key], dict) and 'custom' in gene[key].keys():
                    for new_key in gene[key]['custom']:
                        if 'FSLDIR' in gene[key]['custom'][new_key]:
                            gene[key]['custom'][new_key] = "{FSLDIR}/etc/default_flobs.flobs".format(FSLDIR=os.getenv('FSLDIR'))#gene[key]['custom'][new_key].format(FSLDIR=os.getenv('FSLDIR'))
                            break_ = True
                            break
                if break_:
                    break
        if break_:
            break
    
# Load general execution configuration (debug mode, pipeline counts, storage limits, processing backend)
with open(opj(dir, 'configuration', 'general_configuration.pkl'), 'rb') as f:
    config = pickle.load(f)
    
# Load JSON file containing workflow node link definitions and connection patterns
with open(opj(dir, 'configuration', 'default_links.json')) as f:
    prelim_links = json.load(f)
    
# Transform link definitions from JSON into internal dictionary format for workflow construction
links = fix_links(prelim_links)

# ============================================================================
# CONFIGURE NIPYPE EXECUTION SETTINGS
# ============================================================================

# Use content-based hashing for workflow node caching (deterministic, content-aware)
conf.set("execution", "hash_method", "content")
# Save crash reports as plain text files for easier debugging
conf.set("execution", "crashfile_format", "txt")

# Clean up completed node working directories in non-debug mode to save disk space
if not config['debug']:
    conf.set("execution", "remove_node_directories", "true")

# ============================================================================
# PARSE COMMAND-LINE ARGUMENTS AND INITIALIZE GLOBAL VARIABLES
# ============================================================================
    
# First argument: whether to rerun the entire analysis (True/False string)
if sys.argv[1] == "True":
    config['rerun'] = True

else:
    config['rerun'] = False

# Second argument (optional): IPython cluster profile for parallel processing
if len(sys.argv) > 2:
    profile = sys.argv[2]

# Wiggle factor: small random perturbation applied during parameter generation
wiggle = 10
# Dictionary mapping gene indices to their genetic algorithm gene definitions
map_genes = {}
# Track the starting index for pipeline solutions in the current generation
solution_start = 0

# ============================================================================
# INITIALIZE BIDS LAYOUT AND EXTRACT DATASET INFORMATION
# ============================================================================

# Parse BIDS dataset structure from input directory
layout = BIDSLayout(data_dir)
# Extract all task names from the BIDS dataset
tasks = layout.get_tasks()


# ============================================================================
# UTILITY FUNCTION: CHECK IF SUFFICIENT UNIQUE PIPELINES HAVE BEEN GENERATED
# ============================================================================

def check_pipes(): 
    # Load unique pipeline configurations for each task and verify if target count is met
    unique = []
    for task in tasks:
        try:
            # Load results dataframe for current task (contains pipeline configurations and scores)
            frame = load('', task+'.pkl')
            # Count unique pipelines by dropping duplicates based on parameter columns (excludes R, P, Score)
            unique.append(frame.astype(str).drop_duplicates(subset=frame.columns.difference(['R', 'P', 'Score'])).shape[0] > config['pipelines'])
        except AttributeError:
            return
    
    # Return "stop" if all tasks have reached the minimum unique pipeline count
    if sum(unique) == config['pipelines']:
        return "stop"
    else:
        return

# ============================================================================
# FITNESS FUNCTION: EVALUATE PIPELINE SOLUTIONS FOR GENETIC ALGORITHM
# ============================================================================
        
def fitness_func(solution, solution_idx):
    # For split-half validation mode: average fitness scores across all tasks
    if config['split_half']:
        avg = []
        for task in tasks:
            # Load results dataframe for current task
            frame = load('', task+'.pkl')
            # Append the fitness score for this solution from the current task
            avg.append(frame['Score'][solution_start+solution_idx])
        return np.mean(avg)
    else:
        # If not using split-half validation, return neutral fitness score
        return 1

# ============================================================================
# CALLBACK FUNCTION: TRIGGERED ON EACH GENERATION OF THE GENETIC ALGORITHM
# ============================================================================
    
def on_pop_gen(ga):
    # Get the current generation number and population from the genetic algorithm
    gen = ga.generations_completed
    generation = gen
    pop_ = ga.population
    # Transpose population to get parameters in column format
    params_ = pop_.transpose()
    # Calculate the starting pipeline index for this generation
    pipeline_ = generation * pop_.shape[0]
    global solution_start
    solution_start = pipeline_
    
    # Check if enough unique pipelines have been generated; stop if threshold met
    if check_pipes():
        return "stop"
    
    # Handle rerun mode: restore previous generation parameters if available
    if config['rerun']:
        # Load all existing generation parameter files to find the last generation
        generation = glob.glob('/scratch_dir/processed/reproducibility/generation_*.pkl')
        generation = len(generation) - 1
        # Load the parameters from the last generation
        is_params = load('reproducibility', 'generation_'+str(generation)+'.pkl')
        if type(is_params) != str:
            params_ = is_params
            pop_ = params_.transpose()
            pipeline_ = generation * pop_.shape[0]
            solution_start = pipeline_
    else:
        # Save current generation parameters for reproducibility tracking
        save('reproducibility', 'generation_'+str(generation)+'.pkl', params_)
    
    for task in tasks:
        # Get BIDS dataset information for current task (subjects, sessions, runs, datatypes)
        subjects = layout.get_subjects(task=task)
        subjects.sort()
        types = layout.get_datatypes()
        sessions = layout.get_sessions(task=task)
        runs = layout.get_runs(task=task)
        
        # Create task-specific configuration directory and copy configuration files for reproducibility
        os.makedirs(out_dir + '/reproducibility/' + task + '/configuration/', exist_ok=True)
        shutil.copyfile('/code/multiverse/configuration/multiverse_configuration.pkl', out_dir + '/reproducibility/' + task + '/configuration/multiverse_configuration.pkl')
        shutil.copyfile('/code/multiverse/configuration/general_configuration.pkl', out_dir + '/reproducibility/' + task + '/configuration/general_configuration.pkl')
        
        # Determine if multi-session or multi-run data is present
        if sessions or runs:
            multiscan = True
        else:
            multiscan = False

        # For rerun mode, load existing results; otherwise start fresh
        if config['rerun']:
            frame = ''
        else:
            frame = load('', task+'.pkl')
        
        # Calculate storage requirements: GB needed per pipeline based on data dimensions and processing overhead
        gb_per_pipe = len(subjects) * (len(sessions) + 1) * (len(runs) + 1) * 0.83
        
        # Determine batch size for pipeline processing (split into batches if needed for memory constraints)
        batch_size = config.get('batches', pop_.shape[0])
        iterations = math.ceil(pop_.shape[0] / batch_size)
        
        # Adjust batch size based on available storage to prevent disk overflow
        if (config['storage'] / gb_per_pipe) < pop_.shape[0]:
            batch_size_ = int(config['storage'] / gb_per_pipe)
            iterations_ = math.ceil(pop_.shape[0] / batch_size)
        else:
            batch_size_ = pop_.shape[0]
            iterations_ = 1
        
        # Use the more conservative batch size (smaller of the two)
        if batch_size > batch_size_:
            batch_size = batch_size_
            iterations = iterations_
        
        # Find any existing completed checkpoint batches to avoid reprocessing
        existing_checkpoints = glob.glob(out_dir + '/checkpoints_' + task + '_batch_*_done')

        # Process each batch of pipelines separately
        for batch in range(iterations):
            # Check if this batch has existing checkpoints (partial completion detection)
            checkpoints = glob.glob('/scratch_dir/processed/reproducibility/checkpoints_' + task + '_batch_' + str(batch)+ '/checkpoint_*.pkl')
            if checkpoints:
                # Load existing workflows to determine last completed batch
                workflows = glob.glob('/scratch_dir/processed/reproducibility/' + task + '_workflow*')
                last_batch = len(workflows) - 1
                if batch < last_batch:
                    # Skip this batch if it's not the last one (already completed)
                    continue
                elif batch == last_batch:
                    # Remove results from incomplete last batch to reprocess
                    frame = load('', task+'.pkl')
                    frame.drop(range(batch*batch_size, (batch+1)*batch_size))

            # Extract parameters and population for this batch
            if (batch+1) * batch_size < pop_.shape[0]:
                params = params_[:, batch*batch_size:(batch+1)*batch_size]
                pop = pop_[batch*batch_size:(batch+1)*batch_size,:]
            else:
                # Last batch may have fewer pipelines than batch_size
                params = params_[:, batch*batch_size:]
                pop = pop_[batch*batch_size:,:]
            
            # Calculate absolute pipeline index for this batch
            pipeline = pipeline_ + batch * batch_size
            
            # Track which pipelines have already been run to avoid duplicates
            if type(frame) != str:
                already_run = set(range(frame.shape[0]))
            else:
                already_run = set()
            
            # Generate pipeline configurations from genetic algorithm parameters and workflow links
            master, expand_inputs, unique_pipelines = generate_dictionaries(map_genes, links, params, pop, multiscan, wiggle, pipeline, frame)
            
            # Handle existing checkpoint batches: update batch numbering if found
            if existing_checkpoints and not config['rerun']:
                existing_checkpoints.sort(key=lambda x: int(re.search('batch_([0-9]+)', x).group(1)))
                last_batch = int(re.search('batch_([0-9]+)', existing_checkpoints[-1]).group(1)) + 1
                batch += last_batch
            
            # Count unique pipelines and identify duplicates
            un = unique_pipelines.shape[0]
            # Find unique pipeline configurations (excluding result columns R, P, Score)
            test_unique = unique_pipelines.astype(str).drop_duplicates(subset=unique_pipelines.columns.difference(['R', 'P', 'Score']))
            test_un = test_unique.shape[0]
            
            # If duplicates are detected, reuse their results
            if test_un < un:
                # Find all duplicate pipeline configurations
                duplicates = unique_pipelines[unique_pipelines.astype(str).duplicated(keep=False, subset=unique_pipelines.columns.difference(['R', 'P', 'Score']))].astype(str)
                # Group duplicates together
                duplicates = duplicates.groupby(list(duplicates)).apply(lambda x: tuple(x.index)).to_list()
                for dup in duplicates:
                    for row in dup:
                        already_run.add(row)
                        
                        # Copy results from the first occurrence to subsequent duplicates
                        if row == dup[0]:
                            continue
                        else:
                            unique_pipelines['R'][row] = unique_pipelines['R'][dup[0]]
                            unique_pipelines['P'][row] = unique_pipelines['P'][dup[0]]
                            unique_pipelines['Score'][row] = unique_pipelines['Score'][dup[0]]
            
            # Determine which pipelines need to be run (new pipelines only)
            to_run = [i for i in list(test_unique.index.values) if i >= pipeline and i not in already_run]
            
            # Skip batch if no new pipelines need to be run
            if not to_run:
                continue
            
            # Update frame with unique pipelines for this batch
            frame = unique_pipelines
            
            # Identify pipelines that can be replaced with results from already-run pipelines
            to_replace = [l-pipeline for l in range(pipeline, pipeline+pop.shape[0]) if l not in to_run]
            
            # Optimize by replacing duplicate parameter sets with results from first occurrence
            if to_replace:
                start_ind = min(to_run)
                try:
                    params[:,to_replace] = params[:,start_ind-pipeline].reshape(-1,1)
                except IndexError:
                    continue
                if start_ind != pipeline:
                    params = np.delete(params, range(start_ind-pipeline), 1)
                pop = params.transpose()
                master, expand_inputs, _ = generate_dictionaries(map_genes, links, params, pop, multiscan, wiggle, start_ind, frame)
            
            # Save unique pipelines dataframe for results tracking
            out_frame = save('', task+'.pkl', unique_pipelines)
            
            # Only process if both anatomical and functional data are present
            if 'anat' in types and 'func' in types and to_run:
                # SLURM queue mode: prepare workflow for batch submission without running immediately
                if config['processing'] == 'SLURM' and 'num_generations' not in config:
                    # Create checkpoint directory for SLURM batch
                    save_dir = out_dir + '/reproducibility/checkpoints_' + task + '_batch_' + str(batch)
                    conf.set("execution", "crashdump_dir", save_dir)
                    
                    # Construct the Nipype workflow for this batch
                    pipelines = analysis(exp_dir, task+'_'+working_dir+'_'+str(batch), data_dir, out_dir)
                    pipelines = pipelines.construct(subjects, sessions, runs, task, pipeline, master, expand_inputs, config['split_half'], to_run, config['networks'], out_frame)
                    # Set workflow inputs: brain mask and task identifier
                    pipelines.inputs.inputnode.mask = mask
                    pipelines.inputs.inputnode.task = task

                    # Handle rerun mode: save or update workflow file
                    if os.path.exists(save_dir + '_done') and config['rerun']:
                        wf_path = save('reproducibility', task + '_workflow_' + str(batch) + '.pkl', pipelines)
                    elif config['rerun'] and os.path.exists(save_dir) and glob.glob(save_dir + '/crash-*'):
                        # Remove crash files and retry
                        for crash in glob.glob(save_dir + '/crash-*'):
                            os.remove(crash)
                    else:
                        save('reproducibility', task + '_workflow_' + str(batch) + '.pkl', pipelines)
                    
                    # Exit after submitting last batch to let SLURM handle execution
                    if batch == (iterations-1):
                        sys.exit()
                else:
                    # Local execution mode: run workflows directly (not through SLURM queue)
                    # Construct the Nipype workflow for this batch
                    pipelines = analysis(exp_dir, task+'_'+working_dir+'_'+str(batch), data_dir, out_dir)
                    pipelines = pipelines.construct(subjects, sessions, runs, task, pipeline, master, expand_inputs, config['split_half'], to_run, config['networks'], out_frame)
                    # Set workflow inputs: brain mask and task identifier
                    pipelines.inputs.inputnode.mask = mask
                    pipelines.inputs.inputnode.task = task
                    
                    # Configure plugin arguments for workflow execution (task batching, IPython profile for SLURM)
                    plugin_args = {'task': task, 'batch': batch}
        
                    # If SLURM processing is selected but num_generations is set, switch to IPython for local execution
                    if config['processing'] == 'SLURM':
                        config['processing'] = 'IPython'
                        plugin_args['profile'] = profile
                    
                    # Load workflow from checkpoint if this batch was previously started
                    if checkpoints and batch == last_batch:
                        pipelines = load('reproducibility', task + '_workflow_' + str(batch) + '.pkl')
                    else:
                        save('reproducibility', task + '_workflow_' + str(batch) + '.pkl', pipelines)
                    
                    # Set crash dump directory for workflow debugging
                    save_dir = out_dir + '/reproducibility/checkpoints_' + task + '_batch_' + str(batch)
                    conf.set("execution", "crashdump_dir", save_dir)
                    
                    # Execute the workflow with configured processing backend (multiprocessing or IPython parallel)
                    pipelines.run(plugin=config['processing'], plugin_args=plugin_args)
                
                    # Organize and save results from completed workflows
                    organized = organize(task, out_frame)
                    
                    # Mark batch as completed and clean up working directory if no crashes occurred
                    if not config['debug'] and not glob.glob(save_dir + '/crash-*'):
                        os.rename(save_dir, save_dir + '_done')
                        os.mkdir(out_dir + '/reproducibility/' + task + '_batch_' + str(batch) + '/configuration')
                        shutil.rmtree('/scratch_dir/' + working_dir)
                
    # End of multiverse loop: exit if not running multiple generations (single generation mode)
    if 'num_generations' not in config:
        # If checkpoints exist, rename them to mark completion
        # os.rename('/scratch_dir/processed/reproducibility/checkpoints', '/scratch_dir/processed/reproducibility/checkpoints_finished')
        
        # Exit after completing single generation
        sys.exit()

# ============================================================================
# MAIN FUNCTION: INITIALIZE AND RUN THE GENETIC ALGORITHM
# ============================================================================
        
def main():
    # Load genetic algorithm hyperparameters from config, or use defaults for single-generation mode
    if 'num_generations' in config:
        # Multi-generation evolution: use configured genetic algorithm parameters
        num_generations = config['num_generations']
        num_parents_mating = config['num_parents_mating']
        parent_selection_type = config['parent_selection_type']
        crossover_type = config['crossover_type']
        mutation_type = config['mutation_type']
        sol_per_pop = config['sol_per_pop']
    else:
        # Single-generation mode: generate fixed number of pipelines without evolution
        num_generations = 1
        num_parents_mating = 2
        parent_selection_type = 'random'
        crossover_type = 'single_point'
        mutation_type = 'random'
        if config['pipelines'] == 1:
            sol_per_pop = 2
        else:
            sol_per_pop = config['pipelines']
    
    # Build gene space: list of possible values for each gene (optimization parameter)
    gene_space = []
    dummy = 0
    num_genes = len(genes)
    
    for i, gene in enumerate(genes):
        # Map gene index to gene definition dictionary
        map_genes[i] = gene
        # Skip marker genes (e.g., 'l1d_bases_end') that indicate section boundaries
        if 'end' in list(gene.keys())[0]:
            dummy += 1
            continue
        
        # Extract possible values for this gene
        vals = list(gene.values())[0]
        # Convert boolean values to integers (0/1) for genetic algorithm
        if type(vals) == list:
            vals = [int(val) if type(val) == bool else val for val in vals]
        
        gene_space.append(vals)
    
    # Adjust gene count for marker genes (sections with 'end' markers)
    num_genes -= dummy
    
    # Initialize genetic algorithm with configuration and callback functions
    ga = pg.GA(num_generations=num_generations,
               num_parents_mating=num_parents_mating,
               # Fitness function evaluates quality of each solution
               fitness_func=fitness_func,
               # Callback triggered at population creation and each generation
               on_start=on_pop_gen,
               on_generation=on_pop_gen,
               sol_per_pop=sol_per_pop,
               
               # Gene precision: 3 decimal places for floating-point parameters
               gene_type=[float, 3],
               
               # Number of optimization parameters (genes)
               num_genes=num_genes,
               # Possible values for each gene
               gene_space=gene_space,
               # Parent selection strategy for breeding next generation
               parent_selection_type=parent_selection_type,
               
               # Genetic algorithm control parameters
               keep_parents=0,
               save_solutions=False,
               
               # Crossover and mutation operators for variation
               crossover_type=crossover_type,
               mutation_type=mutation_type,
               # Probability of gene mutation on each solution
               mutation_probability=0.2,
               )
    # Run the genetic algorithm for specified generations
    ga.run()
    
    # Post-processing can be added here for final analysis, results aggregation, etc.
    
# ============================================================================
# SCRIPT ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()
