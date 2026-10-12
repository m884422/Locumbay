import os
import sys
import re
import json
import urllib.parse
import datetime
import requests
from bs4 import BeautifulSoup

LOGIN_URL = "https://locumbay.com/guest/access/signIn"
SHIFTS_URL = "https://locumbay.com/guest/shifts/getShifts"
VACANCIES_URL = "https://locumbay.com/guest/vacancies/searchVacancies"
SHIFT_DETAILS_URL = "https://locumbay.com/guest/booked-jobs/modalShiftDetails"
CACHE_FILE = "pharmacies_cache.json"

def clean_address(addr):
    if not addr:
        return ""
    addr = re.sub(r',\s*,', ',', addr)
    addr = re.sub(r'\s+', ' ', addr).strip(', ')
    parts = [p.strip() for p in addr.split(',')]
    deduped = []
    for p in parts:
        if not deduped or p.lower() != deduped[-1].lower():
            deduped.append(p)
    return ', '.join(deduped)

def load_pharmacies_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Warning reading cache: {e}")
    return {}

def save_pharmacies_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"[!] Warning saving cache: {e}")

def fetch_data(email, password):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest"
    })

    print("[*] Contacting LocumBay...")
    session.get("https://locumbay.com/")

    print("[*] Authenticating with LocumBay...")
    res = session.post(LOGIN_URL, data={"email": email, "password": password})
    try:
        data = res.json()
    except Exception as e:
        print("[!] Error decoding login response.")
        sys.exit(1)

    if data.get("status") != "success":
        print("[!] Login failed. Please check credentials in Secrets.")
        sys.exit(1)

    print("[+] Successfully authenticated!")

    # Load cache
    pharmacy_cache = load_pharmacies_cache()

    # Discover pharmacies from open vacancies
    try:
        print("[*] Fetching pharmacy directory from vacancies...")
        v_res = session.get(VACANCIES_URL).json()
        for v in v_res.get("data", []):
            pname = v.get("pharmacyName", "").strip()
            if pname:
                addr = v.get("address", "").strip()
                city = v.get("city", "").strip()
                postcode = v.get("postcode", "").strip()
                full_addr = clean_address(", ".join(p for p in [addr, city, postcode] if p))
                lat = v.get("latitude")
                lon = v.get("longitude")
                if pname not in pharmacy_cache or not pharmacy_cache[pname].get("lat"):
                    pharmacy_cache[pname] = {
                        "address": full_addr,
                        "postcode": postcode,
                        "lat": lat,
                        "lon": lon
                    }
    except Exception as e:
        print(f"[!] Note: Could not scan vacancies directory: {e}")

    print("[*] Fetching shifts from Shift Management Dashboard...")
    shifts_res = session.post(SHIFTS_URL, data={})
    try:
        shifts_data = shifts_res.json().get("payload", [])
    except Exception as e:
        print(f"[!] Error decoding shifts response: {e}")
        sys.exit(1)

    print(f"[+] Retrieved {len(shifts_data)} shift records.")

    # Check for any shifts with missing address in cache
    missing_lookup = {}
    for s in shifts_data:
        pname = s.get("pharmacyName", "").strip()
        if pname and (pname not in pharmacy_cache or not pharmacy_cache[pname].get("address")):
            if pname not in missing_lookup:
                missing_lookup[pname] = s.get("id")

    if missing_lookup:
        print(f"[*] Fetching address details for {len(missing_lookup)} new pharmacies...")
        for pname, vid in missing_lookup.items():
            try:
                dt_res = session.post(SHIFT_DETAILS_URL, data={"vacancy_id": vid})
                soup = BeautifulSoup(dt_res.text, "html.parser")
                cdiv = soup.find("div", id="booking_request_content")
                if cdiv:
                    lat = cdiv.get("data-lat")
                    lon = cdiv.get("data-lon")
                    p_tag = cdiv.find("p")
                    lines = [l.strip() for l in p_tag.stripped_strings] if p_tag else []
                    addr_line = clean_address(lines[1]) if len(lines) > 1 else ""
                    pharmacy_cache[pname] = {
                        "address": addr_line,
                        "lat": lat,
                        "lon": lon
                    }
            except Exception as e:
                print(f"[!] Could not get details for {pname}: {e}")

        save_pharmacies_cache(pharmacy_cache)

    return shifts_data, pharmacy_cache

