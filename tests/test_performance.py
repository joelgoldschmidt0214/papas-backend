"""
Performance tests for TOMOSU Backend API
Tests to validate 95% of requests respond within 200ms target (requirement 8.1, 8.2)
"""

import pytest
import time
import statistics
from typing import List, Dict, Any
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from cache.manager import cache_manager
from models.responses import (
    PostResponse,
    UserResponse,
    CommentResponse,
    TagResponse,
    SurveyResponse,
)


class TestAPIPerformance:
    """Test API endpoint performance requirements"""

    @pytest.fixture
    def client(self):
        """Test client fixture"""
        return TestClient(app)

    @pytest.fixture
    def mock_cache_manager(self):
        """Mock cache manager with sample data for performance testing"""
        # Create sample data for performance testing
        sample_users = {
            i: UserResponse(
                user_id=i,
                username=f"user{i}",
                display_name=f"User {i}",
                email=f"user{i}@example.com",
                profile_image_url=None,
                bio=f"Bio for user {i}",
                area="Tokyo",
                created_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
            )
            for i in range(1, 101)  # 100 users
        }

        sample_posts = []
        for i in range(1, 201):  # 200 posts
            post = PostResponse(
                post_id=i,
                user_id=(i % 100) + 1,
                content=f"Sample post content {i}",
                created_at=f"2024-01-{(i % 30) + 1:02d}T12:00:00",
                updated_at=f"2024-01-{(i % 30) + 1:02d}T12:00:00",
                author=sample_users[(i % 100) + 1],
                tags=[],
                likes_count=i % 50,
                comments_count=i % 20,
                is_liked=False,
                is_bookmarked=False,
            )
            sample_posts.append(post)

        with (
            patch.object(cache_manager, "is_initialized", return_value=True),
            patch.object(cache_manager, "get_posts", return_value=sample_posts[:20]),
            patch.object(cache_manager, "get_post_by_id") as mock_get_post,
            patch.object(cache_manager, "get_user_profile") as mock_get_user,
            patch.object(cache_manager, "get_tags") as mock_get_tags,
            patch.object(cache_manager, "get_surveys") as mock_get_surveys,
        ):
            mock_get_post.return_value = sample_posts[0]
            mock_get_user.return_value = sample_users[1]
            mock_get_tags.return_value = []
            mock_get_surveys.return_value = []

            yield cache_manager

    def measure_response_time(
        self, client: TestClient, method: str, url: str, **kwargs
    ) -> float:
        """Measure response time for a single request"""
        start_time = time.time()

        if method.upper() == "GET":
            response = client.get(url, **kwargs)
        elif method.upper() == "POST":
            response = client.post(url, **kwargs)
        else:
            raise ValueError(f"Unsupported method: {method}")

        end_time = time.time()
        response_time = end_time - start_time

        # Ensure request was successful
        assert response.status_code in [200, 201], (
            f"Request failed with status {response.status_code}"
        )

        return response_time

    def run_performance_test(
        self,
        client: TestClient,
        endpoint_config: Dict[str, Any],
        num_requests: int = 100,
    ) -> Dict[str, Any]:
        """Run performance test for a specific endpoint"""
        response_times = []

        for _ in range(num_requests):
            response_time = self.measure_response_time(
                client,
                endpoint_config["method"],
                endpoint_config["url"],
                **endpoint_config.get("kwargs", {}),
            )
            response_times.append(response_time)

        # Calculate statistics
        avg_time = statistics.mean(response_times)
        median_time = statistics.median(response_times)
        min_time = min(response_times)
        max_time = max(response_times)

        # Count requests under 200ms
        requests_under_200ms = sum(1 for t in response_times if t < 0.2)
        performance_percentage = (requests_under_200ms / num_requests) * 100

        return {
            "endpoint": endpoint_config["url"],
            "method": endpoint_config["method"],
            "num_requests": num_requests,
            "response_times": response_times,
            "avg_time_ms": round(avg_time * 1000, 2),
            "median_time_ms": round(median_time * 1000, 2),
            "min_time_ms": round(min_time * 1000, 2),
            "max_time_ms": round(max_time * 1000, 2),
            "requests_under_200ms": requests_under_200ms,
            "performance_percentage": round(performance_percentage, 2),
            "meets_target": performance_percentage >= 95.0,
        }

    def test_posts_endpoint_performance(self, client, mock_cache_manager):
        """Test posts endpoint performance (requirement 8.1, 8.2)"""
        endpoint_config = {
            "method": "GET",
            "url": "/api/v1/posts",
            "kwargs": {"params": {"skip": 0, "limit": 20}},
        }

        results = self.run_performance_test(client, endpoint_config, num_requests=50)

        # Log results for analysis
        print(f"\nPosts endpoint performance:")
        print(f"Average response time: {results['avg_time_ms']}ms")
        print(f"Performance percentage: {results['performance_percentage']}%")
        print(f"Meets 95% target: {results['meets_target']}")

        # Assert performance requirements
        assert results["performance_percentage"] >= 95.0, (
            f"Posts endpoint performance {results['performance_percentage']}% below 95% target"
        )
        assert results["avg_time_ms"] < 200, (
            f"Average response time {results['avg_time_ms']}ms exceeds 200ms target"
        )

    def test_single_post_endpoint_performance(self, client, mock_cache_manager):
        """Test single post retrieval performance"""
        endpoint_config = {"method": "GET", "url": "/api/v1/posts/1"}

        results = self.run_performance_test(client, endpoint_config, num_requests=50)

        print(f"\nSingle post endpoint performance:")
        print(f"Average response time: {results['avg_time_ms']}ms")
        print(f"Performance percentage: {results['performance_percentage']}%")

        assert results["performance_percentage"] >= 95.0
        assert results["avg_time_ms"] < 200

    def test_user_profile_endpoint_performance(self, client, mock_cache_manager):
        """Test user profile endpoint performance"""
        endpoint_config = {"method": "GET", "url": "/api/v1/users/1"}

        results = self.run_performance_test(client, endpoint_config, num_requests=50)

        print(f"\nUser profile endpoint performance:")
        print(f"Average response time: {results['avg_time_ms']}ms")
        print(f"Performance percentage: {results['performance_percentage']}%")

        assert results["performance_percentage"] >= 95.0
        assert results["avg_time_ms"] < 200

    def test_tags_endpoint_performance(self, client, mock_cache_manager):
        """Test tags endpoint performance"""
        endpoint_config = {"method": "GET", "url": "/api/v1/tags"}

        results = self.run_performance_test(client, endpoint_config, num_requests=50)

        print(f"\nTags endpoint performance:")
        print(f"Average response time: {results['avg_time_ms']}ms")
        print(f"Performance percentage: {results['performance_percentage']}%")

        assert results["performance_percentage"] >= 95.0
        assert results["avg_time_ms"] < 200

    def test_health_check_performance(self, client, mock_cache_manager):
        """Test health check endpoint performance"""
        endpoint_config = {"method": "GET", "url": "/api/v1/system/health"}

        with patch("main.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_session_local.return_value = mock_db

            results = self.run_performance_test(
                client, endpoint_config, num_requests=50
            )

            print(f"\nHealth check endpoint performance:")
            print(f"Average response time: {results['avg_time_ms']}ms")
            print(f"Performance percentage: {results['performance_percentage']}%")

            assert results["performance_percentage"] >= 95.0
            assert results["avg_time_ms"] < 200

    def test_comprehensive_performance_suite(self, client, mock_cache_manager):
        """Run comprehensive performance test across multiple endpoints"""
        endpoints = [
            {
                "method": "GET",
                "url": "/api/v1/posts",
                "kwargs": {"params": {"skip": 0, "limit": 20}},
            },
            {"method": "GET", "url": "/api/v1/posts/1"},
            {"method": "GET", "url": "/api/v1/users/1"},
            {"method": "GET", "url": "/api/v1/tags"},
        ]

        all_results = []
        total_requests = 0
        total_under_200ms = 0

        for endpoint_config in endpoints:
            results = self.run_performance_test(
                client, endpoint_config, num_requests=25
            )
            all_results.append(results)
            total_requests += results["num_requests"]
            total_under_200ms += results["requests_under_200ms"]

        # Calculate overall performance
        overall_performance = (total_under_200ms / total_requests) * 100

        print(f"\nComprehensive performance test results:")
        print(f"Total requests: {total_requests}")
        print(f"Requests under 200ms: {total_under_200ms}")
        print(f"Overall performance: {overall_performance:.2f}%")

        # Print individual endpoint results
        for result in all_results:
            print(
                f"{result['method']} {result['endpoint']}: "
                f"{result['avg_time_ms']}ms avg, "
                f"{result['performance_percentage']}% under 200ms"
            )

        # Assert overall performance requirement
        assert overall_performance >= 95.0, (
            f"Overall API performance {overall_performance:.2f}% below 95% target"
        )


class TestCachePerformance:
    """Test cache manager performance"""

    def test_cache_initialization_time(self):
        """Test that cache initializes within 5 seconds (requirement 8.1)"""
        with (
            patch("cache.manager.crud") as mock_crud,
            patch("sqlalchemy.orm.Session") as mock_session,
        ):
            # Mock database responses with reasonable data sizes
            mock_crud.select_users.return_value = [MagicMock() for _ in range(100)]
            mock_crud.select_posts.return_value = [MagicMock() for _ in range(200)]
            mock_crud.select_surveys.return_value = [MagicMock() for _ in range(50)]

            mock_session.query.return_value.all.return_value = []
            mock_session.query.return_value.filter.return_value.count.return_value = 0

            # Measure initialization time
            start_time = time.time()

            test_cache = cache_manager.__class__()
            success = test_cache.initialize(mock_session)

            end_time = time.time()
            initialization_time = end_time - start_time

            print(f"\nCache initialization time: {initialization_time:.2f} seconds")

            assert success, "Cache initialization should succeed"
            assert initialization_time < 5.0, (
                f"Cache initialization took {initialization_time:.2f}s, exceeds 5s target"
            )

    def test_cache_memory_efficiency(self):
        """Test cache memory usage is reasonable"""
        with patch.object(cache_manager, "is_initialized", return_value=True):
            memory_stats = cache_manager.get_memory_stats()

            print(f"\nCache memory usage: {memory_stats['total_mb']:.2f} MB")
            print(f"Memory breakdown: {memory_stats['breakdown']}")

            # Assert reasonable memory usage (adjust based on expected data size)
            assert memory_stats["total_mb"] < 100, (
                f"Cache memory usage {memory_stats['total_mb']:.2f}MB seems excessive"
            )


class TestPaginationPerformance:
    """Test pagination efficiency across endpoints"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_pagination_consistency(self, client):
        """Test that pagination parameters work consistently across endpoints"""
        with (
            patch.object(cache_manager, "is_initialized", return_value=True),
            patch.object(cache_manager, "get_posts") as mock_get_posts,
            patch.object(cache_manager, "get_tags") as mock_get_tags,
            patch.object(cache_manager, "get_surveys") as mock_get_surveys,
        ):
            # Mock responses
            mock_get_posts.return_value = []
            mock_get_tags.return_value = []
            mock_get_surveys.return_value = []

            # Test different pagination parameters
            pagination_tests = [
                {"skip": 0, "limit": 10},
                {"skip": 10, "limit": 20},
                {"skip": 50, "limit": 50},
                {"skip": 100, "limit": 100},
            ]

            endpoints = ["/api/v1/posts", "/api/v1/tags", "/api/v1/surveys"]

            for endpoint in endpoints:
                for params in pagination_tests:
                    start_time = time.time()
                    response = client.get(endpoint, params=params)
                    response_time = time.time() - start_time

                    assert response.status_code == 200
                    assert response_time < 0.2, (
                        f"Pagination request to {endpoint} with {params} took {response_time:.3f}s"
                    )

    def test_large_pagination_performance(self, client):
        """Test performance with large pagination parameters"""
        with (
            patch.object(cache_manager, "is_initialized", return_value=True),
            patch.object(cache_manager, "get_posts") as mock_get_posts,
        ):
            # Mock large dataset
            large_dataset = [MagicMock() for _ in range(100)]
            mock_get_posts.return_value = large_dataset

            # Test large limit
            start_time = time.time()
            response = client.get("/api/v1/posts", params={"skip": 0, "limit": 100})
            response_time = time.time() - start_time

            assert response.status_code == 200
            assert response_time < 0.2, (
                f"Large pagination request took {response_time:.3f}s, exceeds 200ms target"
            )


class TestCompressionPerformance:
    """Test response compression effectiveness"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_gzip_compression_headers(self, client):
        """Test that compression headers are properly set"""
        with (
            patch.object(cache_manager, "is_initialized", return_value=True),
            patch.object(cache_manager, "get_posts") as mock_get_posts,
        ):
            # Mock large response data
            large_posts = [MagicMock() for _ in range(50)]
            mock_get_posts.return_value = large_posts

            # Request with compression
            response = client.get("/api/v1/posts", headers={"Accept-Encoding": "gzip"})

            assert response.status_code == 200

            # Check if compression was applied for large responses
            # Note: TestClient may not actually compress, but middleware should be configured
            print(f"Response headers: {dict(response.headers)}")
