"""
octopus/client.py
Interacts with Octopus Cloud (octopus.app) via the Octopus REST API.

Key operations:
  - Create a deployment (trigger release to an environment)
  - Get deployment status per environment
  - Trigger rollback (re-deploy previous release)

Octopus REST API docs: https://octopus.com/docs/octopus-rest-api
"""
import asyncio
import aiohttp
from config.settings import settings


class OctopusClient:

    def __init__(self):
        self.base_url = f"{settings.OCTOPUS_URL.rstrip('/')}/api/{settings.OCTOPUS_SPACE_ID}"
        self.headers = {
            "X-Octopus-ApiKey": settings.OCTOPUS_API_KEY,
            "Content-Type": "application/json",
        }

    # ─────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────
    async def _get(self, path: str) -> dict:
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(f"{self.base_url}{path}") as resp:
                resp.raise_for_status()
                return await resp.json()

    async def _post(self, path: str, payload: dict) -> dict:
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.post(f"{self.base_url}{path}", json=payload) as resp:
                resp.raise_for_status()
                return await resp.json()

    # ─────────────────────────────────────────────────────────────
    # Resolve Octopus IDs from names
    # ─────────────────────────────────────────────────────────────
    async def _get_project_id(self, app: str) -> str:
        """
        Finds the Octopus project whose Name matches the app name.
        Raises ValueError if not found.
        """
        data = await self._get(f"/projects?name={app}&take=1")
        items = data.get("Items", [])
        if not items:
            raise ValueError(f"No Octopus project found for app `{app}`. "
                             f"Make sure the project name in Octopus matches exactly.")
        return items[0]["Id"]

    async def _get_environment_id(self, environment: str) -> str:
        """
        Finds the Octopus environment ID by name (case-insensitive match on qa/uat/prod).
        """
        ENV_NAME_MAP = {"qa": "QA", "uat": "UAT", "prod": "Production"}
        env_name = ENV_NAME_MAP.get(environment.lower(), environment)
        data = await self._get(f"/environments?name={env_name}&take=1")
        items = data.get("Items", [])
        if not items:
            raise ValueError(f"No Octopus environment found for `{environment}`. "
                             f"Expected environment named `{env_name}` in Octopus.")
        return items[0]["Id"]

    async def _get_release_id(self, project_id: str, build_number: str) -> str:
        """
        Finds the Octopus release matching the Jenkins build number.
        Convention: Octopus release version = build number (e.g. "42" or "1.0.42").
        """
        data = await self._get(f"/projects/{project_id}/releases?take=100")
        for release in data.get("Items", []):
            # Match if version contains the build number
            if str(build_number) in release.get("Version", ""):
                return release["Id"]
        raise ValueError(
            f"No Octopus release found containing build number `{build_number}`. "
            f"Ensure Jenkins publishes a release to Octopus with version containing the build number."
        )

    # ─────────────────────────────────────────────────────────────
    # Deploy
    # ─────────────────────────────────────────────────────────────
    async def deploy(self, app: str, build_number: str, environment: str) -> dict:
        """
        Creates an Octopus deployment for the given app, build, and environment.
        This triggers the full Octopus deployment process.
        """
        try:
            project_id = await self._get_project_id(app)
            environment_id = await self._get_environment_id(environment)
            release_id = await self._get_release_id(project_id, build_number)

            payload = {
                "ReleaseId": release_id,
                "EnvironmentId": environment_id,
                "Comments": f"Triggered via Teams bot — build #{build_number}",
            }
            result = await self._post("/deployments", payload)
            return {
                "status": "triggered",
                "deployment_id": result.get("Id"),
                "url": f"{settings.OCTOPUS_URL}/app#/{settings.OCTOPUS_SPACE_ID}/deployments/{result.get('Id')}",
            }
        except ValueError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": f"Octopus API error: {str(e)}"}

    # ─────────────────────────────────────────────────────────────
    # Status
    # ─────────────────────────────────────────────────────────────
    async def get_status(self, app: str) -> dict:
        """
        Returns the latest deployment state for each environment (QA, UAT, Prod).
        """
        try:
            project_id = await self._get_project_id(app)
            data = await self._get(
                f"/deployments?projects={project_id}&take=50"
            )
            # Summarise latest deployment per environment
            env_status = {}
            for d in data.get("Items", []):
                env_name = d.get("EnvironmentId", "unknown")
                if env_name not in env_status:
                    env_status[env_name] = {
                        "release": d.get("ReleaseId", "?"),
                        "state": d.get("State", "Unknown"),
                        "created": d.get("Created", ""),
                    }
            return env_status if env_status else {}
        except Exception as e:
            return {"error": str(e)}

    # ─────────────────────────────────────────────────────────────
    # Rollback — re-deploy the previous release
    # ─────────────────────────────────────────────────────────────
    async def rollback(self, app: str, environment: str) -> dict:
        """
        Finds the second-latest release for the project and redeploys it.
        """
        try:
            project_id = await self._get_project_id(app)
            environment_id = await self._get_environment_id(environment)

            releases = await self._get(
                f"/projects/{project_id}/releases?take=2"
            )
            items = releases.get("Items", [])
            if len(items) < 2:
                return {"status": "error",
                        "message": "No previous release found to roll back to."}

            previous_release = items[1]  # [0] = latest, [1] = previous
            payload = {
                "ReleaseId": previous_release["Id"],
                "EnvironmentId": environment_id,
                "Comments": f"Rollback via Teams bot — reverting to {previous_release['Version']}",
            }
            result = await self._post("/deployments", payload)
            return {
                "status": "triggered",
                "rollback_to": previous_release["Version"],
                "deployment_id": result.get("Id"),
            }
        except ValueError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": f"Rollback error: {str(e)}"}