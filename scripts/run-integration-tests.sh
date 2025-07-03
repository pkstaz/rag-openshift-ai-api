#!/bin/bash

# Integration Tests Runner
# 
# This script runs comprehensive integration tests for the RAG API
# with different configurations and service availability checks.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TESTS_DIR="$PROJECT_ROOT/tests"
INTEGRATION_TESTS_DIR="$TESTS_DIR/integration"
REPORTS_DIR="$PROJECT_ROOT/test-reports"
PYTEST_CONFIG="$PROJECT_ROOT/pytest.ini"

# Default values
TEST_TYPE="all"
VERBOSE=false
PARALLEL=false
COVERAGE=false
REPORT_FORMAT="html"
SKIP_SERVICES=false
TIMEOUT=300

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

# Function to show usage
show_usage() {
    cat << EOF
Integration Tests Runner

Usage: $0 [OPTIONS]

Options:
    -t, --test-type TYPE     Test type to run (default: all)
                            Types: all, unit, integration, performance, api, elasticsearch, vllm
    -v, --verbose           Enable verbose output
    -p, --parallel          Run tests in parallel
    -c, --coverage          Generate coverage report
    -r, --report FORMAT     Report format (html, xml, json) (default: html)
    -s, --skip-services     Skip service availability checks
    --timeout SECONDS       Test timeout in seconds (default: 300)
    -h, --help             Show this help message

Examples:
    $0                                    # Run all tests
    $0 -t integration -v                  # Run integration tests with verbose output
    $0 -t performance -c -r html          # Run performance tests with coverage
    $0 -t elasticsearch --skip-services   # Run ElasticSearch tests without service checks
    $0 -t api -p                          # Run API tests in parallel

EOF
}

# Function to check dependencies
check_dependencies() {
    print_status "Checking dependencies..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed"
        exit 1
    fi
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 is required but not installed"
        exit 1
    fi
    
    # Check pytest
    if ! python3 -c "import pytest" &> /dev/null; then
        print_warning "pytest not found, installing..."
        pip3 install pytest pytest-cov pytest-xdist pytest-html
    fi
    
    # Check test dependencies
    local missing_deps=()
    for dep in "elasticsearch" "requests" "numpy" "fastapi"; do
        if ! python3 -c "import $dep" &> /dev/null; then
            missing_deps+=("$dep")
        fi
    done
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        print_warning "Missing dependencies: ${missing_deps[*]}"
        print_status "Installing test dependencies..."
        pip3 install "${missing_deps[@]}"
    fi
    
    print_success "Dependencies check completed"
}

# Function to check service availability
check_services() {
    if [ "$SKIP_SERVICES" = true ]; then
        print_warning "Skipping service availability checks"
        return 0
    fi
    
    print_status "Checking service availability..."
    
    # Check ElasticSearch
    if python3 -c "
import requests
try:
    response = requests.get('${ES_URL:-http://localhost:9200}', timeout=5)
    print('ElasticSearch: OK' if response.status_code == 200 else 'ElasticSearch: Not available')
except:
    print('ElasticSearch: Not available')
" 2>/dev/null | grep -q "OK"; then
        print_success "ElasticSearch is available"
        ES_AVAILABLE=true
    else
        print_warning "ElasticSearch is not available"
        ES_AVAILABLE=false
    fi
    
    # Check vLLM
    if python3 -c "
import requests
try:
    response = requests.get('${VLLM_URL:-http://localhost:8001}/v1/models', timeout=5)
    print('vLLM: OK' if response.status_code == 200 else 'vLLM: Not available')
except:
    print('vLLM: Not available')
" 2>/dev/null | grep -q "OK"; then
        print_success "vLLM is available"
        VLLM_AVAILABLE=true
    else
        print_warning "vLLM is not available"
        VLLM_AVAILABLE=false
    fi
}

# Function to setup test environment
setup_test_environment() {
    print_status "Setting up test environment..."
    
    # Create reports directory
    mkdir -p "$REPORTS_DIR"
    
    # Create pytest configuration if it doesn't exist
    if [ ! -f "$PYTEST_CONFIG" ]; then
        cat > "$PYTEST_CONFIG" << EOF
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --verbose
    --tb=short
    --maxfail=10
markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
    api: API tests
    elasticsearch: Tests requiring ElasticSearch
    vllm: Tests requiring vLLM
    slow: Slow running tests
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
EOF
        print_success "Created pytest configuration"
    fi
    
    # Set environment variables
    export ENV_ENVIRONMENT="test"
    export API_DEBUG="true"
    export ES_INDEX_NAME="rag_documents_test"
    export VLLM_TIMEOUT="30"
    export RAG_TOP_K="3"
    
    print_success "Test environment setup completed"
}

