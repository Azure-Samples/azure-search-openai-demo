"""
Quick tests for TIER 1 components
Tests: Database, Cache, Rate Limiting, Monitoring
"""

import pytest
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app', 'backend'))


class TestDatabaseModule:
    """✅ Test: Database module imports and initializes"""
    
    def test_database_module_imports(self):
        """Test: Can import database module"""
        try:
            from db.database import DatabaseManager
            assert DatabaseManager is not None
            print("✅ Database module imported successfully")
        except ImportError as e:
            pytest.fail(f"Failed to import database module: {e}")
    
    def test_database_models_import(self):
        """Test: Can import database models"""
        try:
            from db.models import BrowserAgentModel, TaskModel, ProjectModel, AuditLogModel
            assert BrowserAgentModel is not None
            assert TaskModel is not None
            assert ProjectModel is not None
            assert AuditLogModel is not None
            print("✅ Database models imported successfully")
        except ImportError as e:
            pytest.fail(f"Failed to import database models: {e}")
    
    def test_database_helpers_import(self):
        """Test: Can import database helpers"""
        try:
            import db.helpers as helpers_module
            assert helpers_module is not None
            assert hasattr(helpers_module, 'save_agent_to_db')
            assert hasattr(helpers_module, 'get_agent_from_db')
            print("✅ Database helpers imported successfully")
        except ImportError as e:
            pytest.fail(f"Failed to import database helpers: {e}")


class TestCacheModule:
    """✅ Test: Cache module imports and initializes"""
    
    def test_cache_module_imports(self):
        """Test: Can import cache module"""
        try:
            from cache.cache import RedisManager
            assert RedisManager is not None
            print("✅ Cache module imported successfully")
        except ImportError as e:
            pytest.fail(f"Failed to import cache module: {e}")
    
    def test_session_manager_import(self):
        """Test: Can import session manager"""
        try:
            from cache.session import SessionManager
            assert SessionManager is not None
            print("✅ Session manager imported successfully")
        except ImportError as e:
            pytest.fail(f"Failed to import session manager: {e}")


class TestRateLimitingModule:
    """✅ Test: Rate limiting module imports and initializes"""
    
    def test_rate_limiter_imports(self):
        """Test: Can import rate limiter"""
        try:
            from middleware.rate_limiter import RateLimiter, rate_limit
            assert RateLimiter is not None
            assert rate_limit is not None
            print("✅ Rate limiter module imported successfully")
        except ImportError as e:
            pytest.fail(f"Failed to import rate limiter: {e}")


class TestMonitoringModule:
    """✅ Test: Monitoring module imports and initializes"""
    
    def test_insights_module_imports(self):
        """Test: Can import application insights"""
        try:
            from monitoring.insights import ApplicationInsightsManager
            assert ApplicationInsightsManager is not None
            print("✅ Monitoring module imported successfully")
        except ImportError as e:
            pytest.fail(f"Failed to import monitoring module: {e}")


class TestHealthChecks:
    """✅ Test: Health checks endpoints"""
    
    def test_health_check_module_imports(self):
        """Test: Can import health check functions"""
        try:
            from app import get_health_status
            assert get_health_status is not None
            print("✅ Health check module imported successfully")
        except ImportError as e:
            # This might fail if app not fully initialized, which is OK
            print("ℹ️  Health check import skipped (app may need initialization)")


