import unittest
import io
from datetime import date
from app import create_app, db
from app.models import User, Role, Customer, Admin, Category, Product, Order, OrderItem, Schedule, Payment
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    WTF_CSRF_ENABLED = False

class AdminTestCase(unittest.TestCase):
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

    def test_admin_crud_category_access_protection(self):
        """Uji rute kategori dilindungi dan menolak pelanggan biasa"""
        # Buat Pelanggan biasa
        u_cust = User(email='cust@example.com')
        u_cust.set_password('cust123')
        u_cust.roles.append(self.customer_role)
        db.session.add(u_cust)
        db.session.flush()
        c = Customer(user_id=u_cust.id, name='Budi', phone='081234567890', address='Alamat')
        db.session.add(c)
        db.session.commit()

        # Login Pelanggan
        self.client.post('/auth/login', data={
            'email': 'cust@example.com',
            'password': 'cust123'
        }, follow_redirects=True)

        # Coba buka halaman kelola kategori (harus diredirect/ditolak)
        response = self.client.get('/admin/categories', follow_redirects=True)
        self.assertNotIn(b'Manajemen Kategori', response.data)

        # Coba tambah kategori (harus diredirect/ditolak)
        response_add = self.client.post('/admin/category/add', data={
            'name': 'Tata Rias',
            'description': 'Layanan rias'
        }, follow_redirects=True)
        self.assertNotIn(b'berhasil ditambahkan', response_add.data)

    def test_admin_category_crud_workflow(self):
        """Uji sukses alur CRUD kategori oleh admin (Tambah, Edit, Hapus)"""
        # Buat Admin
        u_admin = User(email='admin_test@example.com')
        u_admin.set_password('admin123')
        u_admin.roles.append(self.admin_role)
        db.session.add(u_admin)
        db.session.commit()

        # Login Admin
        self.client.post('/auth/login', data={
            'email': 'admin_test@example.com',
            'password': 'admin123'
        }, follow_redirects=True)

        # 1. Tambah Kategori
        response_add = self.client.post('/admin/category/add', data={
            'name': 'Tenda Pesta',
            'description': 'Kategori untuk menyewakan tenda acara'
        }, follow_redirects=True)
        self.assertIn(b'Tenda Pesta', response_add.data)
        self.assertIn(b'berhasil ditambahkan', response_add.data)
        
        # Periksa di DB
        cat = Category.query.filter_by(name='Tenda Pesta').first()
        self.assertIsNotNone(cat)
        self.assertEqual(cat.description, 'Kategori untuk menyewakan tenda acara')

        # 2. Edit Kategori
        response_edit = self.client.post(f'/admin/category/{cat.id}/edit', data={
            'name': 'Tenda Premium',
            'description': 'Kategori tenda ber-AC'
        }, follow_redirects=True)
        self.assertIn(b'berhasil diubah menjadi', response_edit.data)
        self.assertIn(b'Tenda Premium', response_edit.data)
        
        # Periksa di DB
        db.session.refresh(cat)
        self.assertEqual(cat.name, 'Tenda Premium')
        self.assertEqual(cat.description, 'Kategori tenda ber-AC')

        # 3. Hapus Kategori
        response_delete = self.client.post(f'/admin/category/{cat.id}/delete', follow_redirects=True)
        self.assertIn(b'Tenda Premium', response_delete.data)
        self.assertIn(b'berhasil dihapus', response_delete.data)
        
        # Periksa di DB
        deleted_cat = Category.query.filter_by(name='Tenda Premium').first()
        self.assertIsNone(deleted_cat)

    def test_admin_category_validation(self):
        """Uji kegagalan validasi (nama kosong, nama duplikat)"""
        # Buat Admin
        u_admin = User(email='admin_test@example.com')
        u_admin.set_password('admin123')
        u_admin.roles.append(self.admin_role)
        db.session.add(u_admin)
        db.session.commit()

        # Login Admin
        self.client.post('/auth/login', data={
            'email': 'admin_test@example.com',
            'password': 'admin123'
        }, follow_redirects=True)

        # Coba tambah kategori tanpa nama (kosong)
        response_empty = self.client.post('/admin/category/add', data={
            'name': '',
            'description': 'Tanpa nama'
        }, follow_redirects=True)
        self.assertIn(b'Nama kategori wajib diisi.', response_empty.data)

        # Buat kategori awal
        cat1 = Category(name='Makeup Pengantin', description='Rias')
        db.session.add(cat1)
        db.session.commit()

        # Coba tambah kategori dengan nama duplikat
        response_dup = self.client.post('/admin/category/add', data={
            'name': 'Makeup Pengantin',
            'description': 'Rias duplikat'
        }, follow_redirects=True)
        self.assertIn(b'Makeup Pengantin', response_dup.data)
        self.assertIn(b'sudah ada', response_dup.data)

    def test_admin_category_delete_protection_with_products(self):
        """Uji pencegahan penghapusan kategori jika memiliki produk terkait"""
        # Buat Admin
        u_admin = User(email='admin_test@example.com')
        u_admin.set_password('admin123')
        u_admin.roles.append(self.admin_role)
        db.session.add(u_admin)

        # Buat Kategori & Produk
        cat = Category(name='Tenda', description='Kategori tenda')
        db.session.add(cat)
        db.session.flush()

        prod = Product(category_id=cat.id, name='Tenda Sederhana', price=500000.0, stock=2, description='Tenda 4x4')
        db.session.add(prod)
        db.session.commit()

        # Login Admin
        self.client.post('/auth/login', data={
            'email': 'admin_test@example.com',
            'password': 'admin123'
        }, follow_redirects=True)

        # Coba hapus kategori (harus ditolak karena ada produk)
        response = self.client.post(f'/admin/category/{cat.id}/delete', follow_redirects=True)
        self.assertIn(b'tidak dapat dihapus karena masih digunakan', response.data)
        
        # Periksa di DB (kategori harus tetap ada)
        db_cat = db.session.get(Category, cat.id)
        self.assertIsNotNone(db_cat)

    def test_admin_crud_product_access_protection(self):
        """Uji rute manajemen barang dilindungi dan menolak pelanggan biasa"""
        # Buat Pelanggan biasa
        u_cust = User(email='cust_prod@example.com')
        u_cust.set_password('cust123')
        u_cust.roles.append(self.customer_role)
        db.session.add(u_cust)
        db.session.flush()
        c = Customer(user_id=u_cust.id, name='Budi', phone='081234567890', address='Alamat')
        db.session.add(c)
        db.session.commit()

        # Login Pelanggan
        self.client.post('/auth/login', data={
            'email': 'cust_prod@example.com',
            'password': 'cust123'
        }, follow_redirects=True)

        # Coba buka halaman kelola barang
        response = self.client.get('/admin/products', follow_redirects=True)
        self.assertNotIn(b'Manajemen Dekorasi & Layanan', response.data)

        # Coba tambah barang
        response_add = self.client.post('/admin/product/add', data={
            'name': 'Barang Ilegal',
            'category_id': '1'
        }, follow_redirects=True)
        self.assertNotIn(b'berhasil ditambahkan', response_add.data)

    def test_admin_product_crud_workflow(self):
        """Uji sukses alur CRUD barang oleh admin (Tambah dengan file, Edit, Hapus)"""
        # Buat Admin
        u_admin = User(email='admin_prod@example.com')
        u_admin.set_password('admin123')
        u_admin.roles.append(self.admin_role)
        db.session.add(u_admin)

        # Buat Kategori
        cat = Category(name='Rias Wajah', description='Makeup')
        db.session.add(cat)
        db.session.commit()

        # Login Admin
        self.client.post('/auth/login', data={
            'email': 'admin_prod@example.com',
            'password': 'admin123'
        }, follow_redirects=True)

        # 1. Tambah Produk dengan Simulasi Upload Gambar
        data_add = {
            'name': 'Makeup Pengantin Adat',
            'category_id': str(cat.id),
            'price': '1500000',
            'stock': '2',
            'description': 'Layanan makeup adat premium',
            'status': 'Active',
            'image': (io.BytesIO(b"fake image bytes"), 'pengantin.png')
        }
        response_add = self.client.post('/admin/product/add', data=data_add, content_type='multipart/form-data', follow_redirects=True)
        self.assertIn(b'Makeup Pengantin Adat', response_add.data)
        self.assertIn(b'berhasil ditambahkan', response_add.data)

        # Periksa di DB
        prod = Product.query.filter_by(name='Makeup Pengantin Adat').first()
        self.assertIsNotNone(prod)
        self.assertEqual(prod.price, 1500000.0)
        self.assertEqual(prod.stock, 2)
        self.assertIsNotNone(prod.image_path)

        # 2. Edit Produk
        data_edit = {
            'name': 'Makeup Pengantin Adat Premium',
            'category_id': str(cat.id),
            'price': '2000000',
            'stock': '3',
            'description': 'Layanan makeup premium terupdate',
            'status': 'Active',
            'image': (io.BytesIO(b"updated image bytes"), 'pengantin_updated.png')
        }
        response_edit = self.client.post(f'/admin/product/{prod.id}/edit', data=data_edit, content_type='multipart/form-data', follow_redirects=True)
        self.assertIn(b'Makeup Pengantin Adat Premium', response_edit.data)
        self.assertIn(b'berhasil diperbarui', response_edit.data)

        # Periksa di DB
        db.session.refresh(prod)
        self.assertEqual(prod.name, 'Makeup Pengantin Adat Premium')
        self.assertEqual(prod.price, 2000000.0)
        self.assertEqual(prod.stock, 3)

        # 3. Hapus Produk
        response_delete = self.client.post(f'/admin/product/{prod.id}/delete', follow_redirects=True)
        self.assertIn(b'berhasil dihapus', response_delete.data)

        # Periksa di DB
        deleted_prod = Product.query.filter_by(name='Makeup Pengantin Adat Premium').first()
        self.assertIsNone(deleted_prod)

    def test_admin_product_delete_protection_with_orders(self):
        """Uji produk tidak dapat dihapus jika telah disewa (terkait order_items)"""
        # Buat Admin
        u_admin = User(email='admin_prod_protect@example.com')
        u_admin.set_password('admin123')
        u_admin.roles.append(self.admin_role)
        db.session.add(u_admin)

        # Buat Kategori & Produk
        cat = Category(name='Stage', description='Panggung')
        db.session.add(cat)
        db.session.flush()

        prod = Product(category_id=cat.id, name='Panggung Utama 6x4', price=2500000.0, stock=1, description='Panggung kayu')
        db.session.add(prod)
        db.session.flush()

        # Buat Customer & Order & OrderItem
        u_cust = User(email='cust_order@example.com')
        u_cust.set_password('cust123')
        u_cust.roles.append(self.customer_role)
        db.session.add(u_cust)
        db.session.flush()
        cust = Customer(user_id=u_cust.id, name='Siti', phone='081234567890', address='Alamat')
        db.session.add(cust)
        db.session.flush()

        order = Order(
            customer_id=cust.id,
            order_date=date.today(),
            start_date=date.today(),
            end_date=date.today(),
            event_address='Alamat Acara',
            total_price=2500000.0,
            status='Pending'
        )
        db.session.add(order)
        db.session.flush()

        order_item = OrderItem(order_id=order.id, product_id=prod.id, quantity=1, price=2500000.0)
        db.session.add(order_item)
        db.session.commit()

        # Login Admin
        self.client.post('/auth/login', data={
            'email': 'admin_prod_protect@example.com',
            'password': 'admin123'
        }, follow_redirects=True)

        # Coba hapus panggung (harus ditolak karena disewa)
        response = self.client.post(f'/admin/product/{prod.id}/delete', follow_redirects=True)
        self.assertIn(b'tidak dapat dihapus karena telah disewa', response.data)

        # Periksa di DB (harus tetap ada)
        db_prod = db.session.get(Product, prod.id)
        self.assertIsNotNone(db_prod)

    def test_admin_orders_list_access(self):
        """Uji akses daftar pesanan admin dilindungi dan menolak pelanggan biasa"""
        # 1. Buat Pelanggan biasa
        u_cust = User(email='cust_orders@example.com')
        u_cust.set_password('cust123')
        u_cust.roles.append(self.customer_role)
        db.session.add(u_cust)
        db.session.flush()
        cust = Customer(user_id=u_cust.id, name='Budi', phone='081234567890', address='Alamat')
        db.session.add(cust)
        db.session.commit()

        # Login Pelanggan
        self.client.post('/auth/login', data={'email': 'cust_orders@example.com', 'password': 'cust123'}, follow_redirects=True)

        # Akses /admin/orders (harus ditolak/diredirect)
        response = self.client.get('/admin/orders', follow_redirects=True)
        self.assertNotIn(b'Manajemen Pesanan', response.data)

        # Logout pelanggan terlebih dahulu
        self.client.get('/auth/logout', follow_redirects=True)

        # 2. Login Admin
        u_admin = User(email='admin_orders@example.com')
        u_admin.set_password('admin123')
        u_admin.roles.append(self.admin_role)
        db.session.add(u_admin)
        db.session.commit()

        self.client.post('/auth/login', data={'email': 'admin_orders@example.com', 'password': 'admin123'}, follow_redirects=True)

        # Akses /admin/orders (harus sukses)
        response_admin = self.client.get('/admin/orders', follow_redirects=True)
        self.assertEqual(response_admin.status_code, 200)
        self.assertIn(b'Manajemen Pesanan', response_admin.data)

    def test_admin_order_detail_view(self):
        """Uji admin dapat melihat detail pesanan tertentu"""
        # Buat Admin
        u_admin = User(email='admin_detail@example.com')
        u_admin.set_password('admin123')
        u_admin.roles.append(self.admin_role)
        db.session.add(u_admin)
        db.session.flush()
        
        # Buat Kategori & Produk
        cat = Category(name='Tenda', description='Tenda')
        db.session.add(cat)
        db.session.flush()
        prod = Product(category_id=cat.id, name='Tenda Gold', price=1000000.0, stock=2, description='Tenda dekorasi')
        db.session.add(prod)
        db.session.flush()

        # Buat Customer & Order
        u_cust = User(email='cust_detail@example.com')
        u_cust.set_password('cust123')
        u_cust.roles.append(self.customer_role)
        db.session.add(u_cust)
        db.session.flush()
        cust = Customer(user_id=u_cust.id, name='Siti', phone='081234567890', address='Alamat')
        db.session.add(cust)
        db.session.flush()

        order = Order(
            customer_id=cust.id,
            order_date=date.today(),
            start_date=date.today(),
            end_date=date.today(),
            event_address='Alamat Acara',
            total_price=1000000.0,
            status='Pending'
        )
        db.session.add(order)
        db.session.flush()
        order_item = OrderItem(order_id=order.id, product_id=prod.id, quantity=1, price=1000000.0)
        db.session.add(order_item)
        db.session.commit()

        # Login Admin
        self.client.post('/auth/login', data={'email': 'admin_detail@example.com', 'password': 'admin123'}, follow_redirects=True)

        # Akses detail order
        response = self.client.get(f'/admin/order/{order.id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Rincian Pesanan', response.data)
        self.assertIn(b'Tenda Gold', response.data)
        self.assertIn(b'Siti', response.data)

    def test_admin_order_status_update_workflow(self):
        """Uji alur pembaruan status pesanan oleh admin (Pending -> Cancelled -> Processing)"""
        # Buat Admin & Admin User
        u_admin = User(email='admin_workflow@example.com')
        u_admin.set_password('admin123')
        u_admin.roles.append(self.admin_role)
        db.session.add(u_admin)
        db.session.flush()
        admin_prof = Admin(user_id=u_admin.id, name='Admin Workflow', phone='08987654321')
        db.session.add(admin_prof)
        db.session.flush()
        
        # Buat Kategori & Produk
        cat = Category(name='Tenda', description='Tenda')
        db.session.add(cat)
        db.session.flush()
        prod = Product(category_id=cat.id, name='Tenda Gold', price=1000000.0, stock=2, description='Tenda dekorasi')
        db.session.add(prod)
        db.session.flush()

        # Buat Customer & Order
        u_cust = User(email='cust_workflow@example.com')
        u_cust.set_password('cust123')
        u_cust.roles.append(self.customer_role)
        db.session.add(u_cust)
        db.session.flush()
        cust = Customer(user_id=u_cust.id, name='Siti', phone='081234567890', address='Alamat')
        db.session.add(cust)
        db.session.flush()

        order = Order(
            customer_id=cust.id,
            order_date=date.today(),
            start_date=date.today(),
            end_date=date.today(),
            event_address='Alamat Acara',
            total_price=1000000.0,
            status='Pending'
        )
        db.session.add(order)
        db.session.flush()
        
        order_item = OrderItem(order_id=order.id, product_id=prod.id, quantity=1, price=1000000.0)
        db.session.add(order_item)
        
        # Simulasikan adanya jadwal Rented
        from datetime import time
        sched = Schedule(
            product_id=prod.id,
            order_id=order.id,
            date=date.today(),
            start_time=time(8, 0),
            end_time=time(22, 0),
            status='Rented'
        )
        db.session.add(sched)
        
        # Simulasikan adanya bukti pembayaran
        pay = Payment(
            order_id=order.id,
            payment_date=date.today(),
            payment_method='transfer',
            payment_proof='payments/proof.jpg',
            status='Pending'
        )
        db.session.add(pay)
        db.session.commit()

        # Login Admin
        self.client.post('/auth/login', data={'email': 'admin_workflow@example.com', 'password': 'admin123'}, follow_redirects=True)

        # 1. Ubah status ke Cancelled
        response_cancel = self.client.post(f'/admin/order/{order.id}/update_status', data={'status': 'Cancelled'}, follow_redirects=True)
        self.assertIn(b'berhasil diperbarui menjadi Cancelled', response_cancel.data)
        
        # Periksa di DB
        db.session.refresh(order)
        self.assertEqual(order.status, 'Cancelled')
        
        # Jadwal Rented harusnya terhapus (kosong)
        schedules_count = Schedule.query.filter_by(order_id=order.id).count()
        self.assertEqual(schedules_count, 0)

        # 2. Ubah status kembali dari Cancelled ke Processing
        response_processing = self.client.post(f'/admin/order/{order.id}/update_status', data={'status': 'Processing'}, follow_redirects=True)
        self.assertIn(b'berhasil diperbarui menjadi Processing', response_processing.data)
        
        # Periksa di DB
        db.session.refresh(order)
        self.assertEqual(order.status, 'Processing')
        
        # Jadwal Rented harusnya dibuat ulang
        schedules_count = Schedule.query.filter_by(order_id=order.id).count()
        self.assertEqual(schedules_count, 1)
        
        # Pembayaran otomatis Approved
        db.session.refresh(pay)
        self.assertEqual(pay.status, 'Approved')
        self.assertEqual(pay.admin_id, admin_prof.id)

    def test_admin_payments_list_access(self):
        """Uji hak akses halaman daftar verifikasi pembayaran hanya untuk admin"""
        # 1. Buat Pelanggan biasa
        u_cust = User(email='cust_pay_list@example.com')
        u_cust.set_password('cust123')
        u_cust.roles.append(self.customer_role)
        db.session.add(u_cust)
        db.session.flush()
        cust = Customer(user_id=u_cust.id, name='Budi', phone='081234567890', address='Alamat')
        db.session.add(cust)
        db.session.commit()

        # Login Pelanggan
        self.client.post('/auth/login', data={'email': 'cust_pay_list@example.com', 'password': 'cust123'}, follow_redirects=True)

        # Akses /admin/payments (harus ditolak/diredirect)
        response = self.client.get('/admin/payments', follow_redirects=True)
        self.assertNotIn(b'Verifikasi Pembayaran', response.data)

        # Logout pelanggan
        self.client.get('/auth/logout', follow_redirects=True)

        # 2. Login Admin
        u_admin = User(email='admin_pay_list@example.com')
        u_admin.set_password('admin123')
        u_admin.roles.append(self.admin_role)
        db.session.add(u_admin)
        db.session.commit()

        self.client.post('/auth/login', data={'email': 'admin_pay_list@example.com', 'password': 'admin123'}, follow_redirects=True)

        # Akses /admin/payments (harus sukses)
        response_admin = self.client.get('/admin/payments', follow_redirects=True)
        self.assertEqual(response_admin.status_code, 200)
        self.assertIn(b'Verifikasi Pembayaran', response_admin.data)

    def test_admin_verify_payment_workflow(self):
        """Uji alur persetujuan (Approve) dan penolakan (Reject) pembayaran oleh admin"""
        # Buat Admin & Admin User
        u_admin = User(email='admin_verify_workflow@example.com')
        u_admin.set_password('admin123')
        u_admin.roles.append(self.admin_role)
        db.session.add(u_admin)
        db.session.flush()
        admin_prof = Admin(user_id=u_admin.id, name='Admin Verify Workflow', phone='08987654321')
        db.session.add(admin_prof)
        db.session.flush()

        # Buat Customer, Order & Payment
        u_cust = User(email='cust_verify_workflow@example.com')
        u_cust.set_password('cust123')
        u_cust.roles.append(self.customer_role)
        db.session.add(u_cust)
        db.session.flush()
        cust = Customer(user_id=u_cust.id, name='Siti', phone='081234567890', address='Alamat')
        db.session.add(cust)
        db.session.flush()

        order = Order(
            customer_id=cust.id,
            order_date=date.today(),
            start_date=date.today(),
            end_date=date.today(),
            event_address='Alamat Acara',
            total_price=500000.0,
            status='Pending'
        )
        db.session.add(order)
        db.session.flush()

        pay = Payment(
            order_id=order.id,
            payment_date=date.today(),
            payment_method='transfer',
            payment_proof='payments/proof.jpg',
            status='Pending'
        )
        db.session.add(pay)
        db.session.commit()

        # Login Admin
        self.client.post('/auth/login', data={'email': 'admin_verify_workflow@example.com', 'password': 'admin123'}, follow_redirects=True)

        # 1. Uji Penolakan Pembayaran (Reject)
        response_reject = self.client.post(f'/admin/payment/{pay.id}/verify', data={'action': 'reject'}, follow_redirects=True)
        self.assertIn(b'telah ditolak', response_reject.data)
        
        # Cek di DB
        db.session.refresh(pay)
        self.assertEqual(pay.status, 'Rejected')
        db.session.refresh(order)
        self.assertEqual(order.status, 'Pending')

        # 2. Uji Persetujuan Pembayaran (Approve)
        pay.status = 'Pending'
        db.session.commit()

        response_approve = self.client.post(f'/admin/payment/{pay.id}/verify', data={'action': 'approve'}, follow_redirects=True)
        self.assertIn(b'berhasil disetujui', response_approve.data)
        
        # Cek di DB
        db.session.refresh(pay)
        self.assertEqual(pay.status, 'Approved')
        self.assertEqual(pay.admin_id, admin_prof.id)
        db.session.refresh(order)
        self.assertEqual(order.status, 'Processing')

if __name__ == '__main__':
    unittest.main()
