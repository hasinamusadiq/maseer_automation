#!/usr/bin/env python3
"""
Parse GitHub Issue and add client to database.
Located at: .github/scripts/update_clients.py
"""

import json
import os
import re
import sys
import requests
import base64
from datetime import datetime

# Calculate paths - we are in .github/scripts/, repo root is 2 levels up
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GITHUB_DIR = os.path.dirname(SCRIPT_DIR)
REPO_ROOT = os.path.dirname(GITHUB_DIR)

# Set paths relative to repo root
DATA_DIR = os.path.join(REPO_ROOT, 'data')
LOGOS_DIR = os.path.join(REPO_ROOT, 'logos')

print(f"📁 Working directories:")
print(f"   Script: {SCRIPT_DIR}")
print(f"   Repo root: {REPO_ROOT}")
print(f"   Data: {DATA_DIR}")
print(f"   Logos: {LOGOS_DIR}")


def save_base64_logo(base64_data, brand_name):
    """Save base64-encoded logo."""
    try:
        if ',' in base64_data:
            header, base64_data = base64_data.split(',', 1)
        
        logo_bytes = base64.b64decode(base64_data)
        
        # Clean filename
        safe_name = re.sub(r'[^\w\s-]', '', brand_name).replace(' ', '_')
        logo_path = os.path.join(LOGOS_DIR, f'{safe_name}_logo.png')
        
        os.makedirs(LOGOS_DIR, exist_ok=True)
        
        with open(logo_path, 'wb') as f:
            f.write(logo_bytes)
        
        print(f"   ✅ Logo saved: {logo_path} ({len(logo_bytes)} bytes)")
        return logo_path
        
    except Exception as e:
        print(f"   ⚠️ Error saving logo: {e}")
        return None


def parse_issue_body(body):
    """Extract client data from issue body."""
    client_data = {}
    
    if not body:
        print("❌ Error: Empty issue body")
        return client_data
    
    lines = body.split('\n')
    
    # Parse table rows
    for line in lines:
        match = re.match(r'\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|', line)
        if match:
            field = match.group(1).lower().replace(' ', '_')
            value = match.group(2).strip()
            
            field_mapping = {
                'brand_name': 'brand_name',
                'local_name': 'local_name',
                'industry': 'industry',
                'location': 'location',
                'primary_color': 'primary_color',
                'secondary_color': 'secondary_color',
                'target_audience': 'target_audience',
                'key_offerings': 'key_offerings',
                'contact_info': 'contact_info'
            }
            
            if field in field_mapping:
                # Clean up value
                clean_value = re.sub(r'<!--.*?-->', '', value).strip()
                clean_value = clean_value.replace('`', '').strip()
                client_data[field_mapping[field]] = clean_value
    
    # Extract JSON block
    json_match = re.search(r'```json\s*(.+?)\s*```', body, re.DOTALL)
    if json_match:
        try:
            json_data = json.loads(json_match.group(1))
            
            # Handle logo
            logo_base64 = json_data.get('logo_base64')
            if logo_base64 and len(str(logo_base64)) > 100:
                print(f"   📸 Found base64 logo ({len(str(logo_base64))} chars)")
                saved_path = save_base64_logo(logo_base64, client_data.get('brand_name', 'unknown'))
                if saved_path:
                    client_data['logo_path'] = saved_path
            
            # Merge other fields
            for key, value in json_data.items():
                if key not in ['logo_base64'] and key not in client_data:
                    client_data[key] = value
                    
        except json.JSONDecodeError as e:
            print(f"   ⚠️ JSON parse error: {e}")
    
    # Defaults
    client_data.setdefault('language', 'Persian')
    client_data.setdefault('location', 'Kabul, Afghanistan')
    client_data.setdefault('platforms', ['instagram_feed', 'instagram_story'])
    client_data.setdefault('signup_date', datetime.now().isoformat())
    
    return client_data


def validate_client_data(data):
    """Validate required fields."""
    required = ['brand_name', 'industry', 'primary_color']
    missing = [f for f in required if not data.get(f)]
    
    if missing:
        print(f"❌ Missing required fields: {missing}")
        return False
    
    return True


def add_to_clients_json(client_data):
    """Add client to database."""
    os.makedirs(DATA_DIR, exist_ok=True)
    clients_file = os.path.join(DATA_DIR, 'clients.json')
    
    # Load existing
    try:
        with open(clients_file, 'r', encoding='utf-8') as f:
            clients = json.load(f)
        if not isinstance(clients, list):
            clients = []
    except (FileNotFoundError, json.JSONDecodeError):
        clients = []
        print(f"   ℹ️ Creating new clients.json")
    
    # Check for duplicate
    exists = any(c.get('brand_name') == client_data['brand_name'] for c in clients if isinstance(c, dict))
    
    if exists:
        print(f"   📝 Updating existing client: {client_data['brand_name']}")
        # Remove old entry
        clients = [c for c in clients if c.get('brand_name') != client_data['brand_name']]
    
    clients.append(client_data)
    print(f"   ✅ Added client: {client_data['brand_name']}")
    
    # Save
    with open(clients_file, 'w', encoding='utf-8') as f:
        json.dump(clients, f, indent=2, ensure_ascii=False)
    
    return True


def fetch_issue(issue_number, token, owner, repo):
    """Fetch issue from GitHub API."""
    if not token:
        print("❌ No GitHub token")
        return None
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    url = f'https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}'
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
        print(f"❌ API error: {response.status_code}")
        return None
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None


def main():
    # Get environment variables
    issue_number = os.getenv('ISSUE_NUMBER')
    token = os.getenv('GITHUB_TOKEN')
    owner = os.getenv('REPO_OWNER') or os.getenv('GITHUB_REPOSITORY_OWNER')
    repo = os.getenv('REPO_NAME') or os.getenv('GITHUB_REPOSITORY', '').split('/')[-1]
    
    print(f"🔍 Configuration:")
    print(f"   Issue: #{issue_number}")
    print(f"   Repo: {owner}/{repo}")
    print(f"   Token: {'✅' if token else '❌'}")
    
    if not issue_number or not token:
        print("❌ Missing required variables")
        sys.exit(1)
    
    # Fetch issue
    issue = fetch_issue(issue_number, token, owner, repo)
    if not issue:
        sys.exit(1)
    
    print(f"\n📋 Issue: {issue.get('title')}")
    
    # Parse
    body = issue.get('body', '')
    client_data = parse_issue_body(body)
    
    print(f"\n📊 Parsed: {json.dumps(client_data, indent=2, ensure_ascii=False)}")
    
    # Validate
    if not validate_client_data(client_data):
        sys.exit(1)
    
    # Save
    if add_to_clients_json(client_data):
        # Set output for GitHub Actions
        github_output = os.getenv('GITHUB_OUTPUT')
        if github_output:
            with open(github_output, 'a') as f:
                f.write(f"updated=true\n")
                f.write(f"brand_name={client_data['brand_name']}\n")
        print("\n🎉 Success!")
        return True
    
    sys.exit(1)


if __name__ == '__main__':
    main()
