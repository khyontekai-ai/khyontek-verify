#!/usr/bin/env python3
"""
build_admin.py — Injects GitHub secrets into admin.html
Run by GitHub Actions during Pages build.
Replaces %%PLACEHOLDER%% tokens with actual values.
"""
import os
import sys

def main():
    admin_id        = os.environ.get('ADMIN_ID', 'adcert')
    admin_pass      = os.environ.get('ADMIN_PASSWORD', '')
    gh_dispatch_url = os.environ.get('GH_DISPATCH_URL', '')
    gh_token        = os.environ.get('GH_PAGES_TOKEN', '')

    with open('admin.html', 'r') as f:
        content = f.read()

    content = content.replace('%%ADMIN_ID%%',       admin_id)
    content = content.replace('%%ADMIN_PASS%%',     admin_pass)
    content = content.replace('%%GH_DISPATCH_URL%%',gh_dispatch_url)
    content = content.replace('%%GH_TOKEN%%',       gh_token)

    os.makedirs('dist', exist_ok=True)
    with open('dist/index.html', 'w') as f:
        f.write(content)

    print("✅ Admin page built successfully → dist/index.html")

if __name__ == '__main__':
    main()
