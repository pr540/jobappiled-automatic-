from apscheduler.schedulers.background import BackgroundScheduler
import time

def test_job():
    print("Job is running!")

scheduler = BackgroundScheduler()
scheduler.add_job(test_job, 'interval', seconds=1)
scheduler.start()
print("Scheduler started...")
time.sleep(3)
scheduler.shutdown()
print("Done.")
