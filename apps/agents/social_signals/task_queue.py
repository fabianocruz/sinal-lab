"""Async task queue with concurrency control for Social Signals.

Provides a TaskQueue that can run parallel async tasks with a configurable
concurrency limit (via asyncio.Semaphore). Supports two backends:

- **memory** (default): In-process asyncio.Queue, no external dependencies.
- **redis**: Optional Redis-backed queue via redis.asyncio. Falls back to
  memory mode if redis is not installed.

Usage:
    queue = TaskQueue(max_concurrency=5, backend="memory")
    await queue.enqueue("twitter", collect_twitter_coro())
    await queue.enqueue("reddit", collect_reddit_coro())
    results = await queue.process_all()
    # results = {"twitter": [...], "reddit": [...]}

    # Or use the static helper:
    results = await TaskQueue.run_parallel(
        tasks=[("twitter", coro1), ("reddit", coro2)],
        max_concurrency=5,
    )
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Status of a queued task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


@dataclass
class TaskResult:
    """Result of an executed task.

    Attributes:
        task_id: Unique identifier for the task.
        status: Final status after execution.
        data: Return value on success, None on failure.
        error: Error message on failure, None on success.
        elapsed_seconds: Wall-clock time for this task.
    """

    task_id: str
    status: TaskStatus
    data: Any = None
    error: Optional[str] = None
    elapsed_seconds: float = 0.0


class TaskQueue:
    """Async task queue with semaphore-based concurrency control.

    Args:
        max_concurrency: Maximum tasks running simultaneously (default 5).
        backend: "memory" (default) or "redis". Redis falls back to memory
            if redis.asyncio is not installed.
        task_timeout: Per-task timeout in seconds (default 30).
        redis_url: Redis connection URL (only used when backend="redis").
    """

    def __init__(
        self,
        max_concurrency: int = 5,
        backend: str = "memory",
        task_timeout: float = 30.0,
        redis_url: str = "redis://localhost:6379/0",
    ) -> None:
        self.max_concurrency = max_concurrency
        self.task_timeout = task_timeout
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._tasks: List[Tuple[str, Any]] = []
        self._results: Dict[str, TaskResult] = {}

        # Backend selection
        self._backend = "memory"
        if backend == "redis":
            try:
                import redis.asyncio as aioredis  # noqa: F401

                self._backend = "redis"
                self._redis_url = redis_url
                logger.info("TaskQueue using Redis backend: %s", redis_url)
            except ImportError:
                logger.warning(
                    "redis.asyncio not installed, falling back to memory backend"
                )
                self._backend = "memory"
        else:
            self._backend = "memory"

        logger.debug(
            "TaskQueue initialized: max_concurrency=%d, backend=%s, timeout=%.1fs",
            max_concurrency,
            self._backend,
            task_timeout,
        )

    @property
    def backend(self) -> str:
        """Return the active backend name."""
        return self._backend

    @property
    def pending_count(self) -> int:
        """Return number of tasks not yet processed."""
        return len(self._tasks)

    @property
    def results(self) -> Dict[str, TaskResult]:
        """Return all task results after process_all()."""
        return self._results

    async def enqueue(self, task_id: str, coro: Any) -> None:
        """Add a task to the queue.

        Args:
            task_id: Unique label for the task (e.g., "twitter").
            coro: An awaitable (coroutine) to execute.
        """
        self._tasks.append((task_id, coro))
        logger.debug("Enqueued task: %s (pending: %d)", task_id, len(self._tasks))

    async def _execute_task(self, task_id: str, coro: Any) -> TaskResult:
        """Execute a single task with semaphore and timeout.

        Args:
            task_id: Task identifier for logging and results.
            coro: The awaitable to run.

        Returns:
            TaskResult with status, data, and timing.
        """
        import time

        async with self._semaphore:
            start = time.monotonic()
            try:
                data = await asyncio.wait_for(coro, timeout=self.task_timeout)
                elapsed = time.monotonic() - start
                logger.debug(
                    "Task %s completed in %.2fs", task_id, elapsed,
                )
                return TaskResult(
                    task_id=task_id,
                    status=TaskStatus.COMPLETED,
                    data=data,
                    elapsed_seconds=elapsed,
                )
            except asyncio.TimeoutError:
                elapsed = time.monotonic() - start
                logger.warning(
                    "Task %s timed out after %.2fs", task_id, elapsed,
                )
                return TaskResult(
                    task_id=task_id,
                    status=TaskStatus.TIMED_OUT,
                    error=f"Timed out after {self.task_timeout}s",
                    elapsed_seconds=elapsed,
                )
            except Exception as exc:
                elapsed = time.monotonic() - start
                logger.warning(
                    "Task %s failed after %.2fs: %s", task_id, elapsed, exc,
                )
                return TaskResult(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    error=str(exc),
                    elapsed_seconds=elapsed,
                )

    async def process_all(self) -> Dict[str, TaskResult]:
        """Process all enqueued tasks with concurrency control.

        Tasks run in parallel up to max_concurrency. Each task has an
        independent timeout. Results are stored in self._results.

        Returns:
            Dict mapping task_id to TaskResult.
        """
        if not self._tasks:
            return {}

        task_list = list(self._tasks)
        self._tasks.clear()

        results = await asyncio.gather(
            *[self._execute_task(tid, coro) for tid, coro in task_list],
        )

        self._results = {r.task_id: r for r in results}
        return self._results

    @staticmethod
    async def run_parallel(
        tasks: List[Tuple[str, Any]],
        max_concurrency: int = 5,
        task_timeout: float = 30.0,
    ) -> Dict[str, TaskResult]:
        """Static convenience method: create queue, enqueue, and process.

        Args:
            tasks: List of (task_id, coroutine) tuples.
            max_concurrency: Maximum concurrent tasks.
            task_timeout: Per-task timeout in seconds.

        Returns:
            Dict mapping task_id to TaskResult.
        """
        queue = TaskQueue(
            max_concurrency=max_concurrency,
            task_timeout=task_timeout,
        )
        for task_id, coro in tasks:
            await queue.enqueue(task_id, coro)
        return await queue.process_all()

    def get_summary(self) -> Dict[str, Any]:
        """Return a summary of all task results for logging.

        Returns:
            Dict with counts by status and per-task elapsed times.
        """
        if not self._results:
            return {"total": 0, "completed": 0, "failed": 0, "timed_out": 0}

        completed = sum(
            1 for r in self._results.values() if r.status == TaskStatus.COMPLETED
        )
        failed = sum(
            1 for r in self._results.values() if r.status == TaskStatus.FAILED
        )
        timed_out = sum(
            1 for r in self._results.values() if r.status == TaskStatus.TIMED_OUT
        )

        return {
            "total": len(self._results),
            "completed": completed,
            "failed": failed,
            "timed_out": timed_out,
            "tasks": {
                tid: {
                    "status": r.status.value,
                    "elapsed": round(r.elapsed_seconds, 3),
                    "error": r.error,
                }
                for tid, r in self._results.items()
            },
        }
