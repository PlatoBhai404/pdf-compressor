"""
PDF Compressor - Desktop App (Fixed Layout & Preview Flow)
Requires: pip install customtkinter pypdf
Requires: Ghostscript installed (https://www.ghostscript.com/releases/gsdnld.html)
"""

import os
import sys
import subprocess
import threading
import shutil
import tempfile
from pathlib import Path

try:
    import customtkinter as ctk
    from tkinter import filedialog, messagebox
except ImportError:
    print("Run: pip install customtkinter")
    sys.exit(1)

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

LEVELS = {
    "Max (72 DPI)":      "screen",
    "Balanced (150 DPI)": "ebook",
    "Quality (300 DPI)": "printer",
    "Lossless (600 DPI)": "prepress",
}

def find_ghostscript():
    """Find ghostscript executable across platforms."""
    candidates = ["gs", "gswin64c", "gswin32c"]
    for c in candidates:
        if shutil.which(c):
            return c
    # Windows common install paths
    for path in [
        r"C:\Program Files\gs\gs10.03.1\bin\gswin64c.exe",
        r"C:\Program Files\gs\gs10.02.1\bin\gswin64c.exe",
        r"C:\Program Files (x86)\gs\gs9.56.1\bin\gswin32c.exe",
    ]:
        if os.path.exists(path):
            return path
    return None

def format_bytes(size):
    if size < 1024:
        return f"{size} B"
    elif size < 1048576:
        return f"{size/1024:.1f} KB"
    else:
        return f"{size/1048576:.2f} MB"

