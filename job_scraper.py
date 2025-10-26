from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sqlite3
from datetime import datetime, timedelta
import time
import logging
import os

# Setup logging
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, f'scraper_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def calculate_posted_date(posted_text):
    if "days ago" in posted_text:
        days = int(posted_text.split()[1])
        return datetime.now() - timedelta(days=days)
    elif "day ago" in posted_text:
        return datetime.now() - timedelta(days=1)
    return datetime.now()

def extract_facility_name(title):
    import re
    
    # Pattern 1: After dash (most common)
    if ' - ' in title:
        after_dash = title.split(' - ', 1)[1]
        # Remove codes like (110/125) or CI/WC but keep DC (Detention Center)
        after_dash = re.sub(r'\s*-\s*\([^)]+\)$', '', after_dash)
        after_dash = re.sub(r'\s*-\s*(?!DC)[A-Z]{2}(/[A-Z]{2})?\s*-\s*\([^)]+\)$', '', after_dash)
        # Convert DC acronym to full name
        after_dash = re.sub(r'\bDC\b', 'Detention Center', after_dash)
        return after_dash.strip()
    
    # Pattern 2: Direct facility names with keywords
    patterns = [
        r'([A-Za-z\s]+County\s+(?:Jail|Sheriff|Detention|Correctional)[^,]*)',
        r'([A-Za-z\s]+(?:Jail|Prison|Correctional|Detention)(?:\s+(?:Facility|Center|Institution))?)',
        r'([A-Za-z\s]+(?:Penitentiary|Institution))',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            result = match.group(1).strip()
            # Convert DC acronym to full name
            result = re.sub(r'\bDC\b', 'Detention Center', result)
            return result
    
    return None

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
    
    logger.info("Starting job scraper")
    
    # Load master facility list
    master_facilities = load_master_facilities()
    logger.info(f"Loaded {len(master_facilities)} master facilities")
    
    # Setup Chrome options for GitHub Actions compatibility
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=options)
    driver.get("https://careers.aramark.com/search/?distance=25&category=&type=&sub_category=&industry=correctional+facilities#page-top")
    
    # First, click Load More until we have 100 jobs
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        try:
            current_count = len(driver.find_elements(By.CSS_SELECTOR, "h2.Search--results__card__title"))
            
            if current_count >= 100:
                logger.info(f"Reached 100+ jobs ({current_count}), stopping Load More")
                break
                
            load_more = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "loadMore"))
            )
            logger.info(f"Found {current_count} jobs. Clicking Load More...")
            driver.execute_script("arguments[0].click();", load_more)
            time.sleep(5)
            
            new_count = len(driver.find_elements(By.CSS_SELECTOR, "h2.Search--results__card__title"))
            logger.info(f"After Load More: {new_count} jobs")
            
            if new_count <= current_count:
                logger.info("No more jobs to load")
                break
        except:
            logger.info("No Load More button found")
            break
    
    # Wait for page to fully load
    time.sleep(3)
    
    # Now scrape all jobs at once
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "Search--results__card__title"))
    )
    
    job_cards = driver.find_elements(By.CSS_SELECTOR, "h2.Search--results__card__title")
    logger.info(f"Total jobs found: {len(job_cards)}")
    
    # Process only first 100 jobs
    for i, card in enumerate(job_cards[:100]):
        if i >= 100:
            break
        try:
            link = card.find_element(By.TAG_NAME, "a")
            title = link.text
            url = link.get_attribute("href")
            job_id = url.split("req_id=")[1] if "req_id=" in url else ""
            
            parent = card.find_element(By.XPATH, "../..")
            info_div = parent.find_element(By.CSS_SELECTOR, "div.flex")
            posted_text = info_div.find_element(By.CSS_SELECTOR, "p.text-xs").text
            
            # Get location from the specific class
            try:
                location_element = parent.find_element(By.CSS_SELECTOR, "p.Search--results__card__location")
                location = location_element.text.strip()
            except:
                location = ""
            
            posted_date = calculate_posted_date(posted_text)
            
            facility_name_raw = extract_facility_name(title)
            
            # Match against master list
            facility_name_standard = None
            verified = False
            if facility_name_raw:
                match, score = find_best_match(facility_name_raw, master_facilities)
                if match:
                    facility_name_standard = match
                    verified = True
            
            cursor.execute("SELECT job_id FROM jobs WHERE job_id = ?", (job_id,))
            if not cursor.fetchone():
                cursor.execute('''
                INSERT INTO jobs (job_id, title, url, location, posted_date, facility_name_raw, facility_name_standard, verified_facility)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (job_id, title, url, location, posted_date.strftime('%Y-%m-%d'), facility_name_raw, facility_name_standard, verified))
                
                if verified:
                    logger.info(f"Scraped: {title} - {job_id} [✓ {facility_name_standard}]")
                elif facility_name_raw:
                    logger.info(f"Scraped: {title} - {job_id} [? {facility_name_raw}]")
                else:
                    logger.info(f"Scraped: {title} - {job_id} [No facility found]")
            else:
                logger.info(f"Skipping duplicate: {job_id}")
            
        except Exception as e:
            logger.error(f"Error scraping job: {e}")
    
    conn.commit()
    logger.info("Finished scraping job listings")
    
    # Scrape descriptions
    cursor.execute("SELECT job_id, url FROM jobs WHERE description IS NULL OR description = ''")
    jobs = cursor.fetchall()
    
    for job_id, url in jobs:
        try:
            logger.info(f"Getting description for {job_id}")
            driver.get(url)
            
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//h2[text()='Job Description']"))
            )
            
            desc_header = driver.find_element(By.XPATH, "//h2[text()='Job Description']")
            desc_container = desc_header.find_element(By.XPATH, "../following-sibling::div")
            description = desc_container.text.strip()
            
            # Check if facility name is missing and try to extract from description
            cursor.execute("SELECT facility_name_raw FROM jobs WHERE job_id = ?", (job_id,))
            current_facility = cursor.fetchone()[0]
            
            if not current_facility:
                # Extract facility name from description with better parsing
                import re
                facility_match = re.search(r'at ([A-Za-z\s]+(?:County|State)\s+(?:Jail|Prison|Correctional|Institution))', description)
                if not facility_match:
                    facility_match = re.search(r'at ([A-Za-z\s]+(?:Correctional|Institution))', description)
                
                facility_from_desc = facility_match.group(1).strip() if facility_match else None
                
                # Match description facility against master list
                standard_from_desc = None
                verified_from_desc = False
                if facility_from_desc:
                    match, score = find_best_match(facility_from_desc, master_facilities)
                    if match:
                        standard_from_desc = match
                        verified_from_desc = True
                
                cursor.execute("UPDATE jobs SET description = ?, facility_name_raw = ?, facility_name_standard = ?, verified_facility = ? WHERE job_id = ?", 
                             (description, facility_from_desc, standard_from_desc, verified_from_desc, job_id))
                
                if verified_from_desc:
                    logger.info(f"Found verified facility in description: {standard_from_desc}")
                elif facility_from_desc:
                    logger.info(f"Found unverified facility in description: {facility_from_desc}")
            else:
                cursor.execute("UPDATE jobs SET description = ? WHERE job_id = ?", (description, job_id))
            
            conn.commit()
            
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error getting description for {job_id}: {e}")
    
    # Display results
    cursor.execute("SELECT job_id, title, location, posted_date, description, facility_name_raw, facility_name_standard, verified_facility FROM jobs")
    jobs = cursor.fetchall()
    
    for job in jobs:
        job_id, title, location, posted_date, description, raw_name, standard_name, verified = job
        print(f"\nJob ID: {job_id}")
        print(f"Title: {title}")
        if verified:
            print(f"Facility: ✓ {standard_name}")
        elif raw_name:
            print(f"Facility: ? {raw_name} (unverified)")
        else:
            print(f"Facility: Not identified")
        print(f"Location: {location}")
        print(f"Posted: {posted_date}")
        print(f"Description: {description[:200]}..." if description else "No description")
        print("-" * 80)
    
    # Show verified facilities
    cursor.execute("SELECT DISTINCT facility_name_standard FROM jobs WHERE verified_facility = 1 ORDER BY facility_name_standard")
    verified_facilities = cursor.fetchall()
    
    # Show unverified facilities
    cursor.execute("SELECT DISTINCT facility_name_raw FROM jobs WHERE verified_facility = 0 AND facility_name_raw IS NOT NULL ORDER BY facility_name_raw")
    unverified_facilities = cursor.fetchall()
    
    logger.info("\n=== VERIFIED CORRECTIONAL FACILITIES SERVED BY ARAMARK ===")
    for facility in verified_facilities:
        logger.info(f"✓ {facility[0]}")
    
    logger.info("\n=== UNVERIFIED FACILITIES ===")
    for facility in unverified_facilities:
        logger.info(f"? {facility[0]}")
    
    logger.info(f"\nVerified facilities: {len(verified_facilities)}")
    logger.info(f"Unverified facilities: {len(unverified_facilities)}")
    logger.info(f"Total jobs scraped: {len(jobs)}")
    logger.info(f"Log saved to: {log_file}")
    
    driver.quit()
    conn.close()

if __name__ == "__main__":
    scrape_all_jobs()