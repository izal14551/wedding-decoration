import os
import uuid
from datetime import date, datetime, timedelta
from collections import defaultdict
from flask import render_template, redirect, url_for, flash, request, abort, current_app
from sqlalchemy import func
from werkzeug.utils import secure_filename
from app import db
from app.admin import bp
from app.models import Customer, Product, Order, OrderItem, Payment, Schedule, User, Category, SiteSetting
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

@bp.route('/orders')
@login_required
@admin_required
def orders():
    status_filter = request.args.get('status', 'All').strip()
    
    query = Order.query.order_by(Order.id.desc())
    
    if status_filter != 'All':
        if status_filter == 'Waiting for payment':
            query = query.filter(Order.status == 'Pending').outerjoin(Order.payment).filter((Payment.id == None) | (Payment.status == 'Rejected'))
        elif status_filter == 'Pending verification':
            query = query.filter(Order.status == 'Pending').join(Order.payment).filter(Payment.status == 'Pending')
        elif status_filter in ['Processing', 'Completed', 'Cancelled']:
            query = query.filter(Order.status == status_filter)
            
    orders_list = query.all()
    
    # Calculate counts for badges/tabs
    count_all = Order.query.count()
    count_waiting = Order.query.filter(Order.status == 'Pending').outerjoin(Order.payment).filter((Payment.id == None) | (Payment.status == 'Rejected')).count()
    count_verification = Order.query.filter(Order.status == 'Pending').join(Order.payment).filter(Payment.status == 'Pending').count()
    count_processing = Order.query.filter_by(status='Processing').count()
    count_completed = Order.query.filter_by(status='Completed').count()
    count_cancelled = Order.query.filter_by(status='Cancelled').count()
    
    return render_template(
        'admin/orders.html',
        title='Kelola Pesanan',
        orders=orders_list,
        current_filter=status_filter,
        counts={
            'All': count_all,
            'Waiting for payment': count_waiting,
            'Pending verification': count_verification,
            'Processing': count_processing,
            'Completed': count_completed,
            'Cancelled': count_cancelled
        }
    )

