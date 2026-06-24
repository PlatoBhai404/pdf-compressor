# PDF Compressor

Two ways to run — pick one or use both.

---

## Prerequisites

### 1. Python 3.8+
Download from https://www.python.org/downloads/

### 2. Ghostscript (required for actual compression)
Download from https://www.ghostscript.com/releases/gsdnld.html
- Windows: install the `.exe`, make sure to tick "Add to PATH"
- macOS: `brew install ghostscript`
- Linux: `sudo apt install ghostscript`

### 3. Install Python dependencies
Open a terminal in this folder and run:
```
pip install -r requirements.txt
```

---

## Option A — Desktop App (GUI window)

```
python desktop_app.py
```

A native window opens. Browse for a PDF, pick a compression level, click Compress.

---

## Option B — Web App (browser UI)

```
python server.py
```

Then open **http://localhost:5000** in your browser.
Same experience as the Claude artifact, but with real Ghostscript compression.

---

## Compression levels explained

| Level    | DPI  | Best for                        |
|----------|------|---------------------------------|
| Max      | ~72  | Email, sharing, web uploads     |
| Balanced | ~150 | General use, good quality       |
| Quality  | ~300 | Print-ready documents           |
| Lossless | ~600 | Archiving, near-zero quality loss |

---

## Troubleshooting

**"Ghostscript not found"**
- Windows: reinstall Ghostscript and tick "Add to PATH", then restart your terminal
- macOS/Linux: run `which gs` to confirm it's installed

**Port 5000 already in use (web app)**
Edit `server.py`, last line: change `port=5000` to `port=5001` and open http://localhost:5001
