import unittest
import io
import os
from app import create_app, db
from app.models import User, Role, Admin, Customer, SiteSetting
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    WTF_CSRF_ENABLED = False

class AdminSettingsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Role default
        self.admin_role = Role(name='admin', description='Administrator')
        self.customer_role = Role(name='customer', description='Pelanggan')
        db.session.add_all([self.admin_role, self.customer_role])
        db.session.commit()
        
        # User Admin
        self.u_admin = User(email='admin@example.com')
        self.u_admin.set_password('admin123')
        self.u_admin.roles.append(self.admin_role)
        db.session.add(self.u_admin)
        db.session.flush()
        self.admin = Admin(user_id=self.u_admin.id, name='Admin Utama', phone='081234567890')
        db.session.add(self.admin)
        
        # User Customer
        self.u_cust = User(email='customer@example.com')
        self.u_cust.set_password('cust123')
        self.u_cust.roles.append(self.customer_role)
        db.session.add(self.u_cust)
        db.session.flush()
        self.customer = Customer(user_id=self.u_cust.id, name='Pelanggan Tes', phone='087711223344', address='Jogja')
        db.session.add(self.customer)
        
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_site_setting_model_get_set(self):
        """Uji method static get() dan set() pada model SiteSetting."""
        self.assertEqual(SiteSetting.get('brand_name', 'Default Name'), 'Default Name')
        
        SiteSetting.set('brand_name', 'Griya Saraswati Custom')
        db.session.commit()
        
        self.assertEqual(SiteSetting.get('brand_name'), 'Griya Saraswati Custom')
        
        # Update nilai yang sudah ada
        SiteSetting.set('brand_name', 'Griya Saraswati Updated')
        db.session.commit()
        
        self.assertEqual(SiteSetting.get('brand_name'), 'Griya Saraswati Updated')

    def test_settings_route_access_control(self):
        """Uji hak akses halaman /admin/settings."""
        # 1. Tanpa Login -> Redirect ke login
        res_unauth = self.client.get('/admin/settings')
        self.assertEqual(res_unauth.status_code, 302)
        
        # 2. Login sebagai Customer -> Redirect ke index/home
        self.client.post('/auth/login', data={'email': 'customer@example.com', 'password': 'cust123'})
        res_cust = self.client.get('/admin/settings')
        self.assertEqual(res_cust.status_code, 302)
        self.client.get('/auth/logout')
        
        # 3. Login sebagai Admin -> 200 OK
        self.client.post('/auth/login', data={'email': 'admin@example.com', 'password': 'admin123'})
        res_admin = self.client.get('/admin/settings')
        self.assertEqual(res_admin.status_code, 200)
        self.assertIn(b'Site Settings', res_admin.data)

    def test_save_settings_text_fields(self):
        """Uji penyimpanan form pengaturan teks oleh admin."""
        self.client.post('/auth/login', data={'email': 'admin@example.com', 'password': 'admin123'})
        
        payload = {
            'brand_name': 'Griya Wedding Platinum',
            'brand_tagline': 'Momen Indah Tak Terlupakan',
            'hero_title': 'Selamat Datang di Griya Wedding',
            'hero_subtitle': 'Layanan Dekorasi Terlengkap',
            'why_choose_us_p1': 'Paragraf alasan pertama.',
            'why_choose_us_p2': 'Paragraf alasan kedua.',
            'gallery_title': 'Galeri Momen Pengantin',
            'gallery_caption_1': 'Dekorasi Tenda',
            'footer_description': 'Deskripsi footer custom.',
            'footer_address': 'Jl. Kaliurang KM 5',
            'footer_phone': '089988776655',
            'footer_email': 'kontak@griyawedding.com',
            'footer_hours': '08.00 - 17.00 WIB',
            'social_whatsapp': 'https://wa.me/6289988776655',
            'social_instagram': 'https://instagram.com/griyawedding',
            'social_facebook': 'https://facebook.com/griyawedding',
            'social_tiktok': 'https://tiktok.com/@griyawedding',
            'invoice_company_name': 'Griya Wedding PT',
            'invoice_tagline': 'Invoice Resmi',
            'invoice_address': 'Yogyakarta',
            'invoice_phone': '089988776655'
        }
        
        res = self.client.post('/admin/settings', data=payload, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn('Pengaturan situs berhasil disimpan!'.encode('utf-8'), res.data)
        
        # Verifikasi data tersimpan di database
        self.assertEqual(SiteSetting.get('brand_name'), 'Griya Wedding Platinum')
        self.assertEqual(SiteSetting.get('hero_title'), 'Selamat Datang di Griya Wedding')
        self.assertEqual(SiteSetting.get('footer_phone'), '089988776655')
        self.assertEqual(SiteSetting.get('invoice_company_name'), 'Griya Wedding PT')

    def test_save_settings_image_file_upload(self):
        """Uji upload berkas logo dan hero background."""
        self.client.post('/auth/login', data={'email': 'admin@example.com', 'password': 'admin123'})
        
        logo_file = (io.BytesIO(b"fake image logo bytes"), "custom_logo.png")
        hero_bg_file = (io.BytesIO(b"fake image hero bg bytes"), "custom_hero.jpg")
        
        data = {
            'brand_name': 'Griya Brand Logo Test',
            'logo_path': logo_file,
            'hero_bg_path': hero_bg_file
        }
        
        res = self.client.post('/admin/settings', data=data, content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        
        saved_logo = SiteSetting.get('logo_path')
        saved_hero_bg = SiteSetting.get('hero_bg_path')
        
        self.assertTrue(saved_logo.startswith('uploads/settings/logo_path_'))
        self.assertTrue(saved_hero_bg.startswith('uploads/settings/hero_bg_path_'))
        
        # Hapus berkas dummy yang terbuat saat tes
        upload_folder = self.app.config['UPLOAD_FOLDER']
        for p in [saved_logo, saved_hero_bg]:
            full_path = os.path.join(upload_folder, 'settings', os.path.basename(p))
            if os.path.exists(full_path):
                os.remove(full_path)

    def test_settings_rendered_on_customer_pages(self):
        """Uji bahwa nilai pengaturan dari admin otomatis tampil di halaman publik/pelanggan."""
        # Set data custom
        SiteSetting.set('brand_name', 'Griya Saraswati Test Brand')
        SiteSetting.set('hero_title', 'Hero Title Test')
        SiteSetting.set('footer_phone', '08123999888777')
        db.session.commit()
        
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Griya Saraswati Test Brand', res.data)
        self.assertIn(b'Hero Title Test', res.data)
        self.assertIn(b'08123999888777', res.data)

if __name__ == '__main__':
    unittest.main()
