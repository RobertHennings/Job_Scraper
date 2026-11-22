from typing import List, Dict
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import os
import pandas as pd
import datetime as dt
import sys

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
        for search_term in search_terms:
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
        """Visit an individual job posting page and extract additional metadata.

        Args:
            job_url (str): The URL of the individual job posting.

        Returns:
            Dict[str, str]: A dictionary containing additional job details such as description, seniority level, employment type, job function, industries, and number of applicants.
        """
        details = {}
        try:
            job_scraper_log.info(f"Loading Job Details for Job URL: {job_url}")
            self.driver.get(job_url)
            time.sleep(1.5)

            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # Full description
            desc = soup.find("div", class_="show-more-less-html__markup")
            if desc:
                details["description"] = desc.get_text(separator="\n").strip()

            # Criteria list (seniority, employment type, job function, industries)
            criteria_items = soup.find_all(
                "li", class_="description__job-criteria-item"
            )
            criteria_mapping = {
                "Seniority level": "seniority_level",
                "Employment type": "employment_type",
                "Job function": "job_function",
                "Industries": "industries",
            }
            for item in criteria_items:
                header = item.find(
                    "h3",
                    class_="description__job-criteria-subheader",
                )
                value = item.find(
                    "span",
                    class_="description__job-criteria-text",
                )
                if header and value:
                    key = header.text.strip()
                    if key in criteria_mapping:
                        details[criteria_mapping[key]] = value.text.strip()

            # Number of applicants
            applicants = soup.find(
                "span", class_="num-applicants__caption"
            ) or soup.find("figcaption", class_="num-applicants__caption")
            if applicants:
                details["num_applicants"] = applicants.text.strip()
            job_scraper_log.info(f"Number of applicants: {details['num_applicants']}")

        except Exception as e:
            job_scraper_log.error(f"Error scraping job details at {job_url}: {e}")

        return details

    def filter_for_companies(self, companies: List[str]):
        """Filter jobs for specific companies.

        Args:
            companies (List[str]): The list of companies to filter for.
        """
        job_scraper_log.info(f"Filtering jobs for companies: {', '.join(companies)}")
        self.jobs = [job for job in self.jobs if job["company"] in companies]

    def save_to_csv(
        self,
        file_path: str,
        filename: str = f"linkedin_jobs_{dt.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv",
        fieldnames: List[str] = [
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
            "company_logo_url",
            "link",
        ],
        sort_for_newest: bool = True,
    ) -> None:
        """Save scraped jobs to CSV file

        Args:
            filename (str, optional): The name of the CSV file to save the jobs to. Defaults to "linkedin_jobs.csv".
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
            # Sort the jobs df for posting date in descending order before saving to CSV
            sorted_jobs_df = self.get_jobs_df(sort_for_newest=True)
            # Select the chosen columns in the specified order before saving to CSV
            sorted_jobs_df = sorted_jobs_df[fieldnames]
            # Save to .csv file
            sorted_jobs_df.to_csv(full_file_path, index=False, encoding="utf-8")
        else:
            # Sort the jobs df for posting date in descending order before saving to CSV
            sorted_jobs_df = self.get_jobs_df(sort_for_newest=False)
            # Select the chosen columns in the specified order before saving to CSV
            sorted_jobs_df = sorted_jobs_df[fieldnames]
            # Save to .csv file
            sorted_jobs_df.to_csv(full_file_path, index=False, encoding="utf-8")
        job_scraper_log.info(f"Saved {len(self.jobs)} jobs to {filename}")

    def get_jobs_df(
        self, sort_for_newest: bool = True, dt_column: str = "date_posted_datetime"
    ) -> pd.DataFrame:
        """Get the scraped jobs as a pandas DataFrame.

        Returns:
            pd.DataFrame: The DataFrame of scraped jobs.
        """
        jobs_df = pd.DataFrame(self.jobs)
        if sort_for_newest:
            jobs_df[dt_column] = pd.to_datetime(
                jobs_df[dt_column], format="%Y-%m-%d", errors="coerce"
            )
            print(type(jobs_df[dt_column]))
            jobs_df = jobs_df.sort_values(dt_column, ascending=False)
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
    ]
    # 3) Define the locations
    locations = [
        "Germany",
    ]
    # 4) Scrape the jobs
    scraper.scrape_jobs(search_terms=search_terms, locations=locations)
    # 5) Get the jobs DataFrame
    jobs_df = scraper.get_jobs_df()
    # 6) Save the jobs DataFrame to CSV
    today = dt.datetime.now().strftime("%Y-%m-%d")
    filename = rf"linkedin_jobs_{today}.csv"
    file_path = r"Job_Scraper"
    os.makedirs(file_path, exist_ok=True)
    scraper.save_to_csv(
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
        smtp_server="://gmail.com",
        smtp_port=587,
        sender_email=sender_email,
        sender_password=sender_password,
    )
    # 9) Transform the pandas Dataframe to html table to be properly displayed in the email body
    jobs_table = jobs_df.to_html(index=False)
    email_body = f"""
    <html>
    <body>
        <h1>Job Opportunities</h1>
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
