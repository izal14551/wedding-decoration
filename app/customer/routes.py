from flask import render_template, redirect, url_for, flash, request, session, current_app, abort
from flask_login import current_user, login_required
from sqlalchemy import func
from app import db
from app.customer import bp
from app.models import Product, Order, OrderItem, Category, Payment, Schedule, Customer, User
from datetime import datetime, date, time, timedelta
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from babel.dates import format_date, get_day_names

import os

@bp.route('/')
@bp.route('/index')
def index():
    products = Product.query.filter_by(status='Active').all()
    return render_template('customer/index.html', title='Home', products=products)

@bp.route('/decorations')
def decorations():
    search = request.args.get('search', '')
    category_ids = request.args.getlist('category_ids')
    single_category_id = request.args.get('category_id')
    if single_category_id and single_category_id not in category_ids:
        category_ids.append(single_category_id)
    
    query = Product.query.filter_by(status='Active')
    
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
        
    if category_ids:
        valid_ids = []
        for cid in category_ids:
            try:
                valid_ids.append(int(cid))
            except ValueError:
                pass
        if valid_ids:
            query = query.filter(Product.category_id.in_(valid_ids))
            
    products = query.all()
    categories = Category.query.all()
    
    return render_template('customer/decorations.html', 
                           title='Dekorasi', 
                           products=products, 
                           categories=categories, 
                           search=search, 
                           selected_categories=category_ids)

