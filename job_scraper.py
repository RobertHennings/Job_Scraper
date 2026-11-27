from typing import List, Dict
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import time
import os
import re
import pandas as pd
import datetime as dt
import sys
import pyshorteners
from zoneinfo import ZoneInfo

# Import the EmailNotifier class from email_notifier.py
from email_notifier import EmailNotifier

# Create logger
logging.basicConfig(
    force=True,
    filename="job_scraper.log",
    encoding="utf-8",
)
job_scraper_log = logging.getLogger("job_scraper")
job_scraper_log.setLevel(logging.INFO)
# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s",
)
# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
job_scraper_log.addHandler(ch)

# Set up static global variables
BASE_URL = "https://www.linkedin.com/jobs/search/"
COL_NAME_MAPPING_DICT = {
    "search_term": "Search Term",
    "search_location": "Search Location",
    "title": "Job Title",
    "company": "Company Name",
    "location": "Job Location",
    "date_posted": "Date Posted",
    "date_posted_datetime": "Date Posted (Datetime)",
    "company_logo_url": "Company Logo URL",
    "link": "Job Link",
}
FIELDNAMES = [
    "search_term",
    "search_location",
    "title",
    "company",
    "location",
    "date_posted",
    "date_posted_datetime",
    "salary",
    "benefits",
    "seniority_level",
    "employment_type",
    "job_function",
    "industries",
    "num_applicants",
    "description",
    "link",
]
# Get .env file path
env_file_path = os.path.join(os.path.dirname(__file__), ".env")
# Load environment variables from .env file
# if os.path.exists(env_file_path):
#     from dotenv import load_dotenv

#     load_dotenv(env_file_path)


