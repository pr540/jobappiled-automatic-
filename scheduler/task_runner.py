"""APScheduler-based daily task runner."""
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import SchedulerAlreadyRunningError
from apscheduler.triggers.cron import CronTrigger
from core.config import Config
from core.logger import get_logger

log = get_logger("scheduler")

_DEFAULT_MORNING = (8, 0)
_DEFAULT_REPORT  = (20, 0)

# Shared reference so atexit can stop it
_scheduler: BackgroundScheduler | None = None


def _parse_time(t: str, default: tuple[int, int]) -> tuple[int, int]:
    """Parse 'HH:MM' and validate bounds. Returns default on any error."""
    try:
        parts = t.strip().split(":")
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError(f"out of range: {h}:{m}")
        return h, m
    except Exception:
        log.warning(
            f"Invalid time format '{t}' — using {default[0]:02d}:{default[1]:02d}"
        )
        return default


def _add_minutes(h: int, m: int, delta: int) -> tuple[int, int]:
    """Add delta minutes to (h, m) without overflow."""
    total = h * 60 + m + delta
    return (total // 60) % 24, total % 60


def _make_job_defaults() -> dict:
    """Common APScheduler job kwargs: no duplicate runs, 1-hour miss window."""
    return {
        "replace_existing": True,
        "max_instances": 1,
        "misfire_grace_time": 3600,  # run a missed job if within 1 hour; skip otherwise
        "coalesce": True,            # collapse multiple missed firings into one
    }


def start_scheduler(app) -> BackgroundScheduler | None:
    global _scheduler

    if app is None:
        log.error("start_scheduler: app is None — scheduler not started")
        return None

    if _scheduler and _scheduler.running:
        log.warning("Scheduler already running — skipping start")
        return _scheduler

    morning_h, morning_m = _parse_time(Config.MORNING_SCAN_TIME, _DEFAULT_MORNING)
    report_h,  report_m  = _parse_time(Config.REPORT_TIME, _DEFAULT_REPORT)

    apply_h,    apply_m    = _add_minutes(morning_h, morning_m, 30)
    outreach_h, outreach_m = _add_minutes(morning_h, morning_m, 60)

    _scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

    def morning_scan():
        log.info("Scheduler: morning scan started")
        with app.app_context():
            try:
                from agents.job_search_agent import run_job_search
                run_job_search()
            except Exception as e:
                log.error(f"Scheduler: morning scan failed: {e}")

    def auto_apply():
        log.info("Scheduler: auto-apply started")
        with app.app_context():
            try:
                from agents.apply_agent import run_auto_apply
                run_auto_apply()
            except Exception as e:
                log.error(f"Scheduler: auto-apply failed: {e}")

    def recruiter_outreach():
        log.info("Scheduler: recruiter outreach started")
        with app.app_context():
            try:
                from agents.recruiter_agent import run_recruiter_outreach
                run_recruiter_outreach()
            except Exception as e:
                log.error(f"Scheduler: outreach failed: {e}")

    def daily_report():
        log.info("Scheduler: daily report generation")
        with app.app_context():
            try:
                from api.reports import generate_daily_report
                generate_daily_report()
            except Exception as e:
                log.error(f"Scheduler: report failed: {e}")

    defaults = _make_job_defaults()
    _scheduler.add_job(morning_scan,      CronTrigger(hour=morning_h,  minute=morning_m),  id="morning_scan",      **defaults)
    _scheduler.add_job(auto_apply,        CronTrigger(hour=apply_h,    minute=apply_m),    id="auto_apply",        **defaults)
    _scheduler.add_job(recruiter_outreach,CronTrigger(hour=outreach_h, minute=outreach_m), id="recruiter_outreach",**defaults)
    _scheduler.add_job(daily_report,      CronTrigger(hour=report_h,   minute=report_m),   id="daily_report",      **defaults)

    try:
        _scheduler.start()
        atexit.register(_stop_scheduler)
        log.info("Scheduler started", extra={
            "morning_scan":      f"{morning_h:02d}:{morning_m:02d}",
            "auto_apply":        f"{apply_h:02d}:{apply_m:02d}",
            "recruiter_outreach":f"{outreach_h:02d}:{outreach_m:02d}",
            "daily_report":      f"{report_h:02d}:{report_m:02d}",
        })
    except SchedulerAlreadyRunningError:
        log.warning("Scheduler already running — skipped duplicate start")

    return _scheduler


def _stop_scheduler():
    """Registered with atexit — shuts down the scheduler thread cleanly on exit."""
    global _scheduler
    if _scheduler and _scheduler.running:
        try:
            _scheduler.shutdown(wait=False)
            log.info("Scheduler stopped")
        except Exception as e:
            log.warning(f"Scheduler shutdown error: {e}")
