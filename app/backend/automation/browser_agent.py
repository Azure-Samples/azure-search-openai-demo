"""
Browser automation agent using Playwright with Edge browser support.

This module provides intelligent browser automation with RAG-powered decision making.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)


@dataclass
class BrowserConfig:
    """Configuration for browser automation."""

    headless: bool = False
    slow_mo: int = 100
    timeout: int = 30000
    viewport: Dict[str, int] = None
    user_agent: Optional[str] = None

    def __post_init__(self):
        if self.viewport is None:
            self.viewport = {"width": 1920, "height": 1080}


@dataclass
class AutomationStep:
    """Represents a single automation step."""

    action: str  # click, fill, select, wait, navigate, screenshot
    selector: Optional[str] = None
    value: Optional[str] = None
    timeout: int = 30000
    description: str = ""


class BrowserAgent:
    """
    Intelligent browser automation agent.

    Features:
    - Edge browser support (Chromium-based)
    - Automatic retry on failures
    - Screenshot capture
    - Cookie management
    - Session persistence
    """

    def __init__(self, config: Optional[BrowserConfig] = None):
        """Initialize browser agent."""
        self.config = config or BrowserConfig()
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()

    async def start(self, channel: str = "msedge"):
        """
        Start browser instance.

        Args:
            channel: Browser channel - 'msedge' for Edge, 'chrome' for Chrome
        """
        logger.info(f"Starting browser with channel: {channel}")

        self.playwright = await async_playwright().start()

        try:
            # Try to launch Edge first
            self.browser = await self.playwright.chromium.launch(
                channel=channel,
                headless=self.config.headless,
                slow_mo=self.config.slow_mo,
            )
        except Exception as e:
            logger.warning(f"Failed to launch {channel}: {e}. Falling back to chromium.")
            # Fallback to regular Chromium
            self.browser = await self.playwright.chromium.launch(
                headless=self.config.headless,
                slow_mo=self.config.slow_mo,
            )

        self.context = await self.browser.new_context(
            viewport=self.config.viewport,
            user_agent=self.config.user_agent,
        )

        self.page = await self.context.new_page()
        self.page.set_default_timeout(self.config.timeout)

        logger.info("Browser started successfully")

    async def stop(self):
        """Stop browser instance."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

        logger.info("Browser stopped")

    async def navigate(self, url: str, wait_until: str = "domcontentloaded"):
        """
        Navigate to URL.

        Args:
            url: Target URL
            wait_until: Wait strategy - 'load', 'domcontentloaded', 'networkidle'
        """
        logger.info(f"Navigating to: {url}")
        await self.page.goto(url, wait_until=wait_until)

    async def fill_form(self, selector: str, value: str):
        """Fill form field."""
        logger.info(f"Filling field: {selector}")
        await self.page.fill(selector, value)

    async def click(self, selector: str):
        """Click element."""
        logger.info(f"Clicking: {selector}")
        await self.page.click(selector)

    async def wait_for_selector(self, selector: str, state: str = "visible", timeout: Optional[int] = None):
        """Wait for element."""
        logger.info(f"Waiting for: {selector} (state: {state})")
        await self.page.wait_for_selector(selector, state=state, timeout=timeout or self.config.timeout)

    async def screenshot(self, path: str, full_page: bool = True):
        """Take screenshot."""
        logger.info(f"Taking screenshot: {path}")
        await self.page.screenshot(path=path, full_page=full_page)

    async def get_cookies(self) -> List[Dict]:
        """Get all cookies."""
        return await self.context.cookies()

    async def set_cookies(self, cookies: List[Dict]):
        """Set cookies."""
        await self.context.add_cookies(cookies)

    async def execute_steps(self, steps: List[AutomationStep]) -> Dict[str, Any]:
        """
        Execute a sequence of automation steps.

        Args:
            steps: List of automation steps

        Returns:
            Dict with execution results
        """
        results = {
            "success": True,
            "steps_completed": 0,
            "errors": [],
            "screenshots": [],
        }

        for i, step in enumerate(steps):
            try:
                logger.info(f"Step {i+1}/{len(steps)}: {step.description or step.action}")

                if step.action == "navigate":
                    await self.navigate(step.value)

                elif step.action == "fill":
                    await self.fill_form(step.selector, step.value)

                elif step.action == "click":
                    await self.click(step.selector)

                elif step.action == "wait":
                    await self.wait_for_selector(step.selector, timeout=step.timeout)

                elif step.action == "screenshot":
                    screenshot_path = f"screenshots/step_{i+1}.png"
                    await self.screenshot(screenshot_path)
                    results["screenshots"].append(screenshot_path)

                elif step.action == "sleep":
                    await asyncio.sleep(int(step.value or 1))

                else:
                    logger.warning(f"Unknown action: {step.action}")

                results["steps_completed"] += 1

            except Exception as e:
                logger.error(f"Error in step {i+1}: {e}")
                results["success"] = False
                results["errors"].append({
                    "step": i + 1,
                    "action": step.action,
                    "error": str(e)
                })
                # Take error screenshot
                try:
                    error_screenshot = f"screenshots/error_step_{i+1}.png"
                    await self.screenshot(error_screenshot)
                    results["screenshots"].append(error_screenshot)
                except:
                    pass
                break

        return results

    async def extract_text(self, selector: str) -> str:
        """Extract text from element."""
        element = await self.page.query_selector(selector)
        if element:
            return await element.text_content()
        return ""

    async def get_page_content(self) -> str:
        """Get full page content."""
        return await self.page.content()
