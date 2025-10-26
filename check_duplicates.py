import sqlite3

conn = sqlite3.connect('jobs.db')
cursor = conn.cursor()

# Check for duplicate job_ids
cursor.execute("SELECT job_id, COUNT(*) FROM jobs GROUP BY job_id HAVING COUNT(*) > 1")
duplicates = cursor.fetchall()

if duplicates:
    print("Duplicate job_ids found:")
    for job_id, count in duplicates:
        print(f"Job ID {job_id}: {count} times")
else:
    print("No duplicate job_ids found")

# Show total count
cursor.execute("SELECT COUNT(*) FROM jobs")
total = cursor.fetchone()[0]
print(f"\nTotal jobs in database: {total}")

# Show unique count
cursor.execute("SELECT COUNT(DISTINCT job_id) FROM jobs")
unique = cursor.fetchone()[0]
print(f"Unique job_ids: {unique}")

conn.close()