#!/usr/bin/env python3
"""
Khyontek AI — Certificate PDF Generator FINAL v6
- Logo strip and signature block are fully independent
- Up to 3 collab logos in header strip
- Up to 5 signatories in signature block (Pritam + NJK + 3 collabs)
- Dynamic font sizing for signature names based on signatory count
- Text truncation prevents overflow between signature slots
- Collab logo width capped at 200px to prevent header overflow
- Signatures: PNG image → Brittany font fallback → NothingYouCouldDo last resort
- Footer always fixed at bottom — never overlaps
- Three-line right footer: CIN / DPIIT+Assam Startup / Verify URL
- URL-based image loading from Cloudflare R2
"""
import sys, json, argparse, os, math, urllib.request, base64, tempfile, io
import boto3
from botocore.config import Config
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas as rlcanvas
from reportlab.lib.utils import ImageReader
from io import BytesIO
from datetime import datetime

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
FONT_DIR    = os.path.join(SCRIPT_DIR, 'fonts')
LOGO_PATH   = os.path.join(FONT_DIR, 'logo.png')
COLLAB_DIR  = os.path.join(FONT_DIR, 'collab-logos')
SIG_PRITAM  = os.path.join(FONT_DIR, 'sig_pritam_deka.png')
SIG_NJK     = os.path.join(FONT_DIR, 'sig_njk.png')
SIG_FONT_BRITTANY = os.path.join(FONT_DIR, 'BrittanySignature.ttf')
SIG_FONT_FALLBACK = os.path.join(FONT_DIR, 'NothingYouCouldDo-Regular.ttf')

NAVY=(26,40,112); BLUE=(43,62,170); GOLD=(245,166,35)
GREY=(130,135,150); DGREY=(50,55,85); BLK=(26,26,26)
LGREY=(235,237,245); WMB=(220,225,245); WMG=(252,238,200)
WHITE=(255,255,255)

def font(name, size):
    p = os.path.join(FONT_DIR, name)
    if os.path.exists(p): return ImageFont.truetype(p, size)
    print(f"WARNING: Font not found: {p}")
    return ImageFont.load_default()

def get_tw(d, t, f):
    b = d.textbbox((0,0), t, font=f); return b[2]-b[0]

def truncate(d, text, fnt, max_w):
    if get_tw(d, text, fnt) <= max_w: return text
    while len(text) > 3:
        text = text[:-1]
        if get_tw(d, text+"…", fnt) <= max_w: return text+"…"
    return "…"

def fmt_date(ds):
    try:
        dt=datetime.strptime(ds,"%Y-%m-%d"); day=dt.day
        sfx='th' if 11<=day<=13 else {1:'st',2:'nd',3:'rd'}.get(day%10,'th')
        return f"{day}{sfx} {dt.strftime('%B %Y')}"
    except: return ds

def load_img(path, target_h):
    """Load image from local path or HTTP/HTTPS URL. Returns PIL image or None."""
    if not path: return None
    try:
        if str(path).startswith("http://") or str(path).startswith("https://"):
            with urllib.request.urlopen(path, timeout=10) as resp:
                img = Image.open(resp).convert("RGBA")
        else:
            if not os.path.exists(path): return None
            img = Image.open(path).convert("RGBA")
        w = int(img.width * target_h / img.height)
        img = img.resize((w, target_h), Image.LANCZOS)
        bg = Image.new("RGB", img.size, WHITE)
        bg.paste(img, mask=img.split()[3])
        return bg
    except Exception as e:
        print(f"WARNING: Could not load image {path}: {e}")
        return None

def load_img_b64(b64_str, target_h):
    """Load image from base64 string. Returns PIL image or None."""
    if not b64_str: return None
    try:
        img_data = base64.b64decode(b64_str)
        img = Image.open(BytesIO(img_data)).convert("RGBA")
        w = int(img.width * target_h / img.height)
        img = img.resize((w, target_h), Image.LANCZOS)
        bg = Image.new("RGB", img.size, WHITE)
        bg.paste(img, mask=img.split()[3])
        return bg
    except Exception as e:
        print(f"WARNING: Could not decode base64 image: {e}")
        return None

