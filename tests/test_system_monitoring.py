"""
Integration tests for system monitoring and health check endpoints
"""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from datetime import datetime
import time

from main import app
from models.responses import ErrorResponse


class TestSystemHealthEndpoint:
    """Test system health check endpoint"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_health_check_success(self, client):
        """Test successful health check with all components healthy"""
        with patch('cache.manager.cache_manager.is_initialized') as mock_is_initialized, \
             patch('main.SessionLocal') as mock_session_local:
            
            mock_is_initialized.return_value = True
            
            # Mock database session
            mock_db = Mock()
            mock_session_local.return_value = mock_db
            mock_db.execute.return_value = None
            mock_db.close.return_value = None
            
            response = client.get("/api/v1/system/health")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert data["status"] == "healthy"
            assert "timestamp" in data
            assert data["version"] == "1.0.0"
            
            # Verify components
            assert "components" in data
            assert "cache" in data["components"]
            assert "database" in data["components"]
            
            # Verify cache component
            cache_component = data["components"]["cache"]
            assert cache_component["status"] == "healthy"
            assert cache_component["initialized"] is True
            
            # Verify database component
            db_component = data["components"]["database"]
            assert db_component["status"] == "healthy"
            assert db_component["error"] is None
    
    def test_health_check_cache_unhealthy(self, client):
        """Test health check when cache is not initialized"""
        with patch('cache.manager.cache_manager.is_initialized') as mock_is_initialized, \
             patch('main.SessionLocal') as mock_session_local:
            
            mock_is_initialized.return_value = False
            
            # Mock database session (healthy)
            mock_db = Mock()
            mock_session_local.return_value = mock_db
            mock_db.execute.return_value = None
            mock_db.close.return_value = None
            
            response = client.get("/api/v1/system/health")
            
            assert response.status_code == 503
            data = response.json()
            
            assert data["status"] == "unhealthy"
            assert data["components"]["cache"]["status"] == "unhealthy"
            assert data["components"]["cache"]["initialized"] is False
            assert data["components"]["database"]["status"] == "healthy"
    
    def test_health_check_database_unhealthy(self, client):
        """Test health check when database is unhealthy"""
        with patch('cache.manager.cache_manager.is_initialized') as mock_is_initialized, \
             patch('main.SessionLocal') as mock_session_local:
            
            mock_is_initialized.return_value = True
            
            # Mock database session failure
            mock_db = Mock()
            mock_session_local.return_value = mock_db
            mock_db.execute.side_effect = Exception("Database connection failed")
            mock_db.close.return_value = None
            
            response = client.get("/api/v1/system/health")
            
            assert response.status_code == 503
            data = response.json()
            
            assert data["status"] == "unhealthy"
            assert data["components"]["cache"]["status"] == "healthy"
            assert data["components"]["database"]["status"] == "unhealthy"
            assert "Database connection failed" in data["components"]["database"]["error"]
    
    def test_health_check_both_unhealthy(self, client):
        """Test health check when both cache and database are unhealthy"""
        with patch('cache.manager.cache_manager.is_initialized') as mock_is_initialized, \
             patch('main.SessionLocal') as mock_session_local:
            
            mock_is_initialized.return_value = False
            
            # Mock database session failure
            mock_db = Mock()
            mock_session_local.return_value = mock_db
            mock_db.execute.side_effect = Exception("Database connection failed")
            mock_db.close.return_value = None
            
            response = client.get("/api/v1/system/health")
            
            assert response.status_code == 503
            data = response.json()
            
            assert data["status"] == "unhealthy"
            assert data["components"]["cache"]["status"] == "unhealthy"
            assert data["components"]["database"]["status"] == "unhealthy"


class TestSystemMetricsEndpoint:
    """Test system metrics endpoint"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_metrics_success(self, client):
        """Test successful metrics retrieval"""
        mock_cache_stats = {
            "initialized": True,
            "initialization_time": 2.5,
            "posts_count": 150,
            "users_count": 75,
            "comments_count": 300,
            "tags_count": 25,
            "surveys_count": 10,
            "likes_count": 500,
            "bookmarks_count": 200,
            "follows_count": 100
        }
        
        mock_performance_stats = {
            "total_requests": 1000,
            "average_response_time_ms": 85.5,
            "total_response_time": 85.5
        }
        
        with patch('cache.manager.cache_manager.is_initialized') as mock_is_initialized, \
             patch('cache.manager.cache_manager.get_cache_stats') as mock_get_cache_stats, \
             patch('cache.manager.cache_manager.get_performance_stats') as mock_get_perf_stats:
            
            mock_is_initialized.return_value = True
            mock_get_cache_stats.return_value = mock_cache_stats
            mock_get_perf_stats.return_value = mock_performance_stats
            
            response = client.get("/api/v1/system/metrics")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "timestamp" in data
            assert "cache" in data
            assert "performance" in data
            assert "system" in data
            
            # Verify cache metrics
            cache_data = data["cache"]
            assert cache_data["status"] == "initialized"
            assert cache_data["initialization_time_seconds"] == 2.5
            
            data_counts = cache_data["data_counts"]
            assert data_counts["posts"] == 150
            assert data_counts["users"] == 75
            assert data_counts["comments"] == 300
            assert data_counts["tags"] == 25
            assert data_counts["surveys"] == 10
            assert data_counts["likes"] == 500
            assert data_counts["bookmarks"] == 200
            assert data_counts["follows"] == 100
            
            # Verify performance metrics
            perf_data = data["performance"]
            assert perf_data["total_requests"] == 1000
            assert perf_data["average_response_time_ms"] == 85.5
            assert perf_data["total_response_time_seconds"] == 85.5
            
            # Verify system metrics
            system_data = data["system"]
            assert system_data["status"] == "operational"
            assert system_data["version"] == "1.0.0"
            assert "uptime" in system_data
            
            uptime = system_data["uptime"]
            assert "seconds" in uptime
            assert "hours" in uptime
            assert "days" in uptime
            assert isinstance(uptime["seconds"], (int, float))
            assert isinstance(uptime["hours"], (int, float))
            assert isinstance(uptime["days"], (int, float))
    
    def test_metrics_cache_not_initialized(self, client):
        """Test metrics endpoint when cache is not initialized"""
        with patch('cache.manager.cache_manager.is_initialized') as mock_is_initialized:
            mock_is_initialized.return_value = False
            
            response = client.get("/api/v1/system/metrics")
            
            assert response.status_code == 503
            data = response.json()
            
            assert data["error_code"] == "SERVICE_UNAVAILABLE"
            assert "cache" in data["message"].lower()
    
    def test_metrics_uptime_calculation(self, client):
        """Test that uptime is calculated correctly"""
        mock_cache_stats = {
            "initialized": True,
            "initialization_time": 1.0,
            "posts_count": 10,
            "users_count": 5,
            "comments_count": 20,
            "tags_count": 3,
            "surveys_count": 2,
            "likes_count": 15,
            "bookmarks_count": 8,
            "follows_count": 12
        }
        
        mock_performance_stats = {
            "total_requests": 100,
            "average_response_time_ms": 50.0,
            "total_response_time": 5.0
        }
        
        with patch('cache.manager.cache_manager.is_initialized') as mock_is_initialized, \
             patch('cache.manager.cache_manager.get_cache_stats') as mock_get_cache_stats, \
             patch('cache.manager.cache_manager.get_performance_stats') as mock_get_perf_stats:
            
            mock_is_initialized.return_value = True
            mock_get_cache_stats.return_value = mock_cache_stats
            mock_get_perf_stats.return_value = mock_performance_stats
            
            # Make a request to get metrics
            response = client.get("/api/v1/system/metrics")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify uptime structure and reasonable values
            uptime = data["system"]["uptime"]
            assert "seconds" in uptime
            assert "hours" in uptime
            assert "days" in uptime
            
            # Uptime should be positive and reasonable (less than a day for tests)
            assert uptime["seconds"] >= 0
            assert uptime["hours"] >= 0
            assert uptime["days"] >= 0
            assert uptime["seconds"] < 86400  # Less than 24 hours
            
            # Verify relationships between time units
            assert abs(uptime["hours"] - uptime["seconds"] / 3600) < 0.01
            assert abs(uptime["days"] - uptime["hours"] / 24) < 0.01


