from flask import request, current_app
from flask_restx import Namespace, Resource, fields, reqparse
import uuid
from datetime import datetime

from app.services.groq_service import ask_groq, transcribe_audio
# from app.services.ocr_service import extract_text_from_file  # implement later

from context import init_conversation as PATIENT_CONTEXT_FUNC
from context_2 import init_conversation as DOCTOR_CONTEXT_FUNC

api = Namespace("chat", description="Oncology Assistant Chat Operations")

# ── Models for Swagger ──
init_payload = api.model("InitConversation", {
    "user_type": fields.String(required=True, enum=["patient", "doctor"]),
    "cancer_type": fields.String(default="Not specified"),
    "cancer_stage": fields.String(default="Unknown"),
    "language": fields.String(default="en", enum=["en", "hi", "pa", "de", "sv"]),
    "doctor_id": fields.String(description="Required only for doctor mode")
})

message_payload = api.model("SendMessage", {
    "session_id": fields.String(required=True),
    "message": fields.String(required=True),
    "is_voice": fields.Boolean(default=False),
    # "audio": fields.Raw()  # multipart/form-data
})

session_response = api.model("SessionResponse", {
    "session_id": fields.String(),
    "system_prompt": fields.String(),
    "history": fields.List(fields.Raw())
})

# In-memory sessions (replace with Redis/DB in production)
sessions = {}

@api.route("/init")
class InitConversation(Resource):
    @api.expect(init_payload)
    def post(self):
        data = api.payload

        if data["user_type"] == "doctor":
            if data.get("doctor_id") != current_app.config["DOCTOR_ID"]:
                return {"error": "Invalid doctor credentials"}, 403

        session_id = str(uuid.uuid4())

        base_prompt = DOCTOR_CONTEXT_FUNC() if data["user_type"] == "doctor" else PATIENT_CONTEXT_FUNC()

        extra = f"""
<IMPORTANT>
Cancer type: {data.get("cancer_type", "Not specified")}
Stage: {data.get("cancer_stage", "Unknown")}
Language code: {data.get("language", "en")}
Always relate answers to this context.
Keep responses short, warm, supportive.
</IMPORTANT>
"""

        system_prompt = base_prompt + "\n\n" + extra

        sessions[session_id] = {
            "user_type": data["user_type"],
            "cancer_type": data.get("cancer_type", "Not specified"),
            "cancer_stage": data.get("cancer_stage", "Unknown"),
            "language": data.get("language", "en"),
            "history": [{"role": "system", "content": system_prompt}],
            "ui_history": []
        }

        return {
            "session_id": session_id,
            "message": "Session initialized successfully"
        }, 201


@api.route("/message")
class SendMessage(Resource):
    @api.expect(message_payload)
    def post(self):
        data = request.form if request.form else request.json
        session_id = data.get("session_id")

        if not session_id or session_id not in sessions:
            return {"error": "Invalid or expired session"}, 400

        session = sessions[session_id]

        # ── Handle voice input ──
        is_voice = data.get("is_voice", False) == "true" or data.get("is_voice", False)
        message = data.get("message")

        if is_voice and "audio" in request.files:
            audio_file = request.files["audio"]
            audio_bytes = audio_file.read()
            try:
                message = transcribe_audio(audio_bytes, session["language"])
            except Exception as e:
                return {"error": f"Voice transcription failed: {str(e)}"}, 500

        if not message:
            return {"error": "Message is required"}, 400

        # Special handling (appointment / dangerous questions)
        message_lower = message.lower()

        if any(kw in message_lower for kw in ["appointment", "book", "schedule", "contact", "call", "emergency"]):
            reply = (
                f"I cannot make bookings directly.\n\n"
                f"• **Emergency**: {current_app.config['FAKE_EMERGENCY_NUMBER']}\n"
                f"• **Appointments**: {current_app.config['FAKE_APPOINTMENT_EMAIL']}\n\n"
                "Would you like help preparing what to say?"
            )
        elif any(w in message_lower for w in ["dose", "dosage", "treatment plan", "prescribe"]):
            reply = "I'm not allowed to give dosages or specific treatment recommendations.\nPlease discuss this with your oncologist."
        else:
            # Normal LLM call
            session["history"].append({"role": "user", "content": message})
            try:
                reply = ask_groq(session["history"])
                session["history"].append({"role": "assistant", "content": reply})
            except Exception as e:
                return {"error": str(e)}, 500

        # Save to ui_history for context
        session["ui_history"].append(("You" if not is_voice else "You (voice)", message))
        session["ui_history"].append(("Assistant", reply))

        return {
            "reply": reply,
            "history": session["ui_history"][-10:]  # last 10 messages for UI
        }


@api.route("/session/<session_id>")
class GetSession(Resource):
    def get(self, session_id):
        if session_id not in sessions:
            return {"error": "Session not found"}, 404
        return {
            "session_id": session_id,
            "user_type": sessions[session_id]["user_type"],
            "cancer_type": sessions[session_id]["cancer_type"],
            "cancer_stage": sessions[session_id]["cancer_stage"],
            "history_preview": sessions[session_id]["ui_history"][-6:]
        }