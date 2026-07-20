#!/bin/bash
# Code parsing notes added by GitHub Copilot 2026-07-20
# Shebang: run with Bash

# Load the Apptainer/Singularity module so container commands are available
# on the cluster
module load apptainer

# Path to the local Singularity image expected in the user's home directory.
container=~/multiverse.sif
# Local path that will be bound into the container to override nipype's plugins
# base.py if needed.
custom_base=/opt/miniconda-latest/envs/multiverse/lib/python3.8/site-packages/nipype/pipeline/plugins/base.py
#if templateflow breaks
# Optional TemplateFlow cache directory on the host to bind into the container
# as a workaround.
templates=/home/$USER/.cache/templateflow
# Host path for an IPython configuration directory used when binding into the
# container.
ipyth=/home/scratch_dir/.ipython

# If the container image file does not exist locally:
# - Attempt to build/pull it from the Docker registry (fallback commented
#   alternative uses library://).
# If pull/build fails, print an instruction to upload the image manually.
# NOTE: the script exits after this block, which means it will stop when the
#       image was originally missing even if the build/pull command succeeded
#       earlier in the block.
if [ ! -f $container ]; then
    singularity build multiverse.sif docker://gseasons/multiverse:cluster \
    #singularity pull library://gseasons/analysis/multiverse \
    || echo "Cannot access container, please upload the image into your home directory: https://cloud.sylabs.io/library/gseasons/analysis/multiverse.sif"
    exit
fi

# Create a unique IPython profile name combining the SLURM job ID and hostname.
profile=job_${SLURM_JOB_ID}_$(hostname)

# Creating the IPython profile directory/configs for controller and
# engines.
echo "Creating profile ${profile}"
ipython profile create ${profile}

# Start the IPython controller in the background, listening to all interfaces,
# using the created profile and writing logs to file. Wait 45s for it to 
# initialize.
echo "Launching controller"
ipcontroller --ip="*" --profile=${profile} --log-to-file &
sleep 45

# Launch ipengine(s) using srun so they run on compute nodes:
# - Binds passed host paths into the container:
#   - $2 -> /scratch_dir (scratch), $1 -> /data (input data)
#   - ~/multiverse/plugins_base.py is bound over nipype's base.py to inject
#     custom plugin behaviour
#   - ~/multiverse/templateflow or host templateflow cache bound to provide
#     TemplateFlow data if needed
#   - ~/.ipython or custom ipython path bound to preserve IPython config
# Line 63 is an alternative binding setup (commented out).
# Runs ipengine in the background and waits 45s for startup.
echo "Launching engines"
#if templateflow breaks
srun singularity run -B $2:/scratch_dir -e -B ~/multiverse/plugins_base.py:$custom_base -B ~/multiverse/templateflow:$templates -B ~/.ipython:$ipyth -B ~/multiverse:/code/multiverse -B $1:/data $container ipengine --profile=${profile} --location=$(hostname) --log-to-file &
#normal
#srun singularity run -B $2:/scratch_dir -e -B ~/multiverse/plugins_base.py:$custom_base -B ~/.ipython:/scratch_dir/.ipython -B ~/multiverse:/code/multiverse -B $1:/data $container ipengine --profile=${profile} --location=$(hostname) --log-to-file &
sleep 45

# Execute the main job inside the container:
#  - singularity exec runs a shell inside the container with various host
#    directories bound in.
#  - -H $2:/scratch_dir sets the container HOME to the host scratch directory
#    (useful for temporary files).
#  - Binds the custom nipype plugins base.py, TemplateFlow cache, IPython config,
#    local multiverse code (/code/multiverse), and host data directory ($1 -> /data)
#    into the container.
#  - Inside the container it activates the multiverse conda environment,
#    exports USER, and runs the Python launcher:
#        python /code/multiverse/run_multiverse.py ${3} ${profile}
#    where ${3} is the third positional argument passed to this script (e.g.,
#    a subject or config) and ${profile} is the IPython profile name.
# Commented lines 84 - 85 show alternate normal bind setups and a different
# TemplateFlow fallback.
echo "Launching Job"
#normal
#singularity exec -H $2:/scratch_dir -e -B ~/multiverse/plugins_base.py:$custom_base -B ~/.ipython:/scratch_dir/.ipython -B ~/multiverse:/code/multiverse -B $1:/data \
#if templateflow breaks
singularity exec -H $2:/scratch_dir -e -B ~/multiverse/plugins_base.py:$custom_base -B ~/multiverse/templateflow:/scratch_dir/.cache/templateflow -B ~/.ipython:$ipyth -B ~/multiverse:/code/multiverse -B $1:/data \
$container /bin/bash -c \
"source activate multiverse ; export USER=$USER ; python /code/multiverse/run_multiverse.py ${3} ${profile}"
