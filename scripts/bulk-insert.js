// scripts/bulk-insert.js
// Bulk certificate insertion from CSV
// Usage: node scripts/bulk-insert.js students.csv

import { MongoClient } from 'mongodb';
import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, '..', '.env.local') });

// ── Config ──
const MONGODB_URI = process.env.MONGODB_URI;
const DB_NAME     = process.env.DB_NAME || 'khyontek_certs';
const EMAIL_SALT  = process.env.EMAIL_SALT;
const COLLECTION  = 'certificates';

// ── Validate env ──
if (!MONGODB_URI || !EMAIL_SALT) {
  console.error('\n❌  Missing environment variables.');
  console.error('    Make sure .env.local exists with MONGODB_URI, DB_NAME, and EMAIL_SALT.\n');
  process.exit(1);
}

// ── Hash email ──
function hashEmail(email) {
  return crypto
    .createHmac('sha256', EMAIL_SALT)
    .update(email.trim().toLowerCase())
    .digest('hex');
}

// ── Parse CSV (no external library needed) ──
function parseCSV(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const lines   = content.split('\n').map(l => l.trim()).filter(Boolean);

  if (lines.length < 2) {
    console.error('❌  CSV file is empty or has no data rows.\n');
    process.exit(1);
  }

  const headers = lines[0].split(',').map(h => h.trim());
  const required = [
    'cert_id', 'recipient_name', 'email', 'programme',
    'cohort', 'track', 'tier', 'duration', 'issue_date'
  ];

  // Validate headers
  const missing = required.filter(r => !headers.includes(r));
  if (missing.length > 0) {
    console.error(`❌  CSV missing required columns: ${missing.join(', ')}\n`);
    process.exit(1);
  }

  return lines.slice(1).map((line, i) => {
    // Handle commas inside quoted fields
    const values = [];
    let current  = '';
    let inQuotes = false;
    for (const char of line) {
      if (char === '"') { inQuotes = !inQuotes; continue; }
      if (char === ',' && !inQuotes) { values.push(current.trim()); current = ''; continue; }
      current += char;
    }
    values.push(current.trim());

    const row = {};
    headers.forEach((h, idx) => { row[h] = values[idx] || ''; });
    row._rowNumber = i + 2; // +2 for header row + 1-based index
    return row;
  });
}

// ── Validate a single row ──
function validateRow(row) {
  const errors = [];

  if (!row.cert_id)        errors.push('cert_id is empty');
  if (!row.recipient_name) errors.push('recipient_name is empty');
  if (!row.email || !row.email.includes('@')) errors.push('email is invalid');
  if (!row.programme)      errors.push('programme is empty');
  if (!row.cohort)         errors.push('cohort is empty');
  if (!row.track)          errors.push('track is empty');
  if (!['Research Contribution', 'Completion'].includes(row.tier))
    errors.push(`tier must be "Research Contribution" or "Completion" — got: "${row.tier}"`);
  if (!row.duration)       errors.push('duration is empty');
  if (!row.issue_date)     errors.push('issue_date is empty');

  // Cert ID format check
  if (row.cert_id && !/^KAI-[A-Z0-9]+-\d{6,8}$/.test(row.cert_id.trim().toUpperCase()))
    errors.push(`cert_id format invalid: "${row.cert_id}" — expected KAI-[PROG]-[YY][SERIAL]`);

  return errors;
}

