# Khyontek AI — Certificate Verification System v2.0

## Features
- Admin panel with confirmation modal before issuing
- Up to 3 collaborator logos on certificates
- Dynamic signature block (Dr. Pritam Deka + optional NJK)
- Collaborator signatory support
- Custom track name
- Payment tracking
- Resend button on verify portal
- Admin email notification on every verification
- Duplicate student check
- Watermark background design (DNA, neural network, Assam motifs)

## Structure
```
khyontek-verify/
├── index.html                     ← verify.khyontekai.com
├── admin.html                     ← Admin form (GitHub Pages)
├── api/verify.js                  ← Vercel API
├── scripts/
│   ├── generate_cert.py           ← PDF generator v3
│   ├── mongo_insert.py            ← MongoDB insert
│   ├── send_email.py              ← Resend email
│   ├── archive_cert.py            ← GitHub archive
│   ├── build_admin.py             ← Injects secrets at build
│   ├── bulk-insert.js             ← Bulk CSV insert
│   ├── insert-certificate.js      ← Single insert
│   └── fonts/
│       ├── logo.png               ← ADD THIS MANUALLY
│       ├── *.ttf                  ← Font files
│       └── collab-logos/          ← Collaborator logos go here
│           └── README.md
├── .github/workflows/
│   ├── issue-certificate.yml
│   └── deploy-admin.yml
├── vercel.json
├── package.json
├── .env.example
├── .gitignore
└── README.md
```

## GitHub Secrets Required (11 total)
| Secret | Value |
|---|---|
| MONGODB_URI | MongoDB Atlas connection string |
| DB_NAME | khyontek_certs |
| EMAIL_SALT | 64-char hex string — never change |
| RESEND_API_KEY | Resend API key |
| ADMIN_ID | adcert |
| ADMIN_PASSWORD | your admin password |
| GH_PAT | GitHub token (repo + workflow scope) |
| GH_PAGES_TOKEN | same token |
| GH_DISPATCH_URL | https://api.github.com/repos/khyontekai-ai/khyontek-verify/dispatches |
| CERT_ARCHIVE_REPO | khyontekai-ai/khyontek-certificates |
| ADMIN_EMAIL | contact@khyontekai.com |

## Vercel Environment Variables (5)
| Variable | Value |
|---|---|
| MONGODB_URI | same as GitHub secret |
| DB_NAME | khyontek_certs |
| EMAIL_SALT | same as GitHub secret |
| RESEND_API_KEY | same as GitHub secret |
| ADMIN_EMAIL | contact@khyontekai.com |

## Certificate ID Format
KAI-[PROG]-[YY][SERIAL]
Example: KAI-SRIP-260001

## Key URLs
- Verify: https://verify.khyontekai.com
- Admin: https://khyontekai-ai.github.io/khyontek-verify/
- MongoDB: cloud.mongodb.com
- CIN: U62020AS2026PTC029657
