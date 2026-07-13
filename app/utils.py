"""
utils.py — Fungsi bantuan: manajemen file, validasi, unique filename, dan drawing.
"""

import os
import uuid
import cv2
import numpy as np
from datetime import datetime
from pathlib import Path
from app.config import UPLOAD_DIR, RESULT_DIR, DATA_DIR, ALLOWED_IMAGE_EXTENSIONS


def ensure_directories():
    """Buat semua direktori yang diperlukan jika belum ada."""
    for directory in [UPLOAD_DIR, RESULT_DIR, DATA_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def generate_unique_filename(original_filename: str, prefix: str = "upload") -> str:
    """
    Membuat nama file unik menggunakan timestamp dan UUID pendek.
    
    Args:
        original_filename: Nama file asli (untuk mendapatkan ekstensi)
        prefix: Prefix nama file (upload, result, crop)
    
    Returns:
        Nama file unik, contoh: upload_20260608_103012_ab12cd.jpg
    """
    ext = Path(original_filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        ext = ".jpg"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:6]

    return f"{prefix}_{timestamp}_{unique_id}{ext}"


def validate_image_file(filename: str) -> bool:
    """
    Validasi apakah file merupakan gambar yang diizinkan berdasarkan ekstensi.
    
    Args:
        filename: Nama file yang akan divalidasi
    
    Returns:
        True jika ekstensi valid, False jika tidak
    """
    if not filename:
        return False
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_IMAGE_EXTENSIONS


async def save_upload_file(file, destination_path: Path):
    """
    Menyimpan file upload ke path tujuan.
    
    Args:
        file: UploadFile dari FastAPI
        destination_path: Path lengkap untuk menyimpan file
    """
    destination_path.parent.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    with open(destination_path, "wb") as f:
        f.write(content)


def draw_detection_result(image, box, label: str, color=(0, 255, 0), thickness=2):
    """
    Menggambar bounding box dan label pada gambar.
    
    Args:
        image: Gambar (numpy array BGR)
        box: Bounding box [x1, y1, x2, y2]
        label: Teks label yang ditampilkan
        color: Warna bounding box (BGR)
        thickness: Ketebalan garis
    
    Returns:
        Gambar dengan bounding box dan label
    """
    img = image.copy()
    x1, y1, x2, y2 = [int(v) for v in box]

    # Gambar bounding box
    cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)

    # Persiapkan label background
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.7
    font_thickness = 2

    (text_width, text_height), baseline = cv2.getTextSize(
        label, font, font_scale, font_thickness
    )

    # Background rectangle untuk label
    label_y1 = max(y1 - text_height - 10, 0)
    label_y2 = y1
    label_x1 = x1
    label_x2 = x1 + text_width + 10

    cv2.rectangle(img, (label_x1, label_y1), (label_x2, label_y2), color, -1)

    # Teks label (hitam di atas background hijau)
    cv2.putText(
        img, label,
        (x1 + 5, y1 - 5),
        font, font_scale, (0, 0, 0), font_thickness,
    )

    return img


def crop_plate_with_padding(image, box, padding_ratio: float = 0.1):
    """
    Crop area plat dari gambar dengan padding tambahan.
    Padding mencegah huruf di pinggir plat terpotong.
    
    Args:
        image: Gambar asli (numpy array)
        box: Bounding box [x1, y1, x2, y2]
        padding_ratio: Rasio padding terhadap ukuran box (default 10%)
    
    Returns:
        Gambar crop area plat
    """
    h, w = image.shape[:2]
    x1, y1, x2, y2 = [int(v) for v in box]

    # Hitung padding
    box_w = x2 - x1
    box_h = y2 - y1
    pad_x = int(box_w * padding_ratio)
    pad_y = int(box_h * padding_ratio)

    # Terapkan padding dengan batas gambar
    x1 = max(0, x1 - pad_x)
    y1 = max(0, y1 - pad_y)
    x2 = min(w, x2 + pad_x)
    y2 = min(h, y2 + pad_y)

    return image[y1:y2, x1:x2]
