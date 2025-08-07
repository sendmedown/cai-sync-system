import pytest
import requests
import json
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:5001"
API_BASE = f"{BASE_URL}/api"

class TestAuthentication:
    """Test suite for authentication endpoints"""
    
    def test_health_endpoint(self):
        """Test that the health endpoint is accessible"""
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "AI Trading Platform V2.0"
        assert data["version"] == "2.0.0"
        assert "components" in data
        
        # Verify all components are operational
        components = data["components"]
        expected_components = ["authentication", "portfolio", "trading", "chatbot", "strategies", "market_data"]
        for component in expected_components:
            assert component in components
            assert components[component] == "operational"
    
    def test_api_info_endpoint(self):
        """Test API information endpoint"""
        response = requests.get(f"{BASE_URL}/api")
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "AI Trading Platform API"
        assert data["version"] == "2.0.0"
        assert "endpoints" in data
        assert "features" in data
    
    def test_login_success_demo_user(self):
        """Test successful login with demo credentials"""
        login_data = {
            "email": "demo@example.com",
            "password": "demo123"
        }
        
        response = requests.post(f"{API_BASE}/auth/login", json=login_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == "demo@example.com"
        assert data["user"]["role"] == "demo"
    
    def test_login_failure_invalid_credentials(self):
        """Test login failure with invalid credentials"""
        login_data = {
            "email": "invalid@example.com",
            "password": "wrongpassword"
        }
        
        response = requests.post(f"{API_BASE}/auth/login", json=login_data)
        assert response.status_code == 401
        
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "Invalid credentials" in data["error"]
    
    def test_login_failure_missing_email(self):
        """Test login failure with missing email"""
        login_data = {
            "password": "demo123"
        }
        
        response = requests.post(f"{API_BASE}/auth/login", json=login_data)
        assert response.status_code == 400
        
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "Email and password are required" in data["error"]
    
    def test_login_failure_missing_password(self):
        """Test login failure with missing password"""
        login_data = {
            "email": "demo@example.com"
        }
        
        response = requests.post(f"{API_BASE}/auth/login", json=login_data)
        assert response.status_code == 400
        
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "Email and password are required" in data["error"]
    
    def test_login_failure_empty_request(self):
        """Test login failure with empty request body"""
        response = requests.post(f"{API_BASE}/auth/login", json={})
        assert response.status_code == 400
        
        data = response.json()
        assert data["success"] is False
        assert "error" in data
    
    def test_register_success(self):
        """Test successful user registration"""
        register_data = {
            "email": f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com",
            "password": "testpassword123",
            "name": "Test User"
        }
        
        response = requests.post(f"{API_BASE}/auth/register", json=register_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["success"] is True
        assert "user" in data
        assert data["user"]["email"] == register_data["email"]
        assert data["user"]["name"] == register_data["name"]
    
    def test_register_failure_duplicate_email(self):
        """Test registration failure with duplicate email"""
        register_data = {
            "email": "demo@example.com",  # Already exists
            "password": "testpassword123",
            "name": "Test User"
        }
        
        response = requests.post(f"{API_BASE}/auth/register", json=register_data)
        assert response.status_code == 400
        
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "already exists" in data["error"].lower()
    
    def test_register_failure_invalid_email(self):
        """Test registration failure with invalid email format"""
        register_data = {
            "email": "invalid-email-format",
            "password": "testpassword123",
            "name": "Test User"
        }
        
        response = requests.post(f"{API_BASE}/auth/register", json=register_data)
        assert response.status_code == 400
        
        data = response.json()
        assert data["success"] is False
        assert "error" in data
    
    def test_register_failure_weak_password(self):
        """Test registration failure with weak password"""
        register_data = {
            "email": "test@example.com",
            "password": "123",  # Too weak
            "name": "Test User"
        }
        
        response = requests.post(f"{API_BASE}/auth/register", json=register_data)
        assert response.status_code == 400
        
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "password" in data["error"].lower()

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])

