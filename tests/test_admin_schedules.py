import unittest
from datetime import date, datetime, timedelta, time
from app import create_app, db
from app.models import User, Role, Customer, Admin, Category, Product, Order, Schedule
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    WTF_CSRF_ENABLED = False

class AdminSchedulesTestCase(unittest.TestCase):
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
        self.cat = Category(name='Tenda')
        db.session.add(self.cat)
        db.session.flush()
        self.product = Product(category_id=self.cat.id, name='Tenda Pernikahan Gold', price=500000.0, stock=2)
        db.session.add(self.product)
        db.session.commit()
        
        # Buat Order untuk Budi
        self.order = Order(
            customer_id=self.customer.id,
            order_date=date.today(),
            start_date=date.today() + timedelta(days=2),
            end_date=date.today() + timedelta(days=3),
            total_price=1000000.0,
            status='Processing'
        )
        db.session.add(self.order)
        db.session.flush()
        
        # Tambah jadwal Rented terkait Order
        self.sch_rented = Schedule(
            product_id=self.product.id,
            order_id=self.order.id,
            date=date.today() + timedelta(days=2),
            start_time=time(8, 0),
            end_time=time(22, 0),
            status='Rented'
        )
        # Tambah jadwal Maintenance manual
        self.sch_maint = Schedule(
            product_id=self.product.id,
            date=date.today() + timedelta(days=5),
            start_time=time(8, 0),
            end_time=time(22, 0),
            status='Maintenance'
        )
        db.session.add_all([self.sch_rented, self.sch_maint])
        db.session.commit()
        
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_schedules_access_anonymous(self):
        """Pengguna anonim harus dialihkan saat mengakses halaman schedules"""
        response = self.client.get('/admin/schedules')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login', response.location)

    def test_schedules_access_customer(self):
        """Pelanggan non-admin dilarang mengakses halaman schedules (dialihkan ke index)"""
        self.client.post('/auth/login', data={'email': 'budi@example.com', 'password': 'budi123'}, follow_redirects=True)
        response = self.client.get('/admin/schedules')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith('/index') or response.location.endswith('/'))

    def test_schedules_access_admin_and_filtering(self):
        """Admin berhasil mengakses halaman schedules dan menggunakan filter"""
        self.client.post('/auth/login', data={'email': 'admin@example.com', 'password': 'admin123'}, follow_redirects=True)
        
        # Akses dasar
        response = self.client.get('/admin/schedules')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Manajemen Jadwal & Ketersediaan', response.data)
        self.assertIn(b'Tenda Pernikahan Gold', response.data)
        
        # Filter berdasarkan product
        response = self.client.get(f'/admin/schedules?product_id={self.product.id}')
        self.assertEqual(response.status_code, 200)
        
        # Filter berdasarkan status
        response = self.client.get('/admin/schedules?status=Maintenance')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'PEMELIHARAAN', response.data)

    def test_schedule_add_maintenance(self):
        """Admin berhasil menambahkan jadwal pemeliharaan baru"""
        self.client.post('/auth/login', data={'email': 'admin@example.com', 'password': 'admin123'}, follow_redirects=True)
        
        start_date = (date.today() + timedelta(days=10)).strftime('%Y-%m-%d')
        end_date = (date.today() + timedelta(days=11)).strftime('%Y-%m-%d')
        
        response = self.client.post('/admin/schedules/add', data={
            'product_id': self.product.id,
            'start_date': start_date,
            'end_date': end_date,
            'start_time': '09:00',
            'end_time': '18:00'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Berhasil menambahkan 2 jadwal pemeliharaan', response.data)
        
        # Verifikasi entri disimpan di database
        maint_schedules = Schedule.query.filter_by(product_id=self.product.id, status='Maintenance').all()
        # Awalnya 1, ditambah 2 = 3
        self.assertEqual(len(maint_schedules), 3)

    def test_schedule_delete_maintenance(self):
        """Admin berhasil menghapus jadwal pemeliharaan manual"""
        self.client.post('/auth/login', data={'email': 'admin@example.com', 'password': 'admin123'}, follow_redirects=True)
        
        response = self.client.post(f'/admin/schedules/{self.sch_maint.id}/delete', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'telah diselesaikan/dihapus', response.data)
        
        # Verifikasi sudah terhapus
        deleted_sch = db.session.get(Schedule, self.sch_maint.id)
        self.assertIsNone(deleted_sch)

    def test_schedule_delete_rented_blocked(self):
        """Admin dilarang menghapus jadwal berstatus Rented secara manual karena terikat order"""
        self.client.post('/auth/login', data={'email': 'admin@example.com', 'password': 'admin123'}, follow_redirects=True)
        
        response = self.client.post(f'/admin/schedules/{self.sch_rented.id}/delete', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Hanya jadwal pemeliharaan (Maintenance) yang dapat dihapus secara manual', response.data)
        
        # Verifikasi tidak terhapus
        active_sch = db.session.get(Schedule, self.sch_rented.id)
        self.assertIsNotNone(active_sch)

if __name__ == '__main__':
    unittest.main()
