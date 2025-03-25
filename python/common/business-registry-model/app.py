from flask import Flask
from flask_migrate import Migrate

from business_model.models import db

from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

migrate = Migrate(app,
                  db,
                  directory="src/business_model_migrations",
                  **{'dialect_name': 'postgres'})
