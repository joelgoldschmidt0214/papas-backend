#!/usr/bin/env python3
"""
Performance benchmark script for TOMOSU Backend API
Run this script to validate API performance requirements manually
"""

import requests
import time
import statistics
import json
import argparse
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed


class APIPerformanceBenchmark:
    """Benchmark API performance against requirements"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def benchmark_endpoint(
        self,
        endpoint: str,
        num_requests: int = 100,
        concurrent_users: int = 1,
        params: Dict = None,
    ) -> Dict[str, Any]:
        """Benchmark a specific endpoint"""
        url = f"{self.base_url}{endpoint}"
        response_times = []
        errors = []
        status_codes = []

        def make_request():
            try:
                start_time = time.time()
                response = self.session.get(url, params=params, timeout=10)
                end_time = time.time()

                response_time = end_time - start_time
                return response_time, response.status_code, None

            except Exception as e:
                return None, None, str(e)

        print(
            f"Benchmarking {endpoint} with {num_requests} requests, {concurrent_users} concurrent users..."
        )

        start_benchmark = time.time()

        if concurrent_users == 1:
            # Sequential requests
            for i in range(num_requests):
                response_time, status_code, error = make_request()

                if error:
                    errors.append(error)
                else:
                    response_times.append(response_time)
                    status_codes.append(status_code)

                if (i + 1) % 10 == 0:
                    print(f"  Completed {i + 1}/{num_requests} requests")
        else:
            # Concurrent requests
            with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                futures = [executor.submit(make_request) for _ in range(num_requests)]

                completed = 0
                for future in as_completed(futures):
                    response_time, status_code, error = future.result()

                    if error:
                        errors.append(error)
                    else:
                        response_times.append(response_time)
                        status_codes.append(status_code)

                    completed += 1
                    if completed % 10 == 0:
                        print(f"  Completed {completed}/{num_requests} requests")

        end_benchmark = time.time()
        total_time = end_benchmark - start_benchmark

        # Calculate statistics
        if response_times:
            avg_time = statistics.mean(response_times)
            median_time = statistics.median(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            p95_time = sorted(response_times)[int(len(response_times) * 0.95)]
            p99_time = sorted(response_times)[int(len(response_times) * 0.99)]

            requests_under_200ms = sum(1 for t in response_times if t < 0.2)
            performance_percentage = (requests_under_200ms / len(response_times)) * 100

            successful_requests = len(response_times)
            success_rate = (successful_requests / num_requests) * 100

            # Calculate throughput
            throughput = successful_requests / total_time
        else:
            avg_time = median_time = min_time = max_time = p95_time = p99_time = 0
            requests_under_200ms = 0
            performance_percentage = 0
            successful_requests = 0
            success_rate = 0
            throughput = 0

        return {
            "endpoint": endpoint,
            "total_requests": num_requests,
            "successful_requests": successful_requests,
            "failed_requests": len(errors),
            "success_rate": round(success_rate, 2),
            "concurrent_users": concurrent_users,
            "total_time_seconds": round(total_time, 2),
            "throughput_rps": round(throughput, 2),
            "avg_time_ms": round(avg_time * 1000, 2) if avg_time else 0,
            "median_time_ms": round(median_time * 1000, 2) if median_time else 0,
            "min_time_ms": round(min_time * 1000, 2) if min_time else 0,
            "max_time_ms": round(max_time * 1000, 2) if max_time else 0,
            "p95_time_ms": round(p95_time * 1000, 2) if p95_time else 0,
            "p99_time_ms": round(p99_time * 1000, 2) if p99_time else 0,
            "requests_under_200ms": requests_under_200ms,
            "performance_percentage": round(performance_percentage, 2),
            "meets_200ms_target": performance_percentage >= 95.0,
            "errors": errors[:10],  # Show first 10 errors
            "status_codes": dict(
                zip(
                    *zip(
                        *[
                            (code, status_codes.count(code))
                            for code in set(status_codes)
                        ]
                    )
                )
            )
            if status_codes
            else {},
        }

    def run_comprehensive_benchmark(self, num_requests: int = 100) -> Dict[str, Any]:
        """Run comprehensive benchmark across all major endpoints"""
        endpoints = [
            {"path": "/api/v1/posts", "params": {"skip": 0, "limit": 20}},
            {"path": "/api/v1/posts/1", "params": None},
            {"path": "/api/v1/users/1", "params": None},
            {"path": "/api/v1/tags", "params": None},
            {"path": "/api/v1/surveys", "params": None},
            {"path": "/api/v1/system/health", "params": None},
            {"path": "/api/v1/system/metrics", "params": None},
        ]

        results = []
        total_requests = 0
        total_successful = 0
        total_under_200ms = 0
        all_response_times = []

        print(
            f"Running comprehensive benchmark with {num_requests} requests per endpoint..."
        )
        print("=" * 80)

        for endpoint_config in endpoints:
            result = self.benchmark_endpoint(
                endpoint_config["path"],
                num_requests=num_requests,
                params=endpoint_config["params"],
            )
            results.append(result)

            total_requests += result["total_requests"]
            total_successful += result["successful_requests"]
            total_under_200ms += result["requests_under_200ms"]

            # Collect response times for overall statistics
            if result["successful_requests"] > 0:
                # Approximate response times from statistics
                for _ in range(result["successful_requests"]):
                    all_response_times.append(result["avg_time_ms"] / 1000)

            self.print_endpoint_results(result)
            print("-" * 80)

        # Calculate overall performance
        overall_success_rate = (
            (total_successful / total_requests) * 100 if total_requests > 0 else 0
        )
        overall_performance = (
            (total_under_200ms / total_successful) * 100 if total_successful > 0 else 0
        )
        overall_avg_time = (
            statistics.mean(all_response_times) if all_response_times else 0
        )

        summary = {
            "total_endpoints": len(endpoints),
            "total_requests": total_requests,
            "total_successful": total_successful,
            "overall_success_rate": round(overall_success_rate, 2),
            "overall_performance_percentage": round(overall_performance, 2),
            "overall_avg_time_ms": round(overall_avg_time * 1000, 2),
            "meets_95_percent_target": overall_performance >= 95.0,
            "endpoint_results": results,
        }

        self.print_summary(summary)
        return summary

    def print_endpoint_results(self, result: Dict[str, Any]):
        """Print formatted results for a single endpoint"""
        print(f"Endpoint: {result['endpoint']}")
        print(
            f"  Requests: {result['total_requests']} total, {result['successful_requests']} successful"
        )
        print(f"  Success Rate: {result['success_rate']}%")
        print(
            f"  Response Times: avg={result['avg_time_ms']}ms, median={result['median_time_ms']}ms"
        )
        print(
            f"  Performance: {result['requests_under_200ms']}/{result['successful_requests']} under 200ms ({result['performance_percentage']}%)"
        )
        print(
            f"  Percentiles: P95={result['p95_time_ms']}ms, P99={result['p99_time_ms']}ms"
        )
        print(f"  Throughput: {result['throughput_rps']} requests/second")
        print(f"  Meets Target: {'✓' if result['meets_200ms_target'] else '✗'}")

        if result["errors"]:
            print(f"  Errors: {len(result['errors'])} total")
            for error in result["errors"][:3]:
                print(f"    - {error}")

    def print_summary(self, summary: Dict[str, Any]):
        """Print formatted summary results"""
        print("=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)
        print(f"Total Endpoints Tested: {summary['total_endpoints']}")
        print(f"Total Requests: {summary['total_requests']}")
        print(f"Overall Success Rate: {summary['overall_success_rate']}%")
        print(
            f"Overall Performance: {summary['overall_performance_percentage']}% under 200ms"
        )
        print(f"Overall Average Response Time: {summary['overall_avg_time_ms']}ms")
        print(
            f"Meets 95% Target: {'✓ PASS' if summary['meets_95_percent_target'] else '✗ FAIL'}"
        )

        print("\nPer-Endpoint Summary:")
        for result in summary["endpoint_results"]:
            status = "✓" if result["meets_200ms_target"] else "✗"
            print(
                f"  {status} {result['endpoint']}: {result['performance_percentage']}% under 200ms"
            )

    def run_load_test(
        self,
        endpoint: str = "/api/v1/posts",
        concurrent_users: int = 10,
        requests_per_user: int = 10,
    ) -> Dict[str, Any]:
        """Run load test with concurrent users"""
        total_requests = concurrent_users * requests_per_user

        print(f"Running load test on {endpoint}")
        print(f"Concurrent users: {concurrent_users}")
        print(f"Requests per user: {requests_per_user}")
        print(f"Total requests: {total_requests}")
        print("=" * 80)

        result = self.benchmark_endpoint(
            endpoint, num_requests=total_requests, concurrent_users=concurrent_users
        )

        self.print_endpoint_results(result)

        # Additional load test analysis
        print("\nLoad Test Analysis:")
        print(f"  System handled {result['concurrent_users']} concurrent users")
        print(f"  Throughput: {result['throughput_rps']} requests/second")
        print(f"  Load test duration: {result['total_time_seconds']} seconds")

        return result


def main():
    parser = argparse.ArgumentParser(description="TOMOSU API Performance Benchmark")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=100,
        help="Number of requests per endpoint (default: 100)",
    )
    parser.add_argument(
        "--concurrent",
        type=int,
        default=1,
        help="Number of concurrent users for load test (default: 1)",
    )
    parser.add_argument(
        "--endpoint",
        default=None,
        help="Specific endpoint to test (default: run comprehensive test)",
    )
    parser.add_argument(
        "--load-test",
        action="store_true",
        help="Run load test instead of comprehensive benchmark",
    )
    parser.add_argument(
        "--output", default=None, help="Output file for results (JSON format)"
    )

    args = parser.parse_args()

    benchmark = APIPerformanceBenchmark(args.url)

    try:
        if args.load_test:
            endpoint = args.endpoint or "/api/v1/posts"
            results = benchmark.run_load_test(
                endpoint=endpoint,
                concurrent_users=args.concurrent,
                requests_per_user=args.requests // args.concurrent,
            )
        elif args.endpoint:
            results = benchmark.benchmark_endpoint(
                args.endpoint, num_requests=args.requests
            )
            benchmark.print_endpoint_results(results)
        else:
            results = benchmark.run_comprehensive_benchmark(num_requests=args.requests)

        if args.output:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2)
            print(f"\nResults saved to {args.output}")

    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user")
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to API at {args.url}")
        print("Make sure the API server is running")
    except Exception as e:
        print(f"Error running benchmark: {e}")


if __name__ == "__main__":
    main()
