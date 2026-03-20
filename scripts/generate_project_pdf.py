from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs" / "ENTREGA.md"
OUTPUT = ROOT / "proyecto_orbita_command.pdf"

TITLE = "ORBITA COMMAND"
SUBTITLE = "Technical Project Report"
TAGLINE = "Aplicacion web de gestion de misiones con seguridad aplicada, interfaz moderna e integracion con Gemini."


class ProjectDocTemplate(SimpleDocTemplate):
    def afterFlowable(self, flowable):
        level = getattr(flowable, "toc_level", None)
        if level is None:
            return
        text = flowable.getPlainText()
        key = f"heading-{self.page}-{len(text)}-{abs(hash(text))}"
        self.canv.bookmarkPage(key)
        self.notify("TOCEntry", (level, text, self.page, key))


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CoverTitle",
            parent=styles["Title"],
            fontName="Times-Bold",
            alignment=TA_CENTER,
            fontSize=24,
            leading=28,
            textColor=colors.HexColor("#7053B8"),
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CoverAccent",
            parent=styles["Heading2"],
            fontName="Times-Bold",
            alignment=TA_CENTER,
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#F05C76"),
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CoverMeta",
            parent=styles["BodyText"],
            fontName="Times-Roman",
            alignment=TA_CENTER,
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#5B6272"),
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TocHeading",
            parent=styles["Heading1"],
            fontName="Times-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#7053B8"),
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Heading1Custom",
            parent=styles["Heading1"],
            fontName="Times-Bold",
            fontSize=17,
            leading=21,
            textColor=colors.HexColor("#7053B8"),
            spaceBefore=8,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Heading2Custom",
            parent=styles["Heading2"],
            fontName="Times-Bold",
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#F05C76"),
            spaceBefore=7,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyCustom",
            parent=styles["BodyText"],
            fontName="Times-Roman",
            fontSize=10.5,
            leading=15.5,
            alignment=TA_JUSTIFY,
            textColor=colors.HexColor("#313746"),
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BulletCustom",
            parent=styles["BodyText"],
            fontName="Times-Roman",
            fontSize=10.5,
            leading=15.5,
            textColor=colors.HexColor("#313746"),
            leftIndent=14,
            bulletIndent=4,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableCell",
            parent=styles["BodyText"],
            fontName="Times-Roman",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#2E3442"),
        )
    )
    return styles


