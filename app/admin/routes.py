from datetime import date, datetime, timedelta
from collections import defaultdict
from flask import render_template, redirect, url_for
from sqlalchemy import func
from app import db
from app.admin import bp
from app.models import Customer, Product, Order, OrderItem, Payment, Schedule
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
