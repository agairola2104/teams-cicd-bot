"""
jenkins/client.py
Triggers Jenkins jobs via the Jenkins REST API.
Uses python-jenkins library for authentication + job control.
"""
import asyncio
import jenkins
from config.settings import settings


class JenkinsClient:

    def __init__(self):
        self._server = jenkins.Jenkins(
            url=settings.JENKINS_URL,
            username=settings.JENKINS_USER,
            password=settings.JENKINS_TOKEN,
        )

    async def trigger_build(self, app: str, branch: str) -> dict:
        """
        Trigger the Jenkins build job for the given app and branch.
        Returns a dict with job name, queue item number, and status.
        """
        params = {
            "APP_NAME": app,
            "BRANCH": branch,
            "CALLBACK_URL": settings.BOT_CALLBACK_URL,   # Jenkins notifies bot when done
        }
        try:
            queue_item = await asyncio.to_thread(
                self._server.build_job,
                settings.JENKINS_BUILD_JOB,
                parameters=params,
            )
            return {
                "status": "triggered",
                "job": settings.JENKINS_BUILD_JOB,
                "queue_item": queue_item,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_build_status(self, job_name: str, build_number: int) -> dict:
        """
        Poll the status of a specific Jenkins build.
        Returns building flag, result (SUCCESS/FAILURE/ABORTED), and duration.
        """
        try:
            info = await asyncio.to_thread(
                self._server.get_build_info, job_name, build_number
            )
            return {
                "building": info.get("building", False),
                "result": info.get("result"),         # None if still running
                "duration_ms": info.get("duration", 0),
                "url": info.get("url", ""),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_last_successful_build(self, app: str) -> dict:
        """
        Fetch the last successful build number for an app's build job.
        Useful for quick re-deploys.
        """
        try:
            info = await asyncio.to_thread(
                self._server.get_job_info, settings.JENKINS_BUILD_JOB
            )
            last_ok = info.get("lastSuccessfulBuild") or {}
            return {
                "build_number": last_ok.get("number"),
                "url": last_ok.get("url", ""),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
