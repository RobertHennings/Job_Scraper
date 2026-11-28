# LinkedIn Job Scraper with Excel & HTML Export and Email Notifications

An automated job scraper that searches LinkedIn for defined search terms in the specified locations, saves the results to both Excel and interactive HTML files (with shortened links), and emails a daily summary with both files as attachments — all running automatically via GitHub Actions.

## To trigger the cron job and the execution of the script

A POST request is sent via a configured cron schedule on: <https://console.cron-job.org/login>.

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
"- [Interactive HTML Report](#interactive-html-report)
- [GitHub Actions Setup](#github-actions-setup)"
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
- **Excel export** with professional column headers and shortened URLs (using TinyURL)
- **Interactive HTML export** with a keyword search bar and dropdown filters for search term, search location, and company name
- **Date-sorted output** written to timestamped Excel and HTML files
- **Email Notifier** that sends an HTML summary table with both the Excel file and interactive HTML file as attachments
- **GitHub Actions workflow** for fully automated scheduled runs (every 30 minutes during business hours)
- **Automatic commit/push** of updated Excel and log files back to the repository
- **Headless Chrome** execution, suitable for CI/CD environments

---

## Project Structure

```
job_scraper/
├── .github/
│   └── workflows/
│       └── daily-linkedin-scraper.yml    # GitHub Actions workflow

├── Job_Scraper/                            # Output directory for scraped Excel files
├── Job_Scraper_HTML/                       # Output directory for interactive HTML reports
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

3. Save results to `Job_Scraper/linkedin_jobs_<YYYY-MM-DD_HH-MM>.xlsx`
4. Save an interactive HTML report to `Job_Scraper_HTML/linkedin_jobs_<YYYY-MM-DD_HH-MM>.html` (with keyword search and filter dropdowns)
5. Send an email summary with both the Excel file and interactive HTML file as attachments
6. Log all activity to `job_scraper.log` and `email_notifier.log`

The included workflow (`.github/workflows/daily-linkedin-scraper.yml`) runs the scraper **every 30 minutes during business hours** (7-9 AM German time, UTC+2). It:

1. Checks out the repository
2. Sets up Python 3.11
3. Installs Chrome
4. Installs Python dependencies
5. Runs the scraper with GitHub Secrets as environment variables
6. Commits and pushes any updated Excel, HTML, and log files back to the repository

---

## Output Data

Scraped results are saved as Excel files and interactive HTML reports. The data in both formats contains the following fields:

| Column                  | Description                               |
|-------------------------|-------------------------------------------|
| `Search Term`           | The search keyword used                   |
| `Search Location`       | The location searched                     |
| `Job Title`             | Job title                                 |
| `Company Name`          | Company name                              |
| `Job Location`          | Job location                              |
| `Date Posted`           | Human-readable posting date               |
| `Date Posted (Datetime)`| ISO 8601 posting date                     |
| `Salary`                | Salary range (if available)               |
| `Benefits`              | Benefits text (if available)              |
| `Seniority Level`       | E.g., "Entry level", "Associate"        |
| `Employment Type`       | E.g., "Full-time", "Contract"           |
| `Job Function`          | E.g., "Finance", "Engineering"          |
| `Industries`            | Industries listed on the posting          |
| `Num Applicants`        | Number of applicants                      |
| `Description`           | Full job description (if requested)       |
| `Company Logo URL`      | Shortened URL to the company logo         |
| `Job Link`              | "Shortened direct URL to the LinkedIn job  |

---

## Interactive HTML Report

In addition to the Excel file, the scraper generates a self-contained interactive HTML report at `Job_Scraper_HTML/linkedin_jobs_<timestamp>.html`.

### Features

- **Keyword search bar** — type any keyword to filter jobs across all columns (title, company, location, skills, etc.)
- **Dropdown filters** — narrow results by search term, search location, or company name
- **Live row counter** — shows how many jobs match your current filters out of the total
- **Zero dependencies** — fully self-contained (HTML + CSS + vanilla JavaScript), works offline in any modern browser

### Use Case

Open the HTML file in your browser and use the search bar and filters to quickly find jobs matching specific criteria. For example:

1. Select a company from the Company Name dropdown
2. Type a skill like "Python" in the search bar
3. See the updated count of matching jobs

This makes it easy to quickly triage the daily job listings without opening Excel.

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
| **`openpyxl==3.1.5` install fails**      | Use a valid version (e.g., `openpyxl==3.1.2`) — update `requirements.txt`                           |
| **Shortened links not working**          | TinyURL may occasionally have issues — check internet connectivity during execution                    |
| **Email not sent**                       | - Verify `SENDER_EMAIL`/`SENDER_PASSWORD` secrets are set<br>- Use a [Gmail App Password](https://support.google.com/accounts/answer/185833), not your normal password |
| **Chrome/Chromedriver errors**           | Ensure Chrome is installed (`browser-actions/setup-chrome@v1` handles this in CI)                      |
| **LinkedIn blocks or returns no results**| - Add `--headless=new` and a realistic `user-agent` (already configured)<br>- Reduce scraping frequency to avoid rate limiting |
| **No jobs found — workflow exits `0`**   | The script exits successfully with a warning when no jobs are scraped. Check `job_scraper.log` for details |

---

## License

This project is for personal educational use. LinkedIn's Terms of Service prohibit unauthorized scraping of their platform — use responsibly and at your own risk.
