import os
from datetime import datetime, date, time
from app import create_app, db
from app.models import Customer, Category, Product, Order, OrderItem, Payment, Admin, Schedule, User, Role

app = create_app()

with app.app_context():
    print("Mereset database...")
    if db.engine.name == 'mysql':
        db.session.execute(db.text("SET FOREIGN_KEY_CHECKS = 0;"))
        db.session.commit()
        
        old_tables = ['detail_pesanan', 'laporan', 'pembayaran', 'pesanan', 'jadwal', 'barang', 'kategori', 'pelanggan']
        for table in old_tables:
            db.session.execute(db.text(f"DROP TABLE IF EXISTS `{table}`;"))
        db.session.commit()

    db.drop_all()
    db.create_all()

    if db.engine.name == 'mysql':
        db.session.execute(db.text("SET FOREIGN_KEY_CHECKS = 1;"))
        db.session.commit()

    print("Database berhasil direset!")

    # 1. Seed Admin
    print("Seeding Admin...")
    admin_role = Role(name='admin', description='Administrator')
    customer_role = Role(name='customer', description='Pelanggan')
    db.session.add_all([admin_role, customer_role])
    db.session.flush()

    u_admin = User(email='admin@example.com')
    u_admin.set_password('admin123')
    u_admin.roles.append(admin_role)
    db.session.add(u_admin)
    db.session.flush()

    admin = Admin(
        user_id=u_admin.id,
        name='Administrator',
        phone='081234567890'
    )
    db.session.add(admin)
    db.session.flush()

    # 2. Seed Category
    print("Seeding Category...")
    category_pkg = Category(
        name='Package',
        description='Complete wedding decoration packages'
    )
    category_makeup = Category(
        name='Makeup',
        description='Traditional and modern bridal makeup & attire services'
    )
    category_tent = Category(
        name='Tent & Stage',
        description='Tents, stages, and other party equipment'
    )
    db.session.add_all([category_pkg, category_makeup, category_tent])
    db.session.flush()

    # 3. Seed Product (Barang)
    print("Seeding Product...")
    silver_pkg = Product(
        category_id=category_pkg.id,
        name='Silver Package',
        price=12200000.00,
        stock=5,
        description='Paket dekorasi pernikahan silver yang mencakup rias pengantin (1x ganti), rias orang tua, penerima tamu, tarub, dokumentasi foto, aksesoris, dekorasi kamar, henna, dan MC.',
        status='Active'
    )
    gold_pkg = Product(
        category_id=category_pkg.id,
        name='Gold Package',
        price=15300000.00,
        stock=5,
        description='Paket dekorasi pernikahan gold yang lengkap dengan rias pengantin (3x ganti), rias orang tua, penerima tamu, pagar ayu, manggolo, tarub premium, foto, aksesoris melati asli, kamar, henna, MC, tari pengiring, sound system, dan kursi futura.',
        status='Active'
    )
    platinum_pkg = Product(
        category_id=category_pkg.id,
        name='Platinum Package',
        price=17400000.00,
        stock=3,
        description='Paket dekorasi pernikahan platinum super mewah dengan rias pengantin (3x ganti), keluarga lengkap, tarub besar, foto cetak magnetik, organ tunggal & singer, dekorasi kamar premium, henna putih, tari panggih adat, free makeup pre-wedding, dan karpet merah.',
        status='Active'
    )
    db.session.add_all([silver_pkg, gold_pkg, platinum_pkg])
    db.session.flush()

    # 4. Seed Customer
    print("Seeding Customer...")
    u1 = User(email='budi@example.com')
    u1.set_password('budi123')
    u1.roles.append(customer_role)
    
    u2 = User(email='ani@example.com')
    u2.set_password('ani123')
    u2.roles.append(customer_role)
    
    u3 = User(email='siti@example.com')
    u3.set_password('siti123')
    u3.roles.append(customer_role)
    
    db.session.add_all([u1, u2, u3])
    db.session.flush()

    p1 = Customer(
        user_id=u1.id,
        name='Budi Santoso',
        phone='085611223344',
        address='Jl. Merdeka No. 10, Jakarta Pusat',
        is_active=True
    )

    p2 = Customer(
        user_id=u2.id,
        name='Ani Lestari',
        phone='087799887766',
        address='Jl. Melati No. 5, Sleman, Yogyakarta',
        is_active=True
    )

    p3 = Customer(
        user_id=u3.id,
        name='Siti Aminah',
        phone='081233445566',
        address='Jl. Mawar Gg. 3 No. 12, Solo',
        is_active=True
    )
    db.session.add_all([p1, p2, p3])
    db.session.flush()

    # 5. Seed Order & OrderItem & Payment & Schedule
    print("Seeding Transaction & Schedule...")

    # Data Order 1 (Completed in the past)
    order1 = Order(
        customer_id=p1.id,
        order_date=date(2026, 4, 15),
        start_date=date(2026, 5, 10),
        end_date=date(2026, 5, 12),
        event_address='Gedung Serbaguna Sleman',
        notes='Nuansa warna biru muda dan putih',
        total_price=24400000.00,
        status='Completed'
    )
    db.session.add(order1)
    db.session.flush()
    
    det1 = OrderItem(
        order_id=order1.id,
        product_id=silver_pkg.id,
        quantity=1,
        price=12200000.00
    )
    db.session.add(det1)
    
    pay1 = Payment(
        order_id=order1.id,
        admin_id=admin.id,
        payment_date=date(2026, 4, 16),
        payment_method='Transfer Bank Mandiri',
        payment_proof='bukti_transfer_1.jpg',
        status='Approved'
    )
    db.session.add(pay1)

    # Schedule for Order 1
    for d in [date(2026, 5, 10), date(2026, 5, 11), date(2026, 5, 12)]:
        db.session.add(Schedule(
            product_id=silver_pkg.id,
            date=d,
            start_time=time(8, 0),
            end_time=time(22, 0),
            status='Rented'
        ))

    # Data Order 2 (Processing / Today)
    order2 = Order(
        customer_id=p2.id,
        order_date=date(2026, 5, 20),
        start_date=date(2026, 6, 9),
        end_date=date(2026, 6, 11),
        event_address='Halaman Rumah Bu Ani',
        notes='Nuansa adat Jawa Solo Putri',
        total_price=30600000.00,
        status='Processing'
    )
    db.session.add(order2)
    db.session.flush()

    det2 = OrderItem(
        order_id=order2.id,
        product_id=gold_pkg.id,
        quantity=1,
        price=15300000.00
    )
    db.session.add(det2)

    pay2 = Payment(
        order_id=order2.id,
        admin_id=admin.id,
        payment_date=date(2026, 5, 22),
        payment_method='Transfer Bank BCA',
        payment_proof='bukti_transfer_2.jpg',
        status='Approved'
    )
    db.session.add(pay2)

    # Schedule for Order 2
    for d in [date(2026, 6, 9), date(2026, 6, 10), date(2026, 6, 11)]:
        db.session.add(Schedule(
            product_id=gold_pkg.id,
            date=d,
            start_time=time(8, 0),
            end_time=time(22, 0),
            status='Rented'
        ))

    # Data Order 3 (Upcoming - Pending Verification)
    order3 = Order(
        customer_id=p3.id,
        order_date=date(2026, 6, 5),
        start_date=date(2026, 6, 25),
        end_date=date(2026, 6, 27),
        event_address='Grand Ballroom Hotel Tentrem',
        notes='Nuansa modern gold platinum luxury',
        total_price=52200000.00,
        status='Pending'
    )
    db.session.add(order3)
    db.session.flush()

    det3 = OrderItem(
        order_id=order3.id,
        product_id=platinum_pkg.id,
        quantity=1,
        price=17400000.00
    )
    db.session.add(det3)

    pay3 = Payment(
        order_id=order3.id,
        payment_date=date(2026, 6, 8),
        payment_method='Transfer Bank Mandiri',
        payment_proof='bukti_transfer_3.jpg',
        status='Pending'
    )
    db.session.add(pay3)

    # Schedule for Order 3
    for d in [date(2026, 6, 25), date(2026, 6, 26), date(2026, 6, 27)]:
        db.session.add(Schedule(
            product_id=platinum_pkg.id,
            date=d,
            start_time=time(6, 0),
            end_time=time(23, 0),
            status='Rented'
        ))

    # Data Order 4 (Next Month - Unpaid)
    order4 = Order(
        customer_id=p1.id,
        order_date=date(2026, 6, 8),
        start_date=date(2026, 7, 5),
        end_date=date(2026, 7, 6),
        event_address='Masjid Kampus UGM',
        notes='Minimalis rustik',
        total_price=12200000.00,
        status='Pending'
    )
    db.session.add(order4)
    db.session.flush()

    det4 = OrderItem(
        order_id=order4.id,
        product_id=silver_pkg.id,
        quantity=1,
        price=12200000.00
    )
    db.session.add(det4)

    # Schedule for Order 4
    for d in [date(2026, 7, 5), date(2026, 7, 6)]:
        db.session.add(Schedule(
            product_id=silver_pkg.id,
            date=d,
            start_time=time(8, 0),
            end_time=time(22, 0),
            status='Rented'
        ))

    # Data Order 5 (Cancelled)
    order5 = Order(
        customer_id=p2.id,
        order_date=date(2026, 3, 10),
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 2),
        event_address='Balai Desa Condongcatur',
        notes='Dibatalkan oleh pelanggan',
        total_price=15300000.00,
        status='Cancelled'
    )
    db.session.add(order5)
    db.session.flush()

    det5 = OrderItem(
        order_id=order5.id,
        product_id=gold_pkg.id,
        quantity=1,
        price=15300000.00
    )
    db.session.add(det5)

    pay5 = Payment(
        order_id=order5.id,
        admin_id=admin.id,
        payment_date=date(2026, 3, 12),
        payment_method='Transfer Bank BCA',
        payment_proof='bukti_transfer_5.jpg',
        status='Rejected'
    )
    db.session.add(pay5)

    # Maintenance Schedule
    db.session.add(Schedule(
        product_id=platinum_pkg.id,
        date=date(2026, 6, 12),
        start_time=time(8, 0),
        end_time=time(17, 0),
        status='Maintenance'
    ))

    db.session.commit()
    print("Database seeding selesai dengan skema bahasa Inggris sepenuhnya!")
