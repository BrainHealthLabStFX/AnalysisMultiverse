#!/bin/bash

module load apptainer
# To deal with the ipyparallel errors, adding in MK's recommended venv (lines 5 - 12)
module load StdEnv/2023
module load Python

virtualenv --no-download venv
source venv/bin/activate

pip install --no-index --upgrade pip
pip install --no-index ipyparallel

container=~/multiverse.sif
custom_base=/opt/miniconda-latest/envs/multiverse/lib/python3.8/site-packages/nipype/pipeline/plugins/base.py
#if templateflow breaks
templates=/home/$USER/.cache/templateflow
ipyth=/scratch_dir/.ipython


if [ ! -f $container ]; then
    singularity build multiverse.sif docker://gseasons/multiverse:cluster || \
    echo "Cannot access container, please upload the image into your home directory: https://cloud.sylabs.io/library/gseasons/multiverse/multiverse.sif"
    exit
fi

profile=job_${SLURM_JOB_ID}_$(hostname)


echo "Creating profile ${profile}"
ipython profile create ${profile}

echo "Launching controller"
ipcontroller --ip="*" --profile=${profile} --log-to-file &
sleep 45

echo "Launching engines"
#if templateflow breaks
srun singularity run -B $2:/scratch_dir -e -B ~/multiverse/plugins_base.py:$custom_base -B ~/multiverse/templateflow:$templates -B ~/multiverse:/code/multiverse -B $1:/data $container ipengine --profile=${profile} --location=$(hostname) --log-to-file &
#normal
#srun singularity run -B $2:/scratch_dir -e -B ~/multiverse/plugins_base.py:$custom_base -B ~/.ipython:/scratch_dir/.ipython -B ~/multiverse:/code/multiverse -B $1:/data $container ipengine --profile=${profile} --location=$(hostname) --log-to-file &
sleep 45
echo "Launching Job"


#normal
#singularity exec -H $2:/scratch_dir -e -B ~/multiverse/plugins_base.py:$custom_base -B ~/.ipython:/scratch_dir/.ipython -B ~/multiverse:/code/multiverse -B $1:/data \
#if templateflow breaks


singularity exec -B $2:/scratch_dir -e -B ~/multiverse/plugins_base.py:$custom_base -B ~/multiverse/templateflow:/scratch_dir/.cache/templateflow -B ~/multiverse:/code/multiverse -B $1:/data \
$container /bin/bash -c \
"source activate multiverse ; export USER=$USER ; python /code/multiverse/batch_multiverse.py ${3} ${4} ${profile}"

JOB_CHECK=$(sq)

#normal
#singularity exec -H $2:/scratch_dir -e -B ~/multiverse/plugins_base.py:$custom_base -B ~/.ipython:/scratch_dir/.ipython -B ~/multiverse:/code/multiverse -B $1:/data \
#if templateflow breaks


singularity exec -B $2:/scratch_dir -e -B ~/multiverse/plugins_base.py:$custom_base -B ~/multiverse/templateflow:/scratch_dir/.cache/templateflow -B ~/multiverse:/code/multiverse -B $1:/data \
$container /bin/bash -c \
"source activate multiverse ; export USER=$USER ; python /code/multiverse/batch_multiverse_processing.py ${4} '${JOB_CHECK}'"
