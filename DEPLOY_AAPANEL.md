# Panduan Deployment FastAPI di aaPanel

Dokumen ini berisi panduan langkah-demi-langkah untuk mendeploy backend **FastAPI PlatDetect** ke server menggunakan **aaPanel**.

---

## Prasyarat
1. Server VPS dengan **aaPanel** terinstal (direkomendasikan menggunakan sistem operasi Ubuntu/Debian).
2. Modul **Python Manager** (atau menu **Python Project** pada versi aaPanel terbaru) telah terinstal melalui App Store aaPanel.

---

## Langkah 1: Unggah File Backend
1. Kompres folder `backend` proyek Anda menjadi file `.zip` (tanpa menyertakan folder virtual environment `venv` lokal jika ada).
2. Buka menu **Files** di aaPanel.
3. Masuk ke direktori web Anda, misalnya `/www/wwwroot/`.
4. Buat folder baru (misal `/www/wwwroot/plat-detect-backend`).
5. Unggah file `.zip` tadi, lalu ekstrak di dalam folder tersebut. Pastikan struktur foldernya adalah:
   ```text
   /www/wwwroot/plat-detect-backend/
   ├── app/
   │   ├── main.py
   │   ├── config.py
   │   └── ...
   ├── models/
   │   └── best.pt
   ├── data/
   │   ├── kendaraan.csv
   │   └── riwayat_deteksi.csv
   ├── requirements.txt
   ├── .gitignore
   └── README.md
   ```

---

## Langkah 2: Setup Proyek di aaPanel Python Project
1. Buka dashboard **aaPanel**.
2. Masuk ke menu **Website** -> pilih tab **Python Project** (atau buka melalui **Python Manager** jika Anda menggunakan plugin manager terpisah).
3. Klik tombol **Add Project**.
4. Isi form pengaturan proyek sebagai berikut:
   *   **Project Name:** `plat-detect-backend` (atau sesuaikan keinginan Anda)
   *   **Project Path:** Pilih direktori tempat file diekstrak, yaitu `/www/wwwroot/plat-detect-backend`
   *   **Python Version:** Pilih versi Python yang sesuai (disarankan Python **3.10.x** ke atas). Jika belum ada, Anda bisa menginstal versi Python terlebih dahulu melalui tombol *Python Version* di Python Manager.
   *   **Framework:** Pilih **FastAPI** (atau pilih **Other** jika tidak ada).
   *   **Startup Mode / Web Server:** 
       > [!IMPORTANT]
       > **FastAPI** adalah framework ASGI (Asynchronous). Oleh karena itu, **uWSGI TIDAK BISA digunakan**. Anda harus memilih salah satu dari opsi berikut:
       > 
       > **Pilihan A: Gunicorn (Sangat Direkomendasikan)**
       > - Pilih **gunicorn** sebagai Startup Mode.
       > - Pada konfigurasi Gunicorn, aaPanel akan mengizinkan Anda memasukkan target app. Isi dengan `app.main:app`.
       > - Pastikan Anda memasukkan parameter worker class uvicorn di konfigurasi argumennya: `-k uvicorn.workers.UvicornWorker` agar Gunicorn dapat menjalankan aplikasi ASGI FastAPI.
       > 
       > **Pilihan B: Custom Startup Command (Uvicorn Langsung)**
       > - Pilih **Custom / Command** sebagai Startup Mode.
       > - Masukkan perintah startup langsung menunjuk ke virtual environment yang dibuat aaPanel, contoh:
       >   `/www/server/pyporject_evn/plat-detect-backend_venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4`
       >   *(Sesuaikan path folder venv Anda)*.
   *   **Startup File/Entry Point:** Isi dengan `app/main.py`.
   *   **Run command / Target App:** Isi dengan `app:app` (atau `app.main:app` tergantung format form aaPanel Anda).
   *   **Port:** Masukkan port yang ingin Anda gunakan (misal: `8000`).
   *   **Execution Environment:** Pastikan opsi **virtualenv** dicentang agar dependencies terisolasi.
   *   **Autostart on boot:** Centang agar backend otomatis menyala saat server reboot.
5. Klik **Submit**. aaPanel akan membuat proyek beserta virtual environment baru secara otomatis.

---

## Langkah 3: Instalasi Dependencies (Requirements)
1. Setelah proyek berhasil ditambahkan, temukan proyek Anda di daftar proyek.
2. Klik opsi **pip** atau **Manage Dependencies** di sebelah kanan baris proyek Anda.
3. Klik **Install from requirements.txt**, lalu pilih file `requirements.txt` yang berada di dalam folder proyek Anda.
4. Tunggu beberapa menit hingga aaPanel selesai menginstal paket-paket penting seperti `ultralytics` (YOLO), `easyocr`, `fastapi`, `opencv-python-headless`, dll.
   > [!NOTE]
   > Instalasi `easyocr` and `ultralytics` membutuhkan waktu sedikit lebih lama karena mendownload modul-modul machine learning serta dependencies pendukung.

---

## Langkah 4: Mapping Domain (Reverse Proxy)
Agar API backend dapat diakses secara publik menggunakan nama domain (misal: `api.platdetect.com`), Anda perlu melakukan mapping domain:
1. Pada daftar proyek Python di aaPanel, klik tombol **Web service / Map** di samping kanan nama proyek Anda.
2. Masukkan nama domain yang ingin Anda gunakan (misal: `api.platdetect.com`).
3. aaPanel akan secara otomatis membuat konfigurasi website Nginx baru yang bertindak sebagai *reverse proxy*, yang meneruskan request dari domain tersebut secara internal ke port `8000` (atau port yang Anda atur).
4. Jika Anda menggunakan HTTPS, Anda bisa masuk ke menu **Website** -> **PHP Project / HTML Project**, temukan domain yang baru saja di-map, lalu pasang SSL (Let's Encrypt) seperti biasa.

---

## Langkah 5: Penyesuaian Hak Akses Folder (Permission)
FastAPI membutuhkan hak akses tulis (*write permission*) untuk menyimpan gambar upload, hasil deteksi, dan database CSV.
1. Masuk ke menu **Files** di aaPanel.
2. Navigasikan ke `/www/wwwroot/plat-detect-backend`.
3. Pastikan folder-folder berikut memiliki owner `www` (atau user yang menjalankan python service) dan memiliki permission `755` atau `777`:
   *   `data/` (beserta isinya)
   *   `uploads/` (akan dibuat otomatis oleh aplikasi, jika tidak buat manual)
   *   `results/` (akan dibuat otomatis oleh aplikasi, jika tidak buat manual)
   *   `photos/` (akan dibuat otomatis oleh aplikasi, jika tidak buat manual)
