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

    def test_customer_profile_update_success(self):
        """Uji sukses mengubah data profil"""
        u = User(email='budi@example.com')
        u.set_password('budi123')
        u.roles.append(self.customer_role)
        db.session.add(u)
        db.session.flush()
        c = Customer(user_id=u.id, name='Budi', phone='081234567890', address='Alamat Asli')
        db.session.add(c)
        db.session.commit()

        # Login
        self.client.post('/auth/login', data={
            'email': 'budi@example.com',
            'password': 'budi123'
        }, follow_redirects=True)

        # Update Profile
        response = self.client.post('/profile/update', data={
            'name': 'Budi Baru',
            'email': 'budibaru@example.com',
            'phone': '081299998888',
            'address': 'Alamat Baru',
            'password': 'newpassword123'
        }, follow_redirects=True)

        self.assertIn(b'Informasi profil berhasil diperbarui.', response.data)
        
        # Periksa di DB
        updated_user = db.session.get(User, u.id)
        self.assertEqual(updated_user.email, 'budibaru@example.com')
        self.assertEqual(updated_user.customer.name, 'Budi Baru')
        self.assertEqual(updated_user.customer.phone, '081299998888')
        self.assertEqual(updated_user.customer.address, 'Alamat Baru')
        self.assertTrue(updated_user.check_password('newpassword123'))

    def test_customer_profile_update_duplicate_email(self):
        """Uji gagal mengubah profil jika email baru sudah digunakan orang lain"""
        u1 = User(email='budi@example.com')
        u1.set_password('budi123')
        u1.roles.append(self.customer_role)
        db.session.add(u1)
        db.session.flush()
        c1 = Customer(user_id=u1.id, name='Budi', phone='081234567890', address='Alamat')
        db.session.add(c1)

        u2 = User(email='ani@example.com')
        u2.set_password('ani123')
        u2.roles.append(self.customer_role)
        db.session.add(u2)
        db.session.flush()
        c2 = Customer(user_id=u2.id, name='Ani', phone='081234567891', address='Alamat')
        db.session.add(c2)
        db.session.commit()

        # Login budi
        self.client.post('/auth/login', data={
            'email': 'budi@example.com',
            'password': 'budi123'
        }, follow_redirects=True)

        # Coba ubah email budi menjadi ani@example.com
        response = self.client.post('/profile/update', data={
            'name': 'Budi',
            'email': 'ani@example.com',
            'phone': '081234567890',
            'address': 'Alamat'
        }, follow_redirects=True)

        self.assertIn(b'Email sudah digunakan oleh pengguna lain.', response.data)

    def test_customer_profile_update_invalid_phone(self):
        """Uji gagal mengubah profil jika format nomor telepon salah"""
        u = User(email='budi@example.com')
        u.set_password('budi123')
        u.roles.append(self.customer_role)
        db.session.add(u)
        db.session.flush()
        c = Customer(user_id=u.id, name='Budi', phone='081234567890', address='Alamat')
        db.session.add(c)
        db.session.commit()

        # Login
        self.client.post('/auth/login', data={
            'email': 'budi@example.com',
            'password': 'budi123'
        }, follow_redirects=True)

        # Phone non-Indonesia
        response = self.client.post('/profile/update', data={
            'name': 'Budi',
            'email': 'budi@example.com',
            'phone': '12345abcde',
            'address': 'Alamat'
        }, follow_redirects=True)

        self.assertIn(b'Nomor telepon harus format Indonesia', response.data)

    def test_customer_profile_update_short_password(self):
        """Uji gagal mengubah profil jika password baru di bawah 6 karakter"""
        u = User(email='budi@example.com')
        u.set_password('budi123')
        u.roles.append(self.customer_role)
        db.session.add(u)
        db.session.flush()
        c = Customer(user_id=u.id, name='Budi', phone='081234567890', address='Alamat')
        db.session.add(c)
        db.session.commit()

        # Login
        self.client.post('/auth/login', data={
            'email': 'budi@example.com',
            'password': 'budi123'
        }, follow_redirects=True)

        # Password 5 char
        response = self.client.post('/profile/update', data={
            'name': 'Budi',
            'email': 'budi@example.com',
            'phone': '081234567890',
            'address': 'Alamat',
            'password': '12345'
        }, follow_redirects=True)

        self.assertIn(b'Password minimal harus 6 karakter.', response.data)

    def test_admin_view_customers_page(self):
        """Uji admin dapat membuka halaman kelola pelanggan sedangkan pelanggan biasa ditolak"""
        u_admin = User(email='admin_test@example.com')
        u_admin.set_password('admin123')
        u_admin.roles.append(self.admin_role)
        db.session.add(u_admin)
        db.session.commit()

        self.client.post('/auth/login', data={
            'email': 'admin_test@example.com',
            'password': 'admin123'
        }, follow_redirects=True)

        response = self.client.get('/admin/customers', follow_redirects=True)
        self.assertIn(b'Manajemen Pelanggan', response.data)
        self.assertIn(b'Daftar Akun Pelanggan', response.data)

        self.client.get('/auth/logout', follow_redirects=True)

        u_cust = User(email='cust_test@example.com')
        u_cust.set_password('budi123')
        u_cust.roles.append(self.customer_role)
        db.session.add(u_cust)
        db.session.flush()
        c = Customer(user_id=u_cust.id, name='Budi', phone='081234567890', address='Alamat')
        db.session.add(c)
        db.session.commit()

        self.client.post('/auth/login', data={
            'email': 'cust_test@example.com',
            'password': 'budi123'
        }, follow_redirects=True)

        response_cust = self.client.get('/admin/customers', follow_redirects=True)
        self.assertNotIn(b'Manajemen Pelanggan', response_cust.data)

    def test_admin_toggle_customer_status(self):
        """Uji admin mengubah keaktifan akun pelanggan (is_active)"""
        u_admin = User(email='admin_test@example.com')
        u_admin.set_password('admin123')
        u_admin.roles.append(self.admin_role)
        db.session.add(u_admin)

        u_cust = User(email='cust_test@example.com')
        u_cust.set_password('budi123')
        u_cust.roles.append(self.customer_role)
        db.session.add(u_cust)
        db.session.flush()
        c = Customer(user_id=u_cust.id, name='Budi', phone='081234567890', address='Alamat', is_active=True)
        db.session.add(c)
        db.session.commit()

        self.client.post('/auth/login', data={
            'email': 'admin_test@example.com',
            'password': 'admin123'
        }, follow_redirects=True)

        response = self.client.post(f'/admin/customer/{c.id}/toggle_status', follow_redirects=True)
        self.assertIn(b'berhasil dinonaktifkan', response.data)
        
        db.session.refresh(c)
        db.session.refresh(u_cust)
        self.assertFalse(c.is_active)
        self.assertFalse(u_cust.active)

        self.client.get('/auth/logout', follow_redirects=True)

        response_login = self.client.post('/auth/login', data={
            'email': 'cust_test@example.com',
            'password': 'budi123'
        }, follow_redirects=True)
        self.assertIn(b'Your account has been deactivated.', response_login.data)

    def test_admin_delete_customer(self):
        """Uji admin menghapus akun pelanggan secara permanen"""
        u_admin = User(email='admin_test@example.com')
        u_admin.set_password('admin123')
        u_admin.roles.append(self.admin_role)
        db.session.add(u_admin)

        u_cust = User(email='cust_test@example.com')
        u_cust.set_password('budi123')
        u_cust.roles.append(self.customer_role)
        db.session.add(u_cust)
        db.session.flush()
        c = Customer(user_id=u_cust.id, name='Budi', phone='081234567890', address='Alamat')
        db.session.add(c)
        db.session.commit()

        self.client.post('/auth/login', data={
            'email': 'admin_test@example.com',
            'password': 'admin123'
        }, follow_redirects=True)

        response = self.client.post(f'/admin/customer/{c.id}/delete', follow_redirects=True)
        self.assertIn(b'berhasil dihapus permanen', response.data)

        deleted_cust = db.session.get(Customer, c.id)
        deleted_user = db.session.get(User, u_cust.id)
        self.assertIsNone(deleted_cust)
        self.assertIsNone(deleted_user)

if __name__ == '__main__':
    unittest.main()
