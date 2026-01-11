# Test Patterns

Examples and patterns for test-driven development.

## Unit Test Pattern

```python
import pytest
from solver_api.src.module import function_to_test

class TestFunctionName:
    """Tests for function_to_test."""

    def test_happy_path(self):
        """Test normal operation."""
        result = function_to_test(valid_input)
        assert result == expected_output

    def test_edge_case(self):
        """Test boundary conditions."""
        result = function_to_test(edge_input)
        assert result == edge_output

    def test_error_handling(self):
        """Test error conditions."""
        with pytest.raises(ExpectedException):
            function_to_test(invalid_input)
```

## Async Test Pattern

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test async operation."""
    result = await async_function(input)
    assert result == expected
```

## Fixture Pattern

```python
import pytest

@pytest.fixture
def sample_data():
    """Provide test data."""
    return {
        "field": "value",
        "nested": {"key": "value"}
    }

def test_with_fixture(sample_data):
    """Test using fixture data."""
    result = process(sample_data)
    assert result.field == "value"
```

## Mock Pattern

```python
from unittest.mock import Mock, patch

def test_with_mock():
    """Test with mocked dependency."""
    mock_service = Mock()
    mock_service.method.return_value = "mocked"

    result = function_under_test(mock_service)

    mock_service.method.assert_called_once()
    assert result == "expected"

@patch('module.external_service')
def test_with_patch(mock_service):
    """Test with patched module."""
    mock_service.return_value = "mocked"
    result = function_that_uses_service()
    assert result == "expected"
```

## Integration Test Pattern

```python
import pytest
from httpx import AsyncClient
from solver_api.main import app

@pytest.mark.asyncio
async def test_api_endpoint():
    """Test API endpoint integration."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/endpoint",
            json={"field": "value"}
        )

    assert response.status_code == 200
    assert response.json()["result"] == "expected"
```

## Database Test Pattern

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture
async def db_session():
    """Provide test database session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(test_engine) as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_database_operation(db_session):
    """Test database CRUD."""
    # Create
    entity = Entity(field="value")
    db_session.add(entity)
    await db_session.commit()

    # Read
    result = await db_session.get(Entity, entity.id)
    assert result.field == "value"
```

## Project-Specific Patterns

### Signal Extraction Test

```python
@pytest.mark.asyncio
async def test_signal_extraction():
    """Test signal extraction from user message."""
    extractor = SignalExtractor(client)
    signals = await extractor.extract(
        "The brand should feel premium and exclusive"
    )

    assert len(signals) > 0
    assert any(s.enum_id.startswith("E-") for s in signals)
```

### Solver Test

```python
def test_solver_v5():
    """Test H-PHASED solver."""
    solver = SolverV5(graph_cache)
    seeds = [SolverSeed(enum_id="E-M001-001", mu=0.85, sigma=0.10)]

    result = solver.solve(seeds)

    assert result.high_match >= 0.8
    assert result.low_match >= 0.7
```

## Coverage Goals

| Module | Target | Current |
|--------|--------|---------|
| solver_v5.py | 85% | Check with pytest --cov |
| extractor.py | 80% | Check with pytest --cov |
| orchestrator.py | 75% | Check with pytest --cov |
| API endpoints | 70% | Check with pytest --cov |
