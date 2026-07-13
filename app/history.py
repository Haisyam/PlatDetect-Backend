"""
history.py — Menyimpan dan membaca riwayat deteksi dari file CSV.
"""

import pandas as pd
from datetime import datetime
from app.config import HISTORY_CSV, DATA_DIR

# Kolom CSV riwayat deteksi
HISTORY_COLUMNS = [
    "waktu", "nama_file", "plate", "plate_key", "raw_ocr",
    "status", "owner_name", "vehicle_type", "description",
    "confidence_yolo", "ocr_score", "ocr_version",
    "result_image", "plate_crop",
]


def ensure_history_csv():
    """Buat file riwayat_deteksi.csv jika belum ada."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not HISTORY_CSV.exists():
        df = pd.DataFrame(columns=HISTORY_COLUMNS)
        df.to_csv(HISTORY_CSV, index=False)


def save_detection_history(record: dict):
    """
    Simpan satu record riwayat deteksi ke CSV.
    Otomatis menambahkan timestamp.
    
    Args:
        record: dict berisi data deteksi (tanpa kolom 'waktu')
    """
    ensure_history_csv()

    # Tambahkan timestamp
    record["waktu"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Pastikan semua kolom ada
    row = {col: record.get(col, "") for col in HISTORY_COLUMNS}

    new_row = pd.DataFrame([row])
    new_row.to_csv(HISTORY_CSV, mode="a", header=False, index=False)


def get_detection_history(limit: int = 50) -> list[dict]:
    """
    Mengambil riwayat deteksi dari CSV, terbaru ditampilkan paling atas.
    
    Args:
        limit: Jumlah maksimal riwayat yang dikembalikan (default 50)
    
    Returns:
        list[dict]: Daftar riwayat deteksi
    """
    ensure_history_csv()

    try:
        df = pd.read_csv(HISTORY_CSV, dtype=str).fillna("")
        if df.empty:
            return []

        # Terbaru di atas
        df = df.iloc[::-1].head(limit)
        return df.to_dict(orient="records")
    except Exception:
        return []


def delete_history_record(index: int):
    """
    Hapus satu record riwayat berdasarkan index (urutan terbaru, 0-based).

    Args:
        index: Index record yang akan dihapus (0 = terbaru)
    """
    ensure_history_csv()

    df = pd.read_csv(HISTORY_CSV, dtype=str).fillna("")
    if df.empty:
        raise ValueError("Riwayat kosong")

    # Convert index terbaru ke index asli di CSV
    reversed_indices = list(reversed(df.index.tolist()))
    if index < 0 or index >= len(reversed_indices):
        raise ValueError("Index tidak valid")

    actual_index = reversed_indices[index]
    df = df.drop(actual_index)
    df.to_csv(HISTORY_CSV, index=False)

    return {"message": "Riwayat berhasil dihapus"}


def clear_all_history():
    """Hapus seluruh riwayat deteksi."""
    ensure_history_csv()
    df = pd.DataFrame(columns=HISTORY_COLUMNS)
    df.to_csv(HISTORY_CSV, index=False)
    return {"message": "Seluruh riwayat berhasil dihapus"}

