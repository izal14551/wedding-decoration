from flask import render_template, redirect, url_for, flash, request
from app.auth import bp
from app import db
from app.auth.forms import LoginForm, RegistrationForm
from flask_login import login_user, logout_user, current_user, login_required
from app.models import User, Role, Customer, Admin

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('customer.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password', 'danger')
            return redirect(url_for('auth.login'))
        
        if not user.active:
            flash('Your account has been deactivated.', 'danger')
            return redirect(url_for('auth.login'))
            
        login_user(user, remember=form.remember_me.data)
        if user.is_admin():
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('customer.index'))
    return render_template('auth/login.html', title='Login', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('customer.index'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('customer.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        # Creating a centralized authentication user
        user = User(email=form.email.data)
        user.set_password(form.password.data)
        
        # Getting or creating a customer role
        customer_role = Role.query.filter_by(name='customer').first()
        if customer_role is None:
            customer_role = Role(name='customer', description='Pelanggan')
            db.session.add(customer_role)
            
        user.roles.append(customer_role)
        db.session.add(user)
        db.session.flush() 
        
        # Creating related customer profile data
        customer = Customer(
            user_id=user.id,
            name=form.name.data,
            phone=form.phone.data,
            address=form.address.data
        )
        db.session.add(customer)
        db.session.commit()
        
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title='Register', form=form)
