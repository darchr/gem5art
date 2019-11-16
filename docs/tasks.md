# Tasks

## Introduction

The actual gem5 experiment is executed with the help of [Celery](http://www.celeryproject.org/).
Celery server can run many gem5 tasks asynchronously. Once a user creates a gem5Run object (discussed previously) while using gem5art, this object needs to be passed to a method run_gem5_instance() registered with Celery app, which is responsible for starting a Celery task to run gem5.

Celery server can be started with the following command:

```sh
celery -E -A gem5art.tasks.celery worker --autoscale=[number of workers],0
```

This will start a server with events enabled that will accept gem5 tasks as defined in gem5art.
It will autoscale from 0 to desired number of workers.

<!--Then, you can write a script (e.g., `launch_tests.py`) which will first create all of the required artifacts and will call the `run` task defined in gem5art.-->

## Monitoring Celery
You can monitor the celery cluster doing the following:

```sh
flower -A gem5art.tasks.celery --port=5555
```
This will start a webserver on port 5555.

## Removing all tasks

```sh
celery -A gem5art.tasks.celery purge
```

## Viewing state of all jobs in celery

```sh
celery -A gem5art.tasks.celery events
```

```eval_rst
Tasks API Documentation
=======================

Task
----

.. automodule:: gem5art.tasks.tasks
    :members:
    :undoc-members:

.. automodule:: gem5art.tasks.celery
    :members:
    :undoc-members:
```