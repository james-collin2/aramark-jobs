import requests
import sqlite3
from datetime import datetime
import logging
import os
import time
import re
import html

# Setup logging
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, f'api_scraper_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_master_facilities():
    facilities = []
    with open('clean_prisons.txt', 'r') as f:
        for line in f:
            line = line.strip()
            if line and ':' not in line and len(line) > 5:
                facilities.append(line)
    return facilities

def find_best_match(facility_name, master_list):
    from difflib import SequenceMatcher
    best_match = None
    best_score = 0
    
    for master_facility in master_list:
        score = SequenceMatcher(None, facility_name.lower(), master_facility.lower()).ratio()
        if score > best_score and score > 0.7:
            best_score = score
            best_match = master_facility
    
    return best_match, best_score

def clean_html(text):
    if not text:
        return text
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_facility_name(title):
    
    if ' - ' in title:
        after_dash = title.split(' - ', 1)[1]
        after_dash = re.sub(r'\s*-\s*\([^)]+\)$', '', after_dash)
        after_dash = re.sub(r'\s*-\s*(?!DC)[A-Z]{2}(/[A-Z]{2})?\s*-\s*\([^)]+\)$', '', after_dash)
        after_dash = re.sub(r'\bDC\b', 'Detention Center', after_dash)
        return after_dash.strip()
    
    patterns = [
        r'([A-Za-z\s]+County\s+(?:Jail|Sheriff|Detention|Correctional)[^,]*)',
        r'([A-Za-z\s]+(?:Jail|Prison|Correctional|Detention)(?:\s+(?:Facility|Center|Institution))?)',
        r'([A-Za-z\s]+(?:Penitentiary|Institution))',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            result = match.group(1).strip()
            result = re.sub(r'\bDC\b', 'Detention Center', result)
            return result
    
    return None

def setup_database():
    conn = sqlite3.connect('jobs.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS jobs (
        job_id TEXT PRIMARY KEY,
        title TEXT,
        url TEXT,
        location TEXT,
        posted_date DATE,
        description TEXT,
        facility_name_raw TEXT,
        facility_name_standard TEXT,
        verified_facility BOOLEAN
    )
    ''')
    conn.commit()
    return conn

def scrape_all_jobs():
    conn = setup_database()
    cursor = conn.cursor()
    
    logger.info("Starting API job scraper")
    
    master_facilities = load_master_facilities()
    logger.info(f"Loaded {len(master_facilities)} master facilities")
    
    # Get all jobs
    url = "https://careers.aramark.com/wp-json/aramark/jobs?&path=&zips=&industries=correctional%20facilities&categories=&jobfunction=&sub_categories=&types=&keyword=&limit=500"
    
    logger.info("Fetching jobs from API...")
    response = requests.get(url)
    
    if response.status_code != 200:
        logger.error(f"API request failed with status {response.status_code}")
        return
    
    jobs = response.json()
    logger.info(f"Total jobs found: {len(jobs)}")
    
    new_jobs = 0
    updated_jobs = 0
    
    new_job_ids = []
    
    for job in jobs:
        req_id = job.get('req_id')
        title = job.get('title')
        url = job.get('url')
        city = job.get('city', '')
        state = job.get('state', '')
        location = f"{city}, {state}".strip(', ')
        posted_date = job.get('pub_date')
        
        facility_name_raw = extract_facility_name(title)
        facility_name_standard = None
        verified = False
        
        if facility_name_raw:
            match, score = find_best_match(facility_name_raw, master_facilities)
            if match:
                facility_name_standard = match
                verified = True
        
        cursor.execute("SELECT job_id FROM jobs WHERE job_id = ?", (req_id,))
        if not cursor.fetchone():
            cursor.execute('''
            INSERT INTO jobs (job_id, title, url, location, posted_date, facility_name_raw, facility_name_standard, verified_facility)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (req_id, title, url, location, posted_date, facility_name_raw, facility_name_standard, verified))
            new_jobs += 1
            new_job_ids.append(req_id)
            
            if verified:
                logger.info(f"New job: {title} - {req_id} [VERIFIED: {facility_name_standard}]")
            elif facility_name_raw:
                logger.info(f"New job: {title} - {req_id} [UNVERIFIED: {facility_name_raw}]")
            else:
                logger.info(f"New job: {title} - {req_id} [No facility found]")
    
    conn.commit()
    logger.info(f"Added {new_jobs} new jobs")
    
    # Get descriptions only for new jobs
    if new_job_ids:
        logger.info(f"Fetching descriptions for {len(new_job_ids)} new jobs...")
    else:
        logger.info("No new jobs, skipping description fetch")
    
    for job_id in new_job_ids:
        try:
            desc_url = f"https://careers.aramark.com/wp-json/aramark/jobs?limit=1&req_id={job_id}"
            response = requests.get(desc_url)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    description = data[0].get('description', '')
                    description = clean_html(description)
                    cursor.execute("UPDATE jobs SET description = ? WHERE job_id = ?", (description, job_id))
                    updated_jobs += 1
                    logger.info(f"Updated description for {job_id}")
            
            time.sleep(0.5)  # Be nice to the API
            
        except Exception as e:
            logger.error(f"Error getting description for {job_id}: {e}")
    
    conn.commit()
    
    # Summary
    cursor.execute("SELECT COUNT(*) FROM jobs")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT facility_name_standard) FROM jobs WHERE verified_facility = 1")
    verified_facilities = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT facility_name_raw) FROM jobs WHERE verified_facility = 0 AND facility_name_raw IS NOT NULL")
    unverified_facilities = cursor.fetchone()[0]
    
    logger.info(f"\n=== SUMMARY ===")
    logger.info(f"Total jobs in database: {total}")
    logger.info(f"New jobs added: {new_jobs}")
    logger.info(f"Descriptions updated: {updated_jobs}")
    logger.info(f"Verified facilities: {verified_facilities}")
    logger.info(f"Unverified facilities: {unverified_facilities}")
    logger.info(f"Log saved to: {log_file}")
    
    conn.close()

if __name__ == "__main__":
    scrape_all_jobs()
