from flask import Blueprint, session, jsonify

utils_blueprint = Blueprint('utils', __name__)
@utils_blueprint.route("/clear_session", methods=["POST"])
def clear_session():
    session.clear()  # Clears all session data
    return jsonify({"status": "Session cleared!"}), 200
