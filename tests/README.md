# Research Agent Tests

This directory contains the test suite for the Research Agent module, including both unit tests and property-based tests.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                     # Shared pytest fixtures
├── README.md                       # This file
├── property/                       # Property-based tests
│   ├── __init__.py
│   └── test_properties_api.py     # API and quota tracking properties
└── unit/                          # Unit tests (to be added)
```

## Running Tests

### Prerequisites

Ensure all dependencies are installed:

```bash
pip install -r requirements.txt
```

Required packages:
- `hypothesis==6.92.0` - Property-based testing framework
- `pytest==7.4.3` - Test runner
- `pytest-cov==4.1.0` - Coverage reporting

### Run All Tests

```bash
pytest tests/
```

### Run Property Tests Only

```bash
pytest tests/property/
```

### Run Specific Property Test

```bash
pytest tests/property/test_properties_api.py::test_quota_consumption_tracking_accuracy -v
```

### Run with Coverage

```bash
pytest tests/ --cov=research_agent --cov-report=html
```

## Property-Based Tests

Property-based tests use Hypothesis to verify correctness properties across many randomly generated inputs. Each test runs 100 iterations by default.

### Property 12: Quota Consumption Tracking Accuracy

**Location**: `tests/property/test_properties_api.py`

**Validates**: Requirements 4.1

**Description**: For any sequence of API operations, the total quota consumed (as tracked by the rate limiter) should equal the sum of individual operation costs:
- Search operations: 100 units
- Video details: 1 unit per video

**Test Variants**:
1. `test_quota_consumption_tracking_accuracy` - Basic quota tracking with random operation sequences
2. `test_quota_tracking_persists_across_instances` - Verifies quota state persists to disk
3. `test_quota_tracking_mixed_operations` - Tests realistic mixed operation patterns

## Test Configuration

Tests use temporary directories for state files to avoid interfering with production data. The `conftest.py` provides fixtures for:
- `temp_cache_dir` - Temporary directory for cache files
- `quota_state_file` - Temporary quota state file path

## Troubleshooting

### ModuleNotFoundError: No module named 'hypothesis'

Install the required dependencies:
```bash
pip install hypothesis pytest pytest-cov
```

### Network/Proxy Issues

If you encounter proxy errors during installation, try:
```bash
pip install --proxy="" hypothesis pytest pytest-cov
```

Or set the `NO_PROXY` environment variable:
```bash
export NO_PROXY="*"
pip install hypothesis pytest pytest-cov
```