def fetch_from_r2(key):
    """Fetch image from private R2 bucket using credentials from env vars."""
    if not key: return None
    try:
        account_id = os.environ.get('R2_ACCOUNT_ID','')
        access_key = os.environ.get('R2_ACCESS_KEY_ID','')
        secret_key = os.environ.get('R2_SECRET_ACCESS_KEY','')
        bucket     = os.environ.get('R2_BUCKET_NAME','')
        if not all([account_id, access_key, secret_key, bucket]):
            print(f"WARNING: R2 credentials not set — cannot fetch {key}")
            return None
        s3 = boto3.client(
            's3',
            endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version='s3v4'),
            region_name='auto',
        )
        obj = s3.get_object(Bucket=bucket, Key=key)
        img_data = obj['Body'].read()
        return Image.open(io.BytesIO(img_data)).convert("RGBA")
    except Exception as e:
        print(f"WARNING: Could not fetch {key} from R2: {e}")
        return None

def load_r2_img(key, target_h):
    """Fetch image from R2 and resize to target height."""
    if not key: return None
    raw = fetch_from_r2(key)
    if not raw: return None
    try:
        w = int(raw.width * target_h / raw.height)
        resized = raw.resize((w, target_h), Image.LANCZOS)
        bg = Image.new("RGB", resized.size, WHITE)
        bg.paste(resized, mask=resized.split()[3])
        return bg
    except Exception as e:
        print(f"WARNING: Could not resize R2 image {key}: {e}")
        return None

def make_sig_img(text, font_path, size=80, max_w=260, max_h=90, color=NAVY):
    """Render signature font text to PIL image."""
    if not os.path.exists(font_path): return None
    try:
        fnt = ImageFont.truetype(font_path, size)
        tmp = Image.new("RGB",(2000,400),WHITE); dd=ImageDraw.Draw(tmp)
        bbox=dd.textbbox((0,0),text,font=fnt); tw_=bbox[2]-bbox[0]; th_=bbox[3]-bbox[1]
        if tw_>max_w or th_>max_h:
            scale=min(max_w/tw_,max_h/th_); size=int(size*scale)
            fnt=ImageFont.truetype(font_path,size)
            bbox=dd.textbbox((0,0),text,font=fnt); tw_=bbox[2]-bbox[0]; th_=bbox[3]-bbox[1]
        pad=14; out=Image.new("RGB",(tw_+pad*2,th_+pad*2),WHITE); d2=ImageDraw.Draw(out)
        d2.text((pad-bbox[0],pad-bbox[1]),text,font=fnt,fill=color)
        return out
    except Exception as e:
        print(f"WARNING: Could not render sig text: {e}")
        return None

