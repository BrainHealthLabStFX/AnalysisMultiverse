# AnalysisMultiverse

Software for automated multiverse analysis for fMRI

## TODO

- FIX CHECKPOINTS/MAKE CONSISTENT. For clarity, this means that if a run fails, restarting with rerun set to True should use the last generated checkpoint_crash file. Double check that setting DEBUG to FALSE will allow program to be rerun from wherever it last left off (but this should be the default functionality). Check that rerun in debug mode doens't start from the beginning, I think default behaviour might cause software to regenerate the directed graph of pipelines, and go node by node, instead of skipping to where it left off. Double check what rerun behaviour accomplishes with small sample/few pipelines
- Enable running the program in 2 steps -> Initially lower resources are needed to generate the directed graph (can only use 1 CPU), but once analysis actually starts need increased CPUs and memory. Default function should be to initially run program to generate graph, create a checkpoint file, and then automatically rerun with the typical increased resources (this may only apply if not running in batches).
- MAKE SURE CODE SHOULD STOP IF WRONG VALUE ENTERED INTO ATLAS GUI OR BE REPLACED BY DEFAULT

## Run Instructions

- Launch Terminal
  1. For local run 'python /PATH/TO/MULTIVERSE.PY/multiverse.py -r -d /PATH/TO/BIDS_DATA -o /PATH/TO/OUTPUT_FOLDER'
  2. For cluster run 'python /PATH/TO/MULTIVERSE.PY/multiverse.py -c'
      - a. Configure desired settings and parameter space for the cluster (select SLURM for running mode)
      - b. After configuration copy files and directories (excluding updated, hide) to compute cluster
      - c. Run step 1
  3. To rerun an analysis using the same pipelines as a prior run: 'python /PATH/TO/MULTIVERSE.PY/multiverse.py -r -rr -d /PATH/TO/BIDS_DATA -o /PATH/TO/OUTPUT_FOLDER'
      - a. This requires the output directory to contain the reproducibility directory (including generation files) of the analysis to reproduce
      - b. Similarly, the files multiverse/configuration/general_configuration.pkl and multiverse/configuration/multiverse_configuration.pkl should be the same as the analysis to be reproduced
  4. Note: It may take a long time from the workflow calling .run() to actual execution (connecting nodes/inputs/outputs) - important in multiverse, as the more nodes, subjects, and pipelines the longer this will take (important to ask if some way to request fewer resources while this happening, then step up to needed amount once starts running)
  5. Recent update works by submitting multiple partial jobs (i.e. 25 jobs for 200 pipelines -> 25 nodes with 32 cpus, for 8 pipelines) instead of 1 massive job
      - a. Calculates runtime for each job by subdividing total given runtime (for 1 massive job) by the number of subjobs
      - b. If using split_half (still in development/untested), remains as 1 large job, as generations act as batches, and are dependent on each other

## GUI Note

- When setting a parameter with a range (i.e. low, high, step) the default behaviour is [low, high), unless a step is included in which case it will be [low, high] incremented by the step value
  
## Node Naming Conventions/Multiverse Modification

- To add more parameters to multiverse analysis, edit the default.json file in configuration
  1. Find the specific node in the workflow, cross reference with changeable options for nipype interface
  2. Add new entry in format seen in json file
      - a. Non-numeric parameters need a value_map parameter to indicate it will be aliased in the genetic algorithm
      - b. Default category indicates the index of the default value
      - c. alias is what is displayed in GUI
      - d. name is the interface option as displayed in nipype documentation
- Naming conventions
  1. Nodes starting with a capital F (i.e. Fsmooth) are user defined functions with the ability for dynamic function inputs, and letters after F must be lowercase
      - a. Function parameters must follow this naming convention:
          - 1. For variables only affecting the function and not internal nodes -> all lower case, one word (no underscore)
          - 2. For nodes inside the function -> nodename_nipypeinterfaceparametername (similar to the above section, nipypeinterfaceparametername is copied exactly from nipype including underscores)
      - b. To enable dynamic parameter assignment, there must be a linebreak before the workflow is run inside a function (i.e. randomline \n\n workflow.run() or randomline \n\n node.run())
          - 1. If assigning the output of node.run() to a variable, the variable name cannot have an underscore
  2. Entries in json file starting with ~construct~ (i.e. ~construct~Finfo) indicate a dictionary will be constructed from the provided information, and passed to the function (i.e. Finfo) in the format of dictionaryname_parametername
  3. Entries starting with ! (i.e. !correction) indicate that the value will be copied from another parameter as defined in default_links.json
      - a. node_to_add and node_to_copy indicate the name of the parameter to add, and the node the values will be copied from, respectively
          - 1. An additional entry of on_off can be used to modify the above, where the parameter being copied is dependent on the node specified with on_off (i.e. true -> use value, false -> no action)
      - b. verify and values together alter the construction of a dictionary, with values specifying the scenario in which verify is added to the dictionary
      - c. node_to_edit is used if there are mutually exclusive options that must be handled
          - 1. on_off is the node which controls mutual exclusivity, switch indicates the value of on_off that is mutually exclusive with node_to_edit
  4. Naming conventions MUST be followed as they are what enable the dynamic creation of custom pipelines which share data as long as possible, and don't force an analysis of all permutations of multiverse options

