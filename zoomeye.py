#!/usr/bin/env python3
import json
import time
import base64
import requests
from pathlib import Path
from urllib.parse import quote

COOKIES_FILE = "cookies.json"
QUERY = 'port="554" && city="Uhhhh uhhmmmm uhmmm" && after="2026-01-01" && before="2027-01-01"'
OUTPUT_FILE = "ips.txt"
TARGET_IPS = 250
PAGE_SIZE = 10

API_URL = "https://www.zoomeye.ai/api/search"

def load_cookies(cookies_file):
    with open(cookies_file, "r") as f:
        cookies_list = json.load(f)
    return {c["name"]: c["value"] for c in cookies_list if "name" in c}

def build_url(query, page, page_size):
    # Base64 encode the query exactly as the browser does
    b64 = base64.b64encode(query.encode()).decode()
    # URL encode it
    b64_encoded = quote(b64, safe="")
    return f"{API_URL}?q={b64_encoded}&page={page}&pageSize={page_size}&t=v4%2Bv6%2Bweb"

def scrape_ips():
    cookies = load_cookies(COOKIES_FILE)

    session = requests.Session()

    # Set cookies on www.zoomeye.ai — that's where the real API lives
    for name, value in cookies.items():
        session.cookies.set(name, value, domain="www.zoomeye.ai")

    session.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "https://www.zoomeye.ai/",
        "sec-ch-ua": '"Brave";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Linux"',
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
	"X-Csrftoken": cookies.get("ssoCsrfToken", ""),
        "Cube-Authorization": cookies.get("token", ""),  # seen in Access-Control-Allow-Headers
    })

    all_ips = []
    page = 1

    print(f"[→] Searching for: {QUERY}")
    print(f"[→] Target: {TARGET_IPS} IPs\n")

    while len(all_ips) < TARGET_IPS:
        url = build_url(QUERY, page, PAGE_SIZE)
        print(f"[→] Fetching page {page}...")
        print(f"    URL: {url}")

        try:
            r = session.get(url, timeout=15)
            print(f"    Status: {r.status_code}")

            if r.status_code == 401:
                print("[✗] 401 — cookies expired, re-export them.")
                break
            if r.status_code == 403:
                print("[✗] 403 — forbidden.")
                break
            if r.status_code != 200:
                print(f"    Response: {r.text[:300]}")
                break

            data = r.json()
            print(f"    Keys: {list(data.keys())}")

            # Try common result key names
            results = data.get("matches", data.get("data", data.get("results", [])))
            print(f"    Total results: {data.get('total')}")
            print(f"    Max: {data.get('max')}")

            if not results:
                print(f"[i] No results. Full response: {json.dumps(data)[:400]}")
                break

            page_ips = []
            for item in results:
                ip = item.get("ip")
                port = item.get("portinfo", {}).get("port") or item.get("port")
                if ip and port:
                    page_ips.append(f"{ip}:{port}")
                elif ip:
                    page_ips.append(ip)

            all_ips.extend(page_ips)
            print(f"[✓] Page {page}: +{len(page_ips)} IPs (Total: {len(all_ips)})")

            if len(page_ips) < PAGE_SIZE:
                print("[i] Last page reached.")
                break

            page += 1
            time.sleep(5)

        except Exception as e:
            print(f"[✗] Error: {e}")
            break

    return all_ips[:TARGET_IPS]

def main():
    print("=" * 50)
    print("ZoomEye IP Scraper (Cookie-based)")
    print("=" * 50)

    if not Path(COOKIES_FILE).exists():
        print(f"[✗] '{COOKIES_FILE}' not found.")
        return

    ip_list = scrape_ips()

    if ip_list:
        with open(OUTPUT_FILE, "w") as f:
            f.write("\n".join(ip_list))
        print(f"\n[✓] Saved {len(ip_list)} IPs to '{OUTPUT_FILE}'")
    else:
        print("[✗] No IPs found.")

if __name__ == "__main__":
    main()