@bp.route('/order/<int:order_id>')
@login_required
@admin_required
def order_detail(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        flash('Pesanan tidak ditemukan.', 'danger')
        return redirect(url_for('admin.orders'))
        
    duration = (order.end_date - order.start_date).days
    if duration <= 0:
        duration = 1
        
    return render_template(
        'admin/order_detail.html',
        title=f'Rincian Pesanan #{order.id}',
        order=order,
        duration=duration
    )

@bp.route('/order/<int:order_id>/update_status', methods=['POST'])
@login_required
@admin_required
def order_update_status(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        flash('Pesanan tidak ditemukan.', 'danger')
        return redirect(url_for('admin.orders'))
        
    new_status = request.form.get('status')
    valid_statuses = ['Pending', 'Processing', 'Completed', 'Cancelled']
    
    if new_status not in valid_statuses:
        flash('Status tidak valid.', 'danger')
        return redirect(url_for('admin.order_detail', order_id=order.id))
        
    old_status = order.status
    if old_status == new_status:
        flash('Status tidak berubah.', 'info')
        return redirect(url_for('admin.order_detail', order_id=order.id))
        
    # LOGIC:
    # 1. If changing to 'Cancelled', release the schedules
    if new_status == 'Cancelled':
        for schedule in order.schedules.all():
            db.session.delete(schedule)
            
    # 2. If changing FROM 'Cancelled' to active, we must recreate schedules.
    #    First, check availability to prevent double-booking!
    elif old_status == 'Cancelled' and new_status in ['Pending', 'Processing', 'Completed']:
        conflict_found = False
        
        # Check stock availability for each order item
        for item in order.order_items:
            prod = item.product
            qty = item.quantity
            
            # Check availability for each date in rental range
            curr_date = order.start_date
            while curr_date <= order.end_date:
                maintenance_count = Schedule.query.filter_by(
                    product_id=prod.id,
                    date=curr_date,
                    status='Maintenance'
                ).count()
                
                offline_rentals = Schedule.query.filter(
                    Schedule.product_id == prod.id,
                    Schedule.date == curr_date,
                    Schedule.status == 'Rented',
                    Schedule.order_id == None
                ).count()
                
                active_rentals = db.session.query(func.sum(OrderItem.quantity))\
                    .join(Order, OrderItem.order_id == Order.id)\
                    .filter(
                        OrderItem.product_id == prod.id,
                        Order.status != 'Cancelled',
                        Order.id != order.id,  # Exclude current order
                        Order.start_date <= curr_date,
                        Order.end_date >= curr_date
                    ).scalar() or 0
                    
                available_stock = prod.stock - active_rentals - maintenance_count - offline_rentals
                
                if qty > available_stock:
                    is_service = 'rias' in prod.category.name.lower() or 'makeup' in prod.category.name.lower() or 'mc' in prod.category.name.lower() or 'dance' in prod.category.name.lower() or 'jasa' in prod.category.name.lower()
                    unit_name = 'Slot' if is_service else 'Unit'
                    flash(f'Gagal mengaktifkan kembali pesanan. {prod.name} tidak memiliki cukup {unit_name} pada tanggal {curr_date.strftime("%d %b %Y")} (tersedia {available_stock}).', 'danger')
                    conflict_found = True
                    break
                curr_date += timedelta(days=1)
                
            if conflict_found:
                break
                
        if conflict_found:
            return redirect(url_for('admin.order_detail', order_id=order.id))
            
        # No conflict: recreate Schedule records
        from datetime import time
        for item in order.order_items:
            prod = item.product
            qty = item.quantity
            curr_date = order.start_date
            while curr_date <= order.end_date:
                for _ in range(qty):
                    schedule = Schedule(
                        product_id=prod.id,
                        order_id=order.id,
                        date=curr_date,
                        start_time=time(8, 0),
                        end_time=time(22, 0),
                        status='Rented'
                    )
                    db.session.add(schedule)
                curr_date += timedelta(days=1)
                
    # 3. If changing to 'Processing' or 'Completed', set payment status to 'Approved' if payment exists
    if new_status in ['Processing', 'Completed'] and order.payment:
        order.payment.status = 'Approved'
        if current_user.admin:
            order.payment.admin_id = current_user.admin.id
        
    order.status = new_status
    db.session.commit()
    
    flash(f'Status pesanan #{order.id} berhasil diperbarui menjadi {new_status}.', 'success')
    return redirect(url_for('admin.order_detail', order_id=order.id))

@bp.route('/payments')
@login_required
@admin_required
def payments():
    status_filter = request.args.get('status', 'All').strip()
    
    query = Payment.query.order_by(Payment.id.desc())
    
    if status_filter != 'All':
        query = query.filter_by(status=status_filter)
        
    payments_list = query.all()
    
    # Count totals for tabs
    count_all = Payment.query.count()
    count_pending = Payment.query.filter_by(status='Pending').count()
    count_approved = Payment.query.filter_by(status='Approved').count()
    count_rejected = Payment.query.filter_by(status='Rejected').count()
    
    return render_template(
        'admin/payments.html',
        title='Verifikasi Pembayaran',
        payments=payments_list,
        current_filter=status_filter,
        counts={
            'All': count_all,
            'Pending': count_pending,
            'Approved': count_approved,
            'Rejected': count_rejected
        }
    )

@bp.route('/payment/<int:payment_id>/verify', methods=['POST'])
@login_required
@admin_required
def payment_verify(payment_id):
    payment = db.session.get(Payment, payment_id)
    if not payment:
        flash('Data pembayaran tidak ditemukan.', 'danger')
        return redirect(url_for('admin.payments'))
        
    action = request.form.get('action')
    if action not in ['approve', 'reject']:
        flash('Aksi verifikasi tidak valid.', 'danger')
        return redirect(url_for('admin.payments'))
        
    order = payment.order
    if not order:
        flash('Pesanan terkait pembayaran tidak ditemukan.', 'danger')
        return redirect(url_for('admin.payments'))
        
    if action == 'approve':
        payment.status = 'Approved'
        order.status = 'Processing'
        if current_user.admin:
            payment.admin_id = current_user.admin.id
        flash(f'Pembayaran untuk pesanan #{order.id} berhasil disetujui. Pesanan kini sedang diproses.', 'success')
    elif action == 'reject':
        payment.status = 'Rejected'
        flash(f'Pembayaran untuk pesanan #{order.id} telah ditolak.', 'warning')
        
    db.session.commit()
    return redirect(url_for('admin.payments'))

def get_reports_data(periode):
    today = date.today()
    
    if periode == 'daily':
        start_date = today - timedelta(days=30)
        labels = [(start_date + timedelta(days=i)).strftime('%d %b') for i in range(31)]
        labels_keys = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(31)]
    elif periode == 'weekly':
        start_date = today - timedelta(weeks=12)
        labels = []
        labels_keys = []
        for i in range(12, -1, -1):
            d = today - timedelta(weeks=i)
            monday = d - timedelta(days=d.weekday())
            labels.append(monday.strftime('%d %b'))
            labels_keys.append(f"{monday.year}-{monday.isocalendar()[1]}") # YYYY-WeekNum
    elif periode == 'yearly':
        start_date = today - timedelta(days=365*5)
        labels = [str(today.year - i) for i in range(5, -1, -1)]
        labels_keys = labels.copy()
    else: # monthly
        start_date = today - timedelta(days=365)
        labels = []
        labels_keys = []
        for i in range(11, -1, -1):
            m = today.month - i
            y = today.year
            if m <= 0:
                m += 12
                y -= 1
            d = date(y, m, 1)
            labels.append(d.strftime('%b %Y'))
            labels_keys.append(d.strftime('%Y-%m'))
            
    orders = Order.query.filter(
        Order.status != 'Cancelled',
        Order.order_date >= start_date
    ).all()
    
    total_revenue = sum(float(o.total_price) for o in orders)
    total_orders = len(orders)
    avg_transaction = total_revenue / total_orders if total_orders > 0 else 0.0
    successful_orders = sum(1 for o in orders if o.status == 'Completed')
    
    revenue_trend = {k: 0.0 for k in labels_keys}
    orders_trend = {k: 0 for k in labels_keys}
    
    for o in orders:
        if periode == 'daily':
            k = o.order_date.strftime('%Y-%m-%d')
        elif periode == 'weekly':
            monday = o.order_date - timedelta(days=o.order_date.weekday())
            k = f"{monday.year}-{monday.isocalendar()[1]}"
        elif periode == 'yearly':
            k = str(o.order_date.year)
        else: # monthly
            k = o.order_date.strftime('%Y-%m')
            
        if k in revenue_trend:
            revenue_trend[k] += float(o.total_price)
            orders_trend[k] += 1
            
    trend_data = {
        'labels': labels,
        'revenue': [revenue_trend[k] for k in labels_keys],
        'orders': [orders_trend[k] for k in labels_keys]
    }
    
    best_sellers = db.session.query(
        Product.name,
        Category.name.label('category_name'),
        func.sum(OrderItem.quantity).label('total_qty'),
        func.sum(OrderItem.quantity * OrderItem.price).label('total_rev')
    ).join(OrderItem, OrderItem.product_id == Product.id)\
     .join(Order, OrderItem.order_id == Order.id)\
     .join(Category, Product.category_id == Category.id)\
     .filter(Order.status != 'Cancelled', Order.order_date >= start_date)\
     .group_by(Product.id)\
     .order_by(func.sum(OrderItem.quantity).desc())\
     .limit(5).all()
     
    category_contrib = db.session.query(
        Category.name,
        func.sum(OrderItem.quantity * OrderItem.price).label('total_rev')
    ).join(Product, Product.category_id == Category.id)\
     .join(OrderItem, OrderItem.product_id == Product.id)\
     .join(Order, OrderItem.order_id == Order.id)\
     .filter(Order.status != 'Cancelled', Order.order_date >= start_date)\
     .group_by(Category.id).all()
     
    category_data = {
        'labels': [c[0] for c in category_contrib],
        'data': [float(c[1]) for c in category_contrib]
    }
    
    return {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'avg_transaction': avg_transaction,
        'successful_orders': successful_orders,
        'trend_data': trend_data,
        'best_sellers': best_sellers,
        'category_data': category_data,
        'transactions': orders
    }

@bp.route('/reports')
@login_required
@admin_required
def reports():
    periode = request.args.get('periode', 'monthly').lower()
    if periode not in ['daily', 'weekly', 'monthly', 'yearly']:
        periode = 'monthly'
        
    data = get_reports_data(periode)
    
    return render_template(
        'admin/reports.html',
        title='Laporan Keuangan',
        current_periode=periode,
        total_revenue=data['total_revenue'],
        total_orders=data['total_orders'],
        avg_transaction=data['avg_transaction'],
        successful_orders=data['successful_orders'],
        trend_data=data['trend_data'],
        best_sellers=data['best_sellers'],
        category_data=data['category_data'],
        transactions=data['transactions']
    )

@bp.route('/reports/export/excel')
@login_required
@admin_required
def export_excel():
    periode = request.args.get('periode', 'monthly').lower()
    if periode not in ['daily', 'weekly', 'monthly', 'yearly']:
        periode = 'monthly'
        
    data = get_reports_data(periode)
    transactions = data['transactions']
    
    tx_list = []
    for tx in transactions:
        tx_list.append({
            'ID Pesanan': f"#{tx.id}",
            'Nama Pelanggan': tx.customer.name,
            'Email Pelanggan': tx.customer.email,
            'Tanggal Order': tx.order_date.strftime('%Y-%m-%d'),
            'Tanggal Mulai Sewa': tx.start_date.strftime('%Y-%m-%d') if tx.start_date else '-',
            'Tanggal Selesai Sewa': tx.end_date.strftime('%Y-%m-%d') if tx.end_date else '-',
            'Total Harga': float(tx.total_price),
            'Status': tx.status
        })
        
    import pandas as pd
    import io
    from flask import send_file
    
    if len(tx_list) > 0:
        df = pd.DataFrame(tx_list)
    else:
        df = pd.DataFrame(columns=[
            'ID Pesanan', 'Nama Pelanggan', 'Email Pelanggan', 
            'Tanggal Order', 'Tanggal Mulai Sewa', 'Tanggal Selesai Sewa', 
            'Total Harga', 'Status'
        ])
        
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Laporan Transaksi')
        
    output.seek(0)
    
    filename = f"laporan-transaksi-{periode}-{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

@bp.route('/reports/export/pdf')
@login_required
@admin_required
def export_pdf():
    periode = request.args.get('periode', 'monthly').lower()
    if periode not in ['daily', 'weekly', 'monthly', 'yearly']:
        periode = 'monthly'
        
    data = get_reports_data(periode)
    
    admin_name = current_user.name if (current_user.is_authenticated and current_user.admin) else "Administrator"
    print_date = datetime.now().strftime('%d %B %Y')
    
    html_content = render_template(
        'admin/reports_pdf.html',
        current_periode=periode,
        total_revenue=data['total_revenue'],
        total_orders=data['total_orders'],
        avg_transaction=data['avg_transaction'],
        successful_orders=data['successful_orders'],
        best_sellers=data['best_sellers'],
        transactions=data['transactions'],
        admin_name=admin_name,
        print_date=print_date
    )
    
    import io
    from xhtml2pdf import pisa
    from flask import send_file
    
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)
    
    if pisa_status.err:
        flash('Terjadi kesalahan saat menghasilkan berkas PDF.', 'danger')
        return redirect(url_for('admin.reports', periode=periode))
        
    pdf_buffer.seek(0)
    filename = f"laporan-transaksi-{periode}-{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@bp.route('/schedules')