class LinkedInJobScraper:
    def __init__(self) -> None:
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        # Helps prevent LinkedIn from immediately flagging the headless Linux browser
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        self.driver = webdriver.Chrome(options=chrome_options)
        self.jobs = []

    def scrape_jobs(
        self,
        search_terms: List[str] = None,
        locations: List[str] = None,
        search_single_listings: bool = False,
        base_url: str = BASE_URL,
    ) -> None:
        """Scrape LinkedIn jobs for given search terms, locations, and companies.
           All three parameters are lists; every combination is searched.

        Args:
            search_terms (List[str], optional): The search terms to use. Defaults to None.
            locations (List[str], optional): The locations to search in. Defaults to None.
            search_single_listings (bool, optional): Whether to search for single job listings. Defaults to False.
            base_url (str, optional): The base URL for the job search. Defaults to "https://www.linkedin.com/jobs/search/".
        """
        url_ready_search_terms = [
            search_term.replace(" ", "+") for search_term in search_terms
        ]
        for search_term in url_ready_search_terms:
            for location in locations:
                url = f"{base_url}?keywords={search_term}&location={location}"
                job_scraper_log.info(
                    f"Scraping jobs for '{search_term}' in '{location}'.\nURL: {url}"
                )
                self.driver.get(url)
                time.sleep(2)

                try:
                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_all_elements_located(
                            (By.CLASS_NAME, "base-card")
                        )
                    )

                    soup = BeautifulSoup(self.driver.page_source, "html.parser")
                    job_scraper_log.info(f"Inspecting URL returned soup.")
                    job_cards = soup.find_all("div", class_="base-card")
                    job_scraper_log.info(
                        f"Found {len(job_cards)} job cards for '{search_term}' in '{location}'"
                    )
                    for card in job_cards:
                        job_title = card.find("h3", class_="base-search-card__title")
                        company_name = card.find(
                            "h4", class_="base-search-card__subtitle"
                        )
                        location_elem = card.find(
                            "span", class_="job-search-card__location"
                        )
                        job_link = card.find("a", class_="base-card__full-link")
                        date_elem = card.find(
                            "time", class_="job-search-card__listdate"
                        ) or card.find(
                            "time",
                            class_="job-search-card__listdate--new",
                        )
                        salary_elem = card.find(
                            "span",
                            class_="job-search-card__salary-info",
                        )
                        benefits_elem = card.find(
                            "span",
                            class_="result-benefits__text",
                        )
                        company_logo = card.find("img")

                        if all([job_title, company_name, location_elem]):
                            link = job_link["href"] if job_link else "N/A"
                            job_data = {
                                "search_term": search_term,
                                "search_location": location,
                                "title": job_title.text.strip(),
                                "company": company_name.text.strip(),
                                "location": location_elem.text.strip(),
                                "date_posted": (
                                    date_elem.text.strip() if date_elem else "N/A"
                                ),
                                "date_posted_datetime": (
                                    date_elem.get("datetime", "N/A")
                                    if date_elem
                                    else "N/A"
                                ),
                                "salary": (
                                    salary_elem.text.strip() if salary_elem else "N/A"
                                ),
                                "benefits": (
                                    benefits_elem.text.strip()
                                    if benefits_elem
                                    else "N/A"
                                ),
                                "company_logo_url": (
                                    company_logo["data-delayed-url"]
                                    if company_logo
                                    and company_logo.has_attr("data-delayed-url")
                                    else (
                                        company_logo["src"]
                                        if company_logo and company_logo.has_attr("src")
                                        else "N/A"
                                    )
                                ),
                                "link": link,
                                "description": "N/A",
                                "seniority_level": "N/A",
                                "employment_type": "N/A",
                                "job_function": "N/A",
                                "industries": "N/A",
                                "num_applicants": "N/A",
                            }

                            # Visit individual job page for more details
                            if search_single_listings:
                                if link != "N/A":
                                    job_data.update(self._scrape_job_details(link))

                        self.jobs.append(job_data)
                except Exception as e:
                    job_scraper_log.error(f"Error scraping: {e}")
        job_scraper_log.info(f"Scraping complete. Total jobs found: {len(self.jobs)}")

    def _scrape_job_details(self, job_url: str) -> Dict[str, str]:
        """Scrape job details from LinkedIn with robust handling of missing data.

        Based on actual LinkedIn job page structure observed from job postings.
        Handles both direct employer postings and agency/recruiter postings.
        """
        # Initialize all fields with default "N/A" values to avoid <NA> in DataFrame
        details = {
            "description": "N/A",
            "salary": "N/A",
            "benefits": "N/A",
            "seniority_level": "N/A",
            "employment_type": "N/A",
            "job_function": "N/A",
            "industries": "N/A",
            "num_applicants": "N/A",
            "company_name": "N/A",
            "location": "N/A",
            "posted_date": "N/A",
            "date_posted_datetime": "N/A",
            "is_agency_posting": "N/A",
        }
        try:
            job_scraper_log.info(f"Scraping job details: {job_url}")
            self.driver.get(job_url)

            # Wait for main job container to load (more flexible selector)
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        "div.jobs-description, div.job-details, div.show-more-less-html__markup",
                    )
                )
            )
            time.sleep(2)  # Allow final JS rendering

            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # 1. Description (Robust fallbacks)
            desc = soup.find("div", class_="show-more-less-html__markup")
            if not desc:
                desc = soup.find("div", class_="jobs-description__text")
            if not desc:
                desc = soup.find("div", {"data-test-job-detail": "job-description"})
            if not desc:
                desc = soup.find("div", class_="jobs-box__html-content")
            if not desc:
                desc = soup.find("div", {"data-test": "job-description"})
            if desc:
                details["description"] = desc.get_text(separator="\n").strip()

            # 2. Salary/Pay Range (Multiple selectors based on observed structure)
            salary = None
            # Try class-based selectors first
            salary_classes = [
                "jobs-salary__salary-range",
                "job-details__salary",
                "salary",
                "jobs-apply__salary",
            ]
            for cls in salary_classes:
                elem = soup.find(["span", "div"], class_=cls)
                if elem:
                    salary = elem.get_text(strip=True)
                    break

            # If not found, search for pay range text patterns
            if not salary:
                pay_text = soup.find(
                    string=re.compile(r"£|€|\$|base pay|pay range", re.I)
                )
                if pay_text and pay_text.parent:
                    salary = pay_text.parent.get_text(strip=True)

            # Also check for pay range sections (observed in agency postings like Anson McCade)
            if not salary:
                pay_section = soup.find(
                    "section", string=re.compile(r"base pay|pay range", re.I)
                )
                if pay_section:
                    salary = pay_section.get_text(strip=True)

            if salary:
                # Extract and clean salary range (e.g., "£100,000.00/yr - £200,000.00/yr")
                salary_match = re.search(
                    r"[£€\$][\d,]+(?:\.\d+)?(?:\s*[-–]\s*[£€\$][\d,]+(?:\.\d+)?)?",
                    salary,
                )
                if salary_match:
                    details["salary"] = salary_match.group()
                else:
                    details["salary"] = salary

            # 3. Benefits (Often in a list or mentioned in description)
            benefits = []
            benefit_keywords = [
                "health",
                "dental",
                "vision",
                "401",
                "pension",
                "holiday",
                "vacation",
                "bonus",
                "equity",
                "sign-on",
                "stock",
                "insurance",
                "paid time off",
                "ptp",
            ]

            # Look for benefits sections
            benefit_containers = soup.find_all(
                ["div", "section", "ul"], string=re.compile(r"benefit|perk", re.I)
            )
            for container in benefit_containers:
                parent = (
                    container.find_parent(["div", "section"])
                    if container.name != "section"
                    else container
                )
                if parent:
                    items = parent.find_all(["li", "span", "div"])
                    for item in items:
                        text = item.get_text(strip=True).lower()
                        if any(kw in text for kw in benefit_keywords):
                            benefits.append(item.get_text(strip=True))

            # Also check for benefits mentioned in description
            if details["description"] != "N/A":
                desc_text = details["description"].lower()
                if any(kw in desc_text for kw in benefit_keywords):
                    # Extract sentence mentioning benefits
                    sentences = details["description"].split(".")
                    for sentence in sentences:
                        if any(kw in sentence.lower() for kw in benefit_keywords):
                            benefits.append(sentence.strip())

            if benefits:
                details["benefits"] = "; ".join(
                    list(dict.fromkeys(benefits))[:10]
                )  # Limit to top 10, remove duplicates

            # 4. Job Criteria (Seniority, Employment Type, Job Function, Industries)
            criteria_mapping = {
                "Seniority level": "seniority_level",
                "Employment type": "employment_type",
                "Job function": "job_function",
                "Industries": "industries",
            }

            # Try multiple class names for criteria items
            criteria_selectors = [
                "description__job-criteria-item",
                "job-details__job-criteria-item",
                "jobs-details__job-criteria-item",
                "job-criteria__item",
                "jobs-description__job-criteria-item",
            ]

            criteria_items = []
            for sel in criteria_selectors:
                items = soup.find_all("li", class_=sel)
                if items:
                    criteria_items = items
                    break

            for item in criteria_items:
                header = item.find("h3", class_="description__job-criteria-subheader")
                value = item.find("span", class_="description__job-criteria-text")
                if header and value:
                    key = header.get_text(strip=True)
                    if key in criteria_mapping:
                        details[criteria_mapping[key]] = value.get_text(strip=True)

            # Fallback: Look for tags/labels (observed in agency postings like "Entry level", "Full-time")
            if (
                details["seniority_level"] == "N/A"
                or details["employment_type"] == "N/A"
            ):
                tags = soup.find_all(
                    "span", class_=re.compile(r"label|tag|badge", re.I)
                )
                for tag in tags:
                    text = tag.get_text(strip=True).lower()
                    if any(
                        level in text
                        for level in [
                            "entry level",
                            "junior",
                            "senior",
                            "associate",
                            "mid",
                            "executive",
                        ]
                    ):
                        if details["seniority_level"] == "N/A":
                            details["seniority_level"] = tag.get_text(strip=True)
                    if any(
                        emp in text
                        for emp in [
                            "full-time",
                            "part-time",
                            "contract",
                            "temporary",
                            "internship",
                        ]
                    ):
                        if details["employment_type"] == "N/A":
                            details["employment_type"] = tag.get_text(strip=True)

            # 5. Number of Applicants (Only visible if logged in)
            applicants = None
            applicant_selectors = [
                "num-applicants__caption",
                "jobs-details__num-applicants",
                "job-details__num-applicants",
                "jobs-apply__applicants-count",
            ]
            for sel in applicant_selectors:
                elem = soup.find("span", class_=sel) or soup.find(
                    "figcaption", class_=sel
                )
                if elem:
                    applicants = elem.get_text(strip=True)
                    break

            if applicants:
                # Clean: "100+ applicants" → "100"
                num = re.sub(r"[^0-9]", "", applicants)
                details["num_applicants"] = num if num else applicants

            # 6. Company Name (Multiple selectors)
            company = soup.find("a", class_="job-details__company-name")
            if not company:
                company = soup.find("a", {"data-test": "company-name"})
            if not company:
                company = soup.find("a", href=re.compile(r"linkedin.com/company", re.I))
            if not company:
                company = soup.find("h4", class_="job-details__company-name")
            if not company:
                company = soup.find("div", class_="job-details__company-name")
            if company:
                details["company_name"] = company.get_text(strip=True)

            # 7. Location (Multiple selectors)
            location = soup.find("span", class_="job-details__job-location")
            if not location:
                location = soup.find("span", {"data-test": "job-location"})
            if not location:
                location = soup.find(
                    "span",
                    string=re.compile(
                        r"London|United Kingdom|Germany|Remote|Hybrid", re.I
                    ),
                )
            if not location:
                # Try finding location in the job header
                header = soup.find("h4", class_="job-details__job-location")
                if header:
                    location = header
            if location:
                details["location"] = location.get_text(strip=True)

            # 8. Posted Date
            posted = soup.find("time", class_="job-search-card__listdate")
            if not posted:
                posted = soup.find("time", class_="job-search-card__listdate--new")
            if not posted:
                posted = soup.find(
                    "span", string=re.compile(r"ago|posted|day|week|month", re.I)
                )
            if posted:
                details["posted_date"] = posted.get_text(strip=True)
                # Try to extract datetime attribute
                if posted.has_attr("datetime"):
                    details["date_posted_datetime"] = posted.get("datetime")

            # 9. Detect if this is an agency/recruiter posting vs direct employer
            recruiter_indicators = [
                "recruiter",
                "agency",
                "provided pay range",
                "talk with your recruiter",
                "direct message the job poster",
            ]
            page_text = soup.get_text().lower()
            if any(indicator in page_text for indicator in recruiter_indicators):
                details["is_agency_posting"] = "Yes"
            else:
                details["is_agency_posting"] = "No"

        except TimeoutException:
            job_scraper_log.warning(f"Timeout loading job: {job_url}")
            details["error"] = "Timeout"
        except Exception as e:
            job_scraper_log.error(f"Error scraping job {job_url}: {e}")
            details["error"] = str(e)

        return details

    def filter_for_companies(self, companies: List[str]):
        """Filter jobs for specific companies.

        Args:
            companies (List[str]): The list of companies to filter for.
        """
        job_scraper_log.info(f"Filtering jobs for companies: {', '.join(companies)}")
        self.jobs = [job for job in self.jobs if job["company"] in companies]

    def _save(
        self,
        file_path: str,
        filename: str = f"linkedin_jobs_{dt.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv",
        fieldnames: List[str] = FIELDNAMES,
        sort_for_newest: bool = True,
        col_name_mapping_dict: Dict[str, str] = COL_NAME_MAPPING_DICT,
        shorten_links: bool = True,
        drop_duplicates: bool = True,
        duplicates_col_names_subset: List[str] = [
            "title",
            "company",
            "location",
            "date_posted",
            "link",
        ],
    ) -> None:
        """Save scraped jobs to CSV file

        Args:
            file_path (str, optional): The path to the directory where the file will be saved. Defaults to the current directory.
            filename (str, optional): The name of the CSV file to save the jobs to. Defaults to "linkedin_jobs.csv".
            fieldnames (List[str], optional): The list of field names to include in the CSV file. Defaults to the predefined field names.
            sort_for_newest (bool, optional): Whether to sort the jobs by date posted in descending order. Defaults to True.
        """
        if not self.jobs:
            job_scraper_log.error("No jobs found")
            return
        full_file_path = os.path.join(file_path, filename) if file_path else filename
        job_scraper_log.info(
            f"Saving file: {filename} under file path: {file_path}\nFull file path: {full_file_path}"
        )
        if sort_for_newest:
            sort_for_newest = True
        else:
            sort_for_newest = False
        # Sort the jobs df for posting date in descending order before saving to CSV
        sorted_jobs_df = self.get_jobs_df(
            sort_for_newest=sort_for_newest,
            fieldnames=fieldnames,
            shorten_links=shorten_links,
            col_name_mapping_dict=col_name_mapping_dict,
            drop_duplicates=drop_duplicates,
            duplicates_col_names_subset=duplicates_col_names_subset,
        )
        # Select the chosen columns in the specified order before saving to CSV
        sorted_jobs_df = sorted_jobs_df.replace("N/A", pd.NA)
        sorted_jobs_df = sorted_jobs_df.dropna(axis="columns", how="all")
        sorted_jobs_df = sorted_jobs_df.rename(columns=col_name_mapping_dict)
        # Save to .csv file
        # sorted_jobs_df.to_csv(full_file_path, index=False, encoding="utf-8")
        # save to excel file
        sorted_jobs_df.to_excel(full_file_path, index=False)
        job_scraper_log.info(f"Saved {len(self.jobs)} jobs to {filename}")

    def get_jobs_df(
        self,
        sort_for_newest: bool = True,
        dt_column: str = "date_posted_datetime",
        fieldnames: List[str] = FIELDNAMES,
        col_name_mapping_dict: Dict[str, str] = COL_NAME_MAPPING_DICT,
        shorten_links: bool = True,
        drop_duplicates: bool = True,
        duplicates_col_names_subset: List[str] = [
            "title",
            "company",
            "location",
            "date_posted",
            "link",
        ],
    ) -> pd.DataFrame:
        """Get the scraped jobs as a pandas DataFrame.

        Args:
            sort_for_newest (bool, optional): Whether to sort the jobs by date posted in descending order. Defaults to True.
            dt_column (str, optional): The column name for the date posted datetime. Defaults to "date_posted_datetime".
            fieldnames (List[str], optional): The list of field names to include in the DataFrame. Defaults to the predefined field names.
            col_name_mapping_dict (Dict[str, str], optional): The dictionary mapping of column names to be renamed in the DataFrame. Defaults to the predefined mapping.
            shorten_links (bool, optional): Whether to shorten the job and company logo links using TinyURL. Defaults to True.
            drop_duplicates (bool, optional): Whether to drop duplicate job listings based on a subset of columns. Defaults to True.
            duplicates_col_names_subset (List[str], optional): The subset of column names to consider for identifying duplicates. Defaults to ["title", "company", "location", "date_posted", "link"].
        Returns:
            pd.DataFrame: The DataFrame of scraped jobs.
        """
        jobs_df = pd.DataFrame(self.jobs)
        # Drop duplicates based on the specified subset of columns
        if drop_duplicates:
            job_scraper_log.info(
                f"Dropping duplicates based on columns: {', '.join(duplicates_col_names_subset)}"
            )
            duplicated_mask = jobs_df.duplicated(
                subset=duplicates_col_names_subset, keep="first"
            )
            num_duplicates = duplicated_mask.sum()
            job_scraper_log.info(f"Found {num_duplicates} duplicate job listings.")
            if num_duplicates > 0:
                job_scraper_log.info(
                    f"Dropping {num_duplicates} duplicate job listings."
                )
                jobs_df = jobs_df.drop_duplicates(subset=duplicates_col_names_subset)

        if sort_for_newest:
            job_scraper_log.info(f"Sorting jobs by '{dt_column}' in descending order")
            jobs_df[dt_column] = pd.to_datetime(
                jobs_df[dt_column], format="%Y-%m-%d", errors="coerce"
            )
            jobs_df = jobs_df.sort_values(dt_column, ascending=False).reset_index(
                drop=True
            )
        job_scraper_log.info(f"Final DataFrame shape: {jobs_df.shape}")
        jobs_df = jobs_df[fieldnames]
        jobs_df = jobs_df.replace("N/A", pd.NA)
        jobs_df = jobs_df.dropna(axis="columns", how="all")
        job_scraper_log.info(
            f"Final DataFrame shape after dropping empty columns: {jobs_df.shape}"
        )
        if shorten_links:
            job_scraper_log.info(
                f"Shortening job and company logo links using TinyURL."
            )
            type_tiny = pyshorteners.Shortener()
            jobs_df["link"] = [type_tiny.tinyurl.short(li) for li in jobs_df["link"]]
            jobs_df["company_logo_url"] = [
                type_tiny.tinyurl.short(li) for li in jobs_df["company_logo_url"]
            ]
        job_scraper_log.info(f"Renaming columns based on provided mapping dictionary.")
        jobs_df = jobs_df.rename(columns=col_name_mapping_dict)
        return jobs_df

    def close(self):
        self.driver.quit()


