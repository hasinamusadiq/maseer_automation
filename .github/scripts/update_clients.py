#!/usr/bin/env python3
"""
Parse GitHub Issue and add client to clients.json
"""

import json
import os
import re
import sys
import requests


def parse_issue_body(body):
    """Extract client data from GitHub issue body."""
    client_data = {}
    
    lines = body.split('\n')
    
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
                'logo_url': 'logo_path',
                'target_audience': 'target_audience',
                'key_offerings': 'key_offerings',
                'contact': 'contact_info'
            }
            
            if field in field_mapping:
                client_data[field_mapping[field]] = value
    
    json_match = re.search(r'```json\s*(.+?)\s*```', body, re.DOTALL)
    if json_match:
        try:
            json_data = json.loads(json_match.group(1))
            client_data.update(json_data)
        except json.JSONDecodeError:
            pass
    
    client_data.setdefault('language', 'Persian')
    client_data.setdefault('location', 'Kabul, Afghanistan')
    
    return client_data


def validate_client_data(data):
    """Validate required fields."""
    required = ['brand_name', 'industry', 'primary_color', 'logo_path']
    missing = [f for f in required if not data.get(f)]
    
    if missing:
        print(f"Error: Missing required fields: {missing}")
        return False
    
    return True


def add_to_clients_json(client_data):
    """Add new client to clients.json."""
    clients_file = 'data/clients.json'
    
    try:
        with open(clients_file, 'r', encoding='utf-8') as f:
            clients = json.load(f)
    except FileNotFoundError:
        clients = []
    except json.JSONDecodeError:
        print("Error: Could not parse clients.json")
        sys.exit(1)
    
    existing = [c for c in clients if c.get('brand_name') == client_data.get('brand_name')]
    if existing:
        print(f"Warning: Client '{client_data['brand_name']}' already exists. Updating...")
        clients = [c for c in clients if c.get('brand_name') != client_data.get('brand_name')]
    
    clients.append(client_data)
    
    with open(clients_file, 'w', encoding='utf-8') as f:
        json.dump(clients, f, indent=2, ensure_ascii=False)
    
    print(f"Success: Added client: {client_data['brand_name']}")
    return True


def main():
    issue_number = os.getenv('ISSUE_NUMBER')
    github_token = os.getenv('GITHUB_TOKEN')
    
    if not issue_number:
        print("Error: ISSUE_NUMBER not set")
        sys.exit(1)
    
    repo = os.getenv('GITHUB_REPOSITORY')
    
    if github_token and repo:
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        url = f'https://api.github.com/repos/{repo}/issues/{issue_number}'
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"Error: Failed to fetch issue: {response.status_code}")
            sys.exit(1)
        
        issue_data = response.json()
        body = issue_data.get('body', '')
    else:
        print("Error: No GitHub token or repo info")
        sys.exit(1)
    
    client_data = parse_issue_body(body)
    
    if not validate_client_data(client_data):
        sys.exit(1)
    
    if add_to_clients_json(client_data):
        print("::set-output name=updated::true")
    else:
        print("::set-output name=updated::false")
        sys.exit(1)


if __name__ == '__main__':
    main()
