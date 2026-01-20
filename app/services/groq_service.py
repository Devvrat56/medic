import os
from flask import current_app
from groq import Groq

def get_client():
    api_key = current_app.config.get("GROQ_API_KEY")
    if not api_key:
        api_key = os.environ.get("GROQ_API_KEY")
    
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in configuration or environment variables")
        
    return Groq(api_key=api_key)

def ask_groq(messages, model="llama-3.3-70b-versatile"):
    """
    Send messages to Groq API and return the response content.
    messages: list of dicts [{"role": "user", "content": "..."}]
    """
    client = get_client()
    
    try:
        completion = client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=0.6,
            max_tokens=1024,
            top_p=1,
            stop=None,
            stream=False
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Error calling Groq API: {e}")
        raise e

def transcribe_audio(audio_file):
    """
    Transcribe audio using Groq Whisper.
    audio_file: path to file or file-like object (opened in binary mode) with a name attribute or tuple.
    """
    client = get_client()
    
    try:
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3",
            response_format="json"
        )
        return transcription.text
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        raise e