## Adding Additional FEAT Options

- To add more options to the first level FEAT analysis, the template file: nipype/interfaces/fsl/model_templates/feat_ev_none.tcl can be edited
   1. This will also require editing versatile.py lines 784 to 808 so that values can be added to the template file
       - a. In addition, SpecifyModelVersatile will need to be altered so that the produced dictionary will include the altered parameters added to the template file
       - b. Then, the workflow "info" for level1 will need to be updated so that the new parameters will be added to SpecifyModelVersatile
       - c. Finally, changes to the default.json file will need to be made to add new parameters

## Resource Allocation

- On compute canada ~1.2 days for 50 subjects x 8 pipelines with 32 CPUs, 6gb RAM per CPU
- Potential issue: There is a file cap on compute canada of 1000k (Graham), which may result in workflow crashing (likely need to get this extended)
- Generates a lot of data, peaking at ~0.83GB per subject per pipeline
   1. Running with debug set to false will delete files once they are no longer needed by the workflow
       - a. Saves a LOT of space, but if the analysis fails, it cannot be rerun from where it failed, and will restart from the beginning (i.e. progress is lost)
       - b. I think above may not be true, as only deletes intermediate files when they are no longer needed, so should be able to rerun/restart from checkpoint with debug on
       - c. As a consequence, give a buffer when requesting run time, as computation time will be wasted if program fails prior to exiting

# Steps to Run a Test Job on the Nibi HPC Cluster

Process Updated: 2026-07-09

## Setting Up the AnalysisMultiverse Code for the First Time with Git

At this time it is recommended to set up the code using Git since further changes are required.

1. Log-in to the Nibi cluster, and confirm you are in your home directory.
   > __New User Tip__:
   >
   > The command `pwd` should reveal "home/<your_user-name>", and the command prompt should be `[<your_user-name>@cluster-node ~]`.
   > Get familiar with what the command line looks like when you are in your home directory, and get comfortable using the `pwd` ("present working directory") command to check where you are.

3. Run `git config --global core.editor nano` to set Nano as your Git commit message editor.
   > __New User Tip__:
   >
   > While the latest version of Git defaults to using Nano as its text editor, the Digital Research Alliance of Canada's (DRAC) clusters do not usually have the latest package versions installed. The current default on Nibi is VIM, which is not as beginner-friendly as Nano.

4. Run `git config --global --edit` to update your name and email in Git on the cluster; this email should match your GitHub (GH) email if you want to sync with your own account or make pull requests to our repository.

5. Run `git clone https://github.com/BrainHealthLabStFX/AnalysisMultiverse.git --branch main --single-branch` to clone the AnalysisMultiverse codebase from Brain Health Lab's repository to the cluster.
   > __New User Tip__:
   >
   > In this command, we are specifying that we only want the `main` branch files downloaded. If you do not specify wanting only the `main` branch, you will get a lot of unnecessary files downloaded, such as the documentation website build.

6. Run `cd AnalysisMultiverse` to move into the codebase directory once it has finished downloading.
   > __New User Tip__:
   >
   > `cd` = Change Directory

7. Now run `ls -a >> .gitignore` to add all the files and folders from the AnalysisMultiverse directory to your .gitignore.
   Don't worry - we will be updating the .gitignore a few more times!
   > __New User Tip__:
   >
   > The `-a` flag for the `ls` (list) command will show even hidden files and directories, like those that start with a period, like ".gitignore".
   > The `>>` pipes the output of the `ls` command as an appendment to a file, and here we have specified the `.gitignore` file. 
   > Appending to a file means that the output data is added onto the end of the file instead of overwriting the original data.

