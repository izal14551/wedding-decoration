from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# 1. Customer (formerly Pelanggan)
class Customer(UserMixin, db.Model):
    __tablename__ = 'customer'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    orders = db.relationship('Order', backref='customer', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return False

    def get_id(self):
        return f"customer_{self.id}"

    def __repr__(self):
        return f'<Customer {self.email}>'

# 2. Category (formerly Kategori)
class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    products = db.relationship('Product', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'

# 3. Product (formerly Barang)
class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, default=0)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='Active')
    
    order_items = db.relationship('OrderItem', backref='product', lazy='dynamic')
    schedules = db.relationship('Schedule', backref='product', lazy='dynamic')

    def __repr__(self):
        return f'<Product {self.name}>'

# 4. Order (formerly Pesanan)
class Order(db.Model):
    __tablename__ = 'order'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    order_date = db.Column(db.Date, default=datetime.utcnow().date)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    event_address = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(50), default='Pending')
    
    order_items = db.relationship('OrderItem', backref='order', lazy='dynamic', cascade="all, delete-orphan")
    payment = db.relationship('Payment', backref='order', uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Order {self.id}>'

# 5. OrderItem (formerly DetailPesanan)
class OrderItem(db.Model):
    __tablename__ = 'order_item'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Numeric(10, 2), nullable=False)

    def __repr__(self):
        return f'<OrderItem {self.id}>'

# 6. Payment (formerly Pembayaran)
class Payment(db.Model):
    __tablename__ = 'payment'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=True)
    payment_date = db.Column(db.Date, default=datetime.utcnow().date)
    payment_method = db.Column(db.String(50))
    payment_proof = db.Column(db.Text)
    status = db.Column(db.String(50), default='Pending')

    def __repr__(self):
        return f'<Payment {self.id}>'

# 7. Admin
class Admin(UserMixin, db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    verified_payments = db.relationship('Payment', backref='admin', lazy='dynamic')
    reports = db.relationship('Report', backref='admin', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return True

    def get_id(self):
        return f"admin_{self.id}"

    def __repr__(self):
        return f'<Admin {self.email}>'

# 8. Report (formerly Laporan)
class Report(db.Model):
    __tablename__ = 'report'
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow().date)
    total_transaction = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.Text)

    def __repr__(self):
        return f'<Report {self.id}>'

# 9. Schedule (formerly Jadwal)
class Schedule(db.Model):
    __tablename__ = 'schedule'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(50), default='Available')

    def __repr__(self):
        return f'<Schedule {self.id}>'

# Flask-Login user_loader
@login_manager.user_loader
def load_user(id_str):
    if not id_str:
        return None
    try:
        if id_str.startswith('admin_'):
            admin_id = int(id_str.split('_')[1])
            return db.session.get(Admin, admin_id)
        elif id_str.startswith('customer_'):
            customer_id = int(id_str.split('_')[1])
            return db.session.get(Customer, customer_id)
    except (ValueError, IndexError):
        return None
    return None

# Aliases for backward compatibility
User = Customer
Transaction = Payment
Kategori = Category
Barang = Product
Pesanan = Order
DetailPesanan = OrderItem
Pembayaran = Payment
Laporan = Report
Jadwal = Schedule
