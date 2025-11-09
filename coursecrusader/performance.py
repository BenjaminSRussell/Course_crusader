"""
Performance monitoring and benchmarking for Course Crusader.

Provides tools for profiling scraper performance and resource usage.
"""

import time
import psutil
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager


@dataclass
class PerformanceMetrics:
    """
    Performance metrics for a scraping run.
    """
    university: str
    start_time: float
    end_time: Optional[float] = None
    courses_scraped: int = 0
    pages_fetched: int = 0
    errors: int = 0
    memory_peak_mb: float = 0.0

    @property
    def duration_seconds(self) -> float:
        """Calculate duration in seconds."""
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    @property
    def courses_per_second(self) -> float:
        """Calculate scraping rate."""
        duration = self.duration_seconds
        if duration == 0:
            return 0.0
        return self.courses_scraped / duration

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'university': self.university,
            'duration_seconds': round(self.duration_seconds, 2),
            'courses_scraped': self.courses_scraped,
            'pages_fetched': self.pages_fetched,
            'errors': self.errors,
            'memory_peak_mb': round(self.memory_peak_mb, 2),
            'courses_per_second': round(self.courses_per_second, 2)
        }


class PerformanceMonitor:
    """
    Monitor performance metrics during scraping.
    """

    def __init__(self):
        """Initialize performance monitor."""
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.process = psutil.Process(os.getpid())

    def start_monitoring(self, university: str) -> PerformanceMetrics:
        """
        Start monitoring a scraping run.

        Args:
            university: University being scraped

        Returns:
            PerformanceMetrics object
        """
        metrics = PerformanceMetrics(
            university=university,
            start_time=time.time()
        )
        self.metrics[university] = metrics
        return metrics

    def update_metrics(
        self,
        university: str,
        courses: int = 0,
        pages: int = 0,
        errors: int = 0
    ):
        """
        Update metrics during scraping.

        Args:
            university: University name
            courses: Number of courses to add
            pages: Number of pages to add
            errors: Number of errors to add
        """
        if university not in self.metrics:
            return

        metrics = self.metrics[university]
        metrics.courses_scraped += courses
        metrics.pages_fetched += pages
        metrics.errors += errors

        # Update memory peak
        memory_mb = self.process.memory_info().rss / 1024 / 1024
        if memory_mb > metrics.memory_peak_mb:
            metrics.memory_peak_mb = memory_mb

    def end_monitoring(self, university: str):
        """
        End monitoring for a university.

        Args:
            university: University name
        """
        if university in self.metrics:
            self.metrics[university].end_time = time.time()

    def get_metrics(self, university: str) -> Optional[PerformanceMetrics]:
        """Get metrics for a university."""
        return self.metrics.get(university)

    def get_all_metrics(self) -> Dict[str, PerformanceMetrics]:
        """Get all metrics."""
        return self.metrics

    def print_summary(self, university: Optional[str] = None):
        """
        Print performance summary.

        Args:
            university: Optional university filter
        """
        if university and university in self.metrics:
            metrics = [self.metrics[university]]
        else:
            metrics = list(self.metrics.values())

        print("\n" + "="*70)
        print("Performance Summary")
        print("="*70)

        for m in metrics:
            print(f"\n{m.university}:")
            print(f"  Duration: {m.duration_seconds:.2f}s")
            print(f"  Courses: {m.courses_scraped}")
            print(f"  Pages: {m.pages_fetched}")
            print(f"  Rate: {m.courses_per_second:.2f} courses/sec")
            print(f"  Memory Peak: {m.memory_peak_mb:.2f} MB")
            if m.errors > 0:
                print(f"  Errors: {m.errors}")

        print("="*70 + "\n")


@contextmanager
def profile_scraper(university: str, monitor: Optional[PerformanceMonitor] = None):
    """
    Context manager for profiling a scraper run.

    Usage:
        with profile_scraper("UConn") as metrics:
            # Run scraper
            metrics.update(courses=100, pages=10)

    Args:
        university: University being scraped
        monitor: Optional PerformanceMonitor instance

    Yields:
        PerformanceMetrics object
    """
    if monitor is None:
        monitor = PerformanceMonitor()

    metrics = monitor.start_monitoring(university)

    try:
        yield metrics
    finally:
        monitor.end_monitoring(university)
        monitor.print_summary(university)


class Benchmark:
    """
    Benchmarking utilities for testing scraper performance.
    """

    @staticmethod
    def time_function(func, *args, **kwargs) -> tuple[Any, float]:
        """
        Time execution of a function.

        Args:
            func: Function to time
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            (result, duration_seconds) tuple
        """
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()

        return result, end - start

    @staticmethod
    def memory_usage() -> float:
        """
        Get current memory usage in MB.

        Returns:
            Memory usage in megabytes
        """
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024

    @staticmethod
    def benchmark_parser(parser_func, test_data, iterations: int = 10):
        """
        Benchmark a parser function.

        Args:
            parser_func: Parser function to test
            test_data: Data to parse
            iterations: Number of iterations

        Returns:
            Dict with benchmark results
        """
        durations = []

        for _ in range(iterations):
            start = time.time()
            parser_func(test_data)
            end = time.time()
            durations.append(end - start)

        avg_duration = sum(durations) / len(durations)
        min_duration = min(durations)
        max_duration = max(durations)

        return {
            'iterations': iterations,
            'avg_duration_ms': round(avg_duration * 1000, 3),
            'min_duration_ms': round(min_duration * 1000, 3),
            'max_duration_ms': round(max_duration * 1000, 3)
        }
