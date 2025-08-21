"""
Load testing scenarios for TOMOSU Backend API using Locust
Tests system performance under various load conditions
"""

from locust import HttpUser, task, between, events
import random
import json
import time
from typing import Dict, Any


class TOMOSAPIUser(HttpUser):
    """Simulates a typical TOMOSU API user"""

    wait_time = between(1, 3)  # Wait 1-3 seconds between requests

    def on_start(self):
        """Called when a user starts"""
        self.client.verify = False  # Disable SSL verification for testing

        # Test data
        self.sample_post_ids = list(range(1, 101))  # Assume 100 posts exist
        self.sample_user_ids = list(range(1, 51))  # Assume 50 users exist
        self.sample_tags = ["イベント", "お祭り", "安全", "地域", "スポーツ", "文化"]

        # Performance tracking
        self.response_times = []
        self.error_count = 0
        self.success_count = 0

    def record_response(self, response_time: float, success: bool):
        """Record response metrics"""
        self.response_times.append(response_time)
        if success:
            self.success_count += 1
        else:
            self.error_count += 1

    @task(30)
    def browse_posts(self):
        """Most common task: Browse posts (30% of requests)"""
        skip = random.randint(0, 50)
        limit = random.randint(10, 50)

        start_time = time.time()
        with self.client.get(
            f"/api/v1/posts?skip={skip}&limit={limit}", catch_response=True
        ) as response:
            response_time = time.time() - start_time

            if response.status_code == 200:
                self.record_response(response_time, True)

                # Validate response time requirement (95% under 200ms)
                if response_time > 0.2:
                    response.failure(
                        f"Response time {response_time:.3f}s exceeds 200ms target"
                    )
                else:
                    response.success()
            else:
                self.record_response(response_time, False)
                response.failure(f"Got status code {response.status_code}")

    @task(20)
    def view_post_details(self):
        """View specific post details (20% of requests)"""
        post_id = random.choice(self.sample_post_ids)

        start_time = time.time()
        with self.client.get(
            f"/api/v1/posts/{post_id}", catch_response=True
        ) as response:
            response_time = time.time() - start_time

            if response.status_code == 200:
                self.record_response(response_time, True)

                if response_time > 0.2:
                    response.failure(
                        f"Response time {response_time:.3f}s exceeds 200ms target"
                    )
                else:
                    response.success()
            elif response.status_code == 404:
                # 404 is acceptable for non-existent posts
                self.record_response(response_time, True)
                response.success()
            else:
                self.record_response(response_time, False)
                response.failure(f"Got status code {response.status_code}")

    @task(15)
    def browse_posts_by_tag(self):
        """Browse posts by tag (15% of requests)"""
        tag = random.choice(self.sample_tags)
        skip = random.randint(0, 20)
        limit = random.randint(10, 30)

        start_time = time.time()
        with self.client.get(
            f"/api/v1/posts/tags/{tag}?skip={skip}&limit={limit}", catch_response=True
        ) as response:
            response_time = time.time() - start_time

            if response.status_code == 200:
                self.record_response(response_time, True)

                if response_time > 0.2:
                    response.failure(
                        f"Response time {response_time:.3f}s exceeds 200ms target"
                    )
                else:
                    response.success()
            else:
                self.record_response(response_time, False)
                response.failure(f"Got status code {response.status_code}")

    @task(10)
    def view_user_profile(self):
        """View user profiles (10% of requests)"""
        user_id = random.choice(self.sample_user_ids)

        start_time = time.time()
        with self.client.get(
            f"/api/v1/users/{user_id}", catch_response=True
        ) as response:
            response_time = time.time() - start_time

            if response.status_code == 200:
                self.record_response(response_time, True)

                if response_time > 0.2:
                    response.failure(
                        f"Response time {response_time:.3f}s exceeds 200ms target"
                    )
                else:
                    response.success()
            elif response.status_code == 404:
                # 404 is acceptable for non-existent users
                self.record_response(response_time, True)
                response.success()
            else:
                self.record_response(response_time, False)
                response.failure(f"Got status code {response.status_code}")

    @task(8)
    def view_post_comments(self):
        """View post comments (8% of requests)"""
        post_id = random.choice(self.sample_post_ids)

        start_time = time.time()
        with self.client.get(
            f"/api/v1/posts/{post_id}/comments", catch_response=True
        ) as response:
            response_time = time.time() - start_time

            if response.status_code == 200:
                self.record_response(response_time, True)

                if response_time > 0.2:
                    response.failure(
                        f"Response time {response_time:.3f}s exceeds 200ms target"
                    )
                else:
                    response.success()
            elif response.status_code == 404:
                # 404 is acceptable for non-existent posts
                self.record_response(response_time, True)
                response.success()
            else:
                self.record_response(response_time, False)
                response.failure(f"Got status code {response.status_code}")

    @task(7)
    def browse_tags(self):
        """Browse available tags (7% of requests)"""
        start_time = time.time()
        with self.client.get("/api/v1/tags", catch_response=True) as response:
            response_time = time.time() - start_time

            if response.status_code == 200:
                self.record_response(response_time, True)

                if response_time > 0.2:
                    response.failure(
                        f"Response time {response_time:.3f}s exceeds 200ms target"
                    )
                else:
                    response.success()
            else:
                self.record_response(response_time, False)
                response.failure(f"Got status code {response.status_code}")

    @task(5)
    def view_user_followers(self):
        """View user followers (5% of requests)"""
        user_id = random.choice(self.sample_user_ids)

        start_time = time.time()
        with self.client.get(
            f"/api/v1/users/{user_id}/followers", catch_response=True
        ) as response:
            response_time = time.time() - start_time

            if response.status_code == 200:
                self.record_response(response_time, True)

                if response_time > 0.2:
                    response.failure(
                        f"Response time {response_time:.3f}s exceeds 200ms target"
                    )
                else:
                    response.success()
            elif response.status_code == 404:
                # 404 is acceptable for non-existent users
                self.record_response(response_time, True)
                response.success()
            else:
                self.record_response(response_time, False)
                response.failure(f"Got status code {response.status_code}")

    @task(3)
    def browse_surveys(self):
        """Browse surveys (3% of requests)"""
        start_time = time.time()
        with self.client.get("/api/v1/surveys", catch_response=True) as response:
            response_time = time.time() - start_time

            if response.status_code == 200:
                self.record_response(response_time, True)

                if response_time > 0.2:
                    response.failure(
                        f"Response time {response_time:.3f}s exceeds 200ms target"
                    )
                else:
                    response.success()
            else:
                self.record_response(response_time, False)
                response.failure(f"Got status code {response.status_code}")

    @task(2)
    def check_system_health(self):
        """Check system health (2% of requests)"""
        start_time = time.time()
        with self.client.get("/api/v1/system/health", catch_response=True) as response:
            response_time = time.time() - start_time

            if response.status_code == 200:
                self.record_response(response_time, True)

                # Health check should be very fast
                if response_time > 0.1:
                    response.failure(
                        f"Health check response time {response_time:.3f}s too slow"
                    )
                else:
                    response.success()
            else:
                self.record_response(response_time, False)
                response.failure(
                    f"Health check failed with status {response.status_code}"
                )


