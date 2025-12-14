"""
Freelance platform registration automation.

This module handles automated registration on various freelance platforms
including API setup and webhook configuration.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from .browser_agent import BrowserAgent, AutomationStep, BrowserConfig

logger = logging.getLogger(__name__)


class PlatformType(Enum):
    """Supported freelance platforms."""

    UPWORK = "upwork"
    FIVERR = "fiverr"
    FREELANCER = "freelancer"
    TOPTAL = "toptal"
    GURU = "guru"
    PEOPLEPERHOUR = "peopleperhour"
    CUSTOM = "custom"


@dataclass
class RegistrationData:
    """Data required for platform registration."""

    email: str
    password: str
    first_name: str
    last_name: str
    company_name: Optional[str] = None
    country: str = "US"
    phone: Optional[str] = None
    skills: List[str] = None
    bio: Optional[str] = None
    portfolio_url: Optional[str] = None

    def __post_init__(self):
        if self.skills is None:
            self.skills = []


@dataclass
class APIConfig:
    """API configuration for platform."""

    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    webhook_url: Optional[str] = None
    scopes: List[str] = None

    def __post_init__(self):
        if self.scopes is None:
            self.scopes = ["read", "write"]


@dataclass
class RegistrationResult:
    """Result of registration process."""

    success: bool
    platform: str
    account_id: Optional[str] = None
    api_config: Optional[APIConfig] = None
    errors: List[str] = None
    screenshots: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.screenshots is None:
            self.screenshots = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class FreelancePlatformHandler:
    """Base class for platform-specific handlers."""

    def __init__(self, platform: PlatformType):
        self.platform = platform

    def get_registration_steps(self, data: RegistrationData) -> List[AutomationStep]:
        """Get platform-specific registration steps."""
        raise NotImplementedError

    def get_api_setup_steps(self, api_config: APIConfig) -> List[AutomationStep]:
        """Get platform-specific API setup steps."""
        raise NotImplementedError

    def get_webhook_setup_steps(self, webhook_url: str) -> List[AutomationStep]:
        """Get platform-specific webhook setup steps."""
        raise NotImplementedError


class UpworkHandler(FreelancePlatformHandler):
    """Upwork platform handler."""

    def __init__(self):
        super().__init__(PlatformType.UPWORK)
        self.base_url = "https://www.upwork.com"

    def get_registration_steps(self, data: RegistrationData) -> List[AutomationStep]:
        """Get Upwork registration steps."""
        return [
            AutomationStep(
                action="navigate",
                value=f"{self.base_url}/nx/signup",
                description="Navigate to Upwork signup page"
            ),
            AutomationStep(
                action="click",
                selector="button[data-qa='btn-apply']",
                description="Click 'Apply as a Freelancer' button"
            ),
            AutomationStep(
                action="fill",
                selector="input[name='firstName']",
                value=data.first_name,
                description="Fill first name"
            ),
            AutomationStep(
                action="fill",
                selector="input[name='lastName']",
                value=data.last_name,
                description="Fill last name"
            ),
            AutomationStep(
                action="fill",
                selector="input[name='email']",
                value=data.email,
                description="Fill email"
            ),
            AutomationStep(
                action="fill",
                selector="input[name='password']",
                value=data.password,
                description="Fill password"
            ),
            AutomationStep(
                action="click",
                selector="select[name='country']",
                description="Select country dropdown"
            ),
            AutomationStep(
                action="click",
                selector=f"option[value='{data.country}']",
                description=f"Select country: {data.country}"
            ),
            AutomationStep(
                action="click",
                selector="button[type='submit']",
                description="Submit registration form"
            ),
            AutomationStep(
                action="screenshot",
                description="Take confirmation screenshot"
            ),
        ]

    def get_api_setup_steps(self, api_config: APIConfig) -> List[AutomationStep]:
        """Get Upwork API setup steps."""
        return [
            AutomationStep(
                action="navigate",
                value=f"{self.base_url}/ab/account-security/api",
                description="Navigate to API settings"
            ),
            AutomationStep(
                action="click",
                selector="button[data-qa='create-api-key']",
                description="Click create API key"
            ),
            AutomationStep(
                action="fill",
                selector="input[name='apiKeyName']",
                value="Automated API Key",
                description="Name the API key"
            ),
            AutomationStep(
                action="click",
                selector="button[data-qa='confirm']",
                description="Confirm API key creation"
            ),
            AutomationStep(
                action="screenshot",
                description="Screenshot API credentials"
            ),
        ]

    def get_webhook_setup_steps(self, webhook_url: str) -> List[AutomationStep]:
        """Get Upwork webhook setup steps."""
        return [
            AutomationStep(
                action="navigate",
                value=f"{self.base_url}/ab/account-security/webhooks",
                description="Navigate to webhook settings"
            ),
            AutomationStep(
                action="click",
                selector="button[data-qa='add-webhook']",
                description="Add new webhook"
            ),
            AutomationStep(
                action="fill",
                selector="input[name='webhookUrl']",
                value=webhook_url,
                description="Fill webhook URL"
            ),
            AutomationStep(
                action="click",
                selector="button[data-qa='save-webhook']",
                description="Save webhook"
            ),
        ]


class FiverrHandler(FreelancePlatformHandler):
    """Fiverr platform handler."""

    def __init__(self):
        super().__init__(PlatformType.FIVERR)
        self.base_url = "https://www.fiverr.com"

    def get_registration_steps(self, data: RegistrationData) -> List[AutomationStep]:
        """Get Fiverr registration steps."""
        return [
            AutomationStep(
                action="navigate",
                value=f"{self.base_url}/join",
                description="Navigate to Fiverr signup"
            ),
            AutomationStep(
                action="fill",
                selector="input[name='email']",
                value=data.email,
                description="Fill email"
            ),
            AutomationStep(
                action="click",
                selector="button[type='submit']",
                description="Continue with email"
            ),
            AutomationStep(
                action="fill",
                selector="input[name='password']",
                value=data.password,
                description="Fill password"
            ),
            AutomationStep(
                action="fill",
                selector="input[name='username']",
                value=f"{data.first_name.lower()}{data.last_name.lower()}",
                description="Fill username"
            ),
            AutomationStep(
                action="click",
                selector="button[type='submit']",
                description="Complete registration"
            ),
            AutomationStep(
                action="screenshot",
                description="Registration complete"
            ),
        ]

    def get_api_setup_steps(self, api_config: APIConfig) -> List[AutomationStep]:
        """Get Fiverr API setup steps."""
        # Fiverr doesn't have public API - placeholder
        return [
            AutomationStep(
                action="navigate",
                value=f"{self.base_url}/settings",
                description="Navigate to settings"
            ),
        ]

    def get_webhook_setup_steps(self, webhook_url: str) -> List[AutomationStep]:
        """Get Fiverr webhook setup steps."""
        return []


class FreelanceRegistrar:
    """
    Main registrar for freelance platforms.

    Handles full registration cycle:
    1. Account creation
    2. Profile setup
    3. API key generation
    4. Webhook configuration
    """

    PLATFORM_HANDLERS = {
        PlatformType.UPWORK: UpworkHandler,
        PlatformType.FIVERR: FiverrHandler,
    }

    def __init__(self, browser_config: Optional[BrowserConfig] = None):
        """Initialize registrar."""
        self.browser_config = browser_config or BrowserConfig()
        self.browser_agent = None

    async def register_platform(
        self,
        platform: PlatformType,
        registration_data: RegistrationData,
        api_config: Optional[APIConfig] = None,
        setup_api: bool = True,
        setup_webhooks: bool = True,
    ) -> RegistrationResult:
        """
        Register on a freelance platform with full setup.

        Args:
            platform: Target platform
            registration_data: Registration information
            api_config: API configuration (if setup_api is True)
            setup_api: Whether to setup API keys
            setup_webhooks: Whether to setup webhooks

        Returns:
            RegistrationResult with success status and details
        """
        logger.info(f"Starting registration on {platform.value}")

        result = RegistrationResult(
            success=False,
            platform=platform.value
        )

        # Get platform handler
        handler_class = self.PLATFORM_HANDLERS.get(platform)
        if not handler_class:
            result.errors.append(f"Unsupported platform: {platform.value}")
            return result

        handler = handler_class()

        try:
            async with BrowserAgent(self.browser_config) as agent:
                self.browser_agent = agent

                # Step 1: Account registration
                logger.info("Step 1: Account registration")
                reg_steps = handler.get_registration_steps(registration_data)
                reg_result = await agent.execute_steps(reg_steps)

                if not reg_result["success"]:
                    result.errors.extend([e["error"] for e in reg_result["errors"]])
                    result.screenshots = reg_result["screenshots"]
                    return result

                result.screenshots.extend(reg_result["screenshots"])

                # Wait for email confirmation (simulated)
                logger.info("Waiting for account confirmation...")
                await asyncio.sleep(5)

                # Step 2: API setup
                if setup_api and api_config:
                    logger.info("Step 2: API key setup")
                    api_steps = handler.get_api_setup_steps(api_config)
                    api_result = await agent.execute_steps(api_steps)

                    if not api_result["success"]:
                        logger.warning("API setup failed, continuing...")
                        result.errors.extend([e["error"] for e in api_result["errors"]])

                    result.screenshots.extend(api_result["screenshots"])
                    result.api_config = api_config

                # Step 3: Webhook setup
                if setup_webhooks and api_config and api_config.webhook_url:
                    logger.info("Step 3: Webhook configuration")
                    webhook_steps = handler.get_webhook_setup_steps(api_config.webhook_url)
                    webhook_result = await agent.execute_steps(webhook_steps)

                    if not webhook_result["success"]:
                        logger.warning("Webhook setup failed, continuing...")
                        result.errors.extend([e["error"] for e in webhook_result["errors"]])

                    result.screenshots.extend(webhook_result["screenshots"])

                result.success = True
                logger.info(f"Registration complete for {platform.value}")

        except Exception as e:
            logger.error(f"Registration failed: {e}")
            result.errors.append(str(e))

        return result

    async def register_multiple_platforms(
        self,
        platforms: List[PlatformType],
        registration_data: RegistrationData,
        api_config: Optional[APIConfig] = None,
    ) -> List[RegistrationResult]:
        """
        Register on multiple platforms sequentially.

        Args:
            platforms: List of platforms to register on
            registration_data: Registration data
            api_config: API configuration

        Returns:
            List of registration results
        """
        results = []

        for platform in platforms:
            logger.info(f"Processing platform: {platform.value}")
            result = await self.register_platform(
                platform=platform,
                registration_data=registration_data,
                api_config=api_config,
            )
            results.append(result)

            # Delay between registrations to avoid detection
            if result.success:
                await asyncio.sleep(10)

        return results
