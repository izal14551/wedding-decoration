import unittest
from datetime import date, datetime, timedelta, time
from app import create_app, db
from app.models import User, Role, Customer, Category, Product, Schedule
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    WTF_CSRF_ENABLED = False

class CustomerMaintenanceTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Buat peran default
        self.customer_role = Role(name='customer', description='Pelanggan')
        db.session.add(self.customer_role)
        db.session.commit()
        
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
        self.product = Product(category_id=self.cat.id, name='Tenda Gold', price=500000.0, stock=2)
        db.session.add(self.product)
        db.session.commit()
        
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_product_detail_shows_maintenance(self):
        """Halaman detail produk menampilkan status Perawatan di kalender jika dijadwalkan pemeliharaan"""
        # Jadwalkan pemeliharaan untuk besok
        tomorrow = date.today() + timedelta(days=1)
        sch_maint = Schedule(
            product_id=self.product.id,
            date=tomorrow,
            start_time=time(8, 0),
            end_time=time(22, 0),
            status='Maintenance'
        )
        db.session.add(sch_maint)
        db.session.commit()
        
        response = self.client.get(f'/decoration/{self.product.id}?month={tomorrow.month}&year={tomorrow.year}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Perawatan', response.data)
        self.assertIn(b'bi-tools text-warning', response.data)

    def test_checkout_blocked_during_maintenance(self):
        """Checkout harus ditolak jika produk yang disewa berada dalam masa pemeliharaan pada rentang tanggal tersebut"""
        # Login budi
        self.client.post('/auth/login', data={'email': 'budi@example.com', 'password': 'budi123'}, follow_redirects=True)
        
        # Tambah ke keranjang
        response = self.client.post(f'/cart/add/{self.product.id}', data={'quantity': 1}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        # Jadwalkan pemeliharaan untuk lusa (2 hari dari sekarang)
        maintenance_date = date.today() + timedelta(days=2)
        sch_maint = Schedule(
            product_id=self.product.id,
            date=maintenance_date,
            start_time=time(8, 0),
            end_time=time(22, 0),
            status='Maintenance'
        )
        db.session.add(sch_maint)
        db.session.commit()
        
        # Lakukan checkout dengan rentang sewa yang mencakup tanggal pemeliharaan (hari ini s/d 3 hari ke depan)
        start_date_str = date.today().strftime('%Y-%m-%d')
        end_date_str = (date.today() + timedelta(days=3)).strftime('%Y-%m-%d')
        
        response = self.client.post('/checkout', data={
            'start_date': start_date_str,
            'end_date': end_date_str,
            'phone': '087711223344',
            'address': 'Godean Sleman',
            'notes': 'Acara Outdoor'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        # Memastikan checkout ditolak dan redirect ke keranjang dengan flash message yang sesuai
        self.assertIn(b'sedang dalam pemeliharaan (Maintenance)', response.data)
        
if __name__ == '__main__':
    unittest.main()
