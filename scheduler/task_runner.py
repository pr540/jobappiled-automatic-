"""APScheduler-based daily task runner."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from core.config import Config
from core.logger import get_logger

log = get_logger("scheduler")


def _parse_time(t: str) -> tuple[int, int]:
    h, m = t.split(":")
    return int(h), int(m)


def _add_minutes(h: int, m: int, delta: int) -> tuple[int, int]:
    """Add delta minutes to (h, m) without overflow."""
    total = h * 60 + m + delta
    return (total // 60) % 24, total % 60


def start_scheduler(app):
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

    morning_h, morning_m = _parse_time(Config.MORNING_SCAN_TIME)
    report_h, report_m = _parse_time(Config.REPORT_TIME)

    # Derived times — no arithmetic overflow
    apply_h, apply_m = _add_minutes(morning_h, morning_m, 30)
    outreach_h, outreach_m = _add_minutes(morning_h, morning_m, 60)

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

    scheduler.add_job(morning_scan, CronTrigger(hour=morning_h, minute=morning_m), id="morning_scan")
    scheduler.add_job(auto_apply, CronTrigger(hour=apply_h, minute=apply_m), id="auto_apply")
    scheduler.add_job(recruiter_outreach, CronTrigger(hour=outreach_h, minute=outreach_m), id="recruiter_outreach")
    scheduler.add_job(daily_report, CronTrigger(hour=report_h, minute=report_m), id="daily_report")

    scheduler.start()
    log.info("Scheduler started", extra={
        "morning_scan": f"{morning_h:02d}:{morning_m:02d}",
        "auto_apply": f"{apply_h:02d}:{apply_m:02d}",
        "recruiter_outreach": f"{outreach_h:02d}:{outreach_m:02d}",
        "daily_report": f"{report_h:02d}:{report_m:02d}",
    })
    return scheduler
