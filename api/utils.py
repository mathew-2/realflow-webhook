# import os
# import json


# latest_json = None

# # Create logs/ directory if it doesn't exist
# def ensure_logs_dir():
#     base_dir = "/tmp"  # Vercel's only writable directory
#     logs_dir = os.path.join(base_dir, "logs", "call_logs")
#     os.makedirs(logs_dir, exist_ok=True)
#     return logs_dir


# # Convert any data to single-line JSON string
# def to_jsonl_line(data):
#     return json.dumps(data)

# # Save a dictionary to a JSON file
# def save_json_to_file(data, filepath):
#     with open(filepath, "w") as f:
#         json.dump(data, f, indent=2)

# # Load a JSON file if it exists
# def load_json_if_exists(filepath):
#     if os.path.exists(filepath):
#         with open(filepath, "r") as f:
#             return json.load(f)
#     return None

# def extract_and_update_call_state(data):
#     """
#     Extracts call_id from data['call']['id'] and updates logs for Set_Lead_Field / Submit_Lead.
#     Handles toolCalls inside data['message'].
#     """
#     global latest_json
#     # Extract call_id safely
#     # call_id = data.get("message",{}).get("call", {}).get("id")
#     call_id = data["message"]["call"]["id"]
#     if not call_id:
#         print(" No call_id found in webhook data.")
#         return None

#     # filepath = f"logs/call_logs/{call_id}.json"

#     logs_dir = ensure_logs_dir()
#     filepath = os.path.join(logs_dir, f"{call_id}.json")

#     # Load or initialize existing state
#     existing = load_json_if_exists(filepath)
#     if not existing:
#         existing = {"call_id": call_id, "call_details": {}}

#     # Extract toolCalls from the correct location
#     tool_calls = []
#     if "message" in data and "toolCalls" in data["message"]:
#         tool_calls = data["message"]["toolCalls"]
#     elif "toolCallList" in data:
#         tool_calls = data["toolCallList"]
#     elif "toolWithToolCallList" in data:
#         tool_calls = data["toolWithToolCallList"]

#     if not tool_calls:
#         print(f" No toolCalls found for call {call_id}")
#         return existing

#     # Iterate and update arguments
#     for call in tool_calls:
#         try:
#             func = call["function"]
#             func_name = func["name"]
#             args = func["arguments"]
#         except (KeyError, TypeError):
#             # skip malformed call entries
#             continue

#         # Some toolCalls send arguments as JSON strings
#         if isinstance(args, str):
#             try:
#                 args = json.loads(args)
#             except json.JSONDecodeError:
#                 continue

#         # Handle Set_Lead_Field and Submit_Lead
#         if func_name in ["Update_Lead_Field", "Finalize_Lead_Submission"]:
#             if func_name not in existing["call_details"]:
#                 existing["call_details"][func_name] = {"name": func_name, "arguments": {}}

#             # For Set_Lead_Field, map field/value
#             if func_name == "Update_Lead_Field" and "field" in args and "value" in args:
#                 existing["call_details"][func_name]["arguments"][args["field"]] = args["value"]
#             else:
#                 for k, v in args.items():
#                     existing["call_details"][func_name]["arguments"][k] = v

#     # Save and return updated log
#     save_json_to_file(existing, filepath)
#     return existing


# =================================================================================

# import json

# # Store all processed webhook payloads in memory
# all_json = []

# def extract_and_update_call_state(data):
#     """
#     Extracts call info and tool calls from webhook payload.
#     Stores every call in memory (no file writes).
#     """
#     global all_json

#     # Safely get call_id
#     call_id = (
#         data.get("message", {})
#             .get("call", {})
#             .get("id")
#     )

#     if not call_id:
#         return {"error": "No call_id found in webhook data"}

#     # Get tool calls if available
#     tool_calls = []
#     msg = data.get("message", {})

#     if "toolCalls" in msg:
#         tool_calls = msg["toolCalls"]
#     elif "toolCallList" in data:
#         tool_calls = data["toolCallList"]
#     elif "toolWithToolCallList" in data:
#         tool_calls = data["toolWithToolCallList"]

#     # Build clean summary for this webhook
#     summary = {
#         "call_id": call_id,
#         "tool_calls_count": len(tool_calls),
#         "tool_calls": []
#     }

#     for call in tool_calls:
#         try:
#             func = call["function"]
#             name = func.get("name", "")
#             args = func.get("arguments", {})

#             if isinstance(args, str):
#                 args = json.loads(args)

#             summary["tool_calls"].append({
#                 "name": name,
#                 "args": args
#             })
#         except Exception:
#             continue

#     # Append this summary to history
#     all_json.append(summary)
#     return summary

# def get_latest_json():
#     """Return last stored webhook json"""
#     return all_json





import json

# Store consolidated leads by call_id
lead_records = {}

def extract_and_update_call_state(data):
    """
    Consolidates all tool calls for each call_id into one complete JSON record.
    """
    global lead_records

    call_id = (
        data.get("message", {})
            .get("call", {})
            .get("id")
    )
    if not call_id:
        return {"error": "No call_id found"}

    # Initialize record if not exists
    if call_id not in lead_records:
        lead_records[call_id] = {
            "call_id": call_id,
            "lead_fields": {},
            "conversation_notes": [],
            "final_submission": {}
        }

    record = lead_records[call_id]

    # Detect tool calls
    msg = data.get("message", {})
    tool_calls = (
        msg.get("toolCalls")
        or data.get("toolCallList")
        or data.get("toolWithToolCallList")
        or []
    )

    # Process each tool call
    for call in tool_calls:
        try:
            func = call["function"]
            name = func.get("name")
            args = func.get("arguments", {})
            if isinstance(args, str):
                args = json.loads(args)
        except Exception:
            continue

        # Update_Lead_Field → merge structured lead fields
        if name == "Update_Lead_Field":
            record["lead_fields"].update(args)

        # Add_Conversation_Note → append note text
        elif name == "Add_Conversation_Note":
            note = args.get("conversation_note", "")
            if note:
                record["conversation_notes"].append(note)

        # Finalize_Lead_Submission → store consent + summary
        elif name == "Finalize_Lead_Submission":
            record["final_submission"].update(args)

        # Record_Consent_Decline → capture reason
        elif name == "Record_Consent_Decline":
            record["final_submission"]["decline_reason"] = args.get("decline_reason", "")

    # Save back to dict
    lead_records[call_id] = record
    return record


def get_latest_json():
    """
    Return the consolidated dictionary of all call_ids and their accumulated data.
    """
    return list(lead_records.values())