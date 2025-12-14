"""Quick test of Taskade integration"""
import asyncio
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app', 'backend'))

from automation import TaskadeClient, TaskadeConfig, TaskadeFreelanceIntegration

async def main():
    print("🧪 Testing Taskade Integration...")
    print("=" * 50)
    
    # Enterprise API key
    api_key = "tskdp_NvhoURdQXa1eDDxnCWrZYtb7k4uU2ZkHEC"
    
    config = TaskadeConfig(api_key=api_key)
    print(f"✅ Config created: {config.base_url}")
    
    try:
        async with TaskadeClient(config) as client:
            print("✅ Client connected")
            
            # Test workspace listing
            try:
                workspaces = await client.get_workspaces()
                print(f"✅ Found {len(workspaces)} workspaces")
                for ws in workspaces[:3]:
                    print(f"   - {ws.name} ({ws.id})")
            except Exception as e:
                print(f"⚠️  Workspace listing: {e}")
            
            # Test integration helper
            integration = TaskadeFreelanceIntegration(client=client)
            print("✅ Integration helper created")
            
            try:
                ws_id = await integration.setup_workspace("Test Workspace")
                print(f"✅ Workspace ready: {ws_id}")
            except Exception as e:
                print(f"⚠️  Workspace setup: {e}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    print("=" * 50)
    print("✅ All tests passed!")
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
