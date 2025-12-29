#!/usr/bin/env python3
"""
Advanced CI/CD Pipeline Orchestrator
Handles multi-stage deployments with parallel execution and quality gates
"""

import asyncio
import json
import sys
import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StageStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Stage:
    name: str
    commands: List[str]
    parallel: bool = False
    continue_on_error: bool = False
    timeout: int = 300
    quality_gate: Optional[Dict] = None
    status: StageStatus = StageStatus.PENDING


class PipelineOrchestrator:
    def __init__(self, config_file: str):
        with open(config_file, 'r') as f:
            self.config = json.load(f)
        
        self.stages = self._parse_stages()
        self.metrics = {
            'start_time': time.time(),
            'stages_executed': 0,
            'stages_failed': 0,
            'total_duration': 0
        }
    
    def _parse_stages(self) -> List[Stage]:
        stages = []
        for stage_config in self.config.get('stages', []):
            stages.append(Stage(
                name=stage_config['name'],
                commands=stage_config['commands'],
                parallel=stage_config.get('parallel', False),
                continue_on_error=stage_config.get('continue_on_error', False),
                timeout=stage_config.get('timeout', 300),
                quality_gate=stage_config.get('quality_gate')
            ))
        return stages
    
    async def _run_command(self, command: str, timeout: int) -> tuple:
        """Execute a shell command asynchronously"""
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout
            )
            
            return proc.returncode, stdout.decode(), stderr.decode()
        except asyncio.TimeoutError:
            logger.error(f"Command timed out after {timeout}s: {command}")
            return -1, "", "Command timeout"
        except Exception as e:
            logger.error(f"Command failed: {e}")
            return -1, "", str(e)
    
    def _check_quality_gate(self, stage: Stage, output: str) -> bool:
        """Evaluate quality gate criteria"""
        if not stage.quality_gate:
            return True
        
        gate_type = stage.quality_gate.get('type')
        threshold = stage.quality_gate.get('threshold')
        
        if gate_type == 'test_coverage':
            # Parse coverage from output
            import re
            match = re.search(r'(\d+)%\s+coverage', output)
            if match:
                coverage = int(match.group(1))
                passed = coverage >= threshold
                logger.info(f"Coverage: {coverage}% (threshold: {threshold}%)")
                return passed
        
        elif gate_type == 'test_pass_rate':
            # Parse test results
            import re
            match = re.search(r'(\d+)\s+passed.*?(\d+)\s+failed', output)
            if match:
                passed = int(match.group(1))
                failed = int(match.group(2))
                total = passed + failed
                pass_rate = (passed / total * 100) if total > 0 else 0
                gate_passed = pass_rate >= threshold
                logger.info(f"Test pass rate: {pass_rate:.1f}% (threshold: {threshold}%)")
                return gate_passed
        
        return True
    
    async def _execute_stage(self, stage: Stage) -> bool:
        """Execute a single stage"""
        logger.info(f"🚀 Starting stage: {stage.name}")
        stage.status = StageStatus.RUNNING
        start_time = time.time()
        
        try:
            if stage.parallel:
                # Execute commands in parallel
                tasks = [
                    self._run_command(cmd, stage.timeout)
                    for cmd in stage.commands
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                all_output = ""
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Command {i+1} failed: {result}")
                        if not stage.continue_on_error:
                            stage.status = StageStatus.FAILED
                            return False
                    else:
                        returncode, stdout, stderr = result
                        all_output += stdout
                        if returncode != 0:
                            logger.error(f"Command {i+1} failed: {stderr}")
                            if not stage.continue_on_error:
                                stage.status = StageStatus.FAILED
                                return False
            else:
                # Execute commands sequentially
                all_output = ""
                for cmd in stage.commands:
                    logger.info(f"Executing: {cmd}")
                    returncode, stdout, stderr = await self._run_command(cmd, stage.timeout)
                    all_output += stdout
                    
                    if returncode != 0:
                        logger.error(f"Command failed: {stderr}")
                        if not stage.continue_on_error:
                            stage.status = StageStatus.FAILED
                            return False
            
            # Check quality gate
            if not self._check_quality_gate(stage, all_output):
                logger.error(f"Quality gate failed for stage: {stage.name}")
                stage.status = StageStatus.FAILED
                return False
            
            duration = time.time() - start_time
            logger.info(f"✅ Stage '{stage.name}' completed in {duration:.2f}s")
            stage.status = StageStatus.SUCCESS
            return True
            
        except Exception as e:
            logger.error(f"Stage '{stage.name}' failed: {e}")
            stage.status = StageStatus.FAILED
            return False
    
    async def execute_pipeline(self) -> bool:
        """Execute the entire pipeline"""
        logger.info("=" * 60)
        logger.info(f"Starting pipeline: {self.config.get('name', 'Unnamed')}")
        logger.info("=" * 60)
        
        for stage in self.stages:
            self.metrics['stages_executed'] += 1
            
            success = await self._execute_stage(stage)
            
            if not success:
                self.metrics['stages_failed'] += 1
                logger.error(f"Pipeline failed at stage: {stage.name}")
                self._print_summary()
                return False
        
        self.metrics['total_duration'] = time.time() - self.metrics['start_time']
        self._print_summary()
        return True
    
    def _print_summary(self):
        """Print pipeline execution summary"""
        logger.info("\n" + "=" * 60)
        logger.info("PIPELINE SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total duration: {self.metrics['total_duration']:.2f}s")
        logger.info(f"Stages executed: {self.metrics['stages_executed']}")
        logger.info(f"Stages failed: {self.metrics['stages_failed']}")
        
        logger.info("\nStage Status:")
        for stage in self.stages:
            status_icon = {
                StageStatus.SUCCESS: "✅",
                StageStatus.FAILED: "❌",
                StageStatus.SKIPPED: "⏭️",
                StageStatus.PENDING: "⏸️"
            }.get(stage.status, "❓")
            logger.info(f"  {status_icon} {stage.name}: {stage.status.value}")


async def main():
    if len(sys.argv) < 2:
        print("Usage: pipeline_orchestrator.py <config.json>")
        sys.exit(1)
    
    orchestrator = PipelineOrchestrator(sys.argv[1])
    success = await orchestrator.execute_pipeline()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
