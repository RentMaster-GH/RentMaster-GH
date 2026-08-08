# services/pdf_generator.py
from fpdf import FPDF
from services.helpers import fmt_money, fmt_date, prop_label


def generate_receipt_pdf(tenant: dict, payment: dict, property_obj: dict = None) -> bytes:
    tenant = tenant if isinstance(tenant, dict) else {}
    payment = payment if isinstance(payment, dict) else {}
    property_obj = property_obj if isinstance(property_obj, dict) else {}

    amount_str = fmt_money(payment.get("amount", 0))
    p_date = fmt_date(payment.get("payment_date"))
    p_ref = payment.get("notes") or str(payment.get("id", "N/A"))[:12]
    t_name = tenant.get("name", "Valued Tenant")
    p_name = prop_label(property_obj) if property_obj else "RentMaster-GH Property"
    p_method = str(payment.get("payment_method") or "online_paystack").replace("_", " ").title()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_fill_color(15, 76, 117)
    pdf.rect(0, 0, 210, 35, 'F')

    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(10, 8)
    pdf.cell(0, 10, "RentMaster-GH Official Receipt", ln=True, align="C")

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(187, 222, 251)
    pdf.cell(0, 6, "Proof of Rent Payment", ln=True, align="C")

    pdf.ln(15)

    pdf.set_draw_color(226, 232, 240)
    pdf.set_fill_color(248, 250, 252)
    pdf.rect(15, 45, 180, 110, 'DF')

    pdf.set_xy(20, 52)
    pdf.set_text_color(30, 41, 59)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "TRANSACTION DETAILS", ln=True)

    pdf.set_font("Helvetica", "", 10)
    pdf.ln(2)

    details = [
        ("Receipt Reference:", p_ref),
        ("Payment Date:", p_date),
        ("Tenant Name:", t_name),
        ("Property Address:", p_name),
        ("Payment Method:", p_method),
    ]

    for label, val in details:
        pdf.set_x(20)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(50, 7, label, ln=False)

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(100, 7, str(val), ln=True)

    pdf.ln(5)

    pdf.set_fill_color(240, 253, 244)
    pdf.rect(20, 115, 170, 18, 'F')

    pdf.set_xy(25, 119)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(15, 76, 117)
    pdf.cell(50, 10, "AMOUNT PAID:", ln=False)

    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(22, 101, 52)
    pdf.cell(100, 10, amount_str, ln=True)

    pdf.set_xy(10, 175)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 10, "Thank you for your payment! Powered by RentMaster-GH System.", align="C")

    return bytes(pdf.output())
