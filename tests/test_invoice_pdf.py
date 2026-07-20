import unittest
from datetime import date, datetime, timedelta
from app import create_app, db
from app.models import User, Role, Customer, Category, Product, Order, OrderItem, Payment
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    WTF_CSRF_ENABLED = False

class InvoicePdfTestCase(unittest.TestCase):
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
        
        # Buat Pelanggan 1 (Budi)
        self.u1 = User(email='budi@example.com')
        self.u1.set_password('budi123')
        self.u1.roles.append(self.customer_role)
        db.session.add(self.u1)
        db.session.flush()
        self.c1 = Customer(user_id=self.u1.id, name='Budi', phone='081234567890', address='Jakarta')
        db.session.add(self.c1)
        
        # Buat Pelanggan 2 (Ani)
        self.u2 = User(email='ani@example.com')
        self.u2.set_password('ani123')
        self.u2.roles.append(self.customer_role)
        db.session.add(self.u2)
        db.session.flush()
        self.c2 = Customer(user_id=self.u2.id, name='Ani', phone='087711223344', address='Jogja')
        db.session.add(self.c2)
        
        # Buat Kategori dan Produk
        self.category = Category(name='Decoration', description='Wedding Decoration')
        db.session.add(self.category)
        db.session.flush()
        
        self.product = Product(
            category_id=self.category.id,
            name='Rustic Wedding Set',
            price=5000000.0,
            stock=3,
            description='Rustic theme',
            status='Active'
        )
        db.session.add(self.product)
        db.session.commit()
        
        # Buat Order 1 untuk Budi (masih Pending / belum diverifikasi)
        self.order_pending = Order(
            customer_id=self.c1.id,
            start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=6),
            event_address='Gedung Serbaguna',
            notes='Mohon disiapkan pagi hari.',
            total_price=10000000.0,
            status='Pending'
        )
        db.session.add(self.order_pending)
        db.session.flush()
        
        item1 = OrderItem(
            order_id=self.order_pending.id,
            product_id=self.product.id,
            quantity=1,
            price=5000000.0
        )
        db.session.add(item1)
        
        # Buat Order 2 untuk Budi (sudah Processing / lunas diverifikasi)
        self.order_verified = Order(
            customer_id=self.c1.id,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=11),
            event_address='Rumah Budi',
            notes='Lunas terverifikasi.',
            total_price=10000000.0,
            status='Processing'
        )
        db.session.add(self.order_verified)
        db.session.flush()
        
        item2 = OrderItem(
            order_id=self.order_verified.id,
            product_id=self.product.id,
            quantity=1,
            price=5000000.0
        )
        db.session.add(item2)
        
        # Tambah payment Approved untuk order_verified
        self.payment = Payment(
            order_id=self.order_verified.id,
            payment_method='Transfer',
            payment_proof='proof.jpg',
            status='Approved'
        )
        db.session.add(self.payment)
        
        db.session.commit()
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_pdf_download_anonymous(self):
        """Pengguna tidak terautentikasi harus dialihkan saat mencoba mengunduh PDF"""
        response = self.client.get(f'/order/{self.order_verified.id}/invoice/pdf')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login', response.location)

    def test_pdf_download_unauthorized_user(self):
        """Pelanggan lain tidak boleh mengakses PDF invoice pelanggan yang bersangkutan (harus 404)"""
        # Login sebagai Ani
        self.client.post('/auth/login', data={
            'email': 'ani@example.com',
            'password': 'ani123'
        }, follow_redirects=True)
        
        # Coba akses order milik Budi
        response = self.client.get(f'/order/{self.order_verified.id}/invoice/pdf')
        self.assertEqual(response.status_code, 404)

    def test_pdf_download_not_verified_yet(self):
        """PDF invoice resmi tidak boleh diunduh jika pembayaran belum disetujui (Approved)"""
        # Login sebagai Budi
        self.client.post('/auth/login', data={
            'email': 'budi@example.com',
            'password': 'budi123'
        }, follow_redirects=True)
        
        # Coba unduh order_pending yang belum diverifikasi
        response = self.client.get(f'/order/{self.order_pending.id}/invoice/pdf')
        self.assertEqual(response.status_code, 302) # Dialihkan kembali ke profil
        
        # Harus ada flash warning di session
        with self.client.session_transaction() as sess:
            # Periksa flask flash messages
            flashes = sess.get('_flashes', [])
            self.assertTrue(any(f[0] == 'warning' and 'hanya dapat diunduh setelah pembayaran diverifikasi' in f[1] for f in flashes))

    def test_pdf_download_success(self):
        """PDF invoice resmi berhasil diunduh setelah pembayaran diverifikasi"""
        # Login sebagai Budi
        self.client.post('/auth/login', data={
            'email': 'budi@example.com',
            'password': 'budi123'
        }, follow_redirects=True)
        
        # Coba unduh order_verified yang sudah disetujui
        response = self.client.get(f'/order/{self.order_verified.id}/invoice/pdf')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/pdf')
        self.assertIn(f'attachment; filename=invoice-{self.order_verified.id}.pdf', response.headers.get('Content-Disposition', ''))
        # Pastikan data PDF valid (biasanya dimulai dengan penanda format PDF '%PDF')
        self.assertTrue(response.data.startswith(b'%PDF'))

if __name__ == '__main__':
    unittest.main()
