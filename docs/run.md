# Run

## Introduction
Each gem5 experiment is wrapped inside a run object which is eventually executed using [Celery](http://www.celeryproject.org/) scheduler (discussed in the next section). gem5art uses a class gem5Run which contains all information required to run a gem5 experiment. gem5Run interacts with the Artifact class of gem5art to ensure reproducibility of gem5 experiments and also stores the current gem5Run object and the output results in the database for later analysis.

## SE and FS mode runs

Next are two methods (for SE (system-emulation) and FS (full-system) modes of gem5) from gem5Run class which give an idea of the required arguments from a user's perspective to create a gem5Run object:

```python
@classmethod
def createSERun(cls,
                gem5_binary: str,
                run_script: str,
                outdir: str,
                gem5_artifact: Artifact,
                gem5_git_artifact: Artifact,
                run_script_git_artifact: Artifact,
                *params: str,
                timeout: int = 60*15) -> 'gem5Run':
.......

@classmethod
def createFSRun(cls,
                gem5_binary: str,
                run_script: str,
                outdir: str,
                gem5_artifact: Artifact,
                gem5_git_artifact: Artifact,
                run_script_git_artifact: Artifact,
                linux_binary: str,
                disk_image: str,
                linux_binary_artifact: Artifact,
                disk_image_artifact: Artifact,
                *params: str,
                timeout: int = 60*15) -> 'gem5Run':
.......
```

For the user it is important to understand different arguments passed to run objects:

- gem5_binary: path to the actual gem5 binary to be used
- run_script: path to the python run script that will be used with gem5 binary
- outdir: path to the directory where gem5 results should be written
- gem5_artifact: gem5 binary git artifact object
- gem5_git_artifact: gem5 source git repo artifact object
- run_script_git_artifact: run script artifact object
- linux_binary (only full-system): path to the actual linux binary to be used (used by run script as well)
- disk_image (only full-system): path to the actual disk image to be used (used by run script as well)
- linux_binary_artifact (only full-system): linux binary artifact object
- disk_image_artifact (only full-system): disk image artifact object
- params: other params to be passed to the run script
- timeout: longest time in seconds for which the current gem5 job is allowed to execute

The artifact parameters (gem5_artifact, gem5_git_artifact, and run_script_git_artifact) are used to ensure this is reproducible run.
Apart from the above mentioned parameters, gem5Run class also keeps track of other features of a gem5 run e.g. start_time, end_time,
current status of gem5 run, kill_reason (if the run is finished) etc.

While the user can write their own run_script to use with gem5 (with any command line arguments), currently when gem5Run object is created for a full-system experiment using createFSRun method, it is assumed that the path to the linux_binary and disk_image is passed to the run_script on the command line (as arguments of the createFSRun method),

## Searching the Database to find Runs

Once you start running the experiments with gem5 and want to know the status of those runs, you can look at the gem5Run artifacts in the database.
For this purpose, gem5art provides a method `getRuns`, which you can use as follows:

```python
import gem5art.run
for i in gem5art.run.getRuns(fs_only=False, limit=100):print(i)
```

The documentation on [getRuns](run.html#gem5art.run.getRuns) is available at the bottom of this page.

```
TO DO: Add examples of new getRuns methods as well.
```

## Runs API Documentation
```eval_rst
Run
---

.. automodule:: gem5art.run
    :members:
    :undoc-members:
```
