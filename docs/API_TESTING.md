# API Testing Documentation

This document describes how to use the API testing script to validate the RAG API functionality, performance, and reliability.

## Overview

The API testing script (`scripts/test-api.sh`) provides comprehensive testing capabilities for the RAG API, including:

- **Health Checks**: Validate API endpoints and service availability
- **Functional Testing**: Test query functionality with various parameters
- **Error Handling**: Verify proper error responses for invalid inputs
- **Performance Testing**: Load testing and response time measurement
- **Reporting**: Detailed test reports with metrics and statistics

## Quick Start

### Basic Usage

```bash
# Run all tests with auto-detected endpoint
./scripts/test-api.sh

# Quick health check only
./scripts/test-api.sh -q

# Test specific endpoint with verbose output
./scripts/test-api.sh -e http://localhost:8000 -v

# Run load testing
./scripts/test-api.sh -l -c 10 -d 120
```

### Prerequisites

- `curl` command-line tool
- Bash shell
- API endpoint accessible (local or remote)
- Optional: OpenShift CLI (`oc`) for route detection

## Command Line Options

| Option | Long Option | Description | Default |
|--------|-------------|-------------|---------|
| `-e` | `--endpoint` | API endpoint URL | Auto-detect |
| `-v` | `--verbose` | Enable verbose output | false |
| `-q` | `--quick` | Quick mode (health checks only) | false |
| `-l` | `--load` | Run load testing | false |
| `-t` | `--timeout` | Request timeout in seconds | 30 |
| `-c` | `--concurrent` | Concurrent requests for load test | 5 |
| `-d` | `--duration` | Load test duration in seconds | 60 |
| `-r` | `--report` | Report format (text, json, html) | text |
| `-h` | `--help` | Show help message | - |

## Test Scenarios

### 1. Health Check Testing

Tests basic API endpoints to ensure the service is running and accessible.

**Endpoints Tested:**
- `/health` - Basic health status
- `/ready` - Service readiness (may return 503 if dependencies unavailable)
- `/api/v1/metrics` - Prometheus metrics
- `/api/v1/info` - API information

**Example:**
```bash
./scripts/test-api.sh -q
```

### 2. Query Functionality Testing

Tests the main RAG query functionality with various parameter combinations.

**Test Cases:**
- Basic query without additional parameters
- Query with metadata filters
- Query with different `top_k` values
- Query with specific model parameter
- Query with all parameters combined

**Example:**
```bash
./scripts/test-api.sh -e http://localhost:8000 -v
```

### 3. Error Scenario Testing

Validates proper error handling for invalid inputs and edge cases.

**Error Cases Tested:**
- Missing required parameters
- Invalid JSON format
- Empty query strings
- Invalid parameter values
- Non-existent endpoints
- Invalid model names

**Example:**
```bash
./scripts/test-api.sh -e http://localhost:8000
```

### 4. Parameter Validation Testing

Tests various parameter combinations to ensure proper validation.

**Parameters Tested:**
- Different `top_k` values (1, 2, 5, 10)
- Various filter combinations
- Model parameter variations

### 5. Performance Testing

Load testing to measure API performance under various conditions.

**Metrics Measured:**
- Response times (min, max, average)
- Success/failure rates
- Requests per second (RPS)
- Concurrent request handling

**Example:**
```bash
# Basic load test
./scripts/test-api.sh -l

# Intensive load test
./scripts/test-api.sh -l -c 20 -d 300

# Quick performance test
./scripts/test-api.sh -l -c 5 -d 30
```

## Environment Variables

The script supports the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `API_ENDPOINT` | Default API endpoint URL | Auto-detect |
| `ES_URL` | ElasticSearch URL for service checks | http://localhost:9200 |
| `VLLM_URL` | vLLM URL for service checks | http://localhost:8001 |

## Test Data

The script uses predefined test data from `tests/test-data.json`:

- **Test Queries**: Sample RAG queries with expected responses
- **Error Test Cases**: Invalid inputs and expected error responses
- **Performance Queries**: Queries optimized for load testing
- **Health Check Endpoints**: API endpoint definitions and expectations
- **Performance Thresholds**: Acceptable performance metrics
- **Load Test Configuration**: Load testing parameters

## Output and Reporting

### Console Output

The script provides colored, structured output:

- **Blue**: Information messages
- **Green**: Success messages
- **Yellow**: Warning messages
- **Red**: Error messages
- **Magenta**: Performance metrics
- **Cyan**: Section headers

### Test Reports

Reports are generated in the `api-test-reports/` directory:

- **Text Report**: Human-readable summary with metrics
- **Timestamp**: Each report includes timestamp for tracking
- **Performance Metrics**: Response times, success rates, throughput
- **Configuration**: Test parameters and environment details

**Report Location:** `api-test-reports/api_test_report_YYYYMMDD_HHMMSS.txt`

### Report Contents

```text
API Test Report
===============
Timestamp: 2024-01-15 14:30:25
API Endpoint: http://localhost:8000
Test Duration: 00:02:15

Test Summary:
  Total Tests: 25
  Passed: 23
  Failed: 2
  Skipped: 0
  Success Rate: 92%

Performance Metrics:
  Total Requests: 45
  Successful Requests: 43
  Failed Requests: 2
  Average Response Time: 1250ms
  Min Response Time: 850ms
  Max Response Time: 3200ms

Test Configuration:
  Verbose Mode: false
  Quick Mode: false
  Load Test: true
  Timeout: 30s
  Concurrent Requests: 5
  Test Duration: 60s
```

## Use Cases

### Development Testing

