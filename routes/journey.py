from flask import Blueprint, jsonify, request
from db import db
from models.journey import Journey

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
