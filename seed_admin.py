from app import create_app, db
from app.models import Admin, User, Role

app = create_app()

with app.app_context():
    admin_email = 'admin@example.com'
    user = User.query.filter_by(email=admin_email).first()
    
    if not user:
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin', description='Administrator')
            db.session.add(admin_role)
            
        u_admin = User(email=admin_email)
        u_admin.set_password('admin123')
        u_admin.roles.append(admin_role)
        db.session.add(u_admin)
        db.session.flush()
        
        admin = Admin(
            user_id=u_admin.id,
            name='Administrator',
            phone='081234567890'
        )
        db.session.add(admin)
        db.session.commit()
        print(f"Admin created successfully with email {admin_email} and password 'admin123'.")
    else:
        print("Admin user already exists.")

