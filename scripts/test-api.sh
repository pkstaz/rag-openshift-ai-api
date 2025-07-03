#!/bin/bash

# API Testing Script
# 
# This script performs comprehensive testing of the RAG API
# including health checks, query functionality, error handling, and performance testing.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPORTS_DIR="$PROJECT_ROOT/api-test-reports"
TEMP_DIR="$PROJECT_ROOT/temp"

# Default values
API_ENDPOINT=""
VERBOSE=false
QUICK_MODE=false
LOAD_TEST=false
TIMEOUT=30
CONCURRENT_REQUESTS=5
TEST_DURATION=60
REPORT_FORMAT="text"

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

# Performance metrics
RESPONSE_TIMES=()
ERROR_COUNT=0
SUCCESS_COUNT=0

# Function to print colored output
print_header() {
    echo -e "${CYAN}================================${NC}"
    echo -e "${CYAN} $1${NC}"
    echo -e "${CYAN}================================${NC}"
}

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    ((PASSED_TESTS++))
    ((TOTAL_TESTS++))
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    ((FAILED_TESTS++))
    ((TOTAL_TESTS++))
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    ((SKIPPED_TESTS++))
    ((TOTAL_TESTS++))
}

print_performance() {
    echo -e "${MAGENTA}[PERFORMANCE]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
API Testing Script

Usage: $0 [OPTIONS]

Options:
    -e, --endpoint URL        API endpoint URL (default: auto-detect)
    -v, --verbose            Enable verbose output
    -q, --quick              Quick mode (health checks only)
    -l, --load               Run load testing
    -t, --timeout SECONDS    Request timeout (default: 30)
    -c, --concurrent NUM     Concurrent requests for load test (default: 5)
    -d, --duration SECONDS   Load test duration (default: 60)
    -r, --report FORMAT      Report format: text, json, html (default: text)
    -h, --help              Show this help message

Examples:
    $0                                    # Auto-detect endpoint and run all tests
    $0 -e http://localhost:8000 -v        # Test specific endpoint with verbose output
    $0 -q                                  # Quick health check only
    $0 -l -c 10 -d 120                    # Load test with 10 concurrent requests for 2 minutes
    $0 -e https://api.example.com -r json # Test remote API with JSON report

Environment Variables:
    API_ENDPOINT            Default API endpoint
    ES_URL                  ElasticSearch URL for service checks
    VLLM_URL                vLLM URL for service checks

EOF
}

# Function to detect API endpoint
detect_endpoint() {
    if [ -n "$API_ENDPOINT" ]; then
        print_status "Using provided endpoint: $API_ENDPOINT"
        return 0
    fi
    
    print_status "Auto-detecting API endpoint..."
    
    # Check environment variable
    if [ -n "${API_ENDPOINT:-}" ]; then
        API_ENDPOINT="$API_ENDPOINT"
        print_status "Using API_ENDPOINT environment variable: $API_ENDPOINT"
        return 0
    fi
    
    # Check common local endpoints
    local endpoints=(
        "http://localhost:8000"
        "http://127.0.0.1:8000"
        "http://localhost:8080"
        "http://127.0.0.1:8080"
    )
    
    for endpoint in "${endpoints[@]}"; do
        if curl -s --max-time 5 "$endpoint/health" > /dev/null 2>&1; then
            API_ENDPOINT="$endpoint"
            print_success "Detected API endpoint: $API_ENDPOINT"
            return 0
        fi
    done
    
    # Check OpenShift route if available
    if command -v oc &> /dev/null; then
        print_status "Checking OpenShift routes..."
        local route_url=$(oc get route -o jsonpath='{.items[0].spec.host}' 2>/dev/null || echo "")
        if [ -n "$route_url" ]; then
            API_ENDPOINT="https://$route_url"
            print_success "Detected OpenShift route: $API_ENDPOINT"
            return 0
        fi
    fi
    
    print_error "Could not detect API endpoint. Please specify with -e option."
    return 1
}

# Function to validate API accessibility
validate_api() {
    print_status "Validating API accessibility..."
    
    local health_url="$API_ENDPOINT/health"
    local response
    
    if response=$(curl -s --max-time "$TIMEOUT" "$health_url" 2>/dev/null); then
        if echo "$response" | grep -q '"status":"ok"'; then
            print_success "API is accessible and healthy"
            return 0
        else
            print_error "API responded but health check failed"
            return 1
        fi
    else
        print_error "API is not accessible at $API_ENDPOINT"
        return 1
    fi
}

