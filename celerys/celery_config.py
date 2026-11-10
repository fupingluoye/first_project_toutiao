from celery import Celery
from config import Config
broker = Config.BROKER
backend = Config.BACKEND

cel = Celery("get_data",
             broker  = broker,
             backend = backend,
             include = ["celerys.celery_task1"]
             )