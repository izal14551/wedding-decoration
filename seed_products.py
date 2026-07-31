from app import create_app, db
from app.models import Kategori, Barang, ProductInclude

app = create_app()

with app.app_context():
    db.create_all()
    # Pastikan Kategori "Package" ada
    category_name = "Package"
    kategori = Kategori.query.filter_by(name=category_name).first()
    if not kategori:
        kategori = Kategori(
            name=category_name,
            description="Paket dekorasi pernikahan lengkap"
        )
        db.session.add(kategori)
        db.session.flush() # Mendapatkan id sebelum commit
        print(f"Kategori '{category_name}' berhasil ditambahkan.")
    
    # Daftar paket dekorasi pernikahan sesuai mockup beserta rincian includes
    packages = [
        {
            "name": "Silver Package",
            "price_per_day": 12200000.0,
            "description": "Paket dekorasi pernikahan silver yang mencakup rias pengantin (1x ganti), rias orang tua, penerima tamu, tarub, dokumentasi foto, aksesoris, dekorasi kamar, henna, dan MC.",
            "stock": 10,
            "includes": [
                {"item_name": "Rias Pengantin (Akad & Resepsi)", "quantity": "1x ganti busana"},
                {"item_name": "Rias Orang Tua (Bapak & Ibu)", "quantity": "2 pasang"},
                {"item_name": "Tarub Dekorasi VIP", "quantity": "1 set (8x12m)"},
                {"item_name": "Pelaminan Bunga Segar Standard", "quantity": "6 meter"},
                {"item_name": "Dokumentasi Foto Album", "quantity": "1 album & flashdisk"},
                {"item_name": "Free Henna Art & Hand Bouquet", "quantity": "1 paket"},
                {"item_name": "MC Pernikahan Professional", "quantity": "1 orang"}
            ]
        },
        {
            "name": "Gold Package",
            "price_per_day": 15300000.0,
            "description": "Paket dekorasi pernikahan gold yang lengkap dengan rias pengantin (3x ganti), rias orang tua, penerima tamu, pagar ayu, manggolo, tarub premium, foto, aksesoris melati asli, kamar, henna, MC, tari pengiring, sound system, dan kursi futura.",
            "stock": 10,
            "includes": [
                {"item_name": "Rias Pengantin (Akad + Resepsi)", "quantity": "3x ganti busana"},
                {"item_name": "Rias Orang Tua & Besan", "quantity": "2 pasang"},
                {"item_name": "Rias Pagar Ayu & Manggolo", "quantity": "4 pasang"},
                {"item_name": "Tarub Premium & Karpet Merah", "quantity": "1 set (10x16m)"},
                {"item_name": "Pelaminan Bunga Segar Premium", "quantity": "8 meter"},
                {"item_name": "Sound System 3000 Watt", "quantity": "1 set"},
                {"item_name": "Kursi Futura + Cover & Pita", "quantity": "100 unit"},
                {"item_name": "Tari Pengiring Panggih Adat", "quantity": "1 tim tari"},
                {"item_name": "Free Henna White & Melati Segar", "quantity": "1 paket"}
            ]
        },
        {
            "name": "Platinum Package",
            "price_per_day": 17400000.0,
            "description": "Paket dekorasi pernikahan platinum super mewah dengan rias pengantin (3x ganti), keluarga lengkap, tarub besar, foto cetak magnetik, organ tunggal & singer, dekorasi kamar premium, henna putih, tari panggih adat, free makeup pre-wedding, dan karpet merah.",
            "stock": 10,
            "includes": [
                {"item_name": "Rias Pengantin Exclusive & Melati Segar", "quantity": "3x ganti busana"},
                {"item_name": "Rias Orang Tua, Besan & Penerima Tamu", "quantity": "Keluarga lengkap"},
                {"item_name": "Pelaminan Luxury Fresh Flowers", "quantity": "12 meter"},
                {"item_name": "Tarub VIP Tunnel & Lighting Dynamic", "quantity": "1 set (12x24m)"},
                {"item_name": "Live Music Organ Tunggal + 2 Singer", "quantity": "1 tim"},
                {"item_name": "Foto & Video Cinema Highlight", "quantity": "Format HD + Album Magz"},
                {"item_name": "Free Pre-Wedding Makeup & Hairdo", "quantity": "1 sesi"},
                {"item_name": "Kursi Futura & Meja VIP", "quantity": "150 unit"},
                {"item_name": "Dekorasi Kamar Pengantin Exclusive", "quantity": "1 set"}
            ]
        }
    ]

    for pkg_data in packages:
        existing_barang = Barang.query.filter_by(name=pkg_data["name"]).first()
        if not existing_barang:
            barang = Barang(
                category_id=kategori.id,
                name=pkg_data["name"],
                price=pkg_data["price_per_day"],
                description=pkg_data["description"],
                stock=pkg_data["stock"],
                status="Active"
            )
            db.session.add(barang)
            db.session.flush()
            target_barang = barang
            print(f"Barang '{pkg_data['name']}' berhasil ditambahkan.")
        else:
            existing_barang.price = pkg_data["price_per_day"]
            existing_barang.description = pkg_data["description"]
            target_barang = existing_barang
            print(f"Barang '{pkg_data['name']}' sudah ada. Memperbarui informasi.")

        # Seed/Update ProductIncludes
        ProductInclude.query.filter_by(product_id=target_barang.id).delete()
        for inc_item in pkg_data.get("includes", []):
            inc = ProductInclude(
                product_id=target_barang.id,
                item_name=inc_item["item_name"],
                quantity=inc_item.get("quantity")
            )
            db.session.add(inc)

    db.session.commit()
    print("Seeding paket pernikahan beserta rincian includes selesai!")