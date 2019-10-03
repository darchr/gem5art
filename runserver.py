
from celery import Celery

# Create a celery server. If you run celery with this file, it will start a
# server that will accept tasks specified by the "run" below.
gem5 = Celery('gem5', backend='rpc', broker='amqp://localhost')
gem5.conf.update(accept_content=['pickle', 'json'])

@gem5.task(bind=True, serializer='pickle')
def spawn_task(self, gem5_run):
    """
    Runs a gem5 instance with the script and any parameters to the script.
    Note: this is "bound" which means self is the task that is running this.
    """

    gem5_run.run(self)
