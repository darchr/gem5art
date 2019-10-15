from .celery import gem5app

@gem5app.task(bind=True, serializer='pickle')
def run_gem5_instance(self, gem5_run):
    """
    Runs a gem5 instance with the script and any parameters to the script.
    Note: this is "bound" which means self is the task that is running this.
    """

    gem5_run.run(self)
