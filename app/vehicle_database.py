"""
vehicle_database.py — Membaca dan mengelola database kendaraan dari file CSV.
"""

import pandas as pd
import re
from app.config import VEHICLE_CSV, DATA_DIR
from app.plate_formatter import is_valid_plate_format


def _normalize_plate(text: str) -> str:
    """Normalisasi plat: uppercase, hapus semua karakter selain huruf & angka."""
    text = str(text).upper()
    text = re.sub(r'[^A-Z0-9]', '', text)
    return text


VEHICLE_COLUMNS = ["plat", "nama_pemilik", "jenis_kendaraan", "keterangan", "foto_pemilik"]


def _ensure_vehicle_csv():
    """Buat file CSV kendaraan dengan header default jika belum ada. Migrasi kolom baru jika perlu."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not VEHICLE_CSV.exists():
        df = pd.DataFrame(columns=VEHICLE_COLUMNS)
        df.to_csv(VEHICLE_CSV, index=False)
    else:
        # Migrasi: baca CSV (toleransi baris rusak), pastikan semua kolom ada, tulis ulang
        try:
            df = pd.read_csv(
                VEHICLE_CSV, dtype=str,
                on_bad_lines="warn",
                names=None,
            )
            df = df.fillna("")
            # Tambahkan kolom yang belum ada
            for col in VEHICLE_COLUMNS:
                if col not in df.columns:
                    df[col] = ""
            # Pastikan urutan kolom benar
            df = df[VEHICLE_COLUMNS]
            df.to_csv(VEHICLE_CSV, index=False)
        except Exception:
            # Jika CSV benar-benar rusak, buat ulang
            df = pd.DataFrame(columns=VEHICLE_COLUMNS)
            df.to_csv(VEHICLE_CSV, index=False)


def load_vehicles() -> list[dict]:
    """Membaca seluruh data kendaraan dari CSV."""
    _ensure_vehicle_csv()
    try:
        df = pd.read_csv(VEHICLE_CSV, dtype=str).fillna("")
        return df.to_dict(orient="records")
    except Exception:
        return []


def find_vehicle_by_plate(plate_text: str) -> dict:
    """
    Mencari kendaraan berdasarkan teks plat.
    Normalisasi dilakukan agar H 2148 BL, h-2148-bl, H2148BL semua cocok.
    """
    _ensure_vehicle_csv()
    plate_key = _normalize_plate(plate_text)

    if not plate_key:
        return {
            "status": "Tidak Terdaftar",
            "plate_key": "",
            "owner_name": "-",
            "vehicle_type": "-",
            "description": "Plat kosong atau tidak valid",
        }

    try:
        df = pd.read_csv(VEHICLE_CSV, dtype=str).fillna("")
        # Normalisasi kolom plat di CSV untuk pencocokan
        df["plat_normalized"] = df["plat"].apply(_normalize_plate)

        match = df[df["plat_normalized"] == plate_key]

        if not match.empty:
            row = match.iloc[0]
            return {
                "status": "Terdaftar",
                "plate_key": plate_key,
                "owner_name": row["nama_pemilik"],
                "vehicle_type": row["jenis_kendaraan"],
                "description": row["keterangan"],
                "foto_pemilik": row.get("foto_pemilik", ""),
            }
    except Exception:
        pass

    return {
        "status": "Tidak Terdaftar",
        "plate_key": plate_key,
        "owner_name": "-",
        "vehicle_type": "-",
        "description": "Plat tidak ditemukan di database",
        "foto_pemilik": "",
    }


def add_vehicle(data: dict) -> dict:
    """
    Menambahkan data kendaraan baru ke CSV.
    Validasi: plat dan nama_pemilik tidak boleh kosong, plat tidak boleh duplikat.
    """
    _ensure_vehicle_csv()

    plat = _normalize_plate(data.get("plat", ""))
    nama_pemilik = str(data.get("nama_pemilik", "")).strip()
    jenis_kendaraan = str(data.get("jenis_kendaraan", "")).strip() or "-"
    keterangan = str(data.get("keterangan", "")).strip() or "-"
    foto_pemilik = str(data.get("foto_pemilik", "")).strip()

    if not plat:
        raise ValueError("Plat nomor tidak boleh kosong")
    if not is_valid_plate_format(plat):
        raise ValueError(
            "Format plat tidak valid. Harus 1 huruf + 4 angka + 2-3 huruf. "
            "Contoh: H2148BL atau E1234XYZ"
        )
    if not nama_pemilik:
        raise ValueError("Nama pemilik tidak boleh kosong")

    # Cek duplikat
    df = pd.read_csv(VEHICLE_CSV, dtype=str).fillna("")
    df["plat_normalized"] = df["plat"].apply(_normalize_plate)

    if plat in df["plat_normalized"].values:
        raise ValueError(f"Plat {plat} sudah terdaftar di database")

    # Tambahkan data baru
    new_row = pd.DataFrame([{
        "plat": plat,
        "nama_pemilik": nama_pemilik,
        "jenis_kendaraan": jenis_kendaraan,
        "keterangan": keterangan,
        "foto_pemilik": foto_pemilik,
    }])
    new_row.to_csv(VEHICLE_CSV, mode="a", header=False, index=False)

    return {
        "plat": plat,
        "nama_pemilik": nama_pemilik,
        "jenis_kendaraan": jenis_kendaraan,
        "keterangan": keterangan,
        "foto_pemilik": foto_pemilik,
    }


def update_vehicle(plat_key: str, data: dict) -> dict:
    """
    Update data kendaraan berdasarkan plat key.
    """
    _ensure_vehicle_csv()

    plat_key = _normalize_plate(plat_key)
    if not plat_key:
        raise ValueError("Plat nomor tidak valid")

    nama_pemilik = str(data.get("nama_pemilik", "")).strip()
    jenis_kendaraan = str(data.get("jenis_kendaraan", "")).strip() or "-"
    keterangan = str(data.get("keterangan", "")).strip() or "-"

    if not nama_pemilik:
        raise ValueError("Nama pemilik tidak boleh kosong")

    df = pd.read_csv(VEHICLE_CSV, dtype=str).fillna("")
    df["plat_normalized"] = df["plat"].apply(_normalize_plate)

    mask = df["plat_normalized"] == plat_key
    if not mask.any():
        raise ValueError(f"Plat {plat_key} tidak ditemukan di database")

    df.loc[mask, "nama_pemilik"] = nama_pemilik
    df.loc[mask, "jenis_kendaraan"] = jenis_kendaraan
    df.loc[mask, "keterangan"] = keterangan

    df.drop(columns=["plat_normalized"], inplace=True)
    df.to_csv(VEHICLE_CSV, index=False)

    return {
        "plat": plat_key,
        "nama_pemilik": nama_pemilik,
        "jenis_kendaraan": jenis_kendaraan,
        "keterangan": keterangan,
    }


def delete_vehicle(plat_key: str) -> dict:
    """
    Hapus data kendaraan berdasarkan plat key.
    """
    _ensure_vehicle_csv()

    plat_key = _normalize_plate(plat_key)
    if not plat_key:
        raise ValueError("Plat nomor tidak valid")

    df = pd.read_csv(VEHICLE_CSV, dtype=str).fillna("")
    df["plat_normalized"] = df["plat"].apply(_normalize_plate)

    mask = df["plat_normalized"] == plat_key
    if not mask.any():
        raise ValueError(f"Plat {plat_key} tidak ditemukan di database")

    df = df[~mask]
    df.drop(columns=["plat_normalized"], inplace=True)
    df.to_csv(VEHICLE_CSV, index=False)

    return {"plat": plat_key, "message": "Data berhasil dihapus"}

