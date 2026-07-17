#!/bin/bash

# Code parsing notes added by GitHub Copilot 2026-07-17
#   Summary of what's documented:

#   1. Module loading - Explains HPC cluster setup (Apptainer, Python, environment)
#   2. Virtual environment - Details venv creation and ipyparallel installation for distributed computing
#   3. Container setup - Documents container paths, bind mounts, and fallback build logic
#   4. Profile creation - Explains unique job profiling for concurrent jobs
#   5. Controller launch - Details IPython controller initialization and network configuration
#   6. Engine launch - Documents worker process setup with all bind mount mappings (scratch, plugins, templates, code, data)
#   7. Main pipeline execution - Explains the analysis workflow orchestration
#   8. Post-processing - Documents results collection and job verification

#   Comments explain the "why" and "what" behind each HPC-specific pattern, container binding strategy, and parameter passing.

# Load required HPC cluster modules for containerization and Python support
# Apptainer (formerly Singularity) is used for running containerized applications
module load apptainer
# StdEnv/2023 provides the standard environment configuration for the cluster
module load StdEnv/2023
# Python module provides the base Python environment
module load Python

# Create and activate a virtual environment to isolate ipyparallel installation
# --no-download flag ensures pip uses cached packages available on the cluster
virtualenv --no-download venv
# Activate the virtual environment to use its isolated Python packages
source venv/bin/activate

# Upgrade pip and install ipyparallel (required for distributed task execution)
# --no-index flag uses only locally cached packages to avoid network issues on compute nodes
pip install --no-index --upgrade pip
pip install --no-index ipyparallel

# Set container image path to the Apptainer/Singularity container file in the home directory
container=~/multiverse.sif
# Path to the custom nipype base plugin file that is bound into the container
# This allows using a modified version of nipype's pipeline plugin
custom_base=/opt/miniconda-latest/envs/multiverse/lib/python3.8/site-packages/nipype/pipeline/plugins/base.py
# Cache directory for templateflow (neuroimaging template data) if needed
templates=/home/$USER/.cache/templateflow
# IPython directory for parallel engine configuration, mounted from scratch storage
ipyth=/scratch_dir/.ipython

# Verify that the container image exists; if not, attempt to build it from Docker Hub
# The container includes all dependencies needed for the multiverse analysis
if [ ! -f $container ]; then
    # Build the container image from the published Docker image on Sylabs Cloud
    singularity build multiverse.sif docker://gseasons/multiverse:cluster || \
    # If build fails, display instructions for manually uploading the container
    echo "Cannot access container, please upload the image into your home directory: https://cloud.sylabs.io/library/gseasons/multiverse/multiverse.sif"
    exit
fi

# Create a unique profile name for this job using the SLURM job ID and hostname
# This allows multiple concurrent jobs to maintain separate IPython profiles
profile=job_${SLURM_JOB_ID}_$(hostname)


# Create a new IPython profile for this job's controller and engines
# The profile contains configuration for the parallel computing cluster
echo "Creating profile ${profile}"
ipython profile create ${profile}

# Start the IPython controller process that will manage the parallel job distribution
# --ip="*" allows connections from any network interface (needed on HPC clusters)
# --profile specifies which profile configuration to use
# --log-to-file enables logging for debugging purposes
echo "Launching controller"
ipcontroller --ip="*" --profile=${profile} --log-to-file &
# Wait 45 seconds to ensure the controller is fully initialized before starting engines
sleep 45

# Launch the IPython parallel engines inside the Singularity container
# These worker processes execute the actual computational tasks
echo "Launching engines"
# Bind mounts connect directories on the host to paths inside the container:
#   $2:/scratch_dir - temporary working directory for scratch files
#   custom_base (plugins_base.py) - modified nipype pipeline plugin
#   templateflow - neuroimaging template library cache
#   ~/multiverse:/code/multiverse - the multiverse analysis code
#   $1:/data - input data directory
srun singularity run -B $2:/scratch_dir -e -B ~/multiverse/plugins_base.py:$custom_base -B ~/multiverse/templateflow:$templates -B ~/multiverse:/code/multiverse -B $1:/data $container ipengine --profile=${profile} --location=$(hostname) --log-to-file &
# Alternative: Normal configuration using ~/.ipython instead of templateflow
#srun singularity run -B $2:/scratch_dir -e -B ~/multiverse/plugins_base.py:$custom_base -B ~/.ipython:/scratch_dir/.ipython -B ~/multiverse:/code/multiverse -B $1:/data $container ipengine --profile=${profile} --location=$(hostname) --log-to-file &
# Wait 45 seconds for engines to connect to the controller
sleep 45
echo "Launching Job"


# Execute the main multiverse analysis pipeline inside the container
# This script orchestrates the entire neuroimaging analysis workflow
# Alternative: Normal configuration using ~/.ipython instead of templateflow
#singularity exec -H $2:/scratch_dir -e -B ~/multiverse/plugins_base.py:$custom_base -B ~/.ipython:/scratch_dir/.ipython -B ~/multiverse:/code/multiverse -B $1:/data \

# Primary execution: Uses templateflow cache for neuroimaging templates
# The bind mounts ensure all necessary data and code are accessible inside the container
singularity exec -B $2:/scratch_dir -e -B ~/multiverse/plugins_base.py:$custom_base -B ~/multiverse/templateflow:/scratch_dir/.cache/templateflow -B ~/multiverse:/code/multiverse -B $1:/data \
$container /bin/bash -c \
"source activate multiverse ; export USER=$USER ; python /code/multiverse/batch_multiverse.py ${3} ${4} ${profile}"

# Capture the queue status showing all running parallel jobs
# This is used to monitor task completion in the post-processing phase
JOB_CHECK=$(sq)

# Alternative: Normal configuration using ~/.ipython instead of templateflow
#singularity exec -H $2:/scratch_dir -e -B ~/multiverse/plugins_base.py:$custom_base -B ~/.ipython:/scratch_dir/.ipython -B ~/multiverse:/code/multiverse -B $1:/data \

# Execute the post-processing/results collection script inside the container
# This processes the outputs from batch_multiverse.py after parallel tasks complete
# Uses the job queue status (${JOB_CHECK}) to verify all jobs have finished
singularity exec -B $2:/scratch_dir -e -B ~/multiverse/plugins_base.py:$custom_base -B ~/multiverse/templateflow:/scratch_dir/.cache/templateflow -B ~/multiverse:/code/multiverse -B $1:/data \
$container /bin/bash -c \
"source activate multiverse ; export USER=$USER ; python /code/multiverse/batch_multiverse_processing.py ${4} '${JOB_CHECK}'"
