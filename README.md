# Aramark Correctional Facilities Job Scraper

Automated job scraper that monitors and tracks job postings at correctional facilities serviced by Aramark. The scraper runs daily via GitHub Actions and stores job data in a SQLite database.

## Features

- 🔄 Automated daily scraping via GitHub Actions
- 🏢 Facility name extraction and verification using fuzzy matching
- 📊 SQLite database storage with full job details
- 📝 Detailed logging for each scraping run
- 📤 CSV export functionality
- ✅ Distinguishes between verified and unverified facilities

## Project Structure

```
careers_aramark/
├── api_scraper.py           # Main scraper script
├── check_db.py              # View database contents
├── export_to_csv.py         # Export jobs to CSV
├── clean_prisons.txt        # Master list of facilities
├── jobs.db                  # SQLite database
├── jobs.csv                 # Exported CSV file
├── requirements.txt         # Python dependencies
├── logs/                    # Scraping logs
└── .github/
    └── workflows/
        └── deploy.yml       # GitHub Actions workflow
```

## Database Schema

```sql
CREATE TABLE jobs (
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
```

## Setup

### Prerequisites

- Python 3.11+
- Git

### Local Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd careers_aramark
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Ensure `clean_prisons.txt` exists with your master facility list

## Usage

### Run Scraper Locally

```bash
python api_scraper.py
```

This will:
- Fetch all jobs from Aramark API filtered by correctional facilities
- Extract and verify facility names
- Store new jobs in `jobs.db`
- Fetch descriptions for new jobs only
- Generate a timestamped log in `logs/` directory

### View Database Contents

```bash
python check_db.py
```

Shows:
- Total jobs count
- Jobs with descriptions
- Verified vs unverified facilities
- Full details of all jobs

### Export to CSV

```bash
python export_to_csv.py
```

Exports all jobs from database to `jobs.csv`

## GitHub Actions Workflow

### Automated Daily Scraping

The workflow runs automatically every day at midnight UTC and can also be triggered manually.

**Workflow file:** `.github/workflows/deploy.yml`

```yaml
on:
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight UTC
  workflow_dispatch:      # Manual trigger
```

### What the Workflow Does

1. Checks out the repository
2. Sets up Python 3.11
3. Installs dependencies
4. Runs `api_scraper.py`
5. Commits and pushes updated `jobs.db` and logs

### Manual Trigger

1. Go to your repository on GitHub
2. Click **Actions** tab
3. Select **Daily Job Scraper** workflow
4. Click **Run workflow** button
5. Select branch and click **Run workflow**

### Required Permissions

The workflow needs `contents: write` permission to commit changes. This is already configured in `deploy.yml`.

## How It Works

### 1. Facility Name Extraction

The scraper uses regex patterns to extract facility names from job titles:

- County facilities: `County Jail`, `County Sheriff`, etc.
- State facilities: `State Prison`, `Correctional Facility`, etc.
- Federal facilities: `Penitentiary`, `Detention Center`, etc.

### 2. Fuzzy Matching

Extracted facility names are matched against `clean_prisons.txt` using:
- `difflib.SequenceMatcher` for similarity scoring
- 70% threshold for verification
- Best match selection

### 3. Incremental Updates

- Only new jobs are added to the database
- Descriptions are fetched only for new jobs (with 0.5s delay between requests)
- Existing jobs are not updated

## Logs

Each scraping run generates a timestamped log file in `logs/` directory:

```
logs/api_scraper_20251025_223050.log
```

Log includes:
- Jobs fetched count
- New jobs added
- Verified vs unverified facilities
- Errors and warnings

## API Endpoint

The scraper uses Aramark's public API:

```
https://careers.aramark.com/wp-json/aramark/jobs?industries=correctional%20facilities&limit=500
```

## Troubleshooting

### No new jobs found
- Check if API is accessible
- Verify the API endpoint hasn't changed
- Review logs for errors

### Facility not verified
- Add the facility to `clean_prisons.txt`
- Ensure exact or similar spelling
- Check fuzzy matching threshold (currently 70%)

### GitHub Actions failing
- Check workflow logs in Actions tab
- Verify repository permissions
- Ensure `clean_prisons.txt` is committed

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally
5. Submit a pull request

## License

This project is for educational and research purposes.
