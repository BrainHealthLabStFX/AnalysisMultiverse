#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct  1 14:54:23 2021

@author: grahamseasons
"""
from nipype import Node, IdentityInterface, Function
from nipype.interfaces.base import Undefined
import re, random
from collections import Counter
import numpy as np
import pandas as pd
import pickle
from pathlib import Path
import os

exp_dir = '/scratch_dir'
out_dir = exp_dir + '/processed'

def no_mask(file):
    """Raises FileNotFoundError for missing mask file"""
    raise FileNotFoundError("Specified mask '{m}' does not exist".format(m=file))

def invalid(mapped):
    """Raises SyntaxError for unsupported parameter format"""
    raise SyntaxError("Input paramater '{name}' in an unsupported format. Acceptable formats are (brain region, thr), (brain region, thr_min, thr_max, or path_to_mask".format(name=mapped))

def generate_dictionaries(map_genes, links, params, pop, multiscan, wiggle, ind_start, frame):
    """Generates dictionaries of analysis parameters for workflow from GA output.
       i.e. Converts numeric values into values accepted by nodes, as defined in links"""
    # Initialize container to track parameter values across populations
    container = np.zeros((1, pop.shape[0]), str)
    # Track indices of individuals in the population
    indexes = [(ind_start, ind_start+pop.shape[0])]
    # Many of the below are accessed through var() -> they are in use, do not delete
    # Initialize dictionary for expanded inputs (dynamic inputs)
    expand_inputs = {}
    # Initialize dictionaries for each analysis stage
    preprocess = {}
    level1 = {}
    # Initialize lists to track unique columns and values for dataframe construction
    unique_cols = []
    unique_cols_temp = []
    unique_vals = []
    # Create level2 dictionary if multiple scans per subject
    if multiscan:
        level2 = {}
    # Initialize dictionaries for remaining analysis stages
    level3 = {}
    correction = {}
    # Start at preprocessing stage
    dic = 'preprocess'
    # Track valid dictionary stages
    valid = []
    master = {}
    previous = ''
    counter = 0
    # Iterate through each mapped gene from GA output
    for key in map_genes:
        gene = map_genes[key]
        keys = list(gene.keys())
        # Extract node name from key using regex (e.g., 'prep_' from 'prep_something')
        node_name = re.search('([A-Za-z0-9]+)_', keys[0]).group(1)
        # Check if this is a new node or continuing from previous
        if not previous or 'end' in previous:
            if key - 1 in map_genes:
                get_value = key - 1
            else:
                get_value = key
            # Skip level2 analysis if only single scan per subject
            if not multiscan and list(map_genes[get_value].values())[0] == 'level2':
                lock = True
                counter += 1
                continue
            elif vars().get('lock', False):
                # Skip nodes until 'end' marker is found
                if node_name == 'end':
                    lock = False
                    dic = gene[keys[0]]
                    continue
                else:
                    continue
            previous = node_name
        # Check when node transitions to a new stage (different node name)
        if previous != node_name:
            # Add nodes from links.json that connect between stages
            for link in links[dic]:
                if previous in link[:len(previous)]:
                    connect = links[dic][link]
                    # Determine if direct copy or formatted copy of node parameters
                    if type(connect) == list:
                        group = re.search('([A-Za-z0-9]+)_', connect[0]).group(1)
                        # Find group in current or previously valid dictionaries
                        if group not in vars()[dic]:
                            for opt in valid:
                                if group in vars()[opt]:
                                    break
                        vals = vars()[dic][group][connect[0]]
                        check = vars()[dic][group][connect[1]]
                        # Assign mutually exclusive values based on rule
                        if len(connect) == 3:
                            rule = connect[2]
                            vars()[dic][previous][link] = [val if check[c] != rule else Undefined for c, val in enumerate(vals)]
                        else:
                            vars()[dic][previous][link] = [val if check[c] else Undefined for c, val in enumerate(vals)]
                    else:
                        # Direct parameter copy from source node
                        try:
                            group = re.search('([A-Za-z0-9]+)_', connect).group(1)
                            if group in vars()[dic]:
                                vars()[dic][previous][link] = vars()[dic][group][connect]
                            else:
                                for opt in valid:
                                    if group in vars()[opt]:
                                        break
                                vars()[dic][previous][link] = vars()[opt][group][connect]
                        except:
                            raise SyntaxError("Node name {pre} in links violates naming convention. Please keep name to alphanumeric characters.".format(pre=connect))
            # Store dynamic input parameters that will be expanded later
            if 'F' == previous[0]:
                expand_inputs[previous[1:]] = vars()[dic][previous]
            previous = node_name
        # Handle end markers that indicate completion of analysis stage
        if 'end' in keys[0]:
            # Define output paths based on current stage parameters
            container, pholder, indexes = define_paths(container, vars()[dic], indexes)
            # Preserve old stage parameters for reference
            vars()[dic+'_old'] = vars()[dic].copy()
            valid.append(dic+'_old')
            # Reset current stage dictionary with placeholder parameters
            vars()[dic].clear()
            vars()[dic].update(pholder)
            # Store stage in master dictionary
            master[dic] = vars()[dic]
            # Move to next analysis stage
            dic = gene[keys[0]]
            counter += 1
            continue
        # Initialize new node in current stage if not present
        if node_name not in vars()[dic]:
            vars()[dic][node_name] = {}
        # Extract parameter values for current GA individual
        values = params[key-counter,:]
        # Determine if float values should be converted to integers
        isint = False
        if values.dtype == float:
            check_vals = [val.is_integer() for val in values]
            if sum(check_vals) == len(check_vals):
                isint = True
        # Skip nodes with '!' prefix (linked nodes handled above)
        if keys[0][0] == '!':
            continue
        # Process non-numeric parameters or parameters requiring dictionary construction
        if len(gene) > 1 or '~construct~' in keys[0]:
            for l, i in enumerate(values):
                if round(i) in gene:
                    mapped = gene[round(i)]
                else:
                    mapped = i
                # Handle dictionary of mutually exclusive parameters (e.g., XFM matrices)
                if type(mapped) == dict and keys[0][-1] == '_':
                    for k in mapped:
                        if keys[0][-1] == '_':
                            param = keys[0] + k
                        else:
                            param = node_name + '_' + k
                        if param not in vars()[dic][node_name]:
                             vars()[dic][node_name][param] = []
                        # Track independently chosen parameters
                        if param not in unique_cols and param not in unique_cols_temp:
                            unique_cols_temp.append(param)
                        vars()[dic][node_name][param].append(mapped[k])
                # Construct dictionary parameters from gene specification
                elif '~construct~' in keys[0]:
                    var_name = re.search('_([A-Za-z]+)', keys[0]).group(1)
                    key_name = re.search('_([A-Za-z]+)$', keys[0]).group(1)
                    param = node_name + '_' + var_name
                    if param not in vars()[dic][node_name]:
                        vars()[dic][node_name][param] = []
                    # Generate threshold ranges from gene values if not all integers
                    if not isint:
                        rand = random.Random(i)
                        # Handle list of networks/thresholds
                        if type(mapped) == list:
                            mapped = [(m[0], rand.randint(int(m[1])-wiggle if int(m[1])-wiggle > 0 else 0, int(m[1])+wiggle if int(m[1])+wiggle > 95 else 95)) if len(m) == 2 and isinstance(m, (tuple,list)) else (m[0], rand.randint(int(m[1]), int(m[2]))) if isinstance(m, (tuple,list)) else m if isinstance(m, str) else invalid(param+'_'+key_name) for m in mapped]
                        # Generate random range from tuple bounds
                        elif mapped == tuple:
                            mapped = rand.randint(mapped[0], mapped[1])
                        else:
                            mapped = i
                    else:
                        # Convert float to int if all values are integers
                        if isinstance(mapped, float):
                            mapped = int(mapped)
                    # Verify all pipelines have dictionary values (one per pipeline)
                    if len(vars()[dic][node_name][param]) != pop.shape[0]:
                        construction_key = key_name
                        vars()[dic][node_name][param].append({key_name: mapped})
                    else:
                        # Ensure parameter is relevant for this analysis type
                        if key_name in links[dic]:
                            if vars()[dic][node_name][param][l][construction_key] not in links[dic][key_name]:
                                continue
                        # Add parameter value to correct pipeline slot
                        vars()[dic][node_name][param][l][key_name] = mapped
                else:
                    # Add simple mapped values without special processing
                    param = keys[0]
                    if param not in vars()[dic][node_name]:
                        vars()[dic][node_name][param] = []
                    # Track this parameter for dataframe construction
                    if param not in unique_cols and param not in unique_cols_temp:
                        unique_cols_temp.append(param)
                    vars()[dic][node_name][param].append(mapped)

            if param not in unique_cols and param not in unique_cols_temp:
                unique_cols_temp.append(param)
        else:
            # Convert float values to integers if all are integer-valued
            if values.dtype == float:
                if isint:
                    values = values.astype(int)
            # Store simple parameter values directly to node dictionary
            vars()[dic][node_name][keys[0]] = values
            # Track parameter for dataframe construction
            if keys[0] not in unique_cols and keys[0] not in unique_cols_temp:
                unique_cols_temp.append(keys[0])
        # Collect unique parameter values for each parameter type
        for param in unique_cols_temp:
            node_name_temp = re.search('([A-Za-z0-9]+)_', param).group(1)
            try:
                unique_vals.append(vars()[dic][node_name_temp][param])
            except KeyError:
                # Look for parameter in previously valid stage dictionaries
                for opt in valid:
                    if node_name_temp in vars()[opt]:
                        break
                unique_vals.append(vars()[opt][node_name_temp][param])
        # Add current parameters to list of all unique parameters
        unique_cols += unique_cols_temp
        unique_cols_temp = []
    # Build output dataframe of pipeline definitions including R, P, Score columns
    unique_cols += ['R', 'P', 'Score']
    l = len(unique_vals[-1])
    unique_vals += [[0]*l, [0]*l, [0]*l]
    # Create dataframe transposing parameter arrays to have pipelines as rows
    pipeline_def = pd.DataFrame(data=np.array(unique_vals, dtype=object).transpose(), columns=unique_cols)
    # Concatenate with existing dataframe if this is a GA iteration
    if type(frame) != str:
        pipeline_def = pd.concat([frame, pipeline_def], ignore_index=True)

    return master, expand_inputs, pipeline_def
    
def metadata(filename, data):
    """Grab TR time from metadata"""
    # Import BIDS layout for querying dataset structure
    from bids.layout import BIDSLayout
    layout = BIDSLayout(data)
    # Retrieve metadata associated with the fMRI file
    meta_data = layout.get_metadata(filename)
    # Extract the repetition time (TR) in seconds
    TR = meta_data['RepetitionTime']
    return TR

def event_grabber(file, data):
    """Get event file/information for subject"""
    # Import regex and BIDS layout
    import re
    from bids.layout import BIDSLayout
    layout = BIDSLayout(data)
    # Extract task name from file path using regex
    task = re.search('task-([0-9A-Za-z]+)_bold', file).group(1)
    # Return empty string for resting state (no event file needed)
    if 'rest' in task:
        return ''
    # Get all event files for this task
    event_file = layout.get(task=task, extension='.tsv')
    # If multiple event files, narrow down by subject, session, and run
    if len(event_file) > 1:
        sub = re.search('/sub-([0-9A-Za-z]+)/', file).group(1)
        ses = re.search('_ses-([A-Za-z]+)_task', file)
        run = re.search('run-([0-9]+)', file)
        # Query with all available identifiers for specificity
        if ses and run:
            event_file = layout.get(task=task, session=ses.group(1), run=run.group(1), subject=sub, extension='.tsv')
        elif ses:
            event_file = layout.get(task=task, session=ses.group(1), subject=sub, extension='.tsv')
        elif run:
            event_file = layout.get(task=task, run=run.group(1), subject=sub, extension='.tsv')
    # Return empty string if no event file found
    elif not len(event_file):
        event_file = ['']
    # Return file path or empty string
    return event_file[0]

def covariate_frame(data):
    """Grab dataframe containing covariate information"""
    # Import BIDS layout for dataset structure
    from bids.layout import BIDSLayout
    layout = BIDSLayout(data)
    # Query for participants.tsv file containing demographic/covariate data
    file = layout.get(return_type='filename', extension='.tsv', suffix='participants')
    # Return path to participants file
    return file[0]

def split_(smoothed, unsmoothed, half):
    """Split functional scan into first and second half for NPAIRs genetic algorithm"""
    # Import nibabel for loading nifti files
    import nibabel as nib
    # Import FSL ExtractROI for temporal subset extraction
    from nipype.interfaces.fsl import ExtractROI
    # Calculate midpoint of time series (number of volumes)
    length = round(nib.load(smoothed).shape[-1] / 2)
    # Extract first half of volumes (t_size=length)
    if half == 'first':
        smoothed = ExtractROI(in_file=smoothed, t_min=0, t_size=length).run().outputs.roi_file
        unsmoothed = ExtractROI(in_file=unsmoothed, t_min=0, t_size=length).run().outputs.roi_file
    # Extract second half of volumes (t_min=length, t_size=-1 means to end)
    elif half == 'second':
        smoothed = ExtractROI(in_file=smoothed, t_min=length, t_size=-1).run().outputs.roi_file
        unsmoothed = ExtractROI(in_file=unsmoothed, t_min=length, t_size=-1).run().outputs.roi_file
    else:
        raise ValueError("Only 'first' and 'second' are valid inputs for split half analysis, but {half} was given instead.".format(half=half))
    # Return split files
    return smoothed, unsmoothed
    
        
def remove(T1w, bold):
    """Remove container"""
    # Extract first element from both inputs (remove list wrapping)
    return T1w[0], bold[0]

def insert(string, ind, new):
    """Insert string at specified location"""
    # Concatenate string parts with insertion at specified index
    return string[:ind] + new + string[ind:]

def make_buff_vars(dic):
    """Creates dynamic functions to index parameters for the correct pipelines - allows for shared data as long as possible"""
    # Template for dynamic function definition
    func = "def buff_var({var}):\n\treturn "
    # Extract all parameter keys from nested dictionary structure
    var = [param_key for key in dic for param_key in dic[key] if param_key != 'id' or param_key != 'link']
    # Build input parameter string
    inputs = ''
    # Build return value string indexing parameters for correct pipeline
    ret = ''
    for v in var:
        inputs += str(v) + ', '
        ret += str(v) + '[i-i_sub], '
    # Add iterator and indexing variables to inputs and return values
    inputs += 'i, i_in, i_sub'
    ret += 'i'
    # Parse input parameter names
    input_names = inputs.split(', ')
    # Return function string, all input names, and output names (excluding indexing vars)
    return func.format(var=inputs) + ret, input_names, input_names[:-2]

def setatts(node, dic, keys):
    """Sets the inputs for automated buffer nodes"""
    # Remove indexing variables from keys list
    keys = keys[:-3]
    # Set each parameter as an attribute on the nipype node
    for key in keys:
        setattr(node.inputs, key, dic[key])
        
def get_links(dic, keys):
    """Creates dictionary of links between pipelines (i.e. when a pipeline splits off from its progenitor)"""
    # Track nodes where pipelines split
    nodes = []
    # Dictionary mapping nodes to pipeline connections
    connections = {}
    expansion = {}
    # Iterate through each pipeline key
    for key in keys:
        check = False
        sub_dic = dic[key]
        try:
            # Check if pipeline is parent to future pipelines (has multiple pipelines)
            if len(sub_dic['id']) > 1:
                check = True
                # Get all pipeline keys except 'id'
                pipeline_keys = list(sub_dic.keys())
                pipeline_keys.remove('id')
            else:
                # Get keys from pipeline within current key
                pipeline_keys = list(sub_dic[key].keys())
                pipeline_keys.remove('id')
                # Direct link for pipelines with no dependent children
                if pipeline_keys[0] not in connections:
                    connections[pipeline_keys[0]] = {}
                connections[pipeline_keys[0]][key] = [key]
        except:
            # Handle missing 'id' or nested structure issues
            check = True
            pipeline_keys = sorted(list(sub_dic.keys()))
            # Empty pipeline list indicates end of structure
            if pipeline_keys == ['id']:
                pipeline_keys = []
        # Build connection links between pipelines
        if check:
            for k in pipeline_keys:
                # Check if pipeline splits off from parent
                if 'link' in sub_dic[k]:
                    link = sub_dic[k]['link']
                    # Get the parent node from link specification
                    node = list(link.values())[0][0]
                    link_key = list(link.keys())[0]
                    key_ = link_key.copy()
                    nodes.append(node)
                    try:
                        # Add connection if node-link combo already exists
                        if link_key in connections[node]:
                            connections[node][link_key].append(k)
                        else:
                            # Look for existing connection linking to same root node
                            current_vals = connections[node].values()
                            current_keys = list(connections[node].keys())
                            # Ensure link to root pipeline, not intermediate stage
                            for i, vals in enumerate(current_vals):
                                if link_key in vals:
                                    key_ = current_keys[i]
                                    break
                            # Add connection to found or new key
                            if key_ in connections[node]:
                                connections[node][key_].append(k)
                            else:
                                connections[node][key_] = [link_key]
                                # Self-link if pipeline doesn't match its key
                                if link_key != k:
                                    connections[node][key_].append(k)
                    except:
                        # Node or link not yet in connections dict - create entry
                        if node in connections:
                            connections[node][link_key] =  [link_key]
                        else:
                            connections[node] = {link_key: [link_key]}
                        # Add pipeline to connection list
                        if k not in connections[node][link_key]:
                            connections[node][link_key].append(k)
                else:
                    # Self-link pipeline to itself
                    pipeline_keys = list(sub_dic[key].keys())
                    pipeline_keys.remove('id')
                    # Create connection entry if not present
                    if pipeline_keys[0] not in connections:
                        connections[pipeline_keys[0]] = {}
                    connections[pipeline_keys[0]][key] = [key]
    # Return split nodes and connection mappings
    return list(dict.fromkeys(nodes)), add_mapping(connections)

def add_mapping(con):
    """Ensure that pipelines with no children are included (self link)"""
    # Track single-child pipelines
    single = []
    out_con = con.copy()
    # Iterate through connection entries
    for key in con:
        # Flatten all pipeline values for this connection
        values = [item for value in con[key].values() for item in value]
        # Check if any pipelines missing from child list
        if single:
            missing = sorted((Counter(single) - Counter(values)).elements())
            # Add self-links for missing pipelines
            for pipe in missing:
                out_con[key][pipe] = [pipe]
            # Update single list with new values
            single = [item for value in out_con[key].values() for item in value]
        else:
            single = values
    # Return connection dict with all pipelines having entries
    return out_con


def traverse(dic, flow, suffix, pipeline, to_run):
    """Makes connections between nodes, sets changeable parameters of nodes"""
    # Determine starting pipeline index (smallest if specified, else use provided)
    if to_run:
        start_pipe_ = min(to_run)
    else:
        start_pipe_ = pipeline
    # Create iterator node that seeds the differentiation into unique pipelines
    iternode = Node(IdentityInterface(fields=['i']), name='iternode'+suffix)
    iternode.iterables = ('i', [start_pipe_])
    # Track buffer nodes used for parameter indexing
    buff_count = []
    # Iterate through each workflow stage (preprocessing, level1, level2, etc.)
    for wf in dic:
        buff_dic = {}
        dic_ = dic[wf]
        dic_k = list(dic_.keys())
        # Get numeric keys representing pipeline starting indices
        start_pipe = [i for i in dic_k if isinstance(i, (int, np.integer))]
        # Determine where pipelines split in this workflow stage
        split_nodes, connections = get_links(dic_, start_pipe)
        outstanding = False
        # Check if pipelines split in this workflow stage
        if connections:
            for i, info in enumerate(dic_[start_pipe_][start_pipe_]):
                # Skip 'id' and 'link' markers
                if info == 'id' or info == 'link':
                    continue
                # For non-split nodes or first node, add directly to buffer dictionary
                if info not in split_nodes or not i:
                    buff_dic[info] = dic_[start_pipe_][start_pipe_][info]
                    outstanding = True
                else:
                    # Create buffer node at pipeline split point
                    if not buff_count:
                        buff_count.append(1)
                    # Move connection from old key to buffer function number
                    connections[buff_count[-1]] = connections.pop(list(buff_dic.keys())[0])
                    # Generate buffer function code and parameter names
                    func, input_names, output_names = make_buff_vars(buff_dic)
                    # Create nipype Function node from generated code
                    vars()['buff_' + str(buff_count[-1])] = Node(Function(input_names=input_names, output_names=output_names), name='buff_' + str(buff_count[-1]))
                    vars()['buff_' + str(buff_count[-1])].inputs.function_str = func
                    vars()['buff_' + str(buff_count[-1])].inputs.i_sub = start_pipe_
                    # Set input attributes on buffer node
                    setatts(vars()['buff_' + str(buff_count[-1])], dic_, input_names)
                    # Connect buffer node outputs to downstream node inputs
                    for name in input_names[:-3]:
                        end = re.search('^([A-Za-z0-9]+)_([A-Za-z_]+)', name)
                        if flow.get_node(wf).get_node(end.group(1)):
                            flow.get_node(wf).connect(vars()['buff_' + str(buff_count[-1])], name, flow.get_node(wf).get_node(end.group(1)), end.group(2))
                    # Increment buffer counter for next buffer node
                    buff_count.append(buff_count[-1] + 1)
                    # Reset buffer dictionary with new split node
                    buff_dic = {info: dic_[start_pipe_][start_pipe_][info]}
                    outstanding = True
        # Handle any outstanding buffer connections
        if outstanding:
            if not buff_count:
                buff_count.append(1)
            # Create final buffer function for remaining parameters
            connections[buff_count[-1]] = connections.pop(list(buff_dic.keys())[0])
            func, input_names, output_names = make_buff_vars(buff_dic)
            # Create buffer node
            vars()['buff_' + str(buff_count[-1])] = Node(Function(input_names=input_names, output_names=output_names), name='buff_' + str(buff_count[-1]))
            vars()['buff_' + str(buff_count[-1])].inputs.function_str = func
            vars()['buff_' + str(buff_count[-1])].inputs.i_sub = start_pipe_
            setatts(vars()['buff_' + str(buff_count[-1])], dic_, input_names)
            # Connect buffer node to downstream nodes
            for name in input_names[:-3]:
                end = re.search('^([A-Za-z0-9]+)_([A-Za-z_]+)', name)
                if flow.get_node(wf).get_node(end.group(1)):
                    flow.get_node(wf).connect(vars()['buff_' + str(buff_count[-1])], name, flow.get_node(wf).get_node(end.group(1)), end.group(2))
            # Connect iterator or previous buffer output to all buffer nodes
            for buff in buff_count:
                if buff == 1 and vars().get('buff_1', False):
                    # First buffer: connect from iterator node
                    vars()['buff_' + str(buff)].itersource = ('iternode'+suffix, 'i')
                    vars()['buff_' + str(buff)].iterables = [('i', connections[buff])]
                    flow.get_node(wf).connect(iternode, 'i', vars()['buff_' + str(buff)], 'i_in')
                elif not vars().get('buff_1', False):
                    break
                else:
                    # Subsequent buffers: connect from previous buffer
                    vars()['buff_' + str(buff)].itersource = ('buff_' + str(buff - 1), 'i')
                    vars()['buff_' + str(buff)].iterables = [('i', connections[buff])]
                    flow.get_node(wf).connect(vars()['buff_' + str(buff - 1)], 'i', vars()['buff_' + str(buff)], 'i_in')
        # Connect constant parameters that don't change across pipelines
        for node in dic_['const']:
            const = dic_['const'][node]
            keys = list(const.keys())
            vals = list(const.values())
            # Extract parameter name and set on node
            for i, k in enumerate(keys):
                k_var = re.search(node+'_([A-Za-z_]+)', k).group(1)
                # Check if node exists in workflow
                if flow.get_node(wf).get_node(node) == None:
                    continue
                # Set parameter value if node input supports it
                if k_var in flow.get_node(wf).get_node(node).inputs.get():
                    setattr(flow.get_node(wf).get_node(node).inputs, k_var, vals[i])
        # Reset buffer count when moving to next workflow stage
        if buff_count and outstanding:
            buff_count = [buff_count[-1]+1]
                

def define_paths(container, dictionary, indexes):
    """Formats dictionary used to store parameters and keeps track of where pipelines split"""
    out_dic = {}
    link = {}
    # Initialize output dictionary with pipeline indices and id tracking
    for i, vals in enumerate(indexes):
        if isinstance(vals, np.ndarray):
            out_dic[int(indexes[i].min())] = {'id': vals}
            rng = indexes[0]
        else:
            # Convert single value or tuple to array range
            if type(vals) == tuple:
                rng = np.array(range(vals[0], vals[1]))
            else:
                rng = np.array(range(vals))
            out_dic[rng[i]] = {'id': rng}
    # Create entry for constant parameters (those unchanged across pipelines)
    out_dic['const'] = {}
    # Iterate through each node and its parameters in the input dictionary
    for i, key in enumerate(dictionary):
        # Process each parameter of the current node
        for subkey in dictionary[key]:
            try:
                # Convert all parameter values to strings for comparison
                placeholder = [str(element) for element in dictionary[key][subkey]]
                container = np.vstack((container, placeholder))
            except:
                pass
            # Find unique parameter values and map to pipelines
            vals, ind = np.unique(container, return_inverse=True, axis=1)
            # Create index list showing which column(s) have each unique value
            index = [np.where((vals[:,i].reshape(-1,1) == container).sum(axis=0) == container.shape[0])[0] for i in range(vals.shape[1])]
            # Sort indices by minimum value to identify pipeline groupings
            index_ = sorted(index, key=min)
            start_ = rng[0]
            # Adjust indices to be global (not relative to current iteration)
            index_ = [arr + start_ for arr in index_]
            # Check if parameter value is constant across all pipelines
            try:
                gen = np.unique(dictionary[key][subkey])
            except:
                tostring = [str(item) for item in dictionary[key][subkey]]
                gen = np.unique(tostring)
            # Iterate through root pipeline starting indices
            for k in out_dic:
                if not isinstance(k, (int, np.integer)):
                    break
                # Mark parameter as constant if only one unique value
                if len(gen) == 1:
                    if key not in out_dic['const']:
                        out_dic['const'][key] = {}
                    if subkey not in out_dic['const'][key]:
                        out_dic['const'][key][subkey] = {}
                    out_dic['const'][key][subkey] = dictionary[key][subkey][0]
                    continue
                # Assign parameters to specific pipelines
                for j, x in enumerate(index_):
                    # Skip pipelines that haven't split from parent yet
                    if 'id' in out_dic[k]:
                        if len(np.intersect1d(x, out_dic[k]['id'])) != len(x):
                            continue
                    # Safely build nested dictionary structure for pipeline parameters
                    if min(index_[j]) not in out_dic[k]:
                        out_dic[k][min(index_[j])] = {}
                    if key not in out_dic[k][min(index_[j])]:
                        out_dic[k][min(index_[j])][key] = {}
                    if subkey not in out_dic[k][min(index_[j])][key]:
                        out_dic[k][min(index_[j])][key][subkey] = {}
                    # Initialize id as [-1] to mark first run
                    if 'id' not in out_dic[k][min(index_[j])]:
                        out_dic[k][min(index_[j])]['id'] = [-1]
                    # Track where pipelines split off from parent
                    if not np.array_equiv(out_dic[k][min(index_[j])]['id'], x):
                        # Record link information if pipeline id changes
                        if not np.array_equiv(out_dic[k][min(index_[j])]['id'], [-1]):
                            cx = Counter(out_dic[k][min(index_[j])]['id'])
                            cid = Counter(x)
                            # Store parent pipeline indices for linking
                            for out in sorted((cx - cid).elements()):
                                link[out] = {min(index_[j]): [key, subkey]}
                        # Create link for intermediate stage splits
                        elif 'id' in out_dic[k]:
                            if not np.array_equiv(out_dic[k][min(index_[j])]['id'], [-1]) or (min(x) == min(out_dic[k]['id']) and len(x) < len(out_dic[k]['id'])):
                                for out in out_dic[k]['id']:
                                    link[out] = {min(index_[j]): [key, subkey]}
                    # Add link information to output dictionary
                    if min(index_[j]) in link:
                        out_dic[k][min(index_[j])]['link'] = link[min(index_[j])]
                    # Update pipeline id to current indices and set parameter to None (placeholder)
                    out_dic[k][min(index_[j])]['id'] = x
                    out_dic[k][min(index_[j])][key][subkey] = None
            # Reset link dictionary for next parameter
            link = {}
            out_dic[subkey] = dictionary[key][subkey]
    # Return container, output dictionary, and final indices
    return container, out_dic, index_


def load(path, file):
    """Load pickled file from output directory"""
    # Construct full file path
    out = os.path.join(out_dir, path, file)
    # Check if file exists before attempting to load
    if os.path.isfile(out):
        with open(out, 'rb') as f:
            loaded = pickle.load(f)
    else:
        # Return empty string if file not found
        loaded = ''
    return loaded

def save(path, file, frame):
    """Save data structure to pickled file in output directory"""
    # Construct output directory path
    out = os.path.join(out_dir, path)
    # Create directory structure if it doesn't exist
    Path(out).mkdir(parents=True, exist_ok=True)
    # Construct full file path
    out = os.path.join(out, file)
    # Pickle and save data to file
    with open(out, 'wb') as f:
        pickle.dump(frame, f)
    # Return path to saved file
    return out

def organize(task, out_frame):
    """Creates a dictionary of final output files, and parameters for each pipeline - excludes parameters that are unchanged across all pipelines
       
       Structure:
           {pipeline: {network: {contrast: file}},
                      {parameters: {parameters}}
                      }
    """
    # Initialize output dictionary with pipeline and constants sections
    processed = {'pipeline': {}, 'constants': {}}
    # Find all corrected output files for this task
    pathlist = Path(out_dir+'/pipelines/'+task).glob('**/*_corrected_[0-9]*')
    # Load pipeline definition dataframe
    dat_frame = out_frame
    with open(dat_frame, 'rb') as file:
        dat_frame = pickle.load(file)
    # Create comparison dataframe with rolled values to detect constants
    comp = pd.DataFrame(np.roll(dat_frame.values, 1, axis=0), index=dat_frame.index)
    # Process each output file
    for path in pathlist:
        path = str(path)
        # Extract network index from file path
        network = int(re.search('.*_network_([0-9]+)', path).group(1))
        # Extract contrast index from file path
        contrast = int(re.search('.*_corrected_([0-9]+).nii.gz', path).group(1))
        # Extract pipeline index (defaults to 0 if not found)
        try:
            pipeline = int(re.search('.*_i_([0-9]+)', path).group(1))
        except:
            pipeline = 0
        # Add output file to pipeline-network-contrast structure
        if pipeline in processed['pipeline']:
            if network in processed['pipeline'][pipeline]['network']:
                processed['pipeline'][pipeline]['network'][network]['contrast'][contrast] = path
            else:
                processed['pipeline'][pipeline]['network'][network] = {'contrast': {contrast: path}}
        else:
            processed['pipeline'][pipeline] = {'network': {network: {'contrast': {contrast: path}}}}
        # Get parameters for this pipeline
        pipe_dat = dat_frame.loc[pipeline]
        # Check each column/parameter to determine if it's constant or variable
        for i, column in enumerate(dat_frame):
            col = pipe_dat[column]
            # If parameter is identical across all pipelines, mark as constant
            if (comp[i] == dat_frame[column]).all():
                processed['constants'][column] = col
                # Handle dictionary parameters for resting state analysis
                if isinstance(col, dict):
                    for key in col:
                        if task == 'rest':
                            # Extract gamma/derivative basis specification
                            if isinstance(key, str) and ('gamma' in key or 'dgamma' in key):
                                processed['constants'][column] = key
                                processed['constants']['derivs'] = col[key]['derivs']
                            # Extract custom specification
                            elif isinstance(key, str) and 'custom' in key:
                                processed['constants'][column] = key
                                processed['constants']['derivs'] = False
                            # Extract seed region and threshold information
                            elif key == 'seedinfo':
                                processed['constants'][key+'region'] = col[key][0][0]
                                processed['constants'][key+'threshold'] = col[key][0][1]
                            else:
                                processed['constants'][key] = col[key]
                        else:
                            processed['constants'][key] = col[key]
                else:
                    processed['constants'][column] = col
                continue
            # Initialize parameters section for this pipeline if needed
            if 'parameters' not in processed['pipeline'][pipeline]:
                processed['pipeline'][pipeline]['parameters'] = {}
            # Handle varying dictionary parameters
            if isinstance(col, dict):
                for key in col:
                    if task == 'rest':
                        # Extract and store gamma/derivative basis specification
                        if isinstance(key, str) and ('gamma' in key or 'dgamma' in key or 'none' in key):
                            processed['pipeline'][pipeline]['parameters'][column] = key
                            processed['pipeline'][pipeline]['parameters']['l1d_derivs'] = col[key]['derivs']
                        # Extract and store custom specification
                        elif isinstance(key, str) and 'custom' in key:
                            processed['pipeline'][pipeline]['parameters'][column] = key
                            processed['pipeline'][pipeline]['parameters']['l1d_derivs'] = False
                        # Extract and store seed region and threshold
                        elif key == 'seedinfo':
                            processed['pipeline'][pipeline]['parameters'][key+'region'] = col[key][0][0]
                            processed['pipeline'][pipeline]['parameters'][key+'threshold'] = col[key][0][1]
                        else:
                            processed['pipeline'][pipeline]['parameters'][key] = col[key]
                    else:
                        processed['pipeline'][pipeline]['parameters'][key] = col[key]
            else:
                # Store non-dictionary parameter values
                processed['pipeline'][pipeline]['parameters'][column] = col
    # Save organized results and return path
    return save('', task+'_organized.pkl', processed)

def mniMask(mask):
    """Replace standard MNI mask with dilated brain mask for improved coverage"""
    import os
    # Identify standard MNI template
    old = os.path.join(os.getenv('FSLDIR'), 'data/standard/MNI152_T1_2mm.nii.gz')
    # Replace with dilated brain mask for better anatomical coverage
    if mask == old:
        mask = os.path.join(os.getenv('FSLDIR'), 'data/standard/MNI152_T1_2mm_brain_mask_dil.nii.gz')
    return mask

def mniMaskpre(mask):
    """Replace standard MNI mask with non-dilated brain mask for preprocessing"""
    import os
    # Identify standard MNI template
    old = os.path.join(os.getenv('FSLDIR'), 'data/standard/MNI152_T1_2mm.nii.gz')
    # Replace with brain mask (non-dilated) for preprocessing
    if mask == old:
        mask = os.path.join(os.getenv('FSLDIR'), 'data/standard/MNI152_T1_2mm_brain.nii.gz')
    return mask
