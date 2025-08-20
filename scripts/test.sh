#!/bin/bash
# Test script for TTS System

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000}"
TIMEOUT=30

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

# Test HTTP endpoint
test_endpoint() {
    local url=$1
    local method=${2:-GET}
    local data=${3:-}
    local expected_status=${4:-200}
    
    local curl_cmd="curl -s -w '%{http_code}' -m $TIMEOUT"
    
    if [[ "$method" == "POST" && -n "$data" ]]; then
        curl_cmd="$curl_cmd -X POST -H 'Content-Type: application/json' -d '$data'"
    fi
    
    local response=$(eval "$curl_cmd '$url'")
    local status_code=$(echo "$response" | tail -c 4)
    local body=$(echo "$response" | sed '$ s/...$//')
    
    if [[ "$status_code" == "$expected_status" ]]; then
        print_status "✓ $url responded with $status_code"
        return 0
    else
        print_error "✗ $url responded with $status_code (expected $expected_status)"
        echo "Response body: $body"
        return 1
    fi
}

# Wait for service to be ready
wait_for_service() {
    local url=$1
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for service at $url..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            print_status "Service is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    print_error "Service did not become ready within $(($max_attempts * 2)) seconds"
    return 1
}

# Test gateway health endpoints
test_health_endpoints() {
    print_test "Testing health endpoints..."
    
    test_endpoint "$GATEWAY_URL/health"
    test_endpoint "$GATEWAY_URL/health/quick"
    test_endpoint "$GATEWAY_URL/health/models"
    test_endpoint "$GATEWAY_URL/models"
}

# Test TTS generation
test_tts_generation() {
    print_test "Testing TTS generation..."
    
    # Test Kokkoro
    local kokkoro_request='{
        "text": "こんにちは、世界！",
        "voice_id": "default",
        "language": "ja",
        "format": "wav"
    }'
    
    test_endpoint "$GATEWAY_URL/tts/kokkoro" "POST" "$kokkoro_request" "200"
    
    # Test Chatterbox
    local chatterbox_request='{
        "text": "Hello, world!",
        "voice_id": "default",
        "language": "en",
        "format": "wav"
    }'
    
    test_endpoint "$GATEWAY_URL/tts/chatterbox" "POST" "$chatterbox_request" "200"
}

# Test error handling
test_error_handling() {
    print_test "Testing error handling..."
    
    # Test invalid model
    local invalid_request='{
        "text": "Hello, world!",
        "voice_id": "default"
    }'
    
    test_endpoint "$GATEWAY_URL/tts/invalid_model" "POST" "$invalid_request" "400"
    
    # Test empty text
    local empty_text_request='{
        "text": "",
        "voice_id": "default"
    }'
    
    test_endpoint "$GATEWAY_URL/tts/kokkoro" "POST" "$empty_text_request" "422"
}

# Test performance
test_performance() {
    print_test "Testing performance..."
    
    local request='{
        "text": "This is a performance test for the TTS system.",
        "voice_id": "default",
        "language": "en"
    }'
    
    local start_time=$(date +%s.%N)
    
    if test_endpoint "$GATEWAY_URL/tts/chatterbox" "POST" "$request" "200"; then
        local end_time=$(date +%s.%N)
        local duration=$(echo "$end_time - $start_time" | bc)
        print_status "TTS generation took ${duration}s"
        
        # Warn if too slow
        if (( $(echo "$duration > 10" | bc -l) )); then
            print_warning "TTS generation is slower than expected (>10s)"
        fi
    fi
}

# Test concurrent requests
test_concurrent_requests() {
    print_test "Testing concurrent requests..."
    
    local request='{
        "text": "Concurrent test request",
        "voice_id": "default",
        "language": "en"
    }'
    
    local pids=()
    local success_count=0
    
    # Start 5 concurrent requests
    for i in {1..5}; do
        (
            if test_endpoint "$GATEWAY_URL/tts/chatterbox" "POST" "$request" "200" > /dev/null 2>&1; then
                echo "success"
            else
                echo "failure"
            fi
        ) &
        pids+=($!)
    done
    
    # Wait for all requests to complete
    for pid in "${pids[@]}"; do
        if wait $pid; then
            ((success_count++))
        fi
    done
    
    print_status "Concurrent requests: $success_count/5 successful"
    
    if [[ $success_count -lt 3 ]]; then
        print_warning "Less than 60% of concurrent requests succeeded"
    fi
}

