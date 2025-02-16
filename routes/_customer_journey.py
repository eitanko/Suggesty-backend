from models import CustomerJourney
from flask import Blueprint, request, jsonify
from db import db

customer_journey_blueprint = Blueprint("customer_journey", __name__)


@customer_journey_blueprint.route("/start", methods=["POST"])
def start_journey():
    """
    Endpoint: /start

    Description:
    This endpoint initializes a new customer journey. It performs the following actions:

    1. Creates a new entry in the `CustomerJourney` table, marking the journey as "in-progress" with a provided `journeyId` and `sessionId`.
    2. Optionally, stores the last step of the journey if provided.
    #. Returns the customer journey ID (`cjid`).

    Method: POST
    Request Body:
    {
        "journeyId": int,  # Required, the ID of the journey being started
        "sessionId": string,  # Required, the ID of the existing session
        "lastStep": string    # Optional, the last step in the journey (if applicable)
    }

    Response:
    {
        "message": "Customer journey initialized",
        "CJID": int             # The customer journey ID
    }
    """
    data = request.get_json()

    journey_id = data.get("journeyId")
    session_id = data.get("sessionId")
    last_step = data.get("lastStep")  # Optional

    if not journey_id or not session_id:
        return jsonify({"error": "Journey ID and Session ID are required"}), 400

    # Create a new customer journey entry
    customer_journey = CustomerJourney(
        journey_id=journey_id,
        session_id=session_id,
        last_step=last_step  # Optional: if the last step is provided
    )

    db.session.add(customer_journey)

    try:
        db.session.commit()
        return jsonify({
            "message": "Customer journey initialized",
            "cjid": customer_journey.id  # Return the customer journey ID (CJID)
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to initialize journey", "message": str(e)}), 500

@customer_journey_blueprint.route("/<int:cjid>/status", methods=["PUT"])
def update_status(cjid):
    """
    Endpoint: /<cjid>/status

    Description:
    This endpoint updates the status of an existing customer journey. It accepts the journey ID (`cjid`) and a new status.

    Method: PUT
    Request Body:
    {
        "status": string  # Required, the new status of the customer journey (e.g., "in-progress", "completed", etc.)
    }

    Response:
    {
        "message": "Customer journey status updated",
        "CJID": int,      # The customer journey ID
        "status": string  # The updated status
    }
    """
    data = request.get_json()
    new_status = data.get("status")

    if not new_status:
        return jsonify({"error": "Status is required"}), 400

    # Retrieve the customer journey by ID
    customer_journey = CustomerJourney.query.get(cjid)
    if not customer_journey:
        return jsonify({"error": "Customer journey not found"}), 404

    # Update the status
    customer_journey.status = new_status

    try:
        db.session.commit()
        return jsonify({
            "message": "Customer journey status updated",
            "cjid": customer_journey.id,
            "status": customer_journey.status
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update status", "message": str(e)}), 500
