import json
import uuid
from datetime import datetime

from django.conf import settings
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .ai_engine import chat_with_ai, get_conversation_summary
from .doctors import DOCTORS, PRACTICE_INFO, get_doctor_by_id
from .models import Appointment, ChatMessage, ChatSession


def index(request):
    """Landing / chat page."""
    if not request.session.get("chat_session_id"):
        session = ChatSession.objects.create()
        request.session["chat_session_id"] = str(session.session_id)
    return render(request, "chat/index.html", {
        "practice": PRACTICE_INFO,
        "doctors": DOCTORS,
    })


def _get_or_create_session(request) -> ChatSession:
    sid = request.session.get("chat_session_id")
    if sid:
        try:
            return ChatSession.objects.get(session_id=sid)
        except ChatSession.DoesNotExist:
            pass
    session = ChatSession.objects.create()
    request.session["chat_session_id"] = str(session.session_id)
    return session


def _process_actions(session: ChatSession, actions: list[dict]):
    """Apply AI-extracted structured actions to the session."""
    for action in actions:
        act = action.get("action")

        if act == "update_patient":
            if action.get("first_name"):
                session.first_name = action["first_name"]
            if action.get("last_name"):
                session.last_name = action["last_name"]
            dob_val = action.get("dob") or action.get("date_of_birth") or action.get("dob_str")
            if dob_val:
                for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"):
                    try:
                        session.date_of_birth = datetime.strptime(dob_val, fmt).date()
                        break
                    except (ValueError, TypeError):
                        continue
            phone_val = action.get("phone") or action.get("phone_number") or action.get("contact_number")
            if phone_val:
                session.phone_number = str(phone_val)
            email_val = action.get("email") or action.get("email_address")
            if email_val:
                session.email = email_val
            session.current_state = "intake"
            session.save()

        elif act == "match_doctor":
            session.matched_doctor_id = action.get("doctor_id", "")
            session.reason_for_visit = action.get("reason", "")
            session.current_state = "scheduling"
            session.save()

        elif act == "book_appointment":
            session.appointment_date = action.get("date", "")
            session.appointment_time = action.get("time", "")
            session.current_state = "confirmation"
            session.save()
            _create_appointment(session)

        elif act == "present_slots":
            session.current_state = "scheduling"
            session.save()


def _create_appointment(session: ChatSession):
    """Create appointment record and send confirmation email."""
    doctor = get_doctor_by_id(session.matched_doctor_id)
    if not doctor:
        return

    appt = Appointment.objects.create(
        session=session,
        patient_first_name=session.first_name,
        patient_last_name=session.last_name,
        patient_email=session.email,
        patient_phone=session.phone_number,
        patient_dob=session.date_of_birth or datetime.now().date(),
        doctor_id=session.matched_doctor_id,
        doctor_name=doctor["name"],
        appointment_date=session.appointment_date,
        appointment_time=session.appointment_time,
        reason=session.reason_for_visit,
    )

    _send_confirmation_email(appt, doctor)
    if session.sms_opt_in:
        _send_confirmation_sms(appt, doctor)


def _send_confirmation_email(appt: Appointment, doctor: dict):
    """Send HTML confirmation email."""
    if not appt.patient_email or not settings.EMAIL_HOST_USER:
        return

    subject = f"Appointment Confirmed — Kyron Medical Practice"
    html_message = f"""
    <div style="font-family: 'Helvetica Neue', sans-serif; max-width: 600px; margin: 0 auto; background: #0a0f1c; color: #ffffff; border-radius: 16px; overflow: hidden;">
        <div style="background: linear-gradient(135deg, #00c2ff 0%, #7c3aed 100%); padding: 32px; text-align: center;">
            <h1 style="margin: 0; font-size: 24px; color: #ffffff;">Kyron Medical</h1>
            <p style="margin: 8px 0 0; opacity: 0.9; color: #e0e0e0;">Appointment Confirmation</p>
        </div>
        <div style="padding: 32px;">
            <p>Hi {appt.patient_first_name},</p>
            <p>Your appointment has been confirmed! Here are your details:</p>
            <div style="background: rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; margin: 20px 0;">
                <p><strong>Doctor:</strong> {doctor['name']} — {doctor['title']}</p>
                <p><strong>Date:</strong> {appt.appointment_date}</p>
                <p><strong>Time:</strong> {appt.appointment_time}</p>
                <p><strong>Location:</strong> {doctor['office']}</p>
                <p><strong>Reason:</strong> {appt.reason}</p>
            </div>
            <p>Please arrive 15 minutes early for check-in. If you need to reschedule, reply to this email or call us at {PRACTICE_INFO['phone']}.</p>
            <p style="margin-top: 24px; color: #888;">— Kyra, your Kyron Medical AI Assistant</p>
        </div>
    </div>
    """
    plain_message = (
        f"Hi {appt.patient_first_name},\n\n"
        f"Your appointment is confirmed!\n\n"
        f"Doctor: {doctor['name']} — {doctor['title']}\n"
        f"Date: {appt.appointment_date}\n"
        f"Time: {appt.appointment_time}\n"
        f"Location: {doctor['office']}\n"
        f"Reason: {appt.reason}\n\n"
        f"Please arrive 15 minutes early. Call {PRACTICE_INFO['phone']} to reschedule.\n\n"
        f"— Kyra, Kyron Medical AI Assistant"
    )

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[appt.patient_email],
            html_message=html_message,
            fail_silently=True,
        )
        appt.confirmation_email_sent = True
        appt.save()
    except Exception:
        pass


