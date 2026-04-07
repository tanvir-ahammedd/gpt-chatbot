import httpx
import json
import time  # add this

url = "http://localhost:8000/chat/stream"

print("Sending streaming request to /chat/stream...\n")

with httpx.stream("POST", url, json={"session_id": "stream-test-1", "message": "what is deep learning?"}) as response:
    if response.status_code != 200:
        print(f"Failed: {response.status_code} {response.text}")
    else:
        for line in response.iter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                
                if data.get("done"):
                    print("\n\n[Stream finished]")
                    break

                print(data.get("content", ""), end="", flush=True)
                
                time.sleep(0.07)