import unittest
from app import create_app, db
from app.models import Category, Product, ProductInclude, User, Role, Admin

from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    WTF_CSRF_ENABLED = False

class ProductIncludesTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Buat role admin dan user admin
        admin_role = Role(name='admin', description='Administrator')
        db.session.add(admin_role)

        admin_user = User(email='admin@test.com')
        admin_user.set_password('password123')
        admin_user.roles.append(admin_role)
        db.session.add(admin_user)
        db.session.flush()

        admin_profile = Admin(user_id=admin_user.id, name='Admin Test', phone='0812345678')
        db.session.add(admin_profile)

        # Buat kategori
        category = Category(name='Package', description='Paket Pernikahan')
        db.session.add(category)
        db.session.commit()

        self.category_id = category.id
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_product_include_model(self):
        product = Product(
            name='Paket Platinum Test',
            category_id=self.category_id,
            price=15000000.0,
            stock=5,
            description='Deskripsi paket platinum'
        )
        db.session.add(product)
        db.session.flush()

        inc1 = ProductInclude(product_id=product.id, item_name='Tenda VIP 10x20m', quantity='1 set')
        inc2 = ProductInclude(product_id=product.id, item_name='Kursi Futura', quantity='100 pcs')
        db.session.add_all([inc1, inc2])
        db.session.commit()

        fetched_product = db.session.get(Product, product.id)
        self.assertEqual(len(fetched_product.includes), 2)
        self.assertEqual(fetched_product.includes[0].item_name, 'Tenda VIP 10x20m')
        self.assertEqual(fetched_product.includes[1].quantity, '100 pcs')

    def test_admin_add_product_with_includes(self):
        # Login admin
        self.client.post('/auth/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Post product add dengan include_names[] dan include_quantities[]
        response = self.client.post('/admin/product/add', data={
            'name': 'Paket Gold Test',
            'category_id': self.category_id,
            'price': '10000000',
            'stock': '3',
            'description': 'Deskripsi Gold',
            'status': 'Active',
            'include_names[]': ['Pelaminan Bunga Segar', 'Rias Pengantin Akad'],
            'include_quantities[]': ['6 meter', '1x ganti']
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)

        product = Product.query.filter_by(name='Paket Gold Test').first()
        self.assertIsNotNone(product)
        self.assertEqual(len(product.includes), 2)
        self.assertEqual(product.includes[0].item_name, 'Pelaminan Bunga Segar')
        self.assertEqual(product.includes[1].quantity, '1x ganti')

    def test_admin_edit_product_includes(self):
        # Setup product awal
        product = Product(
            name='Paket Silver Test',
            category_id=self.category_id,
            price=8000000.0,
            stock=5
        )
        db.session.add(product)
        db.session.flush()
        inc = ProductInclude(product_id=product.id, item_name='Item Lama', quantity='1 unit')
        db.session.add(inc)
        db.session.commit()

        # Login admin
        self.client.post('/auth/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Edit product dengan include baru
        response = self.client.post(f'/admin/product/{product.id}/edit', data={
            'name': 'Paket Silver Test Updated',
            'category_id': self.category_id,
            'price': '8500000',
            'stock': '5',
            'description': 'Updated',
            'status': 'Active',
            'include_names[]': ['Item Baru 1', 'Item Baru 2'],
            'include_quantities[]': ['50 pcs', '2 set']
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        updated_product = db.session.get(Product, product.id)
        self.assertEqual(len(updated_product.includes), 2)
        self.assertEqual(updated_product.includes[0].item_name, 'Item Baru 1')

if __name__ == '__main__':
    unittest.main()
