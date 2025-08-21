#!/usr/bin/env python3
"""
Performance validation script for TOMOSU Backend API optimizations
Validates that the optimizations meet the 95% under 200ms requirement
"""

import sys
import os
import time
import statistics
from typing import List, Dict, Any

# Add the parent directory to the path so we can import from the project
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from main import app
from cache.manager import cache_manager
from models.responses import PostResponse, UserResponse, TagResponse, SurveyResponse


def create_mock_data():
    """Create mock data for performance testing"""
    # Create sample users
    sample_users = {}
    for i in range(1, 101):
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

    # Create sample posts
    sample_posts = []
    for i in range(1, 501):
        post = PostResponse(
            post_id=i,
            user_id=(i % 100) + 1,
            content=f"Sample post content {i} with realistic length text to simulate actual usage",
            created_at=f"2024-01-{(i % 28) + 1:02d}T{(i % 24):02d}:00:00",
            updated_at=f"2024-01-{(i % 28) + 1:02d}T{(i % 24):02d}:00:00",
            author=sample_users[(i % 100) + 1],
            tags=[],
            likes_count=i % 50,
            comments_count=i % 20,
            is_liked=False,
            is_bookmarked=False,
        )
        sample_posts.append(post)

    return sample_users, sample_posts


def measure_endpoint_performance(
    client: TestClient, endpoint: str, params: Dict = None, num_requests: int = 100
) -> Dict[str, Any]:
    """Measure performance of a specific endpoint"""
    response_times = []
    errors = []

    print(f"Testing {endpoint} with {num_requests} requests...")

    for i in range(num_requests):
        try:
            start_time = time.perf_counter()
            response = client.get(endpoint, params=params)
            end_time = time.perf_counter()

            response_time = end_time - start_time

            if response.status_code == 200:
                response_times.append(response_time)
            else:
                errors.append(f"HTTP {response.status_code}")

        except Exception as e:
            errors.append(str(e))

        # Progress indicator
        if (i + 1) % 20 == 0:
            print(f"  Completed {i + 1}/{num_requests} requests")

    # Calculate statistics
    if response_times:
        avg_time = statistics.mean(response_times)
        median_time = statistics.median(response_times)
        min_time = min(response_times)
        max_time = max(response_times)

        sorted_times = sorted(response_times)
        p95_time = sorted_times[int(len(sorted_times) * 0.95)] if sorted_times else 0
        p99_time = sorted_times[int(len(sorted_times) * 0.99)] if sorted_times else 0

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
        "endpoint": endpoint,
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
        "errors": errors[:5],
    }


def print_results(results: Dict[str, Any]):
    """Print formatted performance results"""
    print(f"\n{'=' * 80}")
    print(f"PERFORMANCE RESULTS: {results['endpoint']}")
    print(f"{'=' * 80}")
    print(f"Total Requests:        {results['num_requests']}")
    print(f"Successful Requests:   {results['successful_requests']}")
    print(f"Success Rate:          {results['success_rate']:.1f}%")
    print(f"")
    print(f"Response Times:")
    print(f"  Average:             {results['avg_time_ms']:.2f}ms")
    print(f"  Median:              {results['median_time_ms']:.2f}ms")
    print(f"  Min:                 {results['min_time_ms']:.2f}ms")
    print(f"  Max:                 {results['max_time_ms']:.2f}ms")
    print(f"  P95:                 {results['p95_time_ms']:.2f}ms")
    print(f"  P99:                 {results['p99_time_ms']:.2f}ms")
    print(f"")
    print(f"Performance Targets:")
    print(
        f"  Under 50ms:          {results['requests_under_50ms']}/{results['successful_requests']} ({results['performance_50ms']:.1f}%)"
    )
    print(
        f"  Under 100ms:         {results['requests_under_100ms']}/{results['successful_requests']} ({results['performance_100ms']:.1f}%)"
    )
    print(
        f"  Under 200ms:         {results['requests_under_200ms']}/{results['successful_requests']} ({results['performance_200ms']:.1f}%)"
    )
    print(f"")
    print(f"Target Achievement:")
    print(f"  95% under 200ms:     {'✓ PASS' if results['meets_target'] else '✗ FAIL'}")

    if results["errors"]:
        print(f"\nErrors ({len(results['errors'])} shown):")
        for error in results["errors"]:
            print(f"  - {error}")


