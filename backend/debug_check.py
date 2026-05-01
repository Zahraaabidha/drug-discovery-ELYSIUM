# Run this file from your backend folder to diagnose what's happening
# In VS Code terminal: cd elysium/backend && python debug_check.py

import os
from dotenv import load_dotenv

# Try loading .env explicitly
load_dotenv(dotenv_path=".env", override=True)

key = os.getenv("OPENROUTER_API_KEY", "")
print(f"Key found: {'YES' if key else 'NO - KEY IS MISSING'}")
if key:
    print(f"Key starts with: {key[:12]}...")
    print(f"Key length: {len(key)} chars")
    if key == "changeme" or "your" in key.lower():
        print("WARNING: Key is still the placeholder value!")
    else:
        print("Key looks real - now testing OpenRouter...")
        import requests
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "mistralai/mistral-7b-instruct:free",
                "max_tokens": 50,
                "messages": [{"role": "user", "content": "Say hello in 5 words."}],
            },
            timeout=20,
        )
        print(f"OpenRouter status: {resp.status_code}")
        if resp.status_code == 200:
            print("SUCCESS - Agent will work!")
            print("Response:", resp.json()["choices"][0]["message"]["content"])
        elif resp.status_code == 429:
            print("STILL rate limited - provider key not attached correctly")
            print(resp.text[:300])
        elif resp.status_code == 401:
            print("INVALID KEY - copy the key from OpenRouter again")
        else:
            print("Error:", resp.text[:300])
else:
    print("\nFix: Open elysium/backend/.env and make sure it contains:")
    print("OPENROUTER_API_KEY=sk-or-v1-your-actual-key-here")
    print("(no quotes, no spaces around =)")