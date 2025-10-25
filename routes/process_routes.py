# This is the main end point called from the app to process all the event data and analytics
import time
from flask import Blueprint, request, jsonify, current_app
from services.job_runner import run_jobs

process_blueprint = Blueprint("process", __name__)

@process_blueprint.route("/<int:account_id>", methods=["GET"])
def process_and_fetch(account_id):
    process_flag = request.args.get("process", "false").lower() == "true"

    if process_flag:
        start_time = time.time()
        with current_app.app_context():
            run_jobs([account_id])
        elapsed = time.time() - start_time

        # Format seconds/minutes nicely
        if elapsed < 60:
            duration_str = f"{elapsed:.2f} seconds"
        else:
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            duration_str = f"{minutes}m {seconds}s"

        return jsonify({
            "message": f"✅ Processing finished for account {account_id}",
            "duration": duration_str
        })
    else:
        return jsonify({
            "message": f"ℹ️ Skipped processing for account {account_id}"
        })
