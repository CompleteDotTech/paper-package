"""
Test TypeSafe Jev API directly to debug request format.
"""

import json
import urllib.request
import urllib.error

def test_jev_api(api_key: str):
    """Test the API with different request formats."""

    # TypeSafe API endpoints to try
    endpoints = [
        "https://api.typesafe.ai/v1/systemone",
        "https://api.typesafe.ai/v1/decisions",
        "https://api.typesafe.ai/systemone",
    ]

    # Test request formats
    test_payloads = [
        {
            "state": "Test state",
            "questions": [{
                "type": "noul",
                "prompt": "Is this a test?"
            }]
        },
        {
            "context": "Test state",
            "questions": [{
                "type": "noul",
                "prompt": "Is this a test?"
            }]
        },
    ]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    for endpoint in endpoints:
        print(f"\nTesting endpoint: {endpoint}")

        for i, payload in enumerate(test_payloads):
            print(f"  Format {i+1}:", list(payload.keys()))

            try:
                body = json.dumps(payload).encode('utf-8')
                req = urllib.request.Request(
                    endpoint,
                    data=body,
                    headers=headers,
                    method="POST"
                )

                with urllib.request.urlopen(req, timeout=10) as response:
                    print(f"    ✓ Success! Status: {response.status}")
                    data = response.read().decode('utf-8')
                    result = json.loads(data)
                    print(f"    Response keys: {list(result.keys())}")
                    return True

            except urllib.error.HTTPError as e:
                print(f"    ✗ HTTP {e.code}: {e.reason}")
                try:
                    error_data = e.read().decode('utf-8')
                    print(f"    Error details: {error_data[:200]}")
                except:
                    pass

            except urllib.error.URLError as e:
                print(f"    ✗ Connection error: {e.reason}")
            except Exception as e:
                print(f"    ✗ Error: {e}")

    print("\n⚠ Could not reach TypeSafe API. Check:")
    print("  1. API key is correct")
    print("  2. Internet connection is available")
    print("  3. TypeSafe API is online at https://console.typesafe.ai")

if __name__ == "__main__":
    import sys
    import os

    api_key = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TYPESAFE_API_KEY")

    if not api_key:
        print("Error: No API key provided")
        print("Usage: python3 test_jev_api.py <api_key>")
        sys.exit(1)

    test_jev_api(api_key)
