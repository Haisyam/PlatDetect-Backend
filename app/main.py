"""
main.py — File utama FastAPI backend PRODUK AI - Deteksi Plat Nomor Kendaraan.

Endpoints:
    GET  /             — Info backend
    GET  /health       — Health check
    POST /api/detect   — Upload gambar, deteksi plat, OCR, cek database
    GET  /api/vehicles — Daftar kendaraan dari CSV
    POST /api/vehicles — Tambah kendaraan baru ke CSV
    GET  /api/history  — Riwayat deteksi
"""

import cv2
import traceback
import urllib.parse
import httpx
from pathlib import Path

from fastapi.responses import FileResponse

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import (
    APP_NAME, APP_VERSION, CORS_ORIGINS,
    UPLOAD_DIR, RESULT_DIR, PHOTOS_DIR, BASE_DIR,
)

# Path ke frontend build (hanya tersedia di Docker production)
FRONTEND_DIST = BASE_DIR / "frontend_dist"
from app.utils import (
    ensure_directories,
    generate_unique_filename,
    validate_image_file,
    save_upload_file,
    draw_detection_result,
    crop_plate_with_padding,
)
from app.detector import load_model, is_model_loaded, detect_license_plate, get_best_detection
from app.ocr_engine import load_reader, read_plate_with_multi_ocr
from app.plate_formatter import normalize_plate_key
from app.vehicle_database import load_vehicles, find_vehicle_by_plate, add_vehicle, update_vehicle, delete_vehicle
from app.history import ensure_history_csv, save_detection_history, get_detection_history, delete_history_record, clear_all_history


# ── FastAPI App ─────────────────────────────────────────────────────────────

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Backend API untuk deteksi dan pengenalan plat nomor kendaraan menggunakan YOLO dan OCR",
)

# ── CORS Middleware ─────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup Event ───────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Inisialisasi saat server start: buat direktori, load model dan OCR reader."""
    ensure_directories()
    ensure_history_csv()
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

    # Load YOLO model
    try:
        load_model()
        print(f"[✓] Model YOLO berhasil di-load")
    except FileNotFoundError as e:
        print(f"[✗] Model YOLO tidak ditemukan: {e}")
        print(f"    Letakkan file best.pt di backend/models/best.pt")
    except Exception as e:
        print(f"[✗] Gagal load model YOLO: {e}")

    # Load EasyOCR reader
    try:
        load_reader()
        print(f"[✓] EasyOCR reader berhasil di-load")
    except Exception as e:
        print(f"[✗] Gagal load EasyOCR: {e}")


# ── Static Files ────────────────────────────────────────────────────────────

# Mount setelah direktori dipastikan ada
@app.on_event("startup")
async def mount_static():
    """Mount static file serving setelah direktori dibuat."""
    app.mount("/static/results", StaticFiles(directory=str(RESULT_DIR)), name="results")
    app.mount("/static/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

    # Serve frontend build jika tersedia (production Docker)
    if FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="frontend_assets")
        print(f"[✓] Frontend build ditemukan di {FRONTEND_DIST}")


# ── Pydantic Models ─────────────────────────────────────────────────────────

class VehicleInput(BaseModel):
    plat: str
    nama_pemilik: str
    jenis_kendaraan: str = "-"
    keterangan: str = "-"


class VehicleUpdateInput(BaseModel):
    nama_pemilik: str
    jenis_kendaraan: str = "-"
    keterangan: str = "-"


# ── Helper Response ─────────────────────────────────────────────────────────

def success_response(message: str, data=None):
    """Format response sukses yang konsisten."""
    return {"success": True, "message": message, "data": data}


def error_response(message: str):
    """Format response error yang konsisten."""
    return {"success": False, "message": message, "data": None}


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════


# ── GET / ───────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Serve frontend index.html jika tersedia, atau info backend."""
    if FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
        return FileResponse(str(FRONTEND_DIST / "index.html"))
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "status": "running",
    }


# ── GET /health ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "success": True,
        "message": "Backend aktif",
        "model_loaded": is_model_loaded(),
    }


# ── POST /api/detect ───────────────────────────────────────────────────────

