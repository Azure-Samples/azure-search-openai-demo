"""Browser automation agent powered by Playwright."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    ViewportSize,
    async_playwright,
)

logger = logging.getLogger(__name__)

WaitState = Literal["attached", "detached", "visible", "hidden"]
WaitUntilState = Literal["load", "domcontentloaded", "networkidle"]


@dataclass
class BrowserConfig:
    """Configuration options for the browser session."""

    headless: bool = False
    slow_mo: int = 100
    timeout: int = 30_000
    viewport: Optional[ViewportSize] = None
    user_agent: Optional[str] = None

    def resolved_viewport(self) -> ViewportSize:
        """Return a safe viewport object."""
        return self.viewport or {"width": 1920, "height": 1080}


@dataclass
class AutomationStep:
    """Represents one instruction for the automation agent."""

    action: str
    selector: Optional[str] = None
    value: Optional[str] = None
    timeout: Optional[int] = None
    state: WaitState = "visible"
    description: str = ""


class BrowserAgent:
    """High-level helper built on top of Playwright for deterministic flows."""

    def __init__(
        self,
        config: Optional[BrowserConfig] = None,
        *,
        channel: str = "msedge",
        screenshot_dir: Optional[str | Path] = None,
    ) -> None:
        self.config = config or BrowserConfig()
        self.channel = channel
        self.screenshot_dir = Path(screenshot_dir).expanduser() if screenshot_dir else Path("screenshots")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def __aenter__(self) -> "BrowserAgent":
        await self.start()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.stop()

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------
    async def start(self, channel: Optional[str] = None) -> None:
        """Start Playwright and open a browser context."""

        if self.playwright or self.browser or self.context or self.page:
            # Clean up any dangling state before restarting.
            await self.stop()

        self.channel = channel or self.channel
        logger.info("Starting browser session using channel '%s'", self.channel)

        self.playwright = await async_playwright().start()

        try:
            self.browser = await self.playwright.chromium.launch(
                channel=self.channel,
                headless=self.config.headless,
                slow_mo=self.config.slow_mo,
            )
        except Exception as exc:  # pragma: no cover - launch failure fallback
            logger.warning("Failed to launch %s (%s). Falling back to bundled Chromium.", self.channel, exc)
            self.browser = await self.playwright.chromium.launch(
                headless=self.config.headless,
                slow_mo=self.config.slow_mo,
            )

        viewport = self.config.resolved_viewport()
        self.context = await self.browser.new_context(
            viewport=viewport,
            user_agent=self.config.user_agent,
        )

        self.page = await self.context.new_page()
        self.page.set_default_timeout(self.config.timeout)

    async def stop(self) -> None:
        """Close Playwright resources."""

        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ensure_context(self) -> BrowserContext:
        if not self.context:
            raise RuntimeError("Browser context not initialized. Call start() first.")
        return self.context

    def _ensure_page(self) -> Page:
        if not self.page:
            raise RuntimeError("Browser page not initialized. Call start() first.")
        return self.page

    def _screenshot_path(self, filename: str) -> str:
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        return str(self.screenshot_dir / filename)

    # ------------------------------------------------------------------
    # Primitive actions
    # ------------------------------------------------------------------
    async def navigate(self, url: str, *, wait_until: WaitUntilState = "domcontentloaded") -> None:
        page = self._ensure_page()
        logger.info("Navigating to %s", url)
        await page.goto(url, wait_until=wait_until)

    async def fill_form(self, selector: str, value: str) -> None:
        page = self._ensure_page()
        logger.info("Filling selector %s", selector)
        await page.fill(selector, value)

    async def click(self, selector: str) -> None:
        page = self._ensure_page()
        logger.info("Clicking selector %s", selector)
        await page.click(selector)

    async def wait_for_selector(
        self,
        selector: str,
        *,
        state: WaitState = "visible",
        timeout: Optional[int] = None,
    ) -> None:
        page = self._ensure_page()
        logger.info("Waiting for selector %s (state=%s)", selector, state)
        await page.wait_for_selector(selector, state=state, timeout=timeout or self.config.timeout)

    async def screenshot(self, path: str, *, full_page: bool = True) -> str:
        page = self._ensure_page()
        await page.screenshot(path=path, full_page=full_page)
        return path

    async def get_cookies(self) -> List[Dict[str, Any]]:
        context = self._ensure_context()
        return await context.cookies()

    async def set_cookies(self, cookies: List[Dict[str, Any]]) -> None:
        context = self._ensure_context()
        await context.add_cookies(cookies)

    async def extract_text(self, selector: str) -> str:
        page = self._ensure_page()
        element = await page.query_selector(selector)
        if element is None:
            return ""
        text = await element.text_content()
        return text or ""

    async def get_page_content(self) -> str:
        page = self._ensure_page()
        return await page.content()

    # ------------------------------------------------------------------
    # High-level orchestration
    # ------------------------------------------------------------------
    async def execute_steps(self, steps: List[AutomationStep]) -> Dict[str, Any]:
        """Run a list of steps sequentially, capturing progress and screenshots."""

        results: Dict[str, Any] = {
            "success": True,
            "steps_completed": 0,
            "errors": [],
            "screenshots": [],
        }

        for index, step in enumerate(steps, start=1):
            description = step.description or step.action
            logger.info("Executing step %s/%s: %s", index, len(steps), description)

            try:
                if step.action == "navigate":
                    if not step.value:
                        raise ValueError("navigate step requires a URL value")
                    await self.navigate(step.value)

                elif step.action == "fill":
                    if not step.selector or step.value is None:
                        raise ValueError("fill step requires selector and value")
                    await self.fill_form(step.selector, step.value)

                elif step.action == "click":
                    if not step.selector:
                        raise ValueError("click step requires selector")
                    await self.click(step.selector)

                elif step.action == "wait":
                    if not step.selector:
                        raise ValueError("wait step requires selector")
                    await self.wait_for_selector(
                        step.selector,
                        state=step.state,
                        timeout=step.timeout or self.config.timeout,
                    )

                elif step.action == "screenshot":
                    filename = step.value or f"step_{index}.png"
                    screenshot_path = self._screenshot_path(filename)
                    await self.screenshot(screenshot_path)
                    results["screenshots"].append(screenshot_path)

                elif step.action == "sleep":
                    duration = float(step.value) if step.value else 1.0
                    await asyncio.sleep(max(duration, 0.0))

                else:
                    logger.warning("Unknown automation action '%s'", step.action)

                results["steps_completed"] += 1

            except Exception as exc:  # pragma: no cover - runtime safety path
                logger.error("Error while executing step %s (%s): %s", index, step.action, exc)
                results["success"] = False
                results["errors"].append({
                    "step": index,
                    "action": step.action,
                    "error": str(exc),
                })

                try:
                    error_path = self._screenshot_path(f"error_step_{index}.png")
                    await self.screenshot(error_path)
                    results["screenshots"].append(error_path)
                except Exception as screenshot_exc:  # pragma: no cover
                    logger.warning("Unable to capture error screenshot: %s", screenshot_exc)

                break

        return results
