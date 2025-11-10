"""
Basic tests for Chatify application
"""
import pytest
from app import create_app
from app.utils.security import hash_password, verify_password, validate_username, validate_password


@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app('testing')
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


class TestSecurity:
    """Test security utilities"""
    
    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "testpassword123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert verify_password(password, hashed)
        assert not verify_password("wrongpassword", hashed)
    
    def test_username_validation(self):
        """Test username validation"""
        # Valid usernames
        assert validate_username("alice")[0] is True
        assert validate_username("bob_123")[0] is True
        assert validate_username("user-name")[0] is True
        
        # Invalid usernames
        assert validate_username("ab")[0] is False  # Too short
        assert validate_username("")[0] is False  # Empty
        assert validate_username("a" * 31)[0] is False  # Too long
        assert validate_username("user@name")[0] is False  # Invalid char
    
    def test_password_validation(self):
        """Test password validation"""
        # Valid passwords
        assert validate_password("password123")[0] is True
        assert validate_password("Test1234")[0] is True
        
        # Invalid passwords
        assert validate_password("short")[0] is False  # Too short
        assert validate_password("nodigits")[0] is False  # No numbers
        assert validate_password("12345678")[0] is False  # No letters
        assert validate_password("")[0] is False  # Empty


class TestRoutes:
    """Test application routes"""
    
    def test_home_page(self, client):
        """Test home page loads"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Chatify' in response.data
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
    
    def test_register_page(self, client):
        """Test registration page loads"""
        response = client.get('/auth/register')
        assert response.status_code == 200
        assert b'Create Account' in response.data
    
    def test_login_page(self, client):
        """Test login page loads"""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b'Welcome Back' in response.data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
