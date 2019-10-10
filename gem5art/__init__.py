"""This is the gem5 structured approach package"""

import importlib.util

from . import artifact
from . import gem5run

# Only import tasks if celery is installed
if importlib.util.find_spec('celery') is not None:
    from . import tasks