@app.post("/api/detect")
async def detect_plate(file: UploadFile = File(...)):
    """
    Endpoint utama: menerima gambar, mendeteksi plat nomor,
    membaca teks via OCR, dan mengembalikan informasi pemilik kendaraan.
    """
    try:
        # 1. Validasi file
        if not file.filename:
            return error_response("File tidak memiliki nama")

        if not validate_image_file(file.filename):
            return error_response(
                "Format file tidak didukung. Gunakan JPG, JPEG, PNG, atau WEBP."
            )

        # Cek apakah file kosong
        content = await file.read()
        if len(content) == 0:
            return error_response("File kosong")
        await file.seek(0)  # Reset file pointer

        # 2. Cek model YOLO tersedia
        if not is_model_loaded():
            try:
                load_model()
            except FileNotFoundError:
                return error_response(
                    "Model YOLO (best.pt) tidak ditemukan. "
                    "Pastikan file best.pt ada di folder backend/models/"
                )

        # 3. Simpan file upload
        upload_filename = generate_unique_filename(file.filename, prefix="upload")
        upload_path = UPLOAD_DIR / upload_filename
        await save_upload_file(file, upload_path)

        # 4. Baca gambar dengan OpenCV
        image = cv2.imread(str(upload_path))
        if image is None:
            return error_response("Gambar rusak atau tidak bisa dibaca")

        # 5. Jalankan YOLO deteksi
        results = detect_license_plate(str(upload_path))
        detection = get_best_detection(results)

        if detection is None:
            return error_response("Plat nomor tidak terdeteksi pada gambar.")

        # 6. Crop area plat dengan padding
        box = detection["box"]
        confidence_yolo = round(detection["confidence"], 2)
        plate_crop = crop_plate_with_padding(image, box, padding_ratio=0.1)

        if plate_crop is None or plate_crop.size == 0:
            return error_response("Gagal melakukan crop area plat")

        # 7. Jalankan OCR multi-preprocessing
        ocr_result = read_plate_with_multi_ocr(plate_crop)
        raw_ocr = ocr_result.get("raw", "")
        formatted_plate = ocr_result.get("formatted", "")
        ocr_score = ocr_result.get("score", 0)
        ocr_version = ocr_result.get("version", "none")

        if not raw_ocr:
            return error_response("OCR gagal membaca teks plat nomor")

        # 8. Normalisasi plate key untuk database lookup
        plate_key = normalize_plate_key(raw_ocr)

        # 9. Cek database kendaraan
        vehicle_info = find_vehicle_by_plate(plate_key)

        # 9b. Fetch data pajak dari API eksternal (Graceful handling jika belum di-whitelist)
        pajak_data = None
        if formatted_plate:
            try:
                encoded_plate = urllib.parse.quote(formatted_plate.lower())
                pajak_url = f"https://api.ryzumi.net/api/tool/cek-pajak/jabar?plat={encoded_plate}"
                async with httpx.AsyncClient() as client:
                    # Timeout 5 detik agar tidak menghambat response jika request diblokir/lambat
                    response = await client.get(pajak_url, timeout=5.0)
                    if response.status_code == 200:
                        res_json = response.json()
                        if res_json.get("success"):
                            pajak_data = res_json.get("data")
                        else:
                            print(f"[WARN] API Cek Pajak sukses=false: {res_json.get('message')}")
                    else:
                        print(f"[WARN] API Cek Pajak HTTP Error: {response.status_code}")
            except Exception as e:
                print(f"[ERROR] Gagal memproses API Cek Pajak: {str(e)}")

        # 10. Gambar bounding box dan label pada gambar asli
        label = f"{formatted_plate} ({confidence_yolo:.0%})"
        result_image = draw_detection_result(image, box, label)

        # 11. Simpan gambar hasil ke results/
        base_name = upload_filename.replace("upload_", "")
        result_filename = f"result_{base_name}"
        crop_filename = f"crop_{base_name}"

        result_path = RESULT_DIR / result_filename
        crop_path = RESULT_DIR / crop_filename

        cv2.imwrite(str(result_path), result_image)
        cv2.imwrite(str(crop_path), plate_crop)

        # 12. Simpan riwayat deteksi
        history_record = {
            "nama_file": file.filename,
            "plate": formatted_plate,
            "plate_key": plate_key,
            "raw_ocr": raw_ocr,
            "status": vehicle_info["status"],
            "owner_name": vehicle_info["owner_name"],
            "vehicle_type": vehicle_info["vehicle_type"],
            "description": vehicle_info["description"],
            "confidence_yolo": confidence_yolo,
            "ocr_score": ocr_score,
            "ocr_version": ocr_version,
            "result_image": result_filename,
            "plate_crop": crop_filename,
        }
        save_detection_history(history_record)

        # 13. Return JSON response
        return success_response("Deteksi berhasil", {
            "plate": formatted_plate,
            "plate_key": plate_key,
            "raw_ocr": raw_ocr,
            "status": vehicle_info["status"],
            "owner_name": vehicle_info["owner_name"],
            "vehicle_type": vehicle_info["vehicle_type"],
            "description": vehicle_info["description"],
            "confidence_yolo": confidence_yolo,
            "ocr_score": ocr_score,
            "ocr_version": ocr_version,
            "result_image_url": f"/static/results/{result_filename}",
            "plate_crop_url": f"/static/results/{crop_filename}",
            "foto_pemilik_url": f"/static/photos/{vehicle_info['foto_pemilik']}" if vehicle_info.get('foto_pemilik') else "",
            "data_pajak": pajak_data
        })

    except Exception as e:
        # Log error untuk debugging, tapi jangan kirim stacktrace ke frontend
        print(f"[ERROR] /api/detect: {traceback.format_exc()}")
        return error_response(f"Terjadi kesalahan saat memproses gambar: {str(e)}")


# ── GET /api/vehicles ───────────────────────────────────────────────────────