def generate(data):
    W,H=3307,2339; img=Image.new("RGB",(W,H),WHITE); d=ImageDraw.Draw(img)
    PAD=140; MID=W//2

    # ── Parse meta JSON if present (GitHub dispatch nests extra data here) ──
    import json as _json
    meta = {}
    if data.get('meta'):
        try: meta = _json.loads(data['meta'])
        except: meta = {}

    # ── Parse collabs — from meta.collaborators or flat fields ──
    collabs=[]
    meta_collabs = meta.get('collaborators', [])
    if meta_collabs:
        # New nested format with R2 keys
        for i, c in enumerate(meta_collabs[:3]):
            name = c.get('name','').strip()
            sig_name_check = c.get('sig_name','').strip()
            if name or sig_name_check:  # include if has name OR signatory
                collabs.append({
                    'name':     name,
                    'logo_key': c.get('logo_key',''),
                    'logo_b64': c.get('logo_b64',''),
                    'logo_path':None,
                    'sig_name': c.get('sig_name','').strip(),
                    'sig_title':c.get('sig_title','').strip(),
                    'sig_key':  c.get('sig_key',''),
                    'sig_b64':  c.get('sig_b64',''),
                })
    else:
        # Legacy flat format
        for i in range(1,4):
            name      = data.get(f'collab_{i}_name','').strip()
            logo_file = data.get(f'collab_{i}_logo','').strip()
            logo_url  = data.get(f'collab_{i}_logo_url','').strip()
            sig_name  = data.get(f'collab_{i}_sig_name','').strip()
            sig_title = data.get(f'collab_{i}_sig_title','').strip()
            sig_url   = data.get(f'collab_{i}_sig_url','').strip()
            sig_name_leg = data.get(f'collab_{i}_sig_name','').strip()
            if name or sig_name_leg:  # include if has name OR signatory
                if logo_url: logo_path = logo_url
                elif logo_file: logo_path = os.path.join(COLLAB_DIR, logo_file)
                else: logo_path = None
                collabs.append({'name':name,'logo_path':logo_path,
                    'sig_name':sig_name,'sig_title':sig_title,'sig_url':sig_url})

    show_njk   = meta.get('show_njk_signature', data.get('show_njk_signature', False))

    duration   = data.get('duration','').strip()
    cert_id    = data.get('cert_id','KAI-SRIP-260001')
    end_date   = data.get('issue_date','')
    start_date = data.get('start_date','')
    tier       = data.get('tier','Completion')
    name_str   = data.get('recipient_name','Recipient Name')
    programme  = data.get('programme','')
    track      = data.get('track','')
    # course and institution — read from meta first (GitHub dispatch nests them there)
    course      = meta.get('course',      data.get('course','')).strip()
    institution = meta.get('institution', data.get('institution', data.get('college',''))).strip()

    # ── WATERMARKS ──
    hx,ht,hh,amp,freq=200,300,1600,70,2.8
    for i in range(119):
        t0,t1=i/120,(i+1)/120; y0=ht+t0*hh; y1=ht+t1*hh
        x0a=hx+int(amp*math.sin(2*math.pi*freq*t0)); x1a=hx+int(amp*math.sin(2*math.pi*freq*t1))
        x0b=hx+int(amp*math.sin(2*math.pi*freq*t0+math.pi)); x1b=hx+int(amp*math.sin(2*math.pi*freq*t1+math.pi))
        d.line([x0a,y0,x1a,y1],fill=WMB,width=6); d.line([x0b,y0,x1b,y1],fill=WMB,width=6)
        if i%8==0: d.line([x0a,y0,x0b,y0],fill=WMB,width=4)
    layers=[[(2950,480),(2950,660),(2950,840),(2950,1020)],
            [(3100,560),(3100,740),(3100,920)],[(3240,640),(3240,820)]]
    for li in range(len(layers)-1):
        for n1 in layers[li]:
            for n2 in layers[li+1]: d.line([n1,n2],fill=WMB,width=4)
    for layer in layers:
        for n in layer: d.ellipse([n[0]-22,n[1]-22,n[0]+22,n[1]+22],fill=WMB)
    mn=[(400,760),(530,860),(360,960),(480,1040),(580,940),(440,1140),(540,1220),(380,1300)]
    for a,b in [(0,1),(1,2),(1,4),(2,3),(3,4),(3,5),(5,6),(5,7)]: d.line([mn[a],mn[b]],fill=WMB,width=4)
    for nx,ny in mn: d.ellipse([nx-20,ny-20,nx+20,ny+20],fill=WMB)
    for y0,y1,col in [(270,305,WMB),(1960,1975,WMG)]:
        cy=(y0+y1)//2; x=0
        while x<W:
            d.polygon([(x,cy-13),(x+18,cy),(x,cy+13),(x-18,cy)],fill=col)
            d.rectangle([x-3,cy-22,x+3,cy-15],fill=col)
            d.rectangle([x-3,cy+15,x+3,cy+22],fill=col); x+=70
    for wy,wa,off,wid in [(1440,10,0,4),(1458,10,0.8,3)]:
        prev=None
        for i in range(401):
            t=i/400; x=int(t*W); y=wy+int(wa*math.sin(2*math.pi*3*t+off))
            if prev: d.line([prev,(x,y)],fill=WMG,width=wid); prev=(x,y)
    for row in range(8):
        for col in range(12):
            bx=W-720+col*56; by=1760+row*46; r=5 if (row+col)%3!=0 else 9
            d.ellipse([bx-r,by-r,bx+r,by+r],fill=WMB)
    for cx,cy,sz in [(250,1760,110),(350,1840,90),(175,1850,75)]:
        pts=[]
        for i in range(20):
            a=(i/20)*2*math.pi; x=cx+int(sz*0.35*math.cos(a)); y=cy+int(sz*math.sin(a)*0.9)
            rx=int((x-cx)*math.cos(math.pi/5)-(y-cy)*math.sin(math.pi/5))+cx
            ry=int((x-cx)*math.sin(math.pi/5)+(y-cy)*math.cos(math.pi/5))+cy
            pts.append((rx,ry))
        d.polygon(pts,fill=WMB)

    d.rectangle([0,0,W,8],fill=GOLD)

    # ── LOGO STRIP — only collabs with a logo (independent of signatures) ──
    LOGO_H=300; COLLAB_H=220; STRIP_TOP=10; MAX_COLLAB_LOGO_W=320

    kai=load_img(LOGO_PATH,LOGO_H)
    if kai: img.paste(kai,(PAD,STRIP_TOP)); kai_right=PAD+kai.width
    else:
        fL=font("Italiana-Regular.ttf",100)
        d.text((PAD,STRIP_TOP),"Khyontek.ai",font=fL,fill=BLUE); kai_right=PAD+420

    # Collabs with logo — R2 key → base64 → local path
    collabs_with_logo=[c for c in collabs if c.get('logo_key') or c.get('logo_b64') or c.get('logo_path')]
    if collabs_with_logo:
        SEP_X=kai_right+50
        d.rectangle([SEP_X,STRIP_TOP+30,SEP_X+4,STRIP_TOP+LOGO_H-30],fill=GOLD)
        fAssoc=font("WorkSans-Regular.ttf",28); assoc="In association with"
        aw=get_tw(d,assoc,fAssoc)
        tmp2=Image.new("RGBA",(aw+10,30),(255,255,255,0)); td2=ImageDraw.Draw(tmp2)
        td2.text((0,0),assoc,font=fAssoc,fill=GREY); rot=tmp2.rotate(90,expand=True)
        img.paste(rot,(SEP_X-rot.width//2-8,STRIP_TOP+(LOGO_H-rot.height)//2),rot)
        cx_pos=SEP_X+80
        for c in collabs_with_logo:
            # Try R2 key → base64 → local path
            clogo = load_r2_img(c.get('logo_key',''), COLLAB_H)
            if not clogo: clogo = load_img_b64(c.get('logo_b64',''), COLLAB_H)
            if not clogo and c.get('logo_path'): clogo = load_img(c['logo_path'], COLLAB_H)
            if clogo:
                if clogo.width>MAX_COLLAB_LOGO_W:
                    clogo=clogo.resize((MAX_COLLAB_LOGO_W,COLLAB_H),Image.LANCZOS)
                logo_y=STRIP_TOP+(LOGO_H-COLLAB_H)//2
                img.paste(clogo,(cx_pos,logo_y))
                cx_pos+=clogo.width+70

    # ── CERT ID + DATE ──
    RULE_Y  = STRIP_TOP + LOGO_H + 12
    TITLE_Y = RULE_Y + 28
    fM=font("WorkSans-Regular.ttf",34)
    d.text((W-PAD-get_tw(d,f"Certificate ID: {cert_id}",fM),STRIP_TOP+40),f"Certificate ID: {cert_id}",font=fM,fill=DGREY)
    d.text((W-PAD-get_tw(d,f"Date: {fmt_date(end_date)}",fM),STRIP_TOP+90),f"Date: {fmt_date(end_date)}",font=fM,fill=GREY)

    d.rectangle([0,RULE_Y,W,RULE_Y+10],fill=GOLD); d.rectangle([0,RULE_Y+10,W,RULE_Y+20],fill=NAVY)

    # ── CERTIFICATE TITLE ──
    fBig=font("WorkSans-Bold.ttf",260)
    d.text((MID-get_tw(d,"Certificate",fBig)//2,290),"Certificate",font=fBig,fill=NAVY)
    tier_line='OF COMPLETION' if tier=='Completion' else 'OF RESEARCH CONTRIBUTION'
    fTier=font("WorkSans-Bold.ttf",76)
    d.text((MID-get_tw(d,tier_line,fTier)//2,576),tier_line,font=fTier,fill=NAVY)
    d.rectangle([MID-340,680,MID+340,688],fill=GOLD)
    fC=font("Lora-Italic.ttf",46)
    d.text((MID-get_tw(d,"This is to certify that",fC)//2,710),"This is to certify that",font=fC,fill=GREY)

    # ── RECIPIENT NAME ──
    fN=font("Lora-BoldItalic.ttf",96); nw=get_tw(d,name_str,fN)
    d.text((MID-nw//2,790),name_str,font=fN,fill=NAVY)
    ul=min(nw//2+130,660); d.rectangle([MID-ul,910,MID+ul,916],fill=NAVY)

    # ── COURSE / INSTITUTION LINE ──
    parts=[p for p in [course,institution] if p]
    sub_line="  ·  ".join(parts)
    SUB_Y_OFFSET=0
    if sub_line:
        fSub=font("Lora-Italic.ttf",38)
        d.text((MID-get_tw(d,sub_line,fSub)//2,934),sub_line,font=fSub,fill=GREY)
        SUB_Y_OFFSET=58

    # ── BODY TEXT ──
    fBo=font("Lora-Regular.ttf",40); fBi=font("Lora-Italic.ttf",40)
    named_collabs=[c['name'].strip() for c in collabs if c.get('name','').strip()]
    if named_collabs:
        org_line=f"offered by Khyontek AI Pvt Ltd in collaboration with {' and '.join(named_collabs)},"
    else:
        org_line="offered by Khyontek AI Pvt Ltd,"
    lines=[(f"has successfully completed the {programme}",fBo),(org_line,fBo),
           ("participating in the research track:",fBo),(f"'{track}'",fBi),
           (f"from {fmt_date(start_date)} to {fmt_date(end_date)}.",fBo)]
    y=TITLE_Y+620
    for txt,fnt_ in lines:
        sz=40 if get_tw(d,txt,fnt_)<W-PAD*4 else 34
        fu=font("Lora-Italic.ttf" if fnt_==fBi else "Lora-Regular.ttf",sz)
        d.text((MID-get_tw(d,txt,fu)//2,y),txt,font=fu,fill=BLK); y+=sz+18
    if duration:
        fDur=font("Lora-Italic.ttf",36); dur_txt=f"Duration: {duration}"
        d.text((MID-get_tw(d,dur_txt,fDur)//2,y+6),dur_txt,font=fDur,fill=GREY); y+=52
    fW=font("Lora-Italic.ttf",36); wish="With best wishes for a future defined by curiosity and contribution."
    d.text((MID-get_tw(d,wish,fW)//2,y+16),wish,font=fW,fill=GREY)

    # ── FIXED LAYOUT — footer always at bottom ──
    FOOTER_BAR_Y  = 2260
    FOOTER_TEXT_Y = FOOTER_BAR_Y + 18

    # Three info lines — placed working UP from footer bar
    fF=font("WorkSans-Regular.ttf",26); fFsm=font("WorkSans-Regular.ttf",24)
    LINE_GAP=42
    L3_Y=FOOTER_BAR_Y-24-LINE_GAP   # Verify URL
    L2_Y=L3_Y-LINE_GAP               # DPIIT + Assam Startup
    L1_Y=L2_Y-LINE_GAP               # CIN
    d.text((W-PAD-get_tw(d,"CIN: U62020AS2026PTC029657",fF),L1_Y),
           "CIN: U62020AS2026PTC029657",font=fF,fill=GREY)
    d.text((W-PAD-get_tw(d,"DPIIT Recognised  ·  Assam Startup Recognised",fFsm),L2_Y),
           "DPIIT Recognised  ·  Assam Startup Recognised",font=fFsm,fill=GREY)
    d.text((W-PAD-get_tw(d,"Verify at: programmes.khyontekai.com/verify",fFsm),L3_Y),
           "Verify at: programmes.khyontekai.com/verify",font=fFsm,fill=BLUE)

    # ── SIGNATURE BLOCK — independent of logo count ──
    SIG_IMG_H     = 120
    SIG_DIVIDER_Y = L1_Y - 190
    SIG_Y         = SIG_DIVIDER_Y + 14
    d.rectangle([PAD,SIG_DIVIDER_Y,W-PAD,SIG_DIVIDER_Y+2],fill=LGREY)

    sigs=[]

    # Pritam — always first
    # Priority: R2 URL → local PNG → Brittany font → NothingYouCouldDo
    # Pritam — R2 key → local PNG → Brittany font
    pritam_key = meta.get('pritam_sig_key', 'signatures/sig_pritam.png')
    sig_p = load_r2_img(pritam_key, SIG_IMG_H)
    if not sig_p: sig_p = load_img(SIG_PRITAM, SIG_IMG_H)
    if not sig_p: sig_p = make_sig_img("Pritam Deka", SIG_FONT_BRITTANY, size=90, max_w=300, max_h=SIG_IMG_H)
    sigs.append({'img':sig_p,'name':'Dr Pritam Deka','title':'CEO, Khyontek AI'})

    # NJK — if toggled
    if show_njk:
        njk_key = meta.get('njk_sig_key', 'signatures/sig_njk.png')
        sig_n = load_r2_img(njk_key, SIG_IMG_H)
        if not sig_n: sig_n = load_img(SIG_NJK, SIG_IMG_H)
        if not sig_n: sig_n = make_sig_img("Nayan J Kalita", SIG_FONT_BRITTANY, size=85, max_w=300, max_h=SIG_IMG_H)
        sigs.append({'img':sig_n,'name':'Nayan Jyoti Kalita','title':'CSO, Khyontek AI'})

    # Collab signatories — R2 key → Brittany font fallback
    for c in collabs:
        if c.get('sig_name'):
            cb_img = load_r2_img(c.get('sig_key',''), SIG_IMG_H) if c.get('sig_key') else None
            if not cb_img:
                cb_img = make_sig_img(c['sig_name'], SIG_FONT_BRITTANY, size=80, max_w=260, max_h=SIG_IMG_H)
            sigs.append({'img':cb_img,'name':c['sig_name'],'title':c.get('sig_title','')})

    # Dynamic font size — scales down as n_sigs increases, no overlap
    n_sigs     = len(sigs)
    name_size  = max(22, 32-(n_sigs-1)*2)
    title_size = max(18, 26-(n_sigs-1)*2)
    fSN=font("WorkSans-Regular.ttf",name_size)
    fSS=font("WorkSans-Regular.ttf",title_size)

    # Even slot distribution
    actual_slot = min(500,(W-PAD*2)//max(n_sigs,1))
    max_text_w  = actual_slot - 20

    for i,sig in enumerate(sigs):
        sx=PAD+i*actual_slot
        if sig.get('img'):
            img.paste(sig['img'],(sx,SIG_Y)); rule_y=SIG_Y+SIG_IMG_H+14
        else:
            fFB=font("NothingYouCouldDo-Regular.ttf",80)
            d.text((sx,SIG_Y),sig['name'].split()[0],font=fFB,fill=NAVY)
            rule_y=SIG_Y+100
        d.rectangle([sx,rule_y,sx+300,rule_y+3],fill=NAVY)
        d.text((sx,rule_y+12),truncate(d,sig['name'],fSN,max_text_w),font=fSN,fill=BLK)
        # Wrap title into two lines if too long
        title_str=sig['title']
        if get_tw(d,title_str,fSS)<=max_text_w:
            d.text((sx,rule_y+12+name_size+8),title_str,font=fSS,fill=GREY)
        else:
            # Split at comma or space closest to middle
            words=title_str.split(' ')
            line1=''; line2=''
            for w in words:
                test=line1+(' ' if line1 else '')+w
                if get_tw(d,test,fSS)<=max_text_w: line1=test
                else: line2=(line2+' '+w).strip()
            d.text((sx,rule_y+12+name_size+8), line1,font=fSS,fill=GREY)
            d.text((sx,rule_y+12+name_size+8+title_size+4),line2,font=fSS,fill=GREY)

    # ── FOOTER BAR — always fixed ──
    d.rectangle([0,FOOTER_BAR_Y,  W,FOOTER_BAR_Y+8],fill=GOLD)
    d.rectangle([0,FOOTER_BAR_Y+8,W,H],             fill=NAVY)
    fBot=font("WorkSans-Regular.ttf",24)
    em="programmes@khyontekai.com"; cp="© 2026 Khyontek AI Private Limited"
    d.text((PAD,FOOTER_TEXT_Y),em,font=fBot,fill=(160,170,215))
    d.text((W-PAD-get_tw(d,cp,fBot),FOOTER_TEXT_Y),cp,font=fBot,fill=(160,170,215))

    return img

def save_pdf(img,out):
    if img.mode!='RGB': img=img.convert('RGB')
    buf=BytesIO()
    img.save(buf,'JPEG',quality=95,optimize=True,dpi=(200,200))
    buf.seek(0)
    pw,ph=landscape(A4)
    c=rlcanvas.Canvas(out,pagesize=(pw,ph))
    c.setTitle("Certificate — Khyontek AI")
    c.setAuthor("Khyontek AI Pvt Ltd")
    c.drawImage(ImageReader(buf),0,0,width=pw,height=ph)
    c.save()

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument('--data',   required=True)
    parser.add_argument('--output', required=True)
    args=parser.parse_args()
    data=json.loads(args.data)
    img=generate(data)
    save_pdf(img,args.output)
    print(f"Certificate generated: {args.output}")
