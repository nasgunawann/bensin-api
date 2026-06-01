# Bensin-API

Generator otomatis yang menormalkan payload harga BBM Pertamina yang tidak konsisten menjadi JSON static yang bersih, terstandar, dan siap pakai.

---

## Data dari MyPertamina vs Struktur Data Ternormalisasi

API upstream dari MyPertamina `https://api.web.mypertamina.id/price` punya beberapa inkonsistensi data yang menyulitkan developer untuk langsung memakai. Berikut adalah perbandingannya:

### 1. Perbandingan Skema Data Produk

| Aspek                  | Struktur Mentah Pertamina                                                                                                          | Struktur Ternormalisasi Bensin-API                                                                        |
| :--------------------- | :--------------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------- |
| **Tipe Data Harga**    | `string` (Campuran format)                                                                                                         | `integer` (atau `null` jika tidak tersedia)                                                               |
| **Format Harga**       | Tidak konsisten, contoh:<br>- `"23500"` (angka murni)<br>- `"Rp 10.000"` (rupiah dengan titik)<br>- `"0"` (berarti tidak tersedia) | Pembersihan otomatis:<br>- `23500` (integer)<br>- `10000` (integer)<br>- `null` (dianggap tidak tersedia) |
| **Ketersediaan**       | Tidak ada field status khusus. Ditandakan secara implisit jika harga `"0"`.                                                        | `availability`: `"available"` / `"unavailable"` / `"unknown"`                                             |
| **Standardisasi Nama** | Tidak konsisten antar wilayah, contoh:<br>- `PERTAMINA BIOSOLAR SUBSIDI`<br>- `BIO SOLAR`                                          | `product_canonical`: Nama produk seragam (misal: `BIOSOLAR`, `PERTAMINA DEX`).                            |

### 2. Contoh Perbandingan Payload JSON

#### Sebelum Normalisasi (Raw Pertamina Payload):

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
    }
  ]
}
```

#### Setelah Normalisasi (Bensin-API Payload):

```json
{
  "province": "Prov. Aceh",
  "province_slug": "aceh",
  "pertamina_updated_at": "2026-06-01T15:59:37.000Z",
  "synced_at": "2026-06-01T11:11:11Z",
  "products": [
    {
      "product": "PERTAMINA BIOSOLAR SUBSIDI",
      "product_canonical": "BIOSOLAR",
      "price_rupiah": 6800,
      "availability": "available",
      "pertamina_updated_at": "2026-06-01T15:59:37.000Z"
    },
    {
      "product": "PERTAMAX GREEN 95",
      "product_canonical": "PERTAMAX GREEN 95",
      "price_rupiah": null,
      "availability": "unavailable",
      "pertamina_updated_at": "2026-06-01T15:59:37.000Z"
    }
  ]
}
```

---

## Endpoint API yang Tersedia (Statis)

Karena API ini berbasis file statis (_static-first_), semua data dapat diakses langsung via HTTPS/GET:

### 1. Katalog API Utama (`/v1/index.json`)

Endpoint utama yang memuat metadata generator, tanggal pembaruan global, serta daftar lengkap peta jalan endpoint per provinsi.

- **Struktur Response:**
  ```json
  {
    "api_name": "Indonesia Fuel Price API",
    "version": "v1",
    "author": "Nasrullah Gunawan",
    "github_repository": "https://github.com/nasgunawann/bensin-api",
    "synced_at": "2026-06-01T11:11:11Z",
    "pertamina_updated_at": "2026-06-01T15:59:37.000Z",
    "provinsi_count": 34,
    "provinsi": {
      "aceh": {
        "name": "Prov. Aceh",
        "slug": "aceh",
        "path": "/v1/provinsi/aceh.json",
        "pertamina_updated_at": "2026-06-01T15:59:37.000Z",
        "synced_at": "2026-06-01T11:11:11Z",
        "products_count": 9,
        "file_size_bytes": 2206
      }
    },
    "endpoints": {
      "all_provinces": "/v1/nasional.json",
      "by_province_katalog": {
        "aceh": "/v1/provinsi/aceh.json"
        "bali": "/v1/provinsi/bali.json"
        ...
        "papua-barat-daya": "/v1/provinsi/papua-barat-daya.json"
      }
    }
  }
  ```

### 2. Ringkasan Nasional (`/v1/nasional.json`)

Berisi daftar singkat semua provinsi beserta slug dan path endpoint masing-masing tanpa data harga terperinci. Sangat cocok digunakan untuk memuat daftar pilihan drop-down provinsi di aplikasi Anda secara cepat dan hemat kuota.

- **Struktur Response:**
  ```json
  {
    "version": "v1",
    "synced_at": "2026-06-01T11:11:11Z",
    "pertamina_updated_at": "2026-06-01T15:59:37.000Z",
    "provinces": [
      {
        "province": "Prov. Aceh",
        "province_slug": "aceh",
        "products_count": 9,
        "path": "/v1/provinsi/aceh.json"
      }
    ]
  }
  ```

### 3. Data Per Provinsi (`/v1/provinsi/{slug}.json`)

Menampilkan daftar harga lengkap jenis bahan bakar Pertamina di provinsi tersebut dengan nama produk kanonis terstandar. Ganti `{slug}` dengan nama slug provinsi (contoh: `aceh`, `dki-jakarta`, `jawa-timur`).

- **Struktur Response:** 
 ```json
  {
  "province": "Prov. Aceh",
  "province_slug": "aceh",
  "pertamina_updated_at": "2026-06-01T15:59:37.000Z",
  "synced_at": "2026-06-01T11:11:11.414681Z",
  "products": [
    {
      "product": "DEXLITE",
      "product_canonical": "DEXLITE",
      "price_rupiah": 23500,
      "availability": "available",
      "pertamina_updated_at": "2026-06-01T15:59:37.000Z"
    },
    {
      "product": "PERTALITE",
      "product_canonical": "PERTALITE",
      "price_rupiah": 10000,
      "availability": "available",
      "pertamina_updated_at": "2026-06-01T15:59:37.000Z"
    },
    {
      "product": "PERTAMAX",
      "product_canonical": "PERTAMAX",
      "price_rupiah": 12600,
      "availability": "available",
      "pertamina_updated_at": "2026-06-01T15:59:37.000Z"
    },
...
}
  ```
---

## Cara Run di Lokal?

Ikuti langkah-langkah di bawah ini untuk menjalankan atau menguji proyek secara lokal:

### 1. Setup Virtual Environment (Windows PowerShell)

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
```

### 2. Instalasi Dependensi (Menggunakan `uv` atau `pip`)

```powershell
# Menggunakan uv sebagai alternatif pip yang sangat cepat
uv pip install -r requirements.txt

# Atau menggunakan pip standar
pip install -r requirements.txt
```

### 3. Menjalankan Generator

Untuk memproses berkas lokal `price.json` dan menghasilkan berkas `v1/`:

```powershell
python src/fetch_normalize.py
```

Untuk mengambil data terbaru langsung dari API hulu Pertamina (_live fetch_) sebelum melakukan regenerasi:

```powershell
python src/fetch_normalize.py --fetch
```

### 4. Menjalankan Unit Pengujian (_Tests_)

Untuk memastikan seluruh modul parser dan validasi skema berjalan dengan benar:

```powershell
python -m pytest -v
```
