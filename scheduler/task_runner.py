"""APScheduler-based daily task runner."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from core.config import Config
from core.logger import get_logger

log = get_logger("scheduler")


def _parse_time(t: str) -> tuple[int, int]:
    h, m = t.split(":")
    return int(h), int(m)


def start_scheduler(app):
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

    morning_h, morning_m = _parse_time(Config.MORNING_SCAN_TIME)
    report_h, report_m = _parse_time(Config.REPORT_TIME)

    def morning_scan():
        log.info("Morning scan started")
        with app.app_context():
            from agents.job_search_agent import run_job_search
            run_job_search(app=app)

    def auto_apply():
        log.info("Auto-apply started")
        with app.app_context():
            from agents.apply_agent import run_auto_apply
            run_auto_apply(app=app)

    def recruiter_outreach():
        log.info("Recruiter outreach started")
        with app.app_context():
            from agents.recruiter_agent import run_recruiter_outreach
            run_recruiter_outreach(app=app)

    def daily_report():
        log.info("Daily report generation")
        with app.app_context():
            from api.reports import generate_daily_report
            generate_daily_report()

    scheduler.add_job(morning_scan, CronTrigger(hour=morning_h, minute=morning_m), id="morning_scan")
    scheduler.add_job(auto_apply, CronTrigger(hour=morning_h, minute=morning_m + 30), id="auto_apply")
    scheduler.add_job(recruiter_outreach, CronTrigger(hour=morning_h + 1, minute=0), id="recruiter_outreach")
    scheduler.add_job(daily_report, CronTrigger(hour=report_h, minute=report_m), id="daily_report")

    scheduler.start()
    log.info("Scheduler started", extra={
        "morning_scan": Config.MORNING_SCAN_TIME,
        "report": Config.REPORT_TIME,
    })
    return scheduler