@login_required
@admin_required
def schedules():
    product_id_filter = request.args.get('product_id', 'All').strip()
    status_filter = request.args.get('status', 'All').strip()
    date_filter = request.args.get('date', '').strip()
    
    query = Schedule.query
    
    if product_id_filter != 'All' and product_id_filter:
        query = query.filter_by(product_id=int(product_id_filter))
        
    if status_filter != 'All' and status_filter:
        query = query.filter_by(status=status_filter)
        
    if date_filter:
        try:
            parsed_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter_by(date=parsed_date)
        except ValueError:
            pass
            
    schedules_list = query.order_by(Schedule.date.desc(), Schedule.id.desc()).all()
    products = Product.query.filter_by(status='Active').all()
    
    today_str = date.today().strftime('%Y-%m-%d')
    
    return render_template(
        'admin/schedules.html',
        title='Manajemen Jadwal',
        schedules=schedules_list,
        products_list=products,
        current_product=product_id_filter,
        current_status=status_filter,
        current_date=date_filter,
        today_str=today_str
    )

@bp.route('/schedules/add', methods=['POST'])
@login_required
@admin_required
def schedule_add():
    product_id = request.form.get('product_id')
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    start_time_str = request.form.get('start_time')
    end_time_str = request.form.get('end_time')
    
    if not all([product_id, start_date_str, end_date_str, start_time_str, end_time_str]):
        flash('Semua kolom formulir wajib diisi.', 'danger')
        return redirect(url_for('admin.schedules'))
        
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
    except ValueError:
        flash('Format tanggal atau waktu tidak valid.', 'danger')
        return redirect(url_for('admin.schedules'))
        
    if start_date > end_date:
        flash('Tanggal mulai tidak boleh melebihi tanggal selesai.', 'danger')
        return redirect(url_for('admin.schedules'))
        
    # Validasi barang ada
    product = db.session.get(Product, int(product_id))
    if not product:
        flash('Barang tidak ditemukan.', 'danger')
        return redirect(url_for('admin.schedules'))
        
    # Tambahkan jadwal pemeliharaan per tanggal dalam rentang
    curr_date = start_date
    added_count = 0
    while curr_date <= end_date:
        schedule = Schedule(
            product_id=product.id,
            date=curr_date,
            start_time=start_time,
            end_time=end_time,
            status='Maintenance'
        )
        db.session.add(schedule)
        added_count += 1
        curr_date += timedelta(days=1)
        
    db.session.commit()
    flash(f'Berhasil menambahkan {added_count} jadwal pemeliharaan untuk barang "{product.name}".', 'success')
    return redirect(url_for('admin.schedules'))

