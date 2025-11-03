from flask import Flask, request, jsonify
import os
from .utils import ensure_logs_dir, extract_and_update_call_state


app = Flask(__name__)

# Ensure log folder structure exists
ensure_logs_dir()

@app.route('/webhook', methods=['POST'])
def receive_webhook():
    data = request.get_json(force=True)
    
    #print(" Received webhook:", data)

    updated = extract_and_update_call_state(data)
    if updated:
        print(f" Updated log for call_id: {updated['call_id']}")
        return jsonify({"status": "webhook received", "call_id": updated["call_id"]}), 200
    else:
        print(" Could not extract call_id or relevant fields")
        return jsonify({"status": "invalid payload"}), 400

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"message": "Webhook server running "}), 200


def handler(event, context):
    return app(event, context)

if __name__ == '__main__':
    app.run(port=5000)


