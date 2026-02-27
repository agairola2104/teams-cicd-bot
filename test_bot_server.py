"""
test_bot_server.py
Sends fake HTTP requests to your running bot server to test
the /api/messages and /health endpoints — no Teams needed.

Run FIRST:   python app.py               (in one terminal)
Run SECOND:  python test_bot_server.py   (in another terminal)
"""
import sys
import io
import requests

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BOT_URL = "http://localhost:3978"

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


def test_health():
    print(f"\n{BOLD}{'='*55}")
    print("  HEALTH CHECK")
    print(f"{'='*55}{RESET}\n")
    try:
        r = requests.get(f"{BOT_URL}/health", timeout=5)
        if r.status_code == 200:
            print(f"  {GREEN}[OK] Bot server is running!{RESET}  {r.json()}\n")
            return True
        else:
            print(f"  {RED}[FAIL] Unexpected status: {r.status_code}{RESET}\n")
            return False
    except requests.exceptions.ConnectionError:
        print(f"  {RED}[FAIL] Cannot connect to bot server.")
        print(f"         Make sure 'python app.py' is running first!{RESET}\n")
        return False


def send_message(text: str):
    """Send a fake Teams message payload to the bot."""
    payload = {
        "type": "message",
        "id": "test-activity-id",
        "timestamp": "2024-01-01T00:00:00.000Z",
        "channelId": "msteams",
        "from":         {"id": "test-user-id", "name": "Test User"},
        "conversation": {"id": "test-conversation-id"},
        "recipient":    {"id": "bot-id", "name": "DeployBot"},
        "text": text,
        "serviceUrl": "https://smba.trafficmanager.net/teams/"
    }
    try:
        r = requests.post(
            f"{BOT_URL}/api/messages",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        return r.status_code, r.text
    except Exception as e:
        return None, str(e)


def test_messages():
    print(f"\n{BOLD}{'='*55}")
    print("  MESSAGE ENDPOINT TESTS")
    print(f"{'='*55}{RESET}")
    print(f"  {YELLOW}Note: 401 Unauthorized is EXPECTED here.")
    print(f"  It means the bot received the message correctly but")
    print(f"  rejected auth because MicrosoftAppId is not set.")
    print(f"  This is normal for local testing.{RESET}\n")

    commands = [
        "help",
        "build myapp main",
        "deploy myapp 42 qa",
        "deploy myapp 42 prod",
        "status myapp",
        "history myapp",
        "invalid command here",
    ]

    for cmd in commands:
        status_code, body = send_message(cmd)
        if status_code in (200, 201):
            indicator = f"{GREEN}[{status_code}]{RESET}"
        elif status_code == 401:
            indicator = f"{YELLOW}[401 - expected]{RESET}"
        elif status_code is None:
            indicator = f"{RED}[NO RESPONSE]{RESET}"
        else:
            indicator = f"{RED}[{status_code}]{RESET}"

        print(f"  {indicator}  \"{cmd}\"")

    print()


def test_jenkins_callback():
    print(f"\n{BOLD}{'='*55}")
    print("  JENKINS CALLBACK TEST")
    print(f"{'='*55}{RESET}\n")

    payload = {
        "app": "myapp",
        "build_number": 42,
        "status": "SUCCESS",
        "url": "https://jenkins.example.com/job/build-pipeline/42/"
    }
    try:
        r = requests.post(
            f"{BOT_URL}/api/callback",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if r.status_code == 200:
            print(f"  {GREEN}[OK] Callback endpoint working!{RESET}  {r.json()}\n")
        else:
            print(f"  {RED}[FAIL] Status: {r.status_code}  {r.text}{RESET}\n")
    except Exception as e:
        print(f"  {RED}[ERROR] {e}{RESET}\n")


if __name__ == "__main__":
    server_ok = test_health()
    if server_ok:
        test_messages()
        test_jenkins_callback()
        print(f"{BOLD}Done!")
        print(f"If you saw 401s above, that is normal for local testing.")
        print(f"To test with real Teams messages, see README for ngrok setup.{RESET}\n")
    else:
        print(f"{RED}Start the bot first with:  python app.py{RESET}\n")