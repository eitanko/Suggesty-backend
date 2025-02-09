from flask import Blueprint, jsonify, request
from db import db
from models.journey import Journey
from models.step import Step

journey_blueprint = Blueprint('journey', __name__)

@journey_blueprint.route('/', methods=['POST'])
def add_journey():
    data = request.get_json()

    name = data.get('name')
    description = data.get('description')
    user_id = data.get('userId')

    if not name or not user_id:
        return jsonify({'error': 'Name and userId are required'}), 400

    new_journey = Journey(name=name, description=description, userId=user_id)

    try:
        db.session.add(new_journey)
        db.session.commit()

        return jsonify({
            'message': 'Journey added successfully',
            'id': new_journey.id,
            'name': new_journey.name,
            'description': new_journey.description,
            'userId': new_journey.userId
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to add journey', 'message': str(e)}), 500

# 🔹 GET: Fetch a journey by startUrl
@journey_blueprint.route('/get_journey_id', methods=['GET'])
def get_journey_id():
    start_url = request.args.get("url")

    if not start_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    journey = Journey.query.filter_by(startUrl=start_url).first()

    if journey:
        return jsonify({"id": journey.id})
    else:
        return jsonify({"error": "Journey not found"}), 404

# 🔹 GET: Fetch journey ID & steps for the given URL
@journey_blueprint.route('/get_journey', methods=['GET'])
def get_journey():
    start_url = request.args.get("url")

    if not start_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    journey = Journey.query.filter_by(startUrl=start_url).first()

    if journey:
        # Fetch all steps related to this journey and URL
        steps = Step.query.filter_by(journey_id=journey.id, url=start_url).order_by(Step.index).all()

        steps_data = [
            {
                "event_type": step.event_type,
                "element": step.element
            }
            for step in steps
        ]

        return jsonify({
            "id": journey.id,
            "steps": steps_data
        })

    # If no journey exists for this URL, return None instead of a 404
    return jsonify({
        "id": None,
        "steps": []
    })

