#!/usr/bin/env python3
"""
Deployment script for TOMOSU Backend API.

Handles deployment validation, testing, and deployment to various environments.
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path
from typing import Dict, List, Optional

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import Settings, Environment
from test_deployment import DeploymentTester


class DeploymentManager:
    """Manages deployment process and validation"""

    def __init__(self, environment: str = "development"):
        self.environment = environment
        self.start_time = time.time()
        self.deployment_steps: List[Dict] = []

    def log_step(
        self, step: str, success: bool, message: str = "", details: Dict = None
    ):
        """Log deployment step"""
        step_info = {
            "step": step,
            "success": success,
            "message": message,
            "details": details or {},
            "timestamp": time.time(),
        }
        self.deployment_steps.append(step_info)

        status = "✓" if success else "✗"
        print(f"{status} {step}")
        if message:
            print(f"  {message}")

    def run_command(self, command: List[str], description: str) -> bool:
        """Run shell command and log result"""
        try:
            print(f"Running: {' '.join(command)}")
            result = subprocess.run(command, capture_output=True, text=True, check=True)

            if result.stdout:
                print(f"Output: {result.stdout.strip()}")

            self.log_step(description, True, "Command executed successfully")
            return True

        except subprocess.CalledProcessError as e:
            error_msg = f"Command failed with exit code {e.returncode}"
            if e.stderr:
                error_msg += f": {e.stderr.strip()}"

            self.log_step(description, False, error_msg)
            return False
        except Exception as e:
            self.log_step(description, False, str(e))
            return False

    def validate_prerequisites(self) -> bool:
        """Validate deployment prerequisites"""
        print("Validating deployment prerequisites...")

        # Check Python version
        python_version = sys.version_info
        if python_version < (3, 11):
            self.log_step(
                "Python Version Check",
                False,
                f"Python 3.11+ required, found {python_version.major}.{python_version.minor}",
            )
            return False

        self.log_step(
            "Python Version Check",
            True,
            f"Python {python_version.major}.{python_version.minor}",
        )

        # Check required files
        required_files = [
            "main.py",
            "startup.py",
            "config.py",
            "logging_config.py",
            "database.py",
            "requirements.txt",
            "Dockerfile",
            ".env.example",
        ]

        missing_files = []
        for file_path in required_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)

        if missing_files:
            self.log_step(
                "Required Files Check",
                False,
                f"Missing files: {', '.join(missing_files)}",
            )
            return False

        self.log_step("Required Files Check", True, "All required files present")

        # Check environment file
        env_file = Path(".env")
        if not env_file.exists():
            self.log_step(
                "Environment File Check",
                False,
                ".env file not found. Copy .env.example to .env and configure.",
            )
            return False

        self.log_step("Environment File Check", True, ".env file found")

        return True

    def run_tests(self) -> bool:
        """Run deployment validation tests"""
        print("\nRunning deployment validation tests...")

        tester = DeploymentTester()
        success = tester.run_all_tests()

        if success:
            self.log_step("Deployment Tests", True, "All tests passed")
        else:
            self.log_step("Deployment Tests", False, "Some tests failed")

        return success

    def build_docker_image(self, tag: str = None) -> bool:
        """Build Docker image"""
        if not tag:
            tag = f"tomosu-backend:{self.environment}"

        print(f"\nBuilding Docker image: {tag}")

        return self.run_command(
            ["docker", "build", "-t", tag, "."], f"Build Docker Image ({tag})"
        )

    def test_docker_container(self, tag: str = None) -> bool:
        """Test Docker container startup"""
        if not tag:
            tag = f"tomosu-backend:{self.environment}"

        print(f"\nTesting Docker container: {tag}")

        # Start container in detached mode
        container_name = f"tomosu-test-{int(time.time())}"

        # Start container
        if not self.run_command(
            ["docker", "run", "-d", "--name", container_name, "-p", "8001:8000", tag],
            "Start Test Container",
        ):
            return False

        try:
            # Wait for container to start
            time.sleep(10)

            # Check container health
            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    container_name,
                    "curl",
                    "-f",
                    "http://localhost:8000/api/v1/system/health",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                self.log_step("Container Health Check", True, "Container is healthy")
                success = True
            else:
                self.log_step(
                    "Container Health Check", False, "Container health check failed"
                )
                success = False

        finally:
            # Clean up test container
            subprocess.run(["docker", "stop", container_name], capture_output=True)
            subprocess.run(["docker", "rm", container_name], capture_output=True)

        return success

    def deploy_local(self) -> bool:
        """Deploy locally using Docker Compose"""
        print("\nDeploying locally with Docker Compose...")

        # Build and start services
        commands = [
            (["docker-compose", "build"], "Build Services"),
            (["docker-compose", "up", "-d"], "Start Services"),
        ]

        for command, description in commands:
            if not self.run_command(command, description):
                return False

        # Wait for services to start
        print("Waiting for services to start...")
        time.sleep(15)

        # Test service health
        try:
            import httpx

            response = httpx.get(
                "http://localhost:8000/api/v1/system/health", timeout=10
            )
            if response.status_code == 200:
                self.log_step("Service Health Check", True, "Service is healthy")
                return True
            else:
                self.log_step(
                    "Service Health Check",
                    False,
                    f"Health check returned {response.status_code}",
                )
                return False
        except Exception as e:
            self.log_step("Service Health Check", False, str(e))
            return False

    def deploy_azure(self) -> bool:
        """Deploy to Azure Container Apps"""
        print("\nDeploying to Azure Container Apps...")

        # Check Azure CLI
        if not self.run_command(["az", "--version"], "Check Azure CLI"):
            print(
                "Please install Azure CLI: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
            )
            return False

        # Check login status
        if not self.run_command(["az", "account", "show"], "Check Azure Login"):
            print("Please login to Azure: az login")
            return False

        # Deploy using Azure Container Apps configuration
        config_file = "azure-container-app.yaml"
        if not Path(config_file).exists():
            self.log_step("Azure Config Check", False, f"{config_file} not found")
            return False

        print(
            f"Please review {config_file} and update with your specific values before deployment."
        )
        print(
            "Then run: az containerapp create --resource-group <rg> --environment <env> --yaml azure-container-app.yaml"
        )

        self.log_step("Azure Deployment", True, "Configuration ready for deployment")
        return True

    def cleanup(self):
        """Cleanup deployment resources"""
        print("\nCleaning up...")

        # Stop local services if running
        subprocess.run(["docker-compose", "down"], capture_output=True)

        self.log_step("Cleanup", True, "Resources cleaned up")

    def print_summary(self):
        """Print deployment summary"""
        total_steps = len(self.deployment_steps)
        successful_steps = sum(1 for step in self.deployment_steps if step["success"])
        failed_steps = total_steps - successful_steps

        print("\n" + "=" * 60)
        print("DEPLOYMENT SUMMARY")
        print("=" * 60)
        print(f"Environment: {self.environment}")
        print(f"Total Steps: {total_steps}")
        print(f"Successful: {successful_steps}")
        print(f"Failed: {failed_steps}")
        print(f"Total Time: {time.time() - self.start_time:.2f}s")

        if failed_steps > 0:
            print("\nFAILED STEPS:")
            for step in self.deployment_steps:
                if not step["success"]:
                    print(f"  - {step['step']}: {step['message']}")

        return failed_steps == 0


def main():
    """Main deployment function"""
    parser = argparse.ArgumentParser(description="Deploy TOMOSU Backend API")
    parser.add_argument(
        "--environment",
        choices=["development", "staging", "production"],
        default="development",
        help="Deployment environment",
    )
    parser.add_argument(
        "--target",
        choices=["local", "docker", "azure"],
        default="local",
        help="Deployment target",
    )
    parser.add_argument(
        "--skip-tests", action="store_true", help="Skip deployment validation tests"
    )
    parser.add_argument(
        "--build-only",
        action="store_true",
        help="Only build Docker image, don't deploy",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("TOMOSU Backend API - Deployment Manager")
    print("=" * 60)
    print(f"Environment: {args.environment}")
    print(f"Target: {args.target}")
    print(f"Skip Tests: {args.skip_tests}")

    deployment = DeploymentManager(args.environment)

    try:
        # Step 1: Validate prerequisites
        if not deployment.validate_prerequisites():
            print("\n❌ Prerequisites validation failed")
            return 1

        # Step 2: Run tests (unless skipped)
        if not args.skip_tests:
            if not deployment.run_tests():
                print("\n❌ Deployment tests failed")
                return 1

        # Step 3: Build Docker image
        if args.target in ["docker", "azure"] or args.build_only:
            if not deployment.build_docker_image():
                print("\n❌ Docker build failed")
                return 1

            if args.build_only:
                print("\n🎉 Docker image built successfully!")
                return 0

        # Step 4: Deploy based on target
        success = False
        if args.target == "local":
            success = deployment.deploy_local()
        elif args.target == "docker":
            success = deployment.test_docker_container()
        elif args.target == "azure":
            success = deployment.deploy_azure()

        if success:
            print(f"\n🎉 Deployment to {args.target} completed successfully!")
            return 0
        else:
            print(f"\n❌ Deployment to {args.target} failed")
            return 1

    except KeyboardInterrupt:
        print("\n⚠️  Deployment interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Deployment failed with error: {e}")
        return 1
    finally:
        deployment.print_summary()
        if args.target == "local":
            deployment.cleanup()


if __name__ == "__main__":
    sys.exit(main())