def create_ics(shifts, pharmacy_cache, output_path, base_url=""):
    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//LocumBay Shift Sync//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Locum Shifts",
        "X-WR-TIMEZONE:Europe/London",
        "BEGIN:VTIMEZONE",
        "TZID:Europe/London",
        "BEGIN:STANDARD",
        "DTSTART:19710101T020000",
        "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU",
        "TZOFFSETFROM:+0100",
        "TZOFFSETTO:+0000",
        "TZNAME:GMT",
        "END:STANDARD",
        "BEGIN:DAYLIGHT",
        "DTSTART:19710101T010000",
        "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU",
        "TZOFFSETFROM:+0000",
        "TZOFFSETTO:+0100",
        "TZNAME:BST",
        "END:DAYLIGHT",
        "END:VTIMEZONE"
    ]

    for s in shifts:
        shift_id = s.get("id")
        date_str = s.get("date")  # YYYY-MM-DD
        time_from = s.get("timeFrom", "08:00:00")
        time_to = s.get("timeTo", "18:00:00")
        pharmacy = s.get("pharmacyName", "Locum Pharmacy").strip()
        company = s.get("companyName", "").strip()
        status_info = s.get("status_badge", {})
        status_text = status_info.get("text", "Confirmed") if isinstance(status_info, dict) else str(s.get("status", "Confirmed"))
        total_pay = s.get("total_pay", s.get("pay", "0.00"))
        length = s.get("length", "")
        lunch_break = s.get("break", "")
        lunch_start = s.get("lunchStart", "")
        lunch_end = s.get("lunchEnd", "")

        # Lookup address & coordinates
        p_info = pharmacy_cache.get(pharmacy, {})
        address = p_info.get("address", "")
        lat = p_info.get("lat")
        lon = p_info.get("lon")

        # Location string for calendar
        full_location = f"{pharmacy}, {address}" if address else pharmacy

        dt_start = date_str.replace("-", "") + "T" + time_from.replace(":", "")
        dt_end = date_str.replace("-", "") + "T" + time_to.replace(":", "")

        # Navigation URLs
        encoded_query = urllib.parse.quote(f"{pharmacy}, {address}" if address else pharmacy)
        has_coords = bool(lat and lon)

        apple_maps_url = f"https://maps.apple.com/?daddr={lat},{lon}&q={encoded_query}" if has_coords else f"https://maps.apple.com/?q={encoded_query}"
        google_maps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}" if has_coords else f"https://www.google.com/maps/search/?api=1&query={encoded_query}"
        waze_url = f"https://waze.com/ul?ll={lat},{lon}&navigate=yes" if has_coords else f"https://waze.com/ul?q={encoded_query}&navigate=yes"

        # Web navigation picker URL (hosted on GitHub Pages)
        nav_picker_query = urllib.parse.urlencode({
            "name": pharmacy,
            "addr": address,
            "lat": lat or "",
            "lon": lon or ""
        })
        nav_picker_url = f"{base_url.rstrip('/')}/nav.html?{nav_picker_query}" if base_url else ""

        # Build clean Description / Notes
        desc_items = [
            f"🏥 {pharmacy}",
            f"📍 Address: {address}" if address else "",
            "",
            "🧭 Open in Navigation App:"
        ]
        if nav_picker_url:
            desc_items.append(f"👉 Choose App: {nav_picker_url}")
        desc_items.extend([
            f"• Apple Maps: {apple_maps_url}",
            f"• Google Maps: {google_maps_url}",
            f"• Waze: {waze_url}",
            "",
            "📋 Shift Info:",
            f"• Duration: {length}" if length else "",
            f"• Lunch Break: {lunch_break} ({lunch_start[:5]} - {lunch_end[:5]})" if lunch_break and lunch_start else f"• Lunch Break: {lunch_break}" if lunch_break else "",
            f"• Total Pay: £{total_pay}",
            f"• Status: {status_text}",
            f"• Shift ID: {shift_id}",
            f"• Company: {company}" if company else ""
        ])

        description = "\\n".join(item for item in desc_items if item != "")

        event_lines = [
            "BEGIN:VEVENT",
            f"UID:shift-{shift_id}@locumbay.com",
            f"DTSTAMP:{now_utc}",
            f"DTSTART;TZID=Europe/London:{dt_start}",
            f"DTEND;TZID=Europe/London:{dt_end}",
            f"SUMMARY:Shift: {pharmacy}",
            f"LOCATION:{full_location}"
        ]

        if has_coords:
            try:
                event_lines.append(f"GEO:{float(lat):.6f};{float(lon):.6f}")
            except Exception:
                pass

        event_lines.extend([
            f"DESCRIPTION:{description}",
            "STATUS:CONFIRMED",
            "END:VEVENT"
        ])

        lines.extend(event_lines)

    lines.append("END:VCALENDAR")
    lines.append("")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\r\n".join(lines))
    print(f"[+] Calendar file written successfully: {output_path}")

def main():
    email = os.getenv("LOCUMBAY_EMAIL")
    password = os.getenv("LOCUMBAY_PASSWORD")
    feed_key = os.getenv("SECRET_FEED_KEY", "")
    
    # Base URL for GitHub Pages picker
    repo = os.getenv("GITHUB_REPOSITORY", "") # e.g. username/locumbay-calendar
    if repo:
        owner, repo_name = repo.split("/", 1)
        base_url = f"https://{owner}.github.io/{repo_name}"
    else:
        base_url = os.getenv("PAGES_BASE_URL", "")

    if not email or not password:
        print("[!] Missing required environment variables LOCUMBAY_EMAIL and/or LOCUMBAY_PASSWORD.")
        print("[*] Usage: set LOCUMBAY_EMAIL and LOCUMBAY_PASSWORD.")
        sys.exit(1)

    filename = f"shifts_{feed_key}.ics" if feed_key else "shifts.ics"
    output_path = os.path.join("public", filename)

    shifts, pharmacy_cache = fetch_data(email, password)
    create_ics(shifts, pharmacy_cache, output_path, base_url=base_url)
    print(f"[+] Completed! Feed is ready at public/{filename}")

if __name__ == "__main__":
    main()