// ── Main ──
async function main() {
  const csvPath = process.argv[2];

  if (!csvPath) {
    console.error('\n❌  No CSV file specified.');
    console.error('    Usage: node scripts/bulk-insert.js students.csv\n');
    process.exit(1);
  }

  if (!fs.existsSync(csvPath)) {
    console.error(`\n❌  File not found: ${csvPath}\n`);
    process.exit(1);
  }

  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('  Khyontek AI — Bulk Certificate Insert');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

  // Parse CSV
  const rows = parseCSV(csvPath);
  console.log(`📄  CSV loaded: ${rows.length} row(s) found\n`);

  // Validate all rows first — stop before touching DB if any row has errors
  const validationErrors = [];
  rows.forEach(row => {
    const errors = validateRow(row);
    if (errors.length > 0) {
      validationErrors.push({ row: row._rowNumber, cert_id: row.cert_id || '(empty)', errors });
    }
  });

  if (validationErrors.length > 0) {
    console.error('❌  Validation failed. Fix these errors before inserting:\n');
    validationErrors.forEach(e => {
      console.error(`    Row ${e.row} (${e.cert_id}):`);
      e.errors.forEach(err => console.error(`      - ${err}`));
    });
    console.error('\n    No records were inserted.\n');
    process.exit(1);
  }

  console.log('✅  All rows passed validation\n');

  // Check for duplicate cert_ids within the CSV itself
  const csvIds = rows.map(r => r.cert_id.trim().toUpperCase());
  const duplicatesInCSV = csvIds.filter((id, i) => csvIds.indexOf(id) !== i);
  if (duplicatesInCSV.length > 0) {
    console.error(`❌  Duplicate cert_ids found within the CSV: ${[...new Set(duplicatesInCSV)].join(', ')}`);
    console.error('    Fix duplicates before inserting.\n');
    process.exit(1);
  }

  // Connect to MongoDB
  let client;
  try {
    client = new MongoClient(MONGODB_URI, { connectTimeoutMS: 8000, serverSelectionTimeoutMS: 8000 });
    await client.connect();
    console.log('🔗  Connected to MongoDB Atlas\n');
  } catch (err) {
    console.error(`❌  Could not connect to MongoDB: ${err.message}\n`);
    process.exit(1);
  }

  const db   = client.db(DB_NAME);
  const coll = db.collection(COLLECTION);

  // Check for existing cert_ids in the database
  const existingDocs = await coll.find({ cert_id: { $in: csvIds } }, { projection: { cert_id: 1 } }).toArray();
  const existingIds  = new Set(existingDocs.map(d => d.cert_id));

  if (existingIds.size > 0) {
    console.warn(`⚠️   ${existingIds.size} cert_id(s) already exist in the database and will be skipped:`);
    [...existingIds].forEach(id => console.warn(`      - ${id}`));
    console.log('');
  }

  // Insert records
  let inserted = 0;
  let skipped  = 0;
  let failed   = 0;

  for (const row of rows) {
    const certId = row.cert_id.trim().toUpperCase();

    // Skip duplicates
    if (existingIds.has(certId)) {
      console.log(`  ⏭   Skipped (already exists): ${certId}`);
      skipped++;
      continue;
    }

    // Build document — hash email, never store plain email
    const doc = {
      cert_id:        certId,
      recipient_name: row.recipient_name.trim(),
      email_hash:     hashEmail(row.email),
      programme:      row.programme.trim(),
      cohort:         row.cohort.trim(),
      track:          row.track.trim(),
      tier:           row.tier.trim(),
      duration:       row.duration.trim(),
      issue_date:     row.issue_date.trim(),
      issued_by:      [
        'NJK, Co-Founder & CSO',
        'Dr. Pritam Deka, Co-Founder & CEO'
      ],
      status:     'valid',
      created_at: new Date(),
    };

    try {
      await coll.insertOne(doc);
      console.log(`  ✅  Inserted: ${certId} — ${row.recipient_name.trim()}`);
      inserted++;
    } catch (err) {
      console.error(`  ❌  Failed:   ${certId} — ${err.message}`);
      failed++;
    }
  }

  await client.close();

  // Summary
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('  Summary');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(`  Total rows in CSV : ${rows.length}`);
  console.log(`  ✅  Inserted       : ${inserted}`);
  console.log(`  ⏭   Skipped        : ${skipped}`);
  console.log(`  ❌  Failed         : ${failed}`);
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

  if (failed > 0) {
    console.error('  Some records failed. Check errors above and retry.\n');
    process.exit(1);
  }

  if (inserted === 0 && skipped > 0) {
    console.warn('  All records were already in the database. Nothing new inserted.\n');
  }

  if (inserted > 0) {
    console.log('  All certificates inserted successfully.');
    console.log('  Verify at: https://verify.khyontekai.com\n');
  }
}

main();
