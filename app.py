"""
app.py
Main entry point — aiohttp web server that:
  - Receives Teams messages at POST /api/messages
  - Receives Jenkins build callbacks at POST /api/callback
  - Health check at GET /health
"""
from aiohttp import web
from botbuilder.core import BotFrameworkAdapterSettings, BotFrameworkAdapter
from botbuilder.schema import Activity

from bot.deploy_bot import DeployBot
from config.settings import settings

# ── Bot Framework adapter ────────────────────────────────────
adapter_settings = BotFrameworkAdapterSettings(
    app_id=settings.APP_ID,
    app_password=settings.APP_PASSWORD,
)
adapter = BotFrameworkAdapter(adapter_settings)
bot = DeployBot()


async def on_error(context, error):
    """Global error handler — logs to console and replies to user."""
    print(f"[ERROR] Unhandled exception: {error}")
    await context.send_activity("❌ Something went wrong. Please try again.")


adapter.on_turn_error = on_error


# ── Route handlers ────────────────────────────────────────────
async def messages(req: web.Request) -> web.Response:
    """
    POST /api/messages
    Main Teams webhook endpoint. All messages from Teams arrive here.
    """
    if "application/json" not in req.content_type:
        return web.Response(status=415, text="Unsupported Media Type")

    body = await req.json()
    activity = Activity().deserialize(body)
    auth_header = req.headers.get("Authorization", "")

    response = await adapter.process_activity(activity, auth_header, bot.on_turn)
    if response:
        return web.json_response(data=response.body, status=response.status)
    return web.Response(status=201)


async def jenkins_callback(req: web.Request) -> web.Response:
    """
    POST /api/callback
    Jenkins notifies us here when a build finishes.
    Body: { "app": "myapp", "build_number": 42, "status": "SUCCESS"|"FAILURE", "url": "..." }
    """
    body = await req.json()
    app = body.get("app", "unknown")
    build_number = body.get("build_number", "?")
    status = body.get("status", "UNKNOWN")
    url = body.get("url", "")

    emoji = "✅" if status == "SUCCESS" else "❌"
    print(f"[CALLBACK] Build {build_number} for {app}: {status}")

    # In a real implementation, use a conversation reference saved during
    # the original command to proactively message the Teams channel here.
    # See: https://learn.microsoft.com/en-us/azure/bot-service/bot-builder-howto-proactive-message

    return web.json_response({"received": True})


async def health(req: web.Request) -> web.Response:
    """GET /health — Azure App Service health probe."""
    return web.json_response({"status": "ok", "bot": "DeployBot"})


# ── App factory ───────────────────────────────────────────────
def create_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/api/messages", messages)
    app.router.add_post("/api/callback", jenkins_callback)
    app.router.add_get("/health", health)
    return app


if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=3978)
    print("🤖 DeployBot running on http://localhost:3978")