8. Now run `git add .` and `git commit` to add this change to your local repo.
   > __New User Tip__:
   >
   > The '.' here just stands for "all changes". Your commit message should reflect that you have updated the .gitignore file. Check out our [Contribution Guidelines for this project](docs/CONTRIBUTING.md) for recommendations on how to format your commit messages.

9. Now run the following commands:
    * `git rm -r hide`
    * `git rm -r docs`
    * `git rm -r .github`
    * `git rm -r .spyproject`
    * `git rm .DS_Store`
    * `git rm MultiverseNotes_Gurpreet.docx`
   
   This removes all of the unnecessary directories and files from the cluster and the local repo that were downloaded with the `main` branch.

   (Someday, we will cleanse the GitHub repo, but it is not this day.)
   > __New User Tip__:
   >
   > `-r` is a flag used with the `rm` command to trigger recursive removal, so that all the files within the given directory are removed!

11. Now run `git add -u` and `git commit` to add these changes to the local repo. Your commit message should be about removing unnecessary files for running the code on an HPC cluster.
    > __New User Tip__:
    >
    > The `-u` flag here updates the Git working tree to remove the files.

12. Change directories back to your home directory (`cd ~`) and move all the remaining AM files and subdirectories to your home directory. This can be done using the following commands:
     * `git mv AnalysisMultiverse/.git .`
     * `git mv AnalysisMultiverse/.gitignore .`
     * `git mv AnalysisMultiverse/README.md .`
     * `git mv AnalysisMultiverse/multiverse/ .`
     * `git mv AnalysisMultiverse/multiverse.py .`

13. Confirm the AnalysisMultiverse directory is empty (using `cd AnalysisMultiverse`, `ls -a`, then `cd ~`) before running `rmdir AnalysisMultiverse` in your home directory.
    > __New User Tip__:
    >
    > To use `rmdir`, the directory must be completely empty!

14. Now run `git add -u` and `git commit` to add these changes to the local repo, making an appropriate commit message.

15. In your home directory, run `ls -a >> .gitignore` to add all the files and folders from your home directory to your .gitignore again.

16. There are a lot of directories and files on the cluster - especially hidden ones - that you do not want to track with Git, so in this case, we've simplified the process by adding everything. Now we are going to remove the files we ***want*** to track from the .gitignore. 
    Open the .gitignore file by running `nano -l .gitignore`.
    Make sure all the file and directory names are each on their own, separate lines.
    You'll likely want to add 'slurm*.out' to the file so that your SLURM output files are not tracked - this makes them less cumbersome to move around.
    Now, find and ***delete*** the following lines from the file:
     * multiverse/
     * README.md
     * multiverse.py
    
    Git will now ***not*** ignore these directories and files, and any changes you make to them ***will*** be tracked.
    > __New User Tip__:
    >
    > Using `-l` when you open a file with Nano will display the line numbers for the file.

> [!NOTE]
> Remember how in step 6, we added some directories and files to the .gitignore before removing them from Git and the cluster?
> This is so that if we want to update our code by pulling from GitHub, we won't re-download those unnecessary files!

17. Now run `git add .` and `git commit` and write your commit message about updating the .gitignore to include the excess files from the GitHub repo, and extra files from the HPC cluster.

18. Now make sure all the code is runnable by running `chmod -R 755 multiverse` to change the permissions on the `multiverse/` code directory, and run `chmod 755 multiverse.py` to change the permissions on the `multiverse.py` file.

19. Run `git add .` and `git commit` and write your commit message about updating the permissions. This may take a while, because this change modifies every file in the codebase!

20. It is advisable to create your data and output directories in your `scratch/` directory.
    Use `mkdir` to create them there, and use `pwd` to copy down their exact paths to use with the final command to run the Analysis Multiverse program.
    Make sure both directories are rrx using: `chmod -R 755 <directory name>`
    Because these directories are added to your `scratch/` they will automatically not be tracked by Git!

> [!WARNING]
> Datasets must be in BIDS format, or the code will crash when it checks the validity of the dataset!

22. To check how your configuration files are set, run `cd configuration` and in the `configuration/` directory, run: 
     * `python -m pickle <file-name>.pkl`
        * `general_configuration.pkl` -> configuration for SLURM (adjust your pipelines here)
        * `multiverse_configuration.pkl` -> analysis parameter ranges

23. Assuming no rerun, and assuming a valid configuration file, the `multiverse.py` file must be run from your home directory using the following command: 
     * `python multiverse.py -r -d <path_to_dataset_directory_in_scratch/> -o <path_to_output_directory_in_scratch/>`
    The initial run will create the `multiverse.sif` container file so is expected to take longer than usual.