def draw_later_pages(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setFont("Times-Roman", 10)
    canvas.setFillColor(colors.HexColor("#7053B8"))
    canvas.drawString(2.0 * cm, height - 1.2 * cm, "ORBITA COMMAND Project Report")
    canvas.setFillColor(colors.HexColor("#F05C76"))
    canvas.drawRightString(width - 2.0 * cm, height - 1.2 * cm, "Project Documentation")
    canvas.setStrokeColor(colors.HexColor("#C9C9C9"))
    canvas.line(2.0 * cm, height - 1.35 * cm, width - 2.0 * cm, height - 1.35 * cm)
    canvas.setFillColor(colors.HexColor("#7A7A9A"))
    canvas.drawCentredString(width / 2, 1.0 * cm, str(doc.page))
    canvas.restoreState()


def make_objective_box(styles):
    text = (
        "<b>Objective:</b> document the ORBITA COMMAND system, describe its "
        "modules, security controls, repository contents, operational flow and "
        "Gemini integration with a formal project-oriented structure."
    )
    table = Table([[Paragraph(text, styles["BodyCustom"])]], colWidths=[14.7 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8F5FF")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#8F74D6")),
                ("INNERPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    return table


def make_snapshot_table(styles):
    data = [
        [
            Paragraph("<b>Backend</b><br/>Flask", styles["TableCell"]),
            Paragraph("<b>Database</b><br/>SQLite / SQLAlchemy", styles["TableCell"]),
            Paragraph("<b>AI Assistant</b><br/>Gemini 2.5 Flash", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Auth</b><br/>Flask-Login", styles["TableCell"]),
            Paragraph("<b>Forms</b><br/>WTForms / CSRF", styles["TableCell"]),
            Paragraph("<b>Focus</b><br/>Security and operations", styles["TableCell"]),
        ],
    ]
    table = Table(data, colWidths=[4.9 * cm, 4.9 * cm, 4.9 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FBFAFF")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#9B83DC")),
                ("GRID", (0, 0), (-1, -1), 0.8, colors.HexColor("#D9D1F2")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def make_meta_table(styles):
    data = [
        [Paragraph("<b>Project:</b>", styles["TableCell"]), Paragraph("ORBITA COMMAND", styles["TableCell"])],
        [Paragraph("<b>Type:</b>", styles["TableCell"]), Paragraph("Web application for mission management", styles["TableCell"])],
        [Paragraph("<b>Stack:</b>", styles["TableCell"]), Paragraph("Python, Flask, SQLite, Gemini", styles["TableCell"])],
        [Paragraph("<b>Date:</b>", styles["TableCell"]), Paragraph("March 20, 2026", styles["TableCell"])],
    ]
    table = Table(data, colWidths=[3.3 * cm, 9.0 * cm])
    table.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#C7C7D8")),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def make_toc(styles):
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(
            name="TOCLevel1",
            fontName="Times-Bold",
            fontSize=11,
            leading=15,
            leftIndent=0,
            firstLineIndent=0,
            textColor=colors.HexColor("#7053B8"),
        ),
        ParagraphStyle(
            name="TOCLevel2",
            fontName="Times-Roman",
            fontSize=10,
            leading=14,
            leftIndent=16,
            firstLineIndent=0,
            textColor=colors.HexColor("#6B6F7A"),
        ),
    ]
    toc.dotsMinLevel = 0
    return toc


def heading(text, style, level):
    para = Paragraph(escape(text), style)
    para.toc_level = level
    return para


def parse_document(text, styles):
    story = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 0.15 * cm))
            continue
        if stripped.startswith("# "):
            continue
        if stripped.startswith("## "):
            story.append(Spacer(1, 0.10 * cm))
            story.append(heading(stripped[3:], styles["Heading1Custom"], 0))
            story.append(
                HRFlowable(
                    width="100%",
                    thickness=0.8,
                    color=colors.HexColor("#DDEDB8"),
                    spaceBefore=2,
                    spaceAfter=8,
                )
            )
        elif stripped.startswith("### "):
            story.append(heading(stripped[4:], styles["Heading2Custom"], 1))
        elif stripped.startswith("- "):
            story.append(
                Paragraph(escape(stripped[2:]), styles["BulletCustom"], bulletText="•")
            )
        else:
            story.append(Paragraph(escape(stripped), styles["BodyCustom"]))
    return story


def build_story(text, styles):
    story = [
        Spacer(1, 2.6 * cm),
        Paragraph(SUBTITLE, styles["CoverTitle"]),
        Paragraph(TITLE, styles["CoverAccent"]),
        Paragraph("Mission Management Platform", styles["CoverMeta"]),
        Paragraph(TAGLINE, styles["CoverMeta"]),
        Spacer(1, 0.9 * cm),
        make_objective_box(styles),
        Spacer(1, 1.0 * cm),
        make_snapshot_table(styles),
        Spacer(1, 1.4 * cm),
        make_meta_table(styles),
        PageBreak(),
        Paragraph("Contents", styles["TocHeading"]),
        HRFlowable(width="100%", thickness=0.9, color=colors.HexColor("#DDEDB8"), spaceBefore=3, spaceAfter=10),
        make_toc(styles),
        PageBreak(),
    ]

    story.extend(parse_document(text, styles))
    return story


def main():
    styles = build_styles()
    text = SOURCE.read_text(encoding="utf-8")
    story = build_story(text, styles)
    doc = ProjectDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        title="ORBITA COMMAND - Technical Project Report",
        author="Codex",
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        topMargin=2.2 * cm,
        bottomMargin=1.6 * cm,
    )
    doc.multiBuild(story, onFirstPage=lambda c, d: None, onLaterPages=draw_later_pages)
    print(OUTPUT)


if __name__ == "__main__":
    main()
