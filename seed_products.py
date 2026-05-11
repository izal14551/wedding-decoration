from app import create_app, db
from app.models import Product

app = create_app()

with app.app_context():
    # Daftar paket dekorasi pernikahan sesuai mockup
    packages = [
        {
            "name": "Silver Package",
            "price_per_day": 12200000.0,
            "description": "Paket dekorasi pernikahan silver yang mencakup rias pengantin (1x ganti), rias orang tua, penerima tamu, tarub, dokumentasi foto, aksesoris, dekorasi kamar, henna, dan MC.",
            "category": "Package",
            "stock": 10,
            "image_path": "silver_package.jpg"
        },
        {
            "name": "Gold Package",
            "price_per_day": 15300000.0,
            "description": "Paket dekorasi pernikahan gold yang lengkap dengan rias pengantin (3x ganti), rias orang tua, penerima tamu, pagar ayu, manggolo, tarub premium, foto, aksesoris melati asli, kamar, henna, MC, tari pengiring, sound system, dan kursi futura.",
            "category": "Package",
            "stock": 10,
            "image_path": "gold_package.jpg"
        },
        {
            "name": "Platinum Package",
            "price_per_day": 17400000.0,
            "description": "Paket dekorasi pernikahan platinum super mewah dengan rias pengantin (3x ganti), keluarga lengkap, tarub besar, foto cetak magnetik, organ tunggal & singer, dekorasi kamar premium, henna putih, tari panggih adat, free makeup pre-wedding, dan karpet merah.",
            "category": "Package",
            "stock": 10,
            "image_path": "platinum_package.jpg"
        }
    ]

    for pkg_data in packages:
        existing_product = Product.query.filter_by(name=pkg_data["name"]).first()
        if not existing_product:
            product = Product(
                name=pkg_data["name"],
                price_per_day=pkg_data["price_per_day"],
                description=pkg_data["description"],
                category=pkg_data["category"],
                stock=pkg_data["stock"],
                image_path=pkg_data["image_path"]
            )
            db.session.add(product)
            print(f"Produk '{pkg_data['name']}' berhasil ditambahkan.")
        else:
            # Update harga jika ada perubahan
            existing_product.price_per_day = pkg_data["price_per_day"]
            existing_product.description = pkg_data["description"]
            print(f"Produk '{pkg_data['name']}' sudah ada. Memperbarui informasi.")

    db.session.commit()
    print("Seeding paket pernikahan selesai!")
