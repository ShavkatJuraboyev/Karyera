"""Rezyume (CV) ni PDF shaklida yaratish.

Dizayn: chapda lojuvard yon panel (xatam naqshi, rasm, aloqa, ko'nikma, til), o'ngda asosiy mazmun
(ism, maqsad, tajriba vaqt chizig'i, ta'lim, sertifikat, portfolio). Brauzerdagi CV bilan bir xil ko'rinishda.
"""
import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, FrameBreak, NextPageTemplate, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

from core.exporters import get_fonts, pdf_text

PAGE_W, PAGE_H = A4
SIDE_W = 66 * mm
DEEP = colors.HexColor("#0E2563")
BLUE = colors.HexColor("#1B3A8F")
TURQ = colors.HexColor("#1FA9A4")
INK = colors.HexColor("#17223F")
MUTED = colors.HexColor("#5A6985")
LINE = colors.HexColor("#DFE5F0")
SOFT = colors.HexColor("#DBE5FF")
LIGHT_TURQ = colors.HexColor("#9FE3DF")


def _clip(text, limit):
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _star(c, cx, cy, r):
    """Sakkiz qirrali yulduz (xatam): ikki kvadrat."""
    a = r / 1.4142
    c.saveState()
    c.translate(cx, cy)
    c.rect(-a, -a, 2 * a, 2 * a, stroke=1, fill=0)
    c.rotate(45)
    c.rect(-a, -a, 2 * a, 2 * a, stroke=1, fill=0)
    c.restoreState()


class Avatar(Flowable):
    """Doira ichidagi rasm yoki bosh harflar."""

    def __init__(self, profile, size=36 * mm):
        super().__init__()
        self.profile, self.size = profile, size
        self.hAlign = "CENTER"
        self.img = None
        if profile.photo:
            try:
                from PIL import Image
                im = Image.open(profile.photo.path).convert("RGB")
                side = min(im.size)
                left, top = (im.width - side) // 2, (im.height - side) // 2
                self.img = ImageReader(im.crop((left, top, left + side, top + side)).resize((420, 420)))
            except Exception:
                self.img = None

    def wrap(self, aw, ah):
        return self.size, self.size

    def draw(self):
        c, s = self.canv, self.size
        r = s / 2
        c.saveState()
        p = c.beginPath()
        p.circle(r, r, r - 1.2 * mm)
        c.clipPath(p, stroke=0, fill=0)
        if self.img:
            c.drawImage(self.img, 0, 0, s, s)
        else:
            c.setFillColor(colors.HexColor("#1D3A85"))
            c.rect(0, 0, s, s, stroke=0, fill=1)
            u = self.profile.user
            initials = ((u.first_name or "")[:1] + (u.last_name or "")[:1] or (u.username or "?")[:1]).upper()
            c.setFillColor(colors.white)
            c.setFont(get_fonts()[1], s * 0.34)
            c.drawCentredString(r, r - s * 0.12, initials)
        c.restoreState()
        c.setStrokeColor(colors.white)
        c.setLineWidth(1.4)
        c.circle(r, r, r - 1.2 * mm, stroke=1, fill=0)


class Heading(Flowable):
    def __init__(self, title, width, color, line_color, size=10.5, line_alpha=1.0, line_after_text=False):
        super().__init__()
        self.title, self.width, self.color, self.line_color = title, width, color, line_color
        self.size, self.line_alpha, self.line_after_text = size, line_alpha, line_after_text

    def wrap(self, aw, ah):
        self.width = aw
        return aw, self.size + 9
    
    def draw(self):
        c = self.canv
        font = get_fonts()[1]
        c.setFillColor(self.color)
        c.setFont(font, self.size)
        c.drawString(0, 6, self.title)
        c.setStrokeColor(self.line_color)
        c.setLineWidth(0.7)
        if self.line_alpha < 1:
            c.setStrokeAlpha(self.line_alpha)
        if self.line_after_text:
            x0 = c.stringWidth(self.title, font, self.size) + 3 * mm
            y = 6 + self.size * 0.32
        else:
            x0, y = 0, 0.5
        c.line(x0, y, self.width, y)
        if self.line_alpha < 1:
            c.setStrokeAlpha(1)


class SkillBar(Flowable):
    def __init__(self, name, level, width):
        super().__init__()
        self.name, self.level, self.width = name, level, width

    def wrap(self, aw, ah):
        self.width = aw
        return aw, 9.5 * mm

    def draw(self):
        c = self.canv
        c.setFillColor(colors.white)
        c.setFont(get_fonts()[0], 8.6)
        c.drawString(0, 5.6 * mm, _clip(self.name, 34))
        gap = 1.2 * mm
        bw = (self.width - 3 * gap) / 4
        for i in range(4):
            on = i < (self.level or 0)
            c.setFillColor(TURQ if on else colors.white)
            if not on:
                c.setFillAlpha(0.22)
            c.roundRect(i * (bw + gap), 1.2 * mm, bw, 1.5 * mm, 0.7 * mm, stroke=0, fill=1)
            c.setFillAlpha(1)


