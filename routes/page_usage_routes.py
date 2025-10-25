from flask import Blueprint, request, jsonify
from db import db
from services.page_usage import process_page_usage

page_usage_blueprint = Blueprint("page_usage", __name__)

@page_usage_blueprint.route("/", methods=["POST"])
def process_page_usage_route():
    data = request.get_json(silent=True) or {}
    account_id = data.get("account_id")  # can be None

    results = process_page_usage(db.session, account_ids=account_id)
    return jsonify(results), 200
