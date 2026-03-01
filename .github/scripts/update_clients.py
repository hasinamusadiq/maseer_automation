#!/usr/bin/env python3
"""
Parse GitHub Issue and add client with 1224×1536 Meta specs.
Handles both base64 in body and image attachments in comments.
"""

import json
import os
import re
import sys
import requests
import base64
from datetime import datetime


META_SPECS = {
    "width": 1224,
    "height": 1536,
    "aspect_ratio": "4:5",
    "platforms": ["instagram_feed", "instagram_story", "facebook_feed"],
    "optimal_for": "Meta advertising with maximum screen real estate"
}


def save_base64_logo(base64_data, brand_name):
    """Save base64 logo."""
    try:
        if ',' in base64_data:
            _, base64_data = base64_data.split(',', 1)
        
        logo_bytes = base64.b64decode(base64_data)
        safe_name = re.sub(r'[^\w\s-]', '', brand_name).strip().replace(' ', '_')
        logo_path = f'logos/{safe_name}_logo.png'
        
        os.makedirs('logos', exist_ok=True)
        
        with open(logo_path, 'wb') as f:
            f.write(logo_bytes)
        
        print(f"   ✅ Logo: {logo_path} ({len(logo_bytes)} bytes)")
        return logo_path
        
    except Exception as e:
        print(f"   ⚠️ Logo error: {e}")
        return None


def download_logo_from_url(url, brand_name, token):
    """Download logo from GitHub issue attachment."""
    try:
        headers = {'Authorization': f'Bearer {token}'} if token else {}
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            safe_name = re.sub(r'[^\w\s-]', '', brand_name).strip().replace(' ', '_')
            logo_path = f'logos/{safe_name}_logo.png'
            
            os.makedirs('logos', exist_ok=True)
            
            with open(logo_path, 'wb') as f:
                f.write(response.content)
            
            print(f"   ✅ Logo downloaded: {logo_path} ({len(response.content)} bytes)")
            return logo_path
            
    except Exception as e:
        print(f"   ⚠️ Logo download error: {e}")
    
    return None


def get_issue_comments(issue_number, token, owner, repo):
    """Fetch comments from issue to find logo attachments."""
    url = f'https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments'
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"   ⚠️ Could not fetch comments: {e}")
    
    return []


def find_logo_in_comments(comments, brand_name, token):
    """Search comments for image attachments."""
    for comment in comments:
        body = comment.get('body', '')
        
        # Look for GitHub image markdown ![alt](url)
        img_match = re.search(r'!\[.*?\]\((https://.*?\.(?:png|jpg|jpeg|gif))\)', body, re.IGNORECASE)
        if img_match:
            url = img_match.group(1)
            # Convert to raw URL if needed
            if 'github.com' in url and '/assets/' in url:
                return download_logo_from_url(url, brand_name, token)
        
        # Look for direct URLs
        url_match = re.search(r'(https://.*?\.(?:png|jpg|jpeg|gif))', body, re.IGNORECASE)
        if url_match:
            return download_logo_from_url(url_match.group(1), brand_name, token)
    
    return None


