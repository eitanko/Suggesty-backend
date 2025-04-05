from flask import Flask
from flask_cors import CORS
from db import db
from config import Config
from routes import journey_blueprint, paths_blueprint, customer_journey_blueprint,person_blueprint, utils_blueprint, posthog_events_blueprint, events_blueprint

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
        "chrome-extension://cicpidbfkidjhapfmdalgmjfcfakannj",
        "chrome-extension://ahjlajlgngnfgbbjaihmnkhekaeoabib",
        "http://localhost:3000",
        "https://ux-app-analytics.onrender.com"

    ]}})

# Initialize extensions
db.init_app(app)

# Register blueprints
app.register_blueprint(journey_blueprint, url_prefix='/api/journey')
app.register_blueprint(paths_blueprint, url_prefix='/api/paths')
app.register_blueprint(customer_journey_blueprint, url_prefix='/api/customer_journey')
app.register_blueprint(person_blueprint, url_prefix='/api/person')
app.register_blueprint(utils_blueprint, url_prefix='/api/utils')
app.register_blueprint(posthog_events_blueprint, url_prefix='/api/ph_events')
app.register_blueprint(events_blueprint, url_prefix='/api/events')

@app.cli.command("process-events")
def process_events():
    from services.event_processor import process_raw_events
    process_raw_events(db.session)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
