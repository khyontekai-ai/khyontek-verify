#!/usr/bin/env python3
"""
Khyontek AI — Certificate PDF Generator FINAL v5
All features complete. Fixed layout — footer always at bottom, no overlaps.
"""
import sys, json, argparse, os, math
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

NAVY=(26,40,112); BLUE=(43,62,170); GOLD=(245,166,35)
GREY=(130,135,150); DGREY=(50,55,85); BLK=(26,26,26)
LGREY=(235,237,245); WMB=(220,225,245); WMG=(252,238,200)
WHITE=(255,255,255)

def font(name, size):
    p = os.path.join(FONT_DIR, name)
    if os.path.exists(p): return ImageFont.truetype(p, size)
    print(f"WARNING: Font not found: {p}")
    return ImageFont.load_default()

def tw(d, t, f):
    b = d.textbbox((0,0), t, font=f); return b[2]-b[0]

def fmt_date(ds):
    try:
        dt=datetime.strptime(ds,"%Y-%m-%d"); day=dt.day
        sfx='th' if 11<=day<=13 else {1:'st',2:'nd',3:'rd'}.get(day%10,'th')
        return f"{day}{sfx} {dt.strftime('%B %Y')}"
    except: return ds

def load_img(path, target_h):
    if not path or not os.path.exists(path): return None
    try:
        img=Image.open(path).convert("RGBA")
        w=int(img.width*target_h/img.height)
        img=img.resize((w,target_h),Image.LANCZOS)
        bg=Image.new("RGB",img.size,WHITE)
        bg.paste(img,mask=img.split()[3])
        return bg
    except Exception as e:
        print(f"WARNING: Could not load image {path}: {e}")
        return None

def make_sig_png(text, font_path, size=90, max_w=340, max_h=90, color=NAVY):
    """Render signature font text to PIL image at fixed height."""
    if not os.path.exists(font_path):
        return None
    fnt  = ImageFont.truetype(font_path, size)
    tmp  = Image.new("RGB",(2000,400),WHITE)
    dd   = ImageDraw.Draw(tmp)
    bbox = dd.textbbox((0,0), text, font=fnt)
    tw_  = bbox[2]-bbox[0]; th_=bbox[3]-bbox[1]
    if tw_ > max_w or th_ > max_h:
        scale = min(max_w/tw_, max_h/th_)
        size  = int(size*scale)
        fnt   = ImageFont.truetype(font_path, size)
        bbox  = dd.textbbox((0,0), text, font=fnt)
        tw_   = bbox[2]-bbox[0]; th_=bbox[3]-bbox[1]
    pad=14
    out=Image.new("RGB",(tw_+pad*2, th_+pad*2),WHITE)
    d2=ImageDraw.Draw(out)
    d2.text((pad-bbox[0], pad-bbox[1]), text, font=fnt, fill=color)
    return out

