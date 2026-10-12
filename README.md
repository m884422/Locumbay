# LocumBay Automated Calendar Subscription Feed with Navigation

This automated system synchronizes your shifts from **LocumBay** into an **iCalendar (.ics)** subscription feed hosted via **GitHub Actions** and **GitHub Pages**.

Whenever you book or complete shifts on LocumBay, this feed automatically updates on a schedule and synchronizes directly to your iPhone Calendar, Google Calendar, or Outlook.

---

## 🚗 Navigation & Address Features

Each calendar event includes:
- **Full Street Address & Postcode**: Automatically extracted for every pharmacy branch.
- **Native Map Card (`GEO` coordinates)**: In Apple Calendar, tapping the map pin/location automatically shows travel time and prompts directions.
- **Navigation App Chooser (`nav.html`)**: Clicking the **"👉 Choose App"** link in the event notes opens a clean mobile page with 1-tap buttons for:
  - 🍎 **Apple Maps**
  - 🗺️ **Google Maps**
  - 🚙 **Waze**
- **Direct Navigation Links**: Individual links in the notes let you jump straight into your preferred navigation app in a single tap.

---

## 🛠️ How It Works

```
┌─────────────────┐       ┌──────────────────────┐       ┌────────────────────────┐       ┌─────────────────────────┐
│ LocumBay Portal │ ────> │ GitHub Actions (Cron)│ ────> │ GitHub Pages (.ics)    │ ────> │ Apple / Google Calendar │
│ (Auth & Shifts) │       │ Runs every 3 hours   │       │ https://.../shifts.ics │       │ Auto-subscribes & syncs │
└─────────────────┘       └──────────────────────┘       └────────────────────────┘       └─────────────────────────┘
```

1. **GitHub Actions** wakes up automatically on a schedule (every 5 minutes, or whenever manually triggered).
2. It securely authenticates to your LocumBay account using encrypted **GitHub Secrets**.
3. It fetches your shift management dashboard, resolves full branch addresses and GPS coordinates, and converts all shifts into the standard RFC 5545 iCalendar (`.ics`) format.
4. It publishes the updated calendar and the navigation helper to **GitHub Pages**.
5. Your subscribed calendar on iPhone or Google Calendar refreshes automatically!

---

## 🚀 Setup Instructions

### 1. Create a GitHub Repository
1. Log in to [GitHub](https://github.com/) and create a new repository (e.g. `locumbay-calendar`).
2. Add these files to your repository:
   - `sync_shifts.py`
   - `pharmacies_cache.json`
   - `public/nav.html`
   - `.github/workflows/sync.yml`

### 2. Configure Your Secure Credentials (GitHub Secrets)
Your LocumBay password will **never** be visible in your code or to anyone browsing GitHub.
1. In your GitHub repository, go to **Settings** > **Secrets and variables** > **Actions**.
2. Click **New repository secret** and add:
   - `LOCUMBAY_EMAIL`: Your LocumBay email address (e.g., `your_email@example.com`)
   - `LOCUMBAY_PASSWORD`: Your updated LocumBay password.
   - `SECRET_FEED_KEY` *(Optional)*: A random string (e.g., `a8b2c4`) if you want the calendar file name to be unguessable (`shifts_a8b2c4.ics`).

### 3. Enable GitHub Pages
1. In your repository, go to **Settings** > **Pages**.
2. Under **Build and deployment** > **Source**, select **GitHub Actions**.

### 4. Run the Initial Sync
1. Go to the **Actions** tab in your repository.
2. Select **Sync LocumBay Shifts to Calendar** in the left sidebar.
3. Click **Run workflow** > **Run workflow**.
4. Once completed (green checkmark), your calendar feed URL will be:
   ```text
   https://<YOUR-GITHUB-USERNAME>.github.io/<REPO-NAME>/shifts.ics
   ```

---

## 📱 How to Subscribe on Your iPhone (Apple Calendar)

1. On your iPhone, open **Settings**.
2. Tap **Calendar** > **Accounts** > **Add Account**.
3. Select **Other**, then tap **Add Subscribed Calendar**.
4. In the **Server** field, paste your GitHub Pages feed URL (you can replace `https://` with `webcal://`):
   ```text
   webcal://<YOUR-GITHUB-USERNAME>.github.io/<REPO-NAME>/shifts.ics
   ```
5. Tap **Next**.
6. Set:
   - **Description**: `Locum Shifts`
   - **Auto-Refresh**: `Every 15 Minutes` or `Hourly`
7. Tap **Save**.

---

## 📅 Example Event on Your Calendar

```text
Title:    Shift: Allied Pharmacy - Green Lane
Location: Allied Pharmacy - Green Lane, 17 Green Lane, Tuebrook, Liverpool, L13 7DT
Time:     08:00 - 19:00

Notes:
🏥 Allied Pharmacy - Green Lane
📍 Address: 17 Green Lane, Tuebrook, Liverpool, L13 7DT

🧭 Open in Navigation App:
👉 Choose App: https://.../nav.html?name=...&addr=...&lat=53.423856&lon=-2.928054
• Apple Maps: https://maps.apple.com/?daddr=53.423856,-2.928054...
• Google Maps: https://www.google.com/maps/dir/?api=1&destination=53.423856,-2.928054
• Waze: https://waze.com/ul?ll=53.423856,-2.928054&navigate=yes

📋 Shift Info:
• Duration: 11 Hours
• Lunch Break: 30min paid (13:00 - 13:30)
• Total Pay: £353.04
• Status: Payment Completed
• Shift ID: 103926
• Company: Sharief Healthcare Limited
```
