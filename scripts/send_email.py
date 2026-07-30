#!/usr/bin/env python3
"""
send_email.py — Send certificate email via Resend
Features: collaborator mention, branded HTML, PDF attachment
"""
import sys, json, os, argparse, base64, requests
from datetime import datetime

def fmt_date(ds):
    try:
        dt=datetime.strptime(ds,"%Y-%m-%d"); day=dt.day
        sfx='th' if 11<=day<=13 else {1:'st',2:'nd',3:'rd'}.get(day%10,'th')
        return f"{day}{sfx} {dt.strftime('%B %Y')}"
    except: return ds

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data',required=True)
    parser.add_argument('--pdf',required=True)
    args=parser.parse_args()

    data       = json.loads(args.data)
    api_key    = os.environ['RESEND_API_KEY']
    from_email = 'programmes@khyontekai.com'
    to_email   = data['email']
    first_name = data['recipient_name'].split()[0]
    cert_id    = data['cert_id']
    programme  = data.get('programme','Khyontek AI Programme')
    track      = data.get('track','')
    tier       = data.get('tier','Completion')
    issue_date = fmt_date(data.get('issue_date',''))
    cert_type  = 'Certificate of Research Contribution' if tier=='Research Contribution' else 'Certificate of Completion'

    # Collaborators
    collabs=[]
    for i in range(1,4):
        n=data.get(f'collab_{i}_name','').strip()
        if n: collabs.append(n)

    collab_text=''
    collab_html=''
    if collabs:
        names=' and '.join(collabs)
        collab_text=f' in collaboration with {names}'
        collab_html=f'<p style="font-size:13px;color:#6B7280;margin:4px 0 0;">In collaboration with: <strong>{names}</strong></p>'

    with open(args.pdf,'rb') as f:
        pdf_b64=base64.b64encode(f.read()).decode()
    pdf_filename=os.path.basename(args.pdf)

    html=f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#F5F6FA;font-family:Arial,sans-serif;">
<div style="max-width:600px;margin:0 auto;background:#fff;">
  <div style="background:#1A2870;padding:32px 40px;">
    <div style="font-size:28px;color:#fff;font-weight:bold;">Khyontek.ai</div>
    <div style="font-size:11px;color:#8090CC;letter-spacing:0.2em;text-transform:uppercase;margin-top:4px;">The Shape of Intelligence</div>
  </div>
  <div style="height:3px;background:#F5A623;"></div>
  <div style="padding:40px;">
    <div style="font-size:18px;color:#1A2870;font-weight:bold;margin-bottom:16px;">Dear {first_name},</div>
    <p style="font-size:14px;color:#2E3355;line-height:1.7;margin-bottom:14px;">
      Congratulations on successfully completing the <strong>{programme}</strong>
      offered by Khyontek AI Pvt Ltd{collab_text}.
      We are pleased to present your official certificate.
    </p>
    <div style="background:#ECEEF6;border-left:4px solid #2B3EAA;padding:20px 24px;border-radius:2px;margin:24px 0;">
      <div style="font-size:10px;color:#8A8FA8;letter-spacing:0.16em;text-transform:uppercase;margin-bottom:3px;">Certificate</div>
      <div style="font-size:14px;color:#1A2870;font-weight:bold;margin-bottom:4px;">{cert_type}</div>
      {collab_html}
      <div style="font-size:10px;color:#8A8FA8;letter-spacing:0.16em;text-transform:uppercase;margin:12px 0 3px;">Research Track</div>
      <div style="font-size:14px;color:#1A2870;font-weight:bold;margin-bottom:12px;">{track}</div>
      <div style="font-size:10px;color:#8A8FA8;letter-spacing:0.16em;text-transform:uppercase;margin-bottom:3px;">Certificate ID</div>
      <div style="font-size:14px;color:#1A2870;font-weight:bold;margin-bottom:12px;">{cert_id}</div>
      <div style="font-size:10px;color:#8A8FA8;letter-spacing:0.16em;text-transform:uppercase;margin-bottom:3px;">Issue Date</div>
      <div style="font-size:14px;color:#1A2870;font-weight:bold;">{issue_date}</div>
    </div>
    <p style="font-size:14px;color:#2E3355;line-height:1.7;">Your certificate is attached to this email as a PDF. Please save it for your records.</p>
    <p style="font-size:14px;color:#2E3355;margin-top:14px;">To verify your certificate, visit:</p>
    <a href="https://verify.khyontekai.com" style="display:inline-block;padding:14px 32px;background:#1A2870;color:#fff;text-decoration:none;border-radius:2px;font-size:13px;letter-spacing:0.12em;text-transform:uppercase;margin:8px 0 24px;">Verify Certificate</a>
    <p style="font-size:12px;color:#8A8FA8;">Enter Certificate ID <strong>{cert_id}</strong> and your registered email address to verify.</p>
    <p style="font-style:italic;color:#6B7280;font-size:13px;margin:20px 0;">With best wishes for a future defined by curiosity and contribution.</p>
    <div style="margin-top:32px;padding-top:20px;border-top:1px solid #ECEEF6;">
      <div style="font-size:15px;color:#1A2870;font-weight:bold;">Team Khyontek AI</div>
      <div style="font-size:12px;color:#8A8FA8;margin-top:2px;">Khyontek AI Private Limited · Guwahati, Assam</div>
      <div style="font-size:12px;color:#8A8FA8;margin-top:2px;">CIN: U62020AS2026PTC029657</div>
    </div>
  </div>
  <div style="background:#F5F6FA;padding:20px 40px;text-align:center;font-size:11px;color:#8A8FA8;border-top:1px solid #ECEEF6;">
    <a href="https://khyontekai.com" style="color:#2B3EAA;text-decoration:none;">khyontekai.com</a> &nbsp;·&nbsp;
    <a href="mailto:programmes@khyontekai.com" style="color:#2B3EAA;text-decoration:none;">programmes@khyontekai.com</a><br/>
    © 2026 Khyontek AI Pvt Ltd. All rights reserved.
  </div>
</div>
</body></html>"""

    resp=requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"},
        json={"from":f"Khyontek AI Programmes <{from_email}>","to":[to_email],
              "subject":f"Your Certificate — {programme} | Khyontek AI",
              "html":html,
              "attachments":[{"filename":pdf_filename,"content":pdf_b64}]},
        timeout=30
    )

    if resp.status_code in (200,201):
        print(f"Email sent to {to_email}")
    else:
        print(f"Email failed: {resp.status_code} — {resp.text}")
        sys.exit(1)

if __name__=="__main__":
    main()
