# Daftar Urutan Tugas Pengembangan (Roadmap & Tasks)

Dokumen ini berisi urutan langkah pengembangan sistem penyewaan dekorasi pernikahan (_Wedding Decoration Rental System_) yang disusun secara sistematis berdasarkan modul-modul pada Product Requirements Document (PRD).

---

## 📅 Fase 1: Autentikasi & Manajemen Pengguna (Dasar Sistem)

Fokus pada pembuatan akun, hak akses multi-role (Pelanggan & Admin), dan manajemen profil.

- [x] **1.1 Desain Ulang Model Database**
  - Migrasi tabel database sesuai ERD terbaru (Pelanggan, Admin, Kategori, Barang, Pesanan, DetailPesanan, Pembayaran, Laporan, Jadwal).
- [x] **1.2 Halaman & Fitur Login Multi-Role**
  - Penyesuaian `load_user` Flask-Login menggunakan prefix ID (`admin_{id}` dan `pelanggan_{id}`).
  - Implementasi tampilan halaman login dengan desain Glassmorphism + Tailwind CSS.
- [x] **1.3 Fitur Registrasi Pelanggan**
  - Validasi input registrasi (nama, email unik, password, nomor HP, alamat).
  - Enkripsi password menggunakan bcrypt hashing (`generate_password_hash`).
- [x] **1.4 Fitur Kelola Profil (Pelanggan)**
  - Pelanggan dapat mengubah data profil mereka (nama, nomor HP, alamat, password).
- [x] **1.5 Manajemen Pengguna (Admin)**
  - Halaman admin untuk melihat daftar pelanggan terdaftar.
  - Fitur untuk menonaktifkan akun pelanggan atau menghapus akun.

---

## 📦 Fase 2: Manajemen Kategori & Barang Dekorasi

Fokus pada manajemen inventaris dekorasi yang disewakan oleh Admin dan tampilannya di sisi pelanggan.

- [x] **2.1 Modul CRUD Kategori (Admin)**
  - Fitur tambah kategori dekorasi dan makeup (contoh: Tenda, Kursi, Panggung, Bunga).
  - Fitur edit dan hapus kategori dekorasi.
- [x] **2.2 Modul CRUD Barang (Admin)**
  - Fitur tambah barang baru (mengaitkan kategori, mengisi nama, harga sewa per hari, stok awal/kapasitas slot harian untuk jasa, deskripsi lengkap, upload foto barang).
  - Fitur edit informasi barang dan hapus barang.
  - Pembeda perlakuan stok (Kuantitas fisik untuk alat dekor, Kapasitas slot harian untuk jasa/makeup).
- [x] **2.3 Katalog (Pelanggan)**
  - Halaman beranda untuk menampilkan daftar dekorasi aktif berdasarkan kategori (tab filter).
  - Fitur pencarian barang dan filter berdasarkan kategori.
- [x] **2.4 Detail Barang (Pelanggan)**
  - Halaman detail untuk setiap barang/jasa dekorasi (menampilkan foto, deskripsi lengkap, harga, sisa stok/kapasitas slot harian, dan kalender status ketersediaan).

---

## 🛒 Fase 3: Keranjang Belanja & Validasi Jadwal

Menjembatani pemilihan barang hingga persiapan sebelum pemesanan tanpa ada jadwal bentrok.

- [x] **3.1 Fitur Keranjang Belanja (Add to Cart)**
  - Menyimpan barang pilihan pelanggan ke dalam session cart atau tabel database sementara.
  - Validasi kuantitas sewa agar tidak melebihi stok barang yang tersedia.
- [x] **3.2 Manajemen Keranjang Belanja**
  - Halaman keranjang untuk meninjau barang yang dipilih.
  - Fitur ubah kuantitas (tambah/kurang) barang dan hapus item dari keranjang.
  - Perhitungan total harga sementara secara otomatis.
- [x] **3.3 Sistem Validasi Jadwal Penyewaan**
  - Validasi tanggal sewa saat barang dimasukkan ke keranjang/checkout.
  - Sistem memeriksa tabel `jadwal` untuk mendeteksi apakah barang tersebut sudah disewa oleh pelanggan lain pada tanggal yang sama untuk menghindari _double booking_.

---

## 📝 Fase 4: Checkout & Manajemen Pesanan

Proses penyewaan resmi dari keranjang belanja menjadi pesanan yang tercatat dalam sistem.

