#!/usr/bin/env python3
"""Generate the editable Nova Horizon outreach DOCX and its visual assets."""

from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
OUTPUT = ROOT / "Bambu_Lab_Controller_Project_Overview.docx"

NAVY = "102333"
NAVY_2 = "193446"
TEAL = "159A9C"
CYAN = "36B8C5"
PALE = "EDF5F5"
PALE_BLUE = "EEF3F7"
MID = "63717C"
TEXT = "1D2933"
WHITE = "FFFFFF"
AMBER = "C7821A"
RED = "B44949"
GREEN = "34845A"
BORDER = "CFD9DE"

FONT_REGULAR = Path("/usr/share/fonts/opentype/inter/Inter-Regular.otf")
FONT_SEMIBOLD = Path("/usr/share/fonts/opentype/inter/Inter-SemiBold.otf")
FONT_BOLD = Path("/usr/share/fonts/opentype/inter/Inter-Bold.otf")


def pil_font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    candidate = path if path.exists() else Path(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    )
    return ImageFont.truetype(str(candidate), size)


def rounded_box(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    *,
    fill: str,
    outline: str,
    width: int = 3,
    radius: int = 24,
) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def dashed_line(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    *,
    fill: str,
    width: int = 5,
    dash: int = 16,
    gap: int = 11,
) -> None:
    x1, y1 = start
    x2, y2 = end
    length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    if length == 0:
        return
    dx = (x2 - x1) / length
    dy = (y2 - y1) / length
    position = 0.0
    while position < length:
        segment_end = min(position + dash, length)
        draw.line(
            (
                x1 + dx * position,
                y1 + dy * position,
                x1 + dx * segment_end,
                y1 + dy * segment_end,
            ),
            fill=fill,
            width=width,
        )
        position += dash + gap


def arrow_head(
    draw: ImageDraw.ImageDraw,
    point: tuple[int, int],
    direction: str,
    *,
    fill: str,
) -> None:
    x, y = point
    if direction == "right":
        points = [(x, y), (x - 18, y - 10), (x - 18, y + 10)]
    elif direction == "left":
        points = [(x, y), (x + 18, y - 10), (x + 18, y + 10)]
    elif direction == "down":
        points = [(x, y), (x - 10, y - 18), (x + 10, y - 18)]
    else:
        points = [(x, y), (x - 10, y + 18), (x + 10, y + 18)]
    draw.polygon(points, fill=fill)


def center_lines(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    detail: str,
    *,
    title_font: ImageFont.FreeTypeFont,
    detail_font: ImageFont.FreeTypeFont,
    title_fill: str,
    detail_fill: str,
) -> None:
    x1, y1, x2, y2 = box
    title_box = draw.textbbox((0, 0), title, font=title_font)
    detail_box = draw.multiline_textbbox(
        (0, 0), detail, font=detail_font, spacing=6, align="center"
    )
    title_width = title_box[2] - title_box[0]
    detail_width = detail_box[2] - detail_box[0]
    total_height = (title_box[3] - title_box[1]) + 16 + (
        detail_box[3] - detail_box[1]
    )
    top = y1 + ((y2 - y1) - total_height) / 2
    draw.text(
        (x1 + ((x2 - x1) - title_width) / 2, top),
        title,
        font=title_font,
        fill=title_fill,
    )
    draw.multiline_text(
        (x1 + ((x2 - x1) - detail_width) / 2, top + 55),
        detail,
        font=detail_font,
        fill=detail_fill,
        spacing=6,
        align="center",
    )


