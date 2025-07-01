#!/usr/bin/env python3
"""
Claude Code Parallel Task Executor
Advanced implementation leveraging Claude Code SDK's parallel capabilities
"""

import asyncio
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Coroutine
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import uuid

try:
    import anyio
    from claude_code_sdk import query, ClaudeCodeOptions
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.table import Table
    from rich.live import Live
    from rich.layout import Layout
    from rich.text import Text
    from rich.markdown import Markdown
except ImportError as e:
    print(f"Missing dependencies: {e}")
    print("Install: pip install claude-code-sdk rich anyio")
    exit(1)


@dataclass
class ParallelTask:
    """Represents a task for parallel execution"""
    id: str
    prompt: str
    description: str
    priority: int = 1
    max_turns: int = 5
    timeout: Optional[float] = None
    dependencies: List[str] = None
    tools_allowed: Optional[List[str]] = None
    tools_blocked: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.id is None:
            self.id = str(uuid.uuid4())[:8]


@dataclass
class TaskResult:
    """Result of a parallel task execution"""
    task_id: str
    success: bool
    result: str
    error: Optional[str] = None
    execution_time: float = 0.0
    tokens_used: Optional[int] = None


class ParallelTaskExecutor:
    """Execute multiple Claude Code tasks in parallel with sophisticated coordination"""
    
    def __init__(self, max_parallel: int = 10, console: Optional[Console] = None):
        self.max_parallel = min(max_parallel, 10)  # Claude Code limit
        self.console = console or Console()
        self.completed_tasks: Dict[str, TaskResult] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        
    async def execute_single_task(self, task: ParallelTask, progress: Progress, task_id: TaskID) -> TaskResult:
        """Execute a single Claude Code task"""
        start_time = time.time()
        result_parts = []
        
        try:
            # Create options for this specific task
            options = ClaudeCodeOptions(
                max_turns=task.max_turns,
                permission_mode="bypassPermissions"
            )
            
            # Add tool restrictions if specified
            if task.tools_allowed:
                options.allowed_tools = task.tools_allowed
            if task.tools_blocked:
                options.blocked_tools = task.tools_blocked
            
            progress.update(task_id, description=f"[blue]Executing: {task.description}")
            
            # Execute the task using Claude Code SDK
            async for message in query(prompt=task.prompt, options=options):
                if hasattr(message, 'content') and hasattr(message.content, '__iter__'):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            result_parts.append(block.text)
                elif hasattr(message, 'result'):
                    result_parts.append(str(message.result))
            
            execution_time = time.time() - start_time
            result = '\n'.join(result_parts)
            
            progress.update(task_id, description=f"[green]✓ Completed: {task.description}")
            
            return TaskResult(
                task_id=task.id,
                success=True,
                result=result,
                execution_time=execution_time
            )
            
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            progress.update(task_id, description=f"[red]⏰ Timeout: {task.description}")
            return TaskResult(
                task_id=task.id,
                success=False,
                result="",
                error="Task timeout",
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = time.time() - start_time
            progress.update(task_id, description=f"[red]✗ Failed: {task.description}")
            return TaskResult(
                task_id=task.id,
                success=False,
                result="",
                error=str(e),
                execution_time=execution_time
            )
    
    async def execute_batch(self, tasks: List[ParallelTask], show_progress: bool = True) -> Dict[str, TaskResult]:
        """Execute a batch of tasks in parallel with dependency resolution"""
        
        # Sort tasks by priority and resolve dependencies
        sorted_tasks = self._resolve_dependencies(tasks)
        
        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeElapsedColumn(),
                console=self.console
            ) as progress:
                return await self._execute_with_progress(sorted_tasks, progress)
        else:
            return await self._execute_without_progress(sorted_tasks)
    
    def _resolve_dependencies(self, tasks: List[ParallelTask]) -> List[List[ParallelTask]]:
        """Resolve task dependencies and return batches for sequential execution"""
        task_map = {task.id: task for task in tasks}
        completed = set()
        batches = []
        
        while len(completed) < len(tasks):
            # Find tasks that can run (all dependencies completed)
            ready_tasks = []
            for task in tasks:
                if task.id not in completed:
                    if all(dep in completed for dep in task.dependencies):
                        ready_tasks.append(task)
            
            if not ready_tasks:
                # Circular dependency or missing dependency
                remaining = [task for task in tasks if task.id not in completed]
                self.console.print(f"[red]Warning: Circular dependency detected. Running remaining {len(remaining)} tasks anyway.[/red]")
                ready_tasks = remaining
            
            # Sort by priority within the batch
            ready_tasks.sort(key=lambda x: x.priority, reverse=True)
            batches.append(ready_tasks)
            completed.update(task.id for task in ready_tasks)
        
        return batches
    
    async def _execute_with_progress(self, task_batches: List[List[ParallelTask]], progress: Progress) -> Dict[str, TaskResult]:
        """Execute task batches with progress tracking"""
        all_results = {}
        
        for batch_idx, batch in enumerate(task_batches):
            self.console.print(f"\n[bold blue]Executing Batch {batch_idx + 1}/{len(task_batches)}[/bold blue]")
            
            # Create progress tasks for this batch
            progress_tasks = {}
            for task in batch:
                progress_id = progress.add_task(f"Queued: {task.description}", total=1)
                progress_tasks[task.id] = progress_id
            
            # Execute batch in parallel (up to max_parallel limit)
            semaphore = asyncio.Semaphore(self.max_parallel)
            
            async def run_with_semaphore(task: ParallelTask):
                async with semaphore:
                    return await self.execute_single_task(task, progress, progress_tasks[task.id])
            
            # Execute all tasks in this batch
            batch_results = await asyncio.gather(
                *[run_with_semaphore(task) for task in batch],
                return_exceptions=True
            )
            
            # Process results
            for task, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    result = TaskResult(
                        task_id=task.id,
                        success=False,
                        result="",
                        error=str(result),
                        execution_time=0.0
                    )
                
                all_results[task.id] = result
                self.completed_tasks[task.id] = result
                progress.update(progress_tasks[task.id], completed=1)
        
        return all_results
    
    async def _execute_without_progress(self, task_batches: List[List[ParallelTask]]) -> Dict[str, TaskResult]:
        """Execute task batches without progress display"""
        all_results = {}
        
        for batch in task_batches:
            semaphore = asyncio.Semaphore(self.max_parallel)
            
            async def run_with_semaphore(task: ParallelTask):
                async with semaphore:
                    # Create a dummy progress for the method signature
                    class DummyProgress:
                        def update(self, *args, **kwargs):
                            pass
                    
                    return await self.execute_single_task(task, DummyProgress(), None)
            
            batch_results = await asyncio.gather(
                *[run_with_semaphore(task) for task in batch],
                return_exceptions=True
            )
            
            for task, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    result = TaskResult(
                        task_id=task.id,
                        success=False,
                        result="",
                        error=str(result),
                        execution_time=0.0
                    )
                
                all_results[task.id] = result
                self.completed_tasks[task.id] = result
        
        return all_results
    
    def create_codebase_exploration_tasks(self, base_path: Path, num_tasks: int = 4) -> List[ParallelTask]:
        """Create tasks for parallel codebase exploration"""
        tasks = []
        
        # Task 1: Overall architecture analysis
        tasks.append(ParallelTask(
            id="arch_analysis",
            prompt=f"Analyze the overall architecture of the codebase at {base_path}. Focus on project structure, main modules, and design patterns.",
            description="Architecture Analysis",
            priority=3,
            max_turns=3,
            tools_allowed=["Read", "Glob", "Grep", "LS"]
        ))
        
        # Task 2: Dependencies and imports analysis
        tasks.append(ParallelTask(
            id="deps_analysis",
            prompt=f"Analyze dependencies, imports, and external libraries used in {base_path}. Create a dependency map.",
            description="Dependencies Analysis",
            priority=2,
            max_turns=3,
            tools_allowed=["Read", "Glob", "Grep"]
        ))
        
        # Task 3: Code quality and patterns
        tasks.append(ParallelTask(
            id="quality_analysis",
            prompt=f"Analyze code quality, patterns, and potential issues in {base_path}. Look for code smells, best practices, and refactoring opportunities.",
            description="Code Quality Analysis",
            priority=2,
            max_turns=4,
            tools_allowed=["Read", "Glob", "Grep"]
        ))
        
        # Task 4: Documentation and testing analysis
        tasks.append(ParallelTask(
            id="docs_test_analysis",
            prompt=f"Analyze documentation coverage and testing strategies in {base_path}. Identify gaps and improvement opportunities.",
            description="Documentation & Testing Analysis",
            priority=1,
            max_turns=3,
            tools_allowed=["Read", "Glob", "Grep"]
        ))
        
        return tasks[:num_tasks]
    
    def create_feature_development_tasks(self, feature_description: str) -> List[ParallelTask]:
        """Create coordinated tasks for feature development"""
        base_id = str(uuid.uuid4())[:8]
        
        tasks = [
            ParallelTask(
                id=f"{base_id}_design",
                prompt=f"Design the architecture and API for this feature: {feature_description}. Create detailed specifications.",
                description="Feature Design",
                priority=3,
                max_turns=5,
                tools_allowed=["Read", "Write", "Glob", "Grep"]
            ),
            ParallelTask(
                id=f"{base_id}_implementation",
                prompt=f"Implement the core functionality for: {feature_description}. Follow the design specifications.",
                description="Implementation",
                priority=2,
                max_turns=8,
                dependencies=[f"{base_id}_design"],
                tools_allowed=["Read", "Write", "Edit", "Glob", "Grep"]
            ),
            ParallelTask(
                id=f"{base_id}_tests",
                prompt=f"Create comprehensive tests for the feature: {feature_description}",
                description="Test Creation",
                priority=2,
                max_turns=5,
                dependencies=[f"{base_id}_implementation"],
                tools_allowed=["Read", "Write", "Edit", "Glob", "Grep"]
            ),
            ParallelTask(
                id=f"{base_id}_docs",
                prompt=f"Create documentation for the feature: {feature_description}",
                description="Documentation",
                priority=1,
                max_turns=3,
                dependencies=[f"{base_id}_implementation"],
                tools_allowed=["Read", "Write", "Edit"]
            )
        ]
        
        return tasks
    
    def display_results_summary(self, results: Dict[str, TaskResult]) -> None:
        """Display a comprehensive summary of task results"""
        table = Table(title="Parallel Task Execution Results")
        table.add_column("Task ID", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Time (s)", justify="right")
        table.add_column("Result Preview", max_width=50)
        
        successful = 0
        total_time = 0.0
        
        for result in results.values():
            status = "[green]✓ Success[/green]" if result.success else "[red]✗ Failed[/red]"
            preview = result.result[:100] + "..." if len(result.result) > 100 else result.result
            if result.error:
                preview = f"Error: {result.error}"
            
            table.add_row(
                result.task_id,
                status,
                f"{result.execution_time:.2f}",
                preview
            )
            
            if result.success:
                successful += 1
            total_time += result.execution_time
        
        self.console.print(table)
        self.console.print(f"\n[bold]Summary:[/bold] {successful}/{len(results)} tasks successful, Total time: {total_time:.2f}s")
    
    def save_results(self, results: Dict[str, TaskResult], output_file: Path) -> None:
        """Save results to a JSON file"""
        serializable_results = {}
        for task_id, result in results.items():
            serializable_results[task_id] = asdict(result)
        
        with open(output_file, 'w') as f:
            json.dump(serializable_results, f, indent=2)
        
        self.console.print(f"[green]Results saved to {output_file}[/green]")


async def main():
    parser = argparse.ArgumentParser(description="Claude Code Parallel Task Executor")
    parser.add_argument("--max-parallel", type=int, default=4, help="Maximum parallel tasks (max 10)")
    parser.add_argument("--output", type=Path, help="Output file for results")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Explore command
    explore_parser = subparsers.add_parser("explore", help="Explore codebase in parallel")
    explore_parser.add_argument("--path", type=Path, default=Path.cwd(), help="Path to explore")
    explore_parser.add_argument("--tasks", type=int, default=4, help="Number of exploration tasks")
    
    # Feature command
    feature_parser = subparsers.add_parser("feature", help="Develop feature in parallel")
    feature_parser.add_argument("description", help="Feature description")
    
    # Custom command
    custom_parser = subparsers.add_parser("custom", help="Run custom tasks from JSON")
    custom_parser.add_argument("config", type=Path, help="JSON config file with task definitions")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    console = Console()
    executor = ParallelTaskExecutor(max_parallel=args.max_parallel, console=console)
    
    if args.command == "explore":
        console.print(f"[bold blue]Starting parallel codebase exploration of {args.path}[/bold blue]")
        tasks = executor.create_codebase_exploration_tasks(args.path, args.tasks)
        
    elif args.command == "feature":
        console.print(f"[bold blue]Starting parallel feature development: {args.description}[/bold blue]")
        tasks = executor.create_feature_development_tasks(args.description)
        
    elif args.command == "custom":
        console.print(f"[bold blue]Loading custom tasks from {args.config}[/bold blue]")
        with open(args.config) as f:
            task_configs = json.load(f)
        
        tasks = []
        for config in task_configs:
            tasks.append(ParallelTask(**config))
    
    else:
        console.print("[red]Unknown command[/red]")
        return
    
    # Execute tasks
    console.print(f"[yellow]Executing {len(tasks)} tasks with max {args.max_parallel} parallel[/yellow]")
    results = await executor.execute_batch(tasks)
    
    # Display results
    executor.display_results_summary(results)
    
    # Save results if requested
    if args.output:
        executor.save_results(results, args.output)


if __name__ == "__main__":
    anyio.run(main)