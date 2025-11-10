"""
Authentication tests
"""
import pytest
from app.models import User
from app.utils.database import get_db


@pytest.fixture
def test_user_data():
    """Sample user data for testing"""
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


class TestRegistration:
    """Test user registration"""
    
    def test_register_new_user(self, client, test_user_data):
        """Test successful user registration"""
        response = client.post('/auth/register', json=test_user_data)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert 'user_id' in data
        assert data['username'] == test_user_data['username']
    
    def test_register_duplicate_username(self, client, test_user_data):
        """Test registration with existing username"""
        # Register first user
        client.post('/auth/register', json=test_user_data)
        
        # Try to register again with same username
        response = client.post('/auth/register', json=test_user_data)
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'already exists' in data['error'].lower()
    
    def test_register_invalid_username(self, client, test_user_data):
        """Test registration with invalid username"""
        test_user_data['username'] = 'ab'  # Too short
        
        response = client.post('/auth/register', json=test_user_data)
        assert response.status_code == 400
    
    def test_register_invalid_password(self, client, test_user_data):
        """Test registration with invalid password"""
        test_user_data['password'] = 'short'  # Too short
        
        response = client.post('/auth/register', json=test_user_data)
        assert response.status_code == 400
    
    def test_register_missing_keys(self, client, test_user_data):
        """Test registration without public keys"""
        del test_user_data['identity_pub']
        
        response = client.post('/auth/register', json=test_user_data)
        assert response.status_code == 400


class TestLogin:
    """Test user login"""
    
    def test_login_success(self, client, test_user_data):
        """Test successful login"""
        # Register user first
        client.post('/auth/register', json=test_user_data)
        
        # Login
        login_data = {
            'username': test_user_data['username'],
            'password': test_user_data['password']
        }
        response = client.post('/auth/login', json=login_data)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
    
    def test_login_wrong_password(self, client, test_user_data):
        """Test login with incorrect password"""
        # Register user first
        client.post('/auth/register', json=test_user_data)
        
        # Login with wrong password
        login_data = {
            'username': test_user_data['username'],
            'password': 'WrongPassword123'
        }
        response = client.post('/auth/login', json=login_data)
        
        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent username"""
        login_data = {
            'username': 'nonexistent',
            'password': 'Password123'
        }
        response = client.post('/auth/login', json=login_data)
        
        assert response.status_code == 401


class TestLogout:
    """Test user logout"""
    
    def test_logout(self, client, test_user_data):
        """Test logout functionality"""
        # Register and login
        client.post('/auth/register', json=test_user_data)
        client.post('/auth/login', json={
            'username': test_user_data['username'],
            'password': test_user_data['password']
        })
        
        # Logout
        response = client.post('/auth/logout')
        assert response.status_code == 200


class TestKeyManagement:
    """Test public key management"""
    
    def test_get_prekey_bundle(self, client, test_user_data):
        """Test retrieving user's prekey bundle"""
        # Register user
        client.post('/auth/register', json=test_user_data)
        
        # Login
        client.post('/auth/login', json={
            'username': test_user_data['username'],
            'password': test_user_data['password']
        })
        
        # Get prekey bundle
        response = client.get(f'/chat/prekey-bundle/{test_user_data["username"]}')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['username'] == test_user_data['username']
        assert 'identity_pub' in data
        assert 'signed_prekey_pub' in data
    
    def test_consume_one_time_prekey(self, client, test_user_data):
        """Test that one-time prekeys are consumed"""
        # Register user
        client.post('/auth/register', json=test_user_data)
        
        # Login
        client.post('/auth/login', json={
            'username': test_user_data['username'],
            'password': test_user_data['password']
        })
        
        # Get prekey bundle twice
        response1 = client.get(f'/chat/prekey-bundle/{test_user_data["username"]}')
        response2 = client.get(f'/chat/prekey-bundle/{test_user_data["username"]}')
        
        data1 = response1.get_json()
        data2 = response2.get_json()
        
        # One-time prekeys should be different or None
        if data1.get('one_time_prekey') and data2.get('one_time_prekey'):
            assert data1['one_time_prekey'] != data2['one_time_prekey']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
