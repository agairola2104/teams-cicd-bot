"""
config/settings.py
Loads all environment variables into a single typed config object.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Bot
    APP_ID: str = os.getenv("MicrosoftAppId", "")
    APP_PASSWORD: str = os.getenv("MicrosoftAppPassword", "")

    # Jenkins
    JENKINS_URL: str = os.getenv("JENKINS_URL", "")
    JENKINS_USER: str = os.getenv("JENKINS_USER", "")
    JENKINS_TOKEN: str = os.getenv("JENKINS_TOKEN", "")
    JENKINS_BUILD_JOB: str = os.getenv("JENKINS_BUILD_JOB", "build-pipeline")
    JENKINS_DEPLOY_JOB: str = os.getenv("JENKINS_DEPLOY_JOB", "deploy-pipeline")

    # Octopus
    OCTOPUS_URL: str = os.getenv("OCTOPUS_URL", "")
    OCTOPUS_API_KEY: str = os.getenv("OCTOPUS_API_KEY", "")
    OCTOPUS_SPACE_ID: str = os.getenv("OCTOPUS_SPACE_ID", "Spaces-1")

    # Approval
    APPROVAL_TIMEOUT_MINUTES: int = int(os.getenv("APPROVAL_TIMEOUT_MINUTES", "30"))

    # Callback
    BOT_CALLBACK_URL: str = os.getenv("BOT_CALLBACK_URL", "")

    # Environments that require manual approval before deploying
    APPROVAL_REQUIRED_ENVS: list = ["uat", "prod"]

    # Valid deployment targets
    VALID_ENVIRONMENTS: list = ["qa", "uat", "prod"]


settings = Settings()
