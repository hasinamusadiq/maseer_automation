#!/usr/bin/env python3
"""
Ariana Coach - Parse GitHub Issue from frontend form submission.
Handles base64-encoded logo uploads from the new frontend.
"""

import json
import os
import re
import sys
import requests
import base64
from datetime import datetime


def save_base64_logo(base64_data, brand_name):
    """
    Save base64-encoded logo to logos/ directory.
    Returns the local file path or None if failed.
    """
    try:
        # Clean up base64 string
        if ',' in base64_data:
            header, base64_data = base64_data.split(',', 1)
        
        # Decode base64
        logo_bytes = base64.b64decode(base64_data)
        
        # Create safe filename
        safe_name = brand_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        logo_path = f'logos/{safe_name}_logo.png'
        
        # Ensure logos directory exists
        os.makedirs('logos', exist_ok=True)
        
        # Save file
        with open(logo_path, 'wb') as f:
            f.write(logo_bytes)
        
        print(f"   ✅ Logo saved: {logo_path} ({len(logo_bytes)} bytes)")
        return logo_path
        
    except Exception as e:
        print(f"   ⚠️ Error saving base64 logo: {e}")
        return None


def parse_issue_body(body):
    """
    Extract client data from GitHub issue body.
    Handles base64 logo uploads from Ariana Coach frontend.
    """
    client_data = {}
    
    if not body:
        print("Error: Empty issue body")
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
                clean_value = re.sub(r'<!--.*?-->', '', value).strip()
                client_data[field_mapping[field]] = clean_value
    
    # Extract JSON block with logo data
    json_match = re.search(r'```json\s*(.+?)\s*```', body, re.DOTALL)
    if json_match:
        try:
            json_data = json.loads(json_match.group(1))
            
            # Handle logo base64
            logo_base64 = json_data.get('logo_base64')
            logo_url = json_data.get('logo_url') or json_data.get('logo_path')
            
            if logo_base64 and len(logo_base64) > 100:
                print(f"   📸 Found base64 logo ({len(logo_base64)} chars)")
                brand_name = client_data.get('brand_name', 'unknown')
                saved_path = save_base64_logo(logo_base64, brand_name)
                if saved_path:
                    client_data['logo_path'] = saved_path
            elif logo_url and logo_url.startswith('http'):
                client_data['logo_path'] = logo_url
            else:
                print("   ⚠️ No logo found")
                client_data['logo_path'] = None
            
            # Merge other fields
            for key, value in json_data.items():
                if key not in ['logo_base64', 'logo_url', 'logo_path'] and key not in client_data:
                    client_data[key] = value
                    
        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse JSON block: {e}")
    
    # Set defaults
    client_data.setdefault('language', 'Persian')
    client_data.setdefault('location', 'Kabul, Afghanistan')
    client_data.setdefault('platforms', ['instagram_feed', 'instagram_story', 'instagram_reel', 'facebook_feed'])
    client_data.setdefault('content_tone', 'professional')
    client_data.setdefault('preferred_motion', 'zoom_in')
    client_data.setdefault('signup_date', datetime.now().isoformat())
    
    return client_data


def validate_client_data(data):
    """Validate required fields."""
    required = ['brand_name', 'industry', 'primary_color']
    missing = [f for f in required if not data.get(f)]
    
    if missing:
        print(f"Error: Missing required fields: {missing}")
        return False
    
    return True


def add_to_clients_json(client_data):
    """Add or update client in clients.json."""
    clients_file = 'data/clients.json'
    
    try:
        with open(clients_file, 'r', encoding='utf-8') as f:
            clients = json.load(f)
    except FileNotFoundError:
        clients = []
    except json.JSONDecodeError as e:
        print(f"Error: Could not parse {clients_file}: {e}")
        sys.exit(1)
    
    clients = [c for c in clients if isinstance(c, dict)]
    
    # Check for existing client
    existing_idx = None
    for idx, client in enumerate(clients):
        if isinstance(client, dict) and client.get('brand_name') == client_data.get('brand_name'):
            existing_idx = idx
            break
    
    if existing_idx is not None:
        print(f"Client '{client_data['brand_name']}' already exists. Updating...")
        old_client = clients[existing_idx]
        client_data['signup_history'] = old_client.get('signup_history', [])
        client_data['signup_history'].append({
            'date': old_client.get('signup_date'),
            'data': {k: v for k, v in old_client.items() if k not in ['signup_history']}
        })
        clients[existing_idx] = client_data
    else:
        clients.append(client_data)
        print(f"Success: Added NEW client: {client_data['brand_name']}")
    
    with open(clients_file, 'w', encoding='utf-8') as f:
        json.dump(clients, f, indent=2, ensure_ascii=False)
    
    return True


def fetch_issue_from_api(issue_number, token, owner, repo):
    """Fetch issue data from GitHub API."""
    if not token:
        print("Error: No GitHub token provided")
        return None
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3+json',
        'X-GitHub-Api-Version': '2022-11-28'
    }
    
    url = f'https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}'
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: HTTP {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error: Request failed: {e}")
        return None


def main():
    issue_number = os.getenv('ISSUE_NUMBER')
    github_token = os.getenv('GITHUB_TOKEN')
    repo_owner = os.getenv('REPO_OWNER') or os.getenv('GITHUB_REPOSITORY_OWNER')
    repo_name = os.getenv('REPO_NAME') or os.getenv('GITHUB_REPOSITORY', '').split('/')[-1]
    
    if not issue_number or not github_token:
        print("Error: Required environment variables not set")
        sys.exit(1)
    
    issue_data = fetch_issue_from_api(issue_number, github_token, repo_owner, repo_name)
    
    if not issue_data:
        sys.exit(1)
    
    body = issue_data.get('body', '')
    print(f"\nProcessing: {issue_data.get('title', 'Unknown')}")
    
    client_data = parse_issue_body(body)
    
    if not validate_client_data(client_data):
        sys.exit(1)
    
    if add_to_clients_json(client_data):
        github_output = os.environ.get('GITHUB_OUTPUT')
        if github_output:
            with open(github_output, 'a') as f:
                f.write("updated=true\n")
                f.write(f"brand_name={client_data['brand_name']}\n")
        print("\n✅ Success: Client added from Ariana Coach!")
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
