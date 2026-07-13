"""
ocr_engine.py — Multi-preprocessing OCR engine menggunakan EasyOCR.
Menjalankan OCR pada beberapa versi preprocessing dan memilih hasil terbaik.
"""

import cv2
import numpy as np
from app.plate_formatter import clean_text, format_plate_candidate, score_plate_text

# ── Singleton EasyOCR Reader ────────────────────────────────────────────────
_reader = None


def load_reader():
    """Load EasyOCR reader sekali saja (singleton). GPU=False untuk CPU basic."""
    global _reader
    if _reader is None:
        import easyocr
        _reader = easyocr.Reader(['en'], gpu=False)
    return _reader


# ── Preprocessing Functions ─────────────────────────────────────────────────

def crop_main_plate_line(plate_crop):
    """
    Ambil bagian atas plat saja (sekitar 58% tinggi crop).
    Ini untuk menghindari terbacanya masa berlaku (misal '05 26') 
    yang ada di baris bawah plat Indonesia.
    """
    if plate_crop is None or plate_crop.size == 0:
        return plate_crop

    h, w = plate_crop.shape[:2]
    main_line = plate_crop[0:int(h * 0.58), 0:w]

    # Pastikan crop tidak terlalu kecil
    if main_line.shape[0] < 10 or main_line.shape[1] < 10:
        return plate_crop

    return main_line


def make_ocr_versions(plate_crop) -> dict:
    """
    Membuat beberapa versi preprocessing dari crop plat untuk OCR.
    Setiap versi mengoptimalkan aspek berbeda dari gambar plat.
    
    Versi yang dihasilkan:
    - gray: Grayscale standar
    - clahe: Contrast-Limited Adaptive Histogram Equalization
    - blur: Gaussian blur untuk mengurangi noise
    - sharp: Sharpening untuk memperjelas tepi karakter
    - otsu: Otsu thresholding untuk binarisasi
    - inverted: Versi terbalik dari otsu
    """
    versions = {}

    # Konversi ke grayscale jika belum
    if len(plate_crop.shape) == 3:
        gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
    else:
        gray = plate_crop.copy()

    # 1. Gray — baseline
    versions["gray"] = gray

    # 2. CLAHE — adaptive contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    versions["clahe"] = clahe.apply(gray)

    # 3. Blur — gaussian blur untuk kurangi noise
    versions["blur"] = cv2.GaussianBlur(gray, (3, 3), 0)

    # 4. Sharp — kernel sharpening
    kernel_sharp = np.array([[-1, -1, -1],
                              [-1,  9, -1],
                              [-1, -1, -1]])
    versions["sharp"] = cv2.filter2D(gray, -1, kernel_sharp)

    # 5. Otsu — binary thresholding otomatis
    blurred_for_otsu = cv2.GaussianBlur(gray, (5, 5), 0)
    _, otsu = cv2.threshold(blurred_for_otsu, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    versions["otsu"] = otsu

    # 6. Inverted — kebalikan dari otsu
    versions["inverted"] = cv2.bitwise_not(otsu)

    return versions


# ── Multi-OCR Reader ────────────────────────────────────────────────────────

def read_plate_with_multi_ocr(plate_crop) -> dict:
    """
    Menjalankan OCR pada semua versi preprocessing dan memilih hasil terbaik
    berdasarkan skor format plat Indonesia.
    
    Args:
        plate_crop: Gambar crop area plat (numpy array BGR atau grayscale)
    
    Returns:
        dict: {
            "raw": "H2148BL",
            "formatted": "H 2148 BL",
            "score": 120,
            "version": "clahe"
        }
    """
    reader = load_reader()

    # Ambil baris utama plat (tanpa masa berlaku)
    main_crop = crop_main_plate_line(plate_crop)

    # Buat semua versi preprocessing
    versions = make_ocr_versions(main_crop)

    best_result = {
        "raw": "",
        "formatted": "",
        "score": 0,
        "version": "none",
    }

    allowlist = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    for version_name, version_img in versions.items():
        try:
            # Jalankan OCR
            results = reader.readtext(
                version_img,
                allowlist=allowlist,
                detail=1,
                paragraph=False,
            )

            # Gabungkan semua teks yang terdeteksi
            raw_texts = []
            for detection in results:
                text = detection[1] if len(detection) > 1 else ""
                text = clean_text(text)
                if text:
                    raw_texts.append(text)

            combined_raw = "".join(raw_texts)

            if not combined_raw:
                continue

            # Format dan skor
            formatted = format_plate_candidate(combined_raw)
            score = score_plate_text(combined_raw)

            # Update best jika skor lebih tinggi
            if score > best_result["score"]:
                best_result = {
                    "raw": combined_raw,
                    "formatted": formatted,
                    "score": score,
                    "version": version_name,
                }

        except Exception:
            continue

    return best_result
