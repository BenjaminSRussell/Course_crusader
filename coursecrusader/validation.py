"""
Golden dataset validation framework for Course Crusader.

Provides tools for measuring and improving scraper accuracy against
manually verified course data.
"""

import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class ValidationMetrics:
    """
    Accuracy metrics for a field or entire dataset.
    """
    total: int = 0
    correct: int = 0
    incorrect: int = 0
    missing: int = 0

    @property
    def accuracy(self) -> float:
        """Calculate accuracy percentage."""
        if self.total == 0:
            return 0.0
        return (self.correct / self.total) * 100

    @property
    def completeness(self) -> float:
        """Calculate completeness percentage."""
        if self.total == 0:
            return 0.0
        return ((self.total - self.missing) / self.total) * 100

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'total': self.total,
            'correct': self.correct,
            'incorrect': self.incorrect,
            'missing': self.missing,
            'accuracy': round(self.accuracy, 2),
            'completeness': round(self.completeness, 2)
        }


@dataclass
class ValidationReport:
    """
    Complete validation report for scraped data vs golden dataset.
    """
    university: str
    total_courses: int
    field_metrics: Dict[str, ValidationMetrics] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)

    def add_field_metric(self, field_name: str, metrics: ValidationMetrics):
        """Add metrics for a specific field."""
        self.field_metrics[field_name] = metrics

    def add_error(
        self,
        course_id: str,
        field: str,
        expected: Any,
        actual: Any,
        error_type: str = "mismatch"
    ):
        """Record a validation error."""
        self.errors.append({
            'course_id': course_id,
            'field': field,
            'expected': expected,
            'actual': actual,
            'error_type': error_type
        })

    def overall_accuracy(self) -> float:
        """Calculate overall accuracy across all fields."""
        if not self.field_metrics:
            return 0.0

        total_correct = sum(m.correct for m in self.field_metrics.values())
        total_checks = sum(m.total for m in self.field_metrics.values())

        if total_checks == 0:
            return 0.0

        return (total_correct / total_checks) * 100

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'university': self.university,
            'total_courses': self.total_courses,
            'overall_accuracy': round(self.overall_accuracy(), 2),
            'field_metrics': {
                k: v.to_dict() for k, v in self.field_metrics.items()
            },
            'error_count': len(self.errors),
            'errors': self.errors[:10]  # Include first 10 errors
        }


