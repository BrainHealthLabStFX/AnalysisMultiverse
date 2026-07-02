#!/bin/bash

# To read through this code file, start at line 4.
# Ensure apptainer module is loaded on the cluster before code runs:
module load apptainer

# Set multiverse.sif as `container` if it exists in the home directory:
container=~/multiverse.sif
# Set batch.sh script as `batch_sh`:
batch_sh=~/multiverse/configuration/batch.sh
# Set data-output-path($2)/processed/reproducibility as `reproducibility`:
reproducibility=$2/processed/reproducibility
# Note: These assignments are not creating directories, they are simply 
#       creating a string meant to represent a location that we expect
#       to exist when the time comes in the code to call on it.

# Check if the container exists:
if [ ! -f $container ]; then
    # If it doesn't, build it!
    # Note: singularity commands still work with apptainer
    singularity build multiverse.sif docker://gseasons/multiverse:cluster || \
    echo "Cannot access container, please upload the image into your home directory: https://cloud.sylabs.io/library/gseasons/multiverse/multiverse.sif"
    # If the def file cannot be found, notify the user and exit.
    exit
fi

# Note: Again, this is exporting a location that we expect to exist when 
#       it gets called on, this doesn't create the file itself.
export REQUESTS_CA_BUNDLE=$PWD/cacert.pem

# Bind mounts:
#     * output_path:/scratch_dir
#     * home/multiverse:/code/multiverse
#     * data_path:/data
# Then runs the following commands in a terminal inside the container:
#     * source activate multiverse (this activates the `multiverse` virtual environment)
#     * export USER=$USER (set the user environmental variable to the same as outside the container)
#     * python /code/multiverse/run_multiverse.py ${3} (use python to execute run_multiverse.py, 
#                                                       feeding it the fourth command line argument 
#                                                       used to run the current script, the rerun argument)
singularity exec -B $2:/scratch_dir -B ~/multiverse:/code/multiverse -B $1:/data $container /bin/bash -c "source activate multiverse; export USER=$USER ; python /code/multiverse/run_multiverse.py ${3}"

# After running the run_multiverse.py code, for each file in the reproducibility directory:
# loop over the files in $reproducibility whose names contain "_workflow_", and end in ".pkl"
# Note: This loop has an indentation of a single space.
 for filename in $reproducibility/*_workflow_*.pkl; do
     # This sections compares a filename to a regular expression, as explained by Claude Sonnet 4.6:
     #     - ^ refers to the start of a string
     #     - .*/ refers to any characters followed by a slash, so groups together anything within the 
     #       directory, basically, since it "eats" the directory path
     #     - (.*)_workflow_ captures group 1: any characters, followed by literal "_workflow_"
     #     - (.*) captures group 2: any characters
     #     - .pkl captures the literal ".pkl" - the . can represent any character, technically, but in 
     #       doing that also captures a literal .
     #        e.g. output/processed/reproducibility/sub01_workflow_batch3.pkl
     #     - .*/ consumes "~/output/processed/reproducibility/"
     #     - Group 1 task captures "sub01"
     #           - _workflow_ matches literally
     #     - Group 2 task captures "batch3"
     #           - .pkl matches literally
     #
     # When the regex match succeeds in [[ ]], bash will populate the BASH_REMATCH array, where [0] is 
     # the whole match, [1] = task 1 match ("sub01"), and [2] = task 2 match ("batch3").
     #
     # The `&&` chaining means that ONLY set the `task` and `batch` variables if the regex actually matches.
     #
     # This has the potential for a hidden hiccup, in that `task` and `batch` keep whatever values they have 
     # from the previous loop iteration, since there is no `else` clause to reset them, which could potentially 
     # silently submit a job with stale `task`/`batch` names if a filename doesn't fit the expected pattern 
     # for some reason.
     [[ $filename =~ ^.*/(.*)_workflow_(.*).pkl ]] && task=${BASH_REMATCH[1]} && batch=${BASH_REMATCH[2]}
     # This line submits a SLURM job using the 4th - 8th arguments passed to THIS script, so
     # $4 = config[nodes], $5 = config[ntasks], $6 = config[account], $7 = config[time], $8 = config[mem].
     # It then calls on the batch.sh script, providing batch.sh the data path, the output path, the batch, 
     # and the task as parameters.
     sbatch --nodes=$4 --ntasks=$5 --account=$6 --time=$7  --mem=$8 $batch_sh $1 $2 $batch $task
     # The script then pauses for 45 seconds before submitting the next job, so as to not overwhelm the scheduler.
     sleep 45
 done

### --time=04:00:00 (for testing)
### change it back to --time=$7 , --mem=$8 , --ntasks=$5
