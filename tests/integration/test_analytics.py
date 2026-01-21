#!/usr/bin/env python3
"""
Test script to verify DuckDB analytics storage is working.
Run this after restarting the server.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8080"
API_KEY = "dev-key-123"

def test_analytics():
    print("=" * 60)
    print("Testing DuckDB Analytics Storage")
    print("=" * 60)
    
    # Step 1: Check health
    print("\n1. Checking server health...")
    try:
        resp = requests.get(f"{BASE_URL}/v1/health")
        if resp.status_code == 200:
            print("   ✓ Server is running")
        else:
            print(f"   ✗ Server returned status {resp.status_code}")
            return
    except Exception as e:
        print(f"   ✗ Cannot connect to server: {e}")
        print("   Make sure the server is running on http://localhost:8080")
        return
    
    # Step 2: Check initial analytics (should be empty)
    print("\n2. Checking initial analytics state...")
    headers = {"X-API-Key": API_KEY}
    resp = requests.get(f"{BASE_URL}/v1/analytics?hours=24", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        total = data.get("stats", {}).get("total_queries", 0)
        print(f"   Initial queries: {total}")
        print(f"   Query volume hours: {len(data.get('query_volume', []))}")
        print(f"   Recent queries: {len(data.get('recent_queries', []))}")
    else:
        print(f"   ✗ Failed to get analytics: {resp.status_code}")
        print(f"   Response: {resp.text[:200]}")
        return
    
    # Step 3: Execute a test query
    print("\n3. Executing test query...")
    query_payload = {
        "dataset": "orders",
        "dimensions": [{"name": "order_date"}],
        "metrics": [{"name": "total_revenue"}],
        "limit": 5
    }
    resp = requests.post(
        f"{BASE_URL}/v1/query",
        headers={**headers, "Content-Type": "application/json"},
        json=query_payload
    )
    if resp.status_code == 200:
        result = resp.json()
        rows = len(result.get("rows", []))
        print(f"   ✓ Query executed successfully ({rows} rows returned)")
    else:
        print(f"   ✗ Query failed: {resp.status_code}")
        print(f"   Response: {resp.text[:200]}")
        return
    
    # Step 4: Wait a moment for analytics to be recorded
    print("\n4. Waiting for analytics to be recorded...")
    time.sleep(2)
    
    # Step 5: Check analytics again
    print("\n5. Checking analytics after query...")
    resp = requests.get(f"{BASE_URL}/v1/analytics?hours=24", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        stats = data.get("stats", {})
        total = stats.get("total_queries", 0)
        errors = stats.get("total_errors", 0)
        avg_duration = stats.get("avg_duration_ms", 0)
        cache_hit_rate = stats.get("cache_hit_rate", 0)
        
        print(f"   Total Queries: {total}")
        print(f"   Total Errors: {errors}")
        print(f"   Avg Duration: {avg_duration:.2f}ms")
        print(f"   Cache Hit Rate: {cache_hit_rate*100:.1f}%")
        print(f"   Recent Queries: {len(data.get('recent_queries', []))}")
        
        # Check query volume
        query_volume = data.get("query_volume", [])
        non_zero_hours = [q for q in query_volume if q.get("queries", 0) > 0]
        print(f"   Hours with queries: {len(non_zero_hours)}")
        
        if total > 0:
            print("\n   ✓ SUCCESS: Analytics tracking is working!")
            print(f"   ✓ Query was recorded in DuckDB")
            if len(data.get("recent_queries", [])) > 0:
                print("\n   Recent Queries:")
                for i, q in enumerate(data.get("recent_queries", [])[:3], 1):
                    print(f"     {i}. {q.get('dataset')} - {q.get('duration')} - {q.get('status')}")
        else:
            print("\n   ✗ WARNING: Query was executed but not recorded in analytics")
            print("   Possible issues:")
            print("     - Analytics module not initialized")
            print("     - DuckDB storage not connected")
            print("     - Check server logs for errors")
    else:
        print(f"   ✗ Failed to get analytics: {resp.status_code}")
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)

if __name__ == "__main__":
    test_analytics()