# Test Docker containers (if running locally)
test_docker_containers() {
    if command -v docker &> /dev/null; then
        print_test "Testing Docker containers..."
        
        # Check if containers are running
        local containers=("tts-gateway" "tts-kokkoro" "tts-chatterbox")
        
        for container in "${containers[@]}"; do
            if docker ps --format "table {{.Names}}" | grep -q "$container"; then
                print_status "✓ Container $container is running"
                
                # Check container health
                local health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "unknown")
                if [[ "$health" == "healthy" ]]; then
                    print_status "✓ Container $container is healthy"
                elif [[ "$health" == "unknown" ]]; then
                    print_warning "? Container $container has no health check"
                else
                    print_warning "! Container $container health: $health"
                fi
            else
                print_error "✗ Container $container is not running"
            fi
        done
    else
        print_warning "Docker not available, skipping container tests"
    fi
}

# Generate test report
generate_report() {
    local report_file="test_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "TTS System Test Report"
        echo "======================"
        echo "Date: $(date)"
        echo "Gateway URL: $GATEWAY_URL"
        echo ""
        echo "Test Results:"
        echo "- Health Endpoints: $health_tests_passed"
        echo "- TTS Generation: $tts_tests_passed" 
        echo "- Error Handling: $error_tests_passed"
        echo "- Performance: $performance_tests_passed"
        echo "- Concurrent: $concurrent_tests_passed"
        echo "- Docker: $docker_tests_passed"
        echo ""
        echo "Overall: $total_passed/$total_tests tests passed"
    } > "$report_file"
    
    print_status "Test report saved to $report_file"
}

# Main test runner
run_all_tests() {
    print_status "Starting TTS System tests..."
    print_status "Gateway URL: $GATEWAY_URL"
    echo ""
    
    # Wait for gateway to be ready
    wait_for_service "$GATEWAY_URL/health" || exit 1
    
    local total_tests=0
    local total_passed=0
    
    # Run test suites
    if test_health_endpoints; then
        ((total_passed++))
        health_tests_passed="PASS"
    else
        health_tests_passed="FAIL"
    fi
    ((total_tests++))
    
    if test_tts_generation; then
        ((total_passed++))
        tts_tests_passed="PASS"
    else
        tts_tests_passed="FAIL"
    fi
    ((total_tests++))
    
    if test_error_handling; then
        ((total_passed++))
        error_tests_passed="PASS"
    else
        error_tests_passed="FAIL"
    fi
    ((total_tests++))
    
    if test_performance; then
        ((total_passed++))
        performance_tests_passed="PASS"
    else
        performance_tests_passed="FAIL"
    fi
    ((total_tests++))
    
    if test_concurrent_requests; then
        ((total_passed++))
        concurrent_tests_passed="PASS"
    else
        concurrent_tests_passed="FAIL"
    fi
    ((total_tests++))
    
    if test_docker_containers; then
        ((total_passed++))
        docker_tests_passed="PASS"
    else
        docker_tests_passed="FAIL"
    fi
    ((total_tests++))
    
    # Print summary
    echo ""
    print_status "Test Summary: $total_passed/$total_tests tests passed"
    
    if [[ $total_passed -eq $total_tests ]]; then
        print_status "🎉 All tests passed!"
        exit 0
    else
        print_error "❌ Some tests failed"
        exit 1
    fi
}

# Show help
show_help() {
    echo "TTS System Test Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  all       Run all tests (default)"
    echo "  health    Test health endpoints only"
    echo "  tts       Test TTS generation only"
    echo "  error     Test error handling only"
    echo "  perf      Test performance only"
    echo "  docker    Test Docker containers only"
    echo "  help      Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  GATEWAY_URL   Gateway URL (default: http://localhost:8000)"
    echo "  TIMEOUT       Request timeout in seconds (default: 30)"
    echo ""
    echo "Examples:"
    echo "  $0"
    echo "  GATEWAY_URL=http://gateway:8000 $0 health"
    echo "  $0 tts"
}

# Main function
main() {
    local command="${1:-all}"
    
    case "$command" in
        "all")
            run_all_tests
            ;;
        "health")
            wait_for_service "$GATEWAY_URL/health"
            test_health_endpoints
            ;;
        "tts")
            wait_for_service "$GATEWAY_URL/health"
            test_tts_generation
            ;;
        "error")
            wait_for_service "$GATEWAY_URL/health"
            test_error_handling
            ;;
        "perf")
            wait_for_service "$GATEWAY_URL/health"
            test_performance
            ;;
        "docker")
            test_docker_containers
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
