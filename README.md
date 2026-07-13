# PRODUK AI — Backend Deteksi Plat Nomor Kendaraan

Backend FastAPI untuk sistem deteksi dan pengenalan plat nomor kendaraan menggunakan YOLO dan OCR.

## Fitur

- **Deteksi Plat Nomor** — Upload gambar → YOLO deteksi → crop plat → OCR baca teks → format plat Indonesia → cek database
- **Database Kendaraan** — CRUD sederhana berbasis CSV
- **Riwayat Deteksi** — Semua hasil deteksi tersimpan otomatis
- **Multi-Preprocessing OCR** — 6 versi preprocessing untuk akurasi maksimal

## Tech Stack

- Python 3.10+
- FastAPI + Uvicorn
- Ultralytics YOLO
- EasyOCR
- OpenCV
- Pandas

## Struktur Folder

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI app & endpoints
│   ├── config.py           # Konfigurasi global
│   ├── detector.py         # YOLO model loader & detection
│   ├── ocr_engine.py       # Multi-preprocessing OCR
│   ├── plate_formatter.py  # Format & koreksi plat Indonesia
│   ├── vehicle_database.py # CRUD database kendaraan CSV
│   ├── history.py          # Riwayat deteksi CSV
│   └── utils.py            # Fungsi bantuan
├── models/
│   └── best.pt             # Model YOLO (harus disediakan)
├── data/
│   ├── kendaraan.csv       # Database kendaraan
│   └── riwayat_deteksi.csv # Riwayat deteksi
├── uploads/                # File upload disimpan di sini
├── results/                # Hasil deteksi & crop plat
├── requirements.txt
└── README.md
```

## Setup & Menjalankan

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Letakkan Model YOLO

Letakkan file `best.pt` hasil training ke:

```
backend/models/best.pt
```

### 3. Jalankan Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 7860 --reload
```

### 4. Akses API

- Swagger Docs: [http://localhost:7860/docs](http://localhost:7860/docs)
- Health Check: [http://localhost:7860/health](http://localhost:7860/health)

## API Endpoints

| Method | Endpoint         | Deskripsi                          |
|--------|------------------|------------------------------------|
| GET    | `/`              | Informasi backend                  |
| GET    | `/health`        | Health check                       |
| POST   | `/api/detect`    | Upload gambar & deteksi plat       |
| GET    | `/api/vehicles`  | Daftar kendaraan dari CSV          |
| POST   | `/api/vehicles`  | Tambah kendaraan baru              |
| GET    | `/api/history`   | Riwayat deteksi                    |

## Contoh Response `/api/detect`

```json
{
  "success": true,
  "message": "Deteksi berhasil",
  "data": {
    "plate": "H 2148 BL",
    "plate_key": "H2148BL",
    "raw_ocr": "H2148BL",
    "status": "Terdaftar",
    "owner_name": "Muhamad Haisyam",
    "vehicle_type": "Motor",
    "description": "Kendaraan pribadi",
    "confidence_yolo": 0.87,
    "ocr_score": 120,
    "ocr_version": "clahe",
    "result_image_url": "/static/results/result_xxx.jpg",
    "plate_crop_url": "/static/results/crop_xxx.jpg"
  }
}
```

## Catatan Deployment (Hugging Face Spaces)

- Port utama: `7860`
- Gunakan `opencv-python-headless`
- EasyOCR dengan `gpu=False`
- File `best.pt` harus tersedia di `backend/models/best.pt`
