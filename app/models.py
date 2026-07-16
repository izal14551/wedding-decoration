from datetime import datetime
import uuid
from app import db, login_manager
from flask_security import UserMixin, RoleMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Many-to-many relationship helper table for roles and users
roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)

# Role Model
class Role(db.Model, RoleMixin):
    __tablename__ = 'role'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))

    def __repr__(self):
        return f'<Role {self.name}>'

# User Model (Centralized Auth & Security)
class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False) # flask-security expects 'password'
    active = db.Column(db.Boolean(), default=True)
    fs_uniquifier = db.Column(db.String(64), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))
    customer = db.relationship('Customer', backref='user', uselist=False, cascade="all, delete-orphan")
    admin = db.relationship('Admin', backref='user', uselist=False, cascade="all, delete-orphan")

    def set_password(self, password_plain):
        from flask_security.utils import hash_password
        self.password = hash_password(password_plain)

    def check_password(self, password_plain):
        from flask_security.utils import verify_password
        return verify_password(password_plain, self.password)

    def is_admin(self):
        return any(role.name == 'admin' for role in self.roles)

    # Compatibility properties for current_user
    @property
    def name(self):
        if self.is_admin() and self.admin:
            return self.admin.name
        elif self.customer:
            return self.customer.name
        return None

    @property
    def phone(self):
        if self.is_admin() and self.admin:
            return self.admin.phone
        elif self.customer:
            return self.customer.phone
        return None

    @property
    def address(self):
        if not self.is_admin() and self.customer:
            return self.customer.address
        return None

    def __repr__(self):
        return f'<User {self.email}>'

# 1. Customer (linked to User)
class Customer(db.Model):
    __tablename__ = 'customer'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    orders = db.relationship('Order', backref='customer', lazy='dynamic')

    @property
    def email(self):
        return self.user.email if self.user else None

    def set_password(self, password_plain):
        if self.user:
            self.user.set_password(password_plain)

    def check_password(self, password_plain):
        return self.user.check_password(password_plain) if self.user else False

    def is_admin(self):
        return False

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
    image_path = db.Column(db.String(255), nullable=True)
    
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

# 7. Admin (linked to User)
class Admin(db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    verified_payments = db.relationship('Payment', backref='admin', lazy='dynamic')
    reports = db.relationship('Report', backref='admin', lazy='dynamic')

    @property
    def email(self):
        return self.user.email if self.user else None

    def set_password(self, password_plain):
        if self.user:
            self.user.set_password(password_plain)

    def check_password(self, password_plain):
        return self.user.check_password(password_plain) if self.user else False

    def is_admin(self):
        return True

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
    order_id = db.Column(db.Integer, db.ForeignKey('order.id', ondelete='CASCADE'), nullable=True)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(50), default='Available')

    # Relationship with Order
    order = db.relationship('Order', backref=db.backref('schedules', lazy='dynamic', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<Schedule {self.id}>'

# Flask-Login user_loader (integrated with Flask-Security User model)
@login_manager.user_loader
def load_user(user_id):
    if not user_id:
        return None
    try:
        return db.session.get(User, int(user_id))
    except ValueError:
        return None

# Aliases for backward compatibility
Transaction = Payment
Kategori = Category
Barang = Product
Pesanan = Order
DetailPesanan = OrderItem
Pembayaran = Payment
Laporan = Report
Jadwal = Schedule
