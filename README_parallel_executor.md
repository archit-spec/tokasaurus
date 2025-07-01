# Claude Code Parallel Task Executor

A sophisticated implementation leveraging Claude Code SDK's parallel capabilities for concurrent task execution with dependency resolution, progress tracking, and result coordination.

## Features

### Core Capabilities
- **Parallel Task Execution**: Run up to 10 concurrent Claude Code agents (SDK limit)
- **Dependency Resolution**: Smart scheduling with task dependencies
- **Progress Tracking**: Real-time visual progress with Rich console
- **Batch Processing**: Organize tasks into dependency-resolved batches
- **Result Coordination**: Comprehensive result collection and analysis
- **Tool Restrictions**: Per-task tool allowlists and blocklists

### Predefined Task Templates
- **Codebase Exploration**: Parallel analysis of architecture, dependencies, quality, and documentation
- **Feature Development**: Coordinated design → implementation → testing → documentation pipeline
- **Custom Tasks**: JSON-configurable task definitions with full flexibility

## Installation

```bash
pip install claude-code-sdk rich anyio
```

## Usage Examples

### 1. Parallel Codebase Exploration

```bash
# Explore current directory with 4 parallel agents
python claude_parallel_executor.py explore --path . --tasks 4

# Explore specific project with custom parallel count
python claude_parallel_executor.py explore --path /path/to/project --tasks 6 --max-parallel 6
```

### 2. Coordinated Feature Development

```bash
# Develop a new authentication system
python claude_parallel_executor.py feature "user authentication with JWT tokens"

# Develop API endpoints with documentation
python claude_parallel_executor.py feature "REST API for product catalog management"
```

### 3. Custom Task Configuration

```bash
# Run custom tasks from JSON configuration
python claude_parallel_executor.py custom example_parallel_tasks.json --output results.json
```

## Task Configuration Format

```json
{
  "id": "unique_task_id",
  "prompt": "Detailed prompt for Claude Code agent",
  "description": "Human-readable task description",
  "priority": 3,
  "max_turns": 5,
  "timeout": 300.0,
  "dependencies": ["other_task_id"],
  "tools_allowed": ["Read", "Write", "Edit", "Glob", "Grep"],
  "tools_blocked": ["Bash"]
}
```

## Advanced Features

### Dependency Resolution
Tasks can depend on other tasks, creating sophisticated workflows:
```python
design_task = ParallelTask(id="design", ...)
implement_task = ParallelTask(id="implement", dependencies=["design"], ...)
test_task = ParallelTask(id="test", dependencies=["implement"], ...)
```

### Tool Control
Fine-grained control over which tools each agent can use:
```python
readonly_task = ParallelTask(
    tools_allowed=["Read", "Glob", "Grep"],  # Read-only operations
    tools_blocked=["Write", "Edit", "Bash"]  # No file modifications
)
```

### Progress Tracking
Real-time visual feedback with Rich console:
- Spinner animations for active tasks
- Progress bars for completed work
- Color-coded status indicators
- Execution time tracking

## Architecture

### ParallelTask Class
Defines individual tasks with configuration:
- **Identification**: Unique ID and description
- **Execution**: Prompt, turn limits, timeouts
- **Dependencies**: Task ordering and coordination
- **Tools**: Allowed/blocked tool restrictions

### ParallelTaskExecutor Class
Manages concurrent execution:
- **Batching**: Dependency-resolved execution batches
- **Coordination**: Semaphore-based parallel limits
- **Monitoring**: Progress tracking and result collection
- **Error Handling**: Graceful failure management

### TaskResult Class
Comprehensive execution results:
- **Success/Failure**: Execution status
- **Output**: Full Claude Code response
- **Metrics**: Execution time and resource usage
- **Errors**: Detailed error information

## Practical Use Cases

### 1. Large Codebase Analysis
```bash
# Analyze a complex project with specialized agents
python claude_parallel_executor.py explore --path /large/project --tasks 8
```

### 2. Code Review Workflow
```json
[
  {"id": "security", "prompt": "Security audit...", "priority": 3},
  {"id": "performance", "prompt": "Performance analysis...", "priority": 2},
  {"id": "style", "prompt": "Code style review...", "priority": 1},
  {"id": "summary", "prompt": "Combine findings...", "dependencies": ["security", "performance", "style"]}
]
```

### 3. Documentation Generation
```json
[
  {"id": "api_docs", "prompt": "Generate API documentation...", "tools_allowed": ["Read", "Write"]},
  {"id": "user_guide", "prompt": "Create user guide...", "tools_allowed": ["Read", "Write"]},
  {"id": "dev_guide", "prompt": "Developer setup guide...", "dependencies": ["api_docs"]}
]
```

## Best Practices

### Task Design
- **Focused Prompts**: Clear, specific instructions for each agent
- **Appropriate Scope**: Balance parallelization benefits with task complexity
- **Tool Restrictions**: Use minimal required tools for security and focus

### Dependency Management
- **Logical Flow**: Design natural task dependencies
- **Minimize Coupling**: Reduce unnecessary dependencies for better parallelization
- **Error Handling**: Plan for dependency failures

### Resource Management
- **Parallel Limits**: Stay within Claude Code's 10-agent limit
- **Turn Budgets**: Set appropriate max_turns for task complexity
- **Timeouts**: Prevent runaway tasks with reasonable timeouts

## Integration with Existing Tools

The parallel executor works seamlessly with your existing Claude Code tools:

### With Claude Wrapper
```bash
# Use wrapper configs for specialized agents
python claude_wrapper.py config --model claude-sonnet-4-20250514 --max-turns 10
python claude_parallel_executor.py explore --tasks 4
```

### With Claude TUI
```python
# Integrate parallel results into TUI workflows
executor = ParallelTaskExecutor()
results = await executor.execute_batch(tasks)
# Display results in rich TUI format
```

### With Config Manager
```bash
# Create specialized configurations for different task types
python claude_config_manager.py create analysis --allowed-tools Read Glob Grep
python claude_config_manager.py create development --allowed-tools Read Write Edit Bash
```

## Performance Considerations

- **Parallel Efficiency**: Optimal with 4-8 concurrent agents for most tasks
- **Memory Usage**: Each agent maintains separate context
- **Rate Limits**: Respects Claude Code SDK rate limiting
- **Token Usage**: Monitor cumulative token consumption across agents

## Error Handling

- **Graceful Degradation**: Failed tasks don't block others
- **Detailed Logging**: Comprehensive error reporting
- **Partial Results**: Collect successful results even with some failures
- **Retry Logic**: Manual retry capability for failed tasks

## Output and Results

### Console Output
- Real-time progress tracking
- Color-coded status indicators
- Execution time metrics
- Summary statistics

### JSON Export
```bash
python claude_parallel_executor.py custom tasks.json --output results.json
```

### Result Structure
```json
{
  "task_id": {
    "success": true,
    "result": "Full Claude Code response...",
    "execution_time": 45.2,
    "error": null
  }
}
```

This implementation showcases Claude Code SDK's powerful parallel capabilities while providing practical tools for real-world development workflows.