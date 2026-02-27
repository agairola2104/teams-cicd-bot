"""
test_local.py
Run this to test command parsing and bot logic WITHOUT needing
Teams, Jenkins, or Octopus to be connected.

Usage:
    python test_local.py
"""
import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from bot.command_parser import parse_command

# ── Colours for terminal output ──────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


def run_parser_tests():
    print(f"\n{BOLD}{'='*55}")
    print("  COMMAND PARSER TESTS")
    print(f"{'='*55}{RESET}\n")

    tests = [
        # (input message,                        expected action,  should_have_error)
        ("build myapp main",                     "build",          False),
        ("build myapp feature/login",            "build",          False),
        ("build myapp",                          "build",          True),   # missing branch
        ("deploy myapp 42 qa",                   "deploy",         False),
        ("deploy myapp 42 uat",                  "deploy",         False),
        ("deploy myapp 42 prod",                 "deploy",         False),
        ("deploy myapp 42 staging",              "deploy",         True),   # invalid env
        ("deploy myapp 42",                      "deploy",         True),   # missing env
        ("status myapp",                         "status",         False),
        ("rollback myapp prod",                  "rollback",       False),
        ("history myapp",                        "history",        False),
        ("help",                                 "help",           False),
        ("unknown command",                      "unknown",        True),
        ("",                                     "help",           False),
        ("<at>DeployBot</at> build myapp main",  "build",          False),  # Teams @mention
    ]

    passed = 0
    failed = 0

    for message, expected_action, expect_error in tests:
        cmd = parse_command(message)
        action_ok = cmd.action == expected_action
        error_ok  = bool(cmd.error) == expect_error

        if action_ok and error_ok:
            status = f"{GREEN}[PASS]{RESET}"
            passed += 1
        else:
            status = f"{RED}[FAIL]{RESET}"
            failed += 1

        display_msg = message[:45] + "..." if len(message) > 45 else message
        print(f"  {status}  {YELLOW}\"{display_msg}\"{RESET}")

        if not action_ok:
            print(f"         action:  expected={expected_action!r}  got={cmd.action!r}")
        if not error_ok:
            print(f"         error:   expected={expect_error}  got={bool(cmd.error)}  ({cmd.error})")

        # Show parsed fields for passing commands
        if action_ok and not expect_error:
            fields = []
            if cmd.app:          fields.append(f"app={cmd.app}")
            if cmd.branch:       fields.append(f"branch={cmd.branch}")
            if cmd.build_number: fields.append(f"build={cmd.build_number}")
            if cmd.environment:  fields.append(f"env={cmd.environment}")
            if fields:
                print(f"         parsed:  {', '.join(fields)}")
        print()

    print(f"{BOLD}Results: {GREEN}{passed} passed{RESET}{BOLD}, {RED}{failed} failed{RESET}\n")
    return failed == 0


def run_settings_check():
    print(f"\n{BOLD}{'='*55}")
    print("  SETTINGS / .ENV CHECK")
    print(f"{'='*55}{RESET}\n")

    from config.settings import settings

    checks = [
        ("MicrosoftAppId",       settings.APP_ID,         "Bot Framework"),
        ("MicrosoftAppPassword", settings.APP_PASSWORD,    "Bot Framework"),
        ("JENKINS_URL",          settings.JENKINS_URL,     "Jenkins"),
        ("JENKINS_USER",         settings.JENKINS_USER,    "Jenkins"),
        ("JENKINS_TOKEN",        settings.JENKINS_TOKEN,   "Jenkins"),
        ("OCTOPUS_URL",          settings.OCTOPUS_URL,     "Octopus"),
        ("OCTOPUS_API_KEY",      settings.OCTOPUS_API_KEY, "Octopus"),
    ]

    all_set = True
    for key, value, group in checks:
        if value:
            print(f"  {GREEN}[SET] {RESET} {key:<30} ({group})")
        else:
            print(f"  {YELLOW}[MISSING] {key:<30} -- edit your .env file{RESET}")
            all_set = False

    print()
    if all_set:
        print(f"  {GREEN}All settings configured!{RESET}\n")
    else:
        print(f"  {YELLOW}Some settings are missing.")
        print(f"  The bot will start but commands needing Jenkins/Octopus")
        print(f"  will fail until you fill in .env{RESET}\n")


if __name__ == "__main__":
    parser_ok = run_parser_tests()
    run_settings_check()

    if parser_ok:
        print(f"{GREEN}{BOLD}[OK] All parser tests passed! Your bot logic is working.{RESET}")
        print(f"     Next step: run  python test_bot_server.py\n")
    else:
        print(f"{RED}{BOLD}[ERROR] Some tests failed. Check output above.{RESET}\n")