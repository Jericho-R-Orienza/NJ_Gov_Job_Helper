import os
from datetime import datetime
from scraper import Job, DeptResult

RESULTS_DIR = "results"


def _format_job(i: int, job: Job) -> list[str]:
    salary_str = f"  Salary:     {job.salary}" if job.salary else "  Salary:     Not listed"
    return [
        f"  {i}. {job.title}",
        f"     Department: {job.department}",
        salary_str,
        f"     Link:       {job.url}",
    ]


def print_results(jobs: list[Job], dept_results: list[DeptResult]) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print("\n" + "=" * 65)
    print(f"  NJ GOVERNMENT JOB LISTINGS — {now}")
    print("=" * 65)

    if not jobs:
        print("\n  No job listings found.")
    else:
        # Group by department
        by_dept: dict[str, list[Job]] = {}
        for job in jobs:
            by_dept.setdefault(job.department, []).append(job)

        print(f"\n  Total jobs found: {len(jobs)} across {len(by_dept)} department(s)\n")

        for dept_name, dept_jobs in by_dept.items():
            print(f"  --- {dept_name} ({len(dept_jobs)} job(s)) ---")
            for i, job in enumerate(dept_jobs, 1):
                for line in _format_job(i, job):
                    print(line)
            print()

    # Manual check list
    manual = [d for d in dept_results if d.tier == "tier3"]
    if manual:
        print("-" * 65)
        print("  MANUAL CHECK REQUIRED (could not be scraped automatically):")
        for d in manual:
            print(f"    • {d.name}")
            print(f"      {d.url}")
        print()


def save_results(jobs: list[Job], dept_results: list[DeptResult]) -> str:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filepath = os.path.join(RESULTS_DIR, f"results_{timestamp}.txt")

    lines = [
        f"NJ GOVERNMENT JOB LISTINGS — {timestamp}",
        "=" * 65,
        f"Total jobs: {len(jobs)}",
        "",
    ]

    by_dept: dict[str, list[Job]] = {}
    for job in jobs:
        by_dept.setdefault(job.department, []).append(job)

    for dept_name, dept_jobs in by_dept.items():
        lines.append(f"--- {dept_name} ({len(dept_jobs)} job(s)) ---")
        for i, job in enumerate(dept_jobs, 1):
            lines.extend(_format_job(i, job))
        lines.append("")

    manual = [d for d in dept_results if d.tier == "tier3"]
    if manual:
        lines.append("-" * 65)
        lines.append("MANUAL CHECK REQUIRED:")
        for d in manual:
            lines.append(f"  • {d.name}: {d.url}")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filepath