@app.get("/api/vehicles")
async def get_vehicles():
    """Mengambil daftar semua kendaraan dari database CSV."""
    try:
        vehicles = load_vehicles()
        return success_response("Data kendaraan berhasil dimuat", vehicles)
    except Exception as e:
        return error_response(f"Gagal membaca data kendaraan: {str(e)}")


# ── POST /api/vehicles ──────────────────────────────────────────────────────

@app.post("/api/vehicles")
async def create_vehicle(
    plat: str = Form(...),
    nama_pemilik: str = Form(...),
    jenis_kendaraan: str = Form("-"),
    keterangan: str = Form("-"),
    foto: UploadFile = File(None),
):
    """Menambahkan data kendaraan baru ke database CSV, dengan opsional foto pemilik."""
    try:
        foto_filename = ""
        if foto and foto.filename:
            ext = Path(foto.filename).suffix.lower()
            if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
                return error_response("Foto harus berupa JPG, PNG, atau WEBP")
            from app.utils import generate_unique_filename
            foto_filename = generate_unique_filename(foto.filename, prefix="owner")
            foto_path = PHOTOS_DIR / foto_filename
            content = await foto.read()
            with open(foto_path, "wb") as f:
                f.write(content)

        data = {
            "plat": plat,
            "nama_pemilik": nama_pemilik,
            "jenis_kendaraan": jenis_kendaraan,
            "keterangan": keterangan,
            "foto_pemilik": foto_filename,
        }
        result = add_vehicle(data)
        return success_response("Data kendaraan berhasil ditambahkan", result)
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        return error_response(f"Gagal menambahkan data kendaraan: {str(e)}")


# ── PUT /api/vehicles/{plat} ────────────────────────────────────────────────

@app.put("/api/vehicles/{plat}")
async def update_vehicle_endpoint(plat: str, vehicle: VehicleUpdateInput):
    """Update data kendaraan berdasarkan plat."""
    try:
        result = update_vehicle(plat, vehicle.model_dump())
        return success_response("Data kendaraan berhasil diperbarui", result)
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        return error_response(f"Gagal memperbarui data kendaraan: {str(e)}")


# ── DELETE /api/vehicles/{plat} ─────────────────────────────────────────────

@app.delete("/api/vehicles/{plat}")
async def delete_vehicle_endpoint(plat: str):
    """Hapus data kendaraan berdasarkan plat."""
    try:
        result = delete_vehicle(plat)
        return success_response("Data kendaraan berhasil dihapus", result)
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        return error_response(f"Gagal menghapus data kendaraan: {str(e)}")


# ── GET /api/history ────────────────────────────────────────────────────────

@app.get("/api/history")
async def get_history():
    """Mengambil riwayat deteksi dari CSV."""
    try:
        history = get_detection_history(limit=50)
        return success_response("Riwayat deteksi berhasil dimuat", history)
    except Exception as e:
        return error_response(f"Gagal membaca riwayat deteksi: {str(e)}")


# ── DELETE /api/history/{index} ─────────────────────────────────────────────

@app.delete("/api/history/{index}")
async def delete_history(index: int):
    """Hapus satu record riwayat berdasarkan index."""
    try:
        result = delete_history_record(index)
        return success_response("Riwayat berhasil dihapus", result)
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        return error_response(f"Gagal menghapus riwayat: {str(e)}")


# ── DELETE /api/history ─────────────────────────────────────────────────────

@app.delete("/api/history")
async def clear_history():
    """Hapus seluruh riwayat deteksi."""
    try:
        result = clear_all_history()
        return success_response("Seluruh riwayat berhasil dihapus", result)
    except Exception as e:
        return error_response(f"Gagal menghapus riwayat: {str(e)}")

# ── SPA Fallback ────────────────────────────────────────────────────────────
# Catch-all route untuk SPA client-side routing (harus di paling bawah)
# PENTING: Di FastAPI, routes diproses SEBELUM mounts.
# Jadi static files harus di-serve langsung dari sini.

@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    """Fallback: serve static files, lalu SPA index.html."""
    # 1. Serve result images: /static/results/xxx.jpg
    if full_path.startswith("static/results/"):
        file_name = full_path.replace("static/results/", "", 1)
        file_path = RESULT_DIR / file_name
        if file_path.is_file():
            return FileResponse(str(file_path))

    # 2. Serve upload images: /static/uploads/xxx.jpg
    if full_path.startswith("static/uploads/"):
        file_name = full_path.replace("static/uploads/", "", 1)
        file_path = UPLOAD_DIR / file_name
        if file_path.is_file():
            return FileResponse(str(file_path))

    # 3. Serve owner photos: /static/photos/xxx.jpg
    if full_path.startswith("static/photos/"):
        file_name = full_path.replace("static/photos/", "", 1)
        file_path = PHOTOS_DIR / file_name
        if file_path.is_file():
            return FileResponse(str(file_path))

    # 4. Jangan intercept API paths
    if full_path.startswith("api/"):
        return {"detail": "Not found"}

    # 4. SPA fallback: serve frontend build
    if FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIST / "index.html"))

    return {"detail": "Not found"}