def generate(data):
    W,H=3307,2339
    img=Image.new("RGB",(W,H),WHITE)
    d=ImageDraw.Draw(img)
    PAD=140; MID=W//2

    # Parse data
    collabs=[]
    for i in range(1,4):
        name=data.get(f'collab_{i}_name','').strip()
        logo_file=data.get(f'collab_{i}_logo','').strip()
        sig_name=data.get(f'collab_{i}_sig_name','').strip()
        sig_title=data.get(f'collab_{i}_sig_title','').strip()
        if name:
            logo_path=os.path.join(COLLAB_DIR,logo_file) if logo_file else None
            collabs.append({'name':name,'logo_path':logo_path,'sig_name':sig_name,'sig_title':sig_title})

    show_njk  =data.get('show_njk_signature',False)
    duration  =data.get('duration','').strip()
    cert_id   =data.get('cert_id','KAI-SRIP-260001')
    end_date  =data.get('issue_date','')
    start_date=data.get('start_date','')
    tier      =data.get('tier','Completion')
    name_str  =data.get('recipient_name','Recipient Name')
    programme =data.get('programme','')
    track     =data.get('track','')

    # ── WATERMARKS ──
    hx,ht,hh,amp,freq=200,300,1600,70,2.8
    for i in range(119):
        t0,t1=i/120,(i+1)/120
        y0=ht+t0*hh; y1=ht+t1*hh
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
            d.rectangle([x-3,cy+15,x+3,cy+22],fill=col)
            x+=70
    for wy,wa,off,wid in [(1440,10,0,4),(1458,10,0.8,3)]:
        prev=None
        for i in range(401):
            t=i/400; x=int(t*W); y=wy+int(wa*math.sin(2*math.pi*3*t+off))
            if prev: d.line([prev,(x,y)],fill=WMG,width=wid)
            prev=(x,y)
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

    # ── LOGO STRIP ──
    LOGO_H=180; COLLAB_H=130; STRIP_TOP=32
    kai=load_img(LOGO_PATH,LOGO_H)
    if kai: img.paste(kai,(PAD,STRIP_TOP)); kai_right=PAD+kai.width
    else:
        fL=font("Italiana-Regular.ttf",100); d.text((PAD,STRIP_TOP),"Khyontek.ai",font=fL,fill=BLUE); kai_right=PAD+420
    if collabs:
        SEP_X=kai_right+50
        d.rectangle([SEP_X,STRIP_TOP+20,SEP_X+3,STRIP_TOP+LOGO_H-20],fill=GOLD)
        fAssoc=font("WorkSans-Regular.ttf",24); assoc="In association with"
        aw=tw(d,assoc,fAssoc)
        tmp2=Image.new("RGBA",(aw+10,30),(255,255,255,0)); td2=ImageDraw.Draw(tmp2)
        td2.text((0,0),assoc,font=fAssoc,fill=GREY); rot=tmp2.rotate(90,expand=True)
        img.paste(rot,(SEP_X-rot.width//2-8,STRIP_TOP+(LOGO_H-rot.height)//2),rot)
        cx_pos=SEP_X+55; fCN=font("WorkSans-Regular.ttf",26); fCNsm=font("WorkSans-Regular.ttf",22)
        for c in collabs:
            clogo=load_img(c['logo_path'],COLLAB_H)
            if clogo:
                logo_y=STRIP_TOP+(LOGO_H-COLLAB_H)//2; img.paste(clogo,(cx_pos,logo_y))
                logo_w=clogo.width; cnw=tw(d,c['name'],fCNsm)
                d.text((cx_pos+(logo_w-cnw)//2,logo_y+COLLAB_H+8),c['name'],font=fCNsm,fill=GREY)
                cx_pos+=logo_w+50
            else:
                d.text((cx_pos,STRIP_TOP+(LOGO_H-40)//2),c['name'],font=fCN,fill=NAVY)
                cx_pos+=tw(d,c['name'],fCN)+60

    # Cert ID + Date
    fM=font("WorkSans-Regular.ttf",34)
    d.text((W-PAD-tw(d,f"Certificate ID: {cert_id}",fM),78),f"Certificate ID: {cert_id}",font=fM,fill=DGREY)
    d.text((W-PAD-tw(d,f"Date: {fmt_date(end_date)}",fM),122),f"Date: {fmt_date(end_date)}",font=fM,fill=GREY)
    d.rectangle([0,256,W,266],fill=GOLD); d.rectangle([0,266,W,276],fill=NAVY)

    fBig=font("WorkSans-Bold.ttf",260)
    d.text((MID-tw(d,"Certificate",fBig)//2,290),"Certificate",font=fBig,fill=NAVY)
    tier_line='OF COMPLETION' if tier=='Completion' else 'OF RESEARCH CONTRIBUTION'
    fTier=font("WorkSans-Bold.ttf",76)
    d.text((MID-tw(d,tier_line,fTier)//2,576),tier_line,font=fTier,fill=NAVY)
    d.rectangle([MID-340,680,MID+340,688],fill=GOLD)
    fC=font("Lora-Italic.ttf",46)
    d.text((MID-tw(d,"This is to certify that",fC)//2,710),"This is to certify that",font=fC,fill=GREY)
    fN=font("Lora-BoldItalic.ttf",96); nw=tw(d,name_str,fN)
    d.text((MID-nw//2,790),name_str,font=fN,fill=NAVY)
    ul=min(nw//2+130,660); d.rectangle([MID-ul,910,MID+ul,916],fill=NAVY)

    fBo=font("Lora-Regular.ttf",40); fBi=font("Lora-Italic.ttf",40)
    org_line=(f"offered by Khyontek AI Pvt Ltd in collaboration with {' and '.join(c['name'] for c in collabs)},"
              if collabs else "offered by Khyontek AI Pvt Ltd,")
    lines=[(f"has successfully completed the {programme}",fBo),(org_line,fBo),
           ("participating in the research track:",fBo),(f"'{track}'",fBi),
           (f"from {fmt_date(start_date)} to {fmt_date(end_date)}.",fBo)]
    y=950
    for txt,fnt_ in lines:
        sz=40 if tw(d,txt,fnt_)<W-PAD*4 else 34
        fu=font("Lora-Italic.ttf" if fnt_==fBi else "Lora-Regular.ttf",sz)
        d.text((MID-tw(d,txt,fu)//2,y),txt,font=fu,fill=BLK); y+=sz+18
    if duration:
        fDur=font("Lora-Italic.ttf",36); dur_txt=f"Duration: {duration}"
        d.text((MID-tw(d,dur_txt,fDur)//2,y+6),dur_txt,font=fDur,fill=GREY); y+=52
    fW=font("Lora-Italic.ttf",36); wish="With best wishes for a future defined by curiosity and contribution."
    d.text((MID-tw(d,wish,fW)//2,y+16),wish,font=fW,fill=GREY)

    # ── FIXED LAYOUT — footer at bottom, text above it, sigs above that ──
    FOOTER_BAR_Y  = 2260   # always fixed
    FOOTER_TEXT_Y = FOOTER_BAR_Y + 18

    # Three info lines placed working UP from footer bar
    fF=font("WorkSans-Regular.ttf",26); fFsm=font("WorkSans-Regular.ttf",24)
    LINE_GAP = 42
    L3_Y = FOOTER_BAR_Y - 24 - LINE_GAP      # verify URL
    L2_Y = L3_Y - LINE_GAP                    # recognitions
    L1_Y = L2_Y - LINE_GAP                    # CIN
    line1="CIN: U62020AS2026PTC029657"
    line2="DPIIT Recognised  ·  Assam Startup Recognised"
    line3="Verify at: programmes.khyontekai.com/verify"
    d.text((W-PAD-tw(d,line1,fF),  L1_Y),line1,font=fF,  fill=GREY)
    d.text((W-PAD-tw(d,line2,fFsm),L2_Y),line2,font=fFsm,fill=GREY)
    d.text((W-PAD-tw(d,line3,fFsm),L3_Y),line3,font=fFsm,fill=BLUE)

    # Signature block placed above info lines
    SIG_IMG_H     = 90
    SIG_DIVIDER_Y = L1_Y - 150
    SIG_Y         = SIG_DIVIDER_Y + 14
    d.rectangle([PAD,SIG_DIVIDER_Y,W-PAD,SIG_DIVIDER_Y+2],fill=LGREY)

    sigs=[]
    # Try pre-rendered PNG first, fall back to font rendering
    sig_p_img=load_img(SIG_PRITAM,SIG_IMG_H)
    if not sig_p_img:
        sig_p_img=make_sig_png("Pritam Deka",
            os.path.join(FONT_DIR,"BrittanySignature.ttf"),
            size=90,max_w=340,max_h=SIG_IMG_H)
    sigs.append({'img':sig_p_img,'name':'Dr Pritam Deka','title':'CEO, Khyontek AI'})

    if show_njk:
        sig_n_img=load_img(SIG_NJK,SIG_IMG_H)
        if not sig_n_img:
            sig_n_img=make_sig_png("Nayan J Kalita",
                os.path.join(FONT_DIR,"TheRichJulliettaDemo.ttf"),
                size=85,max_w=340,max_h=SIG_IMG_H)
        sigs.append({'img':sig_n_img,'name':'Nayan Jyoti Kalita','title':'CSO, Khyontek AI'})

    for c in collabs:
        if c.get('sig_name'):
            sigs.append({'img':None,'name':c['sig_name'],'title':c.get('sig_title','')})

    n_sigs=len(sigs)
    actual_slot=min(480,(W-PAD*2)//max(n_sigs,1))
    fSN=font("WorkSans-Regular.ttf",30); fSS=font("WorkSans-Regular.ttf",24)
    fSH=font("NothingYouCouldDo-Regular.ttf",68)

    for i,sig in enumerate(sigs):
        sx=PAD+i*actual_slot
        if sig.get('img'):
            img.paste(sig['img'],(sx,SIG_Y)); rule_y=SIG_Y+SIG_IMG_H+14
        else:
            d.text((sx,SIG_Y),sig['name'].split()[0],font=fSH,fill=NAVY); rule_y=SIG_Y+80
        d.rectangle([sx,rule_y,sx+280,rule_y+3],fill=NAVY)
        d.text((sx,rule_y+12),sig['name'],font=fSN,fill=BLK)
        d.text((sx,rule_y+52),sig['title'],font=fSS,fill=GREY)

    # Footer bar — fixed at bottom
    d.rectangle([0,FOOTER_BAR_Y,  W,FOOTER_BAR_Y+8],fill=GOLD)
    d.rectangle([0,FOOTER_BAR_Y+8,W,H],             fill=NAVY)
    fBot=font("WorkSans-Regular.ttf",24)
    em="programmes@khyontekai.com"; cp="© 2026 Khyontek AI Private Limited"
    d.text((PAD,FOOTER_TEXT_Y),em,font=fBot,fill=(160,170,215))
    d.text((W-PAD-tw(d,cp,fBot),FOOTER_TEXT_Y),cp,font=fBot,fill=(160,170,215))

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
    parser.add_argument('--data',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    data=json.loads(args.data)
    img=generate(data)
    save_pdf(img,args.output)
    print(f"Certificate generated: {args.output}")
