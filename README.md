# AnalysisMultiverse

Software for automated multiverse analysis for fMRI

## Run Instructions

__Information Updated__: 2022-03-21

> [!NOTE]
> More recently updated run instructions have been included at the end of this README. The following instructions are being retained until all the steps provided here can be verified and translated into a formal standard operating procedure (SOP).

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

__Information Updated__: 2022-06-10

- When setting a parameter with a range (i.e. low, high, step) the default behaviour is [low, high), unless a step is included in which case it will be [low, high] incremented by the step value
  
## Node Naming Conventions/Multiverse Modification

__Information Updated__: 2022-03-21

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

__Information Updated__: 2022-04-25

- To add more options to the first level FEAT analysis, the template file: nipype/interfaces/fsl/model_templates/feat_ev_none.tcl can be edited
   1. This will also require editing versatile.py lines 784 to 808 so that values can be added to the template file
       - a. In addition, SpecifyModelVersatile will need to be altered so that the produced dictionary will include the altered parameters added to the template file
       - b. Then, the workflow "info" for level1 will need to be updated so that the new parameters will be added to SpecifyModelVersatile
       - c. Finally, changes to the default.json file will need to be made to add new parameters

## Resource Allocation

__Information Updated__: 2025-04-08

- On compute canada ~1.2 days for 50 subjects x 8 pipelines with 32 CPUs, 6gb RAM per CPU
- Potential issue: There is a file cap on compute canada of 1000k (Graham), which may result in workflow crashing (likely need to get this extended)
- Generates a lot of data, peaking at ~0.83GB per subject per pipeline
   1. Running with debug set to false will delete files once they are no longer needed by the workflow
       - a. Saves a LOT of space, but if the analysis fails, it cannot be rerun from where it failed, and will restart from the beginning (i.e. progress is lost)
       - b. I think above may not be true, as only deletes intermediate files when they are no longer needed, so should be able to rerun/restart from checkpoint with debug on
       - c. As a consequence, give a buffer when requesting run time, as computation time will be wasted if program fails prior to exiting

# Steps to Run a Test Job on the Nibi HPC Cluster

__Information Updated__: 2026-07-16

## Setting Up the AnalysisMultiverse Code for the First Time with Git

At this time it is recommended to set up the code using Git since further changes are required. This will allow you to pull updates from the Brain Health Lab repository as needed.

1. Log-in to the Nibi cluster, and confirm you are in your home directory.
   > __New User Tip__:
   >
   > The command `pwd` should reveal "home/<your_user-name>", and the command prompt should be `[<your_user-name>@cluster-node ~]`.
   > Get familiar with what the command line looks like when you are in your home directory, and get comfortable using the `pwd` ("present working directory") command to check where you are.

3. Run `git config --global core.editor nano` to set Nano as your Git commit message editor.
   > __New User Tip__:
   >
   > While the latest version of Git defaults to using Nano as its text editor, the Digital Research Alliance of Canada's (DRAC) clusters do not usually have the latest package versions installed. The current default on Nibi is VIM, which is not as beginner-friendly as Nano.

4. Run `git config --global --edit` to update your name and email in Git on the cluster; this email should match your GitHub (GH) email if you want to sync with or make pull requests to our repository.

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
   
   This removes all of the unnecessary directories and files from the cluster and the local repo that were downloaded with the `main` branch.

   (Cleaning up the GitHub repo is a work in progress. Someday, it will be finished and these steps will be retired, but it is not this day.)
   > __New User Tip__:
   >
   > `-r` is a flag used with the `rm` command to trigger recursive removal, so that all the files within the given directory are removed!

11. Now run `git add -u` and `git commit` to add these changes to the local repo. Your commit message should be about removing unnecessary files for running the code on an HPC cluster.
    > __New User Tip__:
    >
    > The `-u` flag here updates the Git working tree to remove the files.

12. Change directories back to your home directory (`cd ~`) and move all the remaining AnalysisMultiverse files and subdirectories to your home directory. This can be done using the following commands:
     * `git mv AnalysisMultiverse/.git .`
     * `git mv AnalysisMultiverse/.gitignore .`
     * `git mv AnalysisMultiverse/README.md .`
     * `git mv AnalysisMultiverse/multiverse/ .`
     * `git mv AnalysisMultiverse/multiverse.py .`

> [!WARNING]
> This step moves the multiverse.py file to your home directory, which is where the code is set up to run from. If it is not in the home directory, it will not run properly.