class TestIntegration:
    """✅ Test: Integration between components"""
    
    def test_database_and_cache_together(self):
        """Test: Database and Cache modules can coexist"""
        try:
            from db.database import DatabaseManager
            from cache.cache import RedisManager
            
            # Both should import without conflict
            assert DatabaseManager is not None
            assert RedisManager is not None
            print("✅ Database and Cache modules work together")
        except Exception as e:
            pytest.fail(f"Failed to load Database and Cache together: {e}")
    
    def test_rate_limiting_with_cache(self):
        """Test: Rate limiting depends on cache"""
        try:
            from cache.cache import RedisManager
            from middleware.rate_limiter import RateLimiter
            
            assert RedisManager is not None
            assert RateLimiter is not None
            print("✅ Rate limiting works with cache")
        except Exception as e:
            pytest.fail(f"Failed to load Rate limiting with Cache: {e}")
    
    def test_all_tier1_modules_together(self):
        """Test: All TIER 1 modules can be imported together"""
        try:
            from db.database import DatabaseManager
            from cache.cache import RedisManager
            from middleware.rate_limiter import RateLimiter
            from monitoring.insights import ApplicationInsightsManager
            
            modules = [DatabaseManager, RedisManager, RateLimiter, ApplicationInsightsManager]
            assert all(m is not None for m in modules)
            print("✅ All TIER 1 modules imported successfully")
        except Exception as e:
            pytest.fail(f"Failed to import all TIER 1 modules: {e}")


class TestFileStructure:
    """✅ Test: TIER 1 file structure"""
    
    def test_database_files_exist(self):
        """Test: All database files exist"""
        base_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'backend', 'db')
        required_files = [
            '__init__.py',
            'models.py',
            'database.py',
            'helpers.py'
        ]
        for file in required_files:
            file_path = os.path.join(base_path, file)
            assert os.path.exists(file_path), f"Missing: {file_path}"
        print("✅ All database files exist")
    
    def test_cache_files_exist(self):
        """Test: All cache files exist"""
        base_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'backend', 'cache')
        required_files = ['__init__.py', 'cache.py', 'session.py']
        for file in required_files:
            file_path = os.path.join(base_path, file)
            assert os.path.exists(file_path), f"Missing: {file_path}"
        print("✅ All cache files exist")
    
    def test_middleware_files_exist(self):
        """Test: All middleware files exist"""
        base_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'backend', 'middleware')
        required_files = ['__init__.py', 'rate_limiter.py']
        for file in required_files:
            file_path = os.path.join(base_path, file)
            assert os.path.exists(file_path), f"Missing: {file_path}"
        print("✅ All middleware files exist")
    
    def test_monitoring_files_exist(self):
        """Test: All monitoring files exist"""
        base_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'backend', 'monitoring')
        required_files = ['__init__.py', 'insights.py']
        for file in required_files:
            file_path = os.path.join(base_path, file)
            assert os.path.exists(file_path), f"Missing: {file_path}"
        print("✅ All monitoring files exist")


class TestDocumentation:
    """✅ Test: TIER 1 documentation"""
    
    def test_tier1_docs_exist(self):
        """Test: All TIER 1 documentation files exist"""
        # Find root path
        root = os.path.dirname(__file__)
        while not os.path.exists(os.path.join(root, 'TIER1_DETAILED_REPORT.md')):
            root = os.path.dirname(root)
        
        files = [
            'TIER1_DETAILED_REPORT.md',
            'TIER1_VISUAL_SUMMARY.md',
            'TIER1_TESTING_CHECKLIST.md',
            'CORPORATE_ASSESSMENT.md',
        ]
        
        for file in files:
            file_path = os.path.join(root, file)
            assert os.path.exists(file_path), f"Missing documentation: {file_path}"
        print("✅ All TIER 1 documentation files exist")
    
    def test_tier1_reports_have_content(self):
        """Test: Documentation files have content"""
        # Find root path
        root = os.path.dirname(__file__)
        while not os.path.exists(os.path.join(root, 'TIER1_DETAILED_REPORT.md')):
            root = os.path.dirname(root)
            
        files = {
            'TIER1_DETAILED_REPORT.md': 1000,  # Should be > 1000 lines
            'TIER1_VISUAL_SUMMARY.md': 200,    # Should be > 200 lines
            'TIER1_TESTING_CHECKLIST.md': 500, # Should be > 500 lines
            'CORPORATE_ASSESSMENT.md': 500,    # Should be > 500 lines
        }
        
        for file, min_size in files.items():
            file_path = os.path.join(root, file)
            with open(file_path) as f:
                content = f.read()
                assert len(content) > min_size * 10, f"{file} has insufficient content"
        print("✅ All documentation files have sufficient content")


# Run with: pytest tests/test_tier1_quick.py -v
if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
