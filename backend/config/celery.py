import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("mailsense")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "sync-gmail-every-5-min": {
        "task": "tasks.sync.sync_gmail_inbox_all_users",
        "schedule": crontab(minute="*/5"),
    },
    "classify-pending-batch": {
        "task": "tasks.classify.classify_pending_batch",
        "schedule": crontab(minute="*/2"),
    },
    "daily-digest": {
        "task": "tasks.digest.generate_daily_digest_all",
        "schedule": crontab(hour=8, minute=0),
    },
}
