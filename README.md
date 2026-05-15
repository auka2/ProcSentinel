# ProcSentinel v3 — Memory Forensics Platform

**Detection of Masqueraded Processes in Volatile Memory**

University of Hail · College of Computer Science and Engineering  
Supervised by: **Dr. Ehab Alnfrawy**

| Name | Student ID |
|---|---|
| Omar Khalid Ali | 202111316 |
| Abdulrahman Kasem Shoshara | 202111312 |
| Omar Abdullah Alharbi | 202101085 |
| Khalid Abdulaziz Alrashdan | 202206059 |
| Abdullah Nasser Alnazha | 202100025 |
| Khalid Abdullah Alshammari | 202104213 |

---

## Quick Start (Docker)

### 1. Place your memory dump in the `memory/` folder

```
# Windows
copy C:\Cases\suspect.raw memory\

# Linux / macOS
cp /cases/suspect.raw memory/
```

The file appears in the UI dropdown automatically. No paths to type.

### 2. Build and run

```bash
docker-compose up --build
```

First build takes ~3–5 minutes. Subsequent starts take ~10 seconds.

### 3. Open the browser

```
http://localhost:8501
```

**Username:** `admin`  
**Password:** `procsentinel`

---

## Docker Command Reference

```bash
# First run (builds image)
docker-compose up --build

# Start again after stopping
docker-compose up

# Run in background
docker-compose up -d

# View live logs
docker-compose logs -f

# Stop cleanly  ← ALWAYS use this instead of Ctrl+C alone
docker-compose down

# Full clean rebuild (when you update files)
docker-compose down && docker-compose up --build

# Remove old container if you get a "name already in use" error
docker-compose down
docker-compose up --build
```

> **Important:** Always stop with `docker-compose down`, not just `Ctrl+C`.  
> Ctrl+C stops the container but does not remove it — the next `up --build` will  
> fail with "container name already in use". `docker-compose down` removes it cleanly.

---

## Change Credentials

Edit `.env` (copy from `.env.example` first):

```bash
cp .env.example .env
```

```
PROCSENTINEL_USER=admin
PROCSENTINEL_PASS=your-new-password
```

Then restart:

```bash
docker-compose down && docker-compose up --build
```

---

## AbuseIPDB IP Enrichment (Optional)

Get a free API key at https://www.abuseipdb.com/api  
Add it to `.env`:

```
ABUSEIPDB_KEY=your-key-here
```

Or enter it per-analysis in the UI. Using `.env` is more secure because  
CLI arguments are visible in `ps aux`.

---

## Without Docker (Local Python)

```bash
pip install -r requirements.txt
# Volatility 3 must also be installed and on PATH
pip install volatility3

streamlit run app.py
```

Place dumps in `memory/` next to `app.py`.

---

## What ProcSentinel Detects

| Rule | Description | MITRE |
|---|---|---|
| masquerade_wrong_path | System process running from wrong directory | T1036.005 |
| masquerade_typosquat | Misspelled system process name (svch0st.exe) | T1036.003 |
| masquerade_svchost_no_k | svchost.exe without mandatory -k argument | T1036.005 |
| masquerade_boot_chain | Boot process with wrong parent (PPID spoofing) | T1134.004 |
| unusual_parent_child | lsass.exe with wrong parent | T1055 |
| masquerade_explorer | explorer.exe from wrong path | T1036.005 |
| masquerade_unicode_padding | Invisible Unicode characters in process name | T1036.008 |
| verinfo_mismatch | System binary with missing version metadata | T1036.001 |
| shell_spawned_by_office | Shell spawned by Office or browser | T1566.001 |
| psxview_hidden | Process hidden via DKOM rootkit technique | T1014 |
| malfind_injection | Injected executable code in process memory | T1055 |
| ldr_unlinked_module | Hidden DLL not in PEB module list | T1055.001 |
| exec_from_tmp | Process running from Temp/AppData | T1059 |
| handles_lsass_access | Credential dumping handle to lsass.exe | T1003.001 |
| services_suspicious | Malicious service from writable path | T1543.003 |
| correlation_masq_and_hidden | Masquerade + hidden process combined | T1036+T1014 |

---

## v3 Changes

- All `[DEBUG]` output removed — clean logs only
- Login validates against real credentials (env vars), with 5-attempt lockout
- API key read from `ABUSEIPDB_KEY` env var — no longer exposed in process list
- Artifact downloads stream via `st.download_button` — no OOM on large files
- Boot chain detector no longer flags winlogon/csrss as suspicious when smss.exe has exited (normal Windows behaviour)
- Windows Defender DLLs no longer flagged as hidden injection (false positive)
- MITRE technique badges are clickable links to attack.mitre.org
- Unicode normalization in typosquat engine blocks Cyrillic lookalike attacks
# ProcSentinel
