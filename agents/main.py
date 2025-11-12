"""
Main entry point for the Microsoft 365 Agent.
This module starts the agent application and handles incoming requests.
"""

import asyncio
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings
from botbuilder.schema import (
    Activity,
    ActivityTypes,
    ConversationReference,
    ResourceResponse,
)
from quart import Quart, request, jsonify
from quart_cors import cors

from config.agent_config import AgentConfig
from agent_app import AgentApplication

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if env_path.exists():
    logger.info(f"Loaded environment variables from {env_path}")


class AgentServer:
    """
    Server that hosts the Microsoft 365 Agent.
    This server handles incoming requests and routes them to the agent.
    """
    
    def __init__(self):
        self.app = Quart(__name__)
        # Enable CORS for Bot Framework Emulator
        self.app = cors(self.app, allow_origin="*")
        self.agent_app: Optional[AgentApplication] = None
        self.adapter: Optional[BotFrameworkAdapter] = None
        
        # Add catch-all logging middleware
        @self.app.before_request
        async def log_request():
            # Force print to ensure it shows in console
            print(f"\n{'='*60}")
            print(f"[BEFORE_REQUEST] {request.method} {request.path}")
            print(f"[BEFORE_REQUEST] Headers: {dict(request.headers)}")
            logger.info(f"Incoming request: {request.method} {request.path}")
            logger.info(f"Headers: {dict(request.headers)}")
        
        # Configure routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Set up the Quart routes."""
        
        @self.app.route("/", methods=["GET"])
        async def health_check():
            """Health check endpoint."""
            logger.info("Health check called")
            return jsonify({
                "status": "healthy",
                "service": "Microsoft 365 RAG Agent",
                "version": "1.0.0"
            })
        
        @self.app.route("/api/copilot/health", methods=["GET"])
        async def copilot_health():
            """Health check endpoint for Copilot plugin."""
            return jsonify({
                "status": "healthy",
                "plugin": "ai-master-engineer-rag",
                "version": "1.0.0"
            })
        
        @self.app.route("/api/copilot/search", methods=["POST"])
        async def copilot_search():
            """Search endpoint for Copilot plugin."""
            try:
                if not self.agent_app:
                    return jsonify({"error": "Agent not initialized"}), 500
                
                body = await request.get_json()
                if not body:
                    return jsonify({"error": "Invalid request body"}), 400
                
                # Get auth claims
                auth_claims = {
                    "oid": body.get("userId", ""),
                    "tenant_id": body.get("tenantId", self.agent_app.config.tenant_id)
                }
                
                # Get Copilot handler
                from handlers.copilot_handler import CopilotHandler, CopilotRequest
                copilot_handler = CopilotHandler(
                    self.agent_app.rag_service,
                    self.agent_app.auth_service
                )
                
                # Create request
                copilot_request = CopilotRequest(
                    query=body.get("query", ""),
                    conversation_history=body.get("conversationHistory"),
                    max_results=body.get("maxResults", 5)
                )
                
                # Handle request
                result = await copilot_handler.handle_search_request(
                    copilot_request,
                    auth_claims
                )
                
                return jsonify(result)
                
            except Exception as e:
                logger.error(f"Error in Copilot search: {e}", exc_info=True)
                return jsonify({"error": str(e)}), 500
        
        @self.app.route("/api/copilot/query", methods=["POST"])
        async def copilot_query():
            """Query endpoint for Copilot plugin."""
            try:
                if not self.agent_app:
                    return jsonify({"error": "Agent not initialized"}), 500
                
                body = await request.get_json()
                if not body:
                    return jsonify({"error": "Invalid request body"}), 400
                
                # Get auth claims
                auth_claims = {
                    "oid": body.get("userId", ""),
                    "tenant_id": body.get("tenantId", self.agent_app.config.tenant_id)
                }
                
                # Get Copilot handler
                from handlers.copilot_handler import CopilotHandler, CopilotRequest
                copilot_handler = CopilotHandler(
                    self.agent_app.rag_service,
                    self.agent_app.auth_service
                )
                
                # Create request
                copilot_request = CopilotRequest(
                    query=body.get("message", body.get("query", "")),
                    conversation_history=body.get("conversationHistory"),
                    max_results=body.get("maxResults", 5)
                )
                
                # Handle request
                result = await copilot_handler.handle_query_request(
                    copilot_request,
                    auth_claims
                )
                
                return jsonify(result)
                
            except Exception as e:
                logger.error(f"Error in Copilot query: {e}", exc_info=True)
                return jsonify({"error": str(e)}), 500
        
        @self.app.route("/api/messages", methods=["GET", "OPTIONS"])
        async def messages_options():
            """Handle OPTIONS for CORS preflight."""
            logger.info("OPTIONS request received for /api/messages")
            return "", 200
        
        @self.app.route("/api/messages", methods=["POST"])
        async def messages():
            """Main endpoint for Bot Framework messages."""
            # Force print to ensure it shows in console
            print(f"\n{'='*60}")
            print("[MESSAGES ENDPOINT] POST /api/messages RECEIVED")
            print(f"[MESSAGES ENDPOINT] Headers: {dict(request.headers)}")
            logger.info("=" * 50)
            logger.info("RECEIVED POST REQUEST TO /api/messages")
            logger.info(f"Headers: {dict(request.headers)}")
            
            # Generate simple correlation id for this request
            import uuid
            traceparent = uuid.uuid4().hex
            logger.info(f"traceparent={traceparent}")
            
            try:
                # Get the request body FIRST - before any initialization checks
                body = await request.get_json()
                if not body:
                    logger.error("Invalid request body - body is None")
                    return jsonify({"error": "Invalid request body"}), 400
                
                # Get channel ID from body for logging
                channel_id = body.get('channelId', 'unknown')
                logger.info(f"Received message on channel: {channel_id}")
                if not self.agent_app:
                    logger.error("Agent not initialized")
                    return jsonify({"error": "Agent not initialized"}), 500
                
                # Get the adapter from agent_app
                adapter = self.agent_app.get_adapter()
                if not adapter:
                    logger.error("Adapter not initialized")
                    return jsonify({"error": "Adapter not initialized"}), 500
                
                logger.info(f"Received activity type: {body.get('type', 'unknown')}, channel: {body.get('channelId', 'unknown')}")
                
                # Get auth header (required for Bot Framework authentication)
                # For emulator/testing without auth header, use empty string
                auth_header = request.headers.get("Authorization", "")
                
                logger.info(f"=== REQUEST DETAILS ===")
                logger.info(f"Channel ID from body: {channel_id}")
                logger.info(f"Auth header present: {bool(auth_header)}")
                if auth_header:
                    logger.info(f"Auth header (first 50 chars): {auth_header[:50]}...")
                else:
                    logger.warning("No Authorization header in request")
                
                # Create activity from request
                try:
                    activity = Activity().deserialize(body)
                    logger.info(f"Activity deserialized: type={activity.type}, channel_id={activity.channel_id}")
                    # Use channel_id from activity if available, fallback to body
                    channel_id = activity.channel_id if hasattr(activity, 'channel_id') and activity.channel_id else channel_id
                except Exception as e:
                    logger.error(f"Failed to deserialize activity: {e}", exc_info=True)
                    return jsonify({"error": f"Invalid activity format: {str(e)}"}), 400
                
                # Process the activity using the adapter
                async def logic(context):
                    try:
                        await self.agent_app.agent.on_turn(context)
                    except Exception as e:
                        logger.error(f"Error in agent.on_turn: {e}", exc_info=True)
                        raise
                
                try:
                    logger.info(f"Processing activity through adapter with auth_header present: {bool(auth_header)}")
                    response = await adapter.process_activity(
                        activity,
                        auth_header,
                        logic
                    )
                    logger.info(f"Activity processed successfully, response: {response is not None}")
                    
                    if response:
                        return jsonify(response.serialize())
                    else:
                        return "", 200
                except Exception as auth_error:
                    # Log the full error details
                    error_type = type(auth_error).__name__
                    error_message = str(auth_error)
                    logger.error(f"Adapter error type: {error_type}, message: {error_message}")
                    logger.error(f"Full error: {auth_error}", exc_info=True)
                    
                    # Check channel ID from the activity
                    channel_id_from_activity = getattr(activity, 'channel_id', 'unknown')
                    logger.info(f"Channel ID from activity: {channel_id_from_activity}")
                    
                    # Authentication error handling
                    # For local emulator only: Allow bypass for local development/testing
                    # For webchat and production channels: Require proper authentication
                    local_emulator_only = ["emulator"]
                    
                    if channel_id_from_activity in local_emulator_only:
                        # Only allow bypass for local Bot Framework Emulator
                        # This is safe because emulator runs locally and doesn't expose the service
                        logger.warning(f"Auth error for local emulator ({channel_id_from_activity}), attempting workaround: {auth_error}")
                        
                        try:
                            from botbuilder.core import TurnContext, BotAdapter
                            from botbuilder.schema import ConversationAccount, ChannelAccount
                            
                            # Ensure activity has required fields
                            if not hasattr(activity, 'conversation') or not activity.conversation:
                                activity.conversation = ConversationAccount(id="test-conv-id")
                            if not hasattr(activity, 'from_property') or not activity.from_property:
                                activity.from_property = ChannelAccount(id="test-user", name="Test User")
                            if not hasattr(activity, 'recipient') or not activity.recipient:
                                activity.recipient = ChannelAccount(id="bot", name="Bot")
                            
                            # Create a minimal adapter for local emulator only
                            class LocalEmulatorAdapter(BotAdapter):
                                """Adapter for local Bot Framework Emulator only - skips validation."""

                                async def send_activities(self, context, activities):
                                    responses = []
                                    for activity_to_send in activities:
                                        activity_id = getattr(activity_to_send, "id", None) or str(
                                            uuid.uuid4()
                                        )
                                        responses.append(ResourceResponse(id=activity_id))
                                    return responses

                                async def update_activity(self, context, activity_to_update):
                                    activity_id = getattr(activity_to_update, "id", None) or str(
                                        uuid.uuid4()
                                    )
                                    return ResourceResponse(id=activity_id)

                                async def delete_activity(self, context, reference: ConversationReference):
                                    logger.debug("Local emulator delete_activity called: %s", reference)
                                    return None
                            
                            local_adapter = LocalEmulatorAdapter()
                            turn_context = TurnContext(local_adapter, activity)
                            
                            # Call the agent's on_turn directly (only for local emulator)
                            await self.agent_app.agent.on_turn(turn_context)
                            
                            logger.info("Successfully processed activity via local emulator workaround")
                            return "", 200
                            
                        except Exception as direct_error:
                            logger.error(f"Local emulator processing failed: {direct_error}", exc_info=True)
                            return jsonify({
                                "error": "Authentication failed - check bot credentials",
                                "channel": channel_id_from_activity,
                                "details": str(direct_error)
                            }), 401
                    else:
                        # For webchat and production channels: Require proper authentication
                        # Webchat from Azure Portal should have valid bot credentials
                        logger.error(f"Authentication failed for channel ({channel_id_from_activity}): {auth_error}")
                        logger.error("This may indicate misconfigured bot credentials (MICROSOFT_APP_ID or MICROSOFT_APP_PASSWORD)")
                        
                        return jsonify({
                            "error": "Authentication required",
                            "channel": channel_id_from_activity,
                            "details": "Bot Framework authentication failed. Please verify MICROSOFT_APP_ID and MICROSOFT_APP_PASSWORD are configured correctly.",
                            "help": "For webchat: Ensure bot credentials are set in Azure Portal Bot Channels Registration"
                        }), 401
                except Exception as adapter_error:
                    logger.error(f"Adapter.process_activity failed: {adapter_error}", exc_info=True)
                    # Return more detailed error for debugging
                    import traceback
                    return jsonify({
                        "error": "Activity processing failed",
                        "details": str(adapter_error),
                        "type": type(adapter_error).__name__,
                        "traceback": traceback.format_exc()
                    }), 400
                
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                return jsonify({"error": str(e), "type": type(e).__name__}), 500
        
        @self.app.route("/api/health", methods=["GET"])
        async def health():
            """Detailed health check."""
            try:
                if not self.agent_app:
                    return jsonify({
                        "status": "unhealthy",
                        "error": "Agent not initialized"
                    }), 500
                
                # Check backend connectivity and latency
                import time
                import aiohttp
                backend_ok = False
                backend_latency_ms = None
                backend_status = None
                backend_url = f"{self.agent_app.config.backend_url}/config"
                t0 = time.time()
                try:
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as s:
                        async with s.get(backend_url) as r:
                            backend_status = r.status
                            backend_ok = r.status == 200
                except Exception as _:
                    backend_ok = False
                finally:
                    backend_latency_ms = int((time.time() - t0) * 1000)
                
                # Compose health payload
                health_status = {
                    "status": "healthy" if backend_ok else "degraded",
                    "agent": "initialized",
                    "services": {
                        "rag_service": "initialized",
                        "auth_service": "initialized",
                        "backend": {
                            "ok": backend_ok,
                            "status_code": backend_status,
                            "latency_ms": backend_latency_ms,
                            "url": backend_url
                        }
                    }
                }
                
                return jsonify(health_status)
                
            except Exception as e:
                logger.error(f"Error in health check: {e}")
                return jsonify({
                    "status": "unhealthy",
                    "error": str(e)
                }), 500
        
        @self.app.route("/api/config", methods=["GET"])
        async def config():
            """Get agent configuration (non-sensitive parts)."""
            try:
                if not self.agent_app:
                    return jsonify({"error": "Agent not initialized"}), 500
                
                config_info = {
                    "agent_name": self.agent_app.config.agent_name,
                    "agent_description": self.agent_app.config.agent_description,
                    "max_conversation_turns": self.agent_app.config.max_conversation_turns,
                    "channels": {
                        "teams": self.agent_app.config.enable_teams,
                        "copilot": self.agent_app.config.enable_copilot,
                        "web_chat": self.agent_app.config.enable_web_chat
                    }
                }
                
                return jsonify(config_info)
                
            except Exception as e:
                logger.error(f"Error getting config: {e}")
                return jsonify({"error": "Internal server error"}), 500
    
    async def initialize(self):
        """Initialize the agent application."""
        try:
            # Load configuration
            config = AgentConfig.from_environment()
            config.validate()
            
            # Initialize the agent application
            self.agent_app = AgentApplication(config)
            
            # Get the adapter
            self.adapter = self.agent_app.get_adapter()
            
            logger.info("Agent application initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent application: {e}")
            raise
    
    async def run(self, host: str = "0.0.0.0", port: int = None):
        """Run the agent server."""
        try:
            # Initialize the agent
            await self.initialize()
            
            # Get port from environment variable (Azure App Service uses PORT)
            if port is None:
                port = int(os.getenv("PORT", 8000))
            
            # Start the server
            logger.info(f"Starting agent server on {host}:{port}")
            await self.app.run_task(host=host, port=port)
            
        except Exception as e:
            logger.error(f"Failed to run agent server: {e}")
            raise


async def main():
    """Main function to start the agent server."""
    try:
        # Create and run the server
        server = AgentServer()
        await server.run()
        
    except KeyboardInterrupt:
        logger.info("Agent server stopped by user")
    except Exception as e:
        logger.error(f"Agent server failed: {e}")
        raise


if __name__ == "__main__":
    # Run the agent server
    asyncio.run(main())