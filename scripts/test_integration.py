#!/usr/bin/env python3
"""
Integration Test Script for UBI Connector

Tests all major endpoints and functionality.
"""

import sys
import json
import requests
from typing import Dict, List, Tuple

BASE_URL = "http://localhost:8080"
API_KEY = None

def test_endpoint(name: str, method: str, url: str, headers: Dict = None, data: Dict = None) -> Tuple[bool, str, Dict]:
    """Test an API endpoint."""
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=10)
        else:
            return False, f"Unsupported method: {method}", {}
        
        try:
            result = response.json() if response.content else {}
        except:
            result = {"status_code": response.status_code, "text": response.text[:200]}
        
        if response.status_code < 400:
            return True, f"Status: {response.status_code}", result
        else:
            return False, f"Status: {response.status_code}", result
    except requests.exceptions.ConnectionError:
        return False, "Connection refused - is server running?", {}
    except Exception as e:
        return False, f"Exception: {str(e)}", {}

def main():
    print("=" * 70)
    print("UBI CONNECTOR - INTEGRATION TESTS")
    print("=" * 70)
    print()
    
    results = {"passed": [], "failed": [], "warnings": []}
    
    # Test 1: Health Check
    print("1. Testing Health Endpoint...")
    success, msg, data = test_endpoint("Health", "GET", f"{BASE_URL}/v1/health")
    if success:
        results["passed"].append("Health Check")
        print(f"   ✅ PASSED: {msg}")
    else:
        results["failed"].append("Health Check")
        print(f"   ❌ FAILED: {msg}")
        if "Connection refused" in msg:
            print("   ⚠️  Server not running. Start with: python3 -m uvicorn app.main:app --port 8080")
            sys.exit(1)
    
    # Test 2: Create API Key
    print("\n2. Creating Test API Key...")
    success, msg, data = test_endpoint(
        "Create API Key",
        "POST",
        f"{BASE_URL}/v1/api-keys",
        data={"name": "integration-test", "tenant": "default", "role": "admin"}
    )
    if success and "api_key" in data:
        global API_KEY
        API_KEY = data["api_key"]
        results["passed"].append("API Key Creation")
        print(f"   ✅ PASSED: API key created")
        print(f"   Key: {API_KEY[:20]}...")
    else:
        results["failed"].append("API Key Creation")
        print(f"   ❌ FAILED: {msg}")
        print("   Continuing without API key (some tests will fail)")
    
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    
    # Test 3: List Datasets
    print("\n3. Testing Datasets List...")
    success, msg, data = test_endpoint("Datasets", "GET", f"{BASE_URL}/v1/datasets")
    if success:
        results["passed"].append("Datasets List")
        print(f"   ✅ PASSED: {msg}")
        if "items" in data and len(data["items"]) > 0:
            print(f"   Found {len(data['items'])} dataset(s)")
    else:
        results["failed"].append("Datasets List")
        print(f"   ❌ FAILED: {msg}")
    
    # Test 4: Get Dataset Details
    print("\n4. Testing Dataset Details...")
    success, msg, data = test_endpoint("Dataset Details", "GET", f"{BASE_URL}/v1/datasets/orders")
    if success:
        results["passed"].append("Dataset Details")
        print(f"   ✅ PASSED: {msg}")
    else:
        results["failed"].append("Dataset Details")
        print(f"   ❌ FAILED: {msg}")
    
    # Test 5: Query Execution (if API key available)
    if API_KEY:
        print("\n5. Testing Query Execution...")
        success, msg, data = test_endpoint(
            "Query",
            "POST",
            f"{BASE_URL}/v1/query",
            headers=headers,
            data={
                "dataset": "orders",
                "dimensions": [{"name": "city"}],
                "metrics": [{"name": "total_revenue"}],
                "limit": 5
            }
        )
        if success:
            results["passed"].append("Query Execution")
            print(f"   ✅ PASSED: {msg}")
            if "rows" in data:
                print(f"   Returned {len(data['rows'])} rows")
        else:
            results["failed"].append("Query Execution")
            print(f"   ❌ FAILED: {msg}")
    else:
        results["warnings"].append("Query Execution (skipped - no API key)")
        print("\n5. Testing Query Execution...")
        print("   ⚠️  SKIPPED: No API key available")
    
    # Test 6: SQL Execution (if API key available)
    if API_KEY:
        print("\n6. Testing SQL Execution...")
        success, msg, data = test_endpoint(
            "SQL",
            "POST",
            f"{BASE_URL}/v1/sql",
            headers=headers,
            data={
                "sql": "SELECT city, SUM(revenue) as total FROM orders GROUP BY city LIMIT 5",
                "dataset": "orders"
            }
        )
        if success:
            results["passed"].append("SQL Execution")
            print(f"   ✅ PASSED: {msg}")
        else:
            results["failed"].append("SQL Execution")
            print(f"   ❌ FAILED: {msg}")
    else:
        results["warnings"].append("SQL Execution (skipped - no API key)")
        print("\n6. Testing SQL Execution...")
        print("   ⚠️  SKIPPED: No API key available")
    
    # Test 7: Semantic Models
    print("\n7. Testing Semantic Models...")
    success, msg, data = test_endpoint("Semantic Models", "GET", f"{BASE_URL}/v1/modeling/semantic")
    if success:
        results["passed"].append("Semantic Models")
        print(f"   ✅ PASSED: {msg}")
        if "models" in data:
            print(f"   Found {len(data['models'])} semantic model(s)")
    else:
        results["failed"].append("Semantic Models")
        print(f"   ❌ FAILED: {msg}")
    
    # Test 8: YAML Export (if semantic models exist)
    print("\n8. Testing YAML Export (Feature Branch)...")
    success, msg, data = test_endpoint("Semantic Models", "GET", f"{BASE_URL}/v1/modeling/semantic")
    if success and "models" in data and len(data["models"]) > 0:
        model_id = data["models"][0]["id"]
        success, msg, yaml_data = test_endpoint(
            "YAML Export",
            "GET",
            f"{BASE_URL}/v1/modeling/semantic/{model_id}/yaml",
            headers=headers
        )
        if success:
            results["passed"].append("YAML Export")
            print(f"   ✅ PASSED: {msg}")
            if "content" in yaml_data:
                print(f"   YAML content length: {len(yaml_data['content'])} chars")
        else:
            results["failed"].append("YAML Export")
            print(f"   ❌ FAILED: {msg}")
    else:
        results["warnings"].append("YAML Export (skipped - no semantic models)")
        print("   ⚠️  SKIPPED: No semantic models found")
    
    # Test 9: Schema Introspection
    print("\n9. Testing Schema Introspection...")
    success, msg, data = test_endpoint("Introspection", "GET", f"{BASE_URL}/v1/introspection/datasets")
    if success:
        results["passed"].append("Schema Introspection")
        print(f"   ✅ PASSED: {msg}")
    else:
        results["failed"].append("Schema Introspection")
        print(f"   ❌ FAILED: {msg}")
    
    # Test 10: SQLGlot Integration
    print("\n10. Testing SQLGlot Integration...")
    try:
        import sys
        import os
        # Add parent directory to path
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from app.domain.query.builder import SQLBuilder
        builder = SQLBuilder(dialect="postgres")
        sql, params = builder.build_query(
            dimensions=["city"],
            metrics=["SUM(revenue)"],
            source_table="orders",
            limit=10
        )
        results["passed"].append("SQLGlot Integration")
        print(f"   ✅ PASSED: SQLGlot working")
        print(f"   Generated SQL: {sql[:60]}...")
    except Exception as e:
        results["failed"].append("SQLGlot Integration")
        print(f"   ❌ FAILED: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"✅ Passed: {len(results['passed'])}")
    print(f"❌ Failed: {len(results['failed'])}")
    print(f"⚠️  Warnings: {len(results['warnings'])}")
    print()
    
    if results["passed"]:
        print("Passed Tests:")
        for test in results["passed"]:
            print(f"  ✅ {test}")
    
    if results["failed"]:
        print("\nFailed Tests:")
        for test in results["failed"]:
            print(f"  ❌ {test}")
    
    if results["warnings"]:
        print("\nWarnings:")
        for test in results["warnings"]:
            print(f"  ⚠️  {test}")
    
    print("\n" + "=" * 70)
    
    if len(results["failed"]) == 0:
        print("✅ ALL TESTS PASSED!")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())

