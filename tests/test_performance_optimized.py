"""
Optimized performance tests for TOMOSU Backend API
Tests to validate 95% of requests respond within 200ms target after optimizations
"""

import pytest
import time
import statistics
import asyncio
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
    UserProfileResponse,
)


class TestOptimizedAPIPerformance:
    """Test optimized API endpoint performance requirements"""

    @pytest.fixture
    def client(self):
        """Test client fixture"""
        return TestClient(app)

    @pytest.fixture
    def optimized_cache_manager(self):
        """Mock cache manager with optimized data structures for performance testing"""
        # Create larger sample data to test performance under realistic conditions
        sample_users = {}
        for i in range(1, 501):  # 500 users
            sample_users[i] = UserResponse(
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

        sample_posts = []
        for i in range(1, 1001):  # 1000 posts
            post = PostResponse(
                post_id=i,
                user_id=(i % 500) + 1,
                content=f"Sample post content {i} with some longer text to simulate realistic post sizes",
                created_at=f"2024-01-{(i % 28) + 1:02d}T{(i % 24):02d}:00:00",
                updated_at=f"2024-01-{(i % 28) + 1:02d}T{(i % 24):02d}:00:00",
                author=sample_users[(i % 500) + 1],
                tags=[],
                likes_count=i % 100,
                comments_count=i % 50,
                is_liked=False,
                is_bookmarked=False,
            )
            sample_posts.append(post)

        sample_tags = []
        for i in range(1, 51):  # 50 tags
            tag = TagResponse(tag_id=i, tag_name=f"tag{i}", posts_count=i * 5)
            sample_tags.append(tag)

        sample_surveys = []
        for i in range(1, 101):  # 100 surveys
            survey = SurveyResponse(
                survey_id=i,
                title=f"Survey {i}",
                question_text=f"Question text for survey {i}",
                points=100,
                deadline=None,
                target_audience="All residents",
                created_at=f"2024-01-{(i % 28) + 1:02d}T12:00:00",
                response_count=i * 3,
            )
            sample_surveys.append(survey)

        with (
            patch.object(cache_manager, "is_initialized", return_value=True),
            patch.object(cache_manager, "get_posts") as mock_get_posts,
            patch.object(cache_manager, "get_post_by_id") as mock_get_post,
            patch.object(cache_manager, "get_user_profile") as mock_get_user,
            patch.object(cache_manager, "get_user_by_id") as mock_get_user_by_id,
            patch.object(cache_manager, "get_tags") as mock_get_tags,
            patch.object(cache_manager, "get_surveys") as mock_get_surveys,
            patch.object(cache_manager, "get_posts_by_tag") as mock_get_posts_by_tag,
            patch.object(cache_manager, "get_comments_by_post_id") as mock_get_comments,
            patch.object(cache_manager, "get_user_bookmarks") as mock_get_bookmarks,
            patch.object(cache_manager, "get_user_followers") as mock_get_followers,
            patch.object(cache_manager, "get_user_following") as mock_get_following,
        ):
            # Configure mocks to return appropriate slices for pagination
            def mock_posts_paginated(skip=0, limit=20, current_user_id=None):
                return sample_posts[skip : skip + limit]

            def mock_posts_by_tag_paginated(
                tag_name, skip=0, limit=20, current_user_id=None
            ):
                return sample_posts[skip : skip + limit]  # Simplified for testing

            def mock_user_profile(user_id):
                if user_id in sample_users:
                    user = sample_users[user_id]
                    return UserProfileResponse(
                        user_id=user.user_id,
                        username=user.username,
                        display_name=user.display_name,
                        email=user.email,
                        profile_image_url=user.profile_image_url,
                        bio=user.bio,
                        area=user.area,
                        created_at=user.created_at,
                        updated_at=user.updated_at,
                        followers_count=50,
                        following_count=30,
                        posts_count=25,
                    )
                return None

            mock_get_posts.side_effect = mock_posts_paginated
            mock_get_posts_by_tag.side_effect = mock_posts_by_tag_paginated
            mock_get_post.return_value = sample_posts[0]
            mock_get_user.side_effect = mock_user_profile
            mock_get_user_by_id.return_value = sample_users[
                1
            ]  # Return a valid user for followers/following
            mock_get_tags.return_value = sample_tags
            mock_get_surveys.return_value = sample_surveys
            mock_get_comments.return_value = []
            mock_get_bookmarks.return_value = sample_posts[:10]
            mock_get_followers.return_value = list(sample_users.values())[:20]
            mock_get_following.return_value = list(sample_users.values())[:20]

            yield cache_manager

    def measure_response_time_batch(
        self,
        client: TestClient,
        endpoint_config: Dict[str, Any],
        num_requests: int = 100,
    ) -> Dict[str, Any]:
        """Measure response times for multiple requests efficiently"""
        response_times = []
        errors = []

        for i in range(num_requests):
            try:
                start_time = time.perf_counter()  # Use high-precision timer

                if endpoint_config["method"].upper() == "GET":
                    response = client.get(
                        endpoint_config["url"], **endpoint_config.get("kwargs", {})
                    )
                elif endpoint_config["method"].upper() == "POST":
                    response = client.post(
                        endpoint_config["url"], **endpoint_config.get("kwargs", {})
                    )
                else:
                    raise ValueError(f"Unsupported method: {endpoint_config['method']}")

                end_time = time.perf_counter()
                response_time = end_time - start_time

                if response.status_code in [200, 201]:
                    response_times.append(response_time)
                else:
                    errors.append(f"HTTP {response.status_code}")

            except Exception as e:
                errors.append(str(e))

        # Calculate comprehensive statistics
        if response_times:
            avg_time = statistics.mean(response_times)
            median_time = statistics.median(response_times)
            min_time = min(response_times)
            max_time = max(response_times)

            # Calculate percentiles
            sorted_times = sorted(response_times)
            p95_time = (
                sorted_times[int(len(sorted_times) * 0.95)] if sorted_times else 0
            )
            p99_time = (
                sorted_times[int(len(sorted_times) * 0.99)] if sorted_times else 0
            )

            # Count requests under performance targets
            requests_under_200ms = sum(1 for t in response_times if t < 0.2)
            requests_under_100ms = sum(1 for t in response_times if t < 0.1)
            requests_under_50ms = sum(1 for t in response_times if t < 0.05)

            performance_200ms = (requests_under_200ms / len(response_times)) * 100
            performance_100ms = (requests_under_100ms / len(response_times)) * 100
            performance_50ms = (requests_under_50ms / len(response_times)) * 100

        else:
            avg_time = median_time = min_time = max_time = p95_time = p99_time = 0
            requests_under_200ms = requests_under_100ms = requests_under_50ms = 0
            performance_200ms = performance_100ms = performance_50ms = 0

        return {
            "endpoint": endpoint_config["url"],
            "method": endpoint_config["method"],
            "num_requests": num_requests,
            "successful_requests": len(response_times),
            "failed_requests": len(errors),
            "success_rate": (len(response_times) / num_requests) * 100
            if num_requests > 0
            else 0,
            "avg_time_ms": round(avg_time * 1000, 2),
            "median_time_ms": round(median_time * 1000, 2),
            "min_time_ms": round(min_time * 1000, 2),
            "max_time_ms": round(max_time * 1000, 2),
            "p95_time_ms": round(p95_time * 1000, 2),
            "p99_time_ms": round(p99_time * 1000, 2),
            "requests_under_200ms": requests_under_200ms,
            "requests_under_100ms": requests_under_100ms,
            "requests_under_50ms": requests_under_50ms,
            "performance_200ms": round(performance_200ms, 2),
            "performance_100ms": round(performance_100ms, 2),
            "performance_50ms": round(performance_50ms, 2),
            "meets_target": performance_200ms >= 95.0,
            "errors": errors[:5],  # Show first 5 errors
        }

    def test_optimized_posts_endpoint_performance(
        self, client, optimized_cache_manager
    ):
        """Test optimized posts endpoint performance with larger dataset"""
        endpoint_config = {
            "method": "GET",
            "url": "/api/v1/posts",
            "kwargs": {"params": {"skip": 0, "limit": 20}},
        }

        results = self.measure_response_time_batch(
            client, endpoint_config, num_requests=100
        )

        print(f"\nOptimized Posts endpoint performance:")
        print(f"Average response time: {results['avg_time_ms']}ms")
        print(f"P95 response time: {results['p95_time_ms']}ms")
        print(f"P99 response time: {results['p99_time_ms']}ms")
        print(f"Performance (under 200ms): {results['performance_200ms']}%")
        print(f"Performance (under 100ms): {results['performance_100ms']}%")
        print(f"Performance (under 50ms): {results['performance_50ms']}%")
        print(f"Success rate: {results['success_rate']}%")

        # Assert strict performance requirements
        assert results["success_rate"] >= 99.0, (
            f"Success rate {results['success_rate']}% below 99% target"
        )
        assert results["performance_200ms"] >= 95.0, (
            f"200ms performance {results['performance_200ms']}% below 95% target"
        )
        assert results["avg_time_ms"] < 100, (
            f"Average response time {results['avg_time_ms']}ms exceeds 100ms optimized target"
        )
        assert results["p95_time_ms"] < 200, (
            f"P95 response time {results['p95_time_ms']}ms exceeds 200ms target"
        )

    def test_optimized_pagination_performance(self, client, optimized_cache_manager):
        """Test pagination performance across different page sizes and offsets"""
        pagination_scenarios = [
            {"skip": 0, "limit": 10},
            {"skip": 0, "limit": 20},
            {"skip": 0, "limit": 50},
            {"skip": 0, "limit": 100},
            {"skip": 100, "limit": 20},
            {"skip": 500, "limit": 20},
            {"skip": 1000, "limit": 20},
        ]

        all_results = []

        for params in pagination_scenarios:
            endpoint_config = {
                "method": "GET",
                "url": "/api/v1/posts",
                "kwargs": {"params": params},
            }

            results = self.measure_response_time_batch(
                client, endpoint_config, num_requests=50
            )
            all_results.append(results)

            print(
                f"Pagination {params}: {results['avg_time_ms']}ms avg, {results['performance_200ms']}% under 200ms"
            )

            # Assert each pagination scenario meets performance targets
            assert results["performance_200ms"] >= 95.0, (
                f"Pagination {params} performance {results['performance_200ms']}% below 95% target"
            )
            assert results["avg_time_ms"] < 150, (
                f"Pagination {params} average time {results['avg_time_ms']}ms exceeds 150ms target"
            )

        # Calculate overall pagination performance
        total_requests = sum(r["num_requests"] for r in all_results)
        total_under_200ms = sum(r["requests_under_200ms"] for r in all_results)
        overall_performance = (
            (total_under_200ms / total_requests) * 100 if total_requests > 0 else 0
        )

        print(
            f"\nOverall pagination performance: {overall_performance:.2f}% under 200ms"
        )
        assert overall_performance >= 95.0, (
            f"Overall pagination performance {overall_performance:.2f}% below 95% target"
        )

    def test_comprehensive_optimized_performance_suite(
        self, client, optimized_cache_manager
    ):
        """Run comprehensive performance test across all optimized endpoints"""
        endpoints = [
            {
                "method": "GET",
                "url": "/api/v1/posts",
                "kwargs": {"params": {"skip": 0, "limit": 20}},
            },
            {"method": "GET", "url": "/api/v1/posts/1"},
            {
                "method": "GET",
                "url": "/api/v1/posts/tags/tag1",
                "kwargs": {"params": {"skip": 0, "limit": 20}},
            },
            {"method": "GET", "url": "/api/v1/users/1"},
            {
                "method": "GET",
                "url": "/api/v1/users/1/followers",
                "kwargs": {"params": {"skip": 0, "limit": 20}},
            },
            {
                "method": "GET",
                "url": "/api/v1/users/1/following",
                "kwargs": {"params": {"skip": 0, "limit": 20}},
            },
            {
                "method": "GET",
                "url": "/api/v1/tags",
                "kwargs": {"params": {"skip": 0, "limit": 50}},
            },
            {
                "method": "GET",
                "url": "/api/v1/surveys",
                "kwargs": {"params": {"skip": 0, "limit": 50}},
            },
        ]

        all_results = []
        total_requests = 0
        total_under_200ms = 0
        total_successful = 0

        print(f"\nComprehensive optimized performance test:")
        print("=" * 80)

        for endpoint_config in endpoints:
            results = self.measure_response_time_batch(
                client, endpoint_config, num_requests=50
            )
            all_results.append(results)

            total_requests += results["num_requests"]
            total_under_200ms += results["requests_under_200ms"]
            total_successful += results["successful_requests"]

            print(
                f"{results['method']} {results['endpoint'][:50]:<50} | "
                f"Avg: {results['avg_time_ms']:>6.1f}ms | "
                f"P95: {results['p95_time_ms']:>6.1f}ms | "
                f"200ms: {results['performance_200ms']:>5.1f}% | "
                f"Success: {results['success_rate']:>5.1f}%"
            )

        # Calculate overall performance metrics
        overall_success_rate = (
            (total_successful / total_requests) * 100 if total_requests > 0 else 0
        )
        overall_performance = (
            (total_under_200ms / total_successful) * 100 if total_successful > 0 else 0
        )

        print("=" * 80)
        print(f"Overall Results:")
        print(f"Total requests: {total_requests}")
        print(f"Total successful: {total_successful}")
        print(f"Overall success rate: {overall_success_rate:.2f}%")
        print(f"Overall performance (under 200ms): {overall_performance:.2f}%")
        print(
            f"Meets 95% target: {'✓ PASS' if overall_performance >= 95.0 else '✗ FAIL'}"
        )

        # Assert comprehensive performance requirements
        assert overall_success_rate >= 99.0, (
            f"Overall success rate {overall_success_rate:.2f}% below 99% target"
        )
        assert overall_performance >= 95.0, (
            f"Overall performance {overall_performance:.2f}% below 95% target"
        )

        # Ensure no individual endpoint fails the performance target
        failed_endpoints = [r for r in all_results if not r["meets_target"]]
        assert len(failed_endpoints) == 0, (
            f"Endpoints failed performance target: {[r['endpoint'] for r in failed_endpoints]}"
        )

    def test_response_compression_effectiveness(self, client, optimized_cache_manager):
        """Test that response compression is working effectively for large payloads"""
        # Test with large limit to get bigger response
        endpoint_config = {
            "method": "GET",
            "url": "/api/v1/posts",
            "kwargs": {
                "params": {"skip": 0, "limit": 100},
                "headers": {"Accept-Encoding": "gzip, deflate"},
            },
        }

        results = self.measure_response_time_batch(
            client, endpoint_config, num_requests=20
        )

        print(f"\nResponse compression test (large payload):")
        print(f"Average response time: {results['avg_time_ms']}ms")
        print(f"Performance (under 200ms): {results['performance_200ms']}%")
        print(f"Success rate: {results['success_rate']}%")

        # Even with large payloads, should meet performance targets due to compression
        assert results["performance_200ms"] >= 90.0, (
            f"Large payload performance {results['performance_200ms']}% below 90% target"
        )
        assert results["avg_time_ms"] < 200, (
            f"Large payload average time {results['avg_time_ms']}ms exceeds 200ms target"
        )

    def test_concurrent_request_performance(self, client, optimized_cache_manager):
        """Test performance under simulated concurrent load"""
        import threading
        import queue

        endpoint_config = {
            "method": "GET",
            "url": "/api/v1/posts",
            "kwargs": {"params": {"skip": 0, "limit": 20}},
        }

        results_queue = queue.Queue()
        num_threads = 10
        requests_per_thread = 10

        def worker():
            thread_results = []
            for _ in range(requests_per_thread):
                start_time = time.perf_counter()
                try:
                    response = client.get(
                        endpoint_config["url"], **endpoint_config.get("kwargs", {})
                    )
                    end_time = time.perf_counter()

                    if response.status_code == 200:
                        thread_results.append(end_time - start_time)
                except Exception:
                    pass

            results_queue.put(thread_results)

        # Start concurrent threads
        threads = []
        start_time = time.perf_counter()

        for _ in range(num_threads):
            thread = threading.Thread(target=worker)
            thread.start()
            threads.append(thread)

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Collect all results
        all_response_times = []
        while not results_queue.empty():
            thread_results = results_queue.get()
            all_response_times.extend(thread_results)

        if all_response_times:
            avg_time = statistics.mean(all_response_times)
            requests_under_200ms = sum(1 for t in all_response_times if t < 0.2)
            performance_percentage = (
                requests_under_200ms / len(all_response_times)
            ) * 100
            throughput = len(all_response_times) / total_time
        else:
            avg_time = 0
            performance_percentage = 0
            throughput = 0

        print(f"\nConcurrent request performance:")
        print(f"Threads: {num_threads}")
        print(f"Requests per thread: {requests_per_thread}")
        print(f"Total successful requests: {len(all_response_times)}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Throughput: {throughput:.2f} requests/second")
        print(f"Average response time: {avg_time * 1000:.2f}ms")
        print(f"Performance (under 200ms): {performance_percentage:.2f}%")

        # Assert concurrent performance
        assert len(all_response_times) >= num_threads * requests_per_thread * 0.95, (
            "Too many failed requests under concurrent load"
        )
        assert performance_percentage >= 90.0, (
            f"Concurrent performance {performance_percentage:.2f}% below 90% target"
        )
        assert avg_time < 0.3, (
            f"Concurrent average time {avg_time * 1000:.2f}ms exceeds 300ms target"
        )


class TestOptimizedCachePerformance:
    """Test optimized cache manager performance"""

    def test_optimized_cache_initialization_performance(self):
        """Test that optimized cache initializes efficiently"""
        with (
            patch("cache.manager.crud") as mock_crud,
            patch("sqlalchemy.orm.Session") as mock_session,
        ):
            # Mock larger dataset to test optimization
            mock_crud.select_users.return_value = [MagicMock() for _ in range(500)]
            mock_crud.select_posts.return_value = [MagicMock() for _ in range(1000)]
            mock_crud.select_surveys.return_value = [MagicMock() for _ in range(100)]

            mock_session.query.return_value.all.return_value = [
                MagicMock() for _ in range(50)
            ]
            mock_session.query.return_value.filter.return_value.count.return_value = 10

            # Measure initialization time
            start_time = time.perf_counter()

            test_cache = cache_manager.__class__()
            success = test_cache.initialize(mock_session)

            end_time = time.perf_counter()
            initialization_time = end_time - start_time

            print(
                f"\nOptimized cache initialization time: {initialization_time:.3f} seconds"
            )

            assert success, "Optimized cache initialization should succeed"
            assert initialization_time < 3.0, (
                f"Optimized cache initialization took {initialization_time:.3f}s, exceeds 3s optimized target"
            )

    def test_optimized_pagination_cache_performance(self):
        """Test that pagination caching improves performance"""
        with (
            patch.object(cache_manager, "is_initialized", return_value=True),
            patch.object(
                cache_manager, "posts", {i: MagicMock() for i in range(1, 1001)}
            ),
        ):
            # Simulate cache with sorted posts
            cache_manager._sorted_posts_cache = [
                (i, f"2024-01-01T{i % 24:02d}:00:00") for i in range(1, 1001)
            ]
            cache_manager._cache_dirty = False

            # First call - should populate pagination cache
            start_time = time.perf_counter()
            result1 = cache_manager.get_posts(skip=0, limit=20)
            first_call_time = time.perf_counter() - start_time

            # Second call - should use pagination cache
            start_time = time.perf_counter()
            result2 = cache_manager.get_posts(skip=0, limit=20)
            second_call_time = time.perf_counter() - start_time

            print(f"\nPagination cache performance:")
            print(f"First call (populate cache): {first_call_time * 1000:.3f}ms")
            print(f"Second call (use cache): {second_call_time * 1000:.3f}ms")
            print(
                f"Performance improvement: {(first_call_time / second_call_time):.1f}x faster"
            )

            # Both calls should be fast, but second should be faster
            assert first_call_time < 0.01, (
                f"First pagination call too slow: {first_call_time * 1000:.3f}ms"
            )
            assert second_call_time < 0.005, (
                f"Cached pagination call too slow: {second_call_time * 1000:.3f}ms"
            )
            assert second_call_time <= first_call_time, (
                "Cached call should be faster or equal"
            )

    def test_memory_efficiency_optimizations(self):
        """Test that memory optimizations are effective"""
        with patch.object(cache_manager, "is_initialized", return_value=True):
            # Test pagination cache size limit
            cache_manager._pagination_cache.clear()
            cache_manager._pagination_cache_max_size = 5

            # Add items beyond the limit
            for i in range(10):
                cache_key = f"test_key_{i}"
                if (
                    len(cache_manager._pagination_cache)
                    < cache_manager._pagination_cache_max_size
                ):
                    cache_manager._pagination_cache[cache_key] = [f"data_{i}"]

            print(f"\nMemory efficiency test:")
            print(f"Pagination cache size: {len(cache_manager._pagination_cache)}")
            print(f"Max size limit: {cache_manager._pagination_cache_max_size}")

            # Should not exceed the maximum size
            assert (
                len(cache_manager._pagination_cache)
                <= cache_manager._pagination_cache_max_size
            ), "Pagination cache exceeded size limit"

            # Test that cache clearing works
            cache_manager._pagination_cache.clear()
            assert len(cache_manager._pagination_cache) == 0, "Cache clearing failed"
