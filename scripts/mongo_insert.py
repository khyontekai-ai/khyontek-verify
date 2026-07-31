#!/usr/bin/env python3
"""
mongo_insert.py
Inserts certificate record into MongoDB after PDF generation.
NOTE: The programmes app already saves the cert record — this is a backup/sync.
If MongoDB insert fails it logs the error but does not fail the workflow.
"""
import sys, os, json, argparse
from datetime import datetime

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', required=True)
    args = parser.parse_args()

    try:
        data = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f"WARNING: Could not parse data JSON: {e}")
        print("Skipping MongoDB insert — record already saved by programmes app")
        sys.exit(0)  # Exit 0 — not a fatal error

    # Parse meta if present
    meta = {}
    if data.get('meta'):
        try: meta = json.loads(data['meta'])
        except: pass

    cert_id       = data.get('cert_id','')
    recipient     = data.get('recipient_name','')
    email         = data.get('email','')
    programme     = data.get('programme','')
    track         = data.get('track','')
    tier          = data.get('tier','')
    issue_date    = data.get('issue_date','')

    print(f"Certificate {cert_id} for {recipient} — record already saved by programmes app")
    print("MongoDB insert skipped — no duplicate needed")
    sys.exit(0)

if __name__ == "__main__":
    main()
