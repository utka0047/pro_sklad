"""
Утилиты для генерации PDF-документов со штрих-кодами.
Формат: 5 колонок × 6 строк = 30 штрих-кодов на листе A4.
"""
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
import barcode
from barcode.writer import ImageWriter


COLS = 5
ROWS = 6
PAGE_W, PAGE_H = A4          # 595.28 x 841.89 pt
MARGIN_X = 10 * mm
MARGIN_Y = 12 * mm
GAP_X = 4 * mm
GAP_Y = 5 * mm

CELL_W = (PAGE_W - 2 * MARGIN_X - (COLS - 1) * GAP_X) / COLS
CELL_H = (PAGE_H - 2 * MARGIN_Y - (ROWS - 1) * GAP_Y) / ROWS

BAR_H = CELL_H * 0.78        # высота картинки со штрих-кодом
TEXT_H = CELL_H * 0.20       # высота строки с артикулом

FONT_SIZE_CODE = 7


def _generate_barcode_image(sku: str) -> ImageReader:
    """Генерирует PNG штрих-кода Code128 и возвращает ImageReader для ReportLab."""
    writer = ImageWriter()
    code = barcode.get("code128", sku, writer=writer)
    buf = BytesIO()
    code.write(buf, options={
        "module_height": 10.0,
        "module_width": 0.25,
        "font_size": 0,
        "text_distance": 1.0,
        "quiet_zone": 2.0,
        "dpi": 150,
        "write_text": False,
    })
    buf.seek(0)
    return ImageReader(buf)


def generate_barcodes_pdf(items: list[dict]) -> bytes:
    """
    Генерирует PDF с штрих-кодами (5×6 на лист A4).
    items: список dict с ключами 'sku' (и опционально 'name', который игнорируется).
    Возвращает байты PDF.
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    per_page = COLS * ROWS

    for page_start in range(0, len(items), per_page):
        page_items = items[page_start: page_start + per_page]

        for idx, item in enumerate(page_items):
            col = idx % COLS
            row = idx // COLS

            x = MARGIN_X + col * (CELL_W + GAP_X)
            y_top = PAGE_H - MARGIN_Y - row * (CELL_H + GAP_Y)

            sku = str(item.get("sku", "")).strip()

            # — штрих-код —
            bar_y = y_top - BAR_H
            try:
                img = _generate_barcode_image(sku)
                c.drawImage(img, x, bar_y, width=CELL_W, height=BAR_H,
                            preserveAspectRatio=True, anchor="c")
            except Exception:
                c.setFillColor(colors.whitesmoke)
                c.rect(x, bar_y, CELL_W, BAR_H, fill=1, stroke=0)
                c.setFillColor(colors.black)
                c.setFont("Helvetica", 6)
                c.drawCentredString(x + CELL_W / 2, bar_y + BAR_H / 2, "ошибка генерации")

            # — артикул под штрих-кодом —
            c.setFillColor(colors.black)
            c.setFont("Helvetica-Bold", FONT_SIZE_CODE)
            sku_y = y_top - BAR_H - TEXT_H + 2 * mm
            c.drawCentredString(x + CELL_W / 2, sku_y, sku)

            # — рамка ячейки —
            c.setStrokeColor(colors.Color(0.80, 0.80, 0.80))
            c.setLineWidth(0.3)
            c.rect(x - 1 * mm, y_top - CELL_H, CELL_W + 2 * mm, CELL_H, fill=0, stroke=1)

        c.showPage()

    c.save()
    buf.seek(0)
    return buf.read()
