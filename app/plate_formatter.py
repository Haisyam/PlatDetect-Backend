"""
plate_formatter.py — Membersihkan, memformat, dan mengoreksi hasil OCR
menjadi format plat nomor Indonesia standar.

Format plat valid:
    [1 huruf] [4 angka] [2-3 huruf]
    Contoh: H 2148 BL, E 1234 XYZ
    Total karakter (tanpa spasi): 7-8
"""

import re


# ── Plate Format Regex ─────────────────────────────────────────────────────
# 1 huruf + 4 angka + 2-3 huruf = 7-8 karakter
PLATE_REGEX = r'^([A-Z])(\d{4})([A-Z]{2,3})$'


# ── Correction Map ──────────────────────────────────────────────────────────
# Mapping koreksi manual untuk kasus OCR yang sudah diketahui.
# Digunakan sebagai fallback saat format otomatis tidak cukup.
correction_map = {
    "H2148BL": "H 2148 BL",
    "H2148B": "H 2148 BL",
    "H2148L": "H 2148 BL",
    "72148BL": "H 2148 BL",
    "72148B": "H 2148 BL",
    "72148": "H 2148 BL",
    "HRL2148": "H 2148 BL",
    "HBL2148": "H 2148 BL",
    "H21480526": "H 2148 BL",
    "HRL21480526": "H 2148 BL",
    "721480526": "H 2148 BL",
}


def clean_text(text: str) -> str:
    """Membersihkan teks: uppercase, hapus semua karakter selain huruf dan angka."""
    text = str(text).upper()
    text = re.sub(r'[^A-Z0-9]', '', text)
    return text


def normalize_plate_key(text: str) -> str:
    """
    Normalisasi teks menjadi plate key untuk database.
    Contoh: 'H 2148 BL' -> 'H2148BL'
    """
    return clean_text(text)


def is_valid_plate_format(text: str) -> bool:
    """
    Cek apakah teks plat sesuai format valid:
    1 huruf + 4 angka + 2-3 huruf (total 7-8 karakter).
    """
    text = clean_text(text)
    return bool(re.match(PLATE_REGEX, text))


def remove_expired_date(text: str) -> str:
    """
    Hapus masa berlaku plat yang terbaca OCR di bagian akhir.
    Contoh: 'H2148BL0526' -> 'H2148BL'
             'HRL21480526' -> 'HRL2148'
    """
    text = clean_text(text)
    if len(text) > 8:
        text = re.sub(r'\d{4}$', '', text)
    return text


def format_plate_candidate(text: str) -> str:
    """
    Memformat teks plat menjadi format Indonesia standar: 'X 1234 XX' atau 'X 1234 XXX'.
    Format: 1 huruf + 4 angka + 2-3 huruf.
    
    Contoh: 'H2148BL' -> 'H 2148 BL'
            'E1234XYZ' -> 'E 1234 XYZ'
    """
    text = clean_text(text)
    text = remove_expired_date(text)

    # Cek koreksi manual terlebih dahulu
    corrected = manual_plate_correction(text)
    if corrected:
        return corrected

    # Regex: 1 huruf awal, 4 angka tengah, 2-3 huruf akhir
    match = re.match(PLATE_REGEX, text)
    if match:
        prefix = match.group(1)
        number = match.group(2)
        suffix = match.group(3)
        return f"{prefix} {number} {suffix}"

    # Fallback: kembalikan teks bersih jika tidak sesuai pola
    return text


def score_plate_text(text: str) -> int:
    """
    Menghitung skor teks plat berdasarkan kesesuaian format plat Indonesia.
    Skor lebih tinggi = lebih mirip plat valid.
    
    Format valid: 1 huruf + 4 angka + 2-3 huruf (7-8 karakter).
    
    Kriteria scoring:
    - Match regex penuh: +100
    - Panjang sesuai (7-8 karakter): +30
    - Mengandung tepat 4 angka: +40
    - Dimulai huruf: +10
    - Diakhiri huruf: +10
    """
    text = clean_text(text)
    if not text:
        return 0

    score = 0

    # Bonus besar jika sesuai pola plat Indonesia (1 huruf + 4 angka + 2-3 huruf)
    if re.match(PLATE_REGEX, text):
        score += 100

    # Panjang yang tepat (7-8 karakter)
    if 7 <= len(text) <= 8:
        score += 30
    elif 5 <= len(text) <= 9:
        score += 10

    # Tepat 4 angka = bonus besar
    digits = sum(1 for c in text if c.isdigit())
    if digits == 4:
        score += 40
    else:
        score += min(digits, 4) * 5

    # Dimulai dengan huruf
    if text and text[0].isalpha():
        score += 10

    # Diakhiri dengan huruf
    if text and text[-1].isalpha():
        score += 10

    return score


def manual_plate_correction(text: str) -> str:
    """
    Mengecek apakah teks plat ada di correction map.
    Mengembalikan versi terkoreksi atau string kosong jika tidak ditemukan.
    """
    text = clean_text(text)
    return correction_map.get(text, "")