class GoldenDatasetValidator:
    """
    Validator for comparing scraped data against manually verified golden dataset.
    """

    # Fields to validate (in priority order)
    VALIDATED_FIELDS = [
        'course_id',
        'title',
        'credits',
        'department',
        'level',
        'description',
        'prerequisites_text'
    ]

    def __init__(self, golden_dataset_path: str):
        """
        Initialize validator with golden dataset.

        Args:
            golden_dataset_path: Path to JSON/JSONL file with verified data
        """
        self.golden_dataset_path = Path(golden_dataset_path)
        self.golden_data: Dict[str, Dict] = {}
        self._load_golden_dataset()

    def _load_golden_dataset(self):
        """Load golden dataset from file."""
        if not self.golden_dataset_path.exists():
            raise FileNotFoundError(f"Golden dataset not found: {self.golden_dataset_path}")

        with open(self.golden_dataset_path, 'r', encoding='utf-8') as f:
            if self.golden_dataset_path.suffix == '.jsonl':
                for line in f:
                    if line.strip():
                        course = json.loads(line)
                        key = f"{course['university']}:{course['course_id']}"
                        self.golden_data[key] = course
            else:
                data = json.load(f)
                courses = data if isinstance(data, list) else [data]
                for course in courses:
                    key = f"{course['university']}:{course['course_id']}"
                    self.golden_data[key] = course

    def validate_course(
        self,
        course: Dict,
        golden: Dict
    ) -> Dict[str, bool]:
        """
        Validate a single course against golden data.

        Args:
            course: Scraped course data
            golden: Golden (verified) course data

        Returns:
            Dict mapping field names to validation results (True = correct)
        """
        results = {}

        for field in self.VALIDATED_FIELDS:
            expected = golden.get(field)
            actual = course.get(field)

            if expected is None:
                # Field not in golden data, skip
                continue

            if actual is None:

                results[field] = False
            elif isinstance(expected, str) and isinstance(actual, str):
                # String comparison (case-insensitive, normalized)
                expected_norm = expected.strip().lower()
                actual_norm = actual.strip().lower()
                results[field] = expected_norm == actual_norm
            else:
                results[field] = expected == actual

        return results

    def validate_dataset(
        self,
        scraped_data_path: str,
        university: Optional[str] = None
    ) -> ValidationReport:
        """
        Validate entire scraped dataset against golden data.

        Args:
            scraped_data_path: Path to scraped data file
            university: Optional university filter

        Returns:
            ValidationReport with accuracy metrics
        """
        scraped_courses = []
        with open(scraped_data_path, 'r', encoding='utf-8') as f:
            if Path(scraped_data_path).suffix == '.jsonl':
                for line in f:
                    if line.strip():
                        scraped_courses.append(json.loads(line))
            else:
                data = json.load(f)
                scraped_courses = data if isinstance(data, list) else [data]


        if university:
            scraped_courses = [c for c in scraped_courses if c['university'] == university]

        report = ValidationReport(
            university=university or "All",
            total_courses=len(scraped_courses)
        )

        field_metrics = {field: ValidationMetrics() for field in self.VALIDATED_FIELDS}

        for course in scraped_courses:
            key = f"{course['university']}:{course['course_id']}"

            if key not in self.golden_data:
                # Course not in golden dataset, skip
                continue

            golden = self.golden_data[key]
            validation_results = self.validate_course(course, golden)

            for field, is_correct in validation_results.items():
                metrics = field_metrics[field]
                metrics.total += 1

                if course.get(field) is None:
                    metrics.missing += 1
                elif is_correct:
                    metrics.correct += 1
                else:
                    metrics.incorrect += 1
                    report.add_error(
                        course_id=course['course_id'],
                        field=field,
                        expected=golden.get(field),
                        actual=course.get(field)
                    )


        for field, metrics in field_metrics.items():
            if metrics.total > 0:  # Only include fields that were validated
                report.add_field_metric(field, metrics)

        return report

    def generate_report(
        self,
        scraped_data_path: str,
        output_path: Optional[str] = None
    ) -> ValidationReport:
        """
        Generate validation report and optionally save to file.

        Args:
            scraped_data_path: Path to scraped data
            output_path: Optional path to save report JSON

        Returns:
            ValidationReport
        """
        report = self.validate_dataset(scraped_data_path)

        if output_path:
            with open(output_path, 'w') as f:
                json.dump(report.to_dict(), f, indent=2)

        return report

    def print_report(self, report: ValidationReport):
        """
        Print validation report to console.

        Args:
            report: ValidationReport to print
        """
        print(f"\n{'='*60}")
        print(f"Validation Report: {report.university}")
        print(f"{'='*60}\n")
        print(f"Total Courses: {report.total_courses}")
        print(f"Overall Accuracy: {report.overall_accuracy():.2f}%\n")

        print("Field-by-Field Accuracy:")
        print(f"{'Field':<20} {'Accuracy':<12} {'Completeness':<15} {'Errors'}")
        print("-" * 60)

        for field, metrics in report.field_metrics.items():
            print(f"{field:<20} {metrics.accuracy:>6.2f}%     {metrics.completeness:>6.2f}%        {metrics.incorrect}")

        if report.errors:
            print(f"\n\nTop Errors (showing {min(10, len(report.errors))}):")
            for i, error in enumerate(report.errors[:10], 1):
                print(f"\n{i}. {error['course_id']} - {error['field']}")
                print(f"   Expected: {error['expected']}")
                print(f"   Actual:   {error['actual']}")

        print(f"\n{'='*60}\n")


def create_golden_sample(
    input_path: str,
    output_path: str,
    sample_size: int = 50,
    university: Optional[str] = None
):
    """
    Create a golden dataset sample from scraped data for manual verification.

    Args:
        input_path: Path to scraped data
        output_path: Path to save golden sample
        sample_size: Number of courses to sample
        university: Optional university filter
    """
    import random

    courses = []
    with open(input_path, 'r', encoding='utf-8') as f:
        if Path(input_path).suffix == '.jsonl':
            for line in f:
                if line.strip():
                    courses.append(json.loads(line))
        else:
            data = json.load(f)
            courses = data if isinstance(data, list) else [data]

    if university:
        courses = [c for c in courses if c['university'] == university]

    if len(courses) > sample_size:
        courses = random.sample(courses, sample_size)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(courses, f, indent=2, ensure_ascii=False)

    print(f"Created golden dataset sample: {len(courses)} courses")
    print(f"Saved to: {output_path}")
    print("\nManually verify and correct each course, then use this as golden dataset.")
