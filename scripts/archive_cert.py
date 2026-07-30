#!/usr/bin/env python3
"""
archive_cert.py — Save generated certificate PDF to the
khyontek-certificates private GitHub repository.
Called by GitHub Actions after PDF generation.
"""
import sys
import json
import os
import argparse
import base64
import requests
from datetime import datetime

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data',  required=True)
    parser.add_argument('--pdf',   required=True)
    parser.add_argument('--token', required=True)
    parser.add_argument('--repo',  required=True,
                        help='org/repo-name e.g. khyontekAI/khyontek-certificates')
    args = parser.parse_args()

    data    = json.loads(args.data)
    cert_id = data['cert_id']
    name    = data['recipient_name'].replace(' ', '_')

    # Determine folder path: certificates/YYYY/PROG/
    try:
        year = datetime.strptime(data.get('issue_date',''), "%Y-%m-%d").year
    except:
        year = datetime.utcnow().year

    prog_code = cert_id.split('-')[1] if '-' in cert_id else 'MISC'
    folder    = f"certificates/{year}/{prog_code}"
    filename  = f"{cert_id}_{name}.pdf"
    file_path = f"{folder}/{filename}"

    # Read PDF as base64
    with open(args.pdf, 'rb') as f:
        content_b64 = base64.b64encode(f.read()).decode('utf-8')

    # GitHub API — create file
    url = f"https://api.github.com/repos/{args.repo}/contents/{file_path}"
    headers = {
        "Authorization": f"token {args.token}",
        "Accept":        "application/vnd.github.v3+json",
        "Content-Type":  "application/json",
    }

    payload = {
        "message": f"Add certificate {cert_id} — {data['recipient_name']}",
        "content": content_b64,
        "branch":  "main",
    }

    resp = requests.put(url, headers=headers, json=payload, timeout=30)

    if resp.status_code in (200, 201):
        print(f"✅ Certificate archived: {file_path}")
    elif resp.status_code == 422:
        print(f"⚠️  File already exists in archive: {file_path}")
    else:
        print(f"❌ Archive failed: {resp.status_code} — {resp.text}")
        sys.exit(1)

if __name__ == '__main__':
    main()
