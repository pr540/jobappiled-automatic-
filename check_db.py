import sqlite3
db_path = "instance/jobbot.db"
con = sqlite3.connect(db_path)
rows = con.execute("SELECT platform, title, status, error_message FROM jobs ORDER BY status, platform LIMIT 30").fetchall()
print("All jobs with errors:")
for r in rows:
    msg = (r[3] or "")[:120]
    print(f"  [{r[0]}] {r[2]:8s} {r[1][:40]:40s} | {msg}")
con.close()
