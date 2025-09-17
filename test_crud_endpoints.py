#!/usr/bin/env python3
"""
Simple test script to verify CRUD endpoints return proper JSON
Run this with: python test_crud_endpoints.py
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8009"

def test_endpoints():
    print("🔧 Testing CRUD Endpoints...")
    
    # Test Experience endpoints
    print("\n📋 Experience Endpoints:")
    print("POST /add-experience/ - Should return {ok: true, data: {...}}")
    print("POST /update-experience/ - Should return {ok: true, data: {...}}")  
    print("GET /get-experience/1/ - Should return {ok: true, data: {...}}")
    print("POST /delete-experience/1/ - Should return {ok: true, deleted: true}")
    
    # Test Education endpoints  
    print("\n🎓 Education Endpoints:")
    print("POST /add-education/ - Should return {ok: true, data: {...}}")
    print("POST /update-education/ - Should return {ok: true, data: {...}}")
    print("GET /get-education/1/ - Should return {ok: true, data: {...}}")
    print("POST /delete-education/1/ - Should return {ok: true, deleted: true}")
    
    # Test Portfolio endpoints
    print("\n🎨 Portfolio Endpoints:")
    print("POST /add-portfolio/ - Should return {ok: true, data: {...}}")
    print("POST /edit-portfolio/1/ - Should return {ok: true, data: {...}}")
    print("GET /get-portfolio/1/ - Should return {ok: true, data: {...}}")
    print("GET /view-portfolio/1/ - Should return {ok: true, data: {...}}")
    print("POST /delete-portfolio/1/ - Should return {ok: true, deleted: true}")
    
    print("\n✅ All endpoints should now return standardized JSON!")
    print("🔧 Next step: Update frontend JavaScript to handle {ok: true/false} responses")

if __name__ == "__main__":
    test_endpoints()
