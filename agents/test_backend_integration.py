"""
Test script for backend integration.
This script tests the agent's ability to call the existing backend API.
"""

import asyncio
import logging
import os
from typing import Dict, Any

from config.agent_config import AgentConfig
from services.rag_service import RAGService, RAGRequest


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_backend_integration():
    """Test the backend integration."""
    try:
        # Load configuration
        config = AgentConfig.from_environment()
        
        # Set dummy values for testing
        config.app_id = "test-app-id"
        config.app_password = "test-app-password"
        config.tenant_id = "test-tenant-id"
        config.client_id = "test-client-id"
        config.client_secret = "test-client-secret"
        
        config.validate()
        
        logger.info(f"Testing backend integration with: {config.backend_url}")
        
        # Initialize RAG service
        rag_service = RAGService(config)
        await rag_service.initialize()
        
        # Test 1: Simple chat request
        logger.info("Test 1: Simple chat request")
        request = RAGRequest(
            message="What are the main benefits mentioned in the policy document?",
            conversation_history=[],
            user_id="test-user-123",
            channel_id="test-channel"
        )
        
        response = await rag_service.process_query(request)
        logger.info(f"Response: {response.answer}")
        logger.info(f"Sources: {len(response.sources)}")
        logger.info(f"Citations: {len(response.citations)}")
        logger.info(f"Thoughts: {len(response.thoughts)}")
        
        # Test 2: Chat with conversation history
        logger.info("\nTest 2: Chat with conversation history")
        request_with_history = RAGRequest(
            message="Can you provide more details about the first benefit?",
            conversation_history=[
                {"role": "user", "content": "What are the main benefits mentioned in the policy document?"},
                {"role": "assistant", "content": response.answer}
            ],
            user_id="test-user-123",
            channel_id="test-channel"
        )
        
        response_with_history = await rag_service.process_query(request_with_history)
        logger.info(f"Response with history: {response_with_history.answer}")
        
        # Test 3: Streaming request
        logger.info("\nTest 3: Streaming request")
        async for chunk in rag_service.process_query_stream(request):
            logger.info(f"Stream chunk: {chunk}")
            if chunk.get("type") == "error":
                break
        
        logger.info("✅ All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise
    finally:
        # Clean up
        if 'rag_service' in locals():
            await rag_service.close()


async def test_backend_health():
    """Test if the backend is healthy."""
    import aiohttp
    
    try:
        config = AgentConfig.from_environment()
        
        async with aiohttp.ClientSession() as session:
            # Test health endpoint
            async with session.get(f"{config.backend_url}/") as response:
                if response.status == 200:
                    logger.info("✅ Backend health check passed")
                    return True
                else:
                    logger.error(f"❌ Backend health check failed: {response.status}")
                    return False
                    
    except Exception as e:
        logger.error(f"❌ Backend health check error: {e}")
        return False


async def main():
    """Main test function."""
    logger.info("Starting backend integration tests...")
    
    # Test 1: Backend health
    logger.info("Step 1: Testing backend health...")
    backend_healthy = await test_backend_health()
    
    if not backend_healthy:
        logger.error("Backend is not healthy. Please start the backend first.")
        logger.info("To start the backend, run: cd /workspace/app/backend && python main.py")
        return
    
    # Test 2: Backend integration
    logger.info("Step 2: Testing backend integration...")
    await test_backend_integration()
    
    logger.info("🎉 All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())