"""
PDF Compressor - Flask Backend Server
Run: python server.py
Then open: http://localhost:5000
Requires: pip install flask flask-cors
Requires: Ghostscript installed (https://www.ghostscript.com/releases/gsdnld.html)
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

LEVELS = {"screen", "ebook", "printer", "prepress"}

def find_ghostscript():
    for c in ["gs", "gswin64c", "gswin32c"]:
        if shutil.which(c):
            return c
    for path in [
        r"C:\Program Files\gs\gs10.03.1\bin\gswin64c.exe",
        r"C:\Program Files\gs\gs10.02.1\bin\gswin64c.exe",
        r"C:\Program Files (x86)\gs\gs9.56.1\bin\gswin32c.exe",
    ]:
        if os.path.exists(path):
            return path
    return None


HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PDF Compressor</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f7; color: #1d1d1f; min-height: 100vh; display: flex; align-items: flex-start; justify-content: center; padding: 1rem; overflow-y: auto; }
  .card { background: #fff; border-radius: 16px; padding: 2rem; max-width: 500px; width: 100%; box-shadow: 0 2px 24px rgba(0,0,0,0.08); margin-top: 1rem; margin-bottom: 1rem; }
  h1 { font-size: 22px; font-weight: 600; margin-bottom: 4px; }
  .sub { font-size: 13px; color: #888; margin-bottom: 1.5rem; }
  .drop-zone { border: 1.5px dashed #ccc; border-radius: 12px; background: #fafafa; padding: 2rem 1.5rem; text-align: center; cursor: pointer; transition: border-color .15s, background .15s; margin-bottom: 1.25rem; }
  .drop-zone.over { border-color: #0071e3; background: #f0f6ff; }
  .drop-zone .icon { font-size: 32px; margin-bottom: 8px; }
  .drop-zone p { font-size: 14px; color: #555; }
  .drop-zone span { color: #0071e3; }
  #file-input { display: none; }
  .chip { display: flex; align-items: center; gap: 10px; background: #f5f5f7; border-radius: 10px; padding: 10px 14px; margin-bottom: 1.25rem; }
  .chip .info { flex: 1; min-width: 0; }
  .chip .name { font-size: 13px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .chip .size { font-size: 12px; color: #888; }
  .chip .remove { background: none; border: none; cursor: pointer; font-size: 18px; color: #aaa; padding: 0; line-height: 1; }
  .chip .remove:hover { color: #333; }
  label.section { display: block; font-size: 14px; font-weight: 600; margin-bottom: 10px; }
  .levels { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 1.5rem; }
  .level-btn { border: 1.5px solid #ddd; border-radius: 10px; background: #fff; padding: 10px 8px; cursor: pointer; text-align: center; transition: border-color .12s, background .12s; }
  .level-btn:hover { background: #f5f5f7; }
  .level-btn.active { border-color: #0071e3; background: #f0f6ff; }
  .level-btn .name { font-size: 13px; font-weight: 500; }
  .level-btn .dpi { font-size: 11px; color: #888; margin-top: 2px; }
  .compress-btn { width: 100%; padding: 14px; background: #0071e3; color: #fff; border: none; border-radius: 10px; font-size: 15px; font-weight: 500; cursor: pointer; transition: opacity .12s; margin-bottom: 1rem; }
  .compress-btn:hover { opacity: .88; }
  .compress-btn:disabled { opacity: .4; cursor: not-allowed; }
  .progress-wrap { margin-bottom: 1.25rem; display: none; }
  .progress-info { display: flex; justify-content: space-between; font-size: 13px; font-weight: 500; color: #333; margin-bottom: 6px; }
  .progress-track { height: 6px; background: #eee; border-radius: 3px; overflow: hidden; }
  .progress-fill { height: 100%; background: #0071e3; border-radius: 3px; width: 0%; transition: width .3s; }
  .stats { display: none; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 1.25rem; }
  .stat { background: #f5f5f7; border-radius: 10px; padding: 12px; text-align: center; border: 1.5px solid #eee; }
  .stat .label { font-size: 11px; color: #888; margin-bottom: 4px; }
  .stat .value { font-size: 15px; font-weight: 600; }
  .download-btn { display: none; width: 100%; padding: 14px; background: #1a9e75; color: #fff; border: none; border-radius: 10px; font-size: 15px; font-weight: 600; cursor: pointer; text-align: center; text-decoration: none; transition: opacity .12s; margin-bottom: 0.5rem; }
  .download-btn:hover { opacity: 0.9; }
  .footer { font-size: 12px; color: #bbb; text-align: center; margin-top: 1.5rem; }
  .savings { color: #1a9e75; }
</style>
</head>
<body>
<div class="card">
  <h1>PDF Compressor</h1>
  <p class="sub">Real compression via Ghostscript — running locally on your machine</p>

  <div class="drop-zone" id="drop-zone">
    <div class="icon">📄</div>
    <p>Drop your PDF here or <span id="browse-link">browse to upload</span></p>
    <input type="file" id="file-input" accept="application/pdf">
  </div>

  <div class="chip" id="file-chip" style="display:none;">
    <span style="font-size:20px;">📄</span>
    <div class="info">
      <div class="name" id="chip-name"></div>
      <div class="size" id="chip-size"></div>
    </div>
    <button class="remove" id="remove-btn">×</button>
  </div>

  <label class="section">Compression level</label>
  <div class="levels">
    <button class="level-btn active" data-level="screen">
      <div class="name">⚡ Max</div>
      <div class="dpi">~72 DPI · smallest file</div>
    </button>
    <button class="level-btn" data-level="ebook">
      <div class="name">⚖️ Balanced</div>
      <div class="dpi">~150 DPI · good quality</div>
    </button>
    <button class="level-btn" data-level="printer">
      <div class="name">🖼 Quality</div>
      <div class="dpi">~300 DPI · print ready</div>
    </button>
    <button class="level-btn" data-level="prepress">
      <div class="name">🏆 Lossless</div>
      <div class="dpi">~600 DPI · minimal loss</div>
    </button>
  </div>

  <div class="progress-wrap" id="progress-wrap">
    <div class="progress-info">
      <span id="status-msg">Compressing…</span>
      <span id="progress-pct">0%</span>
    </div>
    <div class="progress-track">
      <div class="progress-fill" id="progress-fill"></div>
    </div>
  </div>

  <button class="compress-btn" id="compress-btn" disabled>Compress PDF</button>

  <div class="stats" id="stats">
    <div class="stat"><div class="label">Original</div><div class="value" id="stat-orig">—</div></div>
    <div class="stat"><div class="label">Compressed</div><div class="value" id="stat-comp">—</div></div>
    <div class="stat"><div class="label">Saved</div><div class="value savings" id="stat-save">—</div></div>
  </div>

  <a class="download-btn" id="download-btn" href="#">⬇ Download compressed PDF</a>

  <p class="footer">🔒 Files processed locally — never uploaded to the internet</p>
</div>

<script>
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const browseLink = document.getElementById('browse-link');
const fileChip = document.getElementById('file-chip');
const chipName = document.getElementById('chip-name');
const chipSize = document.getElementById('chip-size');
const removeBtn = document.getElementById('remove-btn');
const compressBtn = document.getElementById('compress-btn');
const progressWrap = document.getElementById('progress-wrap');
const progressFill = document.getElementById('progress-fill');
const progressPct = document.getElementById('progress-pct');
const statusMsg = document.getElementById('status-msg');
const statsDiv = document.getElementById('stats');
const downloadBtn = document.getElementById('download-btn');
const levelBtns = document.querySelectorAll('.level-btn');

let selectedFile = null;
let selectedLevel = 'screen';

function formatBytes(b) {
  if (b < 1024) return b + ' B';
  if (b < 1048576) return (b/1024).toFixed(1) + ' KB';
  return (b/1048576).toFixed(2) + ' MB';
}

browseLink.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('click', e => { if (e.target !== browseLink) fileInput.click(); });
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault(); dropZone.classList.remove('over');
  const f = e.dataTransfer.files[0];
  if (f && f.type === 'application/pdf') setFile(f);
});
fileInput.addEventListener('change', () => { if (fileInput.files[0]) setFile(fileInput.files[0]); });

levelBtns.forEach(btn => btn.addEventListener('click', () => {
  levelBtns.forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  selectedLevel = btn.dataset.level;
}));

removeBtn.addEventListener('click', () => {
  selectedFile = null; fileChip.style.display = 'none';
  dropZone.style.display = 'block'; compressBtn.disabled = true;
  statsDiv.style.display = 'none'; downloadBtn.style.display = 'none';
  progressWrap.style.display = 'none'; fileInput.value = '';
});

function setFile(f) {
  selectedFile = f;
  chipName.textContent = f.name;
  chipSize.textContent = formatBytes(f.size);
  fileChip.style.display = 'flex';
  dropZone.style.display = 'none';
  compressBtn.disabled = false;
  statsDiv.style.display = 'none';
  downloadBtn.style.display = 'none';
  progressWrap.style.display = 'none';
}

function setProgress(pct, msg) {
  progressWrap.style.display = 'block';
  progressFill.style.width = pct + '%';
  progressPct.textContent = pct + '%';
  statusMsg.textContent = msg;
}

compressBtn.addEventListener('click', async () => {
  if (!selectedFile) return;
  compressBtn.disabled = true;
  statsDiv.style.display = 'none';
  downloadBtn.style.display = 'none';
  setProgress(10, 'Processing local file…');

  const formData = new FormData();
  formData.append('file', selectedFile);
  formData.append('level', selectedLevel);

  try {
    setProgress(40, 'Running Ghostscript compression…');
    const resp = await fetch('/compress', { method: 'POST', body: formData });
    setProgress(80, 'Processing result…');

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.error || 'Server error');
    }

    const blob = await resp.blob();
    const origSize = selectedFile.size;
    const compSize = blob.size;
    const savedPct = Math.round((origSize - compSize) / origSize * 100);

    // Update status text and display calculations
    setProgress(100, 'Done! Compression Complete.');
    document.getElementById('stat-orig').textContent = formatBytes(origSize);
    document.getElementById('stat-comp').textContent = formatBytes(compSize);
    document.getElementById('stat-save').textContent = '-' + (savedPct > 0 ? savedPct : 0) + '%';
    
    // Reveal size metrics container and download button
    statsDiv.style.display = 'grid';

    const url = URL.createObjectURL(blob);
    const baseName = selectedFile.name.replace(/\.pdf$/i, '');
    downloadBtn.href = url;
    downloadBtn.download = baseName + '_compressed.pdf';
    downloadBtn.style.display = 'block';
  } catch (e) {
    setProgress(0, '');
    progressWrap.style.display = 'none';
    alert('Error: ' + e.message);
  } finally {
    compressBtn.disabled = false;
  }
});
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/compress", methods=["POST"])
def compress():
    gs = find_ghostscript()
    if not gs:
        return jsonify({"error": "Ghostscript not found. Install from https://www.ghostscript.com"}), 500

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    level = request.form.get("level", "ebook")
    if level not in LEVELS:
        return jsonify({"error": "Invalid compression level"}), 400

    file = request.files["file"]
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported"}), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "output.pdf")
        file.save(input_path)

        cmd = [
            gs,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS=/{level}",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            f"-sOutputFile={output_path}",
            input_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return jsonify({"error": f"Ghostscript failed: {result.stderr}"}), 500

        stem = Path(file.filename).stem
        return send_file(
            output_path,
            as_attachment=True,
            download_name=f"{stem}_compressed.pdf",
            mimetype="application/pdf",
        )


if __name__ == "__main__":
    gs = find_ghostscript()
    if not gs:
        print("⚠️  WARNING: Ghostscript not found!")
        print("   Install from: https://www.ghostscript.com/releases/gsdnld.html")
    else:
        print(f"✅ Ghostscript found: {gs}")
    print("\n🚀 Starting PDF Compressor server...")
    print("   Open http://localhost:5000 in your browser\n")
    app.run(debug=False, port=5000)