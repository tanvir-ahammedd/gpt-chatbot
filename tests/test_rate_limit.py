import httpx

BASE_URL = "http://localhost:8000"
TOTAL_REQUESTS = 15  # exceed limit

log_file = open("test_api.log", "w", encoding="utf-8")

def log(message):
    print(message)              # print to terminal
    log_file.write(message + "\n")  # write to file

log("Rate Limit Test (RATE_LIMIT_RPM=5)\n")
log(f"Sending {TOTAL_REQUESTS} rapid requests to POST /chat...\n")

for i in range(1, TOTAL_REQUESTS + 1):
    try:
        response = httpx.post(
            f"{BASE_URL}/chat",
            json={"session_id": "rate-limit-test", "message": f"Hello #{i}"},
            timeout=15,
        )

        status = response.status_code

        if status == 200:
            reply = response.json().get("response", "")[:60]
            log(f"Request {i:2d}: [OK ] {status} -> \"{reply}...\"")

        elif status == 429:
            log(f"Request {i:2d}: [429] TOO MANY REQUESTS <-- Rate limit hit!")

        else:
            log(f"Request {i:2d}: [???] {status} -> {response.text[:80]}")

    except httpx.ConnectError:
        log(f"Request {i:2d}: [ERR] Connection refused -- is server running?")
        break
    except Exception as e:
        log(f"Request {i:2d}: [ERR] {e}")

log("\nTest complete.")

log_file.close()