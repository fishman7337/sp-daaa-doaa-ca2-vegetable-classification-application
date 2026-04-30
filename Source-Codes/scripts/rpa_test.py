"""Optional Selenium RPA smoke test.

Usage:
  python scripts/rpa_test.py --base-url http://localhost:3000 --username admin --password admin123
"""

import argparse
import time

from selenium import webdriver
from selenium.webdriver.common.by import By


def main() -> None:
    """Execute main."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    driver = webdriver.Chrome()
    driver.get(args.base_url)

    driver.find_element(By.NAME, "username").send_keys(args.username)
    driver.find_element(By.NAME, "password").send_keys(args.password)
    driver.find_element(By.TAG_NAME, "button").click()

    time.sleep(2)
    driver.quit()


if __name__ == "__main__":
    main()
