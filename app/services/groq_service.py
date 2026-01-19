from flask import request, current_app
from flask_restx import Namespace, Resource, fields
import uuid

from app.services.groq_service import ask_groq, transcribe_audio
from context import init_conversation as PATIENT_CONTEXT
from context_2 import init_conversation as DOCTOR_CONTEXT

api = Namespace("chat", description="Oncology Assistant Chat")

sessions = {}

init_payload = api.model("Init", {
    "user_type": fields.String(required=True, enum=["patient", "doctor"]),
    "cancer_type": fields.String,
    "cancer_stage": fields.String,
    "language": fields.String,
    "doctor_id": fields.String
})

message_payload = api.model("Message", {
    "session_id": fields.String(required=True),
    "message": fields.String(required=True),
    "is_voice": fields.Boolean
})


@api.route("/init")
class Init(Resource):
    @api.expect(init_payload)
    def post(self):
        data = api.payload

        if data["user_type"] == "doctor":
            if data.get("doctor_id") != current_app.config["DOCTOR_ID"]:
                return {"error": "Unauthorized doctor"}, 403

        session_id = str(uuid.uuid4())

        base_prompt = (
            DOCTOR_CONTEXT()
            if data["user_type"] == "doctor"
            else PATIENT_CONTEXT()
        )

        system_prompt = f"""
{base_prompt}

Cancer type: {data.get("cancer_type", "Unknown")}
Stage: {data.get("cancer_stage", "Unknown")}
Language: {data.get("language", "en")}
"""

        sessions[session_id] = {
            "history": [{"role": "system", "content": system_prompt}],
            "ui": []
        }

        return {"session_id": session_id}, 201


@api.route("/message")
class Message(Resource):
    @api.expect(message_payload)
    def post(self):
        data = request.json
        session_id = data["session_id"]

        if session_id not in sessions:
            return {"error": "Invalid session"}, 400

        message = data["message"]
        session = sessions[session_id]

        session["history"].append({"role": "user", "content": message})
        reply = ask_groq(session["history"])
        session["history"].append({"role": "assistant", "content": reply})

        session["ui"].append(("You", message))
        session["ui"].append(("Assistant", reply))

        return {"reply": reply}
