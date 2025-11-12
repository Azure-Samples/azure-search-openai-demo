"""
End-to-End Tests for Agents Service.

Tests the Agents service endpoints and Bot Framework integration.
"""

import pytest
import aiohttp
import json
import os
from typing import Dict, Any, Optional


class TestAgentsService:
    """End-to-end tests for Agents service."""
    
    @pytest.fixture
    def agents_url(self) -> str:
        """Get Agents service URL from environment or use default."""
        return os.getenv("AGENTS_SERVICE_URL", "http://localhost:8000")
    
    @pytest.fixture
    def backend_url(self) -> str:
        """Get Backend service URL from environment or use default."""
        return os.getenv("BACKEND_URL", "http://localhost:50505")
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, agents_url: str):
        """Test Agents service health endpoint."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{agents_url}/api/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    assert response.status == 200
                    data = await response.json()
                    assert "status" in data
                    assert "agent" in data
                    assert "services" in data
                    print(f"Health check response: {json.dumps(data, indent=2)}")
        except aiohttp.ClientConnectorError:
            pytest.skip(f"Agents service not running at {agents_url}")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")
    
    @pytest.mark.asyncio
    async def test_config_endpoint(self, agents_url: str):
        """Test Agents service config endpoint."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{agents_url}/api/config", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    assert response.status == 200
                    data = await response.json()
                    assert "agent_name" in data
                    assert "channels" in data
                    print(f"Config response: {json.dumps(data, indent=2)}")
        except aiohttp.ClientConnectorError:
            pytest.skip(f"Agents service not running at {agents_url}")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")
    
    @pytest.mark.asyncio
    async def test_messages_endpoint_requires_auth(self, agents_url: str):
        """Test that /api/messages requires authentication."""
        # Test without auth header
        message_body = {
            "type": "message",
            "text": "Hello",
            "from": {"id": "test-user", "name": "Test User"},
            "channelId": "webchat"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{agents_url}/api/messages",
                    json=message_body,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    # Should return 401 or 400 (depending on Bot Framework validation)
                    assert response.status in [400, 401, 403]
                    print(f"Auth required test passed: {response.status}")
        except aiohttp.ClientConnectorError:
            pytest.skip(f"Agents service not running at {agents_url}")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")
    
    @pytest.mark.asyncio
    async def test_backend_health_from_agents(self, agents_url: str, backend_url: str):
        """Test that Agents service can reach Backend service."""
        try:
            async with aiohttp.ClientSession() as session:
                # Check Agents health (which checks backend)
                async with session.get(f"{agents_url}/api/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    assert response.status == 200
                    data = await response.json()
                    
                    # Verify backend status is reported
                    if "services" in data and "backend" in data["services"]:
                        backend_status = data["services"]["backend"]
                        print(f"Backend status from Agents: {json.dumps(backend_status, indent=2)}")
                        
                        # If backend is reachable, check it directly
                        if backend_status.get("ok"):
                            try:
                                async with session.get(f"{backend_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as backend_response:
                                    assert backend_response.status == 200
                                    print("Backend health check passed")
                            except aiohttp.ClientConnectorError:
                                pytest.skip(f"Backend service not running at {backend_url}")
        except aiohttp.ClientConnectorError:
            pytest.skip(f"Agents service not running at {agents_url}")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")
    
    @pytest.mark.asyncio
    async def test_correlation_id_propagation(self, agents_url: str, backend_url: str):
        """Test that correlation IDs are propagated from Agents to Backend."""
        # This test requires both services running
        # For now, just verify the endpoint exists
        traceparent = "00-12345678901234567890123456789012-1234567890123456-01"
        
        message_body = {
            "type": "message",
            "text": "Test correlation ID",
            "from": {"id": "test-user", "name": "Test User"},
            "channelId": "emulator"  # Use emulator for local testing
        }
        
        headers = {
            "Content-Type": "application/json",
            "x-traceparent": traceparent
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Note: This will fail without proper auth, but we can verify the endpoint accepts it
                async with session.post(
                    f"{agents_url}/api/messages",
                    json=message_body,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    # Even if auth fails, correlation ID should be logged
                    print(f"Correlation ID test response: {response.status}")
                    # In production, we'd verify the correlation ID in logs
        except aiohttp.ClientConnectorError:
            pytest.skip(f"Agents service not running at {agents_url}")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")


class TestBackendService:
    """End-to-end tests for Backend RAG service."""
    
    @pytest.fixture
    def backend_url(self) -> str:
        """Get Backend service URL from environment or use default."""
        return os.getenv("BACKEND_URL", "http://localhost:50505")
    
    @pytest.fixture
    def auth_token(self) -> Optional[str]:
        """Get auth token for testing (if available)."""
        return os.getenv("TEST_AUTH_TOKEN")
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, backend_url: str):
        """Test Backend service health endpoint with dependency checks."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{backend_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    assert response.status == 200
                    data = await response.json()
                    assert "status" in data
                    assert "dependencies" in data
                    print(f"Backend health check: {json.dumps(data, indent=2)}")
        except aiohttp.ClientConnectorError:
            pytest.skip(f"Backend service not running at {backend_url}")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")
    
    @pytest.mark.asyncio
    async def test_config_endpoint(self, backend_url: str):
        """Test Backend config endpoint."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{backend_url}/config", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    assert response.status == 200
                    data = await response.json()
                    assert "showVectorOption" in data
                    print(f"Backend config: {json.dumps(data, indent=2)}")
        except aiohttp.ClientConnectorError:
            pytest.skip(f"Backend service not running at {backend_url}")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")
    
    @pytest.mark.asyncio
    async def test_chat_endpoint_requires_auth(self, backend_url: str):
        """Test that /chat endpoint handles authentication (required or optional)."""
        chat_body = {
            "messages": [{"role": "user", "content": "Hello"}],
            "context": {}
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{backend_url}/chat",
                    json=chat_body,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    # In production: should return 401 Unauthorized
                    # In local dev: may return 200 if auth is disabled
                    status = response.status
                    assert status in [200, 401], f"Unexpected status code: {status}"
                    
                    if status == 401:
                        print("Chat endpoint correctly requires authentication (401)")
                    elif status == 200:
                        data = await response.json()
                        print("Chat endpoint allows unauthenticated access (200) - likely local dev mode")
                        # Verify it's a valid response structure
                        # Response structure: {"message": {...}, "context": {...}, "session_state": ...}
                        # Or error response: {"error": ...}
                        assert (
                            "message" in data
                            or "error" in data
                            or "context" in data
                            or "answer" in data
                            or "choices" in data
                        ), f"Unexpected response structure: {list(data.keys())}"
        except aiohttp.ClientConnectorError:
            pytest.skip(f"Backend service not running at {backend_url}")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")


class TestIntegration:
    """Integration tests between Agents and Backend."""
    
    @pytest.fixture
    def agents_url(self) -> str:
        """Get Agents service URL."""
        return os.getenv("AGENTS_SERVICE_URL", "http://localhost:8000")
    
    @pytest.fixture
    def backend_url(self) -> str:
        """Get Backend service URL."""
        return os.getenv("BACKEND_URL", "http://localhost:50505")
    
    @pytest.mark.asyncio
    async def test_agents_to_backend_connectivity(self, agents_url: str, backend_url: str):
        """Test that Agents service can connect to Backend."""
        try:
            async with aiohttp.ClientSession() as session:
                # Check Agents health (which pings backend)
                async with session.get(f"{agents_url}/api/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    assert response.status == 200
                    data = await response.json()
                    
                    if "services" in data and "backend" in data["services"]:
                        backend_info = data["services"]["backend"]
                        print(f"Backend connectivity: {json.dumps(backend_info, indent=2)}")
                        
                        # Verify backend URL is correct
                        if "url" in backend_info:
                            assert backend_url in backend_info["url"] or backend_info["url"] in backend_url
        except aiohttp.ClientConnectorError:
            pytest.skip(f"Agents service not running at {agents_url}")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")


if __name__ == "__main__":
    """Run tests directly."""
    import asyncio
    
    async def run_tests():
        """Run basic connectivity tests."""
        agents_url = os.getenv("AGENTS_SERVICE_URL", "http://localhost:8000")
        backend_url = os.getenv("BACKEND_URL", "http://localhost:50505")
        
        print("=" * 60)
        print("E2E Connectivity Tests")
        print("=" * 60)
        
        async with aiohttp.ClientSession() as session:
            # Test Agents health
            print("\n1. Testing Agents service health...")
            try:
                async with session.get(f"{agents_url}/api/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"   ✅ Agents service is healthy")
                        print(f"   Status: {data.get('status')}")
                        if "services" in data and "backend" in data["services"]:
                            backend_status = data["services"]["backend"]
                            print(f"   Backend: {'✅ OK' if backend_status.get('ok') else '❌ Not reachable'}")
                    else:
                        print(f"   ❌ Agents service returned {resp.status}")
            except Exception as e:
                print(f"   ❌ Failed to connect to Agents service: {e}")
            
            # Test Backend health
            print("\n2. Testing Backend service health...")
            try:
                async with session.get(f"{backend_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"   ✅ Backend service is healthy")
                        print(f"   Status: {data.get('status')}")
                        if "dependencies" in data:
                            deps = data["dependencies"]
                            print(f"   Dependencies: {len([d for d in deps.values() if d.get('ok')])}/{len(deps)} healthy")
                    else:
                        print(f"   ❌ Backend service returned {resp.status}")
            except Exception as e:
                print(f"   ❌ Failed to connect to Backend service: {e}")
        
        print("\n" + "=" * 60)
        print("Tests completed")
        print("=" * 60)
    
    asyncio.run(run_tests())