# Usage
if __name__ == "__main__":
    # 1) Set up the scraper instance
    scraper = LinkedInJobScraper()
    # 2) Define the search terms
    search_terms = [
        "Graduate Trading",
        "Junior Trading",
        "Energy Trading",
        "Trading Analyst",
        "Trading Analysis",
        "Power Trading",
    ]
    # 3) Define the locations
    locations = ["Germany", "London"]
    # 4) Scrape the jobs
    scraper.scrape_jobs(search_terms=search_terms, locations=locations)
    # 5) Get the jobs DataFrame
    jobs_df = scraper.get_jobs_df()
    # 6) Save the jobs DataFrame to Excel, current german local time
    today = dt.datetime.now(ZoneInfo("Europe/Berlin")).strftime("%Y-%m-%d %H:%M")
    filename = rf"linkedin_jobs_{today.replace(':', '-')}.xlsx"
    file_path = r"Job_Scraper"
    os.makedirs(file_path, exist_ok=True)
    scraper._save(
        file_path=file_path,
        filename=filename,
    )
    # 7) Close the scraper
    scraper.close()

    if jobs_df.empty:
        job_scraper_log.warning("No jobs scraped today. Skipping CSV save and email.")
        sys.exit(0)
    # 8) Set up the email notifier instance
    sender_email = os.environ.get("SENDER_EMAIL", "").strip()
    sender_password = os.environ.get("SENDER_PASSWORD", "").strip()
    recipient_email = os.environ.get("RECIPIENT_EMAIL", "").strip()

    notifier = EmailNotifier(
        # smtp_server="smtp.web.de",
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        sender_email=sender_email,
        sender_password=sender_password,
    )

    # 9) Transform the pandas Dataframe to html table to be properly displayed in the email body
    jobs_table = jobs_df.to_html(index=False)
    email_body = f"""
    <html>
    <body>
        <h1> Found {len(jobs_df)} Job Opportunities for {today}</h1>
        <p>Search terms: {", ".join(search_terms)}</p>
        <p>Locations: {", ".join(locations)}</p>
        <p>Here are the available job opportunities:</p>
        {jobs_table}
    </body>
    </html>
    """
    # 10) Send the email
    notifier.send_email(
        recipient_email=recipient_email,
        subject=f"LinkedIn Job Listings for day: {today}",
        body=email_body,
        attachments=[os.path.join(file_path, filename)],
    )
