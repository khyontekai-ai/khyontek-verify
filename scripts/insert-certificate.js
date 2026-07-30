// scripts/insert-certificate.js
// Run locally to add certificates to MongoDB before issuing them
// Usage: node scripts/insert-certificate.js
//
// Copy .env.local with MONGODB_URI, DB_NAME, EMAIL_SALT before running

import { MongoClient } from 'mongodb';
import crypto from 'crypto';
import dotenv from 'dotenv';
dotenv.config({ path: '.env.local' });

const MONGODB_URI = process.env.MONGODB_URI;
const DB_NAME     = process.env.DB_NAME || 'khyontek_certs';
const EMAIL_SALT  = process.env.EMAIL_SALT;

function hashEmail(email) {
  return crypto
    .createHmac('sha256', EMAIL_SALT)
    .update(email.trim().toLowerCase())
    .digest('hex');
}

// ── EDIT THIS BLOCK FOR EACH CERTIFICATE ──
const certificate = {
  cert_id:        'KAI-SRIP-250001',
  recipient_name: 'Full Name Here',
  email:          'student@email.com',        // plain email — stored as hash only
  programme:      'Summer Research Immersion Programme',
  cohort:         'Cohort 01',
  track:          'Biological Intelligence Research',
  tier:           'Research Contribution',    // 'Research Contribution' | 'Completion'
  duration:       '45 Days',
  issue_date:     '2025-08-15',               // ISO date string
  issued_by:      ['NJK, Co-Founder & CSO', 'Dr. Pritam Deka, Co-Founder & CEO'],
  status:         'valid',                    // 'valid' | 'revoked'
  created_at:     new Date(),
};
// ── END EDIT BLOCK ──

async function insert() {
  const client = new MongoClient(MONGODB_URI);
  try {
    await client.connect();
    const db   = client.db(DB_NAME);
    const coll = db.collection('certificates');

    // Check for duplicate cert_id
    const existing = await coll.findOne({ cert_id: certificate.cert_id });
    if (existing) {
      console.error('ERROR: Certificate ID already exists:', certificate.cert_id);
      process.exit(1);
    }

    // Hash email — never store plain email
    const doc = {
      ...certificate,
      email_hash: hashEmail(certificate.email),
    };
    delete doc.email; // remove plain email before insert

    await coll.insertOne(doc);
    console.log('Certificate inserted successfully:', doc.cert_id);
    console.log('Recipient:', doc.recipient_name);
    console.log('Tier:', doc.tier);
  } catch (err) {
    console.error('Insert failed:', err.message);
  } finally {
    await client.close();
  }
}

insert();
