import sqlite3
import re
import html

def clean_html(text):
    if not text:
        return text
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

conn = sqlite3.connect('jobs.db')
cursor = conn.cursor()

cursor.execute("SELECT job_id, description FROM jobs WHERE description IS NOT NULL")
jobs = cursor.fetchall()

cleaned = 0
for job_id, description in jobs:
    clean_desc = clean_html(description)
    cursor.execute("UPDATE jobs SET description = ? WHERE job_id = ?", (clean_desc, job_id))
    cleaned += 1

conn.commit()
print(f"Cleaned {cleaned} job descriptions")
conn.close()
