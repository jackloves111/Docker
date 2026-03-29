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

DEFAULT_TIMEZONE = 'Asia/Shanghai'

def _get_setting(key, default=None):
    from app.db.database import db
    with db.get_cursor() as cursor:
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        return row[0] if row else default

def _set_setting(key, value):
    from app.db.database import db
    with db.get_cursor() as cursor:
        cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, str(value)))

def init_scheduler(app):
    global _scheduler, _app
    _app = app

    from app.models.target import Target

    _scheduler = BackgroundScheduler()

    targets = Target.get_enabled()
    logger.info(f"[调度器] 初始化，找到 {len(targets)} 个启用的目标")
    for target in targets:
        add_job(target)

    scheduler_enabled = _get_setting('scheduler_enabled', 'true') == 'true'
    if scheduler_enabled:
        logger.info("[调度器] 数据库配置为启用调度器")
        start_scheduler()
    else:
        logger.info("[调度器] 数据库配置为禁用调度器")

    logger.info("[调度器] 调度器初始化完成")

def add_job(target):
    global _scheduler
    if not _scheduler:
        logger.warning("[调度器] 调度器未初始化，无法添加任务")
        return

    schedule_type = target.get('schedule_type', 'interval')
    if schedule_type == 'manual':
        logger.info(f"[调度器] 目标 {target['name']} 为手动调度类型，跳过任务添加")
        return

    job_id = f"target_{target['id']}"

    if _scheduler.get_job(job_id):
        logger.info(f"[调度器] 任务已存在，先移除: {job_id}")
        _scheduler.remove_job(job_id)

    schedule_type = target.get('schedule_type', 'interval')
    schedule_value = target.get('schedule_value', '360')

    logger.info(f"[调度器] 添加任务 - ID: {job_id}, 目标: {target['name']}, 类型: {schedule_type}, 值: {schedule_value}")

    if schedule_type == 'cron':
        try:
            trigger = CronTrigger.from_crontab(schedule_value, timezone=DEFAULT_TIMEZONE)
            logger.debug(f"[调度器] Cron 表达式解析成功: {schedule_value}, 时区: {DEFAULT_TIMEZONE}")
        except:
            logger.warning(f"[调度器] Cron 表达式解析失败: {schedule_value}，使用间隔 {schedule_value} 分钟")
            trigger = IntervalTrigger(minutes=int(schedule_value))
    else:
        try:
            minutes = int(schedule_value)
            trigger = IntervalTrigger(minutes=minutes)
            logger.debug(f"[调度器] 间隔时间: {minutes} 分钟")
        except:
            logger.warning(f"[调度器] 间隔时间解析失败: {schedule_value}，使用默认值 360 分钟")
            trigger = IntervalTrigger(minutes=360)

    from app.core.engine import trigger_upgrade
    _scheduler.add_job(
        func=trigger_upgrade,
        trigger=trigger,
        id=job_id,
        args=[target['id']],
        replace_existing=True
    )

    logger.info(f"[调度器] 任务添加成功: {target['name']}")

def remove_job(target_id):
    global _scheduler
    if not _scheduler:
        logger.warning("[调度器] 调度器未初始化，无法移除任务")
        return

    job_id = f"target_{target_id}"
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)
        logger.info(f"[调度器] 已移除任务: {job_id}")
    else:
        logger.debug(f"[调度器] 任务不存在，无需移除: {job_id}")

def start_scheduler():
    global _scheduler, _scheduler_running
    if _scheduler and not _scheduler_running:
        _scheduler.start()
        _scheduler_running = True
        _set_setting('scheduler_enabled', 'true')
        logger.info("[调度器] 调度器已启动")

def stop_scheduler():
    global _scheduler, _scheduler_running
    if _scheduler and _scheduler_running:
        _scheduler.shutdown(wait=False)
        _scheduler_running = False
        _set_setting('scheduler_enabled', 'false')
        logger.info("[调度器] 调度器已停止")

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

    logger.debug(f"[调度器] 状态查询: 运行中={_scheduler_running}, 任务数={len(jobs)}")
    return {
        'running': _scheduler_running,
        'jobs': jobs
    }

def sync_jobs():
    global _app
    if not _app:
        logger.warning("[调度器] 应用未初始化，无法同步任务")
        return

    from app.models.target import Target

    targets = Target.get_enabled()
    logger.info(f"[调度器] 同步任务，共 {len(targets)} 个启用的目标")
    for target in targets:
        add_job(target)

    logger.info(f"[调度器] 任务同步完成")