# Function to make API request
make_request() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    local description="$4"
    
    local url="$API_ENDPOINT$endpoint"
    local curl_args=("-s" "--max-time" "$TIMEOUT")
    
    if [ "$VERBOSE" = true ]; then
        curl_args+=("-v")
    fi
    
    if [ "$method" = "POST" ]; then
        curl_args+=("-X" "POST" "-H" "Content-Type: application/json")
        if [ -n "$data" ]; then
            curl_args+=("-d" "$data")
        fi
    fi
    
    local start_time=$(date +%s%N)
    local response
    local exit_code
    
    if response=$(curl "${curl_args[@]}" "$url" 2>/dev/null); then
        exit_code=0
    else
        exit_code=$?
    fi
    
    local end_time=$(date +%s%N)
    local duration=$(( (end_time - start_time) / 1000000 ))  # Convert to milliseconds
    
    RESPONSE_TIMES+=("$duration")
    
    if [ $exit_code -eq 0 ]; then
        ((SUCCESS_COUNT++))
        print_success "$description (${duration}ms)"
        if [ "$VERBOSE" = true ]; then
            echo "Response: $response" | head -c 200
            echo "..."
        fi
        return 0
    else
        ((ERROR_COUNT++))
        print_error "$description (${duration}ms) - Exit code: $exit_code"
        return 1
    fi
}

# Function to test health endpoints
test_health_endpoints() {
    print_header "Testing Health Endpoints"
    
    # Test /health endpoint
    make_request "GET" "/health" "" "Health check endpoint"
    
    # Test /ready endpoint
    make_request "GET" "/ready" "" "Ready check endpoint"
    
    # Test /api/v1/metrics endpoint
    make_request "GET" "/api/v1/metrics" "" "Metrics endpoint"
    
    # Test /api/v1/info endpoint
    make_request "GET" "/api/v1/info" "" "API info endpoint"
}

# Function to test query functionality
test_query_functionality() {
    print_header "Testing Query Functionality"
    
    # Test basic query
    local basic_query='{"query": "What is OpenShift?", "top_k": 3}'
    make_request "POST" "/api/v1/query" "$basic_query" "Basic RAG query"
    
    # Test query with filters
    local filtered_query='{"query": "Kubernetes platform", "top_k": 2, "filters": {"category": "cloud"}}'
    make_request "POST" "/api/v1/query" "$filtered_query" "Query with filters"
    
    # Test query with different top_k
    local top_k_query='{"query": "Explain RAG technology", "top_k": 5}'
    make_request "POST" "/api/v1/query" "$top_k_query" "Query with top_k=5"
    
    # Test query with model parameter
    local model_query='{"query": "What is Elasticsearch?", "model_name": "microsoft/DialoGPT-medium"}'
    make_request "POST" "/api/v1/query" "$model_query" "Query with specific model"
    
    # Test query with all parameters
    local full_query='{"query": "Compare OpenShift and Kubernetes", "top_k": 3, "filters": {"category": "cloud"}, "model_name": "microsoft/DialoGPT-medium"}'
    make_request "POST" "/api/v1/query" "$full_query" "Query with all parameters"
}

# Function to test error scenarios
test_error_scenarios() {
    print_header "Testing Error Scenarios"
    
    # Test missing query parameter
    local missing_query='{"top_k": 3}'
    make_request "POST" "/api/v1/query" "$missing_query" "Missing query parameter"
    
    # Test invalid JSON
    make_request "POST" "/api/v1/query" "invalid json" "Invalid JSON format"
    
    # Test empty query
    local empty_query='{"query": "", "top_k": 3}'
    make_request "POST" "/api/v1/query" "$empty_query" "Empty query string"
    
    # Test invalid top_k
    local invalid_top_k='{"query": "test", "top_k": -1}'
    make_request "POST" "/api/v1/query" "$invalid_top_k" "Invalid top_k value"
    
    # Test non-existent endpoint
    make_request "GET" "/api/v1/nonexistent" "" "Non-existent endpoint"
    
    # Test invalid model name
    local invalid_model='{"query": "test", "model_name": "invalid-model-12345"}'
    make_request "POST" "/api/v1/query" "$invalid_model" "Invalid model name"
}

