#!/usr/bin/env python3
"""
Advanced Deployment Pipeline Monitor
Used in production systems for pre-deployment validation and runtime monitoring
"""
import os
import sys
import json
import logging
import requests
import subprocess
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time
from datetime import datetime
import hashlib
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('deployment_monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class Severity(Enum):
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class EnvVarConfig:
    """Configuration for environment variable validation"""
    name: str
    required: bool = True
    sensitive: bool = False
    pattern: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    allowed_values: Optional[List[str]] = None
    description: str = ""


@dataclass
class ValidationResult:
    """Result of a validation check"""
    passed: bool
    severity: Severity
    message: str
    details: Dict = field(default_factory=dict)


class DeploymentMonitor:
    """
    Comprehensive deployment pipeline monitor used in production
    Validates env vars, checks services, monitors health endpoints
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.results: List[ValidationResult] = []
        self.start_time = time.time()
        
    def _load_config(self, path: Optional[str]) -> Dict:
        """Load configuration from file or use defaults"""
        if path and os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Default configuration for common production scenarios"""
        return {
            "env_vars": [
                {
                    "name": "DATABASE_URL",
                    "required": True,
                    "sensitive": True,
                    "pattern": r"^(postgresql|mysql|mongodb):\/\/.+",
                    "description": "Database connection string"
                },
                {
                    "name": "REDIS_URL",
                    "required": True,
                    "sensitive": True,
                    "pattern": r"^redis:\/\/.+",
                    "description": "Redis connection string"
                },
                {
                    "name": "API_KEY",
                    "required": True,
                    "sensitive": True,
                    "min_length": 32,
                    "description": "API authentication key"
                },
                {
                    "name": "JWT_SECRET",
                    "required": True,
                    "sensitive": True,
                    "min_length": 32,
                    "description": "JWT signing secret"
                },
                {
                    "name": "ENVIRONMENT",
                    "required": True,
                    "allowed_values": ["development", "staging", "production"],
                    "description": "Deployment environment"
                },
                {
                    "name": "LOG_LEVEL",
                    "required": False,
                    "allowed_values": ["DEBUG", "INFO", "WARNING", "ERROR"],
                    "description": "Application log level"
                },
                {
                    "name": "PORT",
                    "required": False,
                    "pattern": r"^\d{2,5}$",
                    "description": "Application port"
                },
                {
                    "name": "AWS_REGION",
                    "required": False,
                    "pattern": r"^[a-z]{2}-[a-z]+-\d$",
                    "description": "AWS region"
                },
                {
                    "name": "SENTRY_DSN",
                    "required": False,
                    "sensitive": True,
                    "pattern": r"^https:\/\/.*@.*\.ingest\.sentry\.io\/\d+$",
                    "description": "Sentry error tracking DSN"
                }
            ],
            "health_checks": [
                {
                    "name": "application",
                    "url": "http://localhost:8000/health",
                    "timeout": 5,
                    "expected_status": 200
                },
                {
                    "name": "database",
                    "url": "http://localhost:8000/health/db",
                    "timeout": 10,
                    "expected_status": 200
                },
                {
                    "name": "cache",
                    "url": "http://localhost:8000/health/cache",
                    "timeout": 5,
                    "expected_status": 200
                }
            ],
            "thresholds": {
                "max_critical": 0,
                "max_errors": 0,
                "max_warnings": 5
            }
        }
    
    def validate_env_vars(self) -> bool:
        """Validate all environment variables against configuration"""
        logger.info("=" * 60)
        logger.info("ENVIRONMENT VARIABLE VALIDATION")
        logger.info("=" * 60)
        
        all_valid = True
        missing = []
        invalid = []
        
        for var_config in self.config.get("env_vars", []):
            env_var = EnvVarConfig(**var_config)
            result = self._validate_single_env_var(env_var)
            self.results.append(result)
            
            if not result.passed:
                all_valid = False
                if env_var.required:
                    missing.append(env_var.name) if not os.getenv(env_var.name) else invalid.append(env_var.name)
                
            self._log_result(result)
        
        if missing:
            logger.error(f"Missing required variables: {', '.join(missing)}")
        if invalid:
            logger.error(f"Invalid variables: {', '.join(invalid)}")
            
        return all_valid
    
    def _validate_single_env_var(self, config: EnvVarConfig) -> ValidationResult:
        """Validate a single environment variable"""
        value = os.getenv(config.name)
        
        # Check if required variable exists
        if config.required and not value:
            return ValidationResult(
                passed=False,
                severity=Severity.CRITICAL,
                message=f"Missing required env var: {config.name}",
                details={"description": config.description}
            )
        
        # If not required and not present, skip
        if not value:
            return ValidationResult(
                passed=True,
                severity=Severity.INFO,
                message=f"Optional env var not set: {config.name}",
                details={}
            )
        
        # Validate length
        if config.min_length and len(value) < config.min_length:
            return ValidationResult(
                passed=False,
                severity=Severity.ERROR,
                message=f"{config.name} length below minimum ({config.min_length})",
                details={"actual_length": len(value)}
            )
        
        if config.max_length and len(value) > config.max_length:
            return ValidationResult(
                passed=False,
                severity=Severity.ERROR,
                message=f"{config.name} length exceeds maximum ({config.max_length})",
                details={"actual_length": len(value)}
            )
        
        # Validate pattern
        if config.pattern and not re.match(config.pattern, value):
            return ValidationResult(
                passed=False,
                severity=Severity.ERROR,
                message=f"{config.name} does not match required pattern",
                details={"pattern": config.pattern}
            )
        
        # Validate allowed values
        if config.allowed_values and value not in config.allowed_values:
            return ValidationResult(
                passed=False,
                severity=Severity.ERROR,
                message=f"{config.name} has invalid value",
                details={
                    "allowed": config.allowed_values,
                    "actual": value
                }
            )
        
        # Check for common security issues
        security_check = self._check_security(config.name, value, config.sensitive)
        if not security_check.passed:
            return security_check
        
        return ValidationResult(
            passed=True,
            severity=Severity.INFO,
            message=f"✓ {config.name} validated",
            details={"masked_value": self._mask_value(value, config.sensitive)}
        )
    
    def _check_security(self, name: str, value: str, sensitive: bool) -> ValidationResult:
        """Check for common security issues"""
        # Check for weak secrets
        if sensitive and any(weak in value.lower() for weak in ["password", "12345", "secret", "test"]):
            return ValidationResult(
                passed=False,
                severity=Severity.WARNING,
                message=f"{name} may contain weak or test credentials",
                details={}
            )
        
        # Check for development values in production
        env = os.getenv("ENVIRONMENT", "").lower()
        if env == "production":
            dev_indicators = ["localhost", "127.0.0.1", "example.com", "test", "dev"]
            if any(indicator in value.lower() for indicator in dev_indicators):
                return ValidationResult(
                    passed=False,
                    severity=Severity.WARNING,
                    message=f"{name} contains development indicators in production",
                    details={}
                )
        
        return ValidationResult(passed=True, severity=Severity.INFO, message="", details={})
    
    def _mask_value(self, value: str, sensitive: bool) -> str:
        """Mask sensitive values for logging"""
        if not sensitive:
            return value
        if len(value) <= 8:
            return "****"
        return f"{value[:4]}...{value[-4:]}"
    
    def check_health_endpoints(self) -> bool:
        """Check health endpoints for all services"""
        logger.info("\n" + "=" * 60)
        logger.info("HEALTH ENDPOINT CHECKS")
        logger.info("=" * 60)
        
        all_healthy = True
        
        for check in self.config.get("health_checks", []):
            result = self._check_single_endpoint(check)
            self.results.append(result)
            self._log_result(result)
            
            if not result.passed:
                all_healthy = False
        
        return all_healthy
    
    def _check_single_endpoint(self, check: Dict) -> ValidationResult:
        """Check a single health endpoint"""
        try:
            response = requests.get(
                check["url"],
                timeout=check.get("timeout", 5)
            )
            
            if response.status_code == check.get("expected_status", 200):
                return ValidationResult(
                    passed=True,
                    severity=Severity.INFO,
                    message=f"✓ {check['name']} health check passed",
                    details={
                        "url": check["url"],
                        "status": response.status_code,
                        "response_time": response.elapsed.total_seconds()
                    }
                )
            else:
                return ValidationResult(
                    passed=False,
                    severity=Severity.ERROR,
                    message=f"✗ {check['name']} returned unexpected status",
                    details={
                        "url": check["url"],
                        "expected": check.get("expected_status", 200),
                        "actual": response.status_code
                    }
                )
        except requests.Timeout:
            return ValidationResult(
                passed=False,
                severity=Severity.ERROR,
                message=f"✗ {check['name']} health check timed out",
                details={"url": check["url"], "timeout": check.get("timeout", 5)}
            )
        except Exception as e:
            return ValidationResult(
                passed=False,
                severity=Severity.CRITICAL,
                message=f"✗ {check['name']} health check failed",
                details={"url": check["url"], "error": str(e)}
            )
    
    def check_deployment_readiness(self) -> bool:
        """Perform pre-deployment readiness checks"""
        logger.info("\n" + "=" * 60)
        logger.info("DEPLOYMENT READINESS CHECKS")
        logger.info("=" * 60)
        
        checks = [
            self._check_git_status,
            self._check_dependencies,
            self._check_disk_space,
            self._check_memory
        ]
        
        all_ready = True
        for check in checks:
            try:
                result = check()
                self.results.append(result)
                self._log_result(result)
                if not result.passed:
                    all_ready = False
            except Exception as e:
                logger.error(f"Check failed: {e}")
                all_ready = False
        
        return all_ready
    
    def _check_git_status(self) -> ValidationResult:
        """Check git status for uncommitted changes"""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.stdout.strip():
                return ValidationResult(
                    passed=False,
                    severity=Severity.WARNING,
                    message="Uncommitted changes detected",
                    details={"changes": result.stdout.strip()}
                )
            
            return ValidationResult(
                passed=True,
                severity=Severity.INFO,
                message="✓ Git status clean",
                details={}
            )
        except Exception as e:
            return ValidationResult(
                passed=True,
                severity=Severity.INFO,
                message="Git check skipped",
                details={"reason": str(e)}
            )
    
    def _check_dependencies(self) -> ValidationResult:
        """Check for dependency issues"""
        # Example: Check if requirements.txt exists
        if os.path.exists("requirements.txt"):
            return ValidationResult(
                passed=True,
                severity=Severity.INFO,
                message="✓ Dependencies file found",
                details={}
            )
        
        return ValidationResult(
            passed=False,
            severity=Severity.WARNING,
            message="No requirements.txt found",
            details={}
        )
    
    def _check_disk_space(self) -> ValidationResult:
        """Check available disk space"""
        try:
            import shutil
            stat = shutil.disk_usage("/")
            free_gb = stat.free / (1024**3)
            
            if free_gb < 1:
                return ValidationResult(
                    passed=False,
                    severity=Severity.CRITICAL,
                    message="Critical: Low disk space",
                    details={"free_gb": round(free_gb, 2)}
                )
            
            return ValidationResult(
                passed=True,
                severity=Severity.INFO,
                message=f"✓ Disk space available: {round(free_gb, 2)}GB",
                details={}
            )
        except Exception as e:
            return ValidationResult(
                passed=True,
                severity=Severity.INFO,
                message="Disk space check skipped",
                details={"reason": str(e)}
            )
    
    def _check_memory(self) -> ValidationResult:
        """Check available memory"""
        try:
            import psutil
            mem = psutil.virtual_memory()
            
            if mem.percent > 90:
                return ValidationResult(
                    passed=False,
                    severity=Severity.WARNING,
                    message=f"High memory usage: {mem.percent}%",
                    details={"available_gb": round(mem.available / (1024**3), 2)}
                )
            
            return ValidationResult(
                passed=True,
                severity=Severity.INFO,
                message=f"✓ Memory available: {round(mem.available / (1024**3), 2)}GB",
                details={}
            )
        except ImportError:
            return ValidationResult(
                passed=True,
                severity=Severity.INFO,
                message="Memory check skipped (psutil not installed)",
                details={}
            )
    
    def _log_result(self, result: ValidationResult):
        """Log a validation result"""
        log_func = {
            Severity.CRITICAL: logger.critical,
            Severity.ERROR: logger.error,
            Severity.WARNING: logger.warning,
            Severity.INFO: logger.info
        }[result.severity]
        
        log_func(result.message)
        if result.details:
            logger.debug(f"  Details: {json.dumps(result.details, indent=2)}")
    
    def generate_report(self) -> Dict:
        """Generate comprehensive validation report"""
        elapsed = time.time() - self.start_time
        
        severity_counts = {s: 0 for s in Severity}
        for result in self.results:
            severity_counts[result.severity] += 1
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(elapsed, 2),
            "total_checks": len(self.results),
            "passed": sum(1 for r in self.results if r.passed),
            "failed": sum(1 for r in self.results if not r.passed),
            "severity_counts": {s.value: count for s, count in severity_counts.items()},
            "deployment_approved": self._should_approve_deployment()
        }
        
        return report
    
    def _should_approve_deployment(self) -> bool:
        """Determine if deployment should be approved based on thresholds"""
        thresholds = self.config.get("thresholds", {})
        severity_counts = {s: 0 for s in Severity}
        
        for result in self.results:
            if not result.passed:
                severity_counts[result.severity] += 1
        
        if severity_counts[Severity.CRITICAL] > thresholds.get("max_critical", 0):
            return False
        if severity_counts[Severity.ERROR] > thresholds.get("max_errors", 0):
            return False
        if severity_counts[Severity.WARNING] > thresholds.get("max_warnings", 5):
            return False
        
        return True
    
    def run_full_validation(self) -> Tuple[bool, Dict]:
        """Run complete validation pipeline"""
        logger.info("Starting deployment validation pipeline...")
        
        env_valid = self.validate_env_vars()
        readiness_valid = self.check_deployment_readiness()
        # health_valid = self.check_health_endpoints()  # Uncomment if services are running
        
        report = self.generate_report()
        
        logger.info("\n" + "=" * 60)
        logger.info("VALIDATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total checks: {report['total_checks']}")
        logger.info(f"Passed: {report['passed']}")
        logger.info(f"Failed: {report['failed']}")
        logger.info(f"Duration: {report['duration_seconds']}s")
        logger.info(f"Deployment approved: {report['deployment_approved']}")
        
        return report["deployment_approved"], report


def main():
    """Main entry point"""
    monitor = DeploymentMonitor()
    
    approved, report = monitor.run_full_validation()
    
    # Save report
    with open("deployment_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    # Exit with appropriate code
    sys.exit(0 if approved else 1)


if __name__ == "__main__":
    main()
