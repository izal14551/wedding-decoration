import unittest
from datetime import date, datetime, timedelta, time
from app import create_app, db
from app.models import User, Role, Customer, Category, Product, Schedule
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    WTF_CSRF_ENABLED = False

class CartValidationApiTestCase(unittest.TestCase):
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

    def test_validate_dates_success(self):
        """Validasi tanggal sukses jika tidak ada konflik atau pemeliharaan"""
        # Login budi
        self.client.post('/auth/login', data={'email': 'budi@example.com', 'password': 'budi123'}, follow_redirects=True)
        
        # Tambah produk ke keranjang
        self.client.post(f'/cart/add/{self.product.id}', data={'quantity': 1}, follow_redirects=True)
        
        start_date = (date.today() + timedelta(days=2)).strftime('%Y-%m-%d')
        end_date = (date.today() + timedelta(days=3)).strftime('%Y-%m-%d')
        
        response = self.client.post('/cart/validate-dates', json={
            'start_date': start_date,
            'end_date': end_date
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['valid'])

    def test_validate_dates_maintenance_conflict(self):
        """Validasi tanggal gagal jika ada masa pemeliharaan (Maintenance)"""
        # Login budi
        self.client.post('/auth/login', data={'email': 'budi@example.com', 'password': 'budi123'}, follow_redirects=True)
        self.client.post(f'/cart/add/{self.product.id}', data={'quantity': 1}, follow_redirects=True)
        
        # Jadwalkan pemeliharaan untuk lusa
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
        
        start_date = date.today().strftime('%Y-%m-%d')
        end_date = (date.today() + timedelta(days=3)).strftime('%Y-%m-%d')
        
        response = self.client.post('/cart/validate-dates', json={
            'start_date': start_date,
            'end_date': end_date
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data['valid'])
        self.assertIn('sedang dalam pemeliharaan (Maintenance)', data['message'])

    def test_validate_dates_stock_conflict(self):
        """Validasi tanggal gagal jika kuantitas di keranjang melebihi stok yang tersedia"""
        # Login budi
        self.client.post('/auth/login', data={'email': 'budi@example.com', 'password': 'budi123'}, follow_redirects=True)
        
        # Tambah Tenda Gold sebanyak 3 unit (sedangkan stok hanya 2)
        # Tambah 2 unit pertama
        self.client.post(f'/cart/add/{self.product.id}', data={'quantity': 2}, follow_redirects=True)
        # Tambah 1 unit lagi (paksa via session atau manual, di sini kita gunakan session)
        with self.client.session_transaction() as sess:
            sess['cart'] = {str(self.product.id): 3}
            
        start_date = (date.today() + timedelta(days=2)).strftime('%Y-%m-%d')
        end_date = (date.today() + timedelta(days=3)).strftime('%Y-%m-%d')
        
        response = self.client.post('/cart/validate-dates', json={
            'start_date': start_date,
            'end_date': end_date
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data['valid'])
        self.assertIn('melebihi stok/kapasitas yang tersedia', data['message'])

    def test_api_product_calendar_success(self):
        """Endpoint API kalender ketersediaan berhasil mengembalikan template kalender HTML"""
        response = self.client.get(f'/api/product/{self.product.id}/calendar?month={date.today().month}&year={date.today().year}')
        self.assertEqual(response.status_code, 200)
        # Memastikan potongan HTML kalender termuat
        self.assertIn(b'Kalender Ketersediaan', response.data)
        self.assertIn(b'calendar-shell', response.data)

if __name__ == '__main__':
    unittest.main()
