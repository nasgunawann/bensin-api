# Bensin-API (Static Generator)

[![Sync Pertamina Prices](https://github.com/nasgunawann/bensin-api/actions/workflows/sync.yml/badge.svg)](https://github.com/nasgunawann/bensin-api/actions/workflows/sync.yml)

Repository ini menyajikan API publik harga bahan bakar Pertamina di seluruh Indonesia yang bersih, terstandar, ringan, dan gratis. Data diperbarui otomatis setiap jam langsung dari hulu dan disajikan sebagai berkas JSON statis yang dihosting di GitHub Pages.

---

## Quick Start: Cara Menggunakan API

### Base URL:
```
https://nasgunawann.github.io/bensin-api
```

### Contoh Penggunaan Instan (JavaScript)

Berikut adalah contoh cara mengambil data harga bahan bakar Pertamina untuk wilayah **DKI Jakarta** (`dki-jakarta`):

```javascript
const baseUrl = 'https://nasgunawann.github.io/bensin-api';
const provinceSlug = 'dki-jakarta'; // ganti sesuai slug provinsi yang diinginkan

fetch(`${baseUrl}/v1/provinsi/${provinceSlug}.json`)
  .then(response => {
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    console.log(`Wilayah: ${data.province}`);
    console.log(`Terakhir Diperbarui Pertamina: ${data.pertamina_updated_at}`);
    
    data.products.forEach(prod => {
      const priceFormatted = prod.price_rupiah 
        ? `Rp ${prod.price_rupiah.toLocaleString('id-ID')}`
        : 'Tidak Tersedia';
        
      console.log(`- ${prod.product}: ${priceFormatted} (${prod.availability})`);
    });
  })
  .catch(error => {
    console.error('Gagal mengambil data:', error);
  });
```

---

## Detail Struktur Kontrak: Upstream vs Ternormalisasi

API resmi dari MyPertamina `https://api.web.mypertamina.id/price` memiliki banyak inkonsistensi data. Berikut adalah perbedaan data dari upstream vs data dari Bensin-API:

### 1. Data Regional per Provinsi (`/v1/provinsi/{slug}.json`)

*   **Contoh URL:** `https://nasgunawann.github.io/bensin-api/v1/provinsi/aceh.json`

#### Before (Respon Mentah Upstream Pertamina)
Payload dari Pertamina berukuran besar karena menulis stempel waktu yang sama berulang kali di setiap baris, tidak konsisten dalam tipe harga, serta nama produk yang acak-acakan:
```json
{
  "province": "Prov. Aceh",
  "list_price": [
    {
      "product": "PERTAMINA BIOSOLAR SUBSIDI",
      "price": "Rp 6.800",
      "updatedDate": "2026-06-01T15:59:37.000Z"
    },
    {
      "product": "PERTAMAX GREEN 95",
      "price": "0",
      "updatedDate": "2026-06-01T15:59:37.000Z"
    },
    {
      "product": "PERTAMAX",
      "price": "12600",
      "updatedDate": "2026-06-01T15:59:37.000Z"
    }
  ]
}
```

#### After (Respon Ternormalisasi Bensin-API)
Data dibersihkan menjadi sangat ringkas (~43.5% ukuran file lebih kecil), harga dikonversi menjadi integer murni supaya konsisten, dan stempel waktu redundan dihilangkan:
```json
{
  "province": "Prov. Aceh",
  "province_slug": "aceh",
  "pertamina_updated_at": "2026-06-01T15:59:37.000Z",
  "synced_at": "2026-06-01T11:48:24Z",
  "products": [
    {
      "product": "BIOSOLAR",
      "price_rupiah": 6800,
      "availability": "available"
    },
    {
      "product": "PERTAMAX GREEN 95",
      "price_rupiah": null,
      "availability": "unavailable"
    },
    {
      "product": "PERTAMAX",
      "price_rupiah": 12600,
      "availability": "available"
    }
  ]
}
```

---

### 2. Katalog Indeks Utama (`/v1/index.json`)

*   **Contoh URL:** `https://nasgunawann.github.io/bensin-api/v1/index.json`

#### Before (Respon Mentah Upstream Pertamina)
Data upstream tidak menyediakan indeks. Pengguna dipaksa mengunduh satu payload berisi seluruh harga 34+ provinsi sekaligus meskipun hanya membutuhkan data dari satu daerah saja.

#### After (Respon Ternormalisasi Bensin-API)
Menyajikan daftar ringkas semua provinsi beserta tautan path-nya, ukuran berkas masing-masing, dan jumlah produk aktif. Developer dapat mengunduh katalog ringan ini untuk memetakan rute navigasi aplikasi:
```json
{
  "api_name": "Indonesia Fuel Price API",
  "version": "v1",
  "author": "Nasrullah Gunawan",
  "github_repository": "https://github.com/nasgunawann/bensin-api",
  "synced_at": "2026-06-01T11:48:24Z",
  "pertamina_updated_at": "2026-06-01T15:59:37.000Z",
  "provinsi_count": 40,
  "provinsi": {
    "aceh": {
      "name": "Prov. Aceh",
      "slug": "aceh",
      "path": "/v1/provinsi/aceh.json",
      "pertamina_updated_at": "2026-06-01T15:59:37.000Z",
      "synced_at": "2026-06-01T11:48:24Z",
      "products_count": 9,
      "file_size_bytes": 1245
    }
  },
  "endpoints": {
    "all_provinces": "/v1/nasional.json"
  }
}
```

---

### 3. Data Nasional Lengkap (`/v1/nasional.json`)

*   **Contoh URL:** `https://nasgunawann.github.io/bensin-api/v1/nasional.json`

Sangat efisien untuk seeding seluruh data harga BBM nasional ke database lokal atau dashboard perbandingan dalam **satu kali HTTP request**. Berisi daftar seluruh provinsi lengkap dengan array produk bahan bakarnya.
*   **Struktur Response:**
    ```json
    {
      "version": "v1",
      "synced_at": "2026-06-01T12:01:51Z",
      "pertamina_updated_at": "2026-06-01T15:59:37.000Z",
      "provinces": [
        {
          "province": "Prov. Aceh",
          "province_slug": "aceh",
          "pertamina_updated_at": "2026-06-01T15:59:37.000Z",
          "synced_at": "2026-06-01T12:01:51Z",
          "products": [
            {
              "product": "DEXLITE",
              "price_rupiah": 23500,
              "availability": "available"
            },
            {
              "product": "PERTALITE",
              "price_rupiah": 10000,
              "availability": "available"
            }
          ]
        }
      ]
    }
    ```

---

## 🛠️ Panduan Pengembangan & Kontribusi

Ikuti langkah-langkah di bawah ini untuk menjalankan atau menguji proyek secara lokal:

### 1. Setup Virtual Environment (Windows PowerShell)
```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
```

### 2. Instalasi Dependensi
```powershell
pip install -r requirements.txt
```

### 3. Menjalankan Generator
Untuk memproses berkas lokal `price.json` dan menghasilkan berkas `v1/`:
```powershell
python src/fetch_normalize.py
```

Untuk mengambil data terbaru langsung dari API hulu Pertamina (*live fetch*) sebelum melakukan regenerasi:
```powershell
python src/fetch_normalize.py --fetch
```

### 4. Menjalankan Unit Pengujian (*Tests*)
```powershell
.venv/Scripts/python -m pytest -v
```

---

## Alur Kontribusi & CI/CD (Pull Request Workflow)

Proyek ini menggunakan alur pembaruan terjadwal:
1. **GitHub Actions** berjalan secara otomatis setiap jam (sesuai penjadwalan cron job).
2. Bot mengambil data dari API MyPertamina, melakukan normalisasi data, lalu memvalidasi struktur data.
3. Bot tidak langsung melakukan push ke branch `main`. Bot akan membuat branch baru `sync/update-snapshots` dan membuka Pull Request otomatis untuk mencegah conflict.
