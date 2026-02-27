"""
bot/cards.py
Adaptive Card builders for all bot responses.
All cards return a botbuilder Attachment ready to send.
"""
from botbuilder.schema import Attachment
import json


def _make_card(body: list, actions: list = None) -> Attachment:
    card = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": body,
    }
    if actions:
        card["actions"] = actions
    return Attachment(
        content_type="application/vnd.microsoft.card.adaptive",
        content=card,
    )


# ── Color helpers ─────────────────────────────────────────────
ENV_COLORS = {"qa": "Good", "uat": "Warning", "prod": "Attention"}


# ─────────────────────────────────────────────────────────────
# Help Card
# ─────────────────────────────────────────────────────────────
def help_card() -> Attachment:
    return _make_card([
        {"type": "TextBlock", "text": "🤖 DeployBot Commands", "weight": "Bolder", "size": "Large"},
        {"type": "TextBlock", "text": "Here's what I can do:", "wrap": True, "spacing": "Small"},
        {
            "type": "FactSet",
            "facts": [
                {"title": "build <app> <branch>",              "value": "Trigger a Jenkins build"},
                {"title": "deploy <app> <build#> <env>",       "value": "Deploy to qa / uat / prod"},
                {"title": "status <app>",                      "value": "Check deployment status in Octopus"},
                {"title": "rollback <app> <env>",              "value": "Roll back to the previous release"},
                {"title": "history <app>",                     "value": "Show last 10 actions for an app"},
            ]
        },
        {
            "type": "TextBlock",
            "text": "💡 UAT and Prod deployments require approval from a Team Lead.",
            "wrap": True, "isSubtle": True, "spacing": "Medium"
        }
    ])


# ─────────────────────────────────────────────────────────────
# Build Triggered Card
# ─────────────────────────────────────────────────────────────
def build_triggered_card(app: str, branch: str, user: str) -> Attachment:
    return _make_card([
        {"type": "TextBlock", "text": "🔨 Build Triggered", "weight": "Bolder", "size": "Medium", "color": "Good"},
        {
            "type": "FactSet",
            "facts": [
                {"title": "App",       "value": app},
                {"title": "Branch",    "value": branch},
                {"title": "Triggered by", "value": user},
                {"title": "Status",    "value": "⏳ Running in Jenkins..."},
            ]
        },
        {
            "type": "TextBlock",
            "text": "I'll update you here when the build completes.",
            "wrap": True, "isSubtle": True
        }
    ])


# ─────────────────────────────────────────────────────────────
# Deploy Triggered Card (QA — no approval needed)
# ─────────────────────────────────────────────────────────────
def deploy_triggered_card(app: str, build: str, env: str, user: str) -> Attachment:
    color = ENV_COLORS.get(env, "Default")
    return _make_card([
        {"type": "TextBlock", "text": f"🚀 Deploying to {env.upper()}", "weight": "Bolder", "size": "Medium", "color": color},
        {
            "type": "FactSet",
            "facts": [
                {"title": "App",          "value": app},
                {"title": "Build",        "value": f"#{build}"},
                {"title": "Environment",  "value": env.upper()},
                {"title": "Triggered by", "value": user},
                {"title": "Status",       "value": "⏳ Deploying via Octopus..."},
            ]
        }
    ])


# ─────────────────────────────────────────────────────────────
# Approval Request Card (UAT / Prod)
# ─────────────────────────────────────────────────────────────
def approval_request_card(
    approval_id: str,
    app: str,
    build: str,
    env: str,
    requested_by: str,
    is_rollback: bool = False,
) -> Attachment:
    action_label = "Rollback" if is_rollback else "Deployment"
    color = ENV_COLORS.get(env, "Warning")
    return _make_card(
        body=[
            {"type": "TextBlock", "text": f"⚠️ {action_label} Approval Required",
             "weight": "Bolder", "size": "Large", "color": color},
            {"type": "TextBlock",
             "text": f"**{requested_by}** wants to deploy `{app}` build **#{build}** to **{env.upper()}**.",
             "wrap": True},
            {
                "type": "FactSet",
                "facts": [
                    {"title": "App",         "value": app},
                    {"title": "Build",       "value": f"#{build}"},
                    {"title": "Environment", "value": env.upper()},
                    {"title": "Requested by","value": requested_by},
                    {"title": "Action",      "value": action_label},
                ]
            },
            {"type": "TextBlock",
             "text": "⏱️ This request will expire in 30 minutes.",
             "wrap": True, "isSubtle": True}
        ],
        actions=[
            {
                "type": "Action.Submit",
                "title": "✅ Approve",
                "style": "positive",
                "data": {"action": "approve", "approval_id": approval_id}
            },
            {
                "type": "Action.Submit",
                "title": "❌ Reject",
                "style": "destructive",
                "data": {"action": "reject", "approval_id": approval_id}
            }
        ]
    )


# ─────────────────────────────────────────────────────────────
# Status Card
# ─────────────────────────────────────────────────────────────
def status_card(app: str, data: dict) -> Attachment:
    facts = []
    for env, info in data.items():
        facts.append({
            "title": env.upper(),
            "value": f"Release {info.get('release', 'N/A')} — {info.get('state', 'Unknown')}"
        })
    return _make_card([
        {"type": "TextBlock", "text": f"📊 Status: {app}", "weight": "Bolder", "size": "Medium"},
        {"type": "FactSet", "facts": facts} if facts else
        {"type": "TextBlock", "text": "No deployments found for this app.", "isSubtle": True}
    ])


# ─────────────────────────────────────────────────────────────
# Error Card
# ─────────────────────────────────────────────────────────────
def error_card(message: str) -> Attachment:
    return _make_card([
        {"type": "TextBlock", "text": "❌ Error", "weight": "Bolder", "color": "Attention"},
        {"type": "TextBlock", "text": message, "wrap": True},
        {"type": "TextBlock", "text": "Type `help` to see all available commands.",
         "wrap": True, "isSubtle": True}
    ])
