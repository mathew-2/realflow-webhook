import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Store consolidated leads by call_id
lead_records = {}


def push_to_google_sheet(record):
    """
    Push the finalized lead data to Google Sheets.
    """
    try:
        # Retrieve the secret key stored in GitHub secrets
        google_credentials = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")

        if not google_credentials:
            raise ValueError("Google service account credentials not found in environment variables.")  
        

        creds_dict = json.loads(google_credentials)

        # Define the scope and credentials
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_dict ,scope)
        client = gspread.authorize(creds)

        # Open the Google Sheet (replace with your actual sheet name)
        sheet = client.open("Realflow-lead-log").sheet1

        # Prepare the row to insert
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            record["call_id"],
            record["lead_fields"].get("username", ""),
            record["lead_fields"].get("contact_number", ""),
            record["lead_fields"].get("contact_email", ""),
            record["lead_fields"].get("role_inquiry", ""),
            record["lead_fields"].get("lead_intent", ""),
            record["lead_fields"].get("asset_category", ""),
            record["lead_fields"].get("property_area", ""),
            record["lead_fields"].get("budget_range", ""),
            record["lead_fields"].get("timeline_priority", ""),
            record["final_submission"].get("has_consent", ""),
            record["final_submission"].get("conversation_summary", "")
        ]
        
        # Append the row to the sheet
        sheet.append_row(row)
        print(" Lead data pushed to Google Sheet")

    except Exception as e:
        print(f" Failed to push data to Google Sheet: {e}")

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
            # Push to Google Sheets upon finalization
            push_to_google_sheet(record)

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