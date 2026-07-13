"""
detector.py — Load dan jalankan model YOLO best.pt untuk deteksi plat nomor.
Model di-load sekali saat startup dan di-reuse untuk semua request.
"""

from app.config import MODEL_PATH, YOLO_CONFIDENCE

# ── Singleton YOLO Model ───────────────────────────────────────────────────
_model = None


def load_model():
    """
    Load model YOLO dari file best.pt.
    Menggunakan singleton pattern agar model hanya di-load sekali.
    """
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model YOLO tidak ditemukan di {MODEL_PATH}. "
                "Pastikan file best.pt sudah ada di folder backend/models/"
            )
        from ultralytics import YOLO
        _model = YOLO(str(MODEL_PATH))
    return _model


def is_model_loaded() -> bool:
    """Cek apakah model sudah ter-load."""
    return _model is not None


def detect_license_plate(image_path: str, conf: float = YOLO_CONFIDENCE) -> list:
    """
    Menjalankan deteksi plat nomor pada gambar menggunakan YOLO.
    
    Args:
        image_path: Path ke file gambar
        conf: Minimum confidence threshold
    
    Returns:
        list: Hasil deteksi YOLO (list of Results objects)
    """
    model = load_model()
    results = model.predict(source=image_path, conf=conf, verbose=False)
    return results


def get_best_detection(results) -> dict | None:
    """
    Mengambil deteksi dengan confidence tertinggi dari hasil YOLO.
    
    Args:
        results: Hasil dari model.predict()
    
    Returns:
        dict dengan keys: box (xyxy), confidence, class_id
        None jika tidak ada deteksi
    """
    best = None
    best_conf = 0.0

    for result in results:
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            continue

        for i in range(len(boxes)):
            conf = float(boxes.conf[i])
            if conf > best_conf:
                best_conf = conf
                best = {
                    "box": boxes.xyxy[i].cpu().numpy(),  # [x1, y1, x2, y2]
                    "confidence": conf,
                    "class_id": int(boxes.cls[i]),
                }

    return best
