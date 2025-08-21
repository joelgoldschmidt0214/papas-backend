"""
Load testing for TOMOSU Backend API
Tests system behavior under concurrent load
"""

import pytest
import asyncio
import aiohttp
import time
import statistics
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch
import threading

from cache.manager import cache_manager


class TestLoadPerformance:
    """Test API performance under load"""

    @pytest.fixture
    def mock_cache_setup(self):
        """Setup mock cache for load testing"""
        with (
            patch.object(cache_manager, "is_initialized", return_value=True),
            patch.object(cache_manager, "get_posts") as mock_get_posts,
            patch.object(cache_manager, "get_post_by_id") as mock_get_post,
            patch.object(cache_manager, "get_user_profile") as mock_get_user,
        ):
            # Mock lightweight responses
            mock_get_posts.return_value = []
            mock_get_post.return_value = None
            mock_get_user.return_value = None

            yield

    def make_concurrent_requests(
        self,
        base_url: str,
        endpoint: str,
        num_requests: int,
        concurrent_users: int = 10,
    ) -> Dict[str, Any]:
        """Make concurrent requests to test load performance"""
        import requests

        url = f"{base_url}{endpoint}"
        response_times = []
        errors = []
        successful_requests = 0

        def make_request():
            try:
                start_time = time.time()
                response = requests.get(url, timeout=5)
                end_time = time.time()

                response_time = end_time - start_time

                if response.status_code == 200:
                    return response_time, None
                else:
                    return None, f"HTTP {response.status_code}"

            except Exception as e:
                return None, str(e)

        # Use ThreadPoolExecutor for concurrent requests
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]

            for future in as_completed(futures):
                response_time, error = future.result()

                if error:
                    errors.append(error)
                else:
                    response_times.append(response_time)
                    successful_requests += 1

        # Calculate statistics
        if response_times:
            avg_time = statistics.mean(response_times)
            median_time = statistics.median(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            requests_under_200ms = sum(1 for t in response_times if t < 0.2)
            performance_percentage = (requests_under_200ms / len(response_times)) * 100
        else:
            avg_time = median_time = min_time = max_time = 0
            requests_under_200ms = 0
            performance_percentage = 0

        return {
            "endpoint": endpoint,
            "total_requests": num_requests,
            "successful_requests": successful_requests,
            "failed_requests": len(errors),
            "concurrent_users": concurrent_users,
            "response_times": response_times,
            "errors": errors,
            "avg_time_ms": round(avg_time * 1000, 2) if avg_time else 0,
            "median_time_ms": round(median_time * 1000, 2) if median_time else 0,
            "min_time_ms": round(min_time * 1000, 2) if min_time else 0,
            "max_time_ms": round(max_time * 1000, 2) if max_time else 0,
            "requests_under_200ms": requests_under_200ms,
            "performance_percentage": round(performance_percentage, 2),
            "success_rate": round((successful_requests / num_requests) * 100, 2),
        }

    @pytest.mark.skip(reason="Load test - run manually with live server")
    def test_concurrent_posts_requests(self, mock_cache_setup):
        """Test posts endpoint under concurrent load"""
        # This test should be run against a live server
        # Skip by default to avoid requiring server setup in CI

        base_url = "http://localhost:8000"  # Adjust as needed
        endpoint = "/api/v1/posts"

        results = self.make_concurrent_requests(
            base_url=base_url, endpoint=endpoint, num_requests=100, concurrent_users=10
        )

        print(f"\nConcurrent load test results for {endpoint}:")
        print(f"Total requests: {results['total_requests']}")
        print(f"Successful requests: {results['successful_requests']}")
        print(f"Success rate: {results['success_rate']}%")
        print(f"Average response time: {results['avg_time_ms']}ms")
        print(f"Performance percentage: {results['performance_percentage']}%")
        print(f"Concurrent users: {results['concurrent_users']}")

        # Assert performance under load
        assert results["success_rate"] >= 95.0, (
            f"Success rate {results['success_rate']}% below 95% target under load"
        )
        assert results["performance_percentage"] >= 90.0, (
            f"Performance {results['performance_percentage']}% below 90% target under load"
        )
        assert results["avg_time_ms"] < 300, (
            f"Average response time {results['avg_time_ms']}ms exceeds 300ms under load"
        )

    @pytest.mark.skip(reason="Load test - run manually with live server")
    def test_sustained_load(self, mock_cache_setup):
        """Test system behavior under sustained load"""
        base_url = "http://localhost:8000"
        endpoint = "/api/v1/posts"

        # Run multiple rounds of concurrent requests
        rounds = 5
        requests_per_round = 50
        concurrent_users = 5

        all_results = []

        for round_num in range(rounds):
            print(f"Running load test round {round_num + 1}/{rounds}")

            results = self.make_concurrent_requests(
                base_url=base_url,
                endpoint=endpoint,
                num_requests=requests_per_round,
                concurrent_users=concurrent_users,
            )

            all_results.append(results)

            # Brief pause between rounds
            time.sleep(1)

        # Analyze sustained performance
        total_requests = sum(r["total_requests"] for r in all_results)
        total_successful = sum(r["successful_requests"] for r in all_results)
        all_response_times = []

        for results in all_results:
            all_response_times.extend(results["response_times"])

        overall_success_rate = (total_successful / total_requests) * 100
        overall_avg_time = (
            statistics.mean(all_response_times) if all_response_times else 0
        )
        requests_under_200ms = sum(1 for t in all_response_times if t < 0.2)
        overall_performance = (
            (requests_under_200ms / len(all_response_times)) * 100
            if all_response_times
            else 0
        )

        print(f"\nSustained load test results:")
        print(f"Total rounds: {rounds}")
        print(f"Total requests: {total_requests}")
        print(f"Overall success rate: {overall_success_rate:.2f}%")
        print(f"Overall average response time: {overall_avg_time * 1000:.2f}ms")
        print(f"Overall performance percentage: {overall_performance:.2f}%")

        # Assert sustained performance
        assert overall_success_rate >= 95.0, (
            f"Sustained success rate {overall_success_rate:.2f}% below 95% target"
        )
        assert overall_performance >= 90.0, (
            f"Sustained performance {overall_performance:.2f}% below 90% target"
        )

    def test_memory_usage_under_load(self):
        """Test that memory usage remains stable under load"""
        with patch.object(cache_manager, "is_initialized", return_value=True):
            # Simulate load by recording many request times
            import random

            initial_memory = cache_manager.get_memory_stats()

            # Simulate 1000 requests with random response times
            for _ in range(1000):
                # Simulate response times between 50ms and 150ms
                response_time = random.uniform(0.05, 0.15)
                cache_manager.record_request_time(response_time)

            final_memory = cache_manager.get_memory_stats()

            print(f"\nMemory usage test:")
            print(f"Initial memory: {initial_memory['total_mb']:.2f} MB")
            print(f"Final memory: {final_memory['total_mb']:.2f} MB")
            print(
                f"Memory increase: {final_memory['total_mb'] - initial_memory['total_mb']:.2f} MB"
            )

            # Memory should not increase significantly
            memory_increase = final_memory["total_mb"] - initial_memory["total_mb"]
            assert memory_increase < 10, (
                f"Memory increased by {memory_increase:.2f}MB under load, possible memory leak"
            )

    def test_performance_metrics_accuracy(self):
        """Test that performance metrics are accurately tracked"""
        with patch.object(cache_manager, "is_initialized", return_value=True):
            # Reset performance metrics
            cache_manager.performance_metrics = (
                cache_manager.performance_metrics.__class__()
            )

            # Record known response times
            test_times = [0.05, 0.1, 0.15, 0.25, 0.3]  # Mix of fast and slow responses

            for response_time in test_times:
                cache_manager.record_request_time(response_time)

            stats = cache_manager.get_performance_stats()

            expected_avg = sum(test_times) / len(test_times)
            expected_under_200ms = sum(1 for t in test_times if t < 0.2)
            expected_percentage = (expected_under_200ms / len(test_times)) * 100

            print(f"\nPerformance metrics accuracy test:")
            print(f"Expected average: {expected_avg * 1000:.2f}ms")
            print(f"Actual average: {stats['average_response_time_ms']:.2f}ms")
            print(f"Expected under 200ms: {expected_under_200ms}")
            print(f"Actual under 200ms: {stats['requests_under_200ms']}")
            print(f"Expected percentage: {expected_percentage:.2f}%")
            print(f"Actual percentage: {stats['performance_percentage']:.2f}%")

            # Assert accuracy
            assert abs(stats["average_response_time_ms"] - expected_avg * 1000) < 1, (
                "Average response time calculation inaccurate"
            )
            assert stats["requests_under_200ms"] == expected_under_200ms, (
                "Under 200ms count inaccurate"
            )
            assert abs(stats["performance_percentage"] - expected_percentage) < 0.1, (
                "Performance percentage calculation inaccurate"
            )


class TestConcurrentCacheAccess:
    """Test cache performance under concurrent access"""

    def test_concurrent_cache_reads(self):
        """Test cache can handle concurrent read operations"""
        with (
            patch.object(cache_manager, "is_initialized", return_value=True),
            patch.object(cache_manager, "posts", {1: None, 2: None, 3: None}),
        ):
            results = []
            errors = []

            def read_cache():
                try:
                    start_time = time.time()
                    # Simulate cache read operations
                    cache_manager.get_posts(skip=0, limit=20)
                    cache_manager.get_post_by_id(1)
                    cache_manager.get_user_profile(1)
                    end_time = time.time()

                    return end_time - start_time
                except Exception as e:
                    errors.append(str(e))
                    return None

            # Run concurrent cache reads
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = [executor.submit(read_cache) for _ in range(100)]

                for future in as_completed(futures):
                    result = future.result()
                    if result is not None:
                        results.append(result)

            print(f"\nConcurrent cache access test:")
            print(f"Successful operations: {len(results)}")
            print(f"Failed operations: {len(errors)}")
            print(f"Average operation time: {statistics.mean(results) * 1000:.2f}ms")

            # Assert no errors and reasonable performance
            assert len(errors) == 0, f"Cache errors under concurrent access: {errors}"
            assert len(results) == 100, "Not all cache operations completed"
            assert statistics.mean(results) < 0.01, (
                "Cache operations too slow under concurrent access"
            )