class AuthenticatedTOMOSUser(TOMOSAPIUser):
    """Simulates an authenticated user who can create posts"""

    def on_start(self):
        """Called when a user starts - includes authentication"""
        super().on_start()

        # Simulate login (in real scenario, would get session cookie)
        # For testing, we'll just set a header or cookie
        self.client.headers.update({"Authorization": "Bearer test-token"})

    @task(5)
    def create_post(self):
        """Create new posts (5% of requests for authenticated users)"""
        post_content = random.choice(
            [
                "新しい地域イベントの提案です！",
                "近所の公園が綺麗になりました。",
                "地域の安全について話し合いませんか？",
                "今度のお祭りの準備を手伝います。",
                "地域のおすすめスポットを紹介します。",
            ]
        )

        tags = random.sample(self.sample_tags, random.randint(1, 3))

        post_data = {"content": post_content, "tags": tags}

        start_time = time.time()
        with self.client.post(
            "/api/v1/posts", json=post_data, catch_response=True
        ) as response:
            response_time = time.time() - start_time

            if response.status_code == 201:
                self.record_response(response_time, True)

                if response_time > 0.3:  # Allow slightly more time for POST requests
                    response.failure(
                        f"Post creation response time {response_time:.3f}s too slow"
                    )
                else:
                    response.success()
            else:
                self.record_response(response_time, False)
                response.failure(
                    f"Post creation failed with status {response.status_code}"
                )


class PerformanceTestUser(HttpUser):
    """Specialized user for performance testing specific scenarios"""

    wait_time = between(0.1, 0.5)  # Faster requests for performance testing

    @task
    def rapid_posts_requests(self):
        """Rapid posts requests to test cache performance"""
        start_time = time.time()
        response = self.client.get("/api/v1/posts?limit=50")
        response_time = time.time() - start_time

        # Strict performance requirements
        if response.status_code == 200:
            if response_time > 0.2:
                print(
                    f"WARNING: Response time {response_time:.3f}s exceeds 200ms target"
                )
        else:
            print(f"ERROR: Request failed with status {response.status_code}")


# Event handlers for custom metrics
@events.request.add_listener
def record_performance_metrics(
    request_type, name, response_time, response_length, exception, **kwargs
):
    """Record custom performance metrics"""
    if exception is None and response_time <= 200:  # 200ms in milliseconds
        # Request met performance target
        pass
    elif exception is None:
        print(f"Performance target missed: {name} took {response_time}ms")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    print("Starting TOMOSU API load test...")
    print("Performance targets:")
    print("- 95% of requests under 200ms")
    print("- Support for 100 concurrent users")
    print("- System should remain stable under load")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops"""
    print("TOMOSU API load test completed.")

    # Calculate performance statistics
    stats = environment.stats
    total_requests = stats.total.num_requests
    failed_requests = stats.total.num_failures
    success_rate = (
        ((total_requests - failed_requests) / total_requests * 100)
        if total_requests > 0
        else 0
    )

    print(f"Total requests: {total_requests}")
    print(f"Failed requests: {failed_requests}")
    print(f"Success rate: {success_rate:.2f}%")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"95th percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")

    # Check if performance targets were met
    if success_rate >= 95.0:
        print("✅ Success rate target met (≥95%)")
    else:
        print(f"❌ Success rate target missed: {success_rate:.2f}% < 95%")

    if stats.total.get_response_time_percentile(0.95) <= 200:
        print("✅ Response time target met (95th percentile ≤200ms)")
    else:
        print(
            f"❌ Response time target missed: 95th percentile {stats.total.get_response_time_percentile(0.95):.2f}ms > 200ms"
        )


# Load testing scenarios
class LightLoadUser(TOMOSAPIUser):
    """Light load scenario - 10-20 users"""

    wait_time = between(2, 5)


class MediumLoadUser(TOMOSAPIUser):
    """Medium load scenario - 50-100 users"""

    wait_time = between(1, 3)


class HeavyLoadUser(TOMOSAPIUser):
    """Heavy load scenario - 100+ users"""

    wait_time = between(0.5, 2)


class SpikeTestUser(TOMOSAPIUser):
    """Spike testing - sudden load increases"""

    wait_time = between(0.1, 1)
