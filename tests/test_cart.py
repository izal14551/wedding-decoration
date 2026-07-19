import unittest
from datetime import date, datetime
from app import create_app, db
from app.models import User, Role, Customer, Category, Product, Order, OrderItem, Schedule
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    WTF_CSRF_ENABLED = False

class CartTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Buat peran default
        self.admin_role = Role(name='admin', description='Administrator')
        self.customer_role = Role(name='customer', description='Pelanggan')
        db.session.add_all([self.admin_role, self.customer_role])
        db.session.commit()
        
        # Buat Pelanggan 1
        self.u1 = User(email='budi@example.com')
        self.u1.set_password('budi123')
        self.u1.roles.append(self.customer_role)
        db.session.add(self.u1)
        db.session.flush()
        self.c1 = Customer(user_id=self.u1.id, name='Budi', phone='081234567890', address='Jakarta')
        db.session.add(self.c1)
        
        # Buat Pelanggan 2
        self.u2 = User(email='ani@example.com')
        self.u2.set_password('ani123')
        self.u2.roles.append(self.customer_role)
        db.session.add(self.u2)
        db.session.flush()
        self.c2 = Customer(user_id=self.u2.id, name='Ani', phone='087711223344', address='Jogja')
        db.session.add(self.c2)
        
        # Buat Kategori dan Produk
        self.category = Category(name='Package', description='Wedding Package')
        db.session.add(self.category)
        db.session.flush()
        
        self.product = Product(
            category_id=self.category.id,
            name='Silver Package',
            price=10000000.0,
            stock=5,
            description='Paket Silver',
            status='Active'
        )
        db.session.add(self.product)
        db.session.commit()
        
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_cart_add_stock_validation(self):
        """Uji validasi stok saat menambahkan produk ke keranjang"""
        # Login Pelanggan 1
        self.client.post('/auth/login', data={
            'email': 'budi@example.com',
            'password': 'budi123'
        }, follow_redirects=True)
        
        # Coba add kuantitas melebihi stok (stok = 5, request = 6)
        response = self.client.post(f'/cart/add/{self.product.id}', data={
            'quantity': 6
        }, follow_redirects=True)
        self.assertIn(b'tidak boleh melebihi kapasitas/stok', response.data)
        
        # Coba add kuantitas valid (quantity = 3)
        response = self.client.post(f'/cart/add/{self.product.id}', data={
            'quantity': 3
        }, follow_redirects=True)
        self.assertIn(b'berhasil ditambahkan ke keranjang', response.data)
        
        with self.client.session_transaction() as sess:
            self.assertIn('cart', sess)
            self.assertEqual(sess['cart'][str(self.product.id)], 3)

    def test_cart_update_limit_validation(self):
        """Uji validasi kuantitas saat memperbarui jumlah di halaman keranjang"""
        # Login Pelanggan 1
        self.client.post('/auth/login', data={
            'email': 'budi@example.com',
            'password': 'budi123'
        }, follow_redirects=True)
        
        # Tambahkan 5 unit (stok maksimal)
        self.client.post(f'/cart/add/{self.product.id}', data={'quantity': 5})
        
        # Coba naikkan kuantitas melebihi batas stok (increase)
        response = self.client.post(f'/cart/update/{self.product.id}', data={
            'action': 'increase'
        }, follow_redirects=True)
        self.assertIn(b'tidak boleh melebihi kapasitas/stok', response.data)

    def test_checkout_validation_and_double_booking(self):
        """Uji alur checkout, validasi tanggal, dan pencegahan double booking"""
        # Login Pelanggan 1
        self.client.post('/auth/login', data={
            'email': 'budi@example.com',
            'password': 'budi123'
        }, follow_redirects=True)
        
        # Tambahkan 3 unit ke keranjang
        self.client.post(f'/cart/add/{self.product.id}', data={'quantity': 3})
        
        # Coba checkout tanggal di masa lalu
        response = self.client.post('/checkout', data={
            'start_date': '2020-01-01',
            'end_date': '2020-01-03',
            'phone': '081234567890',
            'address': 'Gedung A'
        }, follow_redirects=True)
        self.assertIn(b'tidak boleh di masa lalu', response.data)
        
        # Checkout berhasil (3 unit untuk tanggal masa depan: 2026-08-20 s/d 2026-08-22)
        response = self.client.post('/checkout', data={
            'start_date': '2026-08-20',
            'end_date': '2026-08-22',
            'phone': '081234567890',
            'address': 'Gedung A'
        }, follow_redirects=True)
        self.assertIn(b'Pemesanan dekorasi berhasil dibuat', response.data)
        
        # Pastikan pesanan dan detailnya tersimpan di DB
        order = Order.query.filter_by(customer_id=self.c1.id).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.status, 'Pending')
        
        item = OrderItem.query.filter_by(order_id=order.id).first()
        self.assertIsNotNone(item)
        self.assertEqual(item.quantity, 3)
        
        # Pastikan data Schedule dibuat sebanyak 3 unit per hari selama 3 hari = 9 schedule records
        schedules = Schedule.query.filter_by(order_id=order.id).all()
        self.assertEqual(len(schedules), 9)
        
        # Logout Pelanggan 1
        self.client.get('/auth/logout')
        
        # Login Pelanggan 2
        self.client.post('/auth/login', data={
            'email': 'ani@example.com',
            'password': 'ani123'
        }, follow_redirects=True)
        
        # Tambahkan 3 unit ke keranjang untuk Pelanggan 2
        self.client.post(f'/cart/add/{self.product.id}', data={'quantity': 3})
        
        # Coba checkout 3 unit di rentang tanggal yang sama (2026-08-20 s/d 2026-08-22)
        # Sisa stok hanya 2 (5 - 3), maka checkout 3 unit harus DITOLAK
        response = self.client.post('/checkout', data={
            'start_date': '2026-08-20',
            'end_date': '2026-08-22',
            'phone': '087711223344',
            'address': 'Gedung B'
        }, follow_redirects=True)
        self.assertIn(b'melebihi stok/kapasitas yang tersedia (2 Unit)', response.data)
        
        # Sesuaikan kuantitas di keranjang Pelanggan 2 menjadi 2 unit
        # Pertama hapus produk, lalu tambahkan 2 unit
        self.client.post(f'/cart/remove/{self.product.id}')
        self.client.post(f'/cart/add/{self.product.id}', data={'quantity': 2})
        
        # Checkout kembali dengan kuantitas 2 unit pada rentang tanggal yang sama, harus BERHASIL
        response = self.client.post('/checkout', data={
            'start_date': '2026-08-20',
            'end_date': '2026-08-22',
            'phone': '087711223344',
            'address': 'Gedung B'
        }, follow_redirects=True)
        self.assertIn(b'Pemesanan dekorasi berhasil dibuat', response.data)

    def test_checkout_edge_cases(self):
        """Uji berbagai skenario kegagalan checkout (edge cases)"""
        # Login Pelanggan 1
        self.client.post('/auth/login', data={
            'email': 'budi@example.com',
            'password': 'budi123'
        }, follow_redirects=True)

        # Kasus 1: Checkout saat keranjang kosong
        response_empty_cart = self.client.post('/checkout', data={
            'start_date': '2026-09-01',
            'end_date': '2026-09-03',
            'phone': '081234567890',
            'address': 'Gedung A'
        }, follow_redirects=True)
        self.assertIn(b'Keranjang Anda kosong.', response_empty_cart.data)

        # Tambahkan produk ke keranjang untuk kasus berikutnya
        self.client.post(f'/cart/add/{self.product.id}', data={'quantity': 1})

        # Kasus 2: Checkout dengan form tidak lengkap (tanpa alamat)
        response_missing_form = self.client.post('/checkout', data={
            'start_date': '2026-09-01',
            'end_date': '2026-09-03',
            'phone': '081234567890',
            'address': '' # Alamat kosong
        }, follow_redirects=True)
        self.assertIn(b'Silakan isi tanggal sewa dan alamat acara.', response_missing_form.data)

        # Kasus 3: Checkout dengan format tanggal tidak valid
        response_invalid_date = self.client.post('/checkout', data={
            'start_date': '2026-09-01',
            'end_date': 'invalid-date-format',
            'phone': '081234567890',
            'address': 'Gedung A'
        }, follow_redirects=True)
        self.assertIn(b'Format tanggal tidak valid.', response_invalid_date.data)

        # Kasus 4: Checkout dengan tanggal selesai mendahului tanggal mulai
        response_wrong_order = self.client.post('/checkout', data={
            'start_date': '2026-09-03',
            'end_date': '2026-09-01', # end_date < start_date
            'phone': '081234567890',
            'address': 'Gedung A'
        }, follow_redirects=True)
        self.assertIn(b'Tanggal selesai sewa harus setelah atau sama dengan tanggal mulai sewa.', response_wrong_order.data)

