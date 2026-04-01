# WiFi Security Scanner

A Windows-based WiFi security scanner that detects and classifies rogue access points in your surrounding network environment. Built with Python and Tkinter, it scans all visible networks, analyzes them across four security dimensions, and identifies the specific type of rogue network with a confidence percentage.

## How It Works

The scanner uses Windows' built-in `netsh` command to pull a full list of visible networks including signal strength, encryption type, authentication method, MAC addresses, and channel information. Each network is then run through four security checks and a rogue type classifier that scores the network against known attack patterns.

## Rogue Network Types Detected

| Type | Description |
|------|-------------|
| Evil Twin | A fake copy of a legitimate network designed to intercept traffic |
| Honeypot | An open or attractive network set up to lure victims |
| Pineapple | A professional WiFi hacking device that mimics legitimate networks |
| Karma Attack | A network that responds to any connection probe from nearby devices |
| Ad-hoc Rogue | A peer-to-peer network masquerading as an access point |
| Soft AP | A software-created hotspot with suspicious characteristics |
| MAC Spoofing | A network using a falsified or randomized MAC address |

## Security Checks

| Check | What it looks for |
|-------|-------------------|
| Duplicate SSID | Multiple routers broadcasting the same network name (evil twin indicator) |
| Signal Anomaly | Unusually strong signal that could indicate a rogue AP is physically very close |
| Encryption | Open networks or weak WEP encryption |
| MAC Pattern | Spoofed, impossible, or randomized MAC addresses |

## Safety Scoring

Each network starts with a score of 100 and loses points for each issue found. The final score maps to one of three levels:

- **SAFE** (70 to 100) — no significant issues detected
- **CAUTION** (30 to 70) — one or more mild issues present
- **UNSAFE** (0 to 30) — multiple serious issues detected

## Requirements

- Windows 10 or later
- Python 3.8 or later
- WiFi adapter enabled

## Installation

```bash
pip install tkinter
```

Tkinter is included with most Python installations. No other external libraries are needed.

## Running the Scanner

```bash
python wifi_security_scanner.py
```

For best results, right-click and choose **Run as Administrator**. This gives the scanner access to all visible networks rather than just the ones your adapter has recently seen.

## Using the Scanner

1. Click **Scan ALL Networks** to start a scan (takes 5 to 10 seconds)
2. Results appear in the table with safety score, rogue type, and per-feature breakdown
3. Double-click any row to open a detailed popup with full analysis and recommendations
4. Networks you have previously connected to are marked with **[saved]**

## How Confidence Scores Work

The rogue type detector scores each network against the known indicators for each attack type. A confidence of 80% or above means multiple strong indicators were found. Between 60% and 80% means partial evidence. Below 60% means the classification is tentative.

| Label | Confidence |
|-------|-----------|
| [HIGH] | 80% or above |
| [WARN] | 60 to 79% |
| [?] | Below 60% |

## Troubleshooting

**No networks found**
- Make sure WiFi is turned on
- Run the script as Administrator
- Verify that `netsh wlan show networks` works in Command Prompt

**Fewer networks than expected**
- Run as Administrator — standard user mode limits which networks are visible
- Move closer to the area you are scanning

**Program only works on Windows**
- The scanner relies on `netsh`, which is a Windows-only command. It will not run on macOS or Linux.

## Tech Stack
Python, Tkinter, netsh (Windows CLI), Threading, Regular Expressions
