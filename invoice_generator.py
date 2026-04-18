"""
invoice_generator.py
====================
Generates Tax Invoices that exactly match the Metis Eduventures trainer
invoice format (Pavithra A / Saiful Hoda samples).

Usage
-----
    python invoice_generator.py                    # generates both sample invoices
    python invoice_generator.py --json data.json   # generate from JSON file

Dependencies
------------
    pip install reportlab
"""

import json
import argparse
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm

# ── Page constants ────────────────────────────────────────────────────────────
PW, PH = A4                        # 595.27 x 841.89 pts
LM = 15 * mm                       # left margin
RM = PW - 15 * mm                  # right margin
TM = PH - 12 * mm                  # top margin
BM = 12 * mm                       # bottom margin
CW = RM - LM                       # content width

GREY  = colors.HexColor("#D9D9D9")
BLACK = colors.black
WHITE = colors.white
LIGHT = colors.HexColor("#F2F2F2")


# ── Number → words (Indian system) ───────────────────────────────────────────
def _say(n: int) -> str:
    if n == 0:
        return "Zero"
    ones  = ["","One","Two","Three","Four","Five","Six","Seven","Eight","Nine",
             "Ten","Eleven","Twelve","Thirteen","Fourteen","Fifteen","Sixteen",
             "Seventeen","Eighteen","Nineteen"]
    tens_ = ["","","Twenty","Thirty","Forty","Fifty","Sixty","Seventy","Eighty","Ninety"]
    def say(x):
        if x == 0:    return ""
        if x < 20:    return ones[x]
        if x < 100:   return tens_[x//10] + (" " + ones[x%10] if x%10 else "")
        if x < 1000:  return ones[x//100]+" Hundred"+(" "+say(x%100) if x%100 else "")
        if x < 1e5:   return say(x//1000)+" Thousand"+(" "+say(x%1000) if x%1000 else "")
        if x < 1e7:   return say(x//100000)+" Lakh"+(" "+say(x%100000) if x%100000 else "")
        return say(x//10000000)+" Crore"+(" "+say(x%10000000) if x%10000000 else "")
    return say(int(n))

def amount_words(n: float) -> str:
    return f"Rupees {_say(int(round(n)))} Only"


# ── Low-level draw helpers ────────────────────────────────────────────────────
def draw_text(c, x, y, text, size=9, bold=False, align="left", max_width=None):
    font = "Helvetica-Bold" if bold else "Helvetica"
    c.setFont(font, size)
    text = str(text) if text is not None else ""
    if max_width:
        # wrap long text
        words = text.split()
        lines, cur = [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if c.stringWidth(test, font, size) <= max_width:
                cur = test
            else:
                if cur: lines.append(cur)
                cur = w
        if cur: lines.append(cur)
        lh = size * 1.4
        for i, ln in enumerate(lines):
            draw_text(c, x, y - i*lh, ln, size, bold, align)
        return len(lines)
    if align == "center":
        c.drawCentredString(x, y, text)
    elif align == "right":
        c.drawRightString(x, y, text)
    else:
        c.drawString(x, y, text)
    return 1

def hline(c, x1, y, x2, width=0.5):
    c.setLineWidth(width)
    c.line(x1, y, x2, y)

def vline(c, x, y1, y2, width=0.5):
    c.setLineWidth(width)
    c.line(x, y1, x, y2)

def rect(c, x, y, w, h, fill_color=None, stroke=True):
    c.setLineWidth(0.5)
    if fill_color:
        c.setFillColor(fill_color)
        c.rect(x, y, w, h, stroke=int(stroke), fill=1)
        c.setFillColor(BLACK)
    else:
        c.rect(x, y, w, h, stroke=int(stroke), fill=0)

def fmt_num(n) -> str:
    """Format number with Indian comma style."""
    try:
        n = float(n)
        if n == int(n):
            n = int(n)
            s = f"{n:,}"
        else:
            s = f"{n:,.2f}"
        return s
    except:
        return str(n)


# ── Main invoice generator ────────────────────────────────────────────────────
def generate_invoice(data: dict, output_path: str):
    """
    Generate a Tax Invoice PDF matching the Metis Eduventures trainer format.

    Required keys in `data`:
      trainer_name, address, pan
      invoice_month, invoice_date, training_dates, program_name
      billed_to_name, billed_to_address, billed_to_gstin
      sessions: list of dicts with keys:
        description, hsn_code, gst_rate (%), quantity, rate_per_unit
      phone, email
      account_holder, account_number, ifsc, account_type, bank_name

    Optional keys:
      gstin          (default "NA")
      po_number
      invoice_number
      tds_percent    (default 0 — if set e.g. 10, shows deduction row)
      unregistered_note  (custom GST disclaimer text)
      show_pan_in_bank   (bool, default True)
    """
    c = canvas.Canvas(output_path, pagesize=A4)
    c.setTitle("Tax Invoice")
    y = TM   # current Y cursor (moves downward)

    def gap(n=4):
        nonlocal y
        y -= n * mm

    # ══════════════════════════════════════════════════════════════════════════
    # 1. TITLE
    # ══════════════════════════════════════════════════════════════════════════
    draw_text(c, PW/2, y, "Tax Invoice", size=16, bold=True, align="center")
    y -= 7 * mm
    hline(c, LM, y, RM, width=1)
    y -= 4 * mm

    # ══════════════════════════════════════════════════════════════════════════
    # 2. META ROWS  (Name / Invoice Month / PO / Program / Invoice Date / Training Dates)
    # ══════════════════════════════════════════════════════════════════════════
    meta_rows = [
        ("Name:", data["trainer_name"],
         "Invoice Number:", data.get("invoice_number", "")),
        ("Invoice Month:", data["invoice_month"],
         "Invoice Date:", data["invoice_date"]),
        ("PO Number:", data.get("po_number", ""),
         "Training Dates:", data["training_dates"]),
        ("Program Name:", data["program_name"],
         "", ""),
    ]
    col1x, col2x, col3x, col4x = LM, LM+35*mm, LM+CW*0.52, LM+CW*0.52+32*mm
    row_h = 5.5 * mm
    for (k1, v1, k2, v2) in meta_rows:
        if not k1 and not k2:
            continue
        draw_text(c, col1x, y, k1, bold=True)
        draw_text(c, col2x, y, v1, max_width=(col3x - col2x - 2*mm))
        if k2:
            draw_text(c, col3x, y, k2, bold=True)
            draw_text(c, col4x, y, v2, max_width=(RM - col4x))
        y -= row_h

    gap(2)
    hline(c, LM, y, RM)
    gap(3)

    # ══════════════════════════════════════════════════════════════════════════
    # 3. BILLED BY / BILLED TO
    # ══════════════════════════════════════════════════════════════════════════
    half = CW / 2
    by_x  = LM
    to_x  = LM + half + 3*mm
    sec_y = y

    draw_text(c, by_x, y, "Billed By", bold=True, size=10)
    draw_text(c, to_x, y, "Billed To", bold=True, size=10)
    y -= 5.5 * mm

    draw_text(c, by_x, y, f"Name: {data['trainer_name']}")
    draw_text(c, to_x, y, data["billed_to_name"])
    y -= 5 * mm

    # Address — may wrap
    addr_lines_by = _wrap(c, data["address"], half - 15*mm, 9)
    addr_lines_to = _wrap(c, f"Address: {data['billed_to_address']}", half - 5*mm, 9)

    for i, line in enumerate(addr_lines_by):
        draw_text(c, by_x, y - i*5*mm, ("Address: " if i==0 else "          ") + line if i < 1 else line)
    addr_y_by = y - len(addr_lines_by) * 5*mm

    for i, line in enumerate(addr_lines_to):
        draw_text(c, to_x, y - i*5*mm, line)
    addr_y_to = y - len(addr_lines_to) * 5*mm

    y = min(addr_y_by, addr_y_to) - 3*mm

    gstin_by = data.get("gstin", "NA")
    pan_by   = data.get("pan", "")

    if gstin_by and gstin_by != "NA":
        draw_text(c, by_x, y, f"GSTIN: {gstin_by}")
    if pan_by:
        draw_text(c, by_x, y if (not gstin_by or gstin_by=="NA") else y-5*mm,
                  f"PAN: {pan_by}")
        if gstin_by and gstin_by != "NA":
            y -= 5*mm

    billed_to_gstin = data.get("billed_to_gstin", "")
    if billed_to_gstin:
        draw_text(c, to_x, y, f"GSTIN: {billed_to_gstin}")

    y -= 7 * mm
    hline(c, LM, y, RM, width=0.8)
    gap(3)

    # ══════════════════════════════════════════════════════════════════════════
    # 4. SERVICE TABLE
    # ══════════════════════════════════════════════════════════════════════════
    # Detect columns based on sessions
    sessions = data.get("sessions", [])
    has_commercial = any(s.get("commercial") for s in sessions)

    if has_commercial:
        # Saiful format: No | Description | HSN | GST | Commercial | Qty | Amount | GST Rate | Total
        headers = ["No.", "Service Description", "HSN\nCode", "GST", "Commercial", "Qty", "Amount", "GST\nRate", "Total"]
        col_ws  = [8*mm, 52*mm, 18*mm, 12*mm, 22*mm, 12*mm, 20*mm, 16*mm, 18*mm]
    else:
        # Pavithra format: No | Description | HSN | GST Rate | Qty | Rate | Amount | Total Amount | IGST | Total
        headers = ["No.", "Service Description", "HSN\nCode", "GST\nRate", "Qty", "Rate", "Amount", "Total\nAmount", "IGST", "Total"]
        col_ws  = [8*mm, 42*mm, 16*mm, 14*mm, 12*mm, 16*mm, 16*mm, 18*mm, 14*mm, 16*mm]

    tbl_top = y
    row_ht  = 8 * mm
    hdr_ht  = 10 * mm

    # header background
    rect(c, LM, y - hdr_ht, CW, hdr_ht, fill_color=GREY)
    hline(c, LM, y, RM)

    # header text
    cx = LM
    for i, (hdr, cw) in enumerate(zip(headers, col_ws)):
        cx_mid = cx + cw/2
        lines = hdr.split("\n")
        line_h = 3.5 * mm
        start_y = y - hdr_ht/2 + (len(lines)-1)*line_h/2
        for j, ln in enumerate(lines):
            draw_text(c, cx_mid, start_y - j*line_h, ln, size=8, bold=True, align="center")
        if i < len(col_ws)-1:
            vline(c, cx+cw, y, y-hdr_ht)
        cx += cw

    y -= hdr_ht
    hline(c, LM, y, RM)

    subtotal = 0
    total_gst = 0

    for idx, s in enumerate(sessions, 1):
        qty     = float(s.get("quantity", 0))
        rate    = float(s.get("rate_per_unit", 0))
        amount  = round(qty * rate)
        gst_pct = float(str(s.get("gst_rate", 0)).replace("%","").strip())
        gst_amt = round(amount * gst_pct / 100)
        total   = amount + gst_amt
        subtotal  += amount
        total_gst += gst_amt

        if has_commercial:
            commercial = s.get("commercial", "")
            row_vals = [
                str(idx),
                s.get("description",""),
                s.get("hsn_code","NA"),
                s.get("gst_label","NA"),
                commercial,
                fmt_num(qty),
                fmt_num(amount),
                f"{int(gst_pct)}%",
                fmt_num(total),
            ]
        else:
            row_vals = [
                str(idx),
                s.get("description",""),
                s.get("hsn_code","NA"),
                f"{int(gst_pct)}%",
                fmt_num(qty),
                fmt_num(rate),
                fmt_num(amount),
                fmt_num(amount),
                fmt_num(gst_amt),
                fmt_num(total),
            ]

        cx = LM
        for i, (val, cw) in enumerate(zip(row_vals, col_ws)):
            cx_mid = cx + cw/2
            if i == 1:   # description — left-align with padding
                draw_text(c, cx+2*mm, y - row_ht*0.55, val, size=8, max_width=cw-3*mm)
            else:
                draw_text(c, cx_mid, y - row_ht*0.55, val, size=8, align="center")
            if i < len(col_ws)-1:
                vline(c, cx+cw, y, y-row_ht)
            cx += cw

        y -= row_ht
        hline(c, LM, y, RM)

    # outer border for table
    rect(c, LM, y, CW, tbl_top - y)
    gap(3)

    # ══════════════════════════════════════════════════════════════════════════
    # 5. TOTALS SECTION
    # ══════════════════════════════════════════════════════════════════════════
    grand_total = subtotal + total_gst
    words_full  = amount_words(grand_total)

    left_w  = CW * 0.60
    right_w = CW * 0.40
    right_x = LM + left_w

    # "Total in words" row
    tot_row_h = 6 * mm
    rect(c, LM, y - tot_row_h, CW, tot_row_h, fill_color=LIGHT)
    draw_text(c, LM+2*mm, y - tot_row_h*0.6,
              f"Total (in words): {words_full}", size=8.5, bold=False,
              max_width=left_w - 4*mm)
    vline(c, right_x, y, y-tot_row_h)

    label_x  = right_x + 2*mm
    value_x  = RM - 2*mm
    draw_text(c, label_x, y - tot_row_h*0.6, "Amount", size=9, bold=True)
    draw_text(c, value_x, y - tot_row_h*0.6, fmt_num(subtotal), size=9, align="right")
    y -= tot_row_h
    hline(c, LM, y, RM)

    # GST / IGST row
    gst_label = "IGST" if not has_commercial else "GST"
    rect(c, right_x, y-tot_row_h, right_w, tot_row_h)
    draw_text(c, label_x, y - tot_row_h*0.6, gst_label, size=9, bold=True)
    draw_text(c, value_x, y - tot_row_h*0.6, fmt_num(total_gst), size=9, align="right")
    y -= tot_row_h
    hline(c, LM, y, RM)

    # Total Invoice Value row
    rect(c, right_x, y-tot_row_h, right_w, tot_row_h, fill_color=GREY)
    draw_text(c, label_x, y - tot_row_h*0.6, "Total Invoice Value", size=9, bold=True)
    draw_text(c, value_x, y - tot_row_h*0.6, fmt_num(grand_total), size=9, bold=True, align="right")
    y -= tot_row_h
    hline(c, LM, y, RM)
    gap(2)

    # ── TDS deduction row (optional) ──────────────────────────────────────────
    tds_pct = float(data.get("tds_percent", 0))
    if tds_pct:
        tds_amt   = round(grand_total * tds_pct / 100)
        net_total = grand_total - tds_amt
        net_words = amount_words(net_total)

        rect(c, LM, y-tot_row_h, CW, tot_row_h, fill_color=LIGHT)
        draw_text(c, LM+2*mm, y-tot_row_h*0.6,
                  f"Total (in words) After {int(tds_pct)}% Deduction : {net_words}",
                  size=8.5, max_width=left_w - 4*mm)
        vline(c, right_x, y, y-tot_row_h)
        draw_text(c, label_x, y-tot_row_h*0.6,
                  f"After {int(tds_pct)}% Deduction Amount", size=8.5, bold=True)
        draw_text(c, value_x, y-tot_row_h*0.6, fmt_num(net_total), size=9, bold=True, align="right")
        y -= tot_row_h
        hline(c, LM, y, RM)
        gap(2)

    # ══════════════════════════════════════════════════════════════════════════
    # 6. ADDITIONAL INFORMATION
    # ══════════════════════════════════════════════════════════════════════════
    draw_text(c, LM, y, "Additional Information:", bold=True, size=9)
    y -= 5 * mm

    default_note = (
        f"I, {data['trainer_name']}, do not hold a GSTIN number & not crossing "
        "turnover as per threshold limit prescribed under GST laws & is unregistered/"
    )
    note = data.get("unregistered_note", default_note)
    note_lines = _wrap(c, note, CW, 8.5)
    for ln in note_lines:
        draw_text(c, LM, y, ln, size=8.5)
        y -= 5 * mm
    gap(1)

    # ── Bank / contact details table ──────────────────────────────────────────
    col_a = 28*mm
    col_b = CW/2 - col_a
    col_c = 38*mm
    col_d = CW/2 - col_c
    c1x = LM
    c2x = LM + col_a
    c3x = LM + CW/2
    c4x = LM + CW/2 + col_c

    bank_rows = [
        ("Name:", data["trainer_name"],
         "Account Holder Name:", data["account_holder"]),
        ("Number:", data["phone"],
         "Account Number:", data["account_number"]),
        ("Email ID:", data["email"],
         "IFSC Code:", data["ifsc"]),
        ("", "",
         "Account Type:", data.get("account_type", "")),
        ("", "",
         "Bank Name:", data["bank_name"]),
    ]
    if data.get("show_pan_in_bank", True) and data.get("pan"):
        bank_rows.insert(3, ("", "", "Account Holder PAN:", data["pan"]))

    bk_row_h = 5.5 * mm
    bk_top   = y
    for k1, v1, k2, v2 in bank_rows:
        if k1:
            draw_text(c, c1x, y - bk_row_h*0.55, k1, bold=True, size=8.5)
            draw_text(c, c2x, y - bk_row_h*0.55, v1, size=8.5, max_width=col_b - 2*mm)
        draw_text(c, c3x, y - bk_row_h*0.55, k2, bold=True, size=8.5)
        draw_text(c, c4x, y - bk_row_h*0.55, v2, size=8.5, max_width=col_d - 2*mm)
        y -= bk_row_h

    rect(c, LM, y, CW, bk_top - y)
    gap(5)

    # ══════════════════════════════════════════════════════════════════════════
    # 7. SIGNATURE LINE
    # ══════════════════════════════════════════════════════════════════════════
    draw_text(c, RM, y, data["trainer_name"], align="right", bold=True)
    y -= 4 * mm
    draw_text(c, RM, y, "Signature", align="right", size=8.5)

    c.save()
    print(f"✓ Invoice saved: {output_path}")


# ── Internal: pure-text word-wrapper ─────────────────────────────────────────
def _wrap(c, text: str, max_w: float, size: int) -> list:
    font = "Helvetica"
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if c.stringWidth(test, font, size) <= max_w:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines or [""]


# ══════════════════════════════════════════════════════════════════════════════
# SAMPLE DATA — mirrors both real invoices
# ══════════════════════════════════════════════════════════════════════════════

PAVITHRA_DATA = {
    "trainer_name":       "Pavithra A",
    "address":            "127, South street, Kongampalayam, Chithode - 638102",
    "gstin":              "NA",
    "pan":                "EXZPP9764C",
    "email":              "pavithraappusamy37@gmail.com",
    "phone":              "6369106458",
    "account_holder":     "Pavithra A",
    "account_number":     "20406057209",
    "ifsc":               "SBIN0018642",
    "account_type":       "Savings Account",
    "bank_name":          "State Bank Of India",
    "show_pan_in_bank":   False,

    "invoice_month":      "Mar 2026",
    "invoice_date":       "11th Apr",
    "invoice_number":     "INV-001",
    "training_dates":     "01st Mar - 15th Mar",
    "program_name":       "TNSDC Digital Marketing",

    "billed_to_name":     "Metis Eduventures Private Limited",
    "billed_to_address":  "2nd floor, 207A-208, Tower A, Unitech Cyber Park, Sec-39 Gurgaon, Haryana - 122001",
    "billed_to_gstin":    "06AAHCM7263M1ZZ",

    "tds_percent":        0,

    "sessions": [
        {
            "description":    "Live session",
            "hsn_code":       "NA",
            "gst_rate":       0,
            "quantity":       0.5,
            "rate_per_unit":  35000,
        }
    ],

    "unregistered_note": (
        "I, Pavithra A, do not hold a GSTIN number & not crossing turnover as per "
        "threshold limit prescribed under GST laws & is unregistered/"
    ),
}

SAIFUL_DATA = {
    "trainer_name":       "Saiful Hoda",
    "address":            "Room – 205; Hello World, HBR Layout, Bangalore, Karnataka",
    "gstin":              "NA",
    "pan":                "ADGPH4787A",
    "email":              "emailsaifulhoda@gmail.com",
    "phone":              "93809 73378",
    "account_holder":     "Saiful Hoda",
    "account_number":     "029701009161",
    "ifsc":               "ICIC0000297",
    "account_type":       "Savings Account",
    "bank_name":          "ICICI",
    "show_pan_in_bank":   True,

    "invoice_month":      "03/06",
    "invoice_date":       "27/03/06",
    "invoice_number":     "",
    "po_number":          "ADDA007",
    "training_dates":     "23/3/06, 24/3/06, 25/5/06",
    "program_name":       "Data Analytics",

    "billed_to_name":     "Metis Eduventures Private Limited",
    "billed_to_address":  "2nd floor, 207A-208, Tower A, Unitech Cyber Park, Sec-39 Gurgaon, Haryana - 122001",
    "billed_to_gstin":    "",

    "tds_percent":        10,

    "sessions": [
        {
            "description":    "Data Analytics Offline Session's",
            "hsn_code":       "HHH-DA-Gulbarga",
            "gst_label":      "NA",
            "gst_rate":       0,
            "commercial":     "9,000",
            "quantity":       3,
            "rate_per_unit":  9000,
        }
    ],

    "unregistered_note": (
        "I, Saiful Hoda, do not hold a GSTIN, and my turnover does not exceed "
        "the threshold limit prescribed under GST laws. Therefore, I am an "
        "unregistered person under GST."
    ),
}


# ══════════════════════════════════════════════════════════════════════════════
# CLI entry-point
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate trainer tax invoices")
    parser.add_argument("--json", help="Path to JSON file with invoice data")
    parser.add_argument("--out",  help="Output PDF path", default=None)
    parser.add_argument("--sample", choices=["pavithra","saiful","both"],
                        default="both", help="Which sample to generate")
    args = parser.parse_args()

    os.makedirs("/mnt/user-data/outputs", exist_ok=True)

    if args.json:
        with open(args.json) as f:
            invoice_data = json.load(f)
        out = args.out or f"/mnt/user-data/outputs/{invoice_data['trainer_name'].replace(' ','_')}_Invoice.pdf"
        generate_invoice(invoice_data, out)
    else:
        if args.sample in ("pavithra", "both"):
            generate_invoice(PAVITHRA_DATA, "/mnt/user-data/outputs/Pavithra_A_Mar2026_Invoice.pdf")
        if args.sample in ("saiful", "both"):
            generate_invoice(SAIFUL_DATA,   "/mnt/user-data/outputs/Saiful_Hoda_Mar2026_Invoice.pdf")
