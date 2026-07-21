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

__Information Updated__: 2026-07-21

## Setting Up the AnalysisMultiverse Code for the First Time with Git

At this time it is recommended to set up the code using Git since further changes to the code are coming. This will allow you to pull updates from the Brain Health Lab repository as needed.

1. Log-in to the Nibi cluster, and confirm you are in your home directory using `pwd`.  
   > __Command Breakdown__:
   >
   > The command `pwd` ("**P**resent **W**orking **D**irectory") should reveal "home/<your_user-name>", and your current command prompt should be `[<your_user-name>@cluster-node ~]`.
   > Get familiar with what the command line looks like when you are in your home directory, and get comfortable using the `pwd` command to check where you are in the cluster file system.

2. Run `git clone https://github.com/BrainHealthLabStFX/AnalysisMultiverse.git --branch main --single-branch` to clone the AnalysisMultiverse codebase from Brain Health Lab's repository to the cluster. It is expected that this will take a couple of minutes.  
   > __Command Breakdown__:
   >
   > In this command, we are specifying that we only want the `main` branch files downloaded. If you do not specify this, you will download the entire repository, which will get you a lot of unnecessary files.

3. Move all the files and subdirectories from the downloaded AnalysisMultiverse directory to your home directory. This can be done by executing the following commands in succession:
   
   `mv AnalysisMultiverse/.git/ .`  
   `mv AnalysisMultiverse/.github/ .`  
   `mv AnalysisMultiverse/.gitignore .`  
   `mv AnalysisMultiverse/README.md .`  
   `mv AnalysisMultiverse/TODO.md .`  
   `mv AnalysisMultiverse/docs/ .`  
   `mv AnalysisMultiverse/hide/ .`  
   `mv AnalysisMultiverse/multiverse/ .`  
   `mv AnalysisMultiverse/multiverse.py .`    
   > __Command Breakdown__:
   > 
   > The `mv` command takes at least two arguments: the item to move (like a file or directory), and the place (or new name) to move it to.
   > Here, the '.' refers to the present working directory, your home directory.

> [!WARNING]
> Step 3 moves the multiverse.py file to your home directory, which is where the code is set up to run from. If the multiverse.py file is not in the home directory, it will not run properly.
     
4. Confirm the AnalysisMultiverse directory is empty (using `ls -a AnalysisMultiverse/`) before running `rmdir AnalysisMultiverse` in your home directory. This directory was just the folder all the code files arrived in, and it is unnecessary to keep it.
   > __Command Breakdown__:
   >
   > To use `rmdir` the directory must be empty! The `-a` flag displays even hidden files.

5. Now run `git status --porcelain | grep '^??' | cut -c4- >> .gitignore`
   This will add all your pre-existing cluster files and directories to your .gitignore file, keeping them separate from any updates you want to make to the AnalysisMultiverse code.
   > __Command Breakdown__:
   >
   > * `git status --porcelain`: This command produces the script-friendly short output (<xy> <path-of-object>) of `git status`, which at this point should only list your pre-existing cluster files and directories.
   > * `grep '^??'`: The command `grep` is used to find patterns that match the given argument. In this case, '^' refers to start-of-line. Git states that from the short output format, the <xy> status code for untracked files is '??'.
   > * `cut -c4-`: The command `cut` extracts parts of the input according to the flagged option and given range. The `-c` option selects specific characters, while the `4-` range specifies from the 4th character to the end of the line.
   > * `>> .gitignore`: Appends the output to the .gitignore file. Since this file already exists in the AnalysisMultiverse repository, the output of these commands is just added to the end of the file, under the "Cluster" heading.
   > * `|`: This is a pipe, which uses the output from the previous command as input for the next command.

6. Run `git config --global core.editor nano` to set Nano as your Git commit message editor.
   > __New User Tip__:
   >
   > While the latest version of Git defaults to using Nano as its text editor, the Digital Research Alliance of Canada's (DRAC) clusters usually install only the most stable versions of packages (which is not usually the most current). The current default on Nibi's Git is VIM, which is not as beginner-friendly as Nano.

7. Run `git config --global user.name "Your Name"` and `git config --global user.email youremail@email.com` to add your credentials to Git. Use the same email you use with GitHub if you plan on making pull request to make changes to the code.

8. Now run `git add .` and `git commit` to add the changes to your local repo.
   > __Command Breakdown__:
   >
   > The '.' here just stands for "all changes". Your commit message should reflect that you have updated the .gitignore file. Check out our [Contribution Guidelines for this project](docs/CONTRIBUTING.md) for recommendations on how to format your commit messages.

> [!NOTE]
> At this point, if you just want to use our code, we recommend you make ***all*** of the following changes.
>
> Otherwise, skip to step 12 if you want to have the opportunity to submit pull requests with code changes to the Brain Health Lab repository.

9. Run the following successive commands to add more files to your .gitignore:
    
   `echo "TODO.md" >> .gitignore`  
   `echo "docs/" >> .gitignore`  
   `echo "hide/" >> .gitignore`  
   `echo ".github/" >> .gitignore`
   
   This will allow you to pull updates from the Brain Health Lab repository without redownloading these unnecessary files and directories.

