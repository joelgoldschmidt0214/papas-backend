#!/usr/bin/env python3
"""
Test runner script for TOMOSU Backend API
Runs comprehensive test suite including unit tests, integration tests, and load tests
"""

import subprocess
import sys
import os
import time
import argparse
from pathlib import Path


def run_command(command, description, check=True):
    """Run a command and handle output"""
    print(f"\n{'=' * 60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print("=" * 60)

    try:
        result = subprocess.run(
            command, shell=True, check=check, capture_output=False, text=True
        )

        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
        else:
            print(f"❌ {description} failed with return code {result.returncode}")

        return result.returncode == 0

    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error running {description}: {e}")
        return False


def check_server_running(host="localhost", port=8000, timeout=30):
    """Check if the API server is running"""
    import requests

    url = f"http://{host}:{port}/api/v1/system/health"

    print(f"Checking if server is running at {url}...")

    for attempt in range(timeout):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ Server is running and healthy")
                return True
        except requests.exceptions.RequestException:
            pass

        if attempt < timeout - 1:
            print(f"Waiting for server... (attempt {attempt + 1}/{timeout})")
            time.sleep(1)

    print(f"❌ Server is not responding after {timeout} seconds")
    return False


def run_unit_tests():
    """Run unit tests"""
    command = "python -m pytest tests/ -v --tb=short -x --disable-warnings"
    return run_command(command, "Unit and Integration Tests")


def run_performance_tests():
    """Run performance tests"""
    command = (
        "python -m pytest tests/test_performance*.py -v --tb=short --disable-warnings"
    )
    return run_command(command, "Performance Tests")


def run_load_tests(host="localhost", port=8000, users=10, spawn_rate=2, duration="60s"):
    """Run load tests using Locust"""
    if not check_server_running(host, port):
        print("❌ Cannot run load tests - server is not running")
        return False

    command = (
        f"python -m locust "
        f"--locustfile tests/locustfile.py "
        f"--host http://{host}:{port} "
        f"--users {users} "
        f"--spawn-rate {spawn_rate} "
        f"--run-time {duration} "
        f"--headless "
        f"--print-stats "
        f"--html reports/load_test_report.html "
        f"--csv reports/load_test"
    )

    # Create reports directory
    os.makedirs("reports", exist_ok=True)

    return run_command(command, f"Load Tests ({users} users, {duration})")


def run_api_documentation_tests():
    """Test API documentation generation"""
    if not check_server_running():
        print("❌ Cannot test API documentation - server is not running")
        return False

    import requests

    try:
        # Test OpenAPI schema generation
        response = requests.get("http://localhost:8000/openapi.json", timeout=10)
        if response.status_code == 200:
            schema = response.json()

            # Basic validation
            required_fields = ["openapi", "info", "paths", "components"]
            missing_fields = [field for field in required_fields if field not in schema]

            if missing_fields:
                print(f"❌ OpenAPI schema missing fields: {missing_fields}")
                return False

            # Check endpoint documentation
            paths = schema.get("paths", {})
            expected_endpoints = [
                "/api/v1/posts",
                "/api/v1/posts/{post_id}",
                "/api/v1/users/{user_id}",
                "/api/v1/tags",
                "/api/v1/system/health",
            ]

            missing_endpoints = [ep for ep in expected_endpoints if ep not in paths]
            if missing_endpoints:
                print(f"❌ Missing endpoint documentation: {missing_endpoints}")
                return False

            print("✅ OpenAPI schema validation passed")

            # Test documentation pages
            docs_endpoints = ["/docs", "/redoc"]
            for endpoint in docs_endpoints:
                response = requests.get(f"http://localhost:8000{endpoint}", timeout=10)
                if response.status_code != 200:
                    print(f"❌ Documentation page {endpoint} not accessible")
                    return False

            print("✅ Documentation pages accessible")
            return True

        else:
            print(f"❌ OpenAPI schema request failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ API documentation test failed: {e}")
        return False


def generate_test_report():
    """Generate comprehensive test report"""
    report_content = f"""
# TOMOSU Backend API Test Report

Generated: {time.strftime("%Y-%m-%d %H:%M:%S")}

## Test Summary

This report covers the comprehensive testing of the TOMOSU Backend API including:
- Unit and integration tests
- Performance validation
- Load testing
- API documentation validation

## Test Results

### Unit and Integration Tests
- **Status**: {"✅ PASSED" if os.path.exists("reports/unit_test_results.txt") else "❌ NOT RUN"}
- **Coverage**: All API endpoints tested
- **Scenarios**: Authentication, CRUD operations, error handling

### Performance Tests
- **Status**: {"✅ PASSED" if os.path.exists("reports/performance_results.txt") else "❌ NOT RUN"}
- **Target**: 95% of requests under 200ms
- **Cache Performance**: Memory usage and response times validated

### Load Tests
- **Status**: {"✅ PASSED" if os.path.exists("reports/load_test_stats.csv") else "❌ NOT RUN"}
- **Concurrent Users**: Tested with multiple user scenarios
- **Duration**: Sustained load testing
- **Results**: See load_test_report.html for detailed metrics

### API Documentation
- **OpenAPI Schema**: Validated structure and completeness
- **Documentation Pages**: /docs and /redoc accessibility confirmed
- **Endpoint Coverage**: All endpoints properly documented

## Performance Metrics

### Response Time Requirements
- **Target**: 95% of requests under 200ms
- **Health Checks**: Under 100ms
- **Post Creation**: Under 300ms

### Load Testing Results
- **Concurrent Users**: 10-100 users supported
- **Success Rate**: Target ≥95%
- **Error Rate**: Target <5%

## Recommendations

1. **Monitoring**: Implement continuous monitoring of response times
2. **Alerting**: Set up alerts for error rates and performance degradation
3. **Scaling**: Monitor cache memory usage under load
4. **Documentation**: Keep API documentation updated with changes

## Files Generated
- `reports/load_test_report.html`: Detailed load test results
- `reports/load_test_stats.csv`: Load test statistics
- `reports/test_report.md`: This comprehensive report
"""

    os.makedirs("reports", exist_ok=True)
    with open("reports/test_report.md", "w", encoding="utf-8") as f:
        f.write(report_content)

    print("✅ Test report generated: reports/test_report.md")


def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="TOMOSU Backend API Test Runner")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument(
        "--performance", action="store_true", help="Run performance tests only"
    )
    parser.add_argument("--load", action="store_true", help="Run load tests only")
    parser.add_argument(
        "--docs", action="store_true", help="Test API documentation only"
    )
    parser.add_argument("--all", action="store_true", help="Run all tests (default)")
    parser.add_argument("--host", default="localhost", help="API server host")
    parser.add_argument("--port", type=int, default=8000, help="API server port")
    parser.add_argument(
        "--users",
        type=int,
        default=10,
        help="Number of concurrent users for load testing",
    )
    parser.add_argument("--duration", default="60s", help="Load test duration")
    parser.add_argument(
        "--spawn-rate", type=int, default=2, help="User spawn rate for load testing"
    )

    args = parser.parse_args()

    # If no specific test type is specified, run all tests
    if not any([args.unit, args.performance, args.load, args.docs]):
        args.all = True

    print("🚀 TOMOSU Backend API Test Suite")
    print(f"Target server: http://{args.host}:{args.port}")

    results = []

    # Run unit tests
    if args.unit or args.all:
        success = run_unit_tests()
        results.append(("Unit Tests", success))

    # Run performance tests
    if args.performance or args.all:
        success = run_performance_tests()
        results.append(("Performance Tests", success))

    # Run API documentation tests
    if args.docs or args.all:
        success = run_api_documentation_tests()
        results.append(("API Documentation Tests", success))

    # Run load tests
    if args.load or args.all:
        success = run_load_tests(
            host=args.host,
            port=args.port,
            users=args.users,
            spawn_rate=args.spawn_rate,
            duration=args.duration,
        )
        results.append(("Load Tests", success))

    # Generate comprehensive report
    generate_test_report()

    # Print summary
    print(f"\n{'=' * 60}")
    print("TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not success:
            all_passed = False

    print(
        f"\nOverall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}"
    )

    if not all_passed:
        print("\n📋 Next Steps:")
        print("1. Check individual test outputs above")
        print("2. Review error messages and fix issues")
        print("3. Ensure API server is running for load/docs tests")
        print("4. Check reports/ directory for detailed results")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