def _send_confirmation_sms(appt: Appointment, doctor: dict):
    """Send appointment confirmation SMS via Twilio."""
    if not appt.patient_phone or not settings.TWILIO_ACCOUNT_SID:
        return
    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        body = (
            f"Kyron Medical — Appointment Confirmed\n\n"
            f"Doctor: {doctor['name']}\n"
            f"Date: {appt.appointment_date}\n"
            f"Time: {appt.appointment_time}\n"
            f"Location: {doctor['office']}\n\n"
            f"Please arrive 15 min early. Call {PRACTICE_INFO['phone']} to reschedule."
        )
        phone = appt.patient_phone
        if not phone.startswith('+'):
            phone = '+1' + phone.replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
        client.messages.create(
            body=body,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone,
        )
        appt.confirmation_sms_sent = True
        appt.save()
    except Exception:
        pass


@csrf_exempt
@require_POST
def send_message(request):
    """Handle incoming chat message from the frontend."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    user_message = data.get("message", "").strip()
    if not user_message:
        return JsonResponse({"error": "Empty message"}, status=400)

    session = _get_or_create_session(request)

    ChatMessage.objects.create(session=session, role="user", content=user_message)

    messages = list(session.messages.values("role", "content", "timestamp").order_by("timestamp"))

    session_data = {
        "first_name": session.first_name,
        "last_name": session.last_name,
        "dob": str(session.date_of_birth) if session.date_of_birth else "",
        "phone": session.phone_number,
        "email": session.email,
        "matched_doctor_id": session.matched_doctor_id,
        "current_state": session.current_state,
        "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
    }

    try:
        ai_result = chat_with_ai(session_data, user_message)
    except Exception as e:
        error_msg = str(e)
        if "API_KEY_INVALID" in error_msg or "API key not valid" in error_msg:
            fallback = "I'm temporarily unable to connect. Please ensure your Gemini API key is configured correctly in the .env file."
        else:
            fallback = "I'm sorry, I encountered a temporary issue. Please try again in a moment."
        return JsonResponse({"response": fallback, "session_state": session.current_state})

    ChatMessage.objects.create(session=session, role="assistant", content=ai_result["display_text"])

    _process_actions(session, ai_result["actions"])

    session.refresh_from_db()

    response_data = {
        "response": ai_result["display_text"],
        "session_state": session.current_state,
        "patient_name": f"{session.first_name} {session.last_name}".strip(),
    }

    if session.current_state == "confirmation" and session.appointment_date:
        doctor = get_doctor_by_id(session.matched_doctor_id)
        response_data["appointment"] = {
            "doctor": doctor["name"] if doctor else "",
            "date": session.appointment_date,
            "time": session.appointment_time,
            "location": doctor["office"] if doctor else "",
        }

    return JsonResponse(response_data)


@csrf_exempt
@require_POST
def initiate_voice_call(request):
    """Initiate a Vapi voice call to the patient's phone with chat context."""
    session = _get_or_create_session(request)

    if not session.phone_number:
        return JsonResponse({"error": "No phone number on file. Please provide your phone number first."}, status=400)

    messages = list(session.messages.values("role", "content").order_by("timestamp"))
    summary = get_conversation_summary([{"role": m["role"], "content": m["content"]} for m in messages])

    if not settings.VAPI_API_KEY:
        session.voice_call_initiated = True
        session.save()
        return JsonResponse({
            "status": "demo_mode",
            "message": (
                f"Voice call would be initiated to {session.phone_number}. "
                "Configure VAPI_API_KEY in .env to enable real calls."
            ),
            "context_summary": summary,
        })

    import requests

    try:
        resp = requests.post(
            "https://api.vapi.ai/call/phone",
            headers={
                "Authorization": f"Bearer {settings.VAPI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "phoneNumberId": settings.VAPI_PHONE_NUMBER_ID,
                "assistantId": settings.VAPI_ASSISTANT_ID,
                "assistantOverrides": {
                    "firstMessage": (
                        f"Hi {session.first_name or 'there'}! This is Kyra from Kyron Medical. "
                        "I'm continuing our chat conversation. " + summary
                    ),
                },
                "customer": {
                    "number": (
                        session.phone_number if session.phone_number.startswith('+')
                        else '+1' + session.phone_number.replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
                    ),
                    "name": f"{session.first_name} {session.last_name}".strip(),
                },
            },
            timeout=15,
        )

        if resp.status_code == 201:
            call_data = resp.json()
            session.voice_call_initiated = True
            session.vapi_call_id = call_data.get("id", "")
            session.save()
            return JsonResponse({
                "status": "call_initiated",
                "message": f"Calling {session.phone_number} now. Please answer your phone!",
                "call_id": call_data.get("id"),
            })
        else:
            return JsonResponse({
                "error": f"Failed to initiate call: {resp.text}",
            }, status=500)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def reset_session(request):
    """Reset the chat session."""
    if "chat_session_id" in request.session:
        del request.session["chat_session_id"]
    return JsonResponse({"status": "reset"})


@csrf_exempt
@require_POST
def opt_in_sms(request):
    """Handle SMS opt-in."""
    session = _get_or_create_session(request)
    session.sms_opt_in = True
    session.save()
    return JsonResponse({"status": "opted_in", "message": "You've opted in for SMS notifications."})
