import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse
import time
import re

MAIN_URL = "https://www.nj.gov/csc/jobs/otherstate/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
REQUEST_DELAY = 1.0  # seconds between requests

SALARY_PATTERN = re.compile(
    r'(\$[\d,]+(?:\s*[-–]\s*\$[\d,]+)?(?:\s*/\s*(?:yr|year|hr|hour|annual))?'
    r'|Grade\s+\d+'
    r'|Level\s+\d+'
    r'|[\d,]+\s*[-–]\s*[\d,]+\s*/\s*(?:yr|year))',
    re.I
)


@dataclass
class Job:
    title: str
    department: str
    salary: str
    url: str


@dataclass
class DeptResult:
    name: str
    url: str
    tier: str  # "tier1", "tier2", "tier3"
    jobs: list = field(default_factory=list)


def get_departments() -> list[dict]:
    """Scrape the main NJ CSC page and return all department career links."""
    print(f"[INFO] Loading main page: {MAIN_URL}")
    try:
        resp = requests.get(MAIN_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Could not load main page: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # Try to find the main content area first; fall back to full page
    content = (
        soup.find("main")
        or soup.find("div", id=re.compile(r"content|main|body", re.I))
        or soup
    )

    skip_pattern = re.compile(
        r'^(contact|about|home|sitemap|privacy|disclaimer|faq|accessibility|'
        r'login|search|help|back|next|previous|print|share|top)$',
        re.I
    )

    departments = []
    seen_urls = set()

    for a in content.find_all("a", href=True):
        href = a.get("href", "").strip()
        text = a.get_text(strip=True)

        if not href or not text or len(text) < 3:
            continue
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        if skip_pattern.match(text):
            continue

        url = urljoin(MAIN_URL, href)
        parsed = urlparse(url)

        # Skip anchors back to the same page
        if url.split("#")[0] == MAIN_URL.rstrip("/") or url in seen_urls:
            continue

        # Only keep links that go somewhere meaningful (external or different NJ gov path)
        if parsed.scheme not in ("http", "https"):
            continue

        seen_urls.add(url)
        departments.append({"name": text, "url": url})

    return departments


def _extract_salary(text: str) -> str:
    match = SALARY_PATTERN.search(text)
    return match.group(0).strip() if match else ""


def _try_governmentjobs_api(url: str, dept_name: str) -> list[Job] | None:
    """If the URL is a governmentjobs.com page, use their JSON API."""
    if "governmentjobs.com" not in urlparse(url).netloc:
        return None

    match = re.search(r"/careers/([^/?#]+)", urlparse(url).path)
    if not match:
        return None

    agency = match.group(1)
    api_url = f"https://www.governmentjobs.com/careers/{agency}/jobs.json?pageSize=100"

    try:
        resp = requests.get(api_url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        jobs = []
        for item in data.get("value", []):
            title = item.get("JobTitle", "").strip()
            job_url = item.get("JobURL", url)
            salary = item.get("SalaryMin", "")
            salary_max = item.get("SalaryMax", "")
            salary_type = item.get("SalaryType", "")
            if salary and salary_max:
                salary_str = f"${float(salary):,.0f} - ${float(salary_max):,.0f}"
                if salary_type:
                    salary_str += f" / {salary_type}"
            elif salary:
                salary_str = f"${float(salary):,.0f}"
            else:
                salary_str = ""
            if title:
                jobs.append(Job(title=title, department=dept_name, salary=salary_str, url=job_url))
        return jobs
    except Exception:
        return None


def _extract_jobs_from_soup(soup: BeautifulSoup, base_url: str, dept_name: str) -> list[Job]:
    """Extract job listings from a static page using heuristics."""
    jobs = []
    seen = set()

    job_url_pattern = re.compile(
        r"/(job|jobs|career|careers|position|positions|vacancy|vacancies|posting|requisition|opening)",
        re.I,
    )
    title_keyword_pattern = re.compile(
        r"(analyst|specialist|coordinator|manager|director|officer|technician|engineer|"
        r"administrator|clerk|supervisor|associate|trainee|aide|assistant|auditor|"
        r"examiner|inspector|planner|developer|programmer|scientist|investigator|counselor)",
        re.I,
    )

    # Strategy 1: links that look like job postings
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        text = a.get_text(strip=True)

        if not text or len(text) < 5 or len(text) > 150:
            continue

        full_url = urljoin(base_url, href)

        if (job_url_pattern.search(href) or title_keyword_pattern.search(text)) and text not in seen:
            # Try to find salary near this element
            parent = a.find_parent(["li", "tr", "div", "p"])
            salary = _extract_salary(parent.get_text()) if parent else ""
            seen.add(text)
            jobs.append(Job(title=text, department=dept_name, salary=salary, url=full_url))

    # Strategy 2: tables with a title/position column
    for table in soup.find_all("table"):
        ths = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        if not any(h in ths for h in ["position", "title", "job title", "vacancy", "job"]):
            continue
        title_col = next(
            (i for i, h in enumerate(ths) if h in ["position", "title", "job title", "vacancy", "job"]),
            0,
        )
        for row in table.find_all("tr")[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) <= title_col:
                continue
            cell = cells[title_col]
            title = cell.get_text(strip=True)
            link = cell.find("a")
            job_url = urljoin(base_url, link.get("href", "")) if link else base_url
            salary = _extract_salary(row.get_text())
            if title and title not in seen and len(title) > 3:
                seen.add(title)
                jobs.append(Job(title=title, department=dept_name, salary=salary, url=job_url))

    return jobs


def _scrape_with_playwright(url: str, dept_name: str) -> tuple[list[Job], str]:
    """Fallback: render the page with a headless browser."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return [], "tier3"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=30000, wait_until="networkidle")
            html = page.content()
            browser.close()
        soup = BeautifulSoup(html, "html.parser")
        jobs = _extract_jobs_from_soup(soup, url, dept_name)
        return jobs, "tier2"
    except Exception as e:
        print(f" [playwright error: {e}]", end=" ")
        return [], "tier3"


def _fetch_static(url: str) -> requests.Response | None:
    """GET a URL, retrying without SSL verification if the cert check fails."""
    try:
        return requests.get(url, headers=HEADERS, timeout=15)
    except requests.exceptions.SSLError:
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            return requests.get(url, headers=HEADERS, timeout=15, verify=False)
        except Exception:
            return None
    except Exception:
        return None


def scrape_dept(url: str, dept_name: str) -> DeptResult:
    """Scrape a single department URL. Tries tier1 → tier2 → tier3 in order."""
    # Check for known APIs first
    api_jobs = _try_governmentjobs_api(url, dept_name)
    if api_jobs is not None:
        return DeptResult(name=dept_name, url=url, tier="tier1", jobs=api_jobs)

    # Try static HTTP (with SSL retry)
    resp = _fetch_static(url)

    if resp is None or resp.status_code not in range(200, 300):
        # HTTP failed entirely — give playwright a shot before declaring Tier 3
        print(" [HTTP failed, trying playwright]", end=" ", flush=True)
        jobs, tier = _scrape_with_playwright(url, dept_name)
        return DeptResult(name=dept_name, url=url, tier=tier, jobs=jobs)

    soup = BeautifulSoup(resp.text, "html.parser")
    page_text = soup.get_text(strip=True)

    # Very little text → page likely needs JavaScript
    if len(page_text) < 300:
        print(" [JS page, trying playwright]", end=" ", flush=True)
        jobs, tier = _scrape_with_playwright(url, dept_name)
        return DeptResult(name=dept_name, url=url, tier=tier, jobs=jobs)

    jobs = _extract_jobs_from_soup(soup, url, dept_name)
    return DeptResult(name=dept_name, url=url, tier="tier1", jobs=jobs)


# The NJ CSC directory page has stale links for some departments.
# These are the confirmed working replacements.
_URL_CORRECTIONS = {
    # Old URL pattern (substring)          : correct URL
    "mvc/About/employ":                      "https://www.nj.gov/mvc/about/employ.htm",
    "njcourts.gov/public/jobs":             "https://www.njcourts.gov/careers",
    "/sci/home/employment":                  "https://www.nj.gov/sci/employment/",
}


def _apply_url_corrections(url: str) -> str:
    for pattern, replacement in _URL_CORRECTIONS.items():
        if pattern in url:
            return replacement
    return url


def scrape_all() -> tuple[list[Job], list[DeptResult]]:
    """
    Scrape the main NJ CSC page and all linked department career sites.
    Returns (all_jobs, dept_results).
    """
    departments = get_departments()
    if not departments:
        print("[ERROR] No department links found on the main page.")
        return [], []

    print(f"[INFO] Found {len(departments)} department links.\n")

    all_jobs: list[Job] = []
    results: list[DeptResult] = []

    for i, dept in enumerate(departments, 1):
        name = dept["name"]
        url = _apply_url_corrections(dept["url"])
        print(f"[{i:>2}/{len(departments)}] {name[:55]:<55}", end=" ", flush=True)

        result = scrape_dept(url, name)

        tier_label = {"tier1": "OK", "tier2": "playwright", "tier3": "MANUAL CHECK"}[result.tier]
        print(f"→ {tier_label} ({len(result.jobs)} jobs)")

        all_jobs.extend(result.jobs)
        results.append(result)
        time.sleep(REQUEST_DELAY)

    return all_jobs, results
