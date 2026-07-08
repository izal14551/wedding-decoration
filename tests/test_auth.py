import unittest
from app import create_app, db
from app.models import User, Role, Customer, Admin
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    WTF_CSRF_ENABLED = False 
class AuthTestCase(unittest.TestCase):
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
        
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_registration_success(self):
        """Uji registrasi berhasil dengan data valid"""
        response = self.client.post('/auth/register', data={
            'name': 'Pelanggan Baru',
            'email': 'pelanggan@example.com',
            'password': 'password123',
            'password_confirm': 'password123',
            'phone': '081234567890',
            'address': 'Jl. Kenanga No. 12, Yogyakarta'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Congratulations, you are now a registered user!', response.data)
        
        # Periksa di database
        user = User.query.filter_by(email='pelanggan@example.com').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.customer.name, 'Pelanggan Baru')
        self.assertTrue(user.check_password('password123'))

    def test_registration_duplicate_email(self):
        """Uji mencegah registrasi dengan email duplikat"""
        u = User(email='kembar@example.com')
        u.set_password('password123')
        u.roles.append(self.customer_role)
        db.session.add(u)
        db.session.flush()
        c = Customer(user_id=u.id, name='User A', phone='081234567890', address='Alamat A')
        db.session.add(c)
        db.session.commit()

        response = self.client.post('/auth/register', data={
            'name': 'User B',
            'email': 'kembar@example.com',
            'password': 'securepwd',
            'password_confirm': 'securepwd',
            'phone': '087712345678',
            'address': 'Alamat B'
        }, follow_redirects=True)
        
        self.assertIn(b'Please use a different email address.', response.data)
        self.assertIsNone(Customer.query.filter_by(name='User B').first())

    def test_registration_duplicate_admin_email(self):
        """Uji mencegah registrasi dengan email yang sudah digunakan oleh Admin (Celah Keamanan)"""
        u_admin = User(email='admin@example.com')
        u_admin.set_password('admin123')
        u_admin.roles.append(self.admin_role)
        db.session.add(u_admin)
        db.session.flush()
        a = Admin(user_id=u_admin.id, name='Admin Utama', phone='081234567890')
        db.session.add(a)
        db.session.commit()

        response = self.client.post('/auth/register', data={
            'name': 'Hacker',
            'email': 'admin@example.com',
            'password': 'hackerpassword',
            'password_confirm': 'hackerpassword',
            'phone': '089912345678',
            'address': 'Alamat Hacker'
        }, follow_redirects=True)
        
        self.assertIn(b'Please use a different email address.', response.data)
        self.assertIsNone(Customer.query.filter_by(name='Hacker').first())

    def test_registration_invalid_phone_format(self):
        """Uji mencegah nomor telepon format salah (non-Indonesia atau ada huruf)"""
        response = self.client.post('/auth/register', data={
            'name': 'User Phone Error',
            'email': 'phoneerr@example.com',
            'password': 'password123',
            'password_confirm': 'password123',
            'phone': 'abcdefghij', 
            'address': 'Jl. Mawar'
        }, follow_redirects=True)
        
        self.assertIn(b'Nomor telepon harus format Indonesia', response.data)
        
        response2 = self.client.post('/auth/register', data={
            'name': 'User Phone Error 2',
            'email': 'phoneerr2@example.com',
            'password': 'password123',
            'password_confirm': 'password123',
            'phone': '+12025550143',
            'address': 'Jl. Melati'
        }, follow_redirects=True)
        self.assertIn(b'Nomor telepon harus format Indonesia', response2.data)

    def test_registration_missing_fields(self):
        """Uji mencegah kolom nama, email, no hp, alamat kosong"""
        response = self.client.post('/auth/register', data={
            'name': '',
            'email': 'kosong@example.com',
            'password': 'password123',
            'password_confirm': 'password123',
            'phone': '081234567890',
            'address': 'Alamat'
        }, follow_redirects=True)
        self.assertIn(b'This field is required.', response.data)

        response2 = self.client.post('/auth/register', data={
            'name': 'Nama',
            'email': 'kosong@example.com',
            'password': 'password123',
            'password_confirm': 'password123',
            'phone': '081234567890',
            'address': ''
        }, follow_redirects=True)
        self.assertIn(b'This field is required.', response2.data)

    def test_registration_password_mismatch(self):
        """Uji konfirmasi password tidak cocok"""
        response = self.client.post('/auth/register', data={
            'name': 'User Pwd Mismatch',
            'email': 'pwdmismatch@example.com',
            'password': 'password123',
            'password_confirm': 'differentpwd',
            'phone': '081234567890',
            'address': 'Alamat'
        }, follow_redirects=True)
        self.assertIn(b'Passwords must match', response.data)

    def test_admin_access_protection(self):
        """Uji pelanggan biasa (customer) dilarang mengakses halaman admin"""
        u = User(email='customer_biasa@example.com')
        u.set_password('budi123')
        u.roles.append(self.customer_role)
        db.session.add(u)
        db.session.flush()
        c = Customer(user_id=u.id, name='Budi', phone='081234567890', address='Alamat')
        db.session.add(c)
        db.session.commit()

        self.client.post('/auth/login', data={
            'email': 'customer_biasa@example.com',
            'password': 'budi123'
        }, follow_redirects=True)

        response = self.client.get('/admin/dashboard', follow_redirects=True)
        self.assertNotIn(b'Admin Dashboard', response.data)

if __name__ == '__main__':
    unittest.main()
