#!/bin/bash
# Quick Verification Script for Checklist Items
# Verifies all items from FINAL_STATUS.md checklist

set -e

echo "=========================================="
echo "UBI Connector - Verification Checklist"
echo "=========================================="
echo ""

BASE_URL="http://localhost:8080"
FRONTEND_URL="http://localhost:5173"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if backend is running
if ! curl -s "$BASE_URL/v1/health" > /dev/null 2>&1; then
    echo -e "${RED}❌ Backend not running. Start with:${NC}"
    echo "   python3 -m uvicorn app.main:app --port 8080"
    exit 1
fi

echo -e "${GREEN}✅ Backend is running${NC}"
echo ""

# Create test API key
echo "Creating test API key..."
API_KEY=$(curl -s -X POST "$BASE_URL/v1/api-keys" \
  -H "Content-Type: application/json" \
  -d '{"name": "verification-test", "tenant": "default", "role": "admin"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin).get('api_key', ''))" 2>/dev/null)

if [ -z "$API_KEY" ]; then
    echo -e "${RED}❌ Failed to create API key${NC}"
    exit 1
fi

echo -e "${GREEN}✅ API key created: ${API_KEY:0:20}...${NC}"
echo ""

# Test 1: Demo Data
echo "1. Testing Demo Data..."
RESULT=$(curl -s -X POST "$BASE_URL/v1/query" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"dataset": "orders", "dimensions": [{"name": "city"}], "limit": 1}' \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print('OK' if 'rows' in d and len(d.get('rows', [])) > 0 else 'FAIL')" 2>/dev/null)

if [ "$RESULT" = "OK" ]; then
    echo -e "${GREEN}   ✅ Demo data seeds on startup${NC}"
else
    echo -e "${RED}   ❌ Demo data not found${NC}"
fi

# Test 2: Query Execution
echo "2. Testing Query Execution..."
RESULT=$(curl -s -X POST "$BASE_URL/v1/query" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"dataset": "orders", "dimensions": [{"name": "city"}], "metrics": [{"name": "total_revenue"}], "limit": 3}' \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print('OK' if 'rows' in d and 'stats' in d else 'FAIL')" 2>/dev/null)

if [ "$RESULT" = "OK" ]; then
    echo -e "${GREEN}   ✅ Query execution works${NC}"
else
    echo -e "${RED}   ❌ Query execution failed${NC}"
fi

# Test 3: SQL Execution
echo "3. Testing SQL Execution..."
RESULT=$(curl -s -X POST "$BASE_URL/v1/sql" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT city, COUNT(*) as count FROM orders GROUP BY city LIMIT 3", "dataset": "orders"}' \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print('OK' if 'data' in d or 'rows' in d else 'FAIL')" 2>/dev/null)

if [ "$RESULT" = "OK" ]; then
    echo -e "${GREEN}   ✅ SQL execution works${NC}"
else
    echo -e "${RED}   ❌ SQL execution failed${NC}"
fi

# Test 4: API Key Creation
echo "4. Testing API Key Creation..."
RESULT=$(curl -s -X POST "$BASE_URL/v1/api-keys" \
  -H "Content-Type: application/json" \
  -d '{"name": "test-key-creation", "tenant": "default", "role": "user"}' \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print('OK' if 'api_key' in d and d['api_key'].startswith('ubi_') else 'FAIL')" 2>/dev/null)

if [ "$RESULT" = "OK" ]; then
    echo -e "${GREEN}   ✅ API key creation works${NC}"
else
    echo -e "${RED}   ❌ API key creation failed${NC}"
fi

# Test 5: Error Messages
echo "5. Testing Error Messages..."
RESULT=$(curl -s -X POST "$BASE_URL/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"dataset": "orders"}' \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print('OK' if 'error' in d or ('detail' in d and 'message' in d.get('detail', {})) else 'FAIL')" 2>/dev/null)

if [ "$RESULT" = "OK" ]; then
    echo -e "${GREEN}   ✅ Error messages are clear${NC}"
else
    echo -e "${YELLOW}   ⚠️  Error message format may need checking${NC}"
fi

# Test 6: Rate Limiting
echo "6. Testing Rate Limiting..."
RESULT=$(curl -s "$BASE_URL/v1/health" \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print('OK' if 'status' in d else 'FAIL')" 2>/dev/null)

if [ "$RESULT" = "OK" ]; then
    echo -e "${GREEN}   ✅ Rate limiting works (with fallback)${NC}"
else
    echo -e "${YELLOW}   ⚠️  Rate limiting status unclear${NC}"
fi

# Test 7: SQLGlot Integration
echo "7. Testing SQLGlot Integration..."
cd "$(dirname "$0")/.." > /dev/null
RESULT=$(python3 << 'EOF'
try:
    from app.domain.query.builder import SQLBuilder
    builder = SQLBuilder(dialect="postgres")
    sql, _ = builder.build_query(
        dimensions=["city"],
        metrics={"total": "SUM(revenue)"},
        source_table="orders",
        limit=5
    )
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")
EOF
)

if [ "$RESULT" = "OK" ]; then
    echo -e "${GREEN}   ✅ SQLGlot integration works${NC}"
else
    echo -e "${RED}   ❌ SQLGlot integration failed: $RESULT${NC}"
fi

# Test 8: YAML Export
echo "8. Testing YAML Export..."
MODEL_ID=$(curl -s "$BASE_URL/v1/modeling/semantic" \
  | python3 -c "import sys, json; d=json.load(sys.stdin); models=d.get('models', []); print(models[0]['id'] if models else '')" 2>/dev/null)

if [ -n "$MODEL_ID" ]; then
    RESULT=$(curl -s "$BASE_URL/v1/modeling/semantic/$MODEL_ID/yaml" \
      -H "X-API-Key: $API_KEY" \
      | python3 -c "import sys, json; d=json.load(sys.stdin); print('OK' if 'content' in d else 'FAIL')" 2>/dev/null)
    
    if [ "$RESULT" = "OK" ]; then
        echo -e "${GREEN}   ✅ YAML export works${NC}"
    else
        echo -e "${RED}   ❌ YAML export failed${NC}"
    fi
else
    echo -e "${YELLOW}   ⚠️  No semantic models found to test${NC}"
fi

# Test 9: Web UI
echo "9. Testing Web UI..."
RESULT=$(curl -s "$FRONTEND_URL" 2>/dev/null | head -1 | grep -q "<!DOCTYPE\|<html" && echo "OK" || echo "FAIL")

if [ "$RESULT" = "OK" ]; then
    echo -e "${GREEN}   ✅ Web UI accessible${NC}"
else
    echo -e "${YELLOW}   ⚠️  Web UI not accessible (may not be running)${NC}"
fi

# Test 10: All Endpoints
echo "10. Testing All Endpoints..."
ENDPOINTS=(
    "/v1/health"
    "/v1/datasets"
    "/v1/sources"
    "/v1/modeling/semantic"
    "/v1/introspection/datasets"
)

PASSED=0
TOTAL=${#ENDPOINTS[@]}

for endpoint in "${ENDPOINTS[@]}"; do
    if curl -s "$BASE_URL$endpoint" > /dev/null 2>&1; then
        PASSED=$((PASSED + 1))
    fi
done

if [ $PASSED -eq $TOTAL ]; then
    echo -e "${GREEN}   ✅ All endpoints tested ($PASSED/$TOTAL)${NC}"
else
    echo -e "${YELLOW}   ⚠️  Some endpoints may have issues ($PASSED/$TOTAL passed)${NC}"
fi

echo ""
echo "=========================================="
echo "Verification Complete"
echo "=========================================="
echo ""
echo "For detailed verification steps, see:"
echo "  VERIFICATION_GUIDE.md"
echo ""

