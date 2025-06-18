from celery import Celery
from voice_studio_stack.message_queue.rabbitmq.rabbit_config import get_rabbitmq_url
from voice_studio_stack.database.redis.redis_config import get_redis_url
# LOADING VARIABLES
from dotenv import load_dotenv
load_dotenv()   

def make_celery(app_name="cogni_voice_task_app") -> Celery:
    celery = Celery(
        app_name,
        broker=get_rabbitmq_url(),
        backend=get_redis_url(),
        include=["voice_studio_stack.task_queue.celery_q.tasks"]  # Specify the module where your tasks are defined
    )

    celery.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
    )

    return celery