- [x] **4.1 Fitur Checkout Pesanan (Pelanggan)**
  - Pelanggan menentukan tanggal sewa (mulai s/d selesai), jam acara, alamat lengkap pengiriman dekorasi, dan catatan tambahan.
  - Sistem membuat data transaksi baru di tabel `pesanan` dan rincian barang di `detail_pesanan`.
  - Sistem secara otomatis mengisi tabel `jadwal` dengan status `Disewa` untuk barang terkait pada rentang tanggal sewa tersebut.
- [x] **4.2 Invoice & Riwayat Pesanan (Pelanggan)**
  - Tampilan halaman riwayat pesanan pelanggan beserta status transaksinya.
  - Halaman rincian invoice pemesanan sementara dengan status "Menunggu Pembayaran".
- [x] **4.3 Manajemen Pesanan (Admin)**
  - Dashboard admin untuk memantau semua pesanan masuk.
  - Fitur bagi admin untuk mengubah status pesanan (Waiting for payment, Processing, Completed, Cancelled).

---

## 💳 Fase 5: Pembayaran & Verifikasi Admin

Proses pelunasan sewa dekorasi dan verifikasi keabsahan pembayaran oleh administrator.

- [x] **5.1 Upload Bukti Pembayaran (Pelanggan)**
  - Pelanggan mengunggah foto/file bukti transfer pembayaran untuk pesanan tertentu.
  - Status pesanan berubah menjadi "Pending Verification" (Menunggu Verifikasi).
- [x] **5.2 Verifikasi Pembayaran (Admin)**
  - Admin meninjau bukti transfer yang diunggah pelanggan.
  - Admin dapat menyetujui (Approve) atau menolak (Reject) pembayaran.
  - Persetujuan pembayaran akan otomatis mengubah status pesanan menjadi "Processing" (Diproses/Disiapkan).

---

## 📊 Laporan & Output Sistem

Fase final untuk pelaporan administrasi bisnis dan pencetakan dokumen resmi.

- [x] **6.1 Ekspor Invoice Resmi (PDF)**
  - Sistem menghasilkan berkas PDF Invoice resmi yang dapat diunduh oleh pelanggan setelah pembayaran berhasil diverifikasi.
- [x] **6.2 Laporan Keuangan & Statistik (Admin)**
  - Halaman laporan berisi visualisasi total pendapatan, total pesanan, barang terlaris, dan statistik lainnya.
  - Fitur filter laporan berdasarkan periode (harian, mingguan, bulanan, tahunan).
- [x] **6.3 Ekspor Laporan Transaksi**
  - Fitur bagi admin untuk mengunduh laporan transaksi dalam format PDF atau Excel (`OpenPyXL`/`Pandas`).

---

## 📅 Fase 7: Manajemen Jadwal & Pemeliharaan (Admin)

Modul manajemen jadwal bagi admin untuk mengendalikan ketersediaan barang dekorasi.

- [x] **7.1 Manajemen Jadwal & Pemeliharaan (Admin)**
  - Halaman untuk memantau detail status penyewaan barang per tanggal.
  - Fitur untuk menentukan jadwal pemeliharaan (Maintenance) barang yang otomatis mencegah penyewaan (double booking) oleh pelanggan.
  - Kalender ketersediaan detail produk menampilkan status "Perawatan" (Maintenance) secara absolut jika produk dijadwalkan untuk pemeliharaan.
  - Proses checkout memblokir pesanan secara otomatis dengan flash message kustom jika produk dalam masa pemeliharaan pada tanggal acara.
  - Halaman keranjang belanja menampilkan tab kalender ketersediaan dinamis untuk tiap barang yang ada di keranjang.
  - Form checkout di keranjang belanja melakukan validasi AJAX real-time untuk memblokir tombol checkout jika kuantitas melebihi stok tersedia atau bertabrakan dengan jadwal perawatan (Maintenance).
  - Mengintegrasikan Modal Widget Kalender interaktif saat input tanggal sewa diklik, menonaktifkan pemilihan tanggal perawatan/penuh secara absolut, dan mengisi form input tanggal secara otomatis.
  - Menyempurnakan responsivitas kalender di handphone (mobile) dengan meniadakan scroll horizontal, memperkecil sel hari, dan menampilkan indikator status berbentuk dot warna minimalis.
  - Memperlebar tata letak Modal Widget Kalender di desktop/tablet menjadi Extra Large (modal-xl) demi kenyamanan navigasi tanggal sewa.
