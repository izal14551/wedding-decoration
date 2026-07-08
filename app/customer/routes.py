from flask import render_template, redirect, url_for, flash, request, session, current_app, abort
from flask_login import current_user, login_required
from app import db
from app.customer import bp
from app.models import Product, Order, OrderItem, Category, Payment, Schedule, Customer, User
from datetime import datetime, date, time, timedelta
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
import os

@bp.route('/')
@bp.route('/index')
def index():
    products = Product.query.filter_by(status='Active').all()
    return render_template('customer/index.html', title='Home', products=products)

@bp.route('/decorations')
def decorations():
    search = request.args.get('search', '')
    category_id = request.args.get('category_id', '')
    
    query = Product.query.filter_by(status='Active')
    
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
        
    if category_id:
        try:
            query = query.filter_by(category_id=int(category_id))
        except ValueError:
            pass
            
    products = query.all()
    categories = Category.query.all()
    
    return render_template('customer/decorations.html', 
                           title='Dekorasi', 
                           products=products, 
                           categories=categories, 
                           search=search, 
                           selected_category=category_id)

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
def cart_add(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        flash('Produk tidak ditemukan.', 'danger')
        return redirect(url_for('customer.decorations'))
        
    cart_session = session.get('cart', {})
    cart_session[str(product_id)] = cart_session.get(str(product_id), 0) + 1
    session['cart'] = cart_session
    session.modified = True
    
    flash(f'{product.name} berhasil ditambahkan ke keranjang.', 'success')
    
    # Redirect ke cart atau decorations tergantung dari mana aksi ini berasal
    referrer = request.referrer or ''
    if 'decorations' in referrer:
        return redirect(url_for('customer.decorations'))
    return redirect(url_for('customer.index'))

@bp.route('/cart/update/<int:product_id>', methods=['POST'])
@login_required
def cart_update(product_id):
    action = request.form.get('action')
    cart_session = session.get('cart', {})
    
    if str(product_id) in cart_session:
        if action == 'increase':
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
        cart_session = session.get('cart', {})
        cart_session[str(product_id)] = cart_session.get(str(product_id), 0) + 1
        session['cart'] = cart_session
        session.modified = True
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
        
    duration = (end_date - start_date).days
    if duration <= 0:
        duration = 1
        
    # Validasi & Kalkulasi Total Harga
    total_price = 0
    products_to_order = []
    for prod_id_str, qty in cart_session.items():
        prod = db.session.get(Product, int(prod_id_str))
        if not prod:
            continue
        item_total = float(prod.price) * int(qty) * duration
        total_price += item_total
        products_to_order.append((prod, qty))
        
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
        
        # Masukkan ke jadwal ketersediaan barang
        curr_date = start_date
        while curr_date <= end_date:
            schedule = Schedule(
                product_id=prod.id,
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
