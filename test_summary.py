import requests
import json
import time

BASE_URL = "http://127.0.0.1:8080"

def test_summary_flow():
    print("1. Initializing Patient Session...")
    init_payload = {
        "user_type": "patient",
        "cancer_type": "Lung Cancer",
        "cancer_stage": "Stage 2",
        "language": "en"
    }
    resp = requests.post(f"{BASE_URL}/chat/init", json=init_payload)
    if resp.status_code != 201:
        print(f"FAILED: Init failed {resp.text}")
        return
    
    session_id = resp.json().get("session_id")
    print(f"   Session ID: {session_id}")

    print("\n2. Sending Messages (Simulating Patient)...")
    messages = [
        "I have been coughing a lot recently.",
        "It started about 2 months ago.",
        "I also feel very tired and lost some weight."
    ]

    for msg in messages:
        print(f"   Patient: {msg}")
        payload = {"session_id": session_id, "message": msg}
        resp = requests.post(f"{BASE_URL}/chat/message", json=payload)
        if resp.status_code == 200:
            ai_reply = resp.json().get("reply", "")
            print(f"   AI: {ai_reply[:50]}...") # Print first 50 chars
        else:
            print(f"   FAILED: Message failed {resp.text}")

    print("\n3. Generating Summary (Doctor View) - Session Based...")
    summary_payload = {"session_id": session_id}
    resp = requests.post(f"{BASE_URL}/chat/summary", json=summary_payload)
    
    if resp.status_code == 200:
        summary = resp.json().get("summary")
        print("\nSUCCESS! Summary Generated:")
        print("="*40)
        print(summary[:200] + "...")
        print("="*40)
    else:
        print(f"FAILED: Summary generation failed {resp.text}")

    print("\n4. Generating Summary (Stateless Mode) - History Based...")
    # Test the new functionality where we send history directly
    history_payload = {
        "history": [
            {"role": "user", "content": "I have severe headaches."},
            {"role": "assistant", "content": "How long have you had them?"},
            {"role": "user", "content": "For about 3 weeks. They are very painful."}
        ]
    }
    resp = requests.post(f"{BASE_URL}/chat/summary", json=history_payload)

    if resp.status_code == 200:
        summary = resp.json().get("summary")
        print("\nSUCCESS! Stateless Summary Generated:")
        print("="*40)
        print(summary[:200] + "...")
        print("="*40)
    else:
        print(f"FAILED: Stateless summary failed {resp.text}")

if __name__ == "__main__":
    # Give the server a moment to start
    time.sleep(2)
    try:
        test_summary_flow()
    except Exception as e:
        print(f"Test Execution Error: {e}")
