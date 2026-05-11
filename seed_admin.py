from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    admin_email = 'admin@example.com'
    admin_user = User.query.filter_by(email=admin_email).first()
    
    if not admin_user:
        admin = User(
            name='Administrator',
            email=admin_email,
            role='admin',
            phone='081234567890'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print(f"Admin created successfully with email {admin_email} and password 'admin123'.")
    else:
        print("Admin user already exists.")
