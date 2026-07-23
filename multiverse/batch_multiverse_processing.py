#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 19 13:12:07 2022

@author: grahamseasons
"""

# Import standard library modules for system operations and data persistence
import sys
import pickle

# Import analysis and data processing libraries
from functions import organize
import numpy as np

# Import neuroimaging data handling library for loading and processing brain imaging files
import nibabel as nib

# Import dimensionality reduction library for manifold learning techniques
from sklearn.manifold import MDS

# Import visualization libraries for creating plots and custom line collections
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

# Define the base directory path for processed data files
processed = '/scratch_dir/processed'

# MAIN PROCESSING PIPELINE (Currently Commented Out)
# This section contains the core processing logic that will run once integrated
# The workflow processes pipeline outputs and compares similarity between different analysis pipelines
#     # Extract command-line arguments: task name and script identifier
# if len(sys.argv) > 2:
#     task = sys.argv[1]
#     sq = sys.argv[2]

# # Define the output filename for the processed pipeline results
# out_frame = processed + '/{task}.pkl'.format(task=task)
# # Alternative hardcoded path for debugging: out_frame = '/Volumes/NewVolume/_i_0/rest.pkl'
# # out_frame = '/Volumes/NewVolume/_i_0/rest.pkl'
# # Set the task type to 'rest' for testing
# task= 'rest'
# # Process the task if batch script condition is met
# if True:#sq.count('batch.sh') == 1:
#     # Organize the pipeline data and extract file paths
#     paths = organize(task, out_frame)
    
#     # Load the pipeline paths dictionary from the pickled file
#     with open(paths, 'rb') as f:
#         paths = pickle.load(f)
#     # Load the pipeline generation data (hardcoded path to generation_0.pkl)
#     # This contains mapping of parameters to pipeline outcomes
#     with open('/Volumes/NewVolume/_i_0/generation_0.pkl', 'rb') as f:
#         pipelines = pickle.load(f)
#         
#     # Apply Multidimensional Scaling (MDS) to reduce high-dimensional pipeline parameter space to 2D
#     # This allows visualization of pipeline similarity based on parameter choices
#     mds = MDS()
#     embedded = mds.fit_transform(pipelines.transpose())
#     # Initialize figure and axes for visualization
#     fig = plt.figure(1)
#     ax = plt.axes()
#     # Plot all embedded pipelines in 2D space
#     plt.scatter(embedded[:,0], embedded[:,1])
#     # Highlight the first 8 pipelines in a separate color for focus
#     plt.scatter(embedded[:8,0], embedded[:8,1])
#
#     # Initialize lists to store pipeline segment connections and their similarity scores
#     segments = []
#     similarity = []
#
#     # Nested loop to compare all pairs of the first 8 pipelines
#     # This creates pairwise comparisons to calculate similarity between pipeline outputs
#     for i, x in enumerate(embedded[:8]):
#         for j, y in enumerate(embedded[:8]):
#             # Skip self-comparisons and duplicate pairs (only compare j > i)
#             if i >= j:
#                 continue
#
#             # Extract network paths for the current pipeline pair
#             paths1 = paths['pipeline'][i]['network']
#             # List to accumulate correlation statistics between pipeline outputs
#             out_stats = []
#
#             # Double loop through network nodes and their contrast output files
#             for k in range(len(paths['pipeline'][i]['network'])):
#                 for l, m in enumerate(list(paths['pipeline'][i]['network'][k]['contrast'].values())):
#                     # Get corresponding contrast file from the comparison pipeline
#                     m2 = list(paths['pipeline'][j]['network'][k]['contrast'].values())[l]
#                     # Load both contrast maps (brain images) and calculate Pearson correlation
#                     # between flattened voxel data across the entire volume
#                     out = np.corrcoef(np.array(nib.load(m).dataobj).flatten(), np.array(nib.load(m2).dataobj).flatten())[0,1]
#                     out_stats.append(out)
#
#             # Filter out NaN values and compute mean correlation across all contrasts
#             out = [abs(stat) for stat in out_stats if not np.isnan(stat)]
#             out = np.mean(out_stats)
#             # Handle NaN results by setting to 0 and skip this pipeline pair
#             if np.isnan(out):
#                 out = 0
#                 continue
#             else:
#                 pass
#                 # Optional: uncomment to take absolute value of correlation
#                 #out = abs(out)
#
#             # Store the calculated similarity score for this pipeline pair
#             similarity.append(out)
#
#             # Store the line segment coordinates connecting the two pipelines in 2D space
#             segments.append([list(x), list(y)])
#
#     # Convert similarity scores to numpy array for processing
#     similarity = np.array(similarity)
#     # Calculate absolute values for normalization
#     values = np.abs(similarity)
#     # Create a LineCollection with color mapping based on similarity scores
#     # Uses the Purples colormap with values normalized from 0 to maximum similarity
#     # Each line represents a connection between two pipelines, colored by their similarity
#     lc = LineCollection(segments, linewidths=np.full(len(segments), 1), zorder=0, cmap=plt.cm.Purples, norm=plt.Normalize(0, values.max()))
#     # Assign the similarity values to the line collection for color mapping
#     lc.set_array(similarity)
#     # Add the line collection to the plot
#     ax.add_collection(lc)
#
#     # Display the final visualization
#     plt.show()
#     # Placeholder variable (likely for debugging)
#     A=3

#
# FUTURE IMPLEMENTATION ROADMAP AND FEATURE IDEAS
# ================================================
#
# Core Data Processing Pipeline:
#   - Integrate data processing once test data becomes available
#   - Apply dimensionality reduction (MDS or t-SNE) to compress ~60 pipeline parameters to 2D space
#   - Normalize dependent variables (ROI-based metrics for resting state analysis) with default values
#
# Pipeline Clustering and Visualization:
#   - Display pipelines in 2D space to visualize their similarity based on parameter choices
#   - Add third dimension by calculating similarity scores between neighboring pipelines
#   - Weight similarity by Euclidean distance to account for spatial relationships
#   - Identify poorly matching pipeline groups and categorize parameter differences
#   - Locate optimal similarity matches between pipelines (create correlation matrices)
#   - Render similarity on plot using line thickness and opacity visualization
#     (Reference: https://scikit-learn.org/stable/auto_examples/manifold/plot_mds.html#sphx-glr-auto-examples-manifold-plot-mds-py)
#   - Iteratively refine plots to focus on differing parameters between low-similarity groups
#   - Similarly refine to examine parameters matching in high-similarity groups
#
# Advanced Analysis Features:
#   - Develop optimization algorithm for parameter selection and group comparison
#   - Create scatter plots for each significant brain region activation
#   - Show which pipelines agree on activation patterns (fade out disagreeing pipelines)
#
# Output Aggregation and Reporting:
#   - Reorganize MDS layout based on output similarity rather than parameter space
#   - Generate average maps or correlation matrices for brain regions
#   - Create intersection maps showing agreement across pipelines
#
# Edge Case Handling:
#   - Handle case where pipelines show poor spatial similarity or divergent activation patterns
#   - Implement stained glass visualization (overlay all pipelines with different colors/transparencies)
#   - Create dual brain maps: one showing average activation across all pipelines,
#     and one showing voxel-wise variance across pipelines to identify regions of agreement/disagreement

# Lines 133 - 166 are GH Copilot Synopsis of GS's Original Comments:
#TODO: THE THIRD # POINT BELOW THIS ONE

#INSERT DATA PROCESSING HERE - TO BE WRITTEN ONCE WE HAVE TEST DATA

#MULTIDIMENSIONAL SCALING TO REDUCE DIMENSIONS FROM ~60 -> 2 ( or t-SNE )
#FEED IN GA MATRIX -> REPLACE DEPENDENT VARIABLES (i.e. ROI variables if it's REHO) WITH DEFAULT VALUES (FOR REST)


#CLUSTERS PIPELINES IN 2D SO CAN SEE SIMILARITY IN TERMS OF CHOSEN PARAMETERS
#FOR DATA PRESENTATION COULD ADD ANOTHER DIMENSION OF SIMILARITY SCORE WITH PIPELINES IN NEIGHBOURHOOD (SIMILARITY WEIGHTED BY EUCLIDEAN DISTANCE TO EACH POINT)
#POOR SIMILARITY IN NEIGHBOURHOOD, CATEGORIZE DIFFERENCES BETWEEN PIPELINES TO COMPARE
#FIND ACTUAL BEST SIMILARITY BETWEEN PIPELINES (CORRELATION MATRIX TYPE THING?)
#SHOW SIMILARITY ON PLOT AS LINE THICKNESS/OPACITY https://scikit-learn.org/stable/auto_examples/manifold/plot_mds.html#sphx-glr-auto-examples-manifold-plot-mds-py
#CHECK TO SEE WHICH PARAMETERS DIFFER BETWEEN POORLY PERFORMING PIPELINES IN SAME GROUP -> REORGANIZE/REPLOT ONLY CONSIDERING THOSE
#   SAME IDEA WITH ONES THAT DO MATCH WELL

#OPTIMIZATION ALGORITHM FOR ABOVE?

#SCATTER PLOT FOR EACH BRAIN REGION WE GET SIGNIFICANT ACTIVATION -> SHOW WHICH PIPELINES AGREE (others in faded colour)

#REORGANIZE ORIGINAL MDS BY SIMILARITY OF OUTPUTS
#SHOW AVERAGE MAPS (or CORRELATION MATRICES OF BRAIN REGIONS) OR AN INTERSECTION OF ACTIVATION MAPS

#IF NONE OF THEM ARE SPATIALLY SIMILAR, OR ACTIVATION MAPS AREN'T SIMILAR: TBD
#STAINED GLASS AVERAGE (ALL DIFERENT COLOURS, TRANSPARENCIES OVERLAYED)?
#MAP OF BRAIN DISPLAYING AVERAGE ACTIVATION ACROSS PIPELINES, AND MAP WHERE EACH VOXEL REPRESENTS THE VARIANCE ACROSS PIPELINES