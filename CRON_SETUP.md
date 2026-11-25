# External Cron Setup for GitHub Actions (`cron-job.org`)

This guide explains how to reliably trigger GitHub Actions workflows on an exact schedule using **cron-job.org** and GitHub's `workflow_dispatch` API, avoiding the delays and silent drops common with GitHub's native `schedule` trigger. It also covers passing custom `inputs` so individual recipients can have personalized schedules.

---

## Why Use an External Scheduler?

GitHub Actions evaluates native `schedule` events on a best-effort basis. During peak load times (especially `:00`, `:15`, `:30`, and `:45` minutes), scheduled workflows are frequently delayed or silently skipped. Using `cron-job.org` to send authenticated `POST` requests to the GitHub REST API guarantees timely execution and provides execution logs and failure alerts.

---

## Step 1: Configure the GitHub Actions Workflow

Update your workflow file (e.g., `.github/workflows/report.yml`) on your default branch (`main` or `master`) to accept `workflow_dispatch` triggers and an optional `recipient` input:

```yaml
name: Scheduled Job Report

on:
  workflow_dispatch:
    inputs:
      recipient:
        description: 'Identifier for the recipient receiving this report'
        required: false
        default: 'all'
        type: string

jobs:
  send-report:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Run report script
        env:
          TARGET_RECIPIENT: ${{ github.event.inputs.recipient }}
        run: python your_script.py
```

> **Note:** Setting `default: 'all'` ensures the workflow still runs cleanly if triggered manually from the GitHub Actions UI without specifying an input.

---

## Step 2: Handle the Recipient Input in Python

Read the `TARGET_RECIPIENT` environment variable inside your Python script (`your_script.py`) to filter which user receives the report during that specific run:

```python
import os

FRIENDS = {
    "alice": {"email": "alice@example.com", "name": "Alice"},
    "bob": {"email": "bob@example.com", "name": "Bob"},
}

recipient = os.getenv("TARGET_RECIPIENT", "all").strip().lower()

if recipient == "all":
    targets = list(FRIENDS.values())
elif recipient in FRIENDS:
    targets = [FRIENDS[recipient]]
else:
    raise ValueError(f"Unknown recipient: {recipient}")

for person in targets:
    print(f"Generating and sending report to {person['name']} ({person['email']})...")
    # Add your report generation and email/notification logic here
```

---

## Step 3: Generate a GitHub Personal Access Token (PAT)

1. Open your GitHub user **Settings** -> **Developer settings** -> **Personal access tokens** -> **Fine-grained tokens**.
2. Click **Generate new token** and configure:
   * **Token name:** `cron-job-org-trigger`
   * **Expiration:** Set an expiration date (and set a calendar reminder to rotate it before it expires).
   * **Repository access:** Select **Only select repositories** and choose this repository.
   * **Permissions:** Expand **Repository permissions**, locate **Actions**, and set it to **Read and write**.
3. Click **Generate token** and copy the `github_pat_...` token immediately.

> **Organization Repositories:** If the repository belongs to a GitHub Organization, ensure fine-grained PATs are approved by an organization admin, or use a **Classic Personal Access Token** (`ghp_...`) with the `workflow` scope enabled.

---

## Step 4: Set Up Jobs on `cron-job.org`

Create one cronjob per recipient schedule in your **cron-job.org** console:

### 1. Common Tab
* **Title:** Descriptive name (e.g., `Job Report - Alice`)
* **URL:** Replace `OWNER`, `REPO`, and `WORKFLOW_FILE.yml` with your repository details:
  ```text
  https://api.github.com/repos/OWNER/REPO/actions/workflows/WORKFLOW_FILE.yml/dispatches
  ```
* **Execution schedule:** Set the recipient's desired schedule/timezone.
* **Notifications:** Keep **when execution fails** enabled to receive alerts if the token expires or the API returns an error.

### 2. Advanced Tab
* **Request method:** `POST`
* **HTTP authentication:** Leave **Username** and **Password** completely blank (filling these overwrites the `Authorization` header and causes `401 Unauthorized` errors).
* **Headers:** Add the following four headers:

| Key | Value |
| :--- | :--- |
| `Accept` | `application/vnd.github+json` |
| `Authorization` | `Bearer YOUR_GITHUB_PAT` |
| `Content-Type` | `application/json` |
| `User-Agent` | `cron-job.org` |

* **Request body:** Specify the branch (`ref`) and the recipient identifier under `inputs`:

**Example for Alice:**
```json
{
  "ref": "main",
  "inputs": {
    "recipient": "alice"
  }
}
```

**Example for Bob:**
```json
{
  "ref": "main",
  "inputs": {
    "recipient": "bob"
  }
}
```

### 3. Test and Save
1. Click **Test run** at the bottom of the job configuration page.
2. Verify that the response returns **`204 No Content`** (this confirms GitHub accepted and queued the workflow run).
3. Click **Create** to save and activate the schedule.

---

## Troubleshooting

| HTTP Status | Cause | Fix |
| :--- | :--- | :--- |
| `401 Unauthorized` | Invalid, expired, or overwritten token. | Ensure there is a single space after `Bearer`, no trailing spaces, and **HTTP authentication** fields are empty. |
| `403 Forbidden` | Missing `User-Agent` header or insufficient PAT permissions. | Verify `User-Agent: cron-job.org` is set and the PAT has **Actions: Read and write** access. |
| `404 Not Found` | Incorrect owner, repo name, or workflow filename. | Double-check the URL path and ensure the workflow file exists on the default branch. |
| `422 Unprocessable Entity` | Branch doesn't exist or an undeclared input was sent. | Ensure `"ref"` matches an existing branch and every key inside `"inputs"` is defined under `workflow_dispatch.inputs` in the YAML file. |
