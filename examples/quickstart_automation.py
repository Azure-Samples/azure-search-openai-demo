#!/usr/bin/env python3
"""
Quick start script for automation system.

Usage:
    python examples/quickstart_automation.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "app" / "backend"
sys.path.insert(0, str(backend_path))

from automation import (
    FreelanceRegistrar,
    PlatformType,
    RegistrationData,
    APIConfig,
    BrowserConfig,
    MCPTaskManager,
    TaskPriority,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def example_single_registration():
    """Example: Single platform registration."""
    logger.info("=" * 50)
    logger.info("Example 1: Single Platform Registration")
    logger.info("=" * 50)

    # Configure registration data
    registration_data = RegistrationData(
        email="john.doe@example.com",
        password="SecurePassword123!",
        first_name="John",
        last_name="Doe",
        country="US",
        skills=["Python", "JavaScript", "React"],
        bio="Experienced full-stack developer"
    )

    # Configure API and webhooks
    api_config = APIConfig(
        webhook_url="https://your-domain.com/webhook",
        scopes=["read", "write"]
    )

    # Configure browser (visible mode for demo)
    browser_config = BrowserConfig(
        headless=False,  # Set to True for production
        slow_mo=500,     # Slow down for visibility
    )

    # Create registrar
    registrar = FreelanceRegistrar(browser_config)

    # Register on Upwork
    logger.info("Starting registration on Upwork...")
    result = await registrar.register_platform(
        platform=PlatformType.UPWORK,
        registration_data=registration_data,
        api_config=api_config,
        setup_api=True,
        setup_webhooks=True
    )

    # Display results
    if result.success:
        logger.info("✅ Registration successful!")
        logger.info(f"Platform: {result.platform}")
        logger.info(f"Screenshots: {len(result.screenshots)} captured")
        if result.api_config:
            logger.info("🔑 API configured successfully")
    else:
        logger.error("❌ Registration failed")
        for error in result.errors:
            logger.error(f"  - {error}")


async def example_batch_registration():
    """Example: Batch registration on multiple platforms."""
    logger.info("=" * 50)
    logger.info("Example 2: Batch Registration")
    logger.info("=" * 50)

    registration_data = RegistrationData(
        email="jane.smith@example.com",
        password="AnotherSecurePass456!",
        first_name="Jane",
        last_name="Smith",
        country="US"
    )

    api_config = APIConfig(
        webhook_url="https://your-domain.com/webhook"
    )

    browser_config = BrowserConfig(headless=True)

    registrar = FreelanceRegistrar(browser_config)

    # Register on multiple platforms
    platforms = [PlatformType.UPWORK, PlatformType.FIVERR]

    logger.info(f"Registering on {len(platforms)} platforms...")
    results = await registrar.register_multiple_platforms(
        platforms=platforms,
        registration_data=registration_data,
        api_config=api_config
    )

    # Summary
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful

    logger.info(f"\n📊 Batch Registration Summary:")
    logger.info(f"  Total: {len(results)}")
    logger.info(f"  ✅ Successful: {successful}")
    logger.info(f"  ❌ Failed: {failed}")

    for result in results:
        status = "✅" if result.success else "❌"
        logger.info(f"  {status} {result.platform}")


async def example_task_management():
    """Example: Task management with MCP."""
    logger.info("=" * 50)
    logger.info("Example 3: Task Management with MCP")
    logger.info("=" * 50)

    # Create task manager
    manager = MCPTaskManager()

    # Start background processor
    processor = await manager.start_processor()

    # Create multiple tasks
    platforms = ["upwork", "fiverr", "freelancer"]

    for platform in platforms:
        task = manager.create_task(
            title=f"Register on {platform.title()}",
            description=f"Complete registration with API setup on {platform}",
            task_type="registration",
            platform=platform,
            priority=TaskPriority.MEDIUM,
            metadata={
                "email": f"user@example.com",
                "requires_api": True
            }
        )
        await manager.enqueue_task(task)
        logger.info(f"📝 Created task: {task.title} (ID: {task.id})")

    # Monitor progress
    logger.info("\n⏳ Monitoring task progress...")

    for _ in range(10):  # Monitor for 10 seconds
        stats = manager.get_queue_stats()
        logger.info(
            f"Queue: {stats['queue_size']} | "
            f"Running: {stats['running']} | "
            f"Completed: {stats['completed']} | "
            f"Failed: {stats['failed']}"
        )

        if stats['pending'] == 0 and stats['running'] == 0:
            logger.info("✅ All tasks completed!")
            break

        await asyncio.sleep(1)

    # Get final stats
    final_stats = manager.get_queue_stats()
    logger.info(f"\n📊 Final Statistics:")
    logger.info(f"  Total Tasks: {final_stats['total_tasks']}")
    logger.info(f"  ✅ Completed: {final_stats['completed']}")
    logger.info(f"  ❌ Failed: {final_stats['failed']}")

    # Cancel processor
    processor.cancel()


async def example_list_platforms():
    """Example: List supported platforms."""
    logger.info("=" * 50)
    logger.info("Example 4: List Supported Platforms")
    logger.info("=" * 50)

    logger.info("\n🌐 Supported Freelance Platforms:\n")

    for platform in PlatformType:
        if platform != PlatformType.CUSTOM:
            logger.info(f"  • {platform.name} ({platform.value})")

    logger.info("\n📌 Each platform supports:")
    logger.info("  - Automated registration")
    logger.info("  - API key setup (where available)")
    logger.info("  - Webhook configuration")


async def main():
    """Main entry point."""
    print("""
╔═══════════════════════════════════════════════════════╗
║   Freelance Platform Automation - Quick Start       ║
║   Powered by RAG + MCP + Playwright                  ║
╚═══════════════════════════════════════════════════════╝
    """)

    try:
        # Run examples
        # NOTE: Most examples are mocked for demonstration
        # In production, provide real credentials

        # Example 1: List platforms (safe to run)
        await example_list_platforms()

        # Example 2: Task management (safe to run)
        # await example_task_management()

        # Example 3: Single registration (requires real credentials)
        # await example_single_registration()

        # Example 4: Batch registration (requires real credentials)
        # await example_batch_registration()

        logger.info("\n✨ Examples completed!")
        logger.info("\n📚 Next steps:")
        logger.info("  1. Review docs/automation_guide.md")
        logger.info("  2. Add real credentials")
        logger.info("  3. Test on a single platform first")
        logger.info("  4. Use API endpoints for production")

    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Error: {e}", exc_info=True)
    finally:
        logger.info("\n👋 Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