13. Confirm the AnalysisMultiverse directory is empty (using `cd AnalysisMultiverse`, `ls -a`, then `cd ~`) before running `rmdir AnalysisMultiverse` in your home directory. This directory was just the folder all the code files arrived in, and it is unnecessary to keep it.
    > __New User Tip__:
    >
    > To use `rmdir`, the directory must be completely empty!

14. Now run `git add -u` and `git commit` to add these changes to the local repo, making an appropriate commit message.

15. In your home directory, run `ls -a >> .gitignore` to add all the files and folders from your home directory to your .gitignore again.

16. There are a lot of directories and files on the cluster - especially hidden ones - that you do not want to track with Git. In this case, we've simplified the process by adding everything. Now we are going to remove the files we ***want*** to track from the .gitignore. 
    Open the .gitignore file by running `nano -l .gitignore`.
    Make sure all the file and directory names are each on their own, separate lines.
    The additions you made to the file will be at the very end, after the file names, extensions, and directory names that we have already populated under the "Cluster" heading.
    Now, find and ***delete*** the following lines from the file:
     * multiverse/
     * README.md
     * multiverse.py
    
    Git will now ***not*** ignore these directories and files, and any changes you make to them ***will*** be tracked.
    > __New User Tip__:
    >
    > Using `-l` when you open a file with Nano will display the line numbers for the file.

> [!NOTE]
> Remember how in step 7, we added some directories and files to the .gitignore before removing them from Git and the cluster?
> This is so that if you want to update our code by pulling from GitHub, you won't re-download those unnecessary files, saving you precious storage space!

17. Now run `git add .` and `git commit` and write your commit message about updating the .gitignore to include the excess files from the GitHub repo, and extra files from the HPC cluster.

18. Now make sure all the code is runnable by running `chmod -R 755 multiverse` to change the permissions on the multiverse code directory, and run `chmod 755 multiverse.py` to change the permissions on the multiverse.py file.

19. Run `git add .` and `git commit` and write your commit message about updating the permissions. This may take a while, because this change modifies every file in the codebase!

20. It is advisable to create your data and output directories in your scratch directory.
    Use `mkdir` to create them there, and use `pwd` to copy down their exact paths to use with the final command to run the AnalysisMultiverse program.
    Make sure both directories are xrr using: `chmod -R 755 <directory name>`
    Because these directories are added to your scratch directory, they will automatically not be tracked by Git!

> [!WARNING]
> Datasets must be in BIDS format, or the code will crash when it checks the validity of the dataset!

22. To check how your configuration files are set, run `cd configuration` and in the configuration directory, run: 
     * `python -m pickle <file-name>.pkl`
        * general_configuration.pkl -> configuration for SLURM (adjust your pipelines here)
        * multiverse_configuration.pkl -> analysis parameter ranges
      
23. If necessary, you can create a new general_configuration.pkl file by running the following command in this directory:
    * `nano -l new-gen-config-pkl.py`
    This will allow you to enter updated values into a pickle file that can replace the general_configuration.pkl file currently in the repository.
    Once your changes are made, press `Ctrl-O` to write out your changes and then `Ctrl-X` to exit the Nano editor.
    Now run:
    * `python new-gen-config-pkl.py`
    This will generate an updated configuration pickle file as "general_configuration_new.pkl". You can then rename the original version or delete it, and then use `mv general_configuration_new.pkl general_configuration.pkl` to rename your updated version. Remember to document these changes in Git!

> [!NOTE]
> The code is built to divide the total time requested in the general_configuration.pkl file by the number of batches and cores requested for use. To figure out how much wall-clock time your code is going to request, convert your total requested time to seconds and divide it by the number of CPUs (general_configuration['cpu_node'\]) multiplied by the batches (general_configuration['batches'\]). SLURM jobs need at least a couple minutes just to set up. For example, a test dataset of 6 participants doing one task analyzed with 2 pipelines, using 12 CPUs and 6 batches took ~97 minutes. 

23. Assuming no rerun, and assuming a valid configuration file, the multiverse.py file can be run from your home directory using the following command: 
     * `python multiverse.py -r -d <path_to_dataset_directory_in_scratch/> -o <path_to_output_directory_in_scratch/>`
    The initial run will create the multiverse.sif container file, so it is expected to take longer than subsequent runs. 

> [!IMPORTANT]
> You may encounter problems in running your code if you made a previous attempt to run it that failed. If this occurs, go into your scratch directory and rename your data output file to something useful (but different) using `mv <previous-data-output-directory-name> failed-run-July-14`, as an example. Then use `mkdir <previous-data-output-directory-name>` to make a new, empty data output directory, and you can try running the code again by scrolling up through your previous commands using the up arrow on your keyboard.
