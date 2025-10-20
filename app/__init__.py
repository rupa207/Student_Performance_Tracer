from flask import Flask
from .extensions import db, login_manager
from .routes import main_blueprint

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')

    # basic config
    app.config['SECRET_KEY'] = 'dev-key-change-this'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///students.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # init extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'   # redirect to login if not logged in

    # register blueprints
    app.register_blueprint(main_blueprint)

    # create tables
    with app.app_context():
        db.create_all()

    return app
