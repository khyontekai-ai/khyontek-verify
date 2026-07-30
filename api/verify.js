// api/verify.js — Certificate Verification API
// Features: verify, resend, notify admin on verify

import { MongoClient } from 'mongodb';
import crypto from 'crypto';

const MONGODB_URI    = process.env.MONGODB_URI;
const DB_NAME        = process.env.DB_NAME || 'khyontek_certs';
const EMAIL_SALT     = process.env.EMAIL_SALT;
const RESEND_API_KEY = process.env.RESEND_API_KEY;
const ADMIN_EMAIL    = process.env.ADMIN_EMAIL || 'contact@khyontekai.com';
const GH_PAT         = process.env.GH_PAT;
const GH_DISPATCH_URL= process.env.GH_DISPATCH_URL;

const rateLimitMap = new Map();
const RATE_LIMIT   = 5;
const RATE_WINDOW  = 15 * 60 * 1000;

function isRateLimited(ip) {
  const now=Date.now(), entry=rateLimitMap.get(ip);
  if (!entry || now-entry.start>RATE_WINDOW) { rateLimitMap.set(ip,{count:1,start:now}); return false; }
  if (entry.count>=RATE_LIMIT) return true;
  entry.count++; return false;
}

function hashEmail(email) {
  return crypto.createHmac('sha256',EMAIL_SALT).update(email.trim().toLowerCase()).digest('hex');
}

let cachedClient=null;
async function getDb() {
  if (!cachedClient) {
    cachedClient=new MongoClient(MONGODB_URI,{connectTimeoutMS:5000,serverSelectionTimeoutMS:5000});
    await cachedClient.connect();
  }
  return cachedClient.db(DB_NAME);
}

async function notifyAdmin(record, ip) {
  if (!RESEND_API_KEY) return;
  try {
    const now=new Date().toLocaleString('en-IN',{timeZone:'Asia/Kolkata'});
    await fetch('https://api.resend.com/emails',{
      method:'POST',
      headers:{'Authorization':`Bearer ${RESEND_API_KEY}`,'Content-Type':'application/json'},
      body:JSON.stringify({
        from:'Khyontek AI System <programmes@khyontekai.com>',
        to:[ADMIN_EMAIL],
        subject:`Certificate Verified — ${record.cert_id}`,
        html:`<p>A certificate was verified at <strong>${now} IST</strong>.</p>
              <table style="border-collapse:collapse;font-family:Arial;font-size:14px;">
              <tr><td style="padding:6px 16px 6px 0;color:#8A8FA8;">Certificate ID</td><td style="padding:6px 0;color:#1A2870;font-weight:bold;">${record.cert_id}</td></tr>
              <tr><td style="padding:6px 16px 6px 0;color:#8A8FA8;">Recipient</td><td style="padding:6px 0;">${record.recipient_name}</td></tr>
              <tr><td style="padding:6px 16px 6px 0;color:#8A8FA8;">Programme</td><td style="padding:6px 0;">${record.programme}</td></tr>
              <tr><td style="padding:6px 16px 6px 0;color:#8A8FA8;">Track</td><td style="padding:6px 0;">${record.track}</td></tr>
              <tr><td style="padding:6px 16px 6px 0;color:#8A8FA8;">IP Address</td><td style="padding:6px 0;">${ip}</td></tr>
              </table>
              <p style="color:#8A8FA8;font-size:12px;margin-top:20px;">Automated notification from verify.khyontekai.com</p>`
      })
    });
  } catch(e) { console.error('Admin notify failed:',e.message); }
}

export default async function handler(req,res) {
  res.setHeader('Access-Control-Allow-Origin','*');
  res.setHeader('Access-Control-Allow-Methods','POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers','Content-Type');
  if (req.method==='OPTIONS') return res.status(200).end();
  if (req.method!=='POST')    return res.status(405).json({error:'Method not allowed'});

  const ip=req.headers['x-forwarded-for']?.split(',')[0]?.trim()||'unknown';
  if (isRateLimited(ip)) return res.status(429).json({error:'Too many attempts. Please try again after 15 minutes.'});

  const {cert_id,email,action}=req.body||{};
  if (!cert_id||typeof cert_id!=='string') return res.status(400).json({error:'Invalid certificate ID.'});
  if (!email||!email.includes('@'))        return res.status(400).json({error:'Invalid email address.'});

  const cleanId=cert_id.trim().toUpperCase();
  if (!/^KAI-[A-Z0-9]+-\d{6,8}$/.test(cleanId))
    return res.status(404).json({error:'Details do not match our records.'});

  try {
    const db=await getDb();
    const coll=db.collection('certificates');

    const record=await coll.findOne(
      {cert_id:cleanId},
      {projection:{cert_id:1,recipient_name:1,programme:1,cohort:1,
        track:1,tier:1,duration:1,issue_date:1,start_date:1,
        issued_by:1,collaborators:1,status:1,email_hash:1}}
    );

    if (!record) return res.status(404).json({error:'Details do not match our records.'});

    if (hashEmail(email)!==record.email_hash)
      return res.status(401).json({error:'Details do not match our records.'});

    if (record.status==='revoked')
      return res.status(410).json({error:'This certificate has been revoked. Contact programmes@khyontekai.com for assistance.'});

    // Resend action — trigger GitHub Action
    if (action==='resend') {
      if (!GH_PAT||!GH_DISPATCH_URL)
        return res.status(500).json({error:'Resend not configured. Contact programmes@khyontekai.com'});
      try {
        const r=await fetch(GH_DISPATCH_URL,{
          method:'POST',
          headers:{'Authorization':`token ${GH_PAT}`,'Content-Type':'application/json','Accept':'application/vnd.github.v3+json'},
          body:JSON.stringify({event_type:'resend_certificate',client_payload:{cert_id:cleanId,email}})
        });
        if (r.status===204) return res.status(200).json({message:'Certificate resent. Please check your email within 2 minutes.'});
        return res.status(500).json({error:'Resend failed. Please contact programmes@khyontekai.com'});
      } catch(e) {
        return res.status(500).json({error:'Resend failed. Please contact programmes@khyontekai.com'});
      }
    }

    // Notify admin — fire and forget
    notifyAdmin(record,ip);

    const {email_hash:_,...safeRecord}=record;
    return res.status(200).json(safeRecord);

  } catch(err) {
    console.error('[verify] Error:',err.message);
    return res.status(500).json({error:'Verification service unavailable. Please try again.'});
  }
}