class TimelineItem(Flowable):
    def __init__(self, paras, current=False, last=False):
        super().__init__()
        self.paras, self.current, self.last = paras, current, last
        self.pad = 5.5 * mm

    def wrap(self, aw, ah):
        cw = aw - self.pad
        self.hs = [p.wrap(cw, 10000)[1] for p in self.paras]
        self.h = sum(self.hs) + 3.2 * mm
        self.w = aw
        return aw, self.h

    def draw(self):
        c, h = self.canv, self.h
        if not self.last:
            c.setStrokeColor(LINE)
            c.setLineWidth(1.3)
            c.line(1.3 * mm, 0, 1.3 * mm, h - 2.4 * mm)
        c.setLineWidth(1.5)
        c.setStrokeColor(TURQ if self.current else BLUE)
        c.setFillColor(TURQ if self.current else colors.white)
        c.circle(1.3 * mm, h - 2.6 * mm, 1.35 * mm, stroke=1, fill=1)
        y = h
        for p, ph in zip(self.paras, self.hs):
            y -= ph
            p.drawOn(c, self.pad, y)


def build_cv_pdf(profile):
    regular, bold = get_fonts()
    user = profile.user

    def style(name, **kw):
        base = dict(fontName=regular, fontSize=9.4, leading=13, textColor=INK, alignment=TA_LEFT)
        base.update(kw)
        return ParagraphStyle(name, **base)

    s_name = style("name", fontName=bold, fontSize=24, leading=27, textColor=DEEP)
    s_role = style("role", fontSize=12, leading=15, textColor=BLUE)
    s_body = style("body", textColor=colors.HexColor("#2A3858"))
    s_item = style("item", fontName=bold, fontSize=10.6, leading=13.5)
    s_org = style("org", textColor=BLUE, fontSize=9.6, leading=12.5)
    s_when = style("when", textColor=MUTED, fontSize=8.4, leading=11)
    s_side = style("side", textColor=SOFT, fontSize=8.8, leading=12)
    s_li = style("li", textColor=colors.HexColor("#2A3858"), fontSize=9.2, leading=12.5)
    s_lang = style("lang", textColor=colors.white, fontSize=8.8, leading=12)
    s_lang_r = style("langr", textColor=LIGHT_TURQ, fontSize=8.4, leading=12, alignment=2)

    side_w = SIDE_W - 15 * mm
    main_w = PAGE_W - SIDE_W - 26 * mm

    # ---------------- yon panel
    side = [Avatar(profile), Spacer(1, 6 * mm), Heading("Aloqa", side_w, colors.white, colors.white, 10.5, 0.25), Spacer(1, 1 * mm)]
    contacts = [user.phone, user.email, profile.region,
                profile.birth_date.strftime("%d.%m.%Y") if profile.birth_date else ""]
    for value in contacts:
        if value:
            side.append(Paragraph(f'<font color="#1FA9A4">◆</font>&nbsp;&nbsp;{pdf_text(_clip(value, 60))}', s_side))
            side.append(Spacer(1, 1.6 * mm))
    skills = list(profile.skills.all())[:10]
    if skills:
        side += [Spacer(1, 3 * mm), Heading("Ko'nikmalar", side_w, colors.white, colors.white, 10.5, 0.25), Spacer(1, 1.5 * mm)]
        side += [SkillBar(sk.name, sk.level, side_w) for sk in skills]
    langs = list(profile.languages.all())[:8]
    if langs:
        side += [Spacer(1, 3 * mm), Heading("Tillar", side_w, colors.white, colors.white, 10.5, 0.25), Spacer(1, 1 * mm)]
        data = [[Paragraph(pdf_text(_clip(l.language, 24)), s_lang), Paragraph("Ona tili" if l.level == "native" else pdf_text(l.level), s_lang_r)] for l in langs]
        t = Table(data, colWidths=[side_w * 0.5, side_w * 0.5])
        t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                               ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
        side.append(t)
    side.append(FrameBreak())

    # ---------------- asosiy mazmun
    main = [Paragraph(pdf_text(_clip(user.full_name or user.username, 80)), s_name)]
    if profile.desired_position:
        main += [Spacer(1, 1.5 * mm), Paragraph(pdf_text(_clip(profile.desired_position, 120)), s_role)]
    if profile.about:
        main += [Spacer(1, 5 * mm), Paragraph(pdf_text(_clip(profile.about, 1400)), s_body)]

    def heading(title):
        return [Spacer(1, 5.5 * mm), Heading(title, main_w, DEEP, LINE, 11.5, line_after_text=True), Spacer(1, 1.5 * mm)]

    experiences = list(profile.experiences.all())[:8]
    if experiences:
        main += heading("Ish tajribasi")
        for i, e in enumerate(experiences):
            period = f"{e.start_date:%m.%Y} — {e.end_date:%m.%Y}" if e.end_date else f"{e.start_date:%m.%Y} — hozirgacha"
            paras = [Paragraph(pdf_text(_clip(e.position, 100)), s_item), Paragraph(pdf_text(_clip(e.company, 100)), s_org),
                     Paragraph(pdf_text(period), s_when)]
            if e.description:
                paras.append(Paragraph(pdf_text(_clip(e.description, 650)), s_body))
            main.append(TimelineItem(paras, current=not e.end_date, last=i == len(experiences) - 1))

    main += heading("Ta'lim")
    details = [x for x in [profile.faculty.name if profile.faculty else "",
                           f"{profile.course}-kurs" if profile.course and not profile.is_graduate else "",
                           f"bitirgan yil: {profile.graduation_year}" if profile.graduation_year else ""] if x]
    main.append(TimelineItem([
        Paragraph(pdf_text(_clip(profile.direction.name if profile.direction else "Ta'lim yo'nalishi ko'rsatilmagan", 120)), s_item),
        Paragraph("Samarqand iqtisodiyot va servis instituti", s_org),
        Paragraph(pdf_text(", ".join(details)), s_when)], current=not profile.is_graduate, last=True))

    certs = list(profile.certificates.all())[:10]
    if certs:
        main += heading("Sertifikatlar")
        for c in certs:
            year = f'&nbsp;&nbsp;<font color="#5A6985">{c.issue_date:%Y}</font>' if c.issue_date else ""
            line = f"<b>{pdf_text(_clip(c.title, 90))}</b>" + (f", {pdf_text(_clip(c.issuer, 70))}" if c.issuer else "")
            main += [Paragraph(f'<font color="#1B3A8F">◆</font>&nbsp;&nbsp;{line}{year}', s_li), Spacer(1, 1.4 * mm)]

    items = list(profile.portfolio.all())[:8]
    if items:
        main += heading("Portfolio")
        for p in items:
            line = f"<b>{pdf_text(_clip(p.title, 90))}</b>"
            if p.description:
                line += f". {pdf_text(_clip(p.description, 160))}"
            if p.url:
                line += f' <font color="#1B3A8F">{pdf_text(_clip(p.url, 80))}</font>'
            main += [Paragraph(f'<font color="#1B3A8F">◆</font>&nbsp;&nbsp;{line}', s_li), Spacer(1, 1.4 * mm)]

    # ---------------- sahifa shablonlari
    def draw_page(canv, doc):
        canv.saveState()
        canv.setFillColor(DEEP)
        canv.rect(0, 0, SIDE_W, PAGE_H, stroke=0, fill=1)
        canv.setStrokeColor(colors.white)
        canv.setLineWidth(0.7)
        cell = 20 * mm
        for row in range(6):
            canv.setStrokeAlpha(max(0.0, 0.17 - row * 0.03))
            for col in range(4):
                _star(canv, col * cell + cell / 2, PAGE_H - row * cell - cell / 2, 7.5 * mm)
        canv.setStrokeAlpha(1)
        canv.setFillColor(TURQ)
        canv.rect(SIDE_W, 0, 1.2 * mm, PAGE_H, stroke=0, fill=1)
        canv.setFillColor(MUTED)
        canv.setFont(regular, 7.4)
        canv.drawString(SIDE_W + 13 * mm, 8 * mm, "Karyera SIES platformasida yaratilgan")
        canv.drawRightString(PAGE_W - 13 * mm, 8 * mm, f"{doc.page}-sahifa")
        canv.restoreState()

    def frames(with_side):
        out = []
        if with_side:
            out.append(Frame(7.5 * mm, 12 * mm, side_w, PAGE_H - 24 * mm, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id="side"))
        out.append(Frame(SIDE_W + 13 * mm, 16 * mm, main_w, PAGE_H - 30 * mm, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id="main"))
        return out

    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4, title=f"CV — {user.full_name}", author="Karyera SIES",
                          leftMargin=0, rightMargin=0, topMargin=0, bottomMargin=0)
    doc.addPageTemplates([
        PageTemplate(id="first", frames=frames(True), onPage=draw_page, autoNextPageTemplate="later"),
        PageTemplate(id="later", frames=frames(False), onPage=draw_page),
    ])
    doc.build(side + main)
    return buf.getvalue()
