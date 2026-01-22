import requests
import time
import os

BASE_URL = "http://127.0.0.1:8080"
TEST_FILE = "test_upload.txt"

def test_all_endpoints():
    print("🚀 Starting Complete API Test Suite...")
    
    # 1. Test Init
    print("\n[1/4] Testing /init ...")
    init_payload = {
        "user_type": "patient",
        "cancer_type": "Melanoma",
        "cancer_stage": "Unknown",
        "language": "en"
    }
    resp = requests.post(f"{BASE_URL}/chat/init", json=init_payload)
    if resp.status_code != 201:
        print(f"❌ FAIL: Init failed {resp.text}")
        return
    session_id = resp.json().get("session_id")
    print(f"✅ PASS: Session initialized ({session_id})")

    # 2. Test Message
    print("\n[2/4] Testing /message ...")
    msg_payload = {"session_id": session_id, "message": "What is melanoma?"}
    resp = requests.post(f"{BASE_URL}/chat/message", json=msg_payload)
    if resp.status_code == 200:
        print(f"✅ PASS: Message sent. Reply len: {len(resp.json().get('reply', ''))}")
    else:
        print(f"❌ FAIL: Message failed {resp.text}")

    # 3. Test File Upload
    print("\n[3/4] Testing /upload ...")
    with open(TEST_FILE, "w") as f:
        f.write("This is a test medical report content for analysis.")
    
    with open(TEST_FILE, "rb") as f:
        files = {'file': (TEST_FILE, f, 'text/plain')}
        data = {'session_id': session_id}
        resp = requests.post(f"{BASE_URL}/chat/upload", files=files, data=data)
    
    if resp.status_code == 200:
        print(f"✅ PASS: File uploaded. {resp.json().get('message')}")
    else:
        print(f"❌ FAIL: Upload failed {resp.text}")
    
    # Cleanup
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)

    # 4. Test Summary (Both modes)
    print("\n[4/4] Testing /summary ...")
    
    # A. Session Based
    print("   A. Session mode...")
    resp = requests.post(f"{BASE_URL}/chat/summary", json={"session_id": session_id})
    if resp.status_code == 200:
        print("   ✅ PASS: Session summary generated")
    else:
        print(f"   ❌ FAIL: Session summary failed {resp.text}")

    # B. History Based
    print("   B. History mode...")
    hist_payload = {
        "history": [
            {"role": "user", "content": "I have pain in my back."},
            {"role": "assistant", "content": "Is it sharp or dull?"},
            {"role": "user", "content": "Dull ache for 2 weeks."}
        ]
    }
    resp = requests.post(f"{BASE_URL}/chat/summary", json=hist_payload)
    if resp.status_code == 200:
        print("   ✅ PASS: History summary generated")
    else:
        print(f"   ❌ FAIL: History summary failed {resp.text}")

    print("\n🏁 Test Suite Complete.")

if __name__ == "__main__":
    try:
        test_all_endpoints()
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
