"""
Pytest configuration and fixtures
"""
import pytest
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture(scope='session')
def app():
    """Create application for testing"""
    from app import app as flask_app
    
    # Set testing configuration
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    
    return flask_app


@pytest.fixture(scope='function')
def client(app):
    """Create test client"""
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture(scope='function')
def clean_database():
    """Clean database before each test"""
    from app.utils.database import get_db
    
    db = get_db()
    
    # Drop test collections
    db.users.delete_many({})
    db.messages.delete_many({})
    db.groups.delete_many({})
    db.server_chat.delete_many({})
    
    yield db
    
    # Cleanup after test
    db.users.delete_many({})
    db.messages.delete_many({})
    db.groups.delete_many({})
    db.server_chat.delete_many({})


@pytest.fixture
def sample_user():
    """Sample user data"""
    return {
        'username': 'testuser',
        'password': 'Test1234',
        'identity_pub': 'mock_identity_pub_key',
        'signed_prekey_pub': 'mock_signed_prekey',
        'signed_prekey_sig': 'mock_signature',
        'one_time_prekeys': [
            {'id': 'opk1', 'publicKey': 'mock_opk_1'},
            {'id': 'opk2', 'publicKey': 'mock_opk_2'}
        ]
    }


@pytest.fixture
def authenticated_client(client, sample_user):
    """Client with authenticated session"""
    # Register user
    client.post('/auth/register', json=sample_user)
    
    # Login
    client.post('/auth/login', json={
        'username': sample_user['username'],
        'password': sample_user['password']
    })
    
    return client


# Hooks
def pytest_configure(config):
    """Configure pytest"""
    print("\n" + "="*70)
    print("Starting Chatify Test Suite")
    print("="*70)


def pytest_unconfigure(config):
    """Cleanup after all tests"""
    print("\n" + "="*70)
    print("Test Suite Completed")
    print("="*70)


def pytest_collection_finish(session):
    """Print test collection summary"""
    print(f"\nCollected {len(session.items)} test(s)")
