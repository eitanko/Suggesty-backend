from flask import Flask, jsonify, request
from flask_cors import CORS
from db import db
from config import Config
from routes import *
from services.customer_journey_processor import process_journey_metrics
from utils.classify_click_events import classify_button

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
# app.register_blueprint(posthog_events_blueprint, url_prefix='/api/ph_events')
app.register_blueprint(events_blueprint, url_prefix='/api/events')
app.register_blueprint(events_failed_blueprint, url_prefix='/api/process_events_failed')
app.register_blueprint(page_usage_blueprint, url_prefix='/api/page_usage')
app.register_blueprint(event_usage_blueprint, url_prefix='/api/event_usage')
app.register_blueprint(friction_blueprint, url_prefix='/api/friction')
app.register_blueprint(form_usage_blueprint, url_prefix='/api/form_usage')
app.register_blueprint(insights_blueprint, url_prefix='/api/insights')

@app.route('/api/process-events', methods=['POST'])
def process_events():
    import logging
    import traceback
    from services.event_processor import process_raw_events
    app.logger.setLevel(logging.INFO)
    try:
        # Run the event processing function
        process_raw_events(db.session)
        return jsonify({"status": "success", "message": "Events processed successfully"}), 200
    except Exception as e:
        app.logger.error("Error processing events:\n" + traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/process_events_failed', methods=['POST'])
def trigger_journey_evaluation():
    timeout = request.args.get('timeout', default=30, type=int)
    from services.event_processor_failed import evaluate_journey_failures
    updated_count = evaluate_journey_failures(db.session, timeout_minutes=timeout)

    return jsonify({
        "message": "Evaluation complete",
        "journeys_failed": updated_count
    })

@app.route('/api/process_journey_metrics', methods=['POST'])
def run_report():
    try:
        # Get account_id from JSON body if provided
        data = request.get_json() if request.is_json else {}
        account_id = data.get('account_id') if data else None
        
        # Run the event processing function
        if account_id:
            result = process_journey_metrics(db.session, account_id=account_id)
        else:
            result = process_journey_metrics(db.session)
            
        return jsonify({
            "status": "success", 
            "message": "Journeys processed successfully",
            "completion_rates": result
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# @app.route("/api/classify_button", methods=["POST"])
# this code is used to classify a button click event based on the elements chain sending the data to an ai classifier.
# based on this we can tell if a form has been submitted, a button was used for navigation.
# def classify_button_api():
#     data = request.json
#
#     try:
#         label = classify_button(data)
#
#         return jsonify({
#             "label": label,
#             "success": True
#         })
#     except Exception as e:
#         return jsonify({
#             "error": str(e),
#             "success": False
#         }), 500

if __name__ == '__main__':
    # Run the report here if you want to trigger the function directly
    app.run(host='0.0.0.0', port=5000)
