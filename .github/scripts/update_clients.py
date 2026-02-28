#!/usr/bin/env python3
"""
Parse GitHub Issue from frontend form submission and add client to clients.json.
This is the BRIDGE between frontend (maseer_portal) and backend (maseer_automation).
"""

import json
import os
import re
import sys
import requests


def parse_issue_body(body):
    """
    Extract client data from GitHub issue body created by frontend form.
    The frontend creates issues with a specific table format.
    """
    client_data = {}
    
    if not body:
        print("Error: Empty issue body")
        return client_data
    
    lines = body.split('\n')
    
    for line in lines:
        # Match table rows: | **Field** | Value |
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
                'logo_url': 'logo_path',  # Frontend sends 'Logo URL', maps to 'logo_path'
                'target_audience': 'target_audience',
                'key_offerings': 'key_offerings',
                'contact_info': 'contact_info'
            }
            
            if field in field_mapping:
                # Clean up the value (remove HTML comments if any)
                clean_value = re.sub(r'<!--.*?-->', '', value).strip()
                client_data[field_mapping[field]] = clean_value
    
    # Try to extract from JSON block if present (fallback)
    json_match = re.search(r'```json\s*(.+?)\s*```', body, re.DOTALL)
    if json_match:
        try:
            json_data = json.loads(json_match.group(1))
            # Merge, but table data takes precedence
            for key, value in json_data.items():
                if key not in client_data or not client_data[key]:
                    client_data[key] = value
        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse JSON block: {e}")
    
    # Set defaults for new clients
    client_data.setdefault('language', 'Persian')
    client_data.setdefault('location', 'Kabul, Afghanistan')
    client_data.setdefault('platforms', ['instagram_feed', 'instagram_story', 'instagram_reel', 'facebook_feed'])
    client_data.setdefault('content_tone', 'professional')
    client_data.setdefault('preferred_motion', 'zoom_in')
    client_data.setdefault('special_notes', 'New client from frontend signup')
    client_data.setdefault('signup_date', datetime.now().isoformat() if 'datetime' in dir() else None)
    
    return client_data


def validate_client_data(data):
    """Validate required fields for new client."""
    required = ['brand_name', 'industry', 'primary_color', 'logo_path']
    missing = [f for f in required if not data.get(f)]
    
    if missing:
        print(f"Error: Missing required fields: {missing}")
        return False
    
    # Validate color format
    primary = data.get('primary_color', '')
    if not re.match(r'^#[0-9A-Fa-f]{6}$', primary):
        print(f"Warning: Primary color {primary} may not be valid hex")
    
    return True


def add_to_clients_json(client_data):
    """
    Add new client to clients.json.
    If client already exists (same brand_name), update it (new signup = new intent).
    """
    clients_file = 'data/clients.json'
    
    # Load existing clients
    try:
        with open(clients_file, 'r', encoding='utf-8') as f:
            clients = json.load(f)
    except FileNotFoundError:
        print(f"Creating new {clients_file}")
        clients = []
    except json.JSONDecodeError as e:
        print(f"Error: Could not parse {clients_file}: {e}")
        sys.exit(1)
    
    # Filter out any non-dict items (like comments)
    clients = [c for c in clients if isinstance(c, dict)]
    
    # Check for existing client (same brand_name)
    existing_idx = None
    for idx, client in enumerate(clients):
        if isinstance(client, dict) and client.get('brand_name') == client_data.get('brand_name'):
            existing_idx = idx
            break
    
    if existing_idx is not None:
        print(f"Client '{client_data['brand_name']}' already exists. Updating with new signup data...")
        # Preserve some fields from old entry if not in new
        old_client = clients[existing_idx]
        client_data['signup_history'] = old_client.get('signup_history', [])
        client_data['signup_history'].append({
            'date': old_client.get('signup_date'),
            'data': {k: v for k, v in old_client.items() if k not in ['signup_history']}
        })
        # Replace with new data
        clients[existing_idx] = client_data
    else:
        # Add new client
        clients.append(client_data)
        print(f"Success: Added NEW client: {client_data['brand_name']}")
    
    # Save back
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
    
    print(f"Fetching issue from: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403:
            print("Error 403: Authentication failed or rate limited")
            print("Response:", response.text)
            return None
        elif response.status_code == 404:
            print(f"Error 404: Issue #{issue_number} not found")
            return None
        else:
            print(f"Error: HTTP {response.status_code}")
            print("Response:", response.text)
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Error: Request failed: {e}")
        return None


def main():
    # Get environment variables
    issue_number = os.getenv('ISSUE_NUMBER')
    github_token = os.getenv('GITHUB_TOKEN')
    repo_owner = os.getenv('REPO_OWNER') or os.getenv('GITHUB_REPOSITORY_OWNER')
    repo_name = os.getenv('REPO_NAME') or os.getenv('GITHUB_REPOSITORY', '').split('/')[-1]
    
    print(f"Environment:")
    print(f"  Issue Number: {issue_number}")
    print(f"  Token present: {'Yes (length: ' + str(len(github_token)) + ')' if github_token else 'No'}")
    print(f"  Repo Owner: {repo_owner}")
    print(f"  Repo Name: {repo_name}")
    
    if not issue_number:
        print("Error: ISSUE_NUMBER not set")
        sys.exit(1)
    
    if not github_token:
        print("Error: GITHUB_TOKEN not set")
        sys.exit(1)
    
    # Fetch issue from API
    issue_data = fetch_issue_from_api(issue_number, github_token, repo_owner, repo_name)
    
    if not issue_data:
        print("Error: Could not fetch issue data")
        sys.exit(1)
    
    body = issue_data.get('body', '')
    print(f"\nIssue title: {issue_data.get('title', 'Unknown')}")
    print(f"Issue body length: {len(body)} characters")
    
    # Parse client data from frontend form submission
    client_data = parse_issue_body(body)
    
    if not validate_client_data(client_data):
        print("Error: Client data validation failed")
        sys.exit(1)
    
    # Add to clients.json
    if add_to_clients_json(client_data):
        # Set output for GitHub Actions
        github_output = os.environ.get('GITHUB_OUTPUT')
        if github_output:
            with open(github_output, 'a') as f:
                f.write("updated=true\n")
                f.write(f"brand_name={client_data['brand_name']}\n")
        print("\n✅ Success: New client added from frontend signup!")
        print(f"   Brand: {client_data['brand_name']}")
        print(f"   Industry: {client_data['industry']}")
        print(f"   Video will be generated in next scheduled run (within 6 hours)")
    else:
        print("Error: Failed to add new client")
        if github_output:
            with open(github_output, 'a') as f:
                f.write("updated=false\n")
        sys.exit(1)


if __name__ == '__main__':
    from datetime import datetime  # Import here to avoid issues if not needed
    main()
