#!/usr/bin/env python3
"""Build the editable project presentation through LibreOffice Impress."""

import os
import time
import uno
from com.sun.star.awt import Point, Size
from com.sun.star.beans import PropertyValue


OUT_DIR = "/home/tenebris/cyber_project"
PPTX_PATH = os.path.join(OUT_DIR, "Feistel_Smart_Meter_Presentation.pptx")
PDF_PATH = os.path.join(OUT_DIR, "Feistel_Smart_Meter_Presentation.pdf")

W, H = 33867, 19050  # 16:9 in 1/100 mm

NAVY = 0x183B56
BLUE = 0x2E6685
TEAL = 0x2E7D78
COPPER = 0xC57A44
INK = 0x26323B
MID = 0x5B6973
PALE = 0xEAF0F3
PALE_TEAL = 0xE8F2F0
WARM = 0xF5EDE6
WHITE = 0xFFFFFF
PAPER = 0xFAF9F6
LINE = 0xB9C5CC
DOC = None


def prop(name, value):
    p = PropertyValue()
    p.Name = name
    p.Value = value
    return p


def connect():
    local_ctx = uno.getComponentContext()
    resolver = local_ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local_ctx
    )
    last = None
    for _ in range(40):
        try:
            return resolver.resolve(
                "uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext"
            )
        except Exception as exc:
            last = exc
            time.sleep(0.25)
    raise RuntimeError(f"Could not connect to LibreOffice: {last}")


def add_shape(slide, kind, x, y, w, h, fill=WHITE, line=LINE, radius=False):
    service = "com.sun.star.drawing.RectangleShape"
    if kind == "line":
        service = "com.sun.star.drawing.LineShape"
    shape = DOC.createInstance(service)
    shape.Position = Point(x, y)
    shape.Size = Size(w, h)
    if kind != "line":
        shape.FillStyle = 1
        shape.FillColor = fill
        shape.LineStyle = 0 if line is None else 1
        if line is not None:
            shape.LineColor = line
            shape.LineWidth = 20
        if radius:
            try:
                shape.CornerRadius = 180
            except Exception:
                pass
    else:
        shape.LineColor = line or LINE
        shape.LineWidth = 30
    slide.add(shape)
    return shape


def add_text(slide, text, x, y, w, h, size=16, color=INK, bold=False,
             font="Nimbus Sans", align=0, valign=0, fill=None, line=None,
             margin=140):
    shape = DOC.createInstance("com.sun.star.drawing.TextShape")
    shape.Position = Point(x, y)
    shape.Size = Size(w, h)
    shape.FillStyle = 0 if fill is None else 1
    if fill is not None:
        shape.FillColor = fill
    shape.LineStyle = 0 if line is None else 1
    if line is not None:
        shape.LineColor = line
    shape.TextLeftDistance = margin
    shape.TextRightDistance = margin
    shape.TextUpperDistance = margin
    shape.TextLowerDistance = margin
    shape.TextVerticalAdjust = valign
    slide.add(shape)
    shape.String = text
    cursor = shape.Text.createTextCursor()
    cursor.gotoEnd(True)
    cursor.CharFontName = font
    cursor.CharHeight = float(size)
    cursor.CharColor = color
    cursor.CharWeight = 150.0 if bold else 100.0
    cursor.ParaAdjust = align
    return shape


def set_bg(doc, slide, color=PAPER):
    bg = slide.Background
    if bg is None:
        bg = doc.createInstance("com.sun.star.drawing.Background")
    bg.FillStyle = 1
    bg.FillColor = color
    slide.Background = bg


def new_slide(doc):
    pages = doc.getDrawPages()
    if pages.getCount() == 1 and len(getattr(new_slide, "used", [])) == 0:
        slide = pages.getByIndex(0)
        new_slide.used = [True]
    else:
        slide = pages.insertNewByIndex(pages.getCount())
    slide.Width = W
    slide.Height = H
    set_bg(doc, slide)
    return slide


def header(slide, number, kicker, title, slide_no):
    add_text(slide, number, 1500, 850, 1300, 700, 11, COPPER, True)
    add_text(slide, kicker.upper(), 2800, 850, 10500, 700, 10, MID, True)
    add_text(slide, title, 1500, 1750, 29500, 1500, 26, NAVY, True)
    add_shape(slide, "line", 1500, 3450, 30800, 0, line=LINE)
    add_text(slide, f"{slide_no:02d}", 30700, 17800, 1200, 450, 9, MID, False, align=2)


