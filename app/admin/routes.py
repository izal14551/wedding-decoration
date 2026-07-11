import os
import uuid
from datetime import date, datetime, timedelta
from collections import defaultdict
from flask import render_template, redirect, url_for, flash, request, abort
from sqlalchemy import func
from app import db
from app.admin import bp
from app.models import Customer, Product, Order, OrderItem, Payment, Schedule, User, Category
from flask_login import login_required, current_user
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            return redirect(url_for('customer.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/')
@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    today = date.today()

    # 1. Summary Cards
    total_orders = Order.query.count()
    total_customers = Customer.query.count()
    total_products = Product.query.count()
    
    revenue_query = db.session.query(func.sum(Order.total_price)).filter(Order.status != 'Cancelled').scalar()
    total_revenue = float(revenue_query) if revenue_query else 0.0

    # 2. Order Status Overview (Pie Chart)
    status_counts = db.session.query(
        Order.status, func.count(Order.id)
    ).group_by(Order.status).all()
    
    status_data = {status: count for status, count in status_counts}
    for s in ['Pending', 'Processing', 'Completed', 'Cancelled']:
        if s not in status_data:
            status_data[s] = 0

    # 3. Revenue Chart (6 bulan terakhir)
    six_months_ago = today - timedelta(days=180)
    monthly_rev = db.session.query(
        Order.order_date, Order.total_price
    ).filter(
        Order.status != 'Cancelled',
        Order.order_date >= six_months_ago
    ).all()
    
    revenue_by_month = defaultdict(float)
    for tgl, harga in monthly_rev:
        month_str = tgl.strftime('%B %Y')
        revenue_by_month[month_str] += float(harga)
        
    months_labels = []
    revenue_values = []
    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year
        if m <= 0:
            m += 12
            y -= 1
        d = date(y, m, 1)
        month_label = d.strftime('%B %Y')
        months_labels.append(month_label)
        revenue_values.append(revenue_by_month.get(month_label, 0.0))

    # 4. Upcoming Events
    upcoming_events = Order.query.filter(
        Order.start_date >= today,
        Order.status != 'Cancelled'
    ).order_by(Order.start_date.asc()).limit(5).all()

    # 5. Decoration Availability
    all_products = Product.query.all()
    decor_availability = []
    for product in all_products:
        rented_today = Schedule.query.filter_by(
            product_id=product.id,
            date=today,
            status='Rented'
        ).count()
        maintenance_today = Schedule.query.filter_by(
            product_id=product.id,
            date=today,
            status='Maintenance'
        ).count()
        
        available_qty = max(0, product.stock - rented_today - maintenance_today)
        
        if maintenance_today > 0 and available_qty == 0:
            status_desc = 'Maintenance'
        elif rented_today >= product.stock:
            status_desc = 'Fully Booked'
        else:
            status_desc = 'Available'
            
        decor_availability.append({
            'product_id': product.id,
            'name': product.name,
            'stock': product.stock,
            'rented': rented_today,
            'maintenance': maintenance_today,
            'available': available_qty,
            'status': status_desc
        })

    # 6. Recent Orders
    recent_orders = Order.query.order_by(Order.id.desc()).limit(5).all()

    # 7. Recent Payments
    recent_payments = Payment.query.order_by(Payment.id.desc()).limit(5).all()

    # 8. Top Rented Decorations
    top_rented_query = db.session.query(
        Product.name, func.sum(OrderItem.quantity)
    ).join(
        OrderItem, Product.id == OrderItem.product_id
    ).join(
        Order, OrderItem.order_id == Order.id
    ).filter(
        Order.status != 'Cancelled'
    ).group_by(
        Product.name
    ).order_by(
        func.sum(OrderItem.quantity).desc()
    ).limit(5).all()
    
    top_rented = [{'name': item[0], 'total_rented': item[1]} for item in top_rented_query]

    return render_template(
        'admin/dashboard.html',
        title='Admin Dashboard',
        today=today,
        total_orders=total_orders,
        total_customers=total_customers,
        total_products=total_products,
        total_revenue=total_revenue,
        status_data=status_data,
        months_labels=months_labels,
        revenue_values=revenue_values,
        upcoming_events=upcoming_events,
        decor_availability=decor_availability,
        recent_orders=recent_orders,
        recent_payments=recent_payments,
        top_rented=top_rented
    )

@bp.route('/customers')
@login_required
@admin_required
def customers():
    customers_list = Customer.query.join(User).all()
    
    total_cust = len(customers_list)
    active_cust = sum(1 for c in customers_list if c.is_active)
    inactive_cust = total_cust - active_cust
    
    return render_template(
        'admin/customers.html',
        title='Kelola Pelanggan',
        customers=customers_list,
        total_customers=total_cust,
        active_customers=active_cust,
        inactive_customers=inactive_cust
    )

@bp.route('/customer/<int:customer_id>/toggle_status', methods=['POST'])
@login_required
@admin_required
def customer_toggle_status(customer_id):
    customer = db.session.get(Customer, customer_id)
    if not customer:
        flash('Pelanggan tidak ditemukan.', 'danger')
        return redirect(url_for('admin.customers'))
        
    customer.is_active = not customer.is_active
    if customer.user:
        customer.user.active = customer.is_active
        
    db.session.commit()
    
    status_str = 'diaktifkan' if customer.is_active else 'dinonaktifkan'
    flash(f'Akun {customer.name} berhasil {status_str}.', 'success')
    return redirect(url_for('admin.customers'))

@bp.route('/customer/<int:customer_id>/delete', methods=['POST'])
@login_required
@admin_required
def customer_delete(customer_id):
    customer = db.session.get(Customer, customer_id)
    if not customer:
        flash('Pelanggan tidak ditemukan.', 'danger')
        return redirect(url_for('admin.customers'))
        
    name = customer.name
    user = customer.user
    if user:
        db.session.delete(user)
    else:
        db.session.delete(customer)
        
    db.session.commit()
    flash(f'Akun pelanggan {name} berhasil dihapus permanen.', 'success')
    return redirect(url_for('admin.customers'))

@bp.route('/categories')
@login_required
@admin_required
def categories():
    categories_list = Category.query.all()
    return render_template(
        'admin/categories.html',
        title='Kelola Kategori',
        categories=categories_list
    )

@bp.route('/category/add', methods=['POST'])
@login_required
@admin_required
def category_add():
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    
    if not name:
        flash('Nama kategori wajib diisi.', 'danger')
        return redirect(url_for('admin.categories'))
        
    # Periksa keunikan nama kategori
    existing_category = Category.query.filter_by(name=name).first()
    if existing_category:
        flash(f'Kategori dengan nama "{name}" sudah ada.', 'danger')
        return redirect(url_for('admin.categories'))
        
    new_category = Category(name=name, description=description)
    db.session.add(new_category)
    db.session.commit()
    
    flash(f'Kategori "{name}" berhasil ditambahkan.', 'success')
    return redirect(url_for('admin.categories'))

@bp.route('/category/<int:category_id>/edit', methods=['POST'])
@login_required
@admin_required
def category_edit(category_id):
    category = db.session.get(Category, category_id)
    if not category:
        flash('Kategori tidak ditemukan.', 'danger')
        return redirect(url_for('admin.categories'))
        
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    
    if not name:
        flash('Nama kategori wajib diisi.', 'danger')
        return redirect(url_for('admin.categories'))
        
    # Periksa keunikan nama kategori jika nama diubah
    if name != category.name:
        existing_category = Category.query.filter_by(name=name).first()
        if existing_category:
            flash(f'Kategori dengan nama "{name}" sudah ada.', 'danger')
            return redirect(url_for('admin.categories'))
            
    old_name = category.name
    category.name = name
    category.description = description
    db.session.commit()
    
    flash(f'Kategori "{old_name}" berhasil diubah menjadi "{name}".', 'success')
    return redirect(url_for('admin.categories'))

@bp.route('/category/<int:category_id>/delete', methods=['POST'])
@login_required
@admin_required
def category_delete(category_id):
    category = db.session.get(Category, category_id)
    if not category:
        flash('Kategori tidak ditemukan.', 'danger')
        return redirect(url_for('admin.categories'))
        
    # Aturan Bisnis: Kategori yang memiliki produk terkait tidak boleh dihapus
    product_count = category.products.count()
    if product_count > 0:
        flash(f'Kategori "{category.name}" tidak dapat dihapus karena masih digunakan oleh {product_count} produk.', 'danger')
        return redirect(url_for('admin.categories'))
        
    name = category.name
    db.session.delete(category)
    db.session.commit()
    
    flash(f'Kategori "{name}" berhasil dihapus.', 'success')
    return redirect(url_for('admin.categories'))

# Definisikan UPLOAD_FOLDER dan ALLOWED_EXTENSIONS
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'uploads', 'products')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/products')
@login_required
@admin_required
def products():
    products_list = Product.query.all()
    categories_list = Category.query.all()
    return render_template(
        'admin/products.html',
        title='Kelola Barang & Jasa',
        products=products_list,
        categories=categories_list
    )

