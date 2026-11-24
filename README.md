# LinkedIn Job Scraper

An automated job scraper that searches LinkedIn for junior/graduate trading positions in Germany, saves the results to CSV, and emails a daily summary — all running automatically via GitHub Actions.


To trigger the cron job and the execution of the script a POST request is sent via a configured cron schedule on: https://console.cron-job.org/login.
## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Running Locally](#running-locally)
  - [Automated Scheduling (GitHub Actions)](#automated-scheduling-github-actions)
- [Output Data](#output-data)
- [GitHub Actions Setup](#github-actions-setup)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Features

- **Automated LinkedIn job scraping** for configured search terms and locations
- **Detailed job metadata extraction** including:
  - Job title, company, and location
  - Date posted (raw text + ISO datetime)
  - Salary information
  - Benefits
  - Seniority level, employment type, job function, and industries
  - Number of applicants
  - Company logo URL and job link
  - Full job description (when individual listing scraping is enabled)
- **Date-sorted output** written to timestamped CSV files
- **Email Notifier** that sends an HTML summary table with the scraped jobs as an attachment
- **GitHub Actions workflow** for fully automated scheduled runs (twice per hour)
- **Automatic commit/push** of updated CSV and log files back to the repository
- **Headless Chrome** execution, suitable for CI/CD environments

---

## Project Structure

```
job_scraper/
├── .github/
│   └── workflows/
│       └── daily-linkedin-scraper.yml    # GitHub Actions workflow
├── Job_Scraper/                            # Output directory for scraped CSV files
├── email_notifier.py                       # Email notification module
├── email_notifier.log                      # Email notifier log output
├── job_scraper.py                          # Main scraper entry point
├── job_scraper.log                         # Scraper log output
├── linkedin_jobs.csv                       # Latest scraped jobs (repository root)
├── requirements.txt                        # Python dependencies
├── .env                                    # Local environment variables (gitignored)
└── README.md
```

---

## Prerequisites

- **Python 3.11+**
- **Chrome browser** (for local runs; GitHub Actions installs it automatically)
- **Gmail account** with an [App Password](https://support.google.com/accounts/answer/185833) (if sending emails)

---

## Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd job_scraper
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Configuration

### Environment Variables

Set the following environment variables locally (e.g., in a `.env` file) or as GitHub Secrets:

| Variable           | Description                                | Required |
|-------------------|--------------------------------------------|----------|
| `SENDER_EMAIL`    | Gmail address used to send notifications   | ✅ Yes  |
| `SENDER_PASSWORD` | Gmail App Password for SMTP authentication | ✅ Yes  |
| `RECIPIENT_EMAIL` | Email address receiving the daily summary  | ✅ Yes  |

### Customizing Search Terms and Locations

Edit the `if __name__ == "__main__"` block in `job_scraper.py`:

```python
search_terms = [
    "Graduate Trading",
    "Junior Trading",
]

locations = [
    "Germany",
]
```

Modify these lists to match your job search preferences.

---

## Usage

### Running Locally

```bash
python job_scraper.py
```

This will:

1. Launch a headless Chrome instance
2. Scrape LinkedIn for the configured search terms and locations
3. Save results to `Job_Scraper/linkedin_jobs_<YYYY-MM-DD>.csv`
4. Send an email summary with the job listings as an attachment
5. Log all activity to `job_scraper.log` and `email_notifier.log`

### Automated Scheduling (GitHub Actions)

The included workflow (`.github/workflows/daily-linkedin-scraper.yml`) runs the scraper **twice per hour** at minutes `:12` and `:42` (UTC). It:

1. Checks out the repository
2. Sets up Python 3.11
3. Installs Chrome
4. Installs Python dependencies
5. Runs the scraper with GitHub Secrets as environment variables
6. Commits and pushes any updated CSV/log files back to the repository

> **Note:** GitHub Actions cron schedules use **UTC** by default. The schedule `12,42 * * * *` runs at 12:12/12:42 UTC = 14:12/14:42 German time (CEST, UTC+2).

---

## Output Data

Scraped results are saved as CSV files containing the following fields:

| Column                  | Description                               |
|-------------------------|-------------------------------------------|
| `search_term`           | The search keyword used                   |
| `search_location`       | The location searched                     |
| `title`                 | Job title                                 |
| `company`               | Company name                              |
| `location`              | Job location                              |
| `date_posted`           | Human-readable posting date               |
| `date_posted_datetime`  | ISO 8601 posting date                     |
| `salary`                | Salary range (if available)               |
| `benefits`              | Benefits text (if available)              |
| `seniority_level`       | E.g., "Entry level", "Associate"          |
| `employment_type`       | E.g., "Full-time", "Contract"             |
| `job_function`          | E.g., "Finance", "Engineering"            |
| `industries`            | Industries listed on the posting          |
| `num_applicants`        | Number of applicants                      |
| `description`           | Full job description (if requested)       |
| `company_logo_url`      | URL of the company logo                   |
| `link`                  | Direct URL to the LinkedIn job posting    |

---

## GitHub Actions Setup

### 1. Add GitHub Secrets

Navigate to **Settings → Secrets and variables → Actions** in your repository and add:

- `SENDER_EMAIL`
- `SENDER_PASSWORD`
- `RECIPIENT_EMAIL`

### 2. Ensure Workflow is on the Default Branch

The workflow file must exist on your repository's **default branch** (`main` or `master`) for the cron schedule to work.

### 3. Enable the Workflow

Go to the **Actions** tab in your repository. If the workflow is not listed, it may have been automatically disabled — re-enable it.

### 4. Manually Trigger (Optional)

You can run the workflow on-demand anytime by:

1. Going to the **Actions** tab
2. Selecting the **"Daily LinkedIn Job Scraper"** workflow
3. Clicking **Run workflow**

---

## Troubleshooting

| Issue                                    | Solution                                                                                              |
|------------------------------------------|-------------------------------------------------------------------------------------------------------|
| **Workflow doesn't run on schedule**     | - Confirm the workflow is on the default branch<br>- Check if it's disabled in the Actions tab<br>- Note: GitHub delays scheduled runs by up to 15–20 minutes on free plans |
| **`pandas==3.0.5` install fails**        | Use a valid version (e.g., `pandas==3.1.1`) — update `requirements.txt`                              |
| **Email not sent**                       | - Verify `SENDER_EMAIL`/`SENDER_PASSWORD` secrets are set<br>- Use a [Gmail App Password](https://support.google.com/accounts/answer/185833), not your normal password |
| **Chrome/Chromedriver errors**           | Ensure Chrome is installed (`browser-actions/setup-chrome@v1` handles this in CI)                      |
| **LinkedIn blocks or returns no results**| - Add `--headless=new` and a realistic `user-agent` (already configured)<br>- Reduce scraping frequency to avoid rate limiting |
| **No jobs found — workflow exits `0`**   | The script exits successfully with a warning when no jobs are scraped. Check `job_scraper.log` for details |

---

## License

This project is for personal educational use. LinkedIn's Terms of Service prohibit unauthorized scraping of their platform — use responsibly and at your own risk.
