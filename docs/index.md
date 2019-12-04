```eval_rst
.. gem5art documentation master file, created by
   sphinx-quickstart on Mon Oct 28 14:35:02 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Zen and the art of gem5 experiments
===================================
```

The gem5art project is a set of Python modules to help make it easier to run experiments with the gem5 simulator.
gem5art contains libraries for *Artifacts, Reproducibility, and Testing.*
You can think of gem5art as a structured [protocol](https://en.wikipedia.org/wiki/Protocol_(science)) for running gem5 experiments

When running an experiment, there are inputs, steps to run the experiment, and outputs.
gem5art tracks all of these through [Artifacts](artifacts).
An artifact is a some object, usually a file, which is used as part of the experiment.

The gem5art project contains an interface to store all of these artifacts in a [database](artifacts.html#artifactdb).
This database is mainly used to aid reproducibility, for instance, when you want to go back and re-run an experiment.
However, it can also be used to share artifacts with others doing similar experiments (e.g., a disk image with a shared workload).

The database is also used to store results from [gem5 runs](run).
Given all of the input artifacts, these [runs](run.html#runs-api-documentation) have enough information to reproduce exactly the same experimental output.
Additionally, there is metadata associated with each gem5 run (e.g., the script name, script parameters, gem5 binary name, etc.) which are useful for aggregating results from many experiments.

These experimental aggregates are useful for testing gem5 as well as conducting research.
We will be using this data by aggregating the data from 100s or 1000s of gem5 experiments to determine the state of gem5's codebase at any particular time.
For instance, as discussed in the [Linux boot tutorial](boot-tutorial), we can use this data to determine which Linux kernels, Ubuntu versions, and boot types are currently functional in gem5.

----

One of the underlying themes of gem5art is that you should fully understand each piece of the experiment you're running.
To this end, gem5art requires that every artifact for a particular experiment is *explicitly* defined.
Additionally, we encourage the use of Python scripts at every level of experimentation from the workload and disk image creation to running gem5.
By using Python scripts, you can both automate and document the processes for running your experiments.

Many of the ideas used to develop gem5art came from our experience using gem5 and the pain points of running complex experiments.
Jason Lowe-Power used gem5 extensively during his PhD at University of Wisconsin-Madison.
Through this experience, he made many mistakes and lost an untold number of days trying to reproduce experiments or re-creating artifacts that were accidentally deleted or moved.
gem5art was designed to reduce the likelihood that this happens to other researchers.



```eval_rst
API documentation
-----------------

.. toctree::
   :maxdepth: 2

   intro.md
   artifacts.md
   run.md
   tasks.md
   disks.md

Tutorials
---------

.. toctree::
   maxdepth: 1

   boot-tutorial.md
   npb-tutorial.md
   spec2006-tutorial.md
   microbench-tutorial.md

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
```

