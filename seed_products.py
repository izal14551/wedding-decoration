from app import create_app, db
from app.models import Kategori, Barang

app = create_app()

with app.app_context():
    # Pastikan Kategori "Package" ada
    category_name = "Package"
    kategori = Kategori.query.filter_by(nama_kategori=category_name).first()
    if not kategori:
        kategori = Kategori(
            nama_kategori=category_name,
            deskripsi="Paket dekorasi pernikahan lengkap"
        )
        db.session.add(kategori)
        db.session.flush() # Mendapatkan kategori_id sebelum commit
        print(f"Kategori '{category_name}' berhasil ditambahkan.")
    
    # Daftar paket dekorasi pernikahan sesuai mockup
    packages = [
        {
            "name": "Silver Package",
            "price_per_day": 12200000.0,
            "description": "Paket dekorasi pernikahan silver yang mencakup rias pengantin (1x ganti), rias orang tua, penerima tamu, tarub, dokumentasi foto, aksesoris, dekorasi kamar, henna, dan MC.",
            "stock": 10
        },
        {
            "name": "Gold Package",
            "price_per_day": 15300000.0,
            "description": "Paket dekorasi pernikahan gold yang lengkap dengan rias pengantin (3x ganti), rias orang tua, penerima tamu, pagar ayu, manggolo, tarub premium, foto, aksesoris melati asli, kamar, henna, MC, tari pengiring, sound system, dan kursi futura.",
            "stock": 10
        },
        {
            "name": "Platinum Package",
            "price_per_day": 17400000.0,
            "description": "Paket dekorasi pernikahan platinum super mewah dengan rias pengantin (3x ganti), keluarga lengkap, tarub besar, foto cetak magnetik, organ tunggal & singer, dekorasi kamar premium, henna putih, tari panggih adat, free makeup pre-wedding, dan karpet merah.",
            "stock": 10
        }
    ]

    for pkg_data in packages:
        existing_barang = Barang.query.filter_by(nama_barang=pkg_data["name"]).first()
        if not existing_barang:
            barang = Barang(
                kategori_id=kategori.kategori_id,
                nama_barang=pkg_data["name"],
                harga=pkg_data["price_per_day"],
                deskripsi=pkg_data["description"],
                stok=pkg_data["stock"],
                status="Aktif"
            )
            db.session.add(barang)
            print(f"Barang '{pkg_data['name']}' berhasil ditambahkan.")
        else:
            # Update harga jika ada perubahan
            existing_barang.harga = pkg_data["price_per_day"]
            existing_barang.deskripsi = pkg_data["description"]
            print(f"Barang '{pkg_data['name']}' sudah ada. Memperbarui informasi.")

    db.session.commit()
    print("Seeding paket pernikahan selesai!")

