import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    DOCTOR_ID = "dev_doc24"
    FAKE_EMERGENCY_NUMBER = "+91-214-352-354-235"
    FAKE_APPOINTMENT_EMAIL = "dvvratshuk@softsensor.ai"
    SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-for-dev-only")