def parse_issue(body):
    """Extract client data from issue."""
    client = {}
    
    if not body:
        return client
    
    # Parse markdown tables
    for line in body.split('\n'):
        match = re.match(r'\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|', line)
        if match:
            field = match.group(1).lower().replace(' ', '_')
            value = re.sub(r'<!--.*?-->', '', match.group(2)).strip()
            
            mapping = {
                'brand_name': 'brand_name',
                'local_name': 'local_name',
                'industry': 'industry',
                'location': 'location',
                'primary_color': 'primary_color',
                'secondary_color': 'secondary_color',
                'target_audience': 'target_audience',
                'key_offerings': 'key_offerings',
                'unique_value': 'unique_value',
                'contact': 'contact_info'
            }
            
            if field in mapping and value and value != '-':
                client[mapping[field]] = value
    
    # Parse JSON block
    json_match = re.search(r'```json\s*(.+?)\s*```', body, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            
            # Handle logo base64
            logo_b64 = data.get('logo_base64')
            if logo_b64 and len(logo_b64) > 100:
                saved = save_base64_logo(logo_b64, client.get('brand_name', 'unknown'))
                if saved:
                    client['logo_path'] = saved
            
            # Check for sample request
            if data.get('request_sample'):
                client['request_sample'] = True
            
            # Merge other fields
            for k, v in data.items():
                if k not in ['logo_base64', 'logo_url', 'request_sample']:
                    if k not in client:
                        client[k] = v
                        
        except json.JSONDecodeError as e:
            print(f"   ⚠️ JSON parse error: {e}")
    
    # Add Meta specs
    client['meta_specs'] = META_SPECS
    client['signup_date'] = datetime.now().isoformat()
    client['campaigns_completed'] = []
    client['sample_generated'] = False
    client['total_videos'] = 0
    
    return client


def validate(client):
    """Validate required fields."""
    required = ['brand_name', 'industry', 'primary_color']
    missing = [f for f in required if not client.get(f)]
    
    if missing:
        print(f"❌ Missing: {missing}")
        return False
    
    # Validate hex
    color = client.get('primary_color', '')
    if not re.match(r'^#[0-9A-Fa-f]{6}$', color):
        if not color.startswith('#'):
            client['primary_color'] = f"#{color}"
    
    return True


def save_client(client):
    """Save to clients.json."""
    path = 'data/clients.json'
    
    try:
        with open(path, 'r') as f:
            clients = json.load(f)
    except:
        clients = []
        os.makedirs('data', exist_ok=True)
    
    # Update existing or append
    existing = None
    for i, c in enumerate(clients):
        if c.get('brand_name', '').lower() == client['brand_name'].lower():
            existing = i
            break
    
    if existing is not None:
        # Preserve history
        client['signup_history'] = clients[existing].get('signup_history', [])
        client['signup_history'].append({
            'date': clients[existing].get('signup_date'),
            'data': {k: v for k, v in clients[existing].items() if k != 'signup_history'}
        })
        clients[existing] = client
        print(f"   🔄 Updated: {client['brand_name']}")
    else:
        clients.append(client)
        print(f"   ✨ New: {client['brand_name']}")
    
    with open(path, 'w') as f:
        json.dump(clients, f, indent=2, ensure_ascii=False)
    
    return True


def fetch_issue(number, token, owner, repo):
    """Fetch from GitHub API."""
    url = f'https://api.github.com/repos/{owner}/{repo}/issues/{number}'
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=30)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        print(f"❌ API error: {e}")
        return None


def main():
    issue_num = os.getenv('ISSUE_NUMBER')
    token = os.getenv('GITHUB_TOKEN') or os.getenv('PAT_TOKEN')
    owner = os.getenv('REPO_OWNER') or os.getenv('GITHUB_REPOSITORY_OWNER')
    repo = os.getenv('REPO_NAME') or os.getenv('GITHUB_REPOSITORY', '').split('/')[-1]
    
    if not issue_num or not token:
        print("❌ Missing ISSUE_NUMBER or token")
        sys.exit(1)
    
    print(f"Processing Issue #{issue_num} in {owner}/{repo}")
    
    issue = fetch_issue(issue_num, token, owner, repo)
    if not issue:
        sys.exit(1)
    
    print(f"Title: {issue.get('title', 'Unknown')}")
    
    client = parse_issue(issue.get('body', ''))
    
    # If no logo in body, check comments
    if not client.get('logo_path'):
        print("   🔍 Checking comments for logo...")
        comments = get_issue_comments(issue_num, token, owner, repo)
        logo_path = find_logo_in_comments(comments, client.get('brand_name', 'unknown'), token)
        if logo_path:
            client['logo_path'] = logo_path
    
    if not validate(client):
        # Output failure
        output = os.environ.get('GITHUB_OUTPUT')
        if output:
            with open(output, 'a') as f:
                f.write("updated=false\n")
        sys.exit(1)
    
    if save_client(client):
        # Output success
        output = os.environ.get('GITHUB_OUTPUT')
        if output:
            with open(output, 'a') as f:
                f.write("updated=true\n")
                f.write(f"brand_name={client['brand_name']}\n")
                f.write(f"request_sample={'true' if client.get('request_sample') else 'false'}\n")
        print(f"\n✅ {client['brand_name']} ready for 1224×1536 campaigns")
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