```bash
# Quick validation during development
./scripts/test-api.sh -q

# Comprehensive testing with verbose output
./scripts/test-api.sh -v
```

### CI/CD Integration

```bash
# Automated testing in CI pipeline
./scripts/test-api.sh -e $API_ENDPOINT -r json

# Performance validation
./scripts/test-api.sh -e $API_ENDPOINT -l -c 10 -d 60
```

### Production Validation

```bash
# Test production endpoint
./scripts/test-api.sh -e https://api.production.com

# Load test production environment
./scripts/test-api.sh -e https://api.production.com -l -c 5 -d 300
```

### OpenShift Deployment

```bash
# Auto-detect OpenShift route
./scripts/test-api.sh

# Test specific OpenShift route
./scripts/test-api.sh -e https://rag-api-openshift.apps.example.com
```

## Troubleshooting

### Common Issues

#### 1. API Endpoint Not Detected

**Symptoms:**
```
[ERROR] Could not detect API endpoint. Please specify with -e option.
```

**Solutions:**
- Specify endpoint manually: `./scripts/test-api.sh -e http://localhost:8000`
- Check if API is running: `curl http://localhost:8000/health`
- Verify port forwarding if using OpenShift: `oc port-forward svc/rag-api 8000:8000`

#### 2. Connection Timeout

**Symptoms:**
```
[ERROR] API is not accessible at http://localhost:8000
```

**Solutions:**
- Increase timeout: `./scripts/test-api.sh -t 60`
- Check network connectivity
- Verify firewall settings
- Check API service status

#### 3. Health Check Failures

**Symptoms:**
```
[ERROR] API responded but health check failed
```

**Solutions:**
- Check API logs for errors
- Verify dependencies (ElasticSearch, vLLM)
- Check API configuration
- Review health endpoint implementation

#### 4. Load Test Failures

**Symptoms:**
- High error rates during load testing
- Timeout errors
- Memory issues

**Solutions:**
- Reduce concurrent requests: `./scripts/test-api.sh -l -c 2`
- Increase timeout: `./scripts/test-api.sh -l -t 60`
- Check resource limits
- Monitor system resources

### Debug Mode

Enable verbose output for detailed debugging:

```bash
./scripts/test-api.sh -v -e http://localhost:8000
```

This will show:
- Full HTTP requests and responses
- Detailed error messages
- Timing information
- Response content (truncated)

### Performance Analysis

For performance issues, run load tests with different parameters:

```bash
# Light load
./scripts/test-api.sh -l -c 1 -d 30

# Medium load
./scripts/test-api.sh -l -c 5 -d 60

# Heavy load
./scripts/test-api.sh -l -c 10 -d 120
```

Compare results to identify bottlenecks and optimal configurations.

## Best Practices

### 1. Test Environment Setup

- Use dedicated test environment when possible
- Ensure consistent test data
- Monitor system resources during testing
- Clean up test artifacts after testing

### 2. Test Execution

- Start with quick health checks
- Run comprehensive tests before load testing
- Use appropriate timeouts for your environment
- Monitor API logs during testing

### 3. Performance Testing

- Start with light load and gradually increase
- Monitor system resources (CPU, memory, network)
- Run tests during off-peak hours in production
- Document baseline performance metrics

### 4. Reporting

- Save test reports for historical comparison
- Track performance trends over time
- Use reports for capacity planning
- Share results with development team

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: API Testing
on: [push, pull_request]

jobs:
  api-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Start API
        run: |
          # Start your API service
          docker-compose up -d
          sleep 30
      
      - name: Run API Tests
        run: |
          chmod +x scripts/test-api.sh
          ./scripts/test-api.sh -e http://localhost:8000 -r json
      
      - name: Upload Test Results
        uses: actions/upload-artifact@v3
        with:
          name: api-test-results
          path: api-test-reports/
```

### OpenShift Pipeline Example

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: api-test-pipeline
spec:
  tasks:
    - name: deploy-api
      taskRef:
        name: deploy-task
      
    - name: test-api
      taskRef:
        name: api-test-task
      params:
        - name: api-endpoint
          value: "$(params.api-endpoint)"
      runAfter: ["deploy-api"]
```

## Extending the Script

### Adding New Test Cases

1. **Update Test Data**: Add new test cases to `tests/test-data.json`
2. **Add Test Functions**: Create new test functions in the script
3. **Update Main Flow**: Integrate new tests into the main execution flow
4. **Update Documentation**: Document new test scenarios

### Custom Test Scenarios

```bash
# Example: Custom test function
test_custom_scenario() {
    print_header "Testing Custom Scenario"
    
    local custom_query='{"query": "Custom test query", "top_k": 1}'
    make_request "POST" "/api/v1/query" "$custom_query" "Custom test scenario"
}
```

### Integration with External Tools

The script can be integrated with external testing tools:

- **JMeter**: Use script output as input for JMeter tests
- **Grafana**: Send metrics to Grafana for visualization
- **Prometheus**: Export metrics in Prometheus format
- **Slack**: Send test results to Slack channels

## Support and Maintenance

### Script Maintenance

- Keep test data updated with API changes
- Review and update performance thresholds
- Add new test scenarios as API evolves
- Maintain compatibility with different environments

### Getting Help

- Check script help: `./scripts/test-api.sh -h`
- Review this documentation
- Check API logs for detailed error information
- Monitor system resources during testing

### Contributing

When contributing to the testing script:

1. Follow existing code style and patterns
2. Add appropriate error handling
3. Update documentation for new features
4. Test changes in multiple environments
5. Add new test cases for new API features 