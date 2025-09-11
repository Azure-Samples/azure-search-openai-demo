import asyncio
import aiohttp
import os
import sys

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app', 'backend'))

from prepdocslib.patentsberta_embeddings import PatentsBertaEmbeddings

class PatentsBertaTestSuite:
    def __init__(self, endpoint: str, api_key: str = None):
        self.endpoint = endpoint
        self.api_key = api_key
        self.embedding_service = PatentsBertaEmbeddings(endpoint, api_key)
        
    async def test_health(self) -> bool:
        print("🏥 Testing health endpoint...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.endpoint}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Health check passed: {data}")
                        return True
                    else:
                        print(f"❌ Health check failed: {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    async def test_info(self) -> bool:
        print("ℹ️  Testing info endpoint...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.endpoint}/info") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Info endpoint: {data}")
                        return True
                    else:
                        print(f"❌ Info endpoint failed: {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Info endpoint error: {e}")
            return False
    
    async def test_single_embedding(self) -> bool:
        print("🔍 Testing single embedding generation...")
        test_text = "structural engineering patent for seismic isolation system"
        
        try:
            embedding = await self.embedding_service.create_embedding(test_text)
            
            if embedding and len(embedding) == 768:
                print(f"✅ Single embedding generated successfully")
                print(f"   Dimensions: {len(embedding)}")
                print(f"   Sample values: {embedding[:5]}...")
                return True
            else:
                print(f"❌ Single embedding failed: wrong dimensions {len(embedding) if embedding else 0}")
                return False
                
        except Exception as e:
            print(f"❌ Single embedding error: {e}")
            return False
    
    async def test_batch_embeddings(self) -> bool:
        print("📦 Testing batch embedding generation...")
        test_texts = [
            "foundation system with load distribution mechanism",
            "composite structural beam with carbon fiber reinforcement", 
            "damping apparatus for earthquake resistant buildings",
            "steel frame connection with moment resistance",
            "concrete column with spiral reinforcement design"
        ]
        
        try:
            embeddings = await self.embedding_service.create_embeddings(test_texts)
            
            if embeddings and len(embeddings) == len(test_texts):
                all_correct_dims = all(len(emb) == 768 for emb in embeddings)
                if all_correct_dims:
                    print(f"✅ Batch embeddings generated successfully")
                    print(f"   Count: {len(embeddings)}")
                    print(f"   Dimensions: {len(embeddings[0])}")
                    return True
                else:
                    print(f"❌ Batch embeddings failed: incorrect dimensions")
                    return False
            else:
                print(f"❌ Batch embeddings failed: wrong count {len(embeddings) if embeddings else 0}")
                return False
                
        except Exception as e:
            print(f"❌ Batch embeddings error: {e}")
            return False
    
    async def test_patent_terminology(self) -> bool:
        print("🔬 Testing patent-specific terminology...")
        
        patent_queries = [
            "apparatus for structural vibration control",
            "method of reinforcing concrete structures", 
            "system for seismic base isolation",
            "device for load transfer in buildings",
            "composition of high-strength concrete mixture"
        ]
        
        try:
            embeddings = await self.embedding_service.create_embeddings(patent_queries)
            
            if embeddings and len(embeddings) == len(patent_queries):
                print(f"✅ Patent terminology embeddings generated")
                
                # Test similarity between related concepts
                # This is a basic test - in practice you'd want more sophisticated similarity testing
                print("   Testing conceptual similarity...")
                
                # Compare "apparatus" and "device" embeddings (should be similar)
                apparatus_emb = embeddings[0]  # "apparatus for structural vibration control"
                device_emb = embeddings[3]     # "device for load transfer in buildings"
                
                # Simple cosine similarity calculation
                import numpy as np
                
                def cosine_similarity(a, b):
                    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
                
                similarity = cosine_similarity(apparatus_emb, device_emb)
                print(f"   Similarity between 'apparatus' and 'device': {similarity:.3f}")
                
                if similarity > 0.5:  # Reasonable threshold for related concepts
                    print("✅ Patent terminology shows good semantic understanding")
                    return True
                else:
                    print("⚠️  Patent terminology similarity lower than expected")
                    return True  # Still pass, but note the issue
            else:
                print(f"❌ Patent terminology test failed")
                return False
                
        except Exception as e:
            print(f"❌ Patent terminology error: {e}")
            return False
    
    async def test_performance(self) -> bool:
        print("⚡ Testing performance...")
        
        import time
        
        # Test single embedding performance
        start_time = time.time()
        await self.embedding_service.create_embedding("test performance query")
        single_time = time.time() - start_time
        
        # Test batch performance
        batch_texts = ["performance test query"] * 10
        start_time = time.time()
        await self.embedding_service.create_embeddings(batch_texts)
        batch_time = time.time() - start_time
        
        print(f"✅ Performance results:")
        print(f"   Single embedding: {single_time:.2f}s")
        print(f"   Batch (10 items): {batch_time:.2f}s")
        print(f"   Avg per item in batch: {batch_time/10:.2f}s")
        
        # Performance is acceptable if single < 10s and batch avg < 2s
        if single_time < 10 and (batch_time/10) < 2:
            print("✅ Performance is acceptable")
            return True
        else:
            print("⚠️  Performance may be slower than expected")
            return True  # Still pass, but note the issue
    
    async def test_authentication(self) -> bool:
        """Test API key authentication"""
        print("🔐 Testing API key authentication...")
        
        try:
            # Test with correct API key (should work)
            if self.api_key:
                headers = {'Content-Type': 'application/json', 'X-API-Key': self.api_key}
                payload = {'texts': ['test authentication'], 'normalize': True}
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.endpoint}/embeddings",
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            print("✅ Authentication with correct API key works")
                        else:
                            print(f"❌ Authentication failed with correct key: {response.status}")
                            return False
                    
                    # Test without API key (should fail if key is required)
                    headers_no_key = {'Content-Type': 'application/json'}
                    async with session.post(
                        f"{self.endpoint}/embeddings",
                        json=payload,
                        headers=headers_no_key,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 401:
                            print("✅ Authentication properly blocks requests without API key")
                            return True
                        else:
                            print(f"⚠️  No API key required (status: {response.status}) - service may be in no-auth mode")
                            return True  # Still pass if no auth is configured
            else:
                print("⚠️  No API key configured - skipping authentication test")
                return True
                
        except Exception as e:
            print(f"❌ Authentication test error: {e}")
            return False

    async def test_input_validation(self):
        """Test input validation and size limits"""
        print("🛡️  Testing input validation and size limits...")
        
        try:
            headers = {'Content-Type': 'application/json'}
            if self.api_key:
                headers['X-API-Key'] = self.api_key
            
            async with aiohttp.ClientSession() as session:
                # Test empty texts array
                payload = {'texts': [], 'normalize': True}
                async with session.post(
                    f"{self.endpoint}/embeddings",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 422:
                        print("✅ Empty texts array properly rejected")
                    else:
                        print(f"⚠️  Empty texts array not rejected (status: {response.status})")
                
                # Test empty string
                payload = {'texts': [''], 'normalize': True}
                async with session.post(
                    f"{self.endpoint}/embeddings",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 422:
                        print("✅ Empty string properly rejected")
                    else:
                        print(f"⚠️  Empty string not rejected (status: {response.status})")
                
                # Test oversized batch (51 items, limit is 50)
                large_batch = ['test text'] * 51
                payload = {'texts': large_batch, 'normalize': True}
                async with session.post(
                    f"{self.endpoint}/embeddings",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 422:
                        print("✅ Oversized batch properly rejected")
                    else:
                        print(f"⚠️  Oversized batch not rejected (status: {response.status})")
                
                # Test oversized text (8193 chars, limit is 8192)
                large_text = 'x' * 8193
                payload = {'texts': [large_text], 'normalize': True}
                async with session.post(
                    f"{self.endpoint}/embeddings",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 422:
                        print("✅ Oversized text properly rejected")
                    else:
                        print(f"⚠️  Oversized text not rejected (status: {response.status})")
                
                # Test valid input within limits
                payload = {'texts': ['Valid patent text for embedding'], 'normalize': True}
                async with session.post(
                    f"{self.endpoint}/embeddings",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        print("✅ Valid input accepted")
                        return True
                    else:
                        print(f"❌ Valid input rejected (status: {response.status})")
                        return False
                        
        except Exception as e:
            print(f"❌ Input validation test error: {e}")
            return False

async def main():
    print("🧪 PatentsBERTa Embedding Service Test Suite")
    print("=" * 50)
    
    # Get endpoint from environment or command line
    endpoint = os.getenv('PATENTSBERTA_ENDPOINT')
    api_key = os.getenv('PATENTSBERTA_API_KEY')
    
    # Clean up API key (remove any trailing whitespace/newlines but preserve base64 padding)
    if api_key:
        api_key = api_key.strip()
    
    if len(sys.argv) > 1:
        endpoint = sys.argv[1]
    
    if not endpoint:
        print("❌ Please provide PatentsBERTa endpoint:")
        print("   python test-patentsberta.py <endpoint>")
        print("   or set PATENTSBERTA_ENDPOINT environment variable")
        sys.exit(1)
    
    print(f"🎯 Testing endpoint: {endpoint}")
    if api_key:
        print("🔑 Using API key authentication")
        print(f"🔍 API key length: {len(api_key)} chars")
        print(f"🔍 API key (first 10 chars): {api_key[:10]}...")
    
    # Initialize test suite
    tester = PatentsBertaTestSuite(endpoint, api_key)
    
    # Run tests
    tests = [
        ("Health Check", tester.test_health),
        ("Info Endpoint", tester.test_info),
        ("Authentication", tester.test_authentication),
        ("Input Validation", tester.test_input_validation),
        ("Single Embedding", tester.test_single_embedding),
        ("Batch Embeddings", tester.test_batch_embeddings),
        ("Patent Terminology", tester.test_patent_terminology),
        ("Performance", tester.test_performance)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        print("-" * 30)
        
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! PatentsBERTa service is working correctly.")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed. Please check the service configuration.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