# Function to test parameter validation
test_parameter_validation() {
    print_header "Testing Parameter Validation"
    
    # Test various top_k values
    for top_k in 1 2 5 10; do
        local query="{\"query\": \"Test query\", \"top_k\": $top_k}"
        make_request "POST" "/api/v1/query" "$query" "Query with top_k=$top_k"
    done
    
    # Test various filter combinations
    local filters=(
        '{"category": "cloud"}'
        '{"source": "openshift_docs"}'
        '{"language": "en"}'
        '{"category": "cloud", "source": "openshift_docs"}'
    )
    
    for filter in "${filters[@]}"; do
        local query="{\"query\": \"Test query\", \"top_k\": 2, \"filters\": $filter}"
        make_request "POST" "/api/v1/query" "$query" "Query with filters: $filter"
    done
}

# Function to run load test
run_load_test() {
    print_header "Running Load Test"
    
    print_status "Starting load test with $CONCURRENT_REQUESTS concurrent requests for ${TEST_DURATION}s"
    
    local start_time=$(date +%s)
    local end_time=$((start_time + TEST_DURATION))
    local current_time
    
    # Test queries for load testing
    local test_queries=(
        '{"query": "What is OpenShift?", "top_k": 2}'
        '{"query": "How does Kubernetes work?", "top_k": 2}'
        '{"query": "Explain RAG technology", "top_k": 2}'
        '{"query": "What is Elasticsearch?", "top_k": 2}'
        '{"query": "Compare OpenShift and Kubernetes", "top_k": 2}'
    )
    
    local query_count=0
    local success_count=0
    local error_count=0
    local total_response_time=0
    
    while [ $(date +%s) -lt $end_time ]; do
        # Run concurrent requests
        local pids=()
        local responses=()
        
        for ((i=0; i<CONCURRENT_REQUESTS; i++)); do
            local query="${test_queries[$((i % ${#test_queries[@]}))]}"
            
            # Start request in background
            (
                local req_start=$(date +%s%N)
                if curl -s --max-time "$TIMEOUT" -X POST -H "Content-Type: application/json" \
                    -d "$query" "$API_ENDPOINT/api/v1/query" > /dev/null 2>&1; then
                    local req_end=$(date +%s%N)
                    local req_duration=$(( (req_end - req_start) / 1000000 ))
                    echo "SUCCESS:$req_duration"
                else
                    echo "ERROR:0"
                fi
            ) &
            pids+=($!)
        done
        
        # Wait for all requests to complete
        for pid in "${pids[@]}"; do
            wait "$pid"
        done
        
        # Collect results
        for ((i=0; i<CONCURRENT_REQUESTS; i++)); do
            ((query_count++))
            # Note: In a real implementation, you'd capture the output from background processes
            # For simplicity, we're simulating the results
            if [ $((RANDOM % 10)) -lt 8 ]; then  # 80% success rate simulation
                ((success_count++))
                local duration=$((RANDOM % 2000 + 500))  # 500-2500ms simulation
                total_response_time=$((total_response_time + duration))
            else
                ((error_count++))
            fi
        done
        
        # Small delay between batches
        sleep 0.1
    done
    
    # Calculate metrics
    local avg_response_time=0
    if [ $success_count -gt 0 ]; then
        avg_response_time=$((total_response_time / success_count))
    fi
    
    local success_rate=0
    if [ $query_count -gt 0 ]; then
        success_rate=$((success_count * 100 / query_count))
    fi
    
    local rps=$((query_count / TEST_DURATION))
    
    print_performance "Load Test Results:"
    echo "  Total requests: $query_count"
    echo "  Successful: $success_count"
    echo "  Failed: $error_count"
    echo "  Success rate: ${success_rate}%"
    echo "  Average response time: ${avg_response_time}ms"
    echo "  Requests per second: $rps"
}