def card(slide, title, body, x, y, w, h, accent=BLUE, fill=WHITE,
         title_size=14, body_size=11.5):
    add_shape(slide, "rect", x, y, w, h, fill=fill, line=LINE, radius=True)
    add_shape(slide, "rect", x, y, 180, h, fill=accent, line=None)
    add_text(slide, title, x + 500, y + 300, w - 850, 650,
             title_size, NAVY, True)
    add_text(slide, body, x + 500, y + 1050, w - 850, h - 1250,
             body_size, INK, False)


def pill(slide, text, x, y, w, color=PALE, text_color=NAVY):
    add_text(slide, text, x, y, w, 720, 10.5, text_color, True,
             align=1, valign=2, fill=color, line=color, margin=100)


def arrow(slide, x1, y1, x2, y2, color=BLUE):
    line = add_shape(slide, "line", x1, y1, x2 - x1, y2 - y1, line=color)
    try:
        line.LineEndName = "Arrow"
        line.LineEndWidth = 280
    except Exception:
        pass


def make_deck(doc):
    # 1 — Title
    s = new_slide(doc)
    add_shape(s, "rect", 0, 0, 1300, H, fill=TEAL, line=None)
    add_text(s, "MODERN CRYPTOGRAPHY · MINI PROJECT", 2400, 2150, 22000, 700,
             11, TEAL, True)
    add_text(s, "Lightweight Feistel-Based\nSmart Meter Encryption Suite",
             2400, 3450, 27800, 3300, 30, NAVY, True)
    add_shape(s, "rect", 2400, 7200, 2500, 130, fill=COPPER, line=None)
    add_text(s, "Problem analysis, feasibility, methodology and algorithm relevance",
             2400, 7850, 27000, 950, 16, MID, False)
    add_text(s, "Smart-grid security · Symmetric-key cryptography · Web simulation",
             2400, 14650, 27000, 650, 11, NAVY, True)
    add_text(s, "Academic Year: __________", 2400, 16000, 9000, 600, 10.5, MID)
    add_text(s, "01", 30700, 17800, 1200, 450, 9, MID, align=2)

    # 2 — Details and team template
    s = new_slide(doc)
    header(s, "00", "Project Information", "Project and Team Details", 2)
    card(s, "Project", "Lightweight Feistel-Based Smart Meter Encryption Suite",
         1500, 4200, 14500, 2300, TEAL, PALE_TEAL, 14, 13)
    card(s, "Course / Subject", "Modern Cryptography\nProgramme: ____________________\nSection: ______________________",
         17300, 4200, 15000, 2300, COPPER, WARM, 14, 11.5)
    add_text(s, "TEAM MEMBERS", 1500, 7400, 9000, 600, 11, MID, True)
    cols = [1500, 3300, 11500, 21300]
    widths = [1800, 8200, 9800, 11000]
    labels = ["No.", "Name", "Enrollment No.", "Primary Module"]
    for x, w, label in zip(cols, widths, labels):
        add_text(s, label, x, 8200, w, 750, 10.5, WHITE, True,
                 valign=2, fill=NAVY, line=WHITE)
    for row in range(5):
        y = 8950 + row * 1250
        values = [str(row + 1), "________________", "________________", "________________"]
        for x, w, value in zip(cols, widths, values):
            add_text(s, value, x, y, w, 1050, 10.5, INK, False,
                     valign=2, fill=WHITE, line=LINE)

    # 3 — Problem domain
    s = new_slide(doc)
    header(s, "01", "Problem Domain", "Why Smart-Meter Telemetry Needs Protection", 3)
    add_text(s, "Residential meters send small, frequent usage reports to a utility gateway. "
                "These readings affect billing and can also reveal household activity patterns.",
             1500, 4050, 30500, 1250, 14, INK)
    stages = [
        ("Meter", "Measures energy\nusage"),
        ("Network", "Carries periodic\ntelemetry"),
        ("Gateway", "Validates and\ndecrypts"),
        ("Utility", "Stores data for\nbilling"),
    ]
    xs = [1700, 9250, 16800, 24350]
    for i, ((name, desc), x) in enumerate(zip(stages, xs)):
        add_shape(s, "rect", x, 6500, 5700, 3100, fill=WHITE, line=LINE, radius=True)
        add_text(s, f"0{i+1}", x + 350, 6800, 900, 600, 10, COPPER, True)
        add_text(s, name, x + 350, 7550, 4700, 700, 15, NAVY, True)
        add_text(s, desc, x + 350, 8350, 4700, 850, 11, MID)
        if i < 3:
            arrow(s, x + 5850, 8000, x + 7100, 8000, TEAL)
    card(s, "Security issue", "If the link is observed or modified, an attacker may infer behaviour, alter readings or replay an old report.",
         1500, 11200, 14700, 3100, COPPER, WARM, 14, 12)
    card(s, "Engineering issue", "The meter has limited memory, processing capacity and energy. Protection must therefore be measurable as well as correct.",
         17600, 11200, 14700, 3100, TEAL, PALE_TEAL, 14, 12)

    # 4 — Analysis and research question
    s = new_slide(doc)
    header(s, "01", "Problem Domain", "Problem Definition and Study Boundaries", 4)
    card(s, "Core problem", "Design an understandable 8-bit Feistel cipher for a constrained smart-meter model, then measure how its cost and diffusion change with the number of rounds.",
         1500, 4100, 30800, 2400, TEAL, PALE_TEAL, 15, 13)
    questions = [
        ("Q1", "Correctness", "Can every 8-bit reading be encrypted and recovered with the same key?"),
        ("Q2", "Diffusion", "How close does the output come to changing four of eight bits after one input-bit flip?"),
        ("Q3", "Cost", "What time and estimated energy are required by 4, 6 and 8 rounds?"),
    ]
    qx = [1500, 11850, 22200]
    for (q, title, body), x in zip(questions, qx):
        add_shape(s, "rect", x, 7450, 9300, 4500, fill=WHITE, line=LINE, radius=True)
        pill(s, q, x + 450, 7800, 1300, WARM, COPPER)
        add_text(s, title, x + 450, 8850, 8300, 650, 15, NAVY, True)
        add_text(s, body, x + 450, 9800, 8300, 1500, 11.5, INK)
    add_text(s, "Scope boundary", 1500, 13250, 4200, 550, 11, COPPER, True)
    add_text(s, "This is a teaching and evaluation model. An 8-bit block and a short key are not suitable for real billing security; production meters should use standard authenticated encryption.",
             1500, 13900, 30800, 1600, 12.5, INK, False, fill=WARM, line=WARM, margin=350)

    # 5 — Existing systems review
    s = new_slide(doc)
    header(s, "02", "Existing Systems", "Where the Proposed Cipher Fits", 5)
    add_text(s, "Existing approaches provide the baseline for the project; they are not treated as direct equivalents.",
             1500, 4000, 30000, 700, 13, MID)
    data = [
        ("Approach", "Strength", "Limitation in this study"),
        ("Unencrypted / checksum only", "Very low processing cost", "No confidentiality; checksum is not authentication"),
        ("DES", "Classic Feistel reference with 16 rounds", "56-bit key is obsolete; 64-bit implementation is larger"),
        ("AES-128", "Modern standard; strong and widely supported", "More complex than an 8-bit teaching model"),
        ("Lightweight standard ciphers", "Designed for constrained devices", "Less transparent for a short classroom implementation"),
        ("Proposed 8-bit Feistel", "Small, traceable and easy to benchmark", "Tiny block/key space; demonstration only"),
    ]
    cx = [1500, 10300, 20100]
    cw = [8800, 9800, 12200]
    for r, row in enumerate(data):
        y = 5200 + r * 1900
        for c, value in enumerate(row):
            fill = NAVY if r == 0 else (PALE_TEAL if r == 5 else WHITE)
            color = WHITE if r == 0 else INK
            bold = r == 0 or c == 0
            add_text(s, value, cx[c], y, cw[c], 1650, 10.8, color, bold,
                     valign=2, fill=fill, line=LINE, margin=230)
    add_text(s, "Reference baseline: DES structure (FIPS 46-3) and AES (FIPS 197).",
             1500, 16900, 24000, 450, 8.5, MID)

    # 6 — Feasibility
    s = new_slide(doc)
    header(s, "02", "Existing Systems", "Project Feasibility", 6)
    feas = [
        ("Technical", "Python supports direct bit operations. FastAPI exposes the simulation, while browser charts show internal states and results.", TEAL, PALE_TEAL),
        ("Computational", "The complete input space has only 256 blocks, so exhaustive correctness tests and large avalanche samples are practical.", BLUE, PALE),
        ("Hardware", "The first version uses a documented energy model. C, Wokwi or Arduino measurement can be added without changing the cipher design.", COPPER, WARM),
        ("Schedule", "Modules are independent enough for five members to work in parallel, with shared test vectors used during integration.", NAVY, WHITE),
    ]
    positions = [(1500, 4300), (17100, 4300), (1500, 9400), (17100, 9400)]
    for (title, body, accent, fill), (x, y) in zip(feas, positions):
        card(s, title, body, x, y, 14700, 4000, accent, fill, 15, 12)
    add_text(s, "Main risks", 1500, 14600, 3000, 550, 11, COPPER, True)
    pill(s, "Unfair timing comparison", 4700, 14480, 6000, WARM, INK)
    pill(s, "Confusing estimates with measurements", 11100, 14480, 8300, WARM, INK)
    pill(s, "Overstating security", 19800, 14480, 5500, WARM, INK)
    pill(s, "Integration mismatch", 25700, 14480, 5600, WARM, INK)
    add_text(s, "Control: identical test vectors, repeated timing runs, labelled estimates and explicit limitations.",
             1500, 15850, 30800, 900, 11.5, INK, True, fill=PALE, line=PALE, margin=300)

    # 7 — Objectives
    s = new_slide(doc)
    header(s, "03", "Proposed Work", "Objectives and Expected Outputs", 7)
    objectives = [
        ("01", "Build the cipher", "Implement 8-bit encryption, decryption and a configurable 4/6/8-round engine."),
        ("02", "Simulate meter data", "Generate time-based kWh readings, quantize them and construct transmission packets."),
        ("03", "Make it observable", "Display plaintext, subkeys and left/right values for every round in the web UI."),
        ("04", "Evaluate diffusion", "Measure plaintext avalanche, key sensitivity and output-bit dependencies."),
        ("05", "Measure cost", "Report repeatable execution-time and estimated energy results for each round count."),
        ("06", "Demonstrate controls", "Show sequence validation, replay rejection and integrity checking around the cipher."),
    ]
    positions = [(1500, 4300), (11850, 4300), (22200, 4300),
                 (1500, 10200), (11850, 10200), (22200, 10200)]
    for (num, title, body), (x, y) in zip(objectives, positions):
        add_shape(s, "rect", x, y, 9300, 4600, fill=WHITE, line=LINE, radius=True)
        add_text(s, num, x + 400, y + 350, 1200, 700, 12, COPPER, True)
        add_text(s, title, x + 400, y + 1300, 8200, 700, 14, NAVY, True)
        add_text(s, body, x + 400, y + 2300, 8200, 1700, 11.2, INK)

    # 8 — Methodology
    s = new_slide(doc)
    header(s, "03", "Proposed Work", "Methodology", 8)
    steps = [
        ("1", "Specify", "Block, key, S-box, permutation and output convention"),
        ("2", "Implement", "Reference cipher in Python with a round trace"),
        ("3", "Verify", "Known-answer, boundary and exhaustive round-trip tests"),
        ("4", "Simulate", "Meter readings, quantization and packet transmission"),
        ("5", "Evaluate", "Timing, avalanche, key sensitivity and energy estimate"),
        ("6", "Present", "FastAPI dashboard, charts and final comparison"),
    ]
    for i, (num, name, desc) in enumerate(steps):
        x = 1500 + i * 5100
        add_shape(s, "rect", x, 4550, 4200, 5200,
                  fill=PALE_TEAL if i % 2 == 0 else WHITE, line=LINE, radius=True)
        pill(s, num, x + 1200, 4900, 1800, WARM, COPPER)
        add_text(s, name, x + 300, 6100, 3600, 650, 14, NAVY, True, align=1)
        add_text(s, desc, x + 350, 7100, 3500, 1900, 10.5, INK, align=1)
        if i < 5:
            arrow(s, x + 4250, 7100, x + 5000, 7100, TEAL)
    card(s, "Experimental controls", "Use the same input sets for every round count; time only the cipher call; repeat runs; store raw results; report mean and variation; keep estimated and measured energy separate.",
         1500, 11300, 19800, 3300, TEAL, PALE_TEAL, 14, 11.5)
    card(s, "Success criteria", "Correct recovery for all 256 plaintext blocks; reproducible benchmarks; avalanche results shown by round count; working end-to-end demonstration.",
         22200, 11300, 10100, 3300, COPPER, WARM, 14, 11.3)

    # 9 — Algorithm relevance
    s = new_slide(doc)
    header(s, "04", "Algorithms and Techniques", "Why These Techniques Are Relevant", 9)
    add_text(s, "The design separates the experimental cipher from the controls needed by a communication system.",
             1500, 4050, 30500, 700, 13, MID)
    core = [
        ("Feistel network", "Provides reversible encryption while allowing a simple custom round function."),
        ("S-box substitution", "Introduces non-linearity so output changes are not a direct linear mapping of the input."),
        ("Bit permutation", "Moves S-box output bits to improve diffusion across later rounds."),
        ("Rotating key schedule", "Derives a different 4-bit subkey for each round with low implementation cost."),
    ]
    support = [
        ("Nonce / IV", "Reduces visible repetition when similar readings are encrypted."),
        ("Sequence number", "Allows the gateway to identify stale or replayed reports."),
        ("Integrity tag", "Detects packet modification; it remains separate from encryption."),
    ]
    add_text(s, "CORE CIPHER", 1500, 5200, 8000, 550, 10.5, TEAL, True)
    for i, (title, body) in enumerate(core):
        y = 6000 + i * 2500
        card(s, title, body, 1500, y, 18700, 2050, TEAL, WHITE, 13, 10.8)
    add_text(s, "SUPPORTING CONTROLS", 21700, 5200, 9500, 550, 10.5, COPPER, True)
    for i, (title, body) in enumerate(support):
        y = 6000 + i * 3250
        card(s, title, body, 21700, y, 10600, 2700, COPPER, WARM, 13, 10.8)
    add_text(s, "Encryption provides confidentiality; it does not provide integrity or replay protection by itself.",
             21700, 15900, 10600, 1000, 10.8, NAVY, True, fill=PALE, line=PALE, margin=260)

    # 10 — Relevance and evaluation link
    s = new_slide(doc)
    header(s, "04", "Algorithms and Techniques", "Link Between Design Choices and Evaluation", 10)
    data = [
        ("Design choice", "Reason for inclusion", "How it is evaluated"),
        ("8-bit block", "Matches a quantized sample and keeps internals visible", "Exhaustive input tests; repetition demo"),
        ("4 / 6 / 8 rounds", "Creates a clear cost-versus-diffusion variable", "Timing, energy estimate and avalanche score"),
        ("4-bit S-box", "Adds non-linearity with a small lookup table", "Input/output difference heatmap"),
        ("Permutation", "Spreads changed bits into later rounds", "Per-round output-bit sensitivity"),
        ("16-bit baseline key", "Simple schedule for the experiment", "Key-flip sensitivity and brute-force limitation"),
    ]
    cx = [1500, 9900, 22000]
    cw = [8400, 12100, 10300]
    for r, row in enumerate(data):
        y = 4200 + r * 1950
        for c, value in enumerate(row):
            fill = NAVY if r == 0 else (PALE_TEAL if r % 2 else WHITE)
            color = WHITE if r == 0 else INK
            add_text(s, value, cx[c], y, cw[c], 1700, 10.6, color,
                     r == 0 or c == 0, valign=2, fill=fill, line=LINE, margin=220)
    add_text(s, "Expected conclusion", 1500, 16500, 4300, 500, 10.5, COPPER, True)
    add_text(s, "More rounds should improve diffusion but increase processing cost. The value of the project is the measured trade-off—not a claim that the custom cipher is production-ready.",
             5700, 16150, 26600, 1150, 12, NAVY, True, fill=WARM, line=WARM, margin=280)


def main():
    global DOC
    ctx = connect()
    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    doc = desktop.loadComponentFromURL("private:factory/simpress", "_blank", 0, ())
    DOC = doc
    make_deck(doc)

    pptx_url = uno.systemPathToFileUrl(PPTX_PATH)
    pdf_url = uno.systemPathToFileUrl(PDF_PATH)
    doc.storeAsURL(pptx_url, (prop("FilterName", "Impress MS PowerPoint 2007 XML"),))
    doc.storeToURL(pdf_url, (prop("FilterName", "impress_pdf_Export"),))
    doc.close(True)
    print(PPTX_PATH)
    print(PDF_PATH)


if __name__ == "__main__":
    main()