@bp.route('/product/add', methods=['POST'])
@login_required
@admin_required
def product_add():
    name = request.form.get('name', '').strip()
    category_id = request.form.get('category_id')
    price_raw = request.form.get('price', '0')
    stock_raw = request.form.get('stock', '0')
    description = request.form.get('description', '').strip()
    status = request.form.get('status', 'Active')
    
    if not name or not category_id:
        flash('Nama barang dan Kategori wajib diisi.', 'danger')
        return redirect(url_for('admin.products'))
        
    try:
        price = float(price_raw)
        stock = int(stock_raw)
    except ValueError:
        flash('Harga sewa harus angka dan Stok/Slot harus bilangan bulat.', 'danger')
        return redirect(url_for('admin.products'))
        
    # Proses Upload Foto
    image_file = request.files.get('image')
    filename_saved = None
    
    if image_file and image_file.filename != '':
        if allowed_file(image_file.filename):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            # Buat nama file unik
            ext = image_file.filename.rsplit('.', 1)[1].lower()
            filename_saved = f"{uuid.uuid4().hex}.{ext}"
            file_path = os.path.join(UPLOAD_FOLDER, filename_saved)
            image_file.save(file_path)
        else:
            flash('Tipe file tidak didukung. Hanya diperbolehkan png, jpg, jpeg, webp.', 'danger')
            return redirect(url_for('admin.products'))
            
    new_product = Product(
        name=name,
        category_id=int(category_id),
        price=price,
        stock=stock,
        description=description,
        status=status,
        image_path=filename_saved
    )
    db.session.add(new_product)
    db.session.commit()
    
    flash(f'Barang "{name}" berhasil ditambahkan.', 'success')
    return redirect(url_for('admin.products'))

