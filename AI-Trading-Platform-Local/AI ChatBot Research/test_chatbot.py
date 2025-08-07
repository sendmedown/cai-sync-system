import pytest
import requests
import json
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:5001"
API_BASE = f"{BASE_URL}/api"

class TestChatbot:
    """Test suite for AI chatbot functionality"""
    
    def test_chatbot_basic_response(self):
        """Test that chatbot returns a valid response to a basic message"""
        message_data = {
            "message": "Hello, how are you?"
        }
        
        response = requests.post(f"{API_BASE}/chat/message", json=message_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "ai_response" in data
        assert "intent" in data
        assert "confidence" in data
        assert "suggestions" in data
        assert "timestamp" in data
        
        # Verify response is not empty
        assert len(data["ai_response"]) > 0
        assert isinstance(data["confidence"], float)
        assert 0 <= data["confidence"] <= 1
        assert isinstance(data["suggestions"], list)
    
    def test_chatbot_portfolio_analysis(self):
        """Test chatbot portfolio analysis intent"""
        message_data = {
            "message": "What's my portfolio performance?"
        }
        
        response = requests.post(f"{API_BASE}/chat/message", json=message_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["intent"] == "portfolio_analysis"
        assert "portfolio" in data["ai_response"].lower() or "performance" in data["ai_response"].lower()
        assert data["confidence"] > 0.7  # High confidence for clear intent
        
        # Check suggestions are relevant
        suggestions = data["suggestions"]
        assert len(suggestions) > 0
        portfolio_keywords = ["portfolio", "allocation", "risk", "optimize"]
        assert any(keyword in " ".join(suggestions).lower() for keyword in portfolio_keywords)
    
    def test_chatbot_market_analysis(self):
        """Test chatbot market analysis intent"""
        message_data = {
            "message": "How is the market performing today?"
        }
        
        response = requests.post(f"{API_BASE}/chat/message", json=message_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["intent"] == "market_analysis"
        assert "market" in data["ai_response"].lower()
        assert data["confidence"] > 0.7
    
    def test_chatbot_strategy_advice(self):
        """Test chatbot strategy advice intent"""
        message_data = {
            "message": "Should I buy AAPL stock?"
        }
        
        response = requests.post(f"{API_BASE}/chat/message", json=message_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["intent"] == "strategy_advice"
        assert data["confidence"] > 0.6
    
    def test_chatbot_risk_management(self):
        """Test chatbot risk management intent"""
        message_data = {
            "message": "What's my portfolio risk exposure?"
        }
        
        response = requests.post(f"{API_BASE}/chat/message", json=message_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["intent"] == "risk_management"
        assert "risk" in data["ai_response"].lower()
        assert data["confidence"] > 0.7
    
    def test_chatbot_technical_analysis(self):
        """Test chatbot technical analysis intent"""
        message_data = {
            "message": "What do the RSI indicators show?"
        }
        
        response = requests.post(f"{API_BASE}/chat/message", json=message_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["intent"] == "technical_analysis"
        assert "rsi" in data["ai_response"].lower() or "technical" in data["ai_response"].lower()
    
    def test_chatbot_empty_message_failure(self):
        """Test chatbot failure with empty message"""
        message_data = {
            "message": ""
        }
        
        response = requests.post(f"{API_BASE}/chat/message", json=message_data)
        assert response.status_code == 400
        
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "empty" in data["error"].lower()
    
    def test_chatbot_missing_message_failure(self):
        """Test chatbot failure with missing message field"""
        message_data = {}
        
        response = requests.post(f"{API_BASE}/chat/message", json=message_data)
        assert response.status_code == 400
        
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "required" in data["error"].lower()
    
    def test_chatbot_with_user_id(self):
        """Test chatbot with user ID for personalization"""
        message_data = {
            "message": "What's my portfolio performance?",
            "user_id": "test_user_123"
        }
        
        response = requests.post(f"{API_BASE}/chat/message", json=message_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "ai_response" in data
        assert len(data["ai_response"]) > 0
    
    def test_chatbot_conversation_context(self):
        """Test that chatbot maintains conversation context"""
        # First message
        message1 = {
            "message": "Tell me about my AAPL position",
            "user_id": "context_test_user"
        }
        
        response1 = requests.post(f"{API_BASE}/chat/message", json=message1)
        assert response1.status_code == 200
        
        # Follow-up message
        message2 = {
            "message": "Should I sell it?",
            "user_id": "context_test_user"
        }
        
        response2 = requests.post(f"{API_BASE}/chat/message", json=message2)
        assert response2.status_code == 200
        
        data2 = response2.json()
        assert data2["success"] is True
        assert len(data2["ai_response"]) > 0
    
    def test_chatbot_suggestions_endpoint(self):
        """Test chatbot suggestions endpoint"""
        response = requests.get(f"{API_BASE}/chat/suggestions")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
        assert len(data["suggestions"]) > 0
        
        # Verify suggestions are meaningful
        for suggestion in data["suggestions"]:
            assert isinstance(suggestion, str)
            assert len(suggestion) > 0
    
    def test_chatbot_history_endpoint(self):
        """Test chatbot conversation history endpoint"""
        # Send a message first to create history
        message_data = {
            "message": "Test message for history",
            "user_id": "history_test_user"
        }
        requests.post(f"{API_BASE}/chat/message", json=message_data)
        
        # Get history
        response = requests.get(f"{API_BASE}/chat/history")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "history" in data
        assert "total_conversations" in data
        assert isinstance(data["history"], list)
    
    def test_chatbot_clear_history(self):
        """Test clearing chatbot conversation history"""
        response = requests.post(f"{API_BASE}/chat/clear")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "message" in data
        assert "cleared" in data["message"].lower()
    
    def test_chatbot_response_time(self):
        """Test that chatbot responds within reasonable time"""
        import time
        
        message_data = {
            "message": "What's my portfolio performance?"
        }
        
        start_time = time.time()
        response = requests.post(f"{API_BASE}/chat/message", json=message_data)
        end_time = time.time()
        
        response_time = end_time - start_time
        assert response_time < 2.0  # Should respond within 2 seconds
        assert response.status_code == 200
    
    def test_chatbot_no_errors_in_response(self):
        """Test that chatbot never returns error messages in AI responses"""
        test_messages = [
            "What's my portfolio?",
            "How is the market?",
            "Should I buy stocks?",
            "What's my risk?",
            "Show me technical analysis",
            "Random question about trading"
        ]
        
        for message in test_messages:
            message_data = {"message": message}
            response = requests.post(f"{API_BASE}/chat/message", json=message_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            
            # Ensure no error keywords in AI response
            ai_response = data["ai_response"].lower()
            error_keywords = ["error", "failed", "exception", "traceback", "none", "null"]
            for keyword in error_keywords:
                assert keyword not in ai_response, f"Error keyword '{keyword}' found in response: {data['ai_response']}"

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])

