"""
bot/deploy_bot.py
Core Teams bot — receives messages, routes commands, sends replies.
"""
from botbuilder.core import ActivityHandler, TurnContext, MessageFactory
from botbuilder.schema import Activity, ActivityTypes

from bot.command_parser import parse_command
from bot.cards import (
    build_triggered_card,
    deploy_triggered_card,
    approval_request_card,
    status_card,
    error_card,
    help_card,
)
from jenkins_client.client import JenkinsClient
from octopus_client.client import OctopusClient
from approval.manager import ApprovalManager
from audit.logger import AuditLogger
from config.settings import settings


class DeployBot(ActivityHandler):

    def __init__(self):
        # Lazy-loaded — clients are only created when first command is used.
        # This lets the bot server start cleanly even if .env is not yet filled in.
        self._jenkins = None
        self._octopus = None
        self.approvals = ApprovalManager()
        self.audit = AuditLogger()

    @property
    def jenkins(self) -> JenkinsClient:
        if self._jenkins is None:
            self._jenkins = JenkinsClient()
        return self._jenkins

    @property
    def octopus(self) -> OctopusClient:
        if self._octopus is None:
            self._octopus = OctopusClient()
        return self._octopus

    # ─────────────────────────────────────────────────────────────
    # Entry point — called on every incoming Teams message
    # ─────────────────────────────────────────────────────────────
    async def on_message_activity(self, turn_context: TurnContext):
        text = turn_context.activity.text or ""
        user = turn_context.activity.from_property.name or "unknown"
        user_id = turn_context.activity.from_property.id or ""

        cmd = parse_command(text)

        if cmd.error:
            await turn_context.send_activity(
                MessageFactory.attachment(error_card(cmd.error))
            )
            return

        if cmd.action == "help":
            await turn_context.send_activity(MessageFactory.attachment(help_card()))
        elif cmd.action == "build":
            await self._handle_build(turn_context, cmd, user)
        elif cmd.action == "deploy":
            await self._handle_deploy(turn_context, cmd, user, user_id)
        elif cmd.action == "status":
            await self._handle_status(turn_context, cmd, user)
        elif cmd.action == "rollback":
            await self._handle_rollback(turn_context, cmd, user)
        elif cmd.action == "history":
            await self._handle_history(turn_context, cmd)
        else:
            await turn_context.send_activity(
                MessageFactory.attachment(error_card("Unknown command. Type `help` to see available commands."))
            )

    async def on_invoke_activity(self, turn_context: TurnContext):
        value = turn_context.activity.value or {}
        action = value.get("action")
        approval_id = value.get("approval_id")
        approver = turn_context.activity.from_property.name
        if action in ("approve", "reject") and approval_id:
            await self.approvals.handle_response(
                approval_id=approval_id,
                approved=(action == "approve"),
                approver=approver,
                turn_context=turn_context,
            )

    async def _handle_build(self, turn_context, cmd, user):
        await turn_context.send_activity(
            MessageFactory.attachment(build_triggered_card(app=cmd.app, branch=cmd.branch, user=user))
        )
        result = await self.jenkins.trigger_build(app=cmd.app, branch=cmd.branch)
        await self.audit.log(user=user, action="build", app=cmd.app,
                             details={"branch": cmd.branch}, result=result)

    async def _handle_deploy(self, turn_context, cmd, user, user_id):
        env = cmd.environment
        if env not in settings.APPROVAL_REQUIRED_ENVS:
            await turn_context.send_activity(
                MessageFactory.attachment(deploy_triggered_card(app=cmd.app, build=cmd.build_number, env=env, user=user))
            )
            result = await self.octopus.deploy(app=cmd.app, build_number=cmd.build_number, environment=env)
            await self.audit.log(user=user, action="deploy", app=cmd.app,
                                 details={"build": cmd.build_number, "env": env}, result=result)
            return
        approval_id = await self.approvals.create(
            app=cmd.app, build_number=cmd.build_number, environment=env,
            requested_by=user, turn_context=turn_context,
        )
        await turn_context.send_activity(
            MessageFactory.attachment(approval_request_card(
                approval_id=approval_id, app=cmd.app, build=cmd.build_number,
                env=env, requested_by=user,
            ))
        )

    async def _handle_status(self, turn_context, cmd, user):
        status_data = await self.octopus.get_status(app=cmd.app)
        await turn_context.send_activity(
            MessageFactory.attachment(status_card(app=cmd.app, data=status_data))
        )

    async def _handle_rollback(self, turn_context, cmd, user):
        approval_id = await self.approvals.create(
            app=cmd.app, build_number="previous", environment=cmd.environment,
            requested_by=user, turn_context=turn_context, is_rollback=True,
        )
        await turn_context.send_activity(
            MessageFactory.attachment(approval_request_card(
                approval_id=approval_id, app=cmd.app, build="previous",
                env=cmd.environment, requested_by=user, is_rollback=True,
            ))
        )

    async def _handle_history(self, turn_context, cmd):
        records = await self.audit.get_history(app=cmd.app, limit=10)
        lines = [f"📋 **Last {len(records)} actions for `{cmd.app}`:**\n"]
        for r in records:
            lines.append(f"• `{r['action']}` by **{r['user']}** → {r['result']} _{r['timestamp']}_")
        await turn_context.send_activity(MessageFactory.text("\n".join(lines)))