# Function to run tests
run_tests() {
    local test_args=()
    local pytest_args=()
    
    # Build pytest arguments
    pytest_args+=("--tb=short")
    pytest_args+=("--maxfail=10")
    
    if [ "$VERBOSE" = true ]; then
        pytest_args+=("-v")
    fi
    
    if [ "$PARALLEL" = true ]; then
        pytest_args+=("-n" "auto")
    fi
    
    if [ "$COVERAGE" = true ]; then
        pytest_args+=("--cov=src")
        pytest_args+=("--cov-report=$REPORT_FORMAT:$REPORTS_DIR/coverage")
        pytest_args+=("--cov-report=term-missing")
    fi
    
    # Add report generation
    pytest_args+=("--html=$REPORTS_DIR/report.html")
    pytest_args+=("--self-contained-html")
    pytest_args+=("--junitxml=$REPORTS_DIR/junit.xml")
    
    # Set timeout
    pytest_args+=("--timeout=$TIMEOUT")
    
    # Determine test path based on type
    case "$TEST_TYPE" in
        "all")
            test_args+=("$TESTS_DIR")
            ;;
        "unit")
            test_args+=("$TESTS_DIR/test_api.py")
            pytest_args+=("-m" "not integration")
            ;;
        "integration")
            test_args+=("$INTEGRATION_TESTS_DIR")
            pytest_args+=("-m" "integration")
            ;;
        "performance")
            test_args+=("$INTEGRATION_TESTS_DIR")
            pytest_args+=("-m" "performance")
            ;;
        "api")
            test_args+=("$INTEGRATION_TESTS_DIR")
            pytest_args+=("-m" "api")
            ;;
        "elasticsearch")
            test_args+=("$INTEGRATION_TESTS_DIR")
            pytest_args+=("-m" "elasticsearch")
            if [ "$ES_AVAILABLE" = false ]; then
                pytest_args+=("--skip-services")
            fi
            ;;
        "vllm")
            test_args+=("$INTEGRATION_TESTS_DIR")
            pytest_args+=("-m" "vllm")
            if [ "$VLLM_AVAILABLE" = false ]; then
                pytest_args+=("--skip-services")
            fi
            ;;
        *)
            print_error "Unknown test type: $TEST_TYPE"
            show_usage
            exit 1
            ;;
    esac
    
    # Run tests
    print_status "Running $TEST_TYPE tests..."
    print_status "Command: pytest ${pytest_args[*]} ${test_args[*]}"
    
    cd "$PROJECT_ROOT"
    
    if pytest "${pytest_args[@]}" "${test_args[@]}"; then
        print_success "$TEST_TYPE tests completed successfully"
        return 0
    else
        print_error "$TEST_TYPE tests failed"
        return 1
    fi
}

# Function to generate test summary
generate_summary() {
    print_status "Generating test summary..."
    
    local report_file="$REPORTS_DIR/report.html"
    local junit_file="$REPORTS_DIR/junit.xml"
    
    if [ -f "$report_file" ]; then
        print_success "HTML report generated: $report_file"
    fi
    
    if [ -f "$junit_file" ]; then
        print_success "JUnit XML report generated: $junit_file"
    fi
    
    if [ "$COVERAGE" = true ] && [ -d "$REPORTS_DIR/coverage" ]; then
        print_success "Coverage report generated: $REPORTS_DIR/coverage/index.html"
    fi
    
    # Print summary statistics if available
    if [ -f "$junit_file" ]; then
        local total_tests=$(grep -c '<testcase' "$junit_file" || echo "0")
        local failed_tests=$(grep -c '<failure' "$junit_file" || echo "0")
        local skipped_tests=$(grep -c '<skipped' "$junit_file" || echo "0")
        
        print_status "Test Summary:"
        echo "  Total tests: $total_tests"
        echo "  Failed: $failed_tests"
        echo "  Skipped: $skipped_tests"
        echo "  Passed: $((total_tests - failed_tests - skipped_tests))"
    fi
}

# Function to cleanup
cleanup() {
    print_status "Cleaning up..."
    
    # Remove test artifacts
    find "$PROJECT_ROOT" -name "*.pyc" -delete
    find "$PROJECT_ROOT" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    # Remove temporary test indices
    if [ "$ES_AVAILABLE" = true ]; then
        python3 -c "
import requests
try:
    response = requests.get('${ES_URL:-http://localhost:9200}/_cat/indices?format=json')
    if response.status_code == 200:
        indices = response.json()
        for index in indices:
            if '_test_' in index['index']:
                requests.delete('${ES_URL:-http://localhost:9200}/' + index['index'])
                print(f'Deleted test index: {index[\"index\"]}')
except:
    pass
" 2>/dev/null || true
    fi
    
    print_success "Cleanup completed"
}

# Main execution
main() {
    print_status "Starting Integration Tests Runner"
    print_status "Project root: $PROJECT_ROOT"
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--test-type)
                TEST_TYPE="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -p|--parallel)
                PARALLEL=true
                shift
                ;;
            -c|--coverage)
                COVERAGE=true
                shift
                ;;
            -r|--report)
                REPORT_FORMAT="$2"
                shift 2
                ;;
            -s|--skip-services)
                SKIP_SERVICES=true
                shift
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Validate report format
    case "$REPORT_FORMAT" in
        html|xml|json|term-missing)
            ;;
        *)
            print_error "Invalid report format: $REPORT_FORMAT"
            exit 1
            ;;
    esac
    
    # Execute test pipeline
    check_dependencies
    check_services
    setup_test_environment
    
    # Set trap for cleanup
    trap cleanup EXIT
    
    # Run tests
    if run_tests; then
        generate_summary
        print_success "All tests completed successfully!"
        exit 0
    else
        generate_summary
        print_error "Tests failed!"
        exit 1
    fi
}

# Run main function with all arguments
main "$@" 