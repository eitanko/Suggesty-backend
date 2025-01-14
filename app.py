from flask import Flask
from flask_cors import CORS
from db import db
from config import Config
from routes import journey_blueprint, step_blueprint, event_blueprint

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS
CORS(app, resources={r"/api/*": {"origins": [
        "chrome-extension://killleidajemobjblfojagljbfcgmcjg",
        "chrome-extension://gngngnjepafimnjjhcinddkehmhadoip"
    ]}})

# Initialize extensions
db.init_app(app)

# Register blueprints
app.register_blueprint(journey_blueprint, url_prefix='/api/journey')
app.register_blueprint(step_blueprint, url_prefix='/api/step')
app.register_blueprint(event_blueprint, url_prefix='/api/event')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