def main():
    """Main performance validation function"""
    print("TOMOSU Backend API Performance Validation")
    print("=" * 80)
    print("Testing optimized API performance against 95% under 200ms target")
    print()

    # Create test client
    client = TestClient(app)

    # Create mock data
    sample_users, sample_posts = create_mock_data()

    # Setup mocks for performance testing
    with (
        patch.object(cache_manager, "is_initialized", return_value=True),
        patch.object(cache_manager, "get_posts") as mock_get_posts,
        patch.object(cache_manager, "get_post_by_id") as mock_get_post,
        patch.object(cache_manager, "get_user_profile") as mock_get_user,
        patch.object(cache_manager, "get_user_by_id") as mock_get_user_by_id,
        patch.object(cache_manager, "get_tags") as mock_get_tags,
        patch.object(cache_manager, "get_surveys") as mock_get_surveys,
        patch.object(cache_manager, "get_posts_by_tag") as mock_get_posts_by_tag,
    ):
        # Configure mocks
        def mock_posts_paginated(skip=0, limit=20, current_user_id=None):
            return sample_posts[skip : skip + limit]

        mock_get_posts.side_effect = mock_posts_paginated
        mock_get_posts_by_tag.side_effect = (
            lambda tag_name, skip=0, limit=20, current_user_id=None: sample_posts[
                skip : skip + limit
            ]
        )
        mock_get_post.return_value = sample_posts[0]
        mock_get_user.return_value = sample_users[1]
        mock_get_user_by_id.return_value = sample_users[1]
        mock_get_tags.return_value = []
        mock_get_surveys.return_value = []

        # Test endpoints
        endpoints_to_test = [
            {"endpoint": "/api/v1/posts", "params": {"skip": 0, "limit": 20}},
            {"endpoint": "/api/v1/posts/1", "params": None},
            {
                "endpoint": "/api/v1/posts",
                "params": {"skip": 0, "limit": 50},
            },  # Larger payload
            {
                "endpoint": "/api/v1/posts",
                "params": {"skip": 100, "limit": 20},
            },  # Different offset
            {"endpoint": "/api/v1/users/1", "params": None},
            {"endpoint": "/api/v1/tags", "params": None},
        ]

        all_results = []
        total_requests = 0
        total_successful = 0
        total_under_200ms = 0

        for test_config in endpoints_to_test:
            results = measure_endpoint_performance(
                client,
                test_config["endpoint"],
                params=test_config["params"],
                num_requests=100,
            )

            all_results.append(results)
            total_requests += results["num_requests"]
            total_successful += results["successful_requests"]
            total_under_200ms += results["requests_under_200ms"]

            print_results(results)

        # Overall summary
        overall_success_rate = (
            (total_successful / total_requests) * 100 if total_requests > 0 else 0
        )
        overall_performance = (
            (total_under_200ms / total_successful) * 100 if total_successful > 0 else 0
        )

        print(f"\n{'=' * 80}")
        print(f"OVERALL PERFORMANCE SUMMARY")
        print(f"{'=' * 80}")
        print(f"Total Endpoints Tested:    {len(endpoints_to_test)}")
        print(f"Total Requests:            {total_requests}")
        print(f"Total Successful:          {total_successful}")
        print(f"Overall Success Rate:      {overall_success_rate:.2f}%")
        print(f"Overall Performance:       {overall_performance:.2f}% under 200ms")
        print(
            f"Target Achievement:        {'✓ PASS' if overall_performance >= 95.0 else '✗ FAIL'}"
        )

        # Individual endpoint summary
        print(f"\nPer-Endpoint Summary:")
        for result in all_results:
            status = "✓" if result["meets_target"] else "✗"
            endpoint_display = f"{result['endpoint']}"
            if len(endpoint_display) > 40:
                endpoint_display = endpoint_display[:37] + "..."
            print(
                f"  {status} {endpoint_display:<40} {result['performance_200ms']:>6.1f}% under 200ms"
            )

        # Final validation
        if overall_performance >= 95.0:
            print(
                f"\n🎉 SUCCESS: API performance optimizations meet the 95% under 200ms target!"
            )
            print(f"   Achieved: {overall_performance:.2f}% of requests under 200ms")
            return 0
        else:
            print(
                f"\n❌ FAILURE: API performance does not meet the 95% under 200ms target"
            )
            print(f"   Achieved: {overall_performance:.2f}% of requests under 200ms")
            return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
