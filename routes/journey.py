from flask import Blueprint, request, jsonify
import boto3
import base64
from uuid import uuid4
from config import Config  # Import the centralized configuration
from models import Journey
from models import Step
from db import db

journey_blueprint = Blueprint('journey', __name__)



# 🔹 Create New Journey - Creates a new journey in the system
@journey_blueprint.route('/', methods=['POST'])
def add_journey():
    """
    📌 Create a New Journey

    Creates a new journey in the system.

    🔹 **Endpoint:** `POST /journey`
    🔹 **Request Body (JSON):**
    ```json
    {
        "name": "User Onboarding",
        "description": "A journey for onboarding new users",
        "userId": 123
    }
    ```

    🔹 **Required Fields:**
      - `name` (string): The name of the journey.
      - `userId` (integer): The ID of the user associated with the journey.

    🔹 **Optional Fields:**
      - `description` (string): A description of the journey.

    🔹 **Responses:**
      - `201 Created` - Successfully added the journey.
      - `400 Bad Request` - Missing required fields (`name`, `userId`).
      - `500 Internal Server Error` - Database error.

    🔹 **Example Success Response:**
    ```json
    {
        "message": "Journey added successfully",
        "id": 1,
        "name": "User Onboarding",
        "description": "A journey for onboarding new users",
        "userId": 123
    }
    ```

    🔹 **Example Error Response:**
    ```json
    {
        "error": "Name and userId are required"
    }
    ```

    """
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



# 🔹 Get Journey Steps: Retrieves a journey and its steps based on the given start URL
@journey_blueprint.route('/', methods=['GET'])
def get_journey_by_url():
    """
    GET /journeys?url=<start_url>

    This endpoint retrieves a journey and its steps based on the given start URL.

    Query Parameter:
    - url (string): The starting URL of the journey.

    Behavior:
    - Fetches the journey that matches the provided start URL.
    - Retrieves all related steps for the journey, ordered by index.
    - If no journey exists for this URL, returns an ID of None and an empty steps list.

    Success Response (200):
    {
        "id": 123,
        "steps": [
            {
                "event_type": "click",
                "element": "#next-button"
            },
            {
                "event_type": "scroll",
                "element": "body"
            }
        ]
    }

    """
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

# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=Config.AWS_ACCESS_KEY,
    aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY
)
# Configuration
BUCKET_NAME = Config.S3_BUCKET_NAME


def upload_to_s3(file_data, file_name, bucket_name):
    """
    Uploads an image file to S3 bucket and returns the URL of the uploaded file.
    :param file_data: The base64-encoded image data.
    :param file_name: The name to be assigned to the file in the S3 bucket.
    :param bucket_name: The name of the S3 bucket to upload the file to.
    :return: The URL of the uploaded file.
    """
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=file_data,
            ContentType='image/png',
        )
        # Generate a public or pre-signed URL for the uploaded object
        url = f"https://{bucket_name}.s3.amazonaws.com/{file_name}"
        return url
    except Exception as e:
        raise Exception(f"Failed to upload to S3: {str(e)}")


@journey_blueprint.route('/<int:journey_id>/step', methods=['POST', 'OPTIONS'])
def save_step(journey_id):
    """
    API endpoint to save a step in the journey. This endpoint accepts step details, including an optional screenshot.

    **Request Body Example:**
    {
        "journeyId": 1,
        "url": "https://example.com",
        "eventType": "click",
        "element": "button#submit",
        "screenshot": "base64encodedimage",
        "index": 3
    }

    **Parameters:**
    - journey_id (int): The unique ID of the journey to which the step belongs.

    **Response Example:**
    {
        "success": true,
        "message": "Step saved successfully",
        "screenshotUrl": "https://bucketname.s3.amazonaws.com/screenshots/12345.png"
    }

    **Errors:**
    - 400: Missing or invalid data.
    - 500: Internal server error.
    """
    try:
        # Log the incoming request data
        data = request.json

        # Extract and decode the screenshot
        screenshot_data = data.get('screenshot')
        if screenshot_data:
            # Generate a unique filename
            file_name = f"screenshots/{uuid4()}.png"

            # Decode the base64 image
            try:
                image_data = base64.b64decode(screenshot_data.split(',')[1])
            except Exception as decode_error:
                return jsonify({"success": False, "error": "Error decoding image data"}), 400

            # Upload the file to S3 and get the URL
            screenshot_url = upload_to_s3(image_data, file_name, BUCKET_NAME)
        else:
            screenshot_url = None

        # Save step details to the database
        step_details = Step(
            journey_id=journey_id,
            url=data["url"],
            event_type=data["eventType"],
            element=data["element"],
            screen_path=screenshot_url,
            index=data["index"]
        )

        # Add to the database session and commit
        db.session.add(step_details)
        db.session.commit()

        return jsonify({"success": True, "message": "Step saved successfully", "screenshotUrl": screenshot_url}), 200
    except Exception as e:
        print(f"Error saving step: {str(e)}")  # Log the error
        return jsonify({"success": False, "error": str(e)}), 500


# 🔹 Get Final Journey Step: Fetch the final step of a given journey
#@step_blueprint.route('/final_step', methods=['GET'])
@journey_blueprint.route('/<int:journey_id>/steps/final', methods=['GET'])
def get_final_step(journey_id):
    """
    GET /journey/<journey_id>/steps/final

    This endpoint retrieves the final step of a given customer journey.

    Path Parameter:
    - journey_id (int): The unique identifier of the journey.

    Behavior:
    - Fetches the last recorded step of the specified journey, ordered by creation time.
    - Returns the event type, element, and URL of the final step.
    - If no steps are found, returns a 404 error.

    Success Response (200):
    {
        "event_type": "click",
        "element": "#submit-button",
        "url": "https://example.com/checkout"
    }

    Error Response (404):
    {
        "error": "No steps found for this journey"
    }
    """
    # Fetch the last step of the journey, ordered by creation time (assuming `createdAt` exists)
    final_step = Step.query.filter_by(journey_id=journey_id).order_by(Step.created_at.desc()).first()

    if final_step:
        return jsonify({
            "event_type":final_step.event_type,
            "element": final_step.element,
            "url": final_step.url
        })
    else:
        return jsonify({"error": "No steps found for this journey"}), 404

