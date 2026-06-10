from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from app import db
from app.customer import bp
from app.models import Product, Order, OrderItem
from datetime import datetime

@bp.route('/')
@bp.route('/index')
def index():
    products = Product.query.all()
    return render_template('customer/index.html', title='Home', products=products)

@bp.route('/book', methods=['POST'])
@login_required
def book():
    product_id = request.form.get('product_id')
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    phone = request.form.get('phone')
    address = request.form.get('address')
    
    if not product_id or not start_date_str or not end_date_str:
        flash('Silakan isi semua data pemesanan dengan lengkap.', 'danger')
        return redirect(url_for('customer.index'))
        
    product = db.session.get(Product, int(product_id))
    if not product:
        flash('Paket tidak ditemukan.', 'danger')
        return redirect(url_for('customer.index'))
        
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    except ValueError:
        flash('Format tanggal tidak valid.', 'danger')
        return redirect(url_for('customer.index'))
        
    duration = (end_date - start_date).days
    if duration <= 0:
        duration = 1 # Minimal 1 hari
        
    total_price = product.price * duration
    
    # Update data profil pengguna jika belum ada
    if phone and not current_user.phone:
        current_user.phone = phone
    if address and not current_user.address:
        current_user.address = address
        
    order = Order(
        customer_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        event_address=address,
        total_price=total_price,
        status='Pending'
    )
    db.session.add(order)
    db.session.flush()
    
    order_item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        quantity=1,
        price=product.price
    )
    db.session.add(order_item)
    db.session.commit()
    
    # Format rupiah secara sederhana
    formatted_price = "{:,.0f}".format(total_price).replace(',', '.')
    flash(f'Pemesanan {product.name} berhasil! Total biaya untuk {duration} hari: Rp {formatted_price}. Admin kami akan segera menghubungi Anda.', 'success')
    return redirect(url_for('customer.index'))
