"""
Gemini-powered AI engine for the Kyron Medical patient chat.
"""
import json
import re
from datetime import datetime

from google import genai
from google.genai import types
from django.conf import settings

from .doctors import DOCTORS, PRACTICE_INFO, generate_availability, get_doctor_by_id

_client = None
_client_key = None


def get_client():
    global _client, _client_key
    key = settings.GEMINI_API_KEY
    if _client is None or _client_key != key:
        _client = genai.Client(api_key=key)
        _client_key = key
    return _client


SYSTEM_PROMPT = """You are Kyra, a friendly and professional AI patient assistant for Kyron Medical Practice.
You help patients with:
1. Scheduling appointments
2. Checking prescription refill status
3. Providing practice information (address, hours, etc.)

CRITICAL RULES:
- NEVER provide medical advice, diagnoses, or treatment recommendations.
- NEVER say anything that could be interpreted as a medical opinion.
- If a patient asks for medical advice, politely redirect them to schedule an appointment with a doctor.
- Always be warm, empathetic, and professional.
- Keep responses concise (2-4 sentences max unless listing options).
- Use the patient's first name once you know it.

PRACTICE INFORMATION:
""" + json.dumps(PRACTICE_INFO, indent=2) + """

AVAILABLE DOCTORS:
""" + json.dumps([{
    "id": d["id"],
    "name": d["name"],
    "title": d["title"],
    "specialty": d["specialty"],
    "body_parts": d["body_parts"],
    "office": d["office"],
} for d in DOCTORS], indent=2) + """

CONVERSATION FLOW FOR APPOINTMENT SCHEDULING:
1. Greet the patient warmly. Ask what you can help with today.
2. If scheduling: collect their info (first name, last name, date of birth, phone number, email address) and reason for visit.
   - Ask for all info you don't have yet. You can collect multiple fields at once if the patient volunteers them.
   - Be conversational, not robotic. E.g., "Great! To get you set up, I'll need a few details..."
3. Based on the reason/body part, semantically match them to the right doctor. If no match exists among our specialists, say "Our practice doesn't currently treat that condition, but we'd recommend consulting with your primary care physician."
4. Present 3-5 available time slots clearly numbered. If the patient has preferences (like "Tuesday" or "afternoon"), filter accordingly.
5. Once they choose a slot number or describe their preference, confirm the appointment and let them know a confirmation email is being sent.

CRITICAL — ALWAYS extract patient data:
Whenever the patient shares ANY personal detail (name, DOB, phone, email), you MUST include an update_patient JSON block.
If someone sends a 10-digit number, that is a phone number. If they send something with @ it's an email.
Use EXACTLY this format with EXACTLY these field names:
```json
{"action": "update_patient", "first_name": "...", "last_name": "...", "dob": "YYYY-MM-DD", "phone": "...", "email": "..."}
```
Only include fields you actually collected in that message. Omit fields you don't know yet.

When you match a doctor based on symptoms:
```json
{"action": "match_doctor", "doctor_id": "dr_xxx", "reason": "brief reason text"}
```

When the patient confirms a specific slot, include:
```json
{"action": "book_appointment", "date": "YYYY-MM-DD", "time": "HH:MM AM/PM"}
```

For prescription refill: gather patient info first (name, DOB for verification), then simulate forwarding to their doctor's office.

CURRENT DATETIME: """ + datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")


def build_contents(messages: list[dict], new_message: str) -> list[types.Content]:
    """Convert message history to Gemini contents format."""
    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part(text=new_message)]))
    return contents


def extract_json_actions(text: str) -> list[dict]:
    """Pull out JSON action blocks from the AI response."""
    actions = []
    # Match ```json { ... } ``` fenced blocks
    for match in re.findall(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL):
        try:
            obj = json.loads(match)
            if "action" in obj:
                actions.append(obj)
        except json.JSONDecodeError:
            continue
    # Match any bare JSON objects containing "action" key
    for match in re.findall(r'\{[^{}]*"action"\s*:\s*"[^"]+?"[^{}]*\}', text):
        try:
            obj = json.loads(match)
            if obj not in actions:
                actions.append(obj)
        except json.JSONDecodeError:
            continue
    return actions


