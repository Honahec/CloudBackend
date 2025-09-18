# 导入Celery应用，确保Django启动时Celery也会启动
from .celery import app as celery_app

__all__ = ('celery_app',)