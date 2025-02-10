from flask import Blueprint, request, jsonify
import boto3
import base64
from uuid import uuid4
from config import Config  # Import the centralized configuration
from db import db
from models.step import Step

step_blueprint = Blueprint('step', __name__)

# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=Config.AWS_ACCESS_KEY,
    aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY
)

# Configuration
BUCKET_NAME = Config.S3_BUCKET_NAME

def upload_to_s3(file_data, file_name, bucket_name):
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

@step_blueprint.route('/', methods=['POST', 'OPTIONS'])
def save_step():
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
            journey_id=data["journeyId"],
            url=data["url"],
            event_type=data["eventType"],
            element=data["element"],
            screen_path=screenshot_url,
            index=data["index"]
        )
        print(step_details)

        # Add to the database session and commit
        db.session.add(step_details)
        db.session.commit()

        return jsonify({"success": True, "message": "Step saved successfully", "screenshotUrl": screenshot_url}), 200
    except Exception as e:
        print(f"Error saving step: {str(e)}")  # Log the error
        return jsonify({"success": False, "error": str(e)}), 500

# 🔹 GET: Fetch steps for a given URL
@step_blueprint.route('/get_steps_by_url', methods=['GET'])
def get_steps_by_url():
    url = request.args.get("url")

    if not url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    steps = Step.query.filter_by(url=url).order_by(Step.index).all()

    steps_data = [
        {
            "id": step.id,
            "journey_id": step.journey_id,
            "event_type": step.event_type,
            "element": step.element,
            "screen_path": step.screen_path,
            "index": step.index
        }
        for step in steps
    ]

    return jsonify({"steps": steps_data})


# 🔹 GET: Fetch the final step of a given journey
@step_blueprint.route('/final_step', methods=['GET'])
def get_final_step():
    journey_id = request.args.get("journeyId")

    if not journey_id:
        return jsonify({"error": "Missing 'journeyId' parameter"}), 400

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