def clean_response(text: str) -> str:
    """Remove JSON action blocks from the display text."""
    # Remove fenced ```json/``` blocks
    cleaned = re.sub(r'```(?:json)?\s*\{.*?\}\s*```', '', text, flags=re.DOTALL)
    # Remove any bare JSON objects containing "action" key
    cleaned = re.sub(r'\{[^{}]*"action"\s*:\s*"[^"]+?"[^{}]*\}', '', cleaned)
    # Collapse multiple blank lines
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


def get_available_slots_for_doctor(doctor_id: str, preference: str = None, limit: int = 5) -> list[dict]:
    """Get available slots, optionally filtered by day/time preference."""
    slots = generate_availability(doctor_id)
    today_str = datetime.now().strftime("%Y-%m-%d")
    slots = [s for s in slots if s["date"] > today_str]

    if preference:
        pref_lower = preference.lower()
        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
        for day in day_names:
            if day in pref_lower:
                slots = [s for s in slots if s["day_of_week"].lower() == day]
                break

        if "morning" in pref_lower:
            slots = [s for s in slots if "AM" in s["time"]]
        elif "afternoon" in pref_lower:
            slots = [s for s in slots if "PM" in s["time"] and int(s["time"].split(":")[0]) < 5]
        elif "evening" in pref_lower:
            slots = [s for s in slots if "PM" in s["time"] and int(s["time"].split(":")[0]) >= 4]

    return slots[:limit]


def chat_with_ai(session_data: dict, user_message: str) -> dict:
    """
    Main conversation handler.
    Returns: {"response": str, "actions": list[dict], "display_text": str}
    """
    c = get_client()

    context_parts = []

    if session_data.get("matched_doctor_id"):
        doctor = get_doctor_by_id(session_data["matched_doctor_id"])
        if doctor:
            slots = get_available_slots_for_doctor(doctor["id"], preference=user_message, limit=8)
            context_parts.append(
                f"\n[SYSTEM: Patient matched with {doctor['name']}. "
                f"Available upcoming slots: {json.dumps(slots[:8])}]\n"
            )

    if session_data.get("first_name"):
        context_parts.append(
            f"\n[SYSTEM: Patient info so far — "
            f"Name: {session_data.get('first_name', '')} {session_data.get('last_name', '')}, "
            f"DOB: {session_data.get('dob', 'unknown')}, "
            f"Phone: {session_data.get('phone', 'unknown')}, "
            f"Email: {session_data.get('email', 'unknown')}, "
            f"State: {session_data.get('current_state', 'greeting')}]\n"
        )

    full_message = user_message
    if context_parts:
        full_message = "".join(context_parts) + "\nPatient says: " + user_message

    history_messages = session_data.get("messages", [])
    contents = build_contents(history_messages, full_message)

    response = c.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7,
            max_output_tokens=1024,
        ),
    )

    response_text = response.text or ""
    actions = extract_json_actions(response_text)
    display_text = clean_response(response_text)

    return {
        "response": response_text,
        "actions": actions,
        "display_text": display_text,
    }


def get_conversation_summary(messages: list[dict]) -> str:
    """Generate a summary of the chat for voice handoff context."""
    c = get_client()
    conversation_text = "\n".join(
        f"{'Patient' if m['role'] == 'user' else 'Kyra'}: {m['content']}"
        for m in messages
    )
    prompt = (
        "Summarize this patient conversation in 3-4 sentences for a voice AI agent "
        "that will continue the conversation. Include the patient's name, reason for "
        "contacting, any appointment details discussed, and where the conversation left off.\n\n"
        + conversation_text
    )

    response = c.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=256,
        ),
    )
    return response.text or ""
