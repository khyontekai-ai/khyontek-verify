#!/usr/bin/env python3
"""
mongo_insert.py — Insert certificate record into MongoDB
Features: collaborator support, payment tracking, duplicate check
"""
import sys, json, os, hashlib, hmac
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

def hash_email(email, salt):
    return hmac.new(
        salt.encode('utf-8'),
        email.strip().lower().encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def main():
    data    = json.loads(sys.argv[1])
    uri     = os.environ['MONGODB_URI']
    db_name = os.environ.get('DB_NAME', 'khyontek_certs')
    salt    = os.environ['EMAIL_SALT']

    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    db     = client[db_name]
    coll   = db['certificates']

    cert_id    = data['cert_id'].strip().upper()
    email_hash = hash_email(data['email'], salt)

    # ── Duplicate check: same email + programme ──
    existing = coll.find_one({
        'email_hash': email_hash,
        'programme':  data.get('programme','')
    })
    if existing:
        print(f"WARNING: Student already has a certificate for this programme: {existing['cert_id']}")
        print(f"Proceeding with new cert_id: {cert_id}")

    # Build collaborators list
    collabs = []
    for i in range(1,4):
        name      = data.get(f'collab_{i}_name','').strip()
        logo      = data.get(f'collab_{i}_logo','').strip()
        sig_name  = data.get(f'collab_{i}_sig_name','').strip()
        sig_title = data.get(f'collab_{i}_sig_title','').strip()
        if name:
            collabs.append({
                'name':      name,
                'logo':      logo,
                'sig_name':  sig_name,
                'sig_title': sig_title,
            })

    doc = {
        'cert_id':             cert_id,
        'recipient_name':      data['recipient_name'].strip(),
        'email_hash':          email_hash,
        'programme':           data.get('programme',''),
        'cohort':              data.get('cohort',''),
        'track':               data.get('track',''),
        'tier':                data.get('tier',''),
        'duration':            data.get('duration',''),
        'start_date':          data.get('start_date',''),
        'issue_date':          data.get('issue_date',''),
        'collaborators':       collabs,
        'show_njk_signature':  data.get('show_njk_signature', False),
        'issued_by':           ['Khyontek AI Private Limited'],
        'payment':             data.get('payment', {}),
        'status':              'valid',
        'created_at':          datetime.utcnow(),
    }

    try:
        coll.insert_one(doc)
        print(f"Inserted: {cert_id} — {doc['recipient_name']}")
        if collabs:
            print(f"Collaborators: {[c['name'] for c in collabs]}")
        if data.get('show_njk_signature'):
            print("NJK signature: enabled")
    except DuplicateKeyError:
        print(f"Already exists: {cert_id} — skipped")
    finally:
        client.close()

if __name__ == '__main__':
    main()
