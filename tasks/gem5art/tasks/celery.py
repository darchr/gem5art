
from celery import Celery # type: ignore

# Create a celery server. If you run celery with this file, it will start a
# server that will accept tasks specified by the "run" below.
gem5app = Celery('gem5', backend='rpc', broker='amqp://localhost',
              include=['gem5art.tasks.tasks'])
gem5app.conf.update(accept_content=['pickle', 'json'])

if __name__ == "__main__":
    gem5app.start()
