import unittest
from datetime import date, datetime, timedelta
from app import create_app, db
from app.models import User, Role, Customer, Admin, Category, Product, Order, OrderItem, Payment
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    WTF_CSRF_ENABLED = False

class AdminReportsTestCase(unittest.TestCase):
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
        
        # Buat Admin
        self.u_admin = User(email='admin@example.com')
        self.u_admin.set_password('admin123')
        self.u_admin.roles.append(self.admin_role)
        db.session.add(self.u_admin)
        db.session.flush()
        self.admin = Admin(user_id=self.u_admin.id, name='Admin Utama', phone='081234567890')
        db.session.add(self.admin)
        
        # Buat Customer
        self.u_cust = User(email='budi@example.com')
        self.u_cust.set_password('budi123')
        self.u_cust.roles.append(self.customer_role)
        db.session.add(self.u_cust)
        db.session.flush()
        self.customer = Customer(user_id=self.u_cust.id, name='Budi', phone='087711223344', address='Jogja')
        db.session.add(self.customer)
        
        # Buat Kategori dan Produk
        self.cat = Category(name='Alat Pernikahan')
        db.session.add(self.cat)
        db.session.flush()
        self.product = Product(category_id=self.cat.id, name='Kursi Tiffany', price=5000.0, stock=100)
        db.session.add(self.product)
        db.session.commit()
        
        # Buat beberapa order untuk data laporan
        self.order1 = Order(
            customer_id=self.customer.id,
            order_date=date.today() - timedelta(days=2),
            start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=7),
            total_price=50000.0,
            status='Completed'
        )
        self.order2 = Order(
            customer_id=self.customer.id,
            order_date=date.today() - timedelta(days=5),
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=12),
            total_price=100000.0,
            status='Processing'
        )
        db.session.add_all([self.order1, self.order2])
        db.session.flush()
        
        # Tambah detail items
        item1 = OrderItem(order_id=self.order1.id, product_id=self.product.id, quantity=10, price=5000.0)
        item2 = OrderItem(order_id=self.order2.id, product_id=self.product.id, quantity=20, price=5000.0)
        db.session.add_all([item1, item2])
        db.session.commit()
        
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_reports_access_anonymous(self):
        """Pengguna anonim harus dialihkan saat mengakses halaman laporan"""
        response = self.client.get('/admin/reports')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login', response.location)

    def test_reports_access_customer(self):
        """Pelanggan non-admin dilarang mengakses halaman laporan (dialihkan ke halaman beranda/index)"""
        self.client.post('/auth/login', data={'email': 'budi@example.com', 'password': 'budi123'}, follow_redirects=True)
        response = self.client.get('/admin/reports')
        self.assertEqual(response.status_code, 302)
        # Sesuai decorator admin_required: dialihkan ke customer.index (bernilai '/index' atau '/')
        self.assertTrue(response.location.endswith('/index') or response.location.endswith('/'))

    def test_reports_access_admin_and_filtering(self):
        """Admin berhasil mengakses laporan dan mengganti filter periode"""
        self.client.post('/auth/login', data={'email': 'admin@example.com', 'password': 'admin123'}, follow_redirects=True)
        
        # 1. Default (Monthly)
        response = self.client.get('/admin/reports')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Laporan Keuangan & Statistik', response.data)
        self.assertIn(b'Rp 150.000', response.data) # total pendapatan
        self.assertIn(b'Kursi Tiffany', response.data) # top best sellers
        
        # 2. Harian
        response = self.client.get('/admin/reports?periode=daily')
        self.assertEqual(response.status_code, 200)
        
        # 3. Mingguan
        response = self.client.get('/admin/reports?periode=weekly')
        self.assertEqual(response.status_code, 200)
        
        # 4. Tahunan
        response = self.client.get('/admin/reports?periode=yearly')
        self.assertEqual(response.status_code, 200)

    def test_reports_export_excel(self):
        """Admin berhasil mengekspor laporan transaksi ke Excel"""
        self.client.post('/auth/login', data={'email': 'admin@example.com', 'password': 'admin123'}, follow_redirects=True)
        
        response = self.client.get('/admin/reports/export/excel?periode=monthly')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertIn('laporan-transaksi-monthly', response.headers.get('Content-Disposition', ''))

    def test_reports_export_pdf(self):
        """Admin berhasil mengekspor laporan transaksi ke PDF"""
        self.client.post('/auth/login', data={'email': 'admin@example.com', 'password': 'admin123'}, follow_redirects=True)
        
        response = self.client.get('/admin/reports/export/pdf?periode=monthly')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/pdf')
        self.assertIn('laporan-transaksi-monthly', response.headers.get('Content-Disposition', ''))
        # PDF signatures
        self.assertTrue(response.data.startswith(b'%PDF'))

if __name__ == '__main__':
    unittest.main()
