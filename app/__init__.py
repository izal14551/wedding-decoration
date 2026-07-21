from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_security import Security, SQLAlchemyUserDatastore
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

security = Security()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from app.models import User, Role
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    security.init_app(app, user_datastore, register_blueprint=False)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.customer import bp as customer_bp
    app.register_blueprint(customer_bp)

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    def unauthorized():
        from flask import flash, redirect, url_for
        flash('Silakan login terlebih dahulu untuk mengakses halaman ini.', 'info')
        return redirect(url_for('auth.login'))
        
    app.login_manager.unauthorized_callback = unauthorized

    @app.route('/auth/login', endpoint='security.login', methods=['GET', 'POST'])
    def security_login_alias():
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))

    @app.context_processor
    def inject_site_settings():
        from app.models import SiteSetting
        try:
            settings = SiteSetting.query.all()
            site = {s.key: s.value for s in settings}
        except Exception:
            site = {}
        return dict(site=site)

    return app


from app import models
