from flask import Flask
from flask_cors import CORS
from db import db
from config import Config
from routes import journey_blueprint, event_blueprint, paths_blueprint, customer_journey_blueprint,person_blueprint

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
# Set a secret key for session encryption
app.secret_key = 'eGSDKSLSEAwoCdecTqZ0ewP8W5j5vkXO'

# Enable CORS
CORS(app, resources={r"/api/*": {"origins": [
        "chrome-extension://killleidajemobjblfojagljbfcgmcjg",
        "chrome-extension://gngngnjepafimnjjhcinddkehmhadoip",
        "chrome-extension://pnicmjaflanjdioaonfnhkmppehbdnbn",
        "http://localhost:3000",
        "https://ux-app-analytics.onrender.com"

    ]}})

# Initialize extensions
db.init_app(app)

# Register blueprints
app.register_blueprint(journey_blueprint, url_prefix='/api/journey')
app.register_blueprint(event_blueprint, url_prefix='/api/event')
app.register_blueprint(paths_blueprint, url_prefix='/api/paths')
app.register_blueprint(customer_journey_blueprint, url_prefix='/api/customer_journey')
app.register_blueprint(person_blueprint, url_prefix='/api/person')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
