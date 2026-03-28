import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import time

logger = logging.getLogger(__name__)

_scheduler = None
_app = None
_scheduler_running = False

def init_scheduler(app):
    global _scheduler, _app
    _app = app

    from app.models.target import Target
    from app.core.engine import run_upgrade_task

    _scheduler = BackgroundScheduler()

    targets = Target.get_enabled()
    for target in targets:
        add_job(target)

    if app.config['APP_CONFIG']['scheduler'].get('default_enabled', True):
        start_scheduler()

    logger.info("Scheduler initialized")

def add_job(target):
    global _scheduler
    if not _scheduler:
        return

    job_id = f"target_{target['id']}"

    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)

    schedule_type = target.get('schedule_type', 'interval')
    schedule_value = target.get('schedule_value', '360')

    if schedule_type == 'cron':
        try:
            trigger = CronTrigger.from_crontab(schedule_value)
        except:
            trigger = IntervalTrigger(minutes=int(schedule_value))
    else:
        try:
            minutes = int(schedule_value)
            trigger = IntervalTrigger(minutes=minutes)
        except:
            trigger = IntervalTrigger(minutes=360)

    _scheduler.add_job(
        func=run_upgrade_task,
        trigger=trigger,
        id=job_id,
        args=[target['id']],
        replace_existing=True
    )

    logger.info(f"Added scheduled job for {target['name']}: {schedule_type}={schedule_value}")

def remove_job(target_id):
    global _scheduler
    if not _scheduler:
        return

    job_id = f"target_{target_id}"
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)
        logger.info(f"Removed scheduled job: {job_id}")

def start_scheduler():
    global _scheduler, _scheduler_running
    if _scheduler and not _scheduler_running:
        _scheduler.start()
        _scheduler_running = True
        logger.info("Scheduler started")

def stop_scheduler():
    global _scheduler, _scheduler_running
    if _scheduler and _scheduler_running:
        _scheduler.shutdown(wait=False)
        _scheduler_running = False
        logger.info("Scheduler stopped")

def get_scheduler_status():
    global _scheduler, _scheduler_running
    if not _scheduler:
        return {'running': False, 'jobs': []}

    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None
        })

    return {
        'running': _scheduler_running,
        'jobs': jobs
    }

def sync_jobs():
    global _app
    if not _app:
        return

    from app.models.target import Target

    targets = Target.get_enabled()
    for target in targets:
        add_job(target)

    logger.info(f"Synced {len(targets)} scheduled jobs")
