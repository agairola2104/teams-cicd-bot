"""
approval/manager.py
Manages pending deployment approvals.

Flow:
  1. Bot calls `create()` → stores pending approval, returns unique ID
  2. Approver clicks ✅/❌ on the Adaptive Card in Teams
  3. Bot calls `handle_response()` → executes or cancels the deployment
  4. Pending approvals expire after APPROVAL_TIMEOUT_MINUTES
"""
import uuid
import asyncio
from datetime import datetime, timedelta
from botbuilder.core import TurnContext, MessageFactory

from config.settings import settings
from bot.cards import deploy_triggered_card, error_card


class PendingApproval:
    def __init__(self, app, build_number, environment, requested_by,
                 turn_context, is_rollback=False):
        self.id = str(uuid.uuid4())
        self.app = app
        self.build_number = build_number
        self.environment = environment
        self.requested_by = requested_by
        self.turn_context = turn_context   # Saved to reply in same channel
        self.is_rollback = is_rollback
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(
            minutes=settings.APPROVAL_TIMEOUT_MINUTES
        )


class ApprovalManager:

    def __init__(self):
        # In-memory store: approval_id → PendingApproval
        # For production, replace with Redis or a database
        self._pending: dict[str, PendingApproval] = {}

    async def create(
        self,
        app: str,
        build_number: str,
        environment: str,
        requested_by: str,
        turn_context: TurnContext,
        is_rollback: bool = False,
    ) -> str:
        """
        Register a pending approval and schedule auto-expiry.
        Returns the approval_id to embed in the Adaptive Card.
        """
        approval = PendingApproval(
            app=app,
            build_number=build_number,
            environment=environment,
            requested_by=requested_by,
            turn_context=turn_context,
            is_rollback=is_rollback,
        )
        self._pending[approval.id] = approval

        # Auto-expire after timeout
        asyncio.create_task(self._expire(approval.id))
        return approval.id

    async def handle_response(
        self,
        approval_id: str,
        approved: bool,
        approver: str,
        turn_context: TurnContext,
    ):
        """
        Called when an approver clicks ✅ or ❌ on the Adaptive Card.
        """
        approval = self._pending.pop(approval_id, None)

        if approval is None:
            await turn_context.send_activity(
                MessageFactory.text("⚠️ This approval request has already been handled or expired.")
            )
            return

        if not approved:
            await turn_context.send_activity(
                MessageFactory.text(
                    f"❌ **{approver}** rejected the deployment of "
                    f"`{approval.app}` build **#{approval.build_number}** to **{approval.environment.upper()}**."
                )
            )
            return

        # Approved — execute the deployment
        await turn_context.send_activity(
            MessageFactory.text(
                f"✅ **{approver}** approved! Deploying `{approval.app}` "
                f"build **#{approval.build_number}** to **{approval.environment.upper()}**..."
            )
        )

        # Import here to avoid circular import
        from octopus.client import OctopusClient
        from audit.logger import AuditLogger

        octopus = OctopusClient()
        audit = AuditLogger()

        if approval.is_rollback:
            result = await octopus.rollback(
                app=approval.app,
                environment=approval.environment,
            )
            action = "rollback"
        else:
            result = await octopus.deploy(
                app=approval.app,
                build_number=approval.build_number,
                environment=approval.environment,
            )
            action = "deploy"

        await audit.log(
            user=approver,
            action=f"{action}_approved",
            app=approval.app,
            details={"env": approval.environment, "build": approval.build_number,
                     "approved_by": approver},
            result=result,
        )

        status = result.get("status", "unknown")
        if status == "triggered":
            link = result.get("url", "")
            await turn_context.send_activity(
                MessageFactory.text(
                    f"🚀 Deployment triggered in Octopus! {link}"
                )
            )
        else:
            await turn_context.send_activity(
                MessageFactory.attachment(
                    error_card(f"Deployment failed: {result.get('message', 'Unknown error')}")
                )
            )

    async def _expire(self, approval_id: str):
        """Wait for the timeout period, then remove if still pending."""
        await asyncio.sleep(settings.APPROVAL_TIMEOUT_MINUTES * 60)
        approval = self._pending.pop(approval_id, None)
        if approval:
            # Notify the channel that the request expired
            try:
                await approval.turn_context.send_activity(
                    MessageFactory.text(
                        f"⏱️ Approval request for `{approval.app}` to "
                        f"**{approval.environment.upper()}** has expired."
                    )
                )
            except Exception:
                pass  # Channel may no longer be reachable
