#!/bin/bash

# AI Trading Platform V2.0 - Local Test Runner
# This script runs the same tests that GitHub Actions will run

set -e  # Exit on any error

echo "🚀 AI Trading Platform V2.0 - Local Test Suite"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_status "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
print_status "Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
pip install -q pytest pytest-cov requests

# Set environment variables
export FLASK_ENV=testing
export DATABASE_URL=sqlite:///test.db
export SECRET_KEY=test-secret-key-for-local-testing

print_status "Starting Flask backend server..."
cd src
python main.py &
BACKEND_PID=$!
cd ..

# Wait for server to start
print_status "Waiting for backend to start..."
sleep 10

# Check if backend is running
if curl -f http://localhost:5001/health > /dev/null 2>&1; then
    print_success "Backend server is running"
else
    print_error "Backend server failed to start"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

# Run tests
echo ""
echo "🧪 Running Test Suite"
echo "===================="

# Backend health check
print_status "Running backend health check..."
if curl -f http://localhost:5001/health > /dev/null 2>&1; then
    print_success "✅ Backend health check passed"
else
    print_error "❌ Backend health check failed"
fi

# Authentication tests
print_status "Running authentication tests..."
if pytest tests/test_auth.py -v --tb=short > test_auth_results.log 2>&1; then
    print_success "✅ Authentication tests passed"
else
    print_warning "⚠️  Authentication tests had issues (check test_auth_results.log)"
fi

# ChatBot tests
print_status "Running ChatBot tests..."
if pytest tests/test_chatbot.py -v --tb=short > test_chatbot_results.log 2>&1; then
    print_success "✅ ChatBot tests passed"
else
    print_error "❌ ChatBot tests failed (check test_chatbot_results.log)"
fi

# Portfolio and trading tests
print_status "Running portfolio and trading tests..."
if pytest tests/test_portfolio_trading.py -v --tb=short > test_portfolio_results.log 2>&1; then
    print_success "✅ Portfolio and trading tests passed"
else
    print_error "❌ Portfolio and trading tests failed (check test_portfolio_results.log)"
fi

# Integration tests
print_status "Running integration tests..."
if pytest tests/test_integration.py -v --tb=short > test_integration_results.log 2>&1; then
    print_success "✅ Integration tests passed"
else
    print_error "❌ Integration tests failed (check test_integration_results.log)"
fi

# Run all tests with coverage
print_status "Running comprehensive test suite with coverage..."
pytest tests/ -v --cov=src --cov-report=html --cov-report=term --tb=short > test_coverage_results.log 2>&1

# Generate test summary
echo ""
echo "📊 Test Summary Report"
echo "====================="

# Count test results
TOTAL_TESTS=$(grep -c "PASSED\|FAILED\|ERROR" test_*_results.log 2>/dev/null || echo "0")
PASSED_TESTS=$(grep -c "PASSED" test_*_results.log 2>/dev/null || echo "0")
FAILED_TESTS=$(grep -c "FAILED\|ERROR" test_*_results.log 2>/dev/null || echo "0")

echo "Total Tests: $TOTAL_TESTS"
echo "Passed: $PASSED_TESTS"
echo "Failed: $FAILED_TESTS"

if [ "$FAILED_TESTS" -eq 0 ]; then
    print_success "🎉 All tests passed!"
    TEST_STATUS="SUCCESS"
else
    print_warning "⚠️  Some tests failed. Check individual log files for details."
    TEST_STATUS="PARTIAL"
fi

# API endpoint validation
echo ""
echo "🔍 API Endpoint Validation"
echo "=========================="

endpoints=(
    "GET /health"
    "GET /api"
    "GET /api/portfolio/"
    "POST /api/chat/message"
)

for endpoint in "${endpoints[@]}"; do
    method=$(echo $endpoint | cut -d' ' -f1)
    path=$(echo $endpoint | cut -d' ' -f2)
    
    if [ "$method" = "GET" ]; then
        if curl -f "http://localhost:5001$path" > /dev/null 2>&1; then
            print_success "✅ $endpoint"
        else
            print_error "❌ $endpoint"
        fi
    elif [ "$method" = "POST" ] && [ "$path" = "/api/chat/message" ]; then
        if curl -f -X POST "http://localhost:5001$path" \
           -H "Content-Type: application/json" \
           -d '{"message": "test"}' > /dev/null 2>&1; then
            print_success "✅ $endpoint"
        else
            print_error "❌ $endpoint"
        fi
    fi
done

# Cleanup
print_status "Cleaning up..."
kill $BACKEND_PID 2>/dev/null || true

# Generate final report
cat > test_report.md << EOF
# AI Trading Platform V2.0 - Local Test Report

**Generated on:** $(date)
**Test Status:** $TEST_STATUS

## Test Results Summary

- **Total Tests:** $TOTAL_TESTS
- **Passed:** $PASSED_TESTS  
- **Failed:** $FAILED_TESTS

## Test Coverage

Coverage report generated in \`htmlcov/index.html\`

## Log Files Generated

- \`test_auth_results.log\` - Authentication test results
- \`test_chatbot_results.log\` - ChatBot test results  
- \`test_portfolio_results.log\` - Portfolio test results
- \`test_integration_results.log\` - Integration test results
- \`test_coverage_results.log\` - Coverage report

## Next Steps

1. Review any failed tests in the log files
2. Open \`htmlcov/index.html\` to view detailed coverage report
3. Compare results with GitHub Actions when you push to repository

EOF

print_success "Test report generated: test_report.md"
print_success "Coverage report available: htmlcov/index.html"

echo ""
echo "🎯 Local Testing Complete!"
echo "=========================="
echo "You can now push to GitHub and compare these results with GitHub Actions."
echo ""
echo "To view coverage report: open htmlcov/index.html in your browser"
echo "To view test logs: cat test_*_results.log"