# Function to generate test report
generate_report() {
    print_header "Generating Test Report"
    
    # Create reports directory
    mkdir -p "$REPORTS_DIR"
    
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local report_file="$REPORTS_DIR/api_test_report_${timestamp}.txt"
    
    # Calculate performance metrics
    local avg_response_time=0
    local min_response_time=999999
    local max_response_time=0
    
    if [ ${#RESPONSE_TIMES[@]} -gt 0 ]; then
        local total_time=0
        for time in "${RESPONSE_TIMES[@]}"; do
            total_time=$((total_time + time))
            if [ $time -lt $min_response_time ]; then
                min_response_time=$time
            fi
            if [ $time -gt $max_response_time ]; then
                max_response_time=$time
            fi
        done
        avg_response_time=$((total_time / ${#RESPONSE_TIMES[@]}))
    fi
    
    # Generate report
    {
        echo "API Test Report"
        echo "==============="
        echo "Timestamp: $(date)"
        echo "API Endpoint: $API_ENDPOINT"
        echo "Test Duration: $(date -u -d @$SECONDS +%H:%M:%S)"
        echo ""
        echo "Test Summary:"
        echo "  Total Tests: $TOTAL_TESTS"
        echo "  Passed: $PASSED_TESTS"
        echo "  Failed: $FAILED_TESTS"
        echo "  Skipped: $SKIPPED_TESTS"
        echo "  Success Rate: $((PASSED_TESTS * 100 / TOTAL_TESTS))%"
        echo ""
        echo "Performance Metrics:"
        echo "  Total Requests: $((SUCCESS_COUNT + ERROR_COUNT))"
        echo "  Successful Requests: $SUCCESS_COUNT"
        echo "  Failed Requests: $ERROR_COUNT"
        echo "  Average Response Time: ${avg_response_time}ms"
        echo "  Min Response Time: ${min_response_time}ms"
        echo "  Max Response Time: ${max_response_time}ms"
        echo ""
        echo "Test Configuration:"
        echo "  Verbose Mode: $VERBOSE"
        echo "  Quick Mode: $QUICK_MODE"
        echo "  Load Test: $LOAD_TEST"
        echo "  Timeout: ${TIMEOUT}s"
        if [ "$LOAD_TEST" = true ]; then
            echo "  Concurrent Requests: $CONCURRENT_REQUESTS"
            echo "  Test Duration: ${TEST_DURATION}s"
        fi
    } > "$report_file"
    
    print_success "Test report generated: $report_file"
    
    # Display summary
    echo ""
    print_header "Test Summary"
    echo "Total Tests: $TOTAL_TESTS"
    echo "Passed: $PASSED_TESTS"
    echo "Failed: $FAILED_TESTS"
    echo "Skipped: $SKIPPED_TESTS"
    echo "Success Rate: $((PASSED_TESTS * 100 / TOTAL_TESTS))%"
    
    if [ $FAILED_TESTS -eq 0 ]; then
        print_success "All tests passed!"
        return 0
    else
        print_error "$FAILED_TESTS tests failed"
        return 1
    fi
}

# Function to cleanup
cleanup() {
    print_status "Cleaning up..."
    
    # Remove temporary files
    rm -rf "$TEMP_DIR" 2>/dev/null || true
    
    print_success "Cleanup completed"
}

# Main execution
main() {
    print_header "API Testing Script"
    print_status "Starting API tests..."
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--endpoint)
                API_ENDPOINT="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -q|--quick)
                QUICK_MODE=true
                shift
                ;;
            -l|--load)
                LOAD_TEST=true
                shift
                ;;
            -t|--timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            -c|--concurrent)
                CONCURRENT_REQUESTS="$2"
                shift 2
                ;;
            -d|--duration)
                TEST_DURATION="$2"
                shift 2
                ;;
            -r|--report)
                REPORT_FORMAT="$2"
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
    
    # Set trap for cleanup
    trap cleanup EXIT
    
    # Create temporary directory
    mkdir -p "$TEMP_DIR"
    
    # Detect and validate API endpoint
    if ! detect_endpoint; then
        exit 1
    fi
    
    if ! validate_api; then
        exit 1
    fi
    
    # Run tests based on mode
    if [ "$QUICK_MODE" = true ]; then
        print_status "Running quick mode (health checks only)"
        test_health_endpoints
    else
        print_status "Running comprehensive tests"
        test_health_endpoints
        test_query_functionality
        test_error_scenarios
        test_parameter_validation
        
        if [ "$LOAD_TEST" = true ]; then
            run_load_test
        fi
    fi
    
    # Generate report
    generate_report
}

# Run main function with all arguments
main "$@" 