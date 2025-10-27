import sqlite3
import csv

conn = sqlite3.connect('jobs.db')
cursor = conn.cursor()

cursor.execute("SELECT * FROM jobs")
jobs = cursor.fetchall()

# Get column names
column_names = [description[0] for description in cursor.description]

# Write to CSV
with open('jobs.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(column_names)
    writer.writerows(jobs)

print(f"Exported {len(jobs)} jobs to jobs.csv")

conn.close()
