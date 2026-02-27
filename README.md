# 🤖 Teams CI/CD DeployBot

A Microsoft Teams bot built in Python that lets your team **trigger Jenkins builds** and **deploy via Octopus Cloud** using simple chat commands — with approval gates for UAT and Production.

---

## 📁 Project Structure

```
teams-cicd-bot/
│
├── app.py                  ← Main entry point (aiohttp web server)
├── requirements.txt
├── Dockerfile
├── .env.example            ← Copy to .env and fill in your values
│
├── config/
│   └── settings.py         ← All environment config in one place
│
├── bot/
│   ├── deploy_bot.py       ← Core bot logic, command routing
│   ├── command_parser.py   ← Parses Teams messages into commands
│   └── cards.py            ← Adaptive Card builders
│
├── jenkins/
│   └── client.py           ← Trigger builds via Jenkins REST API
│
├── octopus/
│   └── client.py           ← Deploy via Octopus Cloud REST API
│
├── approval/
│   └── manager.py          ← UAT/Prod approval flow + timeout
│
└── audit/
    └── logger.py           ← SQLite audit log of all actions
```

---

## 🚀 Step-by-Step Setup

### Step 1 — Prerequisites

- Python 3.11+
- A Microsoft Azure account
- Jenkins server with API access
- Octopus Cloud account (octopus.app)
- Microsoft Teams (admin access to add an app)

---

### Step 2 — Clone & Install

```bash
git clone <your-repo>
cd teams-cicd-bot

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

---

### Step 3 — Register a Bot in Azure

1. Go to [portal.azure.com](https://portal.azure.com)
2. Search → **Azure Bot** → Create
3. Choose **Multi-tenant** for Teams
4. Note the **App ID** and generate a **Client Secret** (this is your App Password)
5. Under **Channels** → Add **Microsoft Teams**
6. Under **Configuration** → set Messaging endpoint to:
   `https://your-app.azurewebsites.net/api/messages`

---

### Step 4 — Configure Environment

```bash
cp .env.example .env
```

Fill in `.env`:

```
MicrosoftAppId=<from Azure Bot>
MicrosoftAppPassword=<client secret from Azure>

JENKINS_URL=https://jenkins.yourcompany.com
JENKINS_USER=your-username
JENKINS_TOKEN=your-api-token
JENKINS_BUILD_JOB=your-build-job-name
JENKINS_DEPLOY_JOB=your-deploy-job-name

OCTOPUS_URL=https://yourcompany.octopus.app
OCTOPUS_API_KEY=API-XXXXXXXXXXXXXXXXXXXX
OCTOPUS_SPACE_ID=Spaces-1

BOT_CALLBACK_URL=https://your-app.azurewebsites.net/api/callback
```

---

### Step 5 — Jenkins Setup

In your Jenkins job, add these **parameters**:
- `APP_NAME` (String)
- `BRANCH` (String)
- `CALLBACK_URL` (String)

Add this to the end of your Jenkinsfile to notify the bot:

```groovy
post {
    always {
        script {
            def status = currentBuild.result ?: 'SUCCESS'
            sh """
                curl -X POST ${CALLBACK_URL} \
                  -H 'Content-Type: application/json' \
                  -d '{"app":"${APP_NAME}","build_number":${BUILD_NUMBER},"status":"${status}","url":"${BUILD_URL}"}'
            """
        }
    }
}
```

---

### Step 6 — Octopus Cloud Setup

1. In Octopus → **Configuration** → **API Keys** → New API Key → copy it to `.env`
2. Make sure each app has a **Project** in Octopus with the **same name** as you use in the bot command
3. Environments must be named exactly: **QA**, **UAT**, **Production**
4. Release versions in Octopus should contain the Jenkins build number (e.g. `1.0.42`)

---

### Step 7 — Run Locally (for testing)

```bash
# Use ngrok to expose local port to Teams during development
ngrok http 3978

# Copy the ngrok HTTPS URL and set it as your bot's messaging endpoint in Azure:
# https://xxxx.ngrok.io/api/messages

# Run the bot
python app.py
```

---

### Step 8 — Deploy to Azure App Service

```bash
# Build and push Docker image
docker build -t deploybot .
docker tag deploybot <your-acr>.azurecr.io/deploybot:latest
docker push <your-acr>.azurecr.io/deploybot:latest

# In Azure Portal → App Service → Create → Docker Container
# Point to your ACR image
# Add all .env values as Application Settings
```

---

### Step 9 — Add Bot to Teams

1. In Azure Bot → **Channels** → Teams → Download app manifest
2. Or create a `manifest.json` manually with your Bot App ID
3. In Teams → **Apps** → **Upload a custom app** → upload the manifest zip
4. Add the bot to your deployment channel

---

## 💬 Bot Commands

| Command | Description |
|---------|-------------|
| `build myapp main` | Trigger a Jenkins build from branch `main` |
| `build myapp feature/xyz` | Build from a feature branch |
| `deploy myapp 42 qa` | Deploy build #42 to QA (auto, no approval) |
| `deploy myapp 42 uat` | Deploy to UAT (requires approval) |
| `deploy myapp 42 prod` | Deploy to Production (requires approval) |
| `status myapp` | Check deployment status across all environments |
| `rollback myapp prod` | Roll back Production to the previous release |
| `history myapp` | Show last 10 actions for this app |
| `help` | Show all commands |

---

## 🔐 Approval Flow

- **QA** → Deploys immediately, no approval needed
- **UAT** → Bot sends an ✅/❌ card to the channel. A Team Lead clicks to approve
- **Prod** → Same as UAT. Approvals expire after 30 minutes (configurable)

---

## 📋 Audit Log

Every command is logged to `audit.db` (SQLite). Use `history <app>` to query via Teams, or connect directly with any SQLite browser.