class TestRequestLoggingMiddleware:
    """Test request logging middleware functionality"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_request_logging_headers(self, client):
        """Test that response time header is added"""
        with patch('cache.manager.cache_manager.is_initialized') as mock_is_initialized:
            mock_is_initialized.return_value = True
            
            response = client.get("/")
            
            # Check that response time header is present
            assert "X-Response-Time" in response.headers
            response_time_header = response.headers["X-Response-Time"]
            assert response_time_header.endswith("s")
            
            # Verify it's a valid time format
            time_value = float(response_time_header[:-1])
            assert time_value >= 0
    
    def test_performance_tracking(self, client):
        """Test that performance metrics are recorded"""
        with patch('cache.manager.cache_manager.is_initialized') as mock_is_initialized, \
             patch('cache.manager.cache_manager.record_request_time') as mock_record_time:
            
            mock_is_initialized.return_value = True
            
            response = client.get("/")
            
            # Verify that performance tracking was called
            mock_record_time.assert_called_once()
            
            # Verify the recorded time is reasonable (should be a small positive number)
            recorded_time = mock_record_time.call_args[0][0]
            assert isinstance(recorded_time, float)
            assert recorded_time >= 0
            assert recorded_time < 10  # Should be less than 10 seconds for a simple request


class TestSystemEndpointsIntegration:
    """Integration tests for system endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_health_and_metrics_consistency(self, client):
        """Test that health and metrics endpoints are consistent"""
        with patch('cache.manager.cache_manager.is_initialized') as mock_is_initialized, \
             patch('cache.manager.cache_manager.get_cache_stats') as mock_get_cache_stats, \
             patch('cache.manager.cache_manager.get_performance_stats') as mock_get_perf_stats, \
             patch('main.SessionLocal') as mock_session_local:
            
            # Setup mocks
            mock_is_initialized.return_value = True
            mock_get_cache_stats.return_value = {
                "initialized": True,
                "initialization_time": 1.5,
                "posts_count": 50,
                "users_count": 25,
                "comments_count": 100,
                "tags_count": 10,
                "surveys_count": 5,
                "likes_count": 150,
                "bookmarks_count": 75,
                "follows_count": 30
            }
            mock_get_perf_stats.return_value = {
                "total_requests": 500,
                "average_response_time_ms": 120.0,
                "total_response_time": 60.0
            }
            
            # Mock database session
            mock_db = Mock()
            mock_session_local.return_value = mock_db
            mock_db.execute.return_value = None
            mock_db.close.return_value = None
            
            # Get both endpoints
            health_response = client.get("/api/v1/system/health")
            metrics_response = client.get("/api/v1/system/metrics")
            
            assert health_response.status_code == 200
            assert metrics_response.status_code == 200
            
            health_data = health_response.json()
            metrics_data = metrics_response.json()
            
            # Verify consistency
            assert health_data["status"] == "healthy"
            assert metrics_data["cache"]["status"] == "initialized"
            assert health_data["components"]["cache"]["initialized"] is True
            
            # Verify timestamps are recent and reasonable
            health_timestamp = datetime.fromisoformat(health_data["timestamp"].replace('Z', '+00:00'))
            metrics_timestamp = datetime.fromisoformat(metrics_data["timestamp"].replace('Z', '+00:00'))
            
            time_diff = abs((metrics_timestamp - health_timestamp).total_seconds())
            assert time_diff < 5  # Should be within 5 seconds of each other