11. Now we'll run the following successive commands to remove those unnecessary files and directories from the cluster:
    
    `git rm TODO.md`  
    `git rm -r docs`  
    `git rm -r hide`  
    `git rm -r .github`
    
    This removes all of the unnecessary directories and files from the cluster and the local repo that were downloaded with the `main` branch.  
    > __Command Breakdown__:
    >
    > `-r` is a flag used with the `rm` command to trigger recursive removal, so that all the files within the given directory are removed!

13. Now run `git add -u` and `git commit` to add these changes to the local repo. Your commit message should be about updating the .gitignore to include the excess files from the GitHub repo, and removing these files to save storage space.
    > __Command Breakdown__:
    >
    > The `-u` flag here updates the Git working tree to remove the files.

14. Now make sure all the code is runnable by running `chmod -R 755 multiverse` to change the permissions on the multiverse code directory, and run `chmod 755 multiverse.py` to change the permissions on the multiverse.py file.
    > __Command Breakdown__:
    >
    > The `-R` flag triggers this command recursively through the entire multiverse directory. The `755` argument is changing the permissions of the "owner-group-others".
    > Permissions can be set to 'r' for read access, 'w' for write access, 'x' for executable access, and '-' for no access. Each number in the command is determined by the user-group's read-write-execute access to the file. User-group access for each of these actions is represented by a '1', and no access is represented by a '0'.
    > For example:
    > * rwe = 111 = 7
    > * rw- = 110 = 6
    > * r-- = 100 = 5
    > * --- = 000 = 0

15. Now run `git add .` and `git commit` and write your commit message about updating the permissions. This may take a while, because this change modifies every file in the codebase!

16. It is advisable to create your data and output directories in your scratch directory.  
    Use `mkdir` to create them there, and move into them using `cd <new-directory-name>`.  
    Then use `pwd` to copy down their exact paths to use with the command to run the AnalysisMultiverse program.  
    Make sure both directories are fully accessible using: `chmod -R 755 <directory-name>`  
    Because these directories are added to your scratch directory, they will automatically not be tracked by Git!

> [!WARNING]
> Datasets must be in BIDS format, or the code will crash when it checks the validity of the dataset!

15. Before running the code, check how your configuration files are set up. Go to the multiverse configuration directory (`cd ~/multiverse/configuration`), and run: 
    * `python -m pickle <file-name>.pkl`
      * general_configuration.pkl: configuration for SLURM (adjust your pipelines here)
        * especially necessary to update will be 'account' to your own allocation account, 'pipelines': 1 or 2 for a test run, 'rerun': False, 'cpu_node': 12, 'ntasks': 12, 'time': 18-00:\00:00, and 'batches': 6
      * multiverse_configuration.pkl: analysis parameter ranges

16. You can create a new general_configuration.pkl file by running the following command in this directory:
    
    `nano -l new-gen-config-pkl.py`
    
    This will allow you to enter updated values into a pickle file that can replace the general_configuration.pkl file currently in the repository.
    Once your changes are made, press `Ctrl-O` to write out your changes and then `Ctrl-X` to exit the Nano editor.  
    
    Now run:
    
    `python new-gen-config-pkl.py`
    
    This will generate an updated configuration pickle file as "general_configuration_new.pkl". You can then rename the original version or delete it, and then use `mv general_configuration_new.pkl general_configuration.pkl` to rename your updated version. Remember to document these changes in Git!

> [!NOTE]
> The code is built to divide the total time requested in the general_configuration.pkl file by the number of batches and cores requested for use. To figure out how much wall-clock time your code is going to request, convert your total requested time to seconds and divide it by the number of CPUs (general_configuration['cpu_node'\]) multiplied by the batches (general_configuration['batches'\]). SLURM jobs need at least a couple minutes just to set up.
> 
> For example, a test dataset of 6 participants doing one task analyzed with 2 pipelines, using 12 CPUs and 6 batches took ~97 minutes.

17. Before your initial run, you must build the container. If you do not do this manually, the code will only build the container and then immediately exit, not processing any data. Use the following commands in succession to build to container:
    
    `module load apptainer`  
    -> loads the Apptainer module required to build the container
    
    `apptainer build multiverse.sif ~/multiverse/build_files/multiverse.def`  
    -> Apptainer builds the multiverse.sif container image from the multiverse.def file
    
    The created container is ~5.9 GB, so the set-up will take some time - this is completely normal!

19. Now, assuming no rerun, and assuming a valid configuration file, the multiverse.py file can be run from your home directory using the following command: 
    `python multiverse.py -r -d <path-to-dataset-directory-in-scratch/> -o <path-to-output-directory-in-scratch/>`

> [!IMPORTANT]
> You may encounter problems in running your code if you made a previous attempt to run it that failed. If this occurs, go into your scratch directory and rename your data output file to something useful (but different) using `mv <data-output-directory-name> failed-<data-output-directory-name>`, as an example. Then use `mkdir <data-output-directory-name>` to make a new, empty data output directory, and you can try running the code again by scrolling up through your previous entered commands using the up arrow on your keyboard.

Congratulations! You have now run the AnalysisMultiverse! 

If you need further guidance for working on the cluster, check out Digital Research Alliance's [technical documentation](https://docs.alliancecan.ca/wiki/Technical_documentation).
