"""Module celery_utils.py."""
from celery import Celery, Task
from flask import Flask


def celery_init_app(app: Flask) -> Celery:
    """celery_init_app function."""

    class FlaskTask(Task):
        """FlaskTask class."""

        def __call__(self, *args, **kwargs):
            """__call__ function."""

            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)

    celery_app.config_from_object(
        {
            "broker_url": "redis://localhost:6379/0",
            "result_backend": "redis://localhost:6379/0",
            "task_track_started": True,
            "worker_cancel_long_running_tasks_on_connection_loss": True,
        }
    )

    celery_app.set_default()
    app.extensions["celery"] = celery_app

    return celery_app
