from flask import request, current_app
from flask_restx import Namespace, Resource, fields
import uuid

from app.services.groq_service import ask_groq
from app.context import init_conversation as PATIENT_CONTEXT
from app.context_2 import init_conversation as DOCTOR_CONTEXT

api = Namespace("chat", description="Oncology Assistant Chat")

# In-memory session store (OK for now)
sessions = {}

# -----------------------------
# API MODELS
# -----------------------------

init_payload = api.model("InitPayload", {
    "user_type": fields.String(required=True, enum=["patient", "doctor"]),
    "cancer_type": fields.String,
    "cancer_stage": fields.String,
    "language": fields.String,
    "doctor_id": fields.String,
})

message_payload = api.model("MessagePayload", {
    "session_id": fields.String(required=True),
    "message": fields.String(required=True),
    "is_voice": fields.Boolean,
})

# -----------------------------
# INIT CHAT
# -----------------------------

@api.route("/init")
class InitChat(Resource):
    @api.expect(init_payload)
    def post(self):
        data = request.json or {}

        user_type = data.get("user_type")
        cancer_type = data.get("cancer_type", "Not specified")
        cancer_stage = data.get("cancer_stage", "Unknown")
        language = data.get("language", "en")
        doctor_id = data.get("doctor_id")

        # Doctor auth check
        if user_type == "doctor":
            if doctor_id != current_app.config["DOCTOR_ID"]:
                return {"error": "Unauthorized doctor"}, 403

        session_id = str(uuid.uuid4())

        base_prompt = (
            DOCTOR_CONTEXT()
            if user_type == "doctor"
            else PATIENT_CONTEXT()
        )

        system_prompt = f"""
{base_prompt}

<IMPORTANT CONTEXT>
Cancer type: {cancer_type}
Cancer stage: {cancer_stage}
Language: {language}
</IMPORTANT CONTEXT>
"""

        sessions[session_id] = {
            "history": [
                {"role": "system", "content": system_prompt}
            ]
        }

        return {"session_id": session_id}, 201


# -----------------------------
# SEND MESSAGE
# -----------------------------

@api.route("/message")
class SendMessage(Resource):
    @api.expect(message_payload)
    def post(self):
        # ✅ JSON ONLY (frontend must send JSON)
        data = request.json

        if not data:
            return {"error": "Invalid JSON body"}, 400

        session_id = data.get("session_id")
        user_message = data.get("message")

        if not session_id or not user_message:
            return {"error": "Missing session_id or message"}, 400

        if session_id not in sessions:
            return {"error": "Invalid session"}, 400

        session = sessions[session_id]

        # Safety guardrails
        dangerous = ["dose", "dosage", "prescribe", "treatment plan"]
        if any(w in user_message.lower() for w in dangerous):
            safe_reply = (
                "I can’t help with specific medical decisions or dosages, "
                "but I can explain how doctors usually think about treatment options "
                "and what questions may help when you speak with your oncologist."
            )
            return {"reply": safe_reply}, 200

        # Normal LLM flow
        session["history"].append(
            {"role": "user", "content": user_message}
        )

        try:
            reply = ask_groq(session["history"])
        except Exception as e:
            return {"error": f"LLM error: {str(e)}"}, 500

        session["history"].append(
            {"role": "assistant", "content": reply}
        )

        return {"reply": reply}, 200
