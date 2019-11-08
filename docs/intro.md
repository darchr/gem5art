
# Zen and the art of gem5 experiments

<!--
## Getting this repository
**Note: Please use --recursive flag with git clone while cloning this repo, as it uses git sub-modules.**
```
git clone --recursive git@github.com:darchr/fs-x86-test
```

If you forget to clone with `--recursive` flag, you can run the following to initialize the submodules.

```
git submodule update --init --recursive
```
-->

## Introduction
The primary motivation behind gem5art is to provide an infrastructure to use a structured approach to run experiments with gem5. Particular goals of gem5art include:

- structured gem5 experiments
- easy to use
- resource sharing
- reproducibility
- easy to extend
- documentation

gem5art is mainly composed of the following components:

- a database to store artifacts
- python objects to wrap gem5 experiments (gem5Run)
- a celery worker to manage gem5 jobs (Tasks)

The process of performing experiments (starting from scratch) can quickly become complicated due to involvement of multiple components.
As an example, following is a diagram which shows the interaction that takes place among different components (artifacts) while running 
full-system experiments with gem5.

![](art.png)

Everything, in this example, is contained in a base git repository (base repo) artifact which can keep track of changes in files not tracked by other repositories.
packer is a tool to generate disk images and serves as an input to the disk image artifact. gem5 source code repo artifacts serves as an input to two other artifacts (gem5 binary and m5 utility).
linux source repository and base repository (specifically kernel config files) are used to build the disk image and multiple artifacts then generate the final results artifact.

gem5art serves as a tool/infrastructure to streamline this entire process and keeps a track of things as they change thus leading to reproducible runs. Moreover, it allows to share the 
artifacts, used in above example, among multiple users.
