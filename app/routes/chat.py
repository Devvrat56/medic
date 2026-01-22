from flask import request, current_app
from flask_restx import Namespace, Resource, fields
from werkzeug.datastructures import FileStorage
import uuid

from app.services.groq_service import ask_groq
from app.services.file_service import save_and_process_file
from context import init_conversation as PATIENT_CONTEXT
from context_2 import init_conversation as DOCTOR_CONTEXT, generate_case_summary

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

summary_payload = api.model("SummaryPayload", {
    "session_id": fields.String(required=True, description="Session ID of the patient to summarize"),
})

# Parser for file uploads (multipart/form-data)
upload_parser = api.parser()
upload_parser.add_argument('file', location='files', type=FileStorage, required=True, help='File to upload (PDF, Image, Text)')
upload_parser.add_argument('session_id', location='form', required=True, help='Session ID')


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
            "user_type": user_type,
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

        # Safety guardrails (basic)
        user_type = session.get("user_type", "patient")
        dangerous = ["dose", "dosage", "prescribe", "treatment plan"]
        
        if user_type == "patient" and any(w in user_message.lower() for w in dangerous):
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


# -----------------------------
# GENERATE SUMMARY
# -----------------------------

@api.route("/summary")
class ChatSummary(Resource):
    @api.expect(summary_payload)
    def post(self):
        data = request.json or {}
        session_id = data.get("session_id")

        if not session_id or session_id not in sessions:
            return {"error": "Session not found"}, 404

        # Retrieve history
        history = sessions[session_id]["history"]
        
        # Format for LLM
        conversation_text = ""
        for msg in history:
            role = msg.get("role")
            content = msg.get("content")
            if role == "user":
                conversation_text += f"Patient: {content}\n"
            elif role == "assistant":
                conversation_text += f"AI: {content}\n"
        
        if not conversation_text.strip():
            return {"error": "No conversation found to summarize"}, 400
            
        # Generate the clinical summary using the doctor-side prompt tool
        prompt = generate_case_summary(conversation_text)
        
        try:
            # We send this as a new independent request to the LLM
            summary = ask_groq([{"role": "user", "content": prompt}])
            return {"summary": summary}, 200
        except Exception as e:
            return {"error": f"LLM error: {str(e)}"}, 500


# -----------------------------
# UPLOAD FILE
# -----------------------------

@api.route("/upload")
class UploadFile(Resource):
    @api.expect(upload_parser)
    def post(self):
        args = upload_parser.parse_args()
        
        session_id = args.get('session_id')
        uploaded_file = args.get('file')

        if not session_id or session_id not in sessions:
            return {"error": "Invalid or missing session_id"}, 400
        
        if not uploaded_file:
            return {"error": "No file provided"}, 400

        try:
            # Extract text from the file (PDF, Image, etc.)
            extracted_text = save_and_process_file(uploaded_file)
            
            if not extracted_text:
                return {"error": "Could not extract text from the file. It might be empty or unreadable."}, 400
                
            # Add context to the session
            system_note = f"\n[SYSTEM UPDATE]: The user uploaded a file named '{uploaded_file.filename}'. Content:\n{extracted_text}\n"
            
            sessions[session_id]["history"].append({
                "role": "system", 
                "content": system_note
            })
            
            return {
                "message": "File uploaded and processed. The assistant now has this context.",
                "filename": uploaded_file.filename,
                "extracted_length": len(extracted_text)
            }, 200
            
        except ValueError as ve:
             return {"error": str(ve)}, 400
        except Exception as e:
            return {"error": f"Failed to process file: {str(e)}"}, 500
