import sqlite3

conn = sqlite3.connect('jobs.db')
cursor = conn.cursor()

# Get total count
cursor.execute("SELECT COUNT(*) FROM jobs")
total = cursor.fetchone()[0]

# Get jobs with descriptions
cursor.execute("SELECT COUNT(*) FROM jobs WHERE description IS NOT NULL AND description != ''")
with_desc = cursor.fetchone()[0]

# Get verified facilities
cursor.execute("SELECT COUNT(DISTINCT facility_name_standard) FROM jobs WHERE verified_facility = 1")
verified_facilities = cursor.fetchone()[0]

# Get unverified facilities
cursor.execute("SELECT COUNT(DISTINCT facility_name_raw) FROM jobs WHERE verified_facility = 0 AND facility_name_raw IS NOT NULL")
unverified_facilities = cursor.fetchone()[0]

# Get all jobs with all fields
cursor.execute("SELECT * FROM jobs")
all_jobs = cursor.fetchall()

print(f"=== DATABASE SUMMARY ===")
print(f"Total jobs: {total}")
print(f"Jobs with descriptions: {with_desc}")
print(f"Verified facilities: {verified_facilities}")
print(f"Unverified facilities: {unverified_facilities}")

print(f"\n=== ALL JOBS (ALL FIELDS) ===")
for job in all_jobs:
    job_id, title, url, location, posted_date, description, raw, standard, verified = job
    print(f"\n{'='*80}")
    print(f"Job ID: {job_id}")
    print(f"Title: {title}")
    print(f"URL: {url}")
    print(f"Location: {location}")
    print(f"Posted Date: {posted_date}")
    print(f"Facility (Raw): {raw}")
    print(f"Facility (Standard): {standard}")
    print(f"Verified: {'✓' if verified else '✗'}")
    print(f"Description: {description[:200] if description else 'No description'}...")
    print(f"{'='*80}")



conn.close()