@bp.route('/product/<int:product_id>/edit', methods=['POST'])
@login_required
@admin_required
def product_edit(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        flash('Barang tidak ditemukan.', 'danger')
        return redirect(url_for('admin.products'))
        
    name = request.form.get('name', '').strip()
    category_id = request.form.get('category_id')
    price_raw = request.form.get('price', '0')
    stock_raw = request.form.get('stock', '0')
    description = request.form.get('description', '').strip()
    status = request.form.get('status', 'Active')
    
    if not name or not category_id:
        flash('Nama barang dan Kategori wajib diisi.', 'danger')
        return redirect(url_for('admin.products'))
        
    try:
        price = float(price_raw)
        stock = int(stock_raw)
    except ValueError:
        flash('Harga sewa harus angka dan Stok/Slot harus bilangan bulat.', 'danger')
        return redirect(url_for('admin.products'))
        
    # Proses Upload Foto Baru
    image_file = request.files.get('image')
    if image_file and image_file.filename != '':
        if allowed_file(image_file.filename):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            # Hapus file gambar lama jika ada
            if product.image_path:
                old_file_path = os.path.join(UPLOAD_FOLDER, product.image_path)
                if os.path.exists(old_file_path):
                    try:
                        os.remove(old_file_path)
                    except OSError:
                        pass
            
            # Simpan file baru
            ext = image_file.filename.rsplit('.', 1)[1].lower()
            filename_saved = f"{uuid.uuid4().hex}.{ext}"
            file_path = os.path.join(UPLOAD_FOLDER, filename_saved)
            image_file.save(file_path)
            product.image_path = filename_saved
        else:
            flash('Tipe file tidak didukung. Hanya diperbolehkan png, jpg, jpeg, webp.', 'danger')
            return redirect(url_for('admin.products'))
            
    product.name = name
    product.category_id = int(category_id)
    product.price = price
    product.stock = stock
    product.description = description
    product.status = status
    db.session.commit()
    
    flash(f'Informasi barang "{name}" berhasil diperbarui.', 'success')
    return redirect(url_for('admin.products'))

@bp.route('/product/<int:product_id>/delete', methods=['POST'])
@login_required
@admin_required
def product_delete(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        flash('Barang tidak ditemukan.', 'danger')
        return redirect(url_for('admin.products'))
        
    # Periksa apakah barang sudah disewa oleh order tertentu
    order_count = product.order_items.count()
    if order_count > 0:
        flash(f'Barang "{product.name}" tidak dapat dihapus karena telah disewa dalam {order_count} transaksi.', 'danger')
        return redirect(url_for('admin.products'))
        
    name = product.name
    # Hapus file gambar dari server
    if product.image_path:
        file_path = os.path.join(UPLOAD_FOLDER, product.image_path)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
                
    db.session.delete(product)
    db.session.commit()
    
    flash(f'Barang "{name}" berhasil dihapus dari sistem.', 'success')
    return redirect(url_for('admin.products'))