def make_architecture_diagram(path: Path) -> None:
    image = Image.new("RGB", (1800, 820), "#FFFFFF")
    draw = ImageDraw.Draw(image)
    title_font = pil_font(FONT_BOLD, 34)
    box_title = pil_font(FONT_BOLD, 30)
    detail_font = pil_font(FONT_REGULAR, 23)
    small_font = pil_font(FONT_SEMIBOLD, 21)

    draw.text((60, 42), "CURRENT LOCAL PATH", font=title_font, fill="#" + NAVY)
    draw.text((1220, 42), "PLANNED / OPTIONAL", font=title_font, fill="#" + MID)

    touch = (70, 140, 400, 335)
    controller = (570, 105, 1190, 410)
    printer = (1370, 140, 1730, 335)
    workstation = (70, 535, 400, 720)
    jetson = (575, 545, 880, 725)
    backend = (990, 545, 1365, 725)
    web = (1460, 545, 1730, 725)

    rounded_box(draw, touch, fill="#EDF5F5", outline="#" + TEAL, width=4)
    rounded_box(draw, controller, fill="#" + NAVY, outline="#" + CYAN, width=5)
    rounded_box(draw, printer, fill="#EEF3F7", outline="#" + NAVY_2, width=4)
    rounded_box(draw, workstation, fill="#F6F8F9", outline="#" + MID, width=3)
    rounded_box(draw, jetson, fill="#FAFBFB", outline="#" + MID, width=3)
    rounded_box(draw, backend, fill="#FAFBFB", outline="#" + MID, width=3)
    rounded_box(draw, web, fill="#FAFBFB", outline="#" + MID, width=3)

    center_lines(
        draw,
        touch,
        "TOUCHSCREEN USER",
        "Dashboard • status\nselected safe controls",
        title_font=box_title,
        detail_font=detail_font,
        title_fill="#" + NAVY,
        detail_fill="#" + MID,
    )
    center_lines(
        draw,
        controller,
        "NOVA HORIZON CONTROLLER",
        "ESP32-P4 • LVGL 9.5 • FreeRTOS\ntelemetry parser • command safety gate\nESP32-C6 hosted Wi-Fi • SD storage",
        title_font=box_title,
        detail_font=detail_font,
        title_fill="#" + WHITE,
        detail_fill="#D9F4F5",
    )
    center_lines(
        draw,
        printer,
        "BAMBU LAB P1S",
        "Local authenticated TLS\nMQTT + camera JPEG",
        title_font=box_title,
        detail_font=detail_font,
        title_fill="#" + NAVY,
        detail_fill="#" + MID,
    )
    center_lines(
        draw,
        workstation,
        "DEVELOPMENT PC",
        "Physically enabled\nlocal HTTP OTA",
        title_font=box_title,
        detail_font=detail_font,
        title_fill="#" + NAVY,
        detail_fill="#" + MID,
    )
    center_lines(
        draw,
        jetson,
        "JETSON ORIN NANO",
        "Vision verification",
        title_font=small_font,
        detail_font=detail_font,
        title_fill="#" + MID,
        detail_fill="#" + MID,
    )
    center_lines(
        draw,
        backend,
        "NOVA HORIZON BACKEND",
        "Optional API / dashboard",
        title_font=small_font,
        detail_font=detail_font,
        title_fill="#" + MID,
        detail_fill="#" + MID,
    )
    center_lines(
        draw,
        web,
        "WEB / REMOTE",
        "Future management",
        title_font=small_font,
        detail_font=detail_font,
        title_fill="#" + MID,
        detail_fill="#" + MID,
    )

    draw.line((400, 238, 570, 238), fill="#" + TEAL, width=7)
    arrow_head(draw, (557, 238), "right", fill="#" + TEAL)
    draw.line((1190, 220, 1370, 220), fill="#" + TEAL, width=7)
    arrow_head(draw, (1357, 220), "right", fill="#" + TEAL)
    draw.line((1370, 270, 1190, 270), fill="#" + NAVY_2, width=7)
    arrow_head(draw, (1203, 270), "left", fill="#" + NAVY_2)
    draw.line((400, 628, 500, 628, 500, 365, 570, 365), fill="#" + MID, width=5)
    arrow_head(draw, (557, 365), "right", fill="#" + MID)

    dashed_line(draw, (730, 545), (730, 410), fill="#" + MID)
    arrow_head(draw, (730, 425), "up", fill="#" + MID)
    dashed_line(draw, (1178, 545), (1080, 410), fill="#" + MID)
    arrow_head(draw, (1091, 426), "up", fill="#" + MID)
    dashed_line(draw, (1365, 635), (1460, 635), fill="#" + MID)
    arrow_head(draw, (1447, 635), "right", fill="#" + MID)

    draw.text((80, 758), "Solid = implemented", font=small_font, fill="#" + TEAL)
    dashed_line(draw, (310, 773), (430, 773), fill="#" + MID, width=4, dash=13, gap=9)
    draw.text((450, 758), "Dashed = planned", font=small_font, fill="#" + MID)
    image.save(path, "PNG", optimize=True)


