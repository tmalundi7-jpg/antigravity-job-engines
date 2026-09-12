"""
Global test fixtures for job_search_engine test suite.

Autouse broker_reset ensures each test starts with a clean LocalMessageBroker
singleton, preventing inter-test thread and queue interference.
"""
import pytest
from core.messaging import LocalMessageBroker


@pytest.fixture(autouse=True, scope="function")
def broker_reset():
    """Reset the LocalMessageBroker singleton before every test function."""
    LocalMessageBroker.reset()
    yield
    # Cleanup after each test as well
    LocalMessageBroker.reset()
