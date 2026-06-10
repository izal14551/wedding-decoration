from app import create_app, db
from app.models import Admin

app = create_app()

with app.app_context():
    admin_email = 'admin@example.com'
    admin_user = Admin.query.filter_by(email=admin_email).first()
    
    if not admin_user:
        admin = Admin(
            nama='Administrator',
            email=admin_email,
            no_hp='081234567890'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print(f"Admin created successfully with email {admin_email} and password 'admin123'.")
    else:
        print("Admin user already exists.")