@bp.route('/schedules/<int:schedule_id>/delete', methods=['POST'])
@login_required
@admin_required
def schedule_delete(schedule_id):
    schedule = db.session.get(Schedule, schedule_id)
    if not schedule:
        flash('Jadwal tidak ditemukan.', 'danger')
        return redirect(url_for('admin.schedules'))
        
    if schedule.status != 'Maintenance':
        flash('Hanya jadwal pemeliharaan (Maintenance) yang dapat dihapus secara manual.', 'danger')
        return redirect(url_for('admin.schedules'))
        
    product_name = schedule.product.name
    schedule_date = schedule.date.strftime('%d %B %Y')
    
    db.session.delete(schedule)
    db.session.commit()
    
    flash(f'Jadwal pemeliharaan barang "{product_name}" pada tanggal {schedule_date} telah diselesaikan/dihapus.', 'success')
    return redirect(url_for('admin.schedules'))


# ==================== SITE SETTINGS ====================

SETTINGS_TEXT_FIELDS = [
    'brand_name', 'brand_tagline',
    'hero_title', 'hero_subtitle',
    'why_choose_us_p1', 'why_choose_us_p2',
    'gallery_title',
    'gallery_caption_1', 'gallery_caption_2', 'gallery_caption_3',
    'gallery_caption_4', 'gallery_caption_5',
    'footer_description', 'footer_address', 'footer_phone',
    'footer_email', 'footer_hours',
    'social_whatsapp', 'social_instagram', 'social_facebook', 'social_tiktok',
    'invoice_company_name', 'invoice_tagline', 'invoice_address', 'invoice_phone',
]

