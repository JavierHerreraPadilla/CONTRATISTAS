from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate


app = Flask(__name__)

app.config['SECRET_KEY'] = "AS2220051ad555sd4f515asbdhjsjkqqqwlw992JAKSD54D5QW1E52"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ingresos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

from ingresos import routes

with app.app_context():
    db.create_all()