@bp.route('/decoration/<int:product_id>')
def product_detail(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        abort(404)
        
    categories = Category.query.all()
    
    today = date.today()
    try:
        month = int(request.args.get('month', today.month))
        year = int(request.args.get('year', today.year))
    except ValueError:
        month = today.month
        year = today.year
        
    # Validasi input bulan & tahun
    if month < 1 or month > 12:
        month = today.month
    if year < today.year - 1 or year > today.year + 5:
        year = today.year
        
    # Hitung bulan/tahun sebelum dan sesudah untuk tombol navigasi
    import calendar
    
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year
        
    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year
        
    # Cek apakah bulan sebelumnya adalah di masa lalu
    is_prev_past = False
    if prev_year < today.year or (prev_year == today.year and prev_month < today.month):
        is_prev_past = True
        
    # Generate list tanggal untuk bulan tersebut menggunakan Calendar (mulai Senin)
    cal = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdayscalendar(year, month)
    
    is_service = 'rias' in product.category.name.lower() or 'makeup' in product.category.name.lower() or 'mc' in product.category.name.lower() or 'dance' in product.category.name.lower() or 'jasa' in product.category.name.lower()
    
    calendar_weeks = []
    
    for week in weeks:
        week_data = []
        for day_num in week:
            if day_num == 0:
                week_data.append({
                    'date': None,
                    'day_num': '',
                    'status': 'Empty',
                    'note': '',
                    'badge_class': ''
                })
            else:
                check_date = date(year, month, day_num)
                
                # Cek apakah tanggal ini di masa lalu
                if check_date < today:
                    week_data.append({
                        'date': check_date,
                        'day_num': day_num,
                        'status': 'Past',
                        'note': 'Lewat',
                        'badge_class': 'bg-secondary-subtle text-secondary border border-secondary-subtle'
                    })
                    continue
                
                # Hitung status ketersediaan
                maintenance_count = Schedule.query.filter_by(
                    product_id=product.id,
                    date=check_date,
                    status='Maintenance'
                ).count()
                
                offline_rentals = Schedule.query.filter(
                    Schedule.product_id == product.id,
                    Schedule.date == check_date,
                    Schedule.status == 'Rented',
                    Schedule.order_id == None
                ).count()
                
                active_rentals = db.session.query(func.sum(OrderItem.quantity))\
                    .join(Order, OrderItem.order_id == Order.id)\
                    .filter(
                        OrderItem.product_id == product.id,
                        Order.status != 'Cancelled',
                        Order.start_date <= check_date,
                        Order.end_date >= check_date
                    ).scalar() or 0
                    
                total_rented = active_rentals + offline_rentals + maintenance_count
                available_stock = max(0, product.stock - total_rented)
                
                if maintenance_count >= product.stock:
                    status = 'Maintenance'
                    note = 'Perawatan'
                    badge_class = 'bg-warning-subtle text-warning border border-warning-subtle'
                elif available_stock <= 0:
                    status = 'Fully Booked'
                    note = 'Penuh'
                    badge_class = 'bg-danger-subtle text-danger border border-danger-subtle'
                else:
                    status = 'Available'
                    note = f"Tersedia: {available_stock} {'Slot' if is_service else 'Unit'}"
                    badge_class = 'bg-success-subtle text-success border border-success-subtle'
                    
                week_data.append({
                    'date': check_date,
                    'day_num': day_num,
                    'status': status,
                    'note': note,
                    'badge_class': badge_class,
                    'available_stock': available_stock
                })
        calendar_weeks.append(week_data)
        
    month_name_id = format_date(date(year, month, 1), format='MMMM', locale='id')
    day_names_dict = get_day_names(width='abbreviated', locale='id')
    day_names = [day_names_dict[i] for i in range(7)]
    
    return render_template(
        'customer/product_detail.html',
        title=f"Detail - {product.name}",
        product=product,
        categories=categories,
        calendar_weeks=calendar_weeks,
        current_month=month,
        current_year=year,
        month_name=month_name_id,
        day_names=day_names,
        prev_month=prev_month,
        prev_year=prev_year,
        next_month=next_month,
        next_year=next_year,
        is_prev_past=is_prev_past,
        is_service=is_service
    )

@bp.route('/cart')
@login_required
def cart():
    cart_session = session.get('cart', {})
    cart_items = []
    total_price = 0
    
    for prod_id_str, qty in cart_session.items():
        prod = db.session.get(Product, int(prod_id_str))
        if prod:
            item_total = float(prod.price) * int(qty)
            total_price += item_total
            cart_items.append({
                'product': prod,
                'quantity': qty,
                'total': item_total
            })
            
    return render_template('customer/cart.html', 
                           title='Keranjang', 
                           cart_items=cart_items, 
                           total_price=total_price)

@bp.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def cart_add(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        flash('Produk tidak ditemukan.', 'danger')
        return redirect(url_for('customer.decorations'))
        
    try:
        quantity = int(request.form.get('quantity', 1))
        if quantity <= 0:
            quantity = 1
    except ValueError:
        quantity = 1
        
    cart_session = session.get('cart', {})
    current_qty = cart_session.get(str(product_id), 0)
    new_qty = current_qty + quantity
    
    if new_qty > product.stock:
        is_service = 'rias' in product.category.name.lower() or 'makeup' in product.category.name.lower() or 'mc' in product.category.name.lower() or 'dance' in product.category.name.lower() or 'jasa' in product.category.name.lower()
        unit_name = 'Slot' if is_service else 'Unit'
        flash(f'Jumlah sewa untuk {product.name} tidak boleh melebihi kapasitas/stok yang tersedia ({product.stock} {unit_name}).', 'danger')
        
        referrer = request.referrer or ''
        if 'decoration/' in referrer:
            return redirect(url_for('customer.product_detail', product_id=product.id))
        return redirect(url_for('customer.decorations'))
        
    cart_session[str(product_id)] = new_qty
    session['cart'] = cart_session
    session.modified = True
    
    flash(f'{product.name} berhasil ditambahkan ke keranjang.', 'success')
    return redirect(url_for('customer.cart'))

@bp.route('/cart/update/<int:product_id>', methods=['POST'])
@login_required
def cart_update(product_id):
    action = request.form.get('action')
    cart_session = session.get('cart', {})
    
    if str(product_id) in cart_session:
        product = db.session.get(Product, product_id)
        if not product:
            cart_session.pop(str(product_id))
            session['cart'] = cart_session
            session.modified = True
            return redirect(url_for('customer.cart'))
            
        if action == 'increase':
            if cart_session[str(product_id)] + 1 > product.stock:
                is_service = 'rias' in product.category.name.lower() or 'makeup' in product.category.name.lower() or 'mc' in product.category.name.lower() or 'dance' in product.category.name.lower() or 'jasa' in product.category.name.lower()
                unit_name = 'Slot' if is_service else 'Unit'
                flash(f'Jumlah sewa untuk {product.name} tidak boleh melebihi kapasitas/stok yang tersedia ({product.stock} {unit_name}).', 'danger')
            else:
                cart_session[str(product_id)] += 1
        elif action == 'decrease':
            cart_session[str(product_id)] -= 1
            if cart_session[str(product_id)] <= 0:
                cart_session.pop(str(product_id))
        session['cart'] = cart_session
        session.modified = True
        
    return redirect(url_for('customer.cart'))

@bp.route('/cart/remove/<int:product_id>', methods=['POST'])
@login_required
def cart_remove(product_id):
    cart_session = session.get('cart', {})
    if str(product_id) in cart_session:
        cart_session.pop(str(product_id))
        session['cart'] = cart_session
        session.modified = True
        flash('Produk berhasil dihapus dari keranjang.', 'success')
    return redirect(url_for('customer.cart'))

@bp.route('/book', methods=['POST'])
@login_required
def book():
    # Bridge dari Booking Modal di beranda langsung dimasukkan ke keranjang dan checkout
    product_id = request.form.get('product_id')
    if product_id:
        product = db.session.get(Product, int(product_id))
        if product:
            cart_session = session.get('cart', {})
            current_qty = cart_session.get(str(product_id), 0)
            if current_qty + 1 <= product.stock:
                cart_session[str(product_id)] = current_qty + 1
                session['cart'] = cart_session
                session.modified = True
            else:
                is_service = 'rias' in product.category.name.lower() or 'makeup' in product.category.name.lower() or 'mc' in product.category.name.lower() or 'dance' in product.category.name.lower() or 'jasa' in product.category.name.lower()
                unit_name = 'Slot' if is_service else 'Unit'
                flash(f'Kapasitas/stok untuk {product.name} tidak mencukupi ({product.stock} {unit_name}).', 'danger')
    return redirect(url_for('customer.cart'))

@bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    cart_session = session.get('cart', {})
    if not cart_session:
        flash('Keranjang Anda kosong.', 'danger')
        return redirect(url_for('customer.cart'))
        
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    phone = request.form.get('phone')
    address = request.form.get('address')
    notes = request.form.get('notes', '')
    
    if not start_date_str or not end_date_str or not address:
        flash('Silakan isi tanggal sewa dan alamat acara.', 'danger')
        return redirect(url_for('customer.cart'))
        
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Format tanggal tidak valid.', 'danger')
        return redirect(url_for('customer.cart'))
        
    if start_date < date.today():
        flash('Tanggal mulai sewa tidak boleh di masa lalu.', 'danger')
        return redirect(url_for('customer.cart'))
        
    if end_date < start_date:
        flash('Tanggal selesai sewa harus setelah atau sama dengan tanggal mulai sewa.', 'danger')
        return redirect(url_for('customer.cart'))
        
    duration = (end_date - start_date).days
    if duration <= 0:
        duration = 1
        
    # Validasi Stok / Ketersediaan & Kalkulasi Total Harga
    total_price = 0
    products_to_order = []
    conflict_found = False
    
    for prod_id_str, qty in cart_session.items():
        prod = db.session.get(Product, int(prod_id_str))
        if not prod:
            continue
            
        qty = int(qty)
        is_service = 'rias' in prod.category.name.lower() or 'makeup' in prod.category.name.lower() or 'mc' in prod.category.name.lower() or 'dance' in prod.category.name.lower() or 'jasa' in prod.category.name.lower()
        unit_name = 'Slot' if is_service else 'Unit'
            
        # Periksa ketersediaan stok setiap tanggal dalam rentang sewa
        curr_date = start_date
        while curr_date <= end_date:
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
                    Order.start_date <= curr_date,
                    Order.end_date >= curr_date
                ).scalar() or 0
                
            available_stock = prod.stock - active_rentals - maintenance_count - offline_rentals
            
            if qty > available_stock:
                if available_stock <= 0:
                    flash(f'Maaf, {prod.name} sudah penuh dipesan (Fully Booked) pada tanggal {curr_date.strftime("%d %b %Y")}. Silakan pilih tanggal lain.', 'danger')
                else:
                    flash(f'Jumlah sewa untuk {prod.name} ({qty} {unit_name}) melebihi stok/kapasitas yang tersedia ({available_stock} {unit_name}) pada tanggal {curr_date.strftime("%d %b %Y")}.', 'danger')
                conflict_found = True
                break
                
            curr_date += timedelta(days=1)
            
        if conflict_found:
            break
            
        item_total = float(prod.price) * qty * duration
        total_price += item_total
        products_to_order.append((prod, qty))
        
    if conflict_found:
        return redirect(url_for('customer.cart'))
        
    if not products_to_order:
        flash('Produk di keranjang tidak valid.', 'danger')
        return redirect(url_for('customer.cart'))
        
    # Perbarui informasi pelanggan jika berubah/baru
    if phone and current_user.phone != phone:
        current_user.customer.phone = phone
    if address and current_user.address != address:
        current_user.customer.address = address
    db.session.add(current_user.customer)
    
    # Buat pesanan baru
    order = Order(
        customer_id=current_user.customer.id,
        order_date=date.today(),
        start_date=start_date,
        end_date=end_date,
        event_address=address,
        notes=notes,
        total_price=total_price,
        status='Pending'
    )
    db.session.add(order)
    db.session.flush()
    
    # Tambahkan detail pesanan dan jadwal
    for prod, qty in products_to_order:
        order_item = OrderItem(
            order_id=order.id,
            product_id=prod.id,
            quantity=qty,
            price=prod.price
        )
        db.session.add(order_item)
        
        # Masukkan ke jadwal ketersediaan barang dengan mengaitkan order_id
        curr_date = start_date
        while curr_date <= end_date:
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
            
    db.session.commit()
    session.pop('cart', None) # Kosongkan keranjang sewa
    
    flash('Pemesanan dekorasi berhasil dibuat! Silakan transfer pembayaran dan unggah bukti transfer.', 'success')
    return redirect(url_for('customer.profile'))

@bp.route('/profile', methods=['GET'])
@login_required
def profile():
    # Ambil riwayat transaksi pesanan milik pelanggan saat ini
    orders = Order.query.filter_by(customer_id=current_user.customer.id).order_by(Order.id.desc()).all()
    return render_template('customer/profile.html', title='Profil Saya', orders=orders)

@bp.route('/profile/update', methods=['POST'])
@login_required
def profile_update():
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    address = request.form.get('address')
    password = request.form.get('password')
    
    if not name or not email:
        flash('Nama dan Email harus diisi.', 'danger')
        return redirect(url_for('customer.profile') + '#edit')
        
    # Cek duplikasi email
    existing_user = User.query.filter(User.email == email, User.id != current_user.id).first()
    if existing_user:
        flash('Email sudah digunakan oleh pengguna lain.', 'danger')
        return redirect(url_for('customer.profile') + '#edit')
        
    # Validasi format nomor telepon Indonesia
    import re
    if phone:
        if not re.match(r'^(08|\+628)\d{8,11}$', phone):
            flash('Nomor telepon harus format Indonesia (cth: 08123456789 atau +628123456789).', 'danger')
            return redirect(url_for('customer.profile') + '#edit')
            
    # Validasi panjang password baru
    if password:
        if len(password) < 6:
            flash('Password minimal harus 6 karakter.', 'danger')
            return redirect(url_for('customer.profile') + '#edit')
        current_user.set_password(password)
        
    current_user.customer.name = name
    current_user.email = email
    current_user.customer.phone = phone
    current_user.customer.address = address
        
    db.session.add(current_user)
    db.session.add(current_user.customer)
    db.session.commit()
    flash('Informasi profil berhasil diperbarui.', 'success')
    return redirect(url_for('customer.profile'))

@bp.route('/order/<int:order_id>/upload_payment', methods=['POST'])
@login_required
def upload_payment(order_id):
    order = db.session.get(Order, order_id)
    if not order or order.customer_id != current_user.customer.id:
        abort(404)
        
    payment_method = request.form.get('payment_method')
    file = request.files.get('payment_proof')
    
    if not payment_method or not file:
        flash('Silakan pilih metode pembayaran dan pilih berkas bukti transfer.', 'danger')
        return redirect(url_for('customer.profile'))
        
    if file.filename == '':
        flash('Berkas belum dipilih.', 'danger')
        return redirect(url_for('customer.profile'))
        
    # Validasi berkas gambar
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        flash('Tipe berkas tidak diperbolehkan. Hanya berkas gambar (PNG, JPG, JPEG, GIF) yang diterima.', 'danger')
        return redirect(url_for('customer.profile'))
        
    # Simpan file
    filename = secure_filename(f"proof_order_{order.id}_{int(datetime.utcnow().timestamp())}.{ext}")
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'payments')
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)
    
    # Cek apakah entri pembayaran sudah ada untuk pesanan ini
    payment = Payment.query.filter_by(order_id=order.id).first()
    if not payment:
        payment = Payment(
            order_id=order.id,
            payment_date=date.today(),
            payment_method=payment_method,
            payment_proof=f"payments/{filename}",
            status='Pending'
        )
        db.session.add(payment)
    else:
        payment.payment_date = date.today()
        payment.payment_method = payment_method
        payment.payment_proof = f"payments/{filename}"
        payment.status = 'Pending'
        
    # Update status pesanan ke Pending Verification jika belum
    order.status = 'Pending' # Status pesanan tetap pending atau bisa didefinisikan khusus
    db.session.commit()
    
    flash('Bukti pembayaran berhasil diunggah. Admin akan segera memverifikasi pembayaran Anda.', 'success')
    return redirect(url_for('customer.profile'))

@bp.route('/order/<int:order_id>/invoice')
@login_required
def invoice(order_id):
    order = db.session.get(Order, order_id)
    if not order or order.customer_id != current_user.customer.id:
        abort(404)
        
    # Menghitung durasi sewa
    duration = (order.end_date - order.start_date).days
    if duration <= 0:
        duration = 1
        
    return render_template('customer/invoice.html', title=f'Invoice #{order.id}', order=order, duration=duration)