SETTINGS_FILE_FIELDS = [
    'logo_path', 'hero_bg_path',
    'gallery_img_1', 'gallery_img_2', 'gallery_img_3',
    'gallery_img_4', 'gallery_img_5',
]

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

def _allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


@bp.route('/settings', methods=['GET'])
@login_required
@admin_required
def settings():
    settings_dict = {s.key: s.value for s in SiteSetting.query.all()}
    return render_template('admin/settings.html', title='Site Settings', settings=settings_dict)


@bp.route('/settings', methods=['POST'])
@login_required
@admin_required
def settings_save():
    # 1. Save all text fields
    for field in SETTINGS_TEXT_FIELDS:
        value = request.form.get(field, '').strip()
        SiteSetting.set(field, value)

    # 2. Save file uploads
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'settings')
    os.makedirs(upload_dir, exist_ok=True)

    for field in SETTINGS_FILE_FIELDS:
        file = request.files.get(field)
        if file and file.filename and _allowed_image(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            safe_name = f"{field}_{uuid.uuid4().hex[:8]}.{ext}"
            file_path = os.path.join(upload_dir, safe_name)
            file.save(file_path)
            # Store relative path from static/
            relative_path = f"uploads/settings/{safe_name}"
            SiteSetting.set(field, relative_path)

    db.session.commit()
    flash('Pengaturan situs berhasil disimpan!', 'success')
    return redirect(url_for('admin.settings'))


# ==================== ADMIN INVOICE & PRINT ====================

@bp.route('/order/<int:order_id>/invoice')
@login_required
@admin_required
def order_invoice(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        flash('Pesanan tidak ditemukan.', 'danger')
        return redirect(url_for('admin.orders'))
        
    duration = (order.end_date - order.start_date).days
    if duration <= 0:
        duration = 1
        
    return render_template(
        'customer/invoice.html',
        title=f'Invoice #{order.id}',
        order=order,
        duration=duration
    )


@bp.route('/order/<int:order_id>/invoice/pdf')
@login_required
@admin_required
def download_invoice_pdf(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        flash('Pesanan tidak ditemukan.', 'danger')
        return redirect(url_for('admin.orders'))
        
    duration = (order.end_date - order.start_date).days
    if duration <= 0:
        duration = 1
        
    html_content = render_template('customer/invoice_pdf.html', order=order, duration=duration)
    
    import io
    from xhtml2pdf import pisa
    from flask import send_file
    
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)
    
    if pisa_status.err:
        flash('Terjadi kesalahan saat menghasilkan berkas PDF.', 'danger')
        return redirect(url_for('admin.order_detail', order_id=order.id))
        
    pdf_buffer.seek(0)
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'invoice-{order.id}.pdf'
    )

