import os
import json

# Create logs/ directory if it doesn't exist
def ensure_logs_dir():
    os.makedirs("logs/call_logs", exist_ok=True)

# Convert any data to single-line JSON string
def to_jsonl_line(data):
    return json.dumps(data)

# Save a dictionary to a JSON file
def save_json_to_file(data, filepath):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

# Load a JSON file if it exists
def load_json_if_exists(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return None

def extract_and_update_call_state(data):
    """
    Extracts call_id from data['call']['id'] and updates logs for Set_Lead_Field / Submit_Lead.
    Handles toolCalls inside data['message'].
    """

    # Extract call_id safely
    # call_id = data.get("message",{}).get("call", {}).get("id")
    call_id = data["message"]["call"]["id"]
    if not call_id:
        print(" No call_id found in webhook data.")
        return None

    filepath = f"logs/call_logs/{call_id}.json"

    # Load or initialize existing state
    existing = load_json_if_exists(filepath)
    if not existing:
        existing = {"call_id": call_id, "call_details": {}}

    # Extract toolCalls from the correct location
    tool_calls = []
    if "message" in data and "toolCalls" in data["message"]:
        tool_calls = data["message"]["toolCalls"]
    elif "toolCallList" in data:
        tool_calls = data["toolCallList"]
    elif "toolWithToolCallList" in data:
        tool_calls = data["toolWithToolCallList"]

    if not tool_calls:
        print(f" No toolCalls found for call {call_id}")
        return existing

    # Iterate and update arguments
    for call in tool_calls:
        try:
            func = call["function"]
            func_name = func["name"]
            args = func["arguments"]
        except (KeyError, TypeError):
            # skip malformed call entries
            continue

        # Some toolCalls send arguments as JSON strings
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                continue

        # Handle Set_Lead_Field and Submit_Lead
        if func_name in ["Update_Lead_Field", "Finalize_Lead_Submission"]:
            if func_name not in existing["call_details"]:
                existing["call_details"][func_name] = {"name": func_name, "arguments": {}}

            # For Set_Lead_Field, map field/value
            if func_name == "Update_Lead_Field" and "field" in args and "value" in args:
                existing["call_details"][func_name]["arguments"][args["field"]] = args["value"]
            else:
                for k, v in args.items():
                    existing["call_details"][func_name]["arguments"][k] = v

    # 5️⃣ Save and return updated log
    save_json_to_file(existing, filepath)
    return existing


