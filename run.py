from scraper import scrape_all
from output import print_results, save_results


def main():
    print("NJ Government Job Scraper — Starting...\n")

    jobs, dept_results = scrape_all()

    print_results(jobs, dept_results)

    if jobs:
        filepath = save_results(jobs, dept_results)
        print(f"[INFO] Results saved to: {filepath}")
    else:
        print("[WARN] No jobs found — nothing saved.")


if __name__ == "__main__":
    main()