def make_placeholder(path: Path, title: str, subtitle: str, size: tuple[int, int]) -> None:
    width, height = size
    image = Image.new("RGB", size, "#F4F7F8")
    draw = ImageDraw.Draw(image)
    pad = max(12, width // 80)
    draw.rounded_rectangle(
        (pad, pad, width - pad, height - pad),
        radius=max(20, width // 70),
        fill="#F8FAFA",
        outline="#" + TEAL,
        width=max(3, width // 350),
    )
    draw.line((pad * 2, pad * 2, width - pad * 2, height - pad * 2), fill="#DDE8EA", width=2)
    draw.line((width - pad * 2, pad * 2, pad * 2, height - pad * 2), fill="#DDE8EA", width=2)
    title_font = pil_font(FONT_BOLD, max(24, width // 32))
    subtitle_font = pil_font(FONT_REGULAR, max(17, width // 48))
    camera_font = pil_font(FONT_SEMIBOLD, max(22, width // 38))
    camera = "PHOTO"
    camera_box = draw.textbbox((0, 0), camera, font=camera_font)
    camera_w = camera_box[2] - camera_box[0]
    draw.rounded_rectangle(
        (
            width / 2 - camera_w / 2 - 24,
            height * 0.2,
            width / 2 + camera_w / 2 + 24,
            height * 0.2 + camera_box[3] - camera_box[1] + 18,
        ),
        radius=12,
        fill="#" + NAVY,
    )
    draw.text(
        (width / 2 - camera_w / 2, height * 0.2 + 8),
        camera,
        font=camera_font,
        fill="white",
    )
    title_box = draw.textbbox((0, 0), title, font=title_font)
    title_w = title_box[2] - title_box[0]
    draw.text(
        ((width - title_w) / 2, height * 0.49),
        title,
        font=title_font,
        fill="#" + NAVY,
    )
    subtitle_box = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    subtitle_w = subtitle_box[2] - subtitle_box[0]
    draw.text(
        ((width - subtitle_w) / 2, height * 0.67),
        subtitle,
        font=subtitle_font,
        fill="#" + MID,
    )
    image.save(path, "PNG", optimize=True)


def set_run_font(run, size: float, color: str = TEXT, bold: bool = False) -> None:
    run.font.name = "Inter"
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "Inter")
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color)
    run.bold = bold


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top: int = 70, start: int = 90, bottom: int = 70, end: int = 90) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table, color: str = BORDER, size: int = 5) -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = borders.find(qn(f"w:{edge}"))
        if tag is None:
            tag = OxmlElement(f"w:{edge}")
            borders.append(tag)
        tag.set(qn("w:val"), "single")
        tag.set(qn("w:sz"), str(size))
        tag.set(qn("w:space"), "0")
        tag.set(qn("w:color"), color)


def fixed_layout(table) -> None:
    tbl_pr = table._tbl.tblPr
    layout = tbl_pr.first_child_found_in("w:tblLayout")
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        tbl_pr.append(layout)
    layout.set(qn("w:type"), "fixed")


def keep_row_together(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    tr_pr.append(cant_split)


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    tr_pr.append(repeat)


def add_text(
    container,
    text: str,
    *,
    size: float = 9.1,
    color: str = TEXT,
    bold: bool = False,
    before: float = 0,
    after: float = 3,
    align: WD_ALIGN_PARAGRAPH | None = None,
    keep_with_next: bool = False,
) -> object:
    paragraph = container.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(before)
    paragraph.paragraph_format.space_after = Pt(after)
    paragraph.paragraph_format.line_spacing = 1.04
    paragraph.paragraph_format.keep_with_next = keep_with_next
    if align is not None:
        paragraph.alignment = align
    run = paragraph.add_run(text)
    set_run_font(run, size, color, bold)
    return paragraph


def add_bullets(container, items: Iterable[str], *, size: float = 8.8, compact: bool = True) -> None:
    for item in items:
        paragraph = container.add_paragraph(style="List Bullet")
        paragraph.paragraph_format.left_indent = Inches(0.18)
        paragraph.paragraph_format.first_line_indent = Inches(-0.12)
        paragraph.paragraph_format.space_after = Pt(1.5 if compact else 3)
        paragraph.paragraph_format.line_spacing = 1.02
        run = paragraph.add_run(item)
        set_run_font(run, size, TEXT)


def section_heading(container, number: str, title: str, *, top: float = 4) -> None:
    table = container.add_table(rows=1, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.autofit = False
    fixed_layout(table)
    table.columns[0].width = Inches(0.42)
    table.columns[1].width = Inches(6.88)
    table.cell(0, 0).width = Inches(0.42)
    table.cell(0, 1).width = Inches(6.88)
    set_cell_shading(table.cell(0, 0), TEAL)
    set_cell_shading(table.cell(0, 1), PALE)
    set_table_borders(table, PALE, 0)
    for cell in table.rows[0].cells:
        set_cell_margins(cell, 55, 80, 55, 80)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    p0 = table.cell(0, 0).paragraphs[0]
    p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r0 = p0.add_run(number)
    set_run_font(r0, 10.2, WHITE, True)
    p1 = table.cell(0, 1).paragraphs[0]
    r1 = p1.add_run(title.upper())
    set_run_font(r1, 10.4, NAVY, True)
    spacer = container.add_paragraph()
    spacer.paragraph_format.space_before = Pt(0)
    spacer.paragraph_format.space_after = Pt(top)
    spacer.paragraph_format.line_spacing = 0.1


def add_table(
    container,
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    widths: Sequence[float],
    *,
    font_size: float = 8.0,
    header_size: float = 8.0,
    row_fills: Sequence[str] | None = None,
) -> object:
    table = container.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    fixed_layout(table)
    set_table_borders(table)
    for index, width in enumerate(widths):
        table.columns[index].width = Inches(width)
        table.cell(0, index).width = Inches(width)
    header_row = table.rows[0]
    set_repeat_table_header(header_row)
    keep_row_together(header_row)
    for index, header in enumerate(headers):
        cell = header_row.cells[index]
        set_cell_shading(cell, NAVY)
        set_cell_margins(cell, 65, 75, 65, 75)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        paragraph = cell.paragraphs[0]
        paragraph.paragraph_format.space_after = Pt(0)
        run = paragraph.add_run(header)
        set_run_font(run, header_size, WHITE, True)
    for row_index, values in enumerate(rows):
        cells = table.add_row().cells
        keep_row_together(table.rows[-1])
        fill = (
            row_fills[row_index]
            if row_fills and row_index < len(row_fills)
            else (WHITE if row_index % 2 == 0 else "F7F9FA")
        )
        for col_index, value in enumerate(values):
            cells[col_index].width = Inches(widths[col_index])
            set_cell_shading(cells[col_index], fill)
            set_cell_margins(cells[col_index], 55, 70, 55, 70)
            cells[col_index].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            paragraph = cells[col_index].paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(0)
            paragraph.paragraph_format.line_spacing = 1.0
            run = paragraph.add_run(value)
            set_run_font(run, font_size, TEXT, col_index == 0)
    return table


def add_picture(container, path: Path, width: float, caption: str, *, after: float = 2) -> None:
    paragraph = container.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(2)
    paragraph.paragraph_format.space_after = Pt(1)
    paragraph.add_run().add_picture(str(path), width=Inches(width))
    caption_p = container.add_paragraph()
    caption_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption_p.paragraph_format.space_after = Pt(after)
    run = caption_p.add_run(caption)
    set_run_font(run, 7.5, MID, False)
    run.italic = True


def add_hyperlink(paragraph, text: str, url: str) -> None:
    part = paragraph.part
    relationship_id = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), relationship_id)
    run = OxmlElement("w:r")
    run_properties = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), TEAL)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    run_properties.extend([color, underline])
    run.append(run_properties)
    text_element = OxmlElement("w:t")
    text_element.text = text
    run.append(text_element)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def add_page_number(paragraph) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    placeholder = OxmlElement("w:t")
    placeholder.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instruction, separate, placeholder, end])
    set_run_font(run, 7.5, MID)


def configure_document(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.48)
    section.bottom_margin = Inches(0.48)
    section.left_margin = Inches(0.58)
    section.right_margin = Inches(0.58)
    section.header_distance = Inches(0.22)
    section.footer_distance = Inches(0.22)
    section.different_first_page_header_footer = True

    normal = document.styles["Normal"]
    normal.font.name = "Inter"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Inter")
    normal.font.size = Pt(9.1)
    normal.font.color.rgb = RGBColor.from_string(TEXT)
    normal.paragraph_format.space_after = Pt(3)

    for style_name in ("List Bullet", "List Number"):
        style = document.styles[style_name]
        style.font.name = "Inter"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Inter")

    section.first_page_header.paragraphs[0].text = ""
    header = section.header
    header_p = header.paragraphs[0]
    header_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    header_p.paragraph_format.space_after = Pt(0)
    run = header_p.add_run("NOVA HORIZON  /  PROJECT OVERVIEW")
    set_run_font(run, 7.2, MID, True)

    first_footer = section.first_page_footer.paragraphs[0]
    first_footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = first_footer.add_run("INDEPENDENT DEVELOPMENT PROJECT  /  ")
    set_run_font(run, 7.2, MID, True)
    add_page_number(first_footer)

    footer = section.footer
    footer_p = footer.paragraphs[0]
    footer_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = footer_p.add_run("NOVA HORIZON CONTROLLER  /  ")
    set_run_font(run, 7.2, MID, True)
    add_page_number(footer_p)

    document.core_properties.title = "Nova Horizon Controller — Project Overview"
    document.core_properties.subject = "Independent Bambu Lab controller development and temporary printer-loan request"
    document.core_properties.author = "Dima"
    document.core_properties.keywords = (
        "Nova Horizon, Bambu Lab, P1S, X1 Carbon, H2D, controller, development loan"
    )
    document.core_properties.comments = (
        "Independent project; Bambu Lab is not currently affiliated."
    )


def page_break(document: Document) -> None:
    document.add_page_break()


def build_document() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    architecture = ASSETS / "architecture_diagram.png"
    cover_photo = ASSETS / "placeholder_cover.png"
    screen_photo = ASSETS / "placeholder_touchscreen.png"
    hardware_photo = ASSETS / "placeholder_hardware.png"
    p1s_photo = ASSETS / "placeholder_p1s.png"
    test_photo = ASSETS / "placeholder_test_setup.png"
    make_architecture_diagram(architecture)
    make_placeholder(
        cover_photo,
        "CURRENT PHYSICAL PROTOTYPE",
        "Replace with a clean, powered-controller photograph",
        (1600, 740),
    )
    make_placeholder(
        screen_photo,
        "CURRENT TOUCHSCREEN INTERFACE",
        "Replace with a straight-on live dashboard photograph",
        (1600, 390),
    )
    make_placeholder(
        hardware_photo,
        "ENCLOSURE OR HARDWARE DEVELOPMENT",
        "Replace with the PCB/display assembly or enclosure work",
        (1200, 330),
    )
    make_placeholder(
        p1s_photo,
        "CONTROLLER CONNECTED TO BAMBU LAB P1S",
        "Replace with a clean, wide prototype-and-printer photograph",
        (1600, 350),
    )
    make_placeholder(
        test_photo,
        "DEVELOPMENT AND TESTING SETUP",
        "Replace with the controller, printer, and development workstation",
        (1600, 300),
    )

    document = Document()
    configure_document(document)

    # Page 1 — Cover
    add_text(document, "NOVA HORIZON", size=11.5, color=TEAL, bold=True, after=6)
    p = document.add_paragraph()
    p.paragraph_format.space_after = Pt(5)
    r = p.add_run("CONTROLLER")
    set_run_font(r, 34, NAVY, True)
    add_text(
        document,
        "A local-first touchscreen controller prototype for monitoring and cautiously controlling Bambu Lab printers.",
        size=15,
        color=NAVY_2,
        bold=False,
        after=10,
    )
    label_table = document.add_table(rows=1, cols=1)
    label_table.alignment = WD_TABLE_ALIGNMENT.LEFT
    set_cell_shading(label_table.cell(0, 0), PALE)
    set_table_borders(label_table, TEAL, 7)
    set_cell_margins(label_table.cell(0, 0), 95, 140, 95, 140)
    label_p = label_table.cell(0, 0).paragraphs[0]
    label_p.paragraph_format.space_after = Pt(0)
    label_r = label_p.add_run("INDEPENDENT BAMBU LAB CONTROLLER DEVELOPMENT PROJECT")
    set_run_font(label_r, 9.4, NAVY, True)
    add_text(document, "Prepared by Dima", size=12, color=TEXT, bold=True, before=10, after=1)
    add_text(
        document,
        "Firmware reviewed: v0.7.1 deployed prototype build  /  July 2026",
        size=8.8,
        color=MID,
        after=8,
    )
    add_picture(document, cover_photo, 7.25, "Current physical prototype.", after=8)
    disclaimer = document.add_table(rows=1, cols=1)
    set_cell_shading(disclaimer.cell(0, 0), NAVY)
    set_table_borders(disclaimer, NAVY, 0)
    set_cell_margins(disclaimer.cell(0, 0), 110, 150, 110, 150)
    disclaimer_p = disclaimer.cell(0, 0).paragraphs[0]
    disclaimer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    disclaimer_r = disclaimer_p.add_run(
        "Bambu Lab is not currently affiliated with or responsible for this independent project."
    )
    set_run_font(disclaimer_r, 9.2, WHITE, True)

    # Page 2 — Overview and status
    page_break(document)
    section_heading(document, "1", "Project overview")
    add_text(
        document,
        "Nova Horizon Controller is a dedicated touchscreen device being developed to put useful printer information and carefully gated controls on a small, always-available local display. The current prototype targets a Bambu Lab P1S and is intended to reduce the need to reach for a phone or computer for routine at-a-glance monitoring and selected printer actions.",
        size=9.3,
        after=4,
    )
    add_text(
        document,
        "The project is local-first: the working P1S integration communicates over the local network. The design leaves clear boundaries for optional Nova Horizon web services and a Jetson Orin Nano vision system, but neither is part of the current working printer path.",
        size=9.3,
        after=6,
    )
    section_heading(document, "2", "Current development status")
    status_rows = [
        (
            "Completed and verified",
            "Firmware build; 4.3-inch display; landscape LVGL UI; aligned touch; ESP32-C6 Wi-Fi; local P1S authentication; live print reporting; chamber-light control; P1 camera liveview; physically enabled LAN OTA.",
        ),
        (
            "Functional, refining",
            "P1S telemetry, on-screen setup, reconnect behavior, SD mounting, camera lifecycle, and UI messaging. Signed v0.7.1 is deployed with stable short health samples; full regression remains pending.",
        ),
        (
            "In active development",
            "Safe validation of pause/resume/cancel, credential-storage hardening, local file indexing and print initiation, and broader regression tests.",
        ),
        (
            "Planned",
            "AMS/filament workflows, multi-printer profiles, optional Nova Horizon backend connectivity, Jetson vision verification, and broader diagnostics.",
        ),
        (
            "Needs more printers",
            "X- and H-series authentication, telemetry, cameras, AMS generations, command behavior, firmware differences, errors, and UI adaptation.",
        ),
    ]
    add_table(
        document,
        ("STATUS", "CURRENT EVIDENCE-BASED POSITION"),
        status_rows,
        (1.55, 5.65),
        font_size=8.1,
        header_size=8.1,
        row_fills=(PALE, WHITE, PALE_BLUE, WHITE, "FFF7E8"),
    )
    add_picture(document, screen_photo, 7.15, "Current touchscreen interface.", after=1)

    # Page 3 — Capabilities and architecture
    page_break(document)
    section_heading(document, "3", "Key planned capabilities")
    capability_rows = [
        (
            "Status / monitoring",
            "Working on P1S, refining",
            "Connection and job state, progress, layers, remaining time, temperatures, fan level, and chamber-light state.",
        ),
        (
            "Job management",
            "Implemented; validation pending",
            "Pause/resume/cancel paths exist; cancel confirms. Chamber light is runtime verified.",
        ),
        (
            "Files / print start",
            "UI scaffold only",
            "Non-destructive SD mount is implemented; media confirmation, indexing, transfer, queueing, and print initiation remain pending.",
        ),
        (
            "Motion / thermal / fan",
            "Intentionally disabled",
            "Visible design scaffolding is rejected by the transport until safely validated.",
        ),
        (
            "Camera / AI vision",
            "P1 camera working; AI planned",
            "On-demand encrypted P1 liveview is implemented; no vision model or Jetson integration exists.",
        ),
        (
            "AMS / filament",
            "Planned",
            "No AMS parser or control workflow is present.",
        ),
        (
            "Multi-printer / remote",
            "Planned",
            "One P1S profile today; optional Nova backend/dashboard is a roadmap item.",
        ),
        (
            "Diagnostics",
            "Partial",
            "Heap, stack, reset, uptime, coredump, OTA, auth, and connection state are reported; long-duration and full error/HMS work remains.",
        ),
    ]
    add_table(
        document,
        ("CAPABILITY", "STATUS", "CURRENT BOUNDARY"),
        capability_rows,
        (1.5, 1.7, 4.0),
        font_size=7.35,
        header_size=7.7,
    )
    add_text(document, "", size=1, after=1)
    section_heading(document, "4", "Hardware and software architecture")
    add_text(
        document,
        "Guition JC4880P443: ESP32-P4NRW32, 32 MB PSRAM, 16 MB flash, ESP32-C6 Wi-Fi, 4.3-inch ST7701S MIPI-DSI display, GT911 touch, and SDMMC. Firmware: ESP-IDF 6.0.2 / FreeRTOS / LVGL 9.5. Working printer transport: authenticated local TLS/MQTT with CA and printer-identity checks.",
        size=8.5,
        after=3,
    )
    add_picture(
        document,
        architecture,
        7.22,
        "Solid lines are implemented; dashed lines are planned. No credentials or private identifiers are shown.",
        after=2,
    )
    add_picture(document, hardware_photo, 4.5, "Enclosure or hardware development.", after=0)

    # Page 4 — Hardware request and loan arrangement
    page_break(document)
    section_heading(document, "5", "Why additional printers are needed")
    add_text(
        document,
        "One P1S can validate only one printer family and one set of firmware, telemetry, camera, accessory, and command behaviors. It cannot establish whether the same fields, responses, reconnect behavior, error states, or interface assumptions hold across Bambu Lab’s X and H families.",
        size=9.0,
        after=4,
    )
    recommendation_rows = [
        (
            "X1 Carbon + AMS",
            "Adds X-series authentication/firmware coverage and a higher-resolution chamber camera plus Micro Lidar behavior—useful for separating model capabilities from P1S assumptions.",
        ),
        (
            "H2D + AMS 2 Pro",
            "Adds the broadest H-series protocol challenge: dual-nozzle state, newer camera/sensor roles, active chamber functions, and newer filament-system behavior.",
        ),
    ]
    add_table(
        document,
        ("RECOMMENDED LOAN UNIT", "TESTING VALUE"),
        recommendation_rows,
        (1.8, 5.4),
        font_size=8.25,
        header_size=8.1,
        row_fills=(PALE, PALE_BLUE),
    )
    add_text(
        document,
        "With the existing P1S, these units would provide broad P/X/H family coverage—not certification of every Bambu Lab model or SKU. A-series and per-model certification would remain separate work.",
        size=8.8,
        color=NAVY_2,
        bold=True,
        before=3,
        after=2,
    )
    refs = document.add_paragraph()
    refs.paragraph_format.space_after = Pt(4)
    ref_run = refs.add_run("Official references: ")
    set_run_font(ref_run, 7.8, MID, True)
    add_hyperlink(
        refs,
        "P1S specification",
        "https://cdn1.bambulab.com/documentation/quick-start-59b0cefdc0fc4/P1S/English%20version-Quick%20Start%20Guide%20for%20P1S.pdf",
    )
    between = refs.add_run("  /  ")
    set_run_font(between, 7.8, MID)
    add_hyperlink(
        refs,
        "X1 Carbon technical specification",
        "https://public-cdn.bambulab.com/store/bambulab-X1-carbon-tech-specs.pdf",
    )
    between = refs.add_run("  /  ")
    set_run_font(between, 7.8, MID)
    add_hyperlink(
        refs,
        "H2D technical data sheet",
        "https://cdn1.bambulab.com/documentation/h2d/en/H2D_Laser_Full_Combo_20250305.pdf",
    )
    add_picture(document, p1s_photo, 7.05, "Controller connected to Bambu Lab P1S.", after=3)
    section_heading(document, "6", "Proposed printer-loan arrangement")
    add_text(
        document,
        "I am requesting one or two printers on a temporary development loan for compatibility development, validation, demonstrations, and preparation of accurate project media. The equipment would be kept in a clean, controlled development environment and used for normal printing, protocol observation, regression testing, and documented demonstrations. The planned LAN-integration work does not require permanent printer modification; I would follow applicable operating and maintenance guidance and document relevant configuration changes.",
        size=8.7,
        after=3,
    )
    add_text(
        document,
        "I am willing to comply with reasonable loan terms, provide periodic progress reports, and share compatibility findings and relevant technical feedback. The printers can be returned at the end of an agreed loan period unless a different arrangement is mutually agreed. This request does not presume approval, endorsement, sponsorship, or partnership.",
        size=8.7,
        after=0,
    )

    # Page 5 — Test and promotion plan
    page_break(document)
    section_heading(document, "7", "Testing and validation plan")
    add_text(
        document,
        "Complete = observed on the current prototype  /  Partial = implemented or observed with remaining tests  /  HW = requested printer required",
        size=7.6,
        color=MID,
        bold=True,
        after=3,
    )
    test_rows = [
        ("Discovery / connection", "Partial: manual profile; no discovery", "HW", "HW"),
        ("Authentication / TLS / MQTT", "Complete for current profile", "HW", "HW"),
        ("Job / temperature telemetry", "Partial: live; regression ongoing", "HW", "HW + dual-nozzle"),
        ("Commands / safety gates", "Light complete; job controls pending", "HW", "HW"),
        ("File handling / print launch", "Pending implementation", "Pending", "Pending"),
        ("Camera behavior", "Partial: local P1 liveview works", "HW", "HW + camera roles"),
        ("AMS / filament state", "Pending implementation", "HW", "HW / AMS 2 Pro"),
        ("Errors / reconnection", "Partial code paths; fault tests pending", "HW", "HW"),
        ("Firmware / long-duration", "Pending matrix", "HW", "HW"),
        ("UI adaptation / regression", "P1S-focused UI working", "HW", "HW"),
    ]
    add_table(
        document,
        ("TEST AREA", "P1S", "X1C + AMS", "H2D + AMS 2 PRO"),
        test_rows,
        (1.45, 2.55, 1.45, 1.75),
        font_size=6.95,
        header_size=7.0,
    )
    add_text(
        document,
        "Safety-sensitive commands will be exercised only with an appropriate setup, confirmation behavior, and a recoverable test job.",
        size=7.7,
        color=NAVY_2,
        bold=True,
        before=2,
        after=2,
    )
    add_picture(document, test_photo, 6.75, "Development and testing setup.", after=2)
    section_heading(document, "8", "Demonstration and promotional plan")
    add_text(
        document,
        "After a reliable demonstration stage, I plan to prepare a dedicated project website, development updates, prototype demonstrations, product walkthroughs, compatibility demonstrations, and educational technical content. Outreach would include multiple 3D-printing and technology YouTube creators, social media content, and carefully targeted Meta advertising.",
        size=8.15,
        after=2,
    )
    add_text(
        document,
        "These are planned activities—not existing creator partnerships or guaranteed coverage. Bambu Lab would be acknowledged as a project supporter only if Bambu Lab agrees and approves the form of that acknowledgment.",
        size=8.15,
        color=NAVY_2,
        bold=True,
        after=0,
    )

    # Page 6 — Value, roadmap, contact
    page_break(document)
    section_heading(document, "9", "Potential value to Bambu Lab")
    add_text(
        document,
        "A successful independent controller could create additional community-driven use cases while generating practical compatibility feedback across printer families. Potential—not guaranteed—value includes:",
        size=8.8,
        after=2,
    )
    add_bullets(
        document,
        (
            "More technical and demonstration content featuring the Bambu Lab ecosystem.",
            "Engagement from advanced users, makers, and integration-oriented customers.",
            "Earlier identification and documentation of cross-model compatibility issues.",
            "Demonstrations of responsible local integration and command gating.",
        ),
        size=8.2,
    )
    section_heading(document, "10", "Development roadmap", top=2)
    roadmap_rows = [
        ("Current — P1S prototype", "Hardware-regression test deployed v0.7.1 telemetry, reconnect, camera lifecycle, SD refresh, health data, and guarded actions."),
        ("Next technical milestone", "Validate supported job commands; harden credentials; implement real local file browse/print start."),
        ("Multi-printer compatibility", "Add model capability profiles; characterize X1 Carbon and H2D telemetry, cameras, AMS, commands, and UI."),
        ("Reliability / hardening", "Reconnect, malformed/error-state, firmware-regression, long-duration, and safe-command testing."),
        ("Creator demonstration", "Presentable enclosure, repeatable demos, accurate photography/video, compatibility summary."),
        ("Public launch preparation", "Website, walkthroughs, support documentation, disclosures, and outreach materials."),
    ]
    add_table(
        document,
        ("PHASE", "SCOPE / EXIT CONDITION"),
        roadmap_rows,
        (1.75, 5.45),
        font_size=7.55,
        header_size=7.8,
    )
    add_text(
        document,
        "No completion dates are asserted; progress depends on hardware access and compatibility findings.",
        size=7.7,
        color=MID,
        after=3,
    )
    section_heading(document, "11", "Contact and next step", top=2)
    add_text(
        document,
        "I would welcome a discussion about whether Bambu Lab would consider a temporary development loan of an X1 Carbon and/or H2D, ideally with their corresponding AMS systems.",
        size=8.7,
        bold=True,
        color=NAVY_2,
        after=3,
    )
    contact_table = document.add_table(rows=3, cols=2)
    contact_table.alignment = WD_TABLE_ALIGNMENT.LEFT
    contact_table.autofit = False
    fixed_layout(contact_table)
    set_table_borders(contact_table, BORDER, 4)
    contact_values = (
        ("DIMA", "Email: [INSERT EMAIL]  /  Phone: [INSERT PHONE]"),
        ("PROJECT", "Website: [INSERT PROJECT WEBSITE]"),
        ("LINKS", "Repository: [INSERT REPOSITORY, IF SHARED]  /  Social: [INSERT SOCIAL LINKS]"),
    )
    for row_index, values in enumerate(contact_values):
        keep_row_together(contact_table.rows[row_index])
        for col_index, value in enumerate(values):
            cell = contact_table.cell(row_index, col_index)
            cell.width = Inches(1.1 if col_index == 0 else 6.1)
            set_cell_shading(cell, PALE if col_index == 0 else WHITE)
            set_cell_margins(cell, 55, 70, 55, 70)
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(0)
            run = paragraph.add_run(value)
            set_run_font(run, 7.7, NAVY if col_index == 0 else TEXT, col_index == 0)
    add_text(
        document,
        "Nova Horizon Controller is an independent development project. Bambu Lab is not currently affiliated with or responsible for it.",
        size=7.7,
        color=MID,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        before=4,
        after=0,
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document.save(OUTPUT)
    print(f"Generated {OUTPUT}")


if __name__ == "__main__":
    build_document()
