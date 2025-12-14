#!/usr/bin/env python3
"""
Taskade Enterprise API Integration Examples

This script demonstrates how to use the Taskade Enterprise API
for managing freelance platform registrations.

Usage:
    python examples/taskade_examples.py

Requirements:
    - Taskade Enterprise API key in environment or Key Vault
    - Active Taskade workspace
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "app" / "backend"))

from automation import (
    TaskadeClient,
    TaskadeConfig,
    TaskadeFreelanceIntegration,
    TaskStatus as TaskadeTaskStatus,
    TaskadeAPIError,
)


async def example_1_basic_connection():
    """Example 1: Test basic Taskade connection"""
    print("\n" + "="*60)
    print("Example 1: Basic Connection Test")
    print("="*60)

    # Configure client
    config = TaskadeConfig(
        api_key=os.getenv("TASKADE_API_KEY", "tskdp_NvhoURdQXa1eDDxnCWrZYtb7k4uU2ZkHEC"),
        timeout=30
    )

    try:
        async with TaskadeClient(config) as client:
            # Get current user
            user = await client.get_current_user()
            print(f"\n✅ Connected as: {user.get('name', 'Unknown')}")
            print(f"   Email: {user.get('email', 'N/A')}")

            # Get workspaces
            workspaces = await client.get_workspaces()
            print(f"\n📁 Found {len(workspaces)} workspace(s):")

            for ws in workspaces:
                print(f"   - {ws.name}")
                print(f"     ID: {ws.id}")
                print(f"     Owner: {ws.owner_id}")
                print(f"     Members: {len(ws.members)}")

            return workspaces[0] if workspaces else None

    except TaskadeAPIError as e:
        print(f"\n❌ Taskade API Error: {e}")
        return None
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        return None


async def example_2_workspace_structure(workspace_id: str):
    """Example 2: Explore workspace structure"""
    print("\n" + "="*60)
    print("Example 2: Workspace Structure")
    print("="*60)

    config = TaskadeConfig(
        api_key=os.getenv("TASKADE_API_KEY", "tskdp_NvhoURdQXa1eDDxnCWrZYtb7k4uU2ZkHEC")
    )

    async with TaskadeClient(config) as client:
        # Get folders
        folders = await client.get_workspace_folders(workspace_id)
        print(f"\n📂 Found {len(folders)} folder(s):")

        for folder in folders:
            print(f"\n   Folder: {folder.get('name', 'Unnamed')}")
            print(f"   ID: {folder.get('id')}")

            # Get agents in folder
            try:
                agents = await client.get_agents(folder["id"])
                print(f"   🤖 AI Agents: {len(agents)}")

                for agent in agents:
                    print(f"      - {agent.name} ({agent.type.value})")
            except:
                print(f"   🤖 AI Agents: 0")

            # Get media files
            try:
                media = await client.get_media_files(folder["id"])
                print(f"   📎 Media Files: {len(media)}")
            except:
                print(f"   📎 Media Files: 0")

        return folders[0]["id"] if folders else None


async def example_3_create_project(workspace_id: str, folder_id: str = None):
    """Example 3: Create a registration project"""
    print("\n" + "="*60)
    print("Example 3: Create Registration Project")
    print("="*60)

    config = TaskadeConfig(
        api_key=os.getenv("TASKADE_API_KEY", "tskdp_NvhoURdQXa1eDDxnCWrZYtb7k4uU2ZkHEC")
    )

    async with TaskadeClient(config) as client:
        # Create project
        project_name = f"Upwork Registration - Test User - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        project = await client.create_project(
            workspace_id=workspace_id,
            name=project_name,
            folder_id=folder_id,
            description="Automated registration tracking for Upwork platform"
        )

        print(f"\n✅ Created project: {project.name}")
        print(f"   ID: {project.id}")
        print(f"   Workspace: {project.workspace_id}")

        # Create tasks
        tasks = [
            ("Complete registration form", 5, "Fill out all required fields"),
            ("Verify email address", 4, "Click verification link in email"),
            ("Setup profile and skills", 3, "Add professional details"),
            ("Generate API credentials", 4, "Create API key in developer settings"),
            ("Configure webhook endpoints", 3, "Setup webhook URLs"),
            ("Test API connection", 2, "Verify API access works")
        ]

        print(f"\n📋 Creating {len(tasks)} tasks...")

        for title, priority, description in tasks:
            task = await client.create_task(
                project_id=project.id,
                title=title,
                description=description,
                priority=priority,
                due_date=datetime.now() + timedelta(days=1)
            )
            print(f"   ✓ {title} (Priority: {priority})")

        print(f"\n✅ Project setup complete!")
        return project


async def example_4_update_tasks(project_id: str):
    """Example 4: Update task progress"""
    print("\n" + "="*60)
    print("Example 4: Update Task Progress")
    print("="*60)

    config = TaskadeConfig(
        api_key=os.getenv("TASKADE_API_KEY", "tskdp_NvhoURdQXa1eDDxnCWrZYtb7k4uU2ZkHEC")
    )

    async with TaskadeClient(config) as client:
        # Get project
        project = await client.get_project(project_id)
        print(f"\n📁 Project: {project.name}")
        print(f"   Tasks: {len(project.tasks)}")

        # Complete first 3 tasks
        print(f"\n⚡ Simulating task completion...")

        for i, task_data in enumerate(project.tasks[:3]):
            task_id = task_data.get("id")
            task_title = task_data.get("title", "Unknown")

            if task_id:
                await client.update_task(
                    task_id=task_id,
                    status=TaskadeTaskStatus.COMPLETED,
                    description=f"✅ Completed successfully at {datetime.now().strftime('%H:%M:%S')}"
                )
                print(f"   ✓ Completed: {task_title}")

                # Simulate delay
                await asyncio.sleep(0.5)

        print(f"\n✅ Updated {min(3, len(project.tasks))} tasks")


async def example_5_create_ai_agent(folder_id: str):
    """Example 5: Create AI monitoring agent"""
    print("\n" + "="*60)
    print("Example 5: Create AI Monitoring Agent")
    print("="*60)

    config = TaskadeConfig(
        api_key=os.getenv("TASKADE_API_KEY", "tskdp_NvhoURdQXa1eDDxnCWrZYtb7k4uU2ZkHEC")
    )

    async with TaskadeClient(config) as client:
        # Generate agent from natural language
        prompt = """
        Create an intelligent assistant for freelance platform registration monitoring.

        The agent should:
        1. Monitor registration progress across Upwork, Fiverr, and Freelancer
        2. Identify blockers like CAPTCHA, email verification issues, or profile requirements
        3. Provide step-by-step guidance for API setup and webhook configuration
        4. Track API rate limits and usage patterns
        5. Alert on registration failures or anomalies
        6. Suggest optimization strategies based on success rates

        The agent has expertise in:
        - Freelance platform policies and requirements
        - API integration best practices
        - Webhook security and configuration
        - Common registration troubleshooting
        """

        print(f"\n🤖 Generating AI agent...")

        agent = await client.generate_agent(
            folder_id=folder_id,
            prompt=prompt
        )

        print(f"\n✅ Created agent: {agent.name}")
        print(f"   ID: {agent.id}")
        print(f"   Type: {agent.type.value}")
        print(f"   Public: {agent.public}")

        if agent.system_prompt:
            print(f"\n   System Prompt:")
            print(f"   {agent.system_prompt[:200]}...")

        return agent


async def example_6_integrated_workflow():
    """Example 6: Complete integrated workflow"""
    print("\n" + "="*60)
    print("Example 6: Integrated Registration Workflow")
    print("="*60)

    config = TaskadeConfig(
        api_key=os.getenv("TASKADE_API_KEY", "tskdp_NvhoURdQXa1eDDxnCWrZYtb7k4uU2ZkHEC")
    )

    async with TaskadeClient(config) as client:
        # Get workspace
        workspaces = await client.get_workspaces()
        if not workspaces:
            print("❌ No workspaces found")
            return

        workspace_id = workspaces[0].id

        # Create integration
        integration = TaskadeFreelanceIntegration(client, workspace_id)

        print(f"\n📁 Using workspace: {workspaces[0].name}")

        # Create registration project
        print(f"\n⚡ Creating registration project...")

        project = await integration.create_registration_project(
            platform_name="Upwork",
            user_email="test@example.com"
        )

        print(f"✅ Project: {project.name}")

        # Simulate registration progress
        steps = [
            "Complete registration form",
            "Verify email address",
            "Setup profile and skills",
            "Generate API credentials"
        ]

        print(f"\n⚡ Simulating registration progress...")

        for step in steps:
            await asyncio.sleep(1)  # Simulate work

            await integration.update_registration_progress(
                project_id=project.id,
                completed_step=step,
                notes=f"Completed at {datetime.now().strftime('%H:%M:%S')}"
            )

            print(f"   ✓ {step}")

        print(f"\n✅ Registration workflow complete!")

        # Complete project
        await client.complete_project(project.id)
        print(f"   Project marked as completed")


async def example_7_list_all_projects(workspace_id: str):
    """Example 7: List all projects and their status"""
    print("\n" + "="*60)
    print("Example 7: List All Projects")
    print("="*60)

    config = TaskadeConfig(
        api_key=os.getenv("TASKADE_API_KEY", "tskdp_NvhoURdQXa1eDDxnCWrZYtb7k4uU2ZkHEC")
    )

    async with TaskadeClient(config) as client:
        folders = await client.get_workspace_folders(workspace_id)

        print(f"\n📊 Registration Projects Summary:")

        total_projects = 0

        for folder in folders:
            print(f"\n📂 Folder: {folder.get('name', 'Unnamed')}")

            # Note: Need to implement get_folder_projects() method
            # For now, just show folder info
            print(f"   ID: {folder.get('id')}")

        print(f"\n✅ Total projects: {total_projects}")


async def main():
    """Run all examples"""
    print("\n" + "="*70)
    print(" " * 15 + "TASKADE ENTERPRISE API EXAMPLES")
    print("="*70)
    print("\n🔑 API Key: tskdp_NvhoURdQXa1eDDxnCWrZYtb7k4uU2ZkHEC")
    print("📖 Documentation: https://docs.taskade.com/api")
    print("🌐 Taskade: https://taskade.com")

    try:
        # Example 1: Test connection
        workspace = await example_1_basic_connection()

        if not workspace:
            print("\n❌ Cannot proceed without workspace")
            return

        workspace_id = workspace.id

        # Example 2: Explore structure
        folder_id = await example_2_workspace_structure(workspace_id)

        # Example 3: Create project
        project = await example_3_create_project(workspace_id, folder_id)

        if project:
            # Example 4: Update tasks
            await example_4_update_tasks(project.id)

        # Example 5: Create AI agent (if folder exists)
        if folder_id:
            try:
                await example_5_create_ai_agent(folder_id)
            except Exception as e:
                print(f"\n⚠️  Could not create agent: {e}")

        # Example 6: Integrated workflow
        await example_6_integrated_workflow()

        # Example 7: List projects
        await example_7_list_all_projects(workspace_id)

        print("\n" + "="*70)
        print(" " * 20 + "✅ ALL EXAMPLES COMPLETED!")
        print("="*70)

        print("\n📚 Next Steps:")
        print("   1. Review docs/taskade_integration.md for detailed guide")
        print("   2. Store API key in Azure Key Vault (recommended)")
        print("   3. Create production workspace and folders")
        print("   4. Setup AI agents for monitoring")
        print("   5. Integrate with your RAG application")

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
