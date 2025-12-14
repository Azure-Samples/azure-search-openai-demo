# Taskade Enterprise API Integration Guide

## 🎯 Overview

This guide covers the integration of **Taskade Enterprise API** with the freelance platform automation system. Taskade provides a complete workspace for managing registration projects, tracking automation tasks, and deploying AI agents for intelligent workflow orchestration.

## 📋 Table of Contents

1. [What is Taskade?](#what-is-taskade)
2. [API Configuration](#api-configuration)
3. [Core Features](#core-features)
4. [Integration Architecture](#integration-architecture)
5. [Usage Examples](#usage-examples)
6. [Freelance Registration Workflow](#freelance-registration-workflow)
7. [AI Agent Integration](#ai-agent-integration)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

## What is Taskade?

Taskade is the **execution layer for ideas** - a platform where:
- **Projects → Databases**: Live, queryable databases powering your apps
- **Workflows → Automations**: Visual workflows that run themselves
- **AI Agents → Workforce**: Autonomous agents that plan, act, and iterate
- **Real-time → Everything**: Instant sync across all your tools

### Key Capabilities

| Feature | Description |
|---------|-------------|
| **Project Management** | Structured data with custom fields and real-time sync |
| **Task Automation** | Create, assign, and track tasks programmatically |
| **AI Agents** | Deploy custom AI assistants with persistent memory |
| **Workflow Engine** | Connect 100+ integrations with AI decision making |
| **Genesis Builder** | Generate apps from natural language prompts |

## API Configuration

### Enterprise API Key

Your Enterprise API key: `tskdp_NvhoURdQXa1eDDxnCWrZYtb7k4uU2ZkHEC`

**⚠️ Security**: Store this key securely in Azure Key Vault.

### Configuration Options

```python
from automation import TaskadeClient, TaskadeConfig

# Basic configuration
config = TaskadeConfig(
    api_key="tskdp_NvhoURdQXa1eDDxnCWrZYtb7k4uU2ZkHEC",
    base_url="https://www.taskade.com/api/v1",
    timeout=30,
    max_retries=3
)

# Azure Key Vault configuration (recommended)
config = TaskadeConfig(
    api_key="",  # Will be loaded from Key Vault
    use_key_vault=True,
    key_vault_url="https://your-vault.vault.azure.net",
    key_vault_secret_name="taskade-api-key"
)

# Create client
client = TaskadeClient(config)
```

### Environment Variables

Add to your `.env` file:

```bash
# Taskade Configuration
TASKADE_API_KEY=tskdp_NvhoURdQXa1eDDxnCWrZYtb7k4uU2ZkHEC
TASKADE_WORKSPACE_ID=your-workspace-id
TASKADE_FOLDER_ID=your-folder-id

# Optional: Azure Key Vault
AZURE_KEY_VAULT_URL=https://your-vault.vault.azure.net
TASKADE_KEY_VAULT_SECRET=taskade-api-key
```

## Core Features

### 1. Workspace Management

```python
async with TaskadeClient(config) as client:
    # Get all workspaces
    workspaces = await client.get_workspaces()

    for workspace in workspaces:
        print(f"Workspace: {workspace.name} (ID: {workspace.id})")

    # Get folders in workspace
    folders = await client.get_workspace_folders(workspace.id)
```

### 2. Project Management

```python
# Create a project
project = await client.create_project(
    workspace_id="ws_123",
    name="Upwork Registration",
    folder_id="folder_456",
    description="Automated registration tracking"
)

# Get project details
project = await client.get_project(project.id)

# Copy project
copied = await client.copy_project(
    project_id=project.id,
    target_folder_id="folder_789",
    new_name="Fiverr Registration"
)

# Complete/restore project
await client.complete_project(project.id)
await client.restore_project(project.id)
```

### 3. Task Management

```python
from automation import TaskStatus
from datetime import datetime, timedelta

# Create a task
task = await client.create_task(
    project_id=project.id,
    title="Complete registration form",
    description="Fill out all required fields on Upwork",
    assignees=["user_123"],
    due_date=datetime.now() + timedelta(days=1),
    priority=5
)

# Update task status
task = await client.update_task(
    task_id=task.id,
    status=TaskStatus.COMPLETED,
    description="Registration form submitted successfully"
)

# Create subtask
subtask = await client.create_task(
    project_id=project.id,
    title="Verify email",
    parent_id=task.id
)

# Delete task
await client.delete_task(task.id)
```

### 4. AI Agent Integration

```python
from automation import AgentType

# Create custom agent
agent = await client.create_agent(
    folder_id="folder_456",
    name="Registration Assistant",
    system_prompt="You are an AI assistant that helps with freelance platform registrations",
    knowledge_sources=["kb_123", "kb_456"],
    public=False
)

# Generate agent from natural language
agent = await client.generate_agent(
    folder_id="folder_456",
    prompt="""Create an agent that monitors Upwork, Fiverr, and Freelancer
    registrations, tracks progress, and identifies blockers."""
)

# Get all agents
agents = await client.get_agents("folder_456")
```

### 5. Media Management

```python
# Get media files
media_files = await client.get_media_files("folder_456")

for media in media_files:
    print(f"File: {media['name']} - {media['url']}")
```

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    RAG Application                          │
│  (Azure Search + OpenAI + Quart Backend)                    │
└───────────────┬─────────────────────────────────────────────┘
                │
                │ Uses
                ↓
┌───────────────────────────────────────────────────────────────┐
│              Automation System                                │
│  ┌─────────────┬──────────────┬──────────────┬──────────────┐│
│  │ Browser     │ Freelance    │ MCP Task     │ RAG Agent    ││
│  │ Agent       │ Registrar    │ Manager      │              ││
│  └─────────────┴──────────────┴──────────────┴──────────────┘│
└───────────────┬───────────────────────────────────────────────┘
                │
                │ Integrates with
                ↓
┌───────────────────────────────────────────────────────────────┐
│              Taskade Enterprise API                           │
│  ┌─────────────┬──────────────┬──────────────┬──────────────┐│
│  │ Workspaces  │ Projects     │ Tasks        │ AI Agents    ││
│  │ & Folders   │              │              │              ││
│  └─────────────┴──────────────┴──────────────┴──────────────┘│
│                                                               │
│  API: https://www.taskade.com/api/v1                         │
│  Docs: https://docs.taskade.com/api                          │
└───────────────────────────────────────────────────────────────┘
```

### Data Flow

```
1. User Request (via API)
   ↓
2. FreelanceRegistrar initiates registration
   ↓
3. TaskadeFreelanceIntegration creates project
   ↓
4. Browser automation starts (BrowserAgent)
   ↓
5. Progress updates → Taskade tasks
   ↓
6. AI Agent monitors and provides recommendations
   ↓
7. Completion → Update Taskade project
```

## Usage Examples

### Example 1: Complete Registration Workflow

```python
from automation import (
    BrowserAgent,
    FreelanceRegistrar,
    TaskadeClient,
    TaskadeConfig,
    TaskadeFreelanceIntegration,
    RegistrationData,
    APIConfig,
    PlatformType
)

async def complete_registration_with_taskade():
    """Complete registration workflow with Taskade tracking"""

    # 1. Setup Taskade client
    taskade_config = TaskadeConfig(
        api_key="tskdp_NvhoURdQXa1eDDxnCWrZYtb7k4uU2ZkHEC"
    )

    async with TaskadeClient(taskade_config) as taskade:
        # 2. Get workspace
        workspaces = await taskade.get_workspaces()
        workspace_id = workspaces[0].id

        # 3. Create integration
        integration = TaskadeFreelanceIntegration(taskade, workspace_id)

        # 4. Create project for tracking
        project = await integration.create_registration_project(
            platform_name="Upwork",
            user_email="john@example.com",
            folder_id="folder_123"
        )

        print(f"Created Taskade project: {project.name}")

        # 5. Setup browser automation
        agent = BrowserAgent()
        registrar = FreelanceRegistrar(agent)

        # 6. Prepare registration data
        reg_data = RegistrationData(
            email="john@example.com",
            password="SecurePass123!",
            first_name="John",
            last_name="Doe",
            country="United States",
            phone="+1234567890"
        )

        api_config = APIConfig(
            webhook_url="https://api.example.com/webhooks/upwork"
        )

        # 7. Perform registration
        print("Starting registration...")
        result = await registrar.register_platform(
            PlatformType.UPWORK,
            reg_data,
            api_config
        )

        # 8. Update progress in Taskade
        if result.success:
            await integration.update_registration_progress(
                project_id=project.id,
                completed_step="Complete registration form",
                notes=f"Registration successful! Profile: {result.profile_url}"
            )

            await integration.update_registration_progress(
                project_id=project.id,
                completed_step="Generate API credentials",
                notes=f"API Key: {result.api_key[:10]}..."
            )

        print(f"✅ Registration {'successful' if result.success else 'failed'}")

        # 9. Complete project
        if result.success:
            await taskade.complete_project(project.id)

# Run workflow
asyncio.run(complete_registration_with_taskade())
```

### Example 2: Batch Registration with AI Monitoring

```python
async def batch_registration_with_monitoring():
    """Register on multiple platforms with AI monitoring"""

    taskade_config = TaskadeConfig(
        api_key="tskdp_NvhoURdQXa1eDDxnCWrZYtb7k4uU2ZkHEC"
    )

    async with TaskadeClient(taskade_config) as taskade:
        workspaces = await taskade.get_workspaces()
        workspace_id = workspaces[0].id

        integration = TaskadeFreelanceIntegration(taskade, workspace_id)

        # Create monitoring agent
        agent = await integration.create_monitoring_agent(
            folder_id="folder_123",
            platforms=["Upwork", "Fiverr", "Freelancer"]
        )

        print(f"Created monitoring agent: {agent.name}")

        # Register on multiple platforms
        platforms = [
            PlatformType.UPWORK,
            PlatformType.FIVERR,
            PlatformType.FREELANCER
        ]

        for platform in platforms:
            # Create project
            project = await integration.create_registration_project(
                platform_name=platform.value,
                user_email="john@example.com",
                folder_id="folder_123"
            )

            # Perform registration
            # ... (similar to Example 1)

            print(f"✅ Completed {platform.value}")
```

### Example 3: Query and Report

```python
async def generate_registration_report():
    """Generate report of all registration projects"""

    taskade_config = TaskadeConfig(
        api_key="tskdp_NvhoURdQXa1eDDxnCWrZYtb7k4uU2ZkHEC"
    )

    async with TaskadeClient(taskade_config) as taskade:
        # Get current user
        user = await taskade.get_current_user()
        print(f"Logged in as: {user['name']}")

        # Get all workspaces
        workspaces = await taskade.get_workspaces()

        for workspace in workspaces:
            print(f"\n📁 Workspace: {workspace.name}")

            # Get folders
            folders = await taskade.get_workspace_folders(workspace.id)

            for folder in folders:
                # Check for registration projects
                if "registration" in folder["name"].lower():
                    print(f"  └─ Folder: {folder['name']}")

                    # Get agents
                    agents = await taskade.get_agents(folder["id"])
                    print(f"     AI Agents: {len(agents)}")
```

## Freelance Registration Workflow

### Full Cycle Automation

```python
async def full_cycle_registration(platform: PlatformType, user_data: RegistrationData):
    """
    Complete registration cycle:
    1. Create Taskade project
    2. Perform registration
    3. Setup API keys
    4. Configure webhooks
    5. Update Taskade with results
    """

    # Taskade setup
    taskade_config = TaskadeConfig(
        api_key="tskdp_NvhoURdQXa1eDDxnCWrZYtb7k4uU2ZkHEC"
    )

    async with TaskadeClient(taskade_config) as taskade:
        workspaces = await taskade.get_workspaces()
        workspace_id = workspaces[0].id

        integration = TaskadeFreelanceIntegration(taskade, workspace_id)

        # Step 1: Create tracking project
        project = await integration.create_registration_project(
            platform_name=platform.value,
            user_email=user_data.email
        )

        # Step 2: Perform registration
        agent = BrowserAgent()
        registrar = FreelanceRegistrar(agent)

        result = await registrar.register_platform(platform, user_data)

        # Step 3: Update tasks
        steps = [
            ("Complete registration form", result.success),
            ("Verify email address", result.success),
            ("Setup profile and skills", result.success),
            ("Generate API credentials", bool(result.api_key)),
            ("Configure webhook endpoints", bool(result.webhook_active)),
        ]

        for step_name, completed in steps:
            if completed:
                await integration.update_registration_progress(
                    project_id=project.id,
                    completed_step=step_name
                )

        # Step 4: Add final notes
        if result.success:
            await taskade.create_task(
                project_id=project.id,
                title="Registration Summary",
                description=f"""
                ✅ Registration completed successfully!

                Platform: {platform.value}
                Profile URL: {result.profile_url}
                API Key: {result.api_key[:10]}...
                Webhook: {result.webhook_url}
                Screenshots: {len(result.screenshots)}

                Ready for production use.
                """
            )

            await taskade.complete_project(project.id)

        return result, project
```

## AI Agent Integration

### Creating Intelligent Agents

```python
async def create_registration_assistant():
    """Create AI agent for registration assistance"""

    taskade_config = TaskadeConfig(
        api_key="tskdp_NvhoURdQXa1eDDxnCWrZYtb7k4uU2ZkHEC"
    )

    async with TaskadeClient(taskade_config) as taskade:
        # Generate agent from prompt
        agent = await taskade.generate_agent(
            folder_id="folder_123",
            prompt="""
            Create an intelligent assistant for freelance platform registration.

            The agent should:
            1. Monitor registration progress across Upwork, Fiverr, and Freelancer
            2. Identify common blockers (CAPTCHA, email verification, profile requirements)
            3. Provide step-by-step guidance for API setup
            4. Suggest webhook configurations
            5. Track API rate limits and usage
            6. Alert on registration failures
            7. Recommend optimization strategies

            The agent should have expertise in:
            - Freelance platform policies and requirements
            - API integration best practices
            - Webhook security and configuration
            - Troubleshooting common registration issues
            """
        )

        print(f"Created agent: {agent.name}")
        print(f"Agent ID: {agent.id}")

        return agent
```

### Agent Knowledge Sources

```python
async def add_knowledge_to_agent(agent_id: str):
    """Add knowledge sources to AI agent"""

    # In Taskade, you can add knowledge sources via:
    # 1. Project links - agent reads from specific projects
    # 2. Media files - upload documentation
    # 3. External URLs - link to platform docs

    # Our RAG system provides the knowledge base
    # Taskade agent can reference:
    # - Freelance_Platform_Registration_Guide.md (in data/)
    # - Platform-specific documentation
    # - Best practices from docs/

    pass  # Managed via Taskade UI or additional API calls
```

## Best Practices

### 1. Security

```python
# ✅ DO: Use Azure Key Vault
config = TaskadeConfig(
    api_key="",
    use_key_vault=True,
    key_vault_url=os.getenv("AZURE_KEY_VAULT_URL"),
    key_vault_secret_name="taskade-api-key"
)

# ❌ DON'T: Hardcode API keys
config = TaskadeConfig(
    api_key="tskdp_hardcoded_key"  # Never do this!
)
```

### 2. Error Handling

```python
from automation import TaskadeAPIError

try:
    async with TaskadeClient(config) as client:
        project = await client.create_project(workspace_id, "Test")
except TaskadeAPIError as e:
    logger.error(f"Taskade API error: {e}")
    # Fallback: Continue without Taskade tracking
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

### 3. Rate Limiting

```python
# Built-in retry logic with exponential backoff
config = TaskadeConfig(
    api_key=api_key,
    max_retries=3,  # Retry up to 3 times
    retry_delay=1.0  # Start with 1 second, then 2, 4, 8...
)
```

### 4. Project Organization

```python
# Create folder structure
# Workspace
#  └─ Freelance Automation
#      ├─ Upwork
#      │   ├─ User1 Registration
#      │   └─ User2 Registration
#      ├─ Fiverr
#      └─ Freelancer

# Use folder_id to organize projects
folder_id = "automation_folder_123"
project = await client.create_project(
    workspace_id=workspace_id,
    name=f"{platform} - {user_email}",
    folder_id=folder_id
)
```

### 5. Task Prioritization

```python
# Critical tasks: priority 5
await client.create_task(
    project_id=project.id,
    title="Complete registration (URGENT)",
    priority=5
)

# Normal tasks: priority 3
await client.create_task(
    project_id=project.id,
    title="Setup API keys",
    priority=3
)

# Low priority: priority 1
await client.create_task(
    project_id=project.id,
    title="Optional: Add profile photo",
    priority=1
)
```

## Troubleshooting

### Issue: Authentication Failed

```python
# Check API key
print(f"API Key: {config.api_key[:10]}...")

# Test connection
user = await client.get_current_user()
print(f"Authenticated as: {user['name']}")
```

### Issue: Rate Limit Exceeded

```python
# Increase retry delay
config = TaskadeConfig(
    api_key=api_key,
    max_retries=5,
    retry_delay=2.0  # Longer delay between retries
)
```

### Issue: Project Not Found

```python
# Verify workspace ID
workspaces = await client.get_workspaces()
for ws in workspaces:
    print(f"Workspace: {ws.name} - {ws.id}")

# Check folder exists
folders = await client.get_workspace_folders(workspace_id)
```

### Issue: Task Creation Failed

```python
# Verify project ID
project = await client.get_project(project_id)
print(f"Project exists: {project.name}")

# Check assignees exist
members = project.members
print(f"Project members: {[m['name'] for m in members]}")
```

## Additional Resources

### Taskade Documentation
- 📖 **API Docs**: https://docs.taskade.com/api
- 🏠 **Main Site**: https://taskade.com
- 📝 **Blog**: https://taskade.com/blog
- 💬 **Forum**: https://forum.taskade.com/changelog
- 🐙 **GitHub**: https://github.com/taskade

### Repository Resources
- 📂 **Cloned Docs**: `/workspaces/azure-search-openai-demo/external/taskade-docs/`
- 🔗 **MCP Server**: `/workspaces/azure-search-openai-demo/external/taskade-mcp/`
- 📘 **API Reference**: `/workspaces/azure-search-openai-demo/external/taskade-docs/api/`

### Internal Documentation
- [Automation Guide](automation_guide.md)
- [Architecture](automation_architecture.md)
- [Quick Start](../AUTOMATION_README.md)
- [Summary](../AUTOMATION_SUMMARY.md)

## Next Steps

1. **Setup**: Store API key in Azure Key Vault
2. **Test**: Run examples to verify integration
3. **Deploy**: Create production workspace and folders
4. **Monitor**: Setup AI agents for intelligent tracking
5. **Scale**: Integrate with CI/CD pipeline

---

**Enterprise API Key**: `tskdp_NvhoURdQXa1eDDxnCWrZYtb7k4uU2ZkHEC`

**Support**: For enterprise support, contact Taskade team or refer to documentation.
