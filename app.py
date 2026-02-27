"""
app.py - Main entry point
"""
import os
from aiohttp import web
from botbuilder.core import BotFrameworkAdapterSettings, BotFrameworkAdapter
from botbuilder.schema import Activity

from bot.deploy_bot import DeployBot
from config.settings import settings

adapter_settings = BotFrameworkAdapterSettings(
    app_id=settings.APP_ID,
    app_password=settings.APP_PASSWORD,
)
adapter = BotFrameworkAdapter(adapter_settings)
bot = DeployBot()


async def on_error(context, error):
    print(f"[ERROR] {error}")
    await context.send_activity("Something went wrong. Please try again.")

adapter.on_turn_error = on_error


async def messages(req: web.Request) -> web.Response:
    if "application/json" not in req.content_type:
        return web.Response(status=415)
    body = await req.json()
    activity = Activity().deserialize(body)
    auth_header = req.headers.get("Authorization", "")
    response = await adapter.process_activity(activity, auth_header, bot.on_turn)
    if response:
        return web.json_response(data=response.body, status=response.status)
    return web.Response(status=201)


async def jenkins_callback(req: web.Request) -> web.Response:
    body = await req.json()
    print(f"[CALLBACK] Build {body.get('build_number')} for {body.get('app')}: {body.get('status')}")
    return web.json_response({"received": True})


async def health(req: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "bot": "DeployBot"})


def create_app() -> web.Application:
    application = web.Application()
    application.router.add_post("/api/messages", messages)
    application.router.add_post("/api/callback", jenkins_callback)
    application.router.add_get("/health", health)
    return application


if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 8000))
    print(f"DeployBot starting on port {PORT}")
    web.run_app(create_app(), host="0.0.0.0", port=PORT)

# Expose app instance for gunicorn
app = create_app()