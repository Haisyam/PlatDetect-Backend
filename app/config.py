"""
Konfigurasi global untuk backend PlatDetect - Deteksi Plat Nomor Kendaraan.
"""

from pathlib import Path

# ── Path Constants ──────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "best.pt"

# ── Local Server Storage ───────────────────────────────────────────────────
# Menggunakan folder lokal di dalam backend/ untuk penyimpanan data & upload.
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"
RESULT_DIR = BASE_DIR / "results"
PHOTOS_DIR = BASE_DIR / "photos"

VEHICLE_CSV = DATA_DIR / "kendaraan.csv"
HISTORY_CSV = DATA_DIR / "riwayat_deteksi.csv"

# ── Image Validation ───────────────────────────────────────────────────────
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# ── YOLO Configuration ─────────────────────────────────────────────────────
YOLO_CONFIDENCE = 0.5

# ── App Metadata ────────────────────────────────────────────────────────────
APP_NAME = "PlatDetect - Deteksi Plat Nomor Kendaraan"
APP_VERSION = "1.0.0"

# ── CORS ────────────────────────────────────────────────────────────────────
CORS_ORIGINS = ["*"]