def compress_pdf(input_path, output_path, level, progress_cb):
    gs = find_ghostscript()
    if not gs:
        raise RuntimeError(
            "Ghostscript not found.\n\n"
            "Install it from: https://www.ghostscript.com/releases/gsdnld.html\n"
            "Then restart this app."
        )
    progress_cb(40, "Running Ghostscript compression…")
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
        raise RuntimeError(f"Ghostscript error:\n{result.stderr}")
    progress_cb(90, "Processing optimizations…")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PDF Compressor")
        self.geometry("520x660")
        self.resizable(True, True)  # Enabled resizing to avoid out-of-screen content bugs
        self.input_path = None
        self.temp_output_path = None
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)

        # Header
        ctk.CTkLabel(self, text="PDF Compressor", font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, padx=30, pady=(20, 2), sticky="w")
        ctk.CTkLabel(self, text="Reduce PDF file size using Ghostscript",
                     font=ctk.CTkFont(size=13), text_color="gray").grid(
            row=1, column=0, padx=30, pady=(0, 14), sticky="w")

        # Drop / select area
        self.drop_frame = ctk.CTkFrame(self, height=100, corner_radius=12,
                                       fg_color=("gray90", "gray20"),
                                       border_width=2, border_color=("gray70", "gray40"))
        self.drop_frame.grid(row=2, column=0, padx=30, pady=(0, 12), sticky="ew")
        self.drop_frame.grid_columnconfigure(0, weight=1)
        self.drop_frame.grid_propagate(False)

        self.file_icon = ctk.CTkLabel(self.drop_frame, text="📄", font=ctk.CTkFont(size=24))
        self.file_icon.grid(row=0, column=0, pady=(14, 2))
        self.file_label = ctk.CTkLabel(self.drop_frame, text="No file selected",
                                        font=ctk.CTkFont(size=13), text_color="gray")
        self.file_label.grid(row=1, column=0, pady=(0, 2))

        ctk.CTkButton(self, text="Browse PDF File…", command=self._pick_file,
                      height=38, corner_radius=8).grid(
            row=3, column=0, padx=30, pady=(0, 16), sticky="ew")

        # Compression level
        ctk.CTkLabel(self, text="Compression level", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=4, column=0, padx=30, pady=(0, 6), sticky="w")

        self.level_var = ctk.StringVar(value="Max (72 DPI)")
        for i, (label, _) in enumerate(LEVELS.items()):
            ctk.CTkRadioButton(self, text=label, variable=self.level_var, value=label,
                               font=ctk.CTkFont(size=13)).grid(
                row=5+i, column=0, padx=44, pady=2, sticky="w")

        # Progress elements
        self.progress_bar = ctk.CTkProgressBar(self, height=6, corner_radius=3)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=9, column=0, padx=30, pady=(16, 4), sticky="ew")

        self.status_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=12, weight="bold"),
                                          text_color="gray")
        self.status_label.grid(row=10, column=0, padx=30, pady=(0, 8))

        # Stats Wrapper Grid Block
        self.stats_frame = ctk.CTkFrame(self, fg_color=("gray90", "gray20"), corner_radius=10)
        self.stats_frame.grid(row=11, column=0, padx=30, pady=(0, 12), sticky="ew")
        self.stats_frame.grid_columnconfigure((0,1,2), weight=1)
        self.stats_frame.grid_remove()

        for col, (label, attr) in enumerate([("Original", "stat_orig"),
                                              ("Compressed", "stat_comp"),
                                              ("Saved", "stat_save")]):
            ctk.CTkLabel(self.stats_frame, text=label, font=ctk.CTkFont(size=11),
                          text_color="gray").grid(row=0, column=col, padx=12, pady=(8,2))
            lbl = ctk.CTkLabel(self.stats_frame, text="—", font=ctk.CTkFont(size=14, weight="bold"))
            lbl.grid(row=1, column=col, padx=12, pady=(0,8))
            setattr(self, attr, lbl)

        # Primary Compression Command Button
        self.compress_btn = ctk.CTkButton(self, text="Compress PDF", height=42,
                                           corner_radius=10, font=ctk.CTkFont(size=14, weight="bold"),
                                           command=self._start_compress, state="disabled")
        self.compress_btn.grid(row=12, column=0, padx=30, pady=(0, 10), sticky="ew")

        # Save Action Button (Hidden until completion metrics match verification rules)
        self.download_btn = ctk.CTkButton(self, text="⬇ Download Compressed PDF", height=42,
                                           fg_color="#1a9e75", hover_color="#147d5c",
                                           corner_radius=10, font=ctk.CTkFont(size=14, weight="bold"),
                                           command=self._save_compressed_file)
        self.download_btn.grid(row=13, column=0, padx=30, pady=(0, 20), sticky="ew")
        self.download_btn.grid_remove()

    def _pick_file(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if path:
            self.input_path = path
            name = Path(path).name
            size = format_bytes(os.path.getsize(path))
            self.file_label.configure(text=f"{name}  ({size})", text_color=("gray20","gray90"))
            self.file_icon.configure(text="✅")
            self.compress_btn.configure(state="normal")
            self.stats_frame.grid_remove()
            self.download_btn.grid_remove()
            self._set_status("")
            self.progress_bar.set(0)

    def _set_status(self, msg, color="gray"):
        self.status_label.configure(text=msg, text_color=color)

    def _set_progress(self, pct, msg=""):
        self.progress_bar.set(pct / 100)
        self._set_status(msg)

    def _start_compress(self):
        if not self.input_path:
            return
        self.compress_btn.configure(state="disabled")
        self.stats_frame.grid_remove()
        self.download_btn.grid_remove()
        self._set_progress(10, "Initializing workspace…")

        level_label = self.level_var.get()
        level = LEVELS[level_label]
        input_path = self.input_path
        
        # Write out target parameters to cache temporary directories instead of downloads
        self.temp_dir = tempfile.mkdtemp()
        self.temp_output_path = os.path.join(self.temp_dir, "optimized_output.pdf")

        def run():
            try:
                compress_pdf(input_path, self.temp_output_path, level,
                             lambda p, m: self.after(0, self._set_progress, p, m))
                orig = os.path.getsize(input_path)
                comp = os.path.getsize(self.temp_output_path)
                saved_pct = round((orig - comp) / orig * 100) if orig > 0 else 0
                self.after(0, self._on_done, orig, comp, saved_pct)
            except Exception as e:
                self.after(0, self._on_error, str(e))

        threading.Thread(target=run, daemon=True).start()

    def _on_done(self, orig, comp, saved_pct):
        self._set_progress(100, "Done! Compression Complete.")
        self.status_label.configure(text_color="#1a9e75")
        self.stat_orig.configure(text=format_bytes(orig))
        self.stat_comp.configure(text=format_bytes(comp))
        
        display_pct = saved_pct if saved_pct > 0 else 0
        color = "#1a9e75" if saved_pct > 0 else "gray"
        self.stat_save.configure(text=f"-{display_pct}%", text_color=color)
        
        # Display feedback charts and execution controls
        self.stats_frame.grid()
        self.download_btn.grid()
        self.compress_btn.configure(state="normal")

    def _save_compressed_file(self):
        if not self.temp_output_path or not os.path.exists(self.temp_output_path):
            messagebox.showerror("Error", "No compressed data file found. Please run compression first.")
            return
            
        initial_name = f"{Path(self.input_path).stem}_compressed.pdf"
        save_path = filedialog.asksaveasfilename(initialfile=initial_name, filetypes=[("PDF files", "*.pdf")])
        
        if save_path:
            try:
                shutil.copy(self.temp_output_path, save_path)
                messagebox.showinfo("Success", f"File saved successfully to:\n{save_path}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Could not write target location data:\n{str(e)}")

    def _on_error(self, msg):
        self._set_progress(0, "")
        self.compress_btn.configure(state="normal")
        messagebox.showerror("Compression failed", msg)


if __name__ == "__main__":
    app = App()
    app.mainloop()