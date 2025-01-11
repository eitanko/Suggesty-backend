from flask import Blueprint, request, jsonify
import boto3
import base64
from uuid import uuid4
from config import Config  # Import the centralized configuration

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

@step_blueprint.route('/', methods=['POST'])
def save_step():
    try:
        # Log the incoming request data
        data = request.json
        print(f"Received data: {data}")

        # Extract and decode the screenshot
        screenshot_data = data.get('screenshot')
        print(f"Screenshot data: {screenshot_data[:100]}")  # Log first 100 characters of the screenshot data for inspection

        if screenshot_data:
            # Generate a unique filename
            file_name = f"screenshots/{uuid4()}.png"
            print(f"Generated file name: {file_name}")

            # Decode the base64 image
            try:
                image_data = base64.b64decode(screenshot_data.split(',')[1])
                print(f"Decoded image data size: {len(image_data)} bytes")
            except Exception as decode_error:
                print(f"Error decoding image data: {decode_error}")
                return jsonify({"success": False, "error": "Error decoding image data"}), 400

            # Upload the file to S3 and get the URL
            screenshot_url = upload_to_s3(image_data, file_name, BUCKET_NAME)
            print(f"S3 URL: {screenshot_url}")
        else:
            screenshot_url = None
            print("No screenshot data provided")

        # Save step details
        step_details = {
            "journeyId": data["journeyId"],
            "url": data["url"],
            "eventType": data["eventType"],
            "element": data["element"],
            "screenshotUrl": screenshot_url,
            "index": data["index"],
        }

        print(f"Step details: {step_details}")

        # Add step_details to your database here
        # Example:
        # db.collection.insert_one(step_details)

        return jsonify({"success": True, "message": "Step saved successfully", "screenshotUrl": screenshot_url}), 200
    except Exception as e:
        print(f"Error saving step: {str(e)}")  # Log the error
        return jsonify({"success": False, "error": str(e)}), 500
