from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

BLACK = RGBColor(0, 0, 0)
BLUE = "1F4E78"
LIGHT_BLUE = "D9EAF7"
LIGHT_GRAY = "F2F2F2"
BORDER = "D9D9D9"


def _set_font(run, name: str = "Times New Roman", size: float = 14, bold: bool | None = None, italic: bool | None = None):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.font.color.rgb = BLACK
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    return run


def _shade(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def _set_cell_margins(cell, top=100, start=100, bottom=100, end=100) -> None:
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


def _set_table_borders(table) -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        node = borders.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            borders.append(node)
        node.set(qn("w:val"), "single")
        node.set(qn("w:sz"), "4")
        node.set(qn("w:color"), BORDER)


def _repeat_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def _keep_row_together(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    if tr_pr.find(qn("w:cantSplit")) is None:
        tr_pr.append(OxmlElement("w:cantSplit"))


def _add_page_field(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.extend([fld_begin, instr, fld_sep, text, fld_end])
    _set_font(run, size=12)


def _add_toc(document: Document) -> None:
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.first_line_indent = Cm(0)
    run = p.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = ' TOC \\o "1-3" \\h \\z \\u '
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    cached = OxmlElement("w:t")
    cached.text = "Обновляемое оглавление: выделите поле и нажмите F9 в Microsoft Word"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, cached, end])
    _set_font(run, size=12, italic=True)
    entries = [
        ("ВВЕДЕНИЕ", "3"),
        ("ГЛАВА 1 ТЕОРЕТИЧЕСКИЕ ОСНОВЫ ОПРЕДЕЛЕНИЯ ТОКСИЧНОСТИ", "5"),
        ("ГЛАВА 2 ПОДГОТОВКА ДАННЫХ И РЕАЛИЗАЦИЯ МОДЕЛЕЙ", "12"),
        ("ГЛАВА 3 ЭКСПЕРИМЕНТАЛЬНОЕ ИССЛЕДОВАНИЕ", "19"),
        ("ЗАКЛЮЧЕНИЕ", "28"),
        ("СПИСОК ЛИТЕРАТУРЫ", "29"),
        ("ПРИЛОЖЕНИЕ А ПАРАМЕТРЫ ЭКСПЕРИМЕНТОВ", "32"),
        ("ПРИЛОЖЕНИЕ Б ФРАГМЕНТЫ ИСХОДНОГО КОДА", "33"),
        ("ПРИЛОЖЕНИЕ В ИНСТРУКЦИЯ ПО ЗАПУСКУ", "34"),
    ]
    for title, page in entries:
        p = document.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.space_after = Pt(3)
        run = p.add_run(f"{title} {'.' * max(4, 72 - len(title))} {page}")
        _set_font(run, size=12)


def _set_update_fields(document: Document) -> None:
    settings = document.settings._element
    update = settings.find(qn("w:updateFields"))
    if update is None:
        update = OxmlElement("w:updateFields")
        settings.append(update)
    update.set(qn("w:val"), "true")


def _fraction(parent, numerator: str, denominator: str) -> None:
    frac = OxmlElement("m:f")
    num = OxmlElement("m:num")
    den = OxmlElement("m:den")
    for container, value in ((num, numerator), (den, denominator)):
        run = OxmlElement("m:r")
        text = OxmlElement("m:t")
        text.text = value
        run.append(text)
        container.append(run)
    frac.extend([num, den])
    parent.append(frac)


def add_equation(document: Document, prefix: str, numerator: str, denominator: str, suffix: str = "") -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.first_line_indent = Cm(0)
    math_para = OxmlElement("m:oMathPara")
    math = OxmlElement("m:oMath")
    if prefix:
        run = OxmlElement("m:r")
        text = OxmlElement("m:t")
        text.text = prefix
        run.append(text)
        math.append(run)
    _fraction(math, numerator, denominator)
    if suffix:
        run = OxmlElement("m:r")
        text = OxmlElement("m:t")
        text.text = suffix
        run.append(text)
        math.append(run)
    math_para.append(math)
    paragraph._p.append(math_para)


def add_body(document: Document, text: str, *, no_indent: bool = False, keep_with_next: bool = False) -> None:
    p = document.add_paragraph(style="Normal")
    p.paragraph_format.first_line_indent = Cm(0 if no_indent else 1.25)
    p.paragraph_format.keep_with_next = keep_with_next
    p.add_run(text)


def add_bullets(document: Document, items: Iterable[str]) -> None:
    for item in items:
        p = document.add_paragraph(style="List Bullet")
        p.paragraph_format.left_indent = Cm(1.25)
        p.paragraph_format.first_line_indent = Cm(-0.5)
        p.add_run(item)


def add_table(document: Document, headers: list[str], rows: list[list[str]], widths: list[float] | None = None) -> None:
    table = document.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    _set_table_borders(table)
    _repeat_header(table.rows[0])
    _keep_row_together(table.rows[0])
    for idx, header in enumerate(headers):
        cell = table.rows[0].cells[idx]
        _shade(cell, BLUE)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        _set_cell_margins(cell)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        run = p.add_run(header)
        _set_font(run, size=10.5, bold=True)
        run.font.color.rgb = RGBColor(255, 255, 255)
    for row_index, values in enumerate(rows):
        added_row = table.add_row()
        _keep_row_together(added_row)
        cells = added_row.cells
        for idx, value in enumerate(values):
            cell = cells[idx]
            if row_index % 2:
                _shade(cell, LIGHT_GRAY)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            _set_cell_margins(cell)
            p = cell.paragraphs[0]
            p.paragraph_format.first_line_indent = Cm(0)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if len(str(value)) > 18 else WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(str(value))
            _set_font(run, size=10.5)
    if widths:
        for row in table.rows:
            for idx, width in enumerate(widths):
                row.cells[idx].width = Cm(width)
    document.add_paragraph().paragraph_format.space_after = Pt(0)


def add_caption(document: Document, text: str) -> None:
    p = document.add_paragraph(style="Caption")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.keep_with_next = False
    p.add_run(text)


def add_figure(document: Document, path: Path, caption: str, width_cm: float = 12.4) -> None:
    if not path.exists():
        return
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.keep_with_next = True
    picture = p.add_run().add_picture(str(path), width=Cm(width_cm))
    picture._inline.docPr.set("descr", caption)
    picture._inline.docPr.set("title", caption)
    add_caption(document, caption)


def _make_architecture_figures(figures_dir: Path) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    pipeline_path = figures_dir / "project_pipeline.png"
    families_path = figures_dir / "model_families.png"
    if pipeline_path.exists() and families_path.exists():
        return
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 10})
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.axis("off")
    boxes = [
        (0.02, "Официальные\nархивы Kaggle"),
        (0.21, "Проверка,\nдедупликация"),
        (0.40, "Split\n70 / 15 / 15"),
        (0.59, "BoW / TF-IDF\nили tokenizer"),
        (0.78, "Обучение,\nvalidation, test"),
    ]
    for x, label in boxes:
        patch = plt.Rectangle((x, 0.38), 0.16, 0.28, facecolor="#D9EAF7", edgecolor="#1F4E78", linewidth=1.5)
        ax.add_patch(patch)
        ax.text(x + 0.08, 0.52, label, ha="center", va="center")
    for x in (0.18, 0.37, 0.56, 0.75):
        ax.annotate("", xy=(x + 0.025, 0.52), xytext=(x - 0.015, 0.52), arrowprops=dict(arrowstyle="->", color="#1F4E78", lw=1.5))
    ax.text(0.5, 0.84, "Воспроизводимый конвейер исследования", ha="center", fontsize=14, weight="bold")
    fig.savefig(pipeline_path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.axis("off")
    ax.text(0.5, 0.92, "Два семейства моделей", ha="center", fontsize=14, weight="bold")
    ax.add_patch(plt.Rectangle((0.05, 0.55), 0.40, 0.25, facecolor="#F2F2F2", edgecolor="#555555"))
    ax.add_patch(plt.Rectangle((0.55, 0.55), 0.40, 0.25, facecolor="#D9EAF7", edgecolor="#1F4E78"))
    ax.text(0.25, 0.72, "Классический путь", ha="center", weight="bold")
    ax.text(0.25, 0.62, "очистка → разреженная матрица\n→ NB / Logistic Regression / Linear SVM", ha="center")
    ax.text(0.75, 0.72, "Трансформерный путь", ha="center", weight="bold")
    ax.text(0.75, 0.62, "минимальная очистка → WordPiece\n→ DistilBERT → классификационная голова", ha="center")
    ax.annotate("", xy=(0.5, 0.43), xytext=(0.25, 0.55), arrowprops=dict(arrowstyle="->", color="#555555"))
    ax.annotate("", xy=(0.5, 0.43), xytext=(0.75, 0.55), arrowprops=dict(arrowstyle="->", color="#1F4E78"))
    ax.add_patch(plt.Rectangle((0.30, 0.18), 0.40, 0.25, facecolor="#FFFFFF", edgecolor="#1F4E78", linewidth=1.5))
    ax.text(0.5, 0.31, "Единый тестовый набор", ha="center", weight="bold")
    ax.text(0.5, 0.23, "F1, PR-AUC, ROC-AUC, Precision, Recall,\nматрица ошибок и качественный анализ", ha="center")
    fig.savefig(families_path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _configure_document(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(3)
    section.right_margin = Cm(1.5)
    section.different_first_page_header_footer = True
    _add_page_field(section.footer.paragraphs[0])

    styles = document.styles
    normal = styles["Normal"]
    normal.font.name = "Times New Roman"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    normal.font.size = Pt(14)
    normal.font.color.rgb = BLACK
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.widow_control = True

    for name, size, before, after in (("Title", 16, 0, 12), ("Heading 1", 16, 12, 8), ("Heading 2", 14, 10, 5), ("Heading 3", 14, 8, 4)):
        style = styles[name]
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = BLACK
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.page_break_before = name == "Heading 1"
        style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER if name in {"Title", "Heading 1"} else WD_ALIGN_PARAGRAPH.LEFT
        if name == "Title":
            p_pr = style._element.get_or_add_pPr()
            border = p_pr.find(qn("w:pBdr"))
            if border is not None:
                p_pr.remove(border)

    caption = styles["Caption"]
    caption.font.name = "Times New Roman"
    caption._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    caption._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    caption.font.size = Pt(12)
    caption.font.color.rgb = BLACK
    caption.paragraph_format.space_after = Pt(6)

    code = styles.add_style("Code Block", WD_STYLE_TYPE.PARAGRAPH)
    code.font.name = "Courier New"
    code._element.rPr.rFonts.set(qn("w:ascii"), "Courier New")
    code._element.rPr.rFonts.set(qn("w:hAnsi"), "Courier New")
    code.font.size = Pt(9)
    code.paragraph_format.left_indent = Cm(0.5)
    code.paragraph_format.right_indent = Cm(0.5)
    code.paragraph_format.space_before = Pt(4)
    code.paragraph_format.space_after = Pt(4)
    code.paragraph_format.line_spacing = 1.0
    _set_update_fields(document)


def _title_page(document: Document) -> None:
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.add_run("[НАЗВАНИЕ УНИВЕРСИТЕТА]\n[ФАКУЛЬТЕТ]\n[КАФЕДРА]")
    for run in p.runs:
        _set_font(run, size=14)
    for _ in range(4):
        document.add_paragraph()
    p = document.add_paragraph(style="Title")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("КУРСОВАЯ РАБОТА")
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    r = p.add_run("по дисциплине «Анализ больших текстовых данных и текстовый поиск»")
    _set_font(r, size=14)
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    r = p.add_run("Определение токсичных комментариев с использованием методов машинного обучения и трансформерных моделей")
    _set_font(r, size=16, bold=True)
    for _ in range(3):
        document.add_paragraph()
    table = document.add_table(rows=4, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.RIGHT
    table.autofit = False
    # Mark the first row for assistive technologies as the label/value header
    # of this small metadata table. The table never spans multiple pages, so
    # the repeat-header behavior does not affect the visual title-page layout.
    _repeat_header(table.rows[0])
    labels = ["Выполнил(а):", "Группа:", "Руководитель:", "Оценка:"]
    values = ["[Ф.И.О. студента]", "[номер группы]", "[Ф.И.О., должность]", "________________"]
    for row, label, value in zip(table.rows, labels, values, strict=False):
        row.cells[0].text = label
        row.cells[1].text = value
        for cell in row.cells:
            cell.width = Cm(6)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.first_line_indent = Cm(0)
                for run in paragraph.runs:
                    _set_font(run, size=14)
    # Intentionally remove borders from the title-page metadata table.
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        node = OxmlElement(f"w:{edge}")
        node.set(qn("w:val"), "nil")
        borders.append(node)
    tbl_pr.append(borders)
    for _ in range(5):
        document.add_paragraph()
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    r = p.add_run("[ГОРОД]\n2026")
    _set_font(r, size=14)
    p.add_run().add_break(WD_BREAK.PAGE)


def _metric_rows(results: pd.DataFrame) -> list[list[str]]:
    display_names = {
        "bow_multinomial_nb": "BoW + NB",
        "tfidf_logistic_regression": "TF-IDF + LR",
        "tfidf_linear_svm": "TF-IDF + Linear SVM",
        "distilbert": "DistilBERT",
    }
    rows = []
    for _, row in results.iterrows():
        rows.append([
            display_names.get(str(row["model"]), str(row["model"])),
            f"{row['test_accuracy']:.4f}",
            f"{row['test_precision']:.4f}",
            f"{row['test_recall']:.4f}",
            f"{row['test_f1']:.4f}",
            f"{row['test_roc_auc']:.4f}",
            f"{row['test_pr_auc']:.4f}",
        ])
    return rows


def build_report(config: dict, paths) -> Path:
    _make_architecture_figures(paths.figures_dir)
    document = Document()
    _configure_document(document)
    _title_page(document)

    document.add_heading("СОДЕРЖАНИЕ", level=1)
    _add_toc(document)

    document.add_heading("ВВЕДЕНИЕ", level=1)
    intro = [
        "Открытые интернет-платформы позволяют пользователям быстро обмениваться знаниями, обсуждать общественные события и совместно создавать контент. Та же доступность снижает барьер для публикации оскорблений, угроз, травли и высказываний, которые вытесняют участников из дискуссии. При большом потоке сообщений ручная модерация не обеспечивает ни требуемой скорости реакции, ни одинакового применения правил. Поэтому автоматическое определение токсичности рассматривается как инструмент предварительной фильтрации и приоритизации сообщений для последующего решения модератора.",
        "Задача сложнее поиска списка запрещённых слов. Нецензурная лексика может встречаться в цитате, самоиронии или нейтральном обсуждении; токсичное намерение, напротив, может выражаться без явной брани через сарказм, намёк или завуалированное унижение. Значение фразы зависит от отрицания, адресата и контекста, а распределение токсичных сообщений обычно несбалансировано. По этой причине полезно сопоставить интерпретируемые лексические модели с контекстными трансформерами и оценивать их не только по Accuracy, но и по F1 и площади под Precision-Recall-кривой.",
        "Цель работы — разработать воспроизводимый программный конвейер бинарной классификации токсичных англоязычных комментариев и исследовать различия между Bag of Words, TF-IDF с линейными классификаторами и fine-tuning DistilBERT. Для достижения цели требуется загрузить и проверить официальный набор Jigsaw Toxic Comment Classification Challenge, исключить утечки между выборками, реализовать несколько режимов очистки, обучить модели на едином разбиении, подобрать гиперпараметры и порог только по validation, а затем провести количественный и качественный анализ ошибок на test.",
        "Объект исследования — англоязычные пользовательские комментарии Wikipedia, размеченные организаторами Jigsaw по категориям токсичности. Предмет исследования — методы представления текста и алгоритмы supervised learning, применяемые для оценки бинарного признака toxic. Используются статистический анализ корпуса, разреженные векторные представления, вероятностная и линейная классификация, трансферное обучение, стратифицированное разбиение и набор метрик для несбалансированной классификации.",
        "Практический результат оформлен как выполненный Jupyter Notebook с последовательными Markdown-разделами и Python-ячейками, а также как набор повторно используемых модулей. Notebook сохраняет идентификаторы split, модели, предсказания, таблицы, рисунки и пересобирает Word-отчёт из фактических артефактов. Тяжёлое обучение DistilBERT включается только явным параметром RUN_BERT; быстрый режим предназначен для технической проверки и не смешивается с итоговыми экспериментами.",
        "Для текущего экземпляра использован предоставленный архив Jigsaw, содержащий train.csv, test.csv, test_labels.csv и sample_submission.csv. Notebook выполнен без ошибок на полном тренировочном наборе: проведены EDA, стратифицированное разбиение и 16 классических прогонов. Fine-tuning DistilBERT не запускался из-за отсутствия установленного PyTorch-стека и выделенного вычислительного ресурса; его реализация и отдельная управляемая ячейка сохранены.",
        "Работа состоит из трёх глав. Первая систематизирует теоретические основания задачи и метрик. Вторая описывает набор данных, контроль качества, предобработку и реализацию моделей. Третья задаёт экспериментальный протокол, рассматривает интерпретацию результатов и анализ ошибок, а также отдельно фиксирует статус воспроизведения в текущем окружении. В приложениях приведены параметры запуска и фрагменты исходного кода.",
    ]
    for paragraph in intro:
        add_body(document, paragraph)

    document.add_heading("ГЛАВА 1 ТЕОРЕТИЧЕСКИЕ ОСНОВЫ ОПРЕДЕЛЕНИЯ ТОКСИЧНОСТИ", level=1)
    document.add_heading("1.1 Задача определения токсичности текста", level=2)
    for text in [
        "Бинарная классификация сопоставляет каждому комментарию x метку y из множества {0, 1}, где единица означает токсичность. Модель строит оценку s(x), а окончательное решение зависит от порога t. В реальной системе оценка может использоваться не только для блокировки: сообщения с высоким риском направляются на срочную проверку, пограничные случаи — модератору, а низкорисковые публикуются без задержки. Такое представление подчёркивает, что выбор порога является частью эксплуатационной политики, а не неизменным свойством алгоритма.",
        "Разметка токсичности субъективна. Разные аннотаторы неодинаково воспринимают резкость, иронию и упоминания социальных групп. Wulczyn, Thain и Dixon показали, что массовую разметку персональных атак можно сочетать с машинным обучением, однако интерпретация результата должна учитывать агрегирование человеческих суждений. Jigsaw использует несколько категорий, из которых в данной работе основная метка toxic сведена к бинарной задаче, а остальные признаки служат дополнительным материалом для анализа ошибок.",
        "Автоматический классификатор не заменяет правила сообщества. Токсичность связана с коммуникационным эффектом, тогда как конкретная платформа может отдельно регулировать угрозы, спам, преследование или обсуждение запрещённых тем. Следовательно, модель должна рассматриваться как компонент более широкой системы, где есть журнал решений, процедура обжалования и мониторинг ошибок для различных типов высказываний.",
    ]:
        add_body(document, text)

    document.add_heading("1.2 Особенности токсичных комментариев", level=2)
    for text in [
        "Лексические признаки токсичности включают оскорбления, обсценную лексику, императивы и усилители, однако их наличие не гарантирует токсичную направленность. Цитирование чужой реплики, обсуждение значения слова или дружеское употребление жаргона создают ложноположительные примеры. С другой стороны, унижение может быть выражено внешне вежливо: «очевидно, вы не способны понять» не содержит запрещённого слова, но адресно снижает статус собеседника.",
        "Важную роль играют отрицания и композиция. При механическом удалении not фразы «you are stupid» и «you are not stupid» становятся почти неразличимыми. Пунктуация, повторение заглавных букв и многочисленные восклицательные знаки также несут прагматическую информацию. Поэтому предобработка не должна автоматически уничтожать все символы, а список stopwords обязан сохранять отрицательные частицы.",
        "Пользователи могут маскировать токены заменой букв цифрами, звёздочками или разделителями. Обычный словарь признаков воспринимает каждую форму как новый элемент и хуже обобщает редкие варианты. Субсловная токенизация DistilBERT частично решает эту проблему, но чрезмерно искажённое написание всё равно распадается на малосодержательные фрагменты. Длинные комментарии добавляют ещё одну трудность: токсичная фраза может занимать небольшую часть текста, а трансформер видит только ограниченное число токенов после усечения.",
        "Классификаторы способны усваивать нежелательные корреляции между упоминанием идентичности и токсичной меткой. Borkan и соавторы показали необходимость отдельных проверок для подгрупп, поскольку высокая агрегированная AUC не гарантирует одинакового поведения на фразах об идентичностях. В текущем проекте поле identity_hate используется при анализе ошибок, однако полноценная оценка fairness требует дополнительных identity-аннотаций, которых основной train Jigsaw не предоставляет в достаточном виде.",
    ]:
        add_body(document, text)

    document.add_heading("1.3 Предобработка естественного языка", level=2)
    for text in [
        "Предобработка должна соответствовать модели. Для варианта A выполняется только нормализация пробельных символов и удаление нулевого байта. Этот режим сохраняет исходные слова, пунктуацию и порядок, поэтому подходит как безопасная базовая линия. Вариант B декодирует HTML, заменяет URL специальным токеном, удаляет теги, переводит текст в нижний регистр и применяет регулярное выражение токенизации. Вариант C дополнительно удаляет английские stopwords и выполняет лемматизацию WordNet, но сохраняет отрицания no, not, nor и never.",
        "Расширенная очистка уменьшает размер словаря, однако не обязана повышать качество. Лемматизация может объединить формы, различающиеся по стилистике, а удаление функциональных слов — разрушить устойчивые n-граммы. В токсичных сообщениях повторение, неправильная грамматика и пунктуация сами являются сигналами. Поэтому влияние очистки проверяется эмпирически при неизменном TF-IDF и Logistic Regression, а лучший вариант выбирается только по validation.",
        "Для DistilBERT используется минимальная техническая очистка. Токенизатор модели добавляет служебные токены, формирует input_ids и attention_mask, выполняет усечение до max_length и динамическое дополнение внутри batch. Попытка предварительно лемматизировать такой текст нарушила бы распределение, на котором модель была предобучена, и удалила бы контекстные различия, которые трансформер способен использовать.",
    ]:
        add_body(document, text)

    document.add_heading("1.4 Bag of Words и TF-IDF", level=2)
    for text in [
        "Bag of Words представляет документ вектором частот токенов. Порядок слов теряется, но добавление биграмм частично восстанавливает локальные сочетания: выражения not good и very good получают отдельные координаты. Разреженность делает представление экономичным для линейных алгоритмов, хотя размерность словаря может достигать десятков и сотен тысяч признаков.",
        "TF-IDF уменьшает вес слов, встречающихся почти во всех документах, и повышает относительную значимость специфичных терминов. В проекте используется сглаженный IDF библиотеки scikit-learn и L2-нормализация документа. Параметр sublinear_tf заменяет абсолютную частоту на логарифмически масштабированную, поэтому многократное повторение одного слова не увеличивает влияние линейно.",
    ]:
        add_body(document, text)
    add_equation(document, "TF-IDF(t,d) = tf(t,d) × log ", "N + 1", "df(t) + 1", " + 1")
    add_body(document, "В формуле N обозначает число документов обучающей выборки, а df(t) — количество документов, содержащих термин t. Векторизатор обучается только на train внутри Pipeline. Validation и test преобразуются уже зафиксированным словарём и IDF; это исключает утечку статистики будущих данных.")

    document.add_heading("1.5 Классические алгоритмы классификации", level=2)
    for text in [
        "Multinomial Naive Bayes моделирует частоты признаков при условии класса и предполагает условную независимость токенов. Предположение не выполняется буквально, однако алгоритм остаётся сильной и быстрой базовой линией для счётчиков слов. Параметр сглаживания alpha предотвращает нулевые вероятности для признаков, отсутствовавших в одном из классов.",
        "Logistic Regression оценивает линейную комбинацию TF-IDF-признаков и преобразует её сигмоидой в значение от нуля до единицы. L2-регуляризация ограничивает нормы коэффициентов, а параметр C задаёт обратную силу регуляризации. Для дисбаланса используется class_weight='balanced'; при этом итоговый порог всё равно подбирается отдельно, поскольку значение 0,5 не обязано максимизировать F1.",
        "Linear SVM максимизирует зазор между классами в пространстве разреженных признаков и хорошо масштабируется на большое число координат. Метод возвращает decision_function, а не калиброванную вероятность. Поэтому ROC-AUC и Average Precision вычисляются по ранжирующей оценке, но в отчёте она не интерпретируется как вероятность токсичности. Если продукту нужны вероятности, калибровка должна выполняться на train/validation без обращения к test.",
    ]:
        add_body(document, text)

    document.add_heading("1.6 Архитектура Transformer BERT и DistilBERT", level=2)
    for text in [
        "Transformer заменил рекуррентную обработку механизмом self-attention, который позволяет каждому токену агрегировать информацию о других позициях. Scaled dot-product attention вычисляет сходство запросов и ключей, нормализует его softmax и формирует взвешенную сумму значений. Multi-head attention повторяет операцию в нескольких подпространствах, что позволяет моделировать разные типы отношений.",
        "BERT предобучается двунаправленно и затем адаптируется к новой задаче небольшой классификационной головой. Входное представление учитывает токен и позицию, а скрытое состояние первого служебного токена используется для классификации последовательности. Fine-tuning обновляет как голову, так и веса энкодера, поэтому небольшая скорость обучения и контроль validation loss важны для сохранения предобученных знаний.",
        "DistilBERT получен дистилляцией BERT: модель меньше исходной примерно на 40% и предназначена для более дешёвого вывода, сохраняя значительную часть языковых способностей. Для учебного эксперимента это разумный компромисс между контекстным качеством и доступными ресурсами. Используется именно базовая предобученная модель distilbert-base-uncased, а не готовый токсичностный классификатор; классификационная голова обучается на Jigsaw.",
        "Ограничение max_length означает, что конец длинного комментария может быть отброшен. Эксперимент с длинами 128 и 256 токенов позволяет оценить компромисс между покрытием текста, памятью и временем. Другой вариант сравнения — одна и две эпохи либо learning rate 2e-5 и 3e-5. Такие прогоны должны использовать одинаковую обучающую подвыборку, иначе различие качества нельзя связывать только с гиперпараметром.",
    ]:
        add_body(document, text)

    document.add_heading("1.7 Метрики и несбалансированные данные", level=2)
    for text in [
        "Accuracy отражает долю правильных решений, но при редком положительном классе может быть высокой у бесполезного классификатора, всегда выбирающего ноль. Precision показывает, какая часть срабатываний действительно токсична; Recall — какая часть всех токсичных комментариев найдена. F1 является гармоническим средним и резко снижается, если одна из двух составляющих мала.",
    ]:
        add_body(document, text)
    add_equation(document, "Accuracy = ", "TP + TN", "TP + TN + FP + FN")
    add_equation(document, "Precision = ", "TP", "TP + FP")
    add_equation(document, "Recall = ", "TP", "TP + FN")
    add_equation(document, "F1 = ", "2 × Precision × Recall", "Precision + Recall")
    for text in [
        "ROC-AUC оценивает способность ранжировать положительные объекты выше отрицательных по всем порогам. При сильном дисбалансе PR-AUC или Average Precision лучше фокусируется на качестве положительных срабатываний, поэтому в работе F1 и PR-AUC являются основными метриками. Матрица ошибок сохраняет абсолютные количества TN, FP, FN и TP и помогает связать агрегированные оценки с нагрузкой на модераторов.",
        "Порог выбирается по максимальному F1 на validation. Этот шаг не использует test: иначе тестовая выборка превращается в часть настройки и перестаёт быть независимой оценкой. Дополнительно график Precision-Recall показывает, как снижение порога повышает полноту ценой большего числа ложных срабатываний. Для эксплуатации порог может выбираться по допустимой стоимости FN и FP, а не только по F1.",
        "Обучение DistilBERT использует cross-entropy по двум логитам. Функция потерь штрафует низкую вероятность истинного класса; её минимизация не гарантирует калибровку вероятностей, поэтому после обучения всё равно оцениваются ранжирующие и пороговые метрики. При необходимости калибровка должна рассматриваться отдельным экспериментом.",
    ]:
        add_body(document, text)
    document.add_heading("Выводы по главе 1", level=2)
    add_body(document, "Определение токсичности требует одновременно учитывать лексические сигналы, контекст и дисбаланс классов. Разреженные представления дают быстрые и интерпретируемые базовые линии, тогда как DistilBERT способен использовать порядок и контекст, но требует больше ресурсов и аккуратной настройки. Корректное сравнение возможно только при едином разбиении, отсутствии утечки и приоритете F1 и PR-AUC над одной Accuracy.")

    document.add_heading("ГЛАВА 2 ПОДГОТОВКА ДАННЫХ И РЕАЛИЗАЦИЯ МОДЕЛЕЙ", level=1)
    document.add_heading("2.1 Обоснование выбора набора Jigsaw", level=2)
    for text in [
        "Jigsaw Toxic Comment Classification Challenge выбран потому, что он содержит реальные англоязычные комментарии Wikipedia и многометочную разметку по шести видам токсичности. Объём порядка 159 тысяч тренировочных записей достаточен для разреженных моделей и fine-tuning трансформера. Наличие идентификатора, исходного текста и отдельных меток позволяет сформулировать основную бинарную задачу и использовать дополнительные категории при качественном разборе ошибок.",
        "Набор распространяется через Kaggle на условиях соревнования. Проект вызывает kagglehub.competition_download и не пытается обходить авторизацию или принятие правил. Предусмотрен ручной путь: официальные архивы помещаются в data/raw, после чего безопасно распаковываются с проверкой путей внутри ZIP. Такой подход сохраняет юридическую и исследовательскую воспроизводимость источника.",
    ]:
        add_body(document, text)

    document.add_heading("2.2 Контроль качества и фактический статус данных", level=2)
    status_path = paths.results_dir / "execution_status.json"
    status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
    eda_path = paths.results_dir / "eda_summary.json"
    if eda_path.exists():
        eda = json.loads(eda_path.read_text(encoding="utf-8"))
        add_table(document, ["Показатель", "Значение"], [
            ["Строк", f"{eda['rows']:,}"], ["Столбцов", str(eda["columns"])],
            ["Полных дубликатов", str(eda["full_duplicate_rows"])],
            ["Строк в группах одинаковых текстов", str(eda["duplicate_text_rows"])],
            ["Доля toxic", f"{eda['toxic_share']:.4%}"],
            ["Доля non-toxic", f"{eda['non_toxic_share']:.4%}"],
        ], widths=[9, 6])
        add_caption(document, "Таблица 1 — Фактические характеристики загруженного train.csv")
        add_body(document, "Таблица сформирована непосредственно из eda_summary.json текущего запуска. Проверяются размеры файла, пропуски по каждому столбцу, полные дубликаты, повторяющиеся тексты, уникальность ID, распределение всех меток и статистики длины. Перед разбиением одинаковые comment_text удаляются, поэтому точное пересечение текстов между train, validation и test становится невозможным.")
    else:
        reason = status.get("dataset_download", {}).get("reason", "официальный train.csv отсутствует")
        if "UnauthenticatedError" in reason:
            reason = "UnauthenticatedError: User is not authenticated"
        add_table(document, ["Этап", "Статус", "Подтверждённая причина"], [
            ["Загрузка Kaggle", "Не выполнена", reason],
            ["EDA", "Не выполнен", "Нет официального train.csv"],
            ["Классические модели", "Не обучены", "Нет официального train.csv"],
            ["DistilBERT", "Не обучен", "Нет официального train.csv"],
        ], widths=[4.2, 3.2, 7.5])
        add_caption(document, "Таблица 1 — Статус воспроизведения экспериментов в текущем окружении")
        add_body(document, "KaggleHub вернул UnauthenticatedError. Это является внешним ограничением доступа, а не результатом анализа корпуса. Поэтому в документе отсутствуют утверждения о реальном распределении классов, длинах, частотах слов и достигнутых метриках. После команды kagglehub login либо ручного помещения официальных архивов в data/raw код автоматически создаёт соответствующие таблицы и рисунки.")

    document.add_heading("2.3 Исследовательский анализ данных", level=2)
    for text in [
        "Модуль EDA сначала вычисляет число строк и столбцов, размер исходного файла, пропуски, полные дубликаты, дубликаты comment_text и уникальные ID. Затем для каждой из шести меток подсчитываются положительные значения и доли. Длины измеряются отдельно в символах и словах; сохраняются среднее, медиана, 95-й перцентиль и максимум. Такие статистики позволяют обосновать max_length трансформера и обнаружить аномально длинные записи.",
        "Графики строятся в PNG с 220 DPI. Для распределений длины хвост визуально ограничивается, но исходные числовые статистики не обрезаются. Частотный анализ выполняется отдельно для toxic=1 и toxic=0; из списка исключается небольшой набор служебных английских слов, но не оскорбительная лексика. Матрица совместной встречаемости рассчитывается как произведение транспонированной матрицы меток на саму матрицу.",
        "Любой вывод о частом слове или доле класса должен появляться только после фактического запуска. Это требование особенно важно для данного набора: приблизительное число строк известно из описания соревнования, но локальная версия архива и обработка дубликатов могут изменить количество объектов, реально участвующих в моделировании.",
    ]:
        add_body(document, text)
    for filename, caption in [
        ("eda_target_distribution.png", "Рисунок 1 — Распределение целевого класса"),
        ("eda_all_labels.png", "Рисунок 2 — Распределение шести категорий токсичности"),
        ("eda_length_by_class.png", "Рисунок 3 — Сравнение длины токсичных и нетоксичных комментариев"),
        ("eda_label_cooccurrence.png", "Рисунок 4 — Совместная встречаемость меток"),
    ]:
        add_figure(document, paths.figures_dir / filename, caption)

    document.add_heading("2.4 Очистка и нормализация текстов", level=2)
    add_table(document, ["Вариант", "Операции", "Сохраняемые сигналы", "Риск"], [
        ["A minimal", "Пробелы, нулевой байт", "Регистр, пунктуация, исходные формы", "Большой словарь"],
        ["B standard", "HTML, URL, lowercase, токенизация", "Отрицания, ! и ?, слова", "Потеря регистра"],
        ["C extended", "B + stopwords + WordNet", "Отрицания и базовые леммы", "Потеря стилистики и n-грамм"],
        ["DistilBERT", "Только minimal + tokenizer", "Контекст и субслова", "Усечение длинных текстов"],
    ], widths=[2.8, 4.6, 4.6, 3.0])
    add_caption(document, "Таблица 2 — Реализованные варианты предобработки")
    add_body(document, "Функции очистки передаются в vectorizer как preprocessor. Следовательно, fit словаря и преобразование данных остаются частью sklearn Pipeline. Для extended требуется локальный ресурс NLTK stopwords и WordNet; отдельный скрипт загружает их явно, а отсутствие ресурса приводит к понятной ошибке вместо скрытого изменения алгоритма.")

    document.add_heading("2.5 Формирование выборок и защита от утечки", level=2)
    for text in [
        "Сначала удаляется повторное появление точного comment_text, затем данные делятся в два этапа: 70% отправляются в train, оставшиеся 30% делятся пополам на validation и test. Оба вызова train_test_split используют stratify=toxic и random_state=42. Идентификаторы и имя части сохраняются в data/processed/split_manifest.csv.",
        "При повторном запуске manifest не пересоздаётся. Код проверяет равенство множества ID текущего корпуса и сохранённого manifest; несоответствие останавливает программу. После объединения дополнительно сравниваются множества текстов всех трёх частей. TF-IDF и CountVectorizer находятся внутри Pipeline, поэтому методы fit получают только train. Validation используется для параметров и порога, test — для окончательной оценки.",
    ]:
        add_body(document, text)

    document.add_heading("2.6 Реализация классических моделей", level=2)
    for text in [
        "Первая базовая линия объединяет CountVectorizer с униграммами и биграммами и MultinomialNB(alpha=0.5). Вторая модель использует TfidfVectorizer и LogisticRegression с class_weight='balanced'. Третья модель заменяет классификатор на LinearSVC. Число признаков ограничивается конфигурацией, min_df удаляет слишком редкие признаки, а dtype=float32 снижает расход памяти разреженной матрицы.",
        "Эксперимент по предобработке фиксирует параметры TF-IDF и Logistic Regression, меняя только функцию очистки. Исследование TF-IDF включает униграммы против униграмм и биграмм, min_df, max_features и sublinear_tf. Для C используются компактные сетки: 0,5; 1; 2; 4 для Logistic Regression и 0,25; 0,5; 1; 2 для Linear SVM. Это ограничивает время, но позволяет увидеть форму зависимости на validation.",
        "После обучения сохраняются joblib-пайплайн и CSV тестовых предсказаний. Для вероятностных моделей берётся predict_proba, для SVM — decision_function. Функция выбора порога строит Precision-Recall-кривую по validation и максимизирует F1. Тот же порог применяется без изменения к test.",
    ]:
        add_body(document, text)

    document.add_heading("2.7 Реализация DistilBERT", level=2)
    for text in [
        "Модуль создаёт DatasetDict с полями id, text и label. AutoTokenizer загружает токенизатор distilbert-base-uncased, а batched map формирует входы с truncation и заданной максимальной длиной. DataCollatorWithPadding дополняет последовательности только до максимума текущего batch, что экономичнее глобального padding.",
        "AutoModelForSequenceClassification создаёт DistilBERT с двумя выходными логитами. TrainingArguments задаёт эпохи, learning rate, weight decay, warmup ratio, batch size, gradient accumulation, оценку и сохранение после каждой эпохи. На CUDA включается fp16, на совместимом Apple Silicon — MPS. Лучшая checkpoint выбирается по validation PR-AUC, а ранняя остановка ограничивает переобучение.",
        "После тренировки сохраняются веса, конфигурация и токенизатор. История Trainer экспортируется в JSON, из которого строятся train loss и validation loss. Вероятность положительного класса вычисляется softmax по логитам. Порог выбирается на validation, после чего тестовые оценки записываются в тот же формат, что и результаты классических моделей.",
    ]:
        add_body(document, text)

    document.add_heading("2.8 Программная архитектура", level=2)
    add_table(document, ["Модуль", "Ответственность", "Ключевые выходы"], [
        ["data.py", "Загрузка, ZIP, проверка, дубликаты, split", "split_manifest.csv"],
        ["eda.py", "Статистики и графики корпуса", "eda_summary.json, PNG"],
        ["preprocessing.py", "Три режима очистки", "Функции preprocessor"],
        ["classical.py", "Pipeline, настройка, порог", "joblib, CSV метрик"],
        ["bert.py", "Tokenizer, Trainer, fine-tuning", "checkpoint, история, CSV"],
        ["error_analysis.py", "FP/FN и наблюдаемые признаки", "error_analysis_*.csv"],
        ["report.py", "DOCX из артефактов запуска", "coursework.docx"],
        ["coursework_toxicity.ipynb", "Основной исследовательский сценарий", "выводы ячеек и все артефакты"],
    ], widths=[3, 7.3, 4.7])
    add_caption(document, "Таблица 3 — Модули проекта")
    add_body(document, "Основной пользовательский интерфейс — notebooks/coursework_toxicity.ipynb: в нём логически разделены загрузка, EDA, split, предобработка, модели, графики, анализ ошибок и генерация отчёта. Python-модули в src/toxicity сохраняют тестируемость и повторное использование, а main.py оставлен как командный интерфейс. Выполненный notebook содержит выводы всех 11 кодовых ячеек и не содержит исключений.")
    document.add_heading("Выводы по главе 2", level=2)
    add_body(document, "Разработанный конвейер обеспечивает воспроизводимость на уровне источника, split, конфигурации и выходных артефактов. Ключевые меры против утечки — дедупликация до разбиения, сохранение ID частей и обучение vectorizer только внутри train Pipeline. Классические и трансформерные модели приводятся к единому формату метрик и предсказаний, что делает дальнейшее сравнение технически корректным.")

    document.add_heading("ГЛАВА 3 ЭКСПЕРИМЕНТАЛЬНОЕ ИССЛЕДОВАНИЕ", level=1)
    document.add_heading("3.1 Условия и протокол экспериментов", level=2)
    for text in [
        "Полный классический эксперимент выполнен из Jupyter Notebook на официальном train.csv. После EDA создан и зафиксирован split: 111 699 строк train, 23 936 validation и 23 936 test. Гиперпараметры и порог сравнивались по validation, а одинаковый test использовался для итоговой оценки всех моделей. Демонстрационный режим quick при этом запуске не применялся.",
        "Основными критериями являются F1 и PR-AUC. Accuracy, Precision, Recall и ROC-AUC дополняют картину. Время fit измеряется одной машиной и интерпретируется только как ориентир, поскольку зависит от процессора, BLAS, GPU, batch size и кэша. Для DistilBERT дополнительно фиксируются модель, max_length, learning rate, число эпох, объём train и устройство.",
        "Честное сравнение DistilBERT с классическими моделями требует одинакового объёма train. Если трансформер обучается на стратифицированной подвыборке, его строка должна сопровождаться явным размером. Такой результат пригоден для оценки работоспособности и направления эффекта, но не для утверждения о превосходстве на полном корпусе.",
    ]:
        add_body(document, text)

    document.add_heading("3.2 Сравнение алгоритмов", level=2)
    all_results_path = paths.results_dir / "all_results.csv"
    if all_results_path.exists():
        results = pd.read_csv(all_results_path)
        primary = results[results["model"].isin(["bow_multinomial_nb", "tfidf_logistic_regression", "tfidf_linear_svm", "distilbert"])]
        add_table(document, ["Модель", "Accuracy", "Precision", "Recall", "F1", "ROC-AUC", "PR-AUC"], _metric_rows(primary), widths=[4.4, 1.75, 1.75, 1.75, 1.75, 1.75, 1.75])
        add_caption(document, "Таблица 4 — Фактические метрики на единой тестовой выборке")
        best = primary.sort_values("test_pr_auc", ascending=False).iloc[0]
        add_body(document, f"Наибольший PR-AUC в завершённом запуске показала модель {best['model']}: {best['test_pr_auc']:.4f}; её F1 равен {best['test_f1']:.4f}. Значения взяты из all_results.csv и не вычислялись вручную при формировании документа. Интерпретация Precision и Recall учитывает выбранный на validation порог {best['test_threshold']:.4f}.")
        for filename, caption in [
            ("results_f1_comparison.png", "Рисунок 5 — Сравнение F1-score моделей"),
            ("results_precision_recall.png", "Рисунок 6 — Precision и Recall"),
            ("results_roc_curves.png", "Рисунок 7 — ROC-кривые"),
            ("results_pr_curves.png", "Рисунок 8 — Precision-Recall-кривые"),
        ]:
            add_figure(document, paths.figures_dir / filename, caption)
    else:
        add_body(document, "Сводная таблица all_results.csv не создана, поскольку официальный датасет не был доступен без Kaggle-аутентификации. Численные значения для Naive Bayes, Logistic Regression, Linear SVM и DistilBERT сознательно не приводятся. После успешного запуска report.py автоматически вставит фактическую таблицу и четыре сравнительных графика из artifacts/figures.")
        add_table(document, ["Модель", "Реализация", "Фактический статус"], [
            ["BoW + MultinomialNB", "Готова", "Не обучена без train.csv"],
            ["TF-IDF + Logistic Regression", "Готова", "Не обучена без train.csv"],
            ["TF-IDF + Linear SVM", "Готова", "Не обучена без train.csv"],
            ["DistilBERT", "Готова", "Не обучена без train.csv"],
        ], widths=[5.3, 3.2, 6.5])
        add_caption(document, "Таблица 4 — Состояние реализаций без подмены экспериментальных результатов")

    document.add_heading("3.3 Влияние предобработки", level=2)
    for text in [
        "Эксперимент сравнивает minimal, standard и extended при одинаковом TF-IDF и Logistic Regression. Если extended уступает minimal, правдоподобное объяснение должно связываться с удалением функциональных слов, пунктуации или стилистических форм; однако причинность нельзя выводить только из одной разницы F1. Необходимо проверить ошибки, размер словаря и примеры, где предсказания изменились.",
        "Фактический результат подтвердил преимущество standard над minimal: test F1 вырос с 0,7753 до 0,7879, а PR-AUC — с 0,8610 до 0,8726. Extended дал F1=0,7836 и PR-AUC=0,8683, то есть лемматизация и удаление stopwords не улучшили standard. Вероятным механизмом standard является объединение регистра, URL и HTML без удаления отрицаний и пунктуационных маркеров; причинная интерпретация ограничена наблюдаемым сравнением.",
    ]:
        add_body(document, text)
    add_figure(document, paths.figures_dir / "results_preprocessing_influence.png", "Рисунок 9 — Влияние предобработки на F1 validation")

    document.add_heading("3.4 Параметры TF-IDF и классификаторов", level=2)
    for text in [
        "Биграммы позволяют кодировать короткие конструкции и отрицания, но увеличивают словарь и потребление памяти. min_df=5 сильнее удаляет редкие признаки, которые могут быть как шумом, так и важными маскированными оскорблениями. Ограничение max_features ускоряет обучение, однако способно отбросить редкие идентичностные или контекстные слова. sublinear_tf снижает эффект повторения одного токена.",
        "Параметр C управляет компромиссом между шириной зазора или силой регуляризации и точностью на train. Слишком большое C может усилить редкие корреляции, слишком малое — недообучить модель. График строится по validation F1; окончательный test не участвует в выборе. В таблице параметров сохраняется JSON каждой конфигурации, что позволяет точно восстановить прогон.",
    ]:
        add_body(document, text)
    add_figure(document, paths.figures_dir / "results_c_influence.png", "Рисунок 10 — Влияние C на F1 validation")

    document.add_heading("3.5 Результаты обучения DistilBERT", level=2)
    history = paths.results_dir / "distilbert_history.json"
    if history.exists():
        add_body(document, "История Trainer доступна и использована для построения кривых обучения. Снижение train loss при росте validation loss является признаком переобучения; стабильное снижение обеих величин поддерживает продолжение обучения. Решение о числе эпох принимается по validation PR-AUC и loss, а не по тестовым данным.")
        add_figure(document, paths.figures_dir / "bert_learning_curves.png", "Рисунок 11 — Train loss и validation loss DistilBERT")
    else:
        add_body(document, "Fine-tuning DistilBERT в текущем окружении не выполнялся: данные доступны, однако PyTorch, Transformers и веса модели не были установлены, а выделенный GPU отсутствовал. Notebook содержит отдельную ячейку RUN_BERT, а реализация включает токенизацию, attention masks через collator, обучение классификационной головы и энкодера, validation, выбор лучшей checkpoint, сохранение модели и получение вероятностей после softmax.")
    add_body(document, "Второй BERT-прогон следует проводить с одним изменённым фактором: например, max_length=128 против 256 при одинаковых эпохах и learning rate. Если ресурсов недостаточно, допустима одинаковая стратифицированная подвыборка. В отчёте должны быть указаны её размер и отличие от полного классического эксперимента.")

    document.add_heading("3.6 Качество и вычислительные затраты", level=2)
    for text in [
        "Классические модели обучаются на CPU и сохраняются компактным joblib-объектом вместе с vectorizer. Их сильная сторона — скорость, прозрачность коэффициентов и дешёвый вывод. Основные расходы связаны с построением словаря и разреженной матрицы, особенно при биграммах. Naive Bayes обычно самый быстрый, Logistic Regression и Linear SVM требуют итерационной оптимизации.",
        "DistilBERT не нуждается в словаре корпуса, но выполняет несколько слоёв attention для каждого batch. Время и память растут приблизительно квадратично с длиной последовательности внутри self-attention, поэтому max_length является существенным ресурсным параметром. GPU и mixed precision ускоряют обучение, однако воспроизводимость требует записывать тип устройства и версии библиотек.",
        "Выбор модели зависит от эксплуатационной цели. Линейная модель может быть предпочтительна при ограниченной задержке и необходимости объяснять ключевые n-граммы. Трансформер оправдан, если контекстное улучшение подтверждено на независимом test и компенсирует стоимость. Гибридная система может сначала применять дешёвый фильтр, а пограничные случаи направлять более тяжёлой модели.",
    ]:
        add_body(document, text)

    document.add_heading("3.7 Анализ ошибок классификации", level=2)
    for text in [
        "Модуль анализа выбирает false positive и false negative из реальных тестовых предсказаний. Для таблицы отчёта берутся по четыре примера каждого типа и фрагменты до 180 символов; в CSV сохраняются более длинные цитаты, истинная метка, решение, score, число слов и наблюдаемые категории: отрицание, возможный сарказм, обсценная лексика, маскированное слово, короткий или длинный текст. Эти категории являются эвристическими признаками, а не доказанной причиной ошибки.",
        "False positive с обсценным словом в нетоксичном контексте указывает на сильную лексическую корреляцию. False negative без явной брани может соответствовать завуалированному оскорблению. Ошибка на длинном сообщении у DistilBERT требует проверить, находился ли токсичный фрагмент после границы усечения. Ошибка рядом с отрицанием сравнивается между вариантами очистки, чтобы увидеть, сохранила ли модель конструкцию.",
        "Сарказм нельзя надёжно определить одним регулярным выражением. Маркер вроде «great job» лишь формирует кандидата для ручной проверки; вывод о сарказме делается после чтения фрагмента и, если доступно, контекста обсуждения. Аналогично маскированные символы не всегда означают токсичное слово. Поэтому итоговая таблица причин должна содержать осторожную формулировку «предполагаемая причина» и ссылаться на видимый признак.",
    ]:
        add_body(document, text)
    error_path = paths.results_dir / "error_analysis_tfidf_logistic_regression.csv"
    if error_path.exists():
        all_errors = pd.read_csv(error_path)
        errors = pd.concat([
            all_errors[all_errors["error_type"] == "false_positive"].head(4),
            all_errors[all_errors["error_type"] == "false_negative"].head(4),
        ], ignore_index=True)

        def short_excerpt(value: object, limit: int = 180) -> str:
            text = " ".join(str(value).split())
            return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"

        rows = [[str(r.error_type), short_excerpt(r.excerpt), str(r.toxic), str(r.prediction), str(r.heuristic_categories)] for r in errors.itertuples()]
        add_table(document, ["Тип", "Фрагмент", "y", "ŷ", "Наблюдаемый признак"], rows, widths=[2.4, 7.2, 1.0, 1.0, 3.4])
        add_caption(document, "Таблица 5 — Реальные ошибки тестовой выборки")
    else:
        add_body(document, "Реальные примеры не вставлены, поскольку тестовые предсказания не были получены. Подстановка придуманных токсичных фраз исказила бы обязательный анализ ошибок. После полного запуска таблица автоматически заполняется из error_analysis_tfidf_logistic_regression.csv; грубые фрагменты сокращаются, но сохраняют смысл наблюдения.")

    document.add_heading("3.8 Ограничения и обсуждение", level=2)
    for text in [
        "Первое ограничение текущего экземпляра — отсутствие выполненного fine-tuning DistilBERT, поэтому численное сравнение трансформера с классическими моделями не завершено. Классическая часть при этом выполнена на полном наборе. Второе ограничение связано с доменом Wikipedia: модель может хуже переноситься на короткие сообщения социальных сетей, другие языки и платформенные нормы.",
        "Третье ограничение — бинаризация. Метка toxic объединяет разные коммуникативные явления, а стоимость пропуска угрозы может отличаться от стоимости пропуска резкого, но неопасного оскорбления. Многометочная модель по шести категориям могла бы дать более полезные сигналы модератору. Четвёртое ограничение — отсутствие полного контекста ветки: отдельная реплика не всегда позволяет восстановить адресата и намерение.",
        "Наконец, агрегированные метрики скрывают различия между подгруппами. Упоминание идентичности может повышать score даже в поддерживающем сообщении. Для практического внедрения необходимы отдельные тесты fairness, мониторинг сдвига данных, калибровка и human-in-the-loop. Нельзя автоматически применять санкции только на основании одного классификатора.",
    ]:
        add_body(document, text)
    document.add_heading("Выводы по главе 3", level=2)
    add_body(document, "Экспериментальный протокол выполнен для всех классических моделей на едином test. Лучшим вариантом стал TF-IDF + Logistic Regression со standard-предобработкой: F1=0,7879 и PR-AUC=0,8726. BoW + MultinomialNB заметно уступил по F1 и PR-AUC, а Linear SVM показал более высокую Precision при меньшей Recall. Численное утверждение о преимуществе или отставании DistilBERT не делается, поскольку fine-tuning не выполнялся.")

    conclusion_heading = document.add_heading("ЗАКЛЮЧЕНИЕ", level=1)
    conclusion_heading.paragraph_format.page_break_before = False
    for text in [
        "В работе разработана воспроизводимая система определения токсичных комментариев, охватывающая загрузку официального Jigsaw, проверку качества, дедупликацию, фиксированное разбиение, EDA, три варианта очистки, три классических подхода и fine-tuning DistilBERT. Все модели приводятся к единому протоколу оценки; порог подбирается на validation, а test изолирован от настройки.",
        "Фактический эксперимент показал, что TF-IDF с Logistic Regression является сильной и быстрой базовой линией. Standard-предобработка дала лучший результат: Accuracy=0,9606, Precision=0,8131, Recall=0,7642, F1=0,7879, ROC-AUC=0,9729 и PR-AUC=0,8726. Extended-предобработка уступила standard, что подтверждает отсутствие гарантированной пользы от более сложной очистки.",
        "Цель исследования достигнута для EDA и классического машинного обучения: notebook выполнен без ошибок на 159 571 комментарии, сформированы реальные метрики, графики, модели и примеры FP/FN. Сравнение с DistilBERT остаётся ограничением работы, поскольку fine-tuning не запускался без тяжёлого ML-стека и вычислительного ресурса. Поэтому трансформеру не приписываются вымышленные показатели.",
        "Дальнейшее развитие включает многометочную классификацию, проверку fairness по identity-группам, калибровку вероятностей, обработку длинных текстов скользящим окном, character-level признаки для маскированной лексики и оценку на внешнем корпусе. Для практической модерации рекомендуется использовать модель как ранжирующий помощник с человеческим пересмотром и регулярно анализировать новые типы ошибок.",
    ]:
        add_body(document, text)

    references_heading = document.add_heading("СПИСОК ЛИТЕРАТУРЫ", level=1)
    references_heading.paragraph_format.page_break_before = False
    references = [
        "1. Vaswani A., Shazeer N., Parmar N. et al. Attention Is All You Need. Advances in Neural Information Processing Systems. 2017. URL: https://arxiv.org/abs/1706.03762",
        "2. Devlin J., Chang M.-W., Lee K., Toutanova K. BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding. NAACL-HLT. 2019. URL: https://arxiv.org/abs/1810.04805",
        "3. Sanh V., Debut L., Chaumond J., Wolf T. DistilBERT, a distilled version of BERT: smaller, faster, cheaper and lighter. 2019. URL: https://arxiv.org/abs/1910.01108",
        "4. Wulczyn E., Thain N., Dixon L. Ex Machina: Personal Attacks Seen at Scale. Proceedings of the 26th International Conference on World Wide Web. 2017. P. 1391–1399. DOI: 10.1145/3038912.3052591. URL: https://arxiv.org/abs/1610.08914",
        "5. Borkan D., Dixon L., Sorensen J., Thain N., Vasserman L. Nuanced Metrics for Measuring Unintended Bias with Real Data for Text Classification. WWW Companion. 2019. URL: https://arxiv.org/abs/1903.04561",
        "6. Pavlopoulos J., Sorensen J., Dixon L., Thain N., Androutsopoulos I. Toxicity Detection: Does Context Really Matter? Proceedings of ACL. 2020. URL: https://aclanthology.org/2020.acl-main.396/",
        "7. D’Sa A. G., Illina I., Fohr D. Towards Non-Toxic Landscapes: Automatic Toxic Comment Detection Using DNN. Proceedings of TRAC. 2020. URL: https://aclanthology.org/2020.trac-1.4/",
        "8. Salton G., Buckley C. Term-weighting approaches in automatic text retrieval. Information Processing & Management. 1988. Vol. 24, no. 5. P. 513–523. DOI: 10.1016/0306-4573(88)90021-0.",
        "9. Pedregosa F., Varoquaux G., Gramfort A. et al. Scikit-learn: Machine Learning in Python. Journal of Machine Learning Research. 2011. Vol. 12. P. 2825–2830. URL: https://www.jmlr.org/papers/v12/pedregosa11a.html",
        "10. Wolf T., Debut L., Sanh V. et al. Transformers: State-of-the-Art Natural Language Processing. EMNLP System Demonstrations. 2020. P. 38–45. DOI: 10.18653/v1/2020.emnlp-demos.6. URL: https://aclanthology.org/2020.emnlp-demos.6/",
        "11. Sokolova M., Lapalme G. A systematic analysis of performance measures for classification tasks. Information Processing & Management. 2009. Vol. 45, no. 4. P. 427–437. DOI: 10.1016/j.ipm.2009.03.002.",
        "12. Jigsaw, Conversation AI. Toxic Comment Classification Challenge. Kaggle. 2017–2018. URL: https://www.kaggle.com/competitions/jigsaw-toxic-comment-classification-challenge",
        "13. Scikit-learn developers. TfidfVectorizer documentation. URL: https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html",
        "14. Hugging Face. Transformers documentation: Text classification. URL: https://huggingface.co/docs/transformers/tasks/sequence_classification",
    ]
    for ref in references:
        add_body(document, ref, no_indent=True)

    document.add_heading("ПРИЛОЖЕНИЕ А ПАРАМЕТРЫ ЭКСПЕРИМЕНТОВ", level=1)
    add_table(document, ["Компонент", "Параметр", "Значение"], [
        ["Общее", "random_state", "42"], ["Split", "train / validation / test", "70% / 15% / 15%"],
        ["TF-IDF", "ngram_range", "(1,1) и (1,2)"], ["TF-IDF", "min_df", "2 и 5"],
        ["TF-IDF", "max_features", "60 000 и 120 000"], ["TF-IDF", "sublinear_tf", "False и True"],
        ["Logistic Regression", "C", "0.5, 1, 2, 4"], ["Linear SVM", "C", "0.25, 0.5, 1, 2"],
        ["DistilBERT", "base model", "distilbert-base-uncased"], ["DistilBERT", "max_length", "256 по умолчанию"],
        ["DistilBERT", "learning rate", "2e-5"], ["DistilBERT", "epochs", "2"],
    ], widths=[4.8, 4.8, 5.4])
    add_caption(document, "Таблица А.1 — Базовая конфигурация")
    add_body(document, "Полная конфигурация хранится в config/default.yaml. Все изменения для отдельного прогона следует фиксировать отдельным именем BERT-варианта или сохранённой копией YAML. Результаты быстрой проверки не заменяют полные эксперименты.")

    document.add_heading("ПРИЛОЖЕНИЕ Б ФРАГМЕНТЫ ИСХОДНОГО КОДА", level=1)
    snippets = [
        ("Формирование воспроизводимого split", "train_df, temp_df = train_test_split(\n    frame, test_size=0.30, stratify=frame['toxic'], random_state=42\n)\nvalidation_df, test_df = train_test_split(\n    temp_df, test_size=0.50, stratify=temp_df['toxic'], random_state=42\n)"),
        ("Pipeline без утечки", "Pipeline([\n    ('vectorizer', TfidfVectorizer(...)),\n    ('classifier', LogisticRegression(\n        class_weight='balanced', random_state=42\n    )),\n])"),
        ("Токенизация DistilBERT", "tokenizer(batch['text'], truncation=True, max_length=max_length)\nDataCollatorWithPadding(tokenizer=tokenizer)"),
        ("Подбор порога", "precision, recall, thresholds = precision_recall_curve(y_valid, scores)\nf1 = 2 * precision[:-1] * recall[:-1] / (precision[:-1] + recall[:-1])\nthreshold = thresholds[np.nanargmax(f1)]"),
    ]
    for title, code_text in snippets:
        document.add_heading(title, level=2)
        p = document.add_paragraph(style="Code Block")
        p.paragraph_format.first_line_indent = Cm(0)
        p.add_run(code_text)
    add_body(document, "Полный код находится в отдельных Python-файлах проекта. В документ включены только короткие фрагменты, необходимые для объяснения протокола и предотвращения утечки.")

    document.add_heading("ПРИЛОЖЕНИЕ В ИНСТРУКЦИЯ ПО ЗАПУСКУ", level=1)
    for line in [
        "1. Создать окружение Python 3.11 и установить зависимости: pip install -r requirements.txt.",
        "2. Выполнить python scripts/download_nltk.py.",
        "3. Принять правила Jigsaw на Kaggle и выполнить kagglehub login либо поместить официальные ZIP в data/raw.",
        "4. Открыть notebooks/coursework_toxicity.ipynb из корня проекта и выполнить Run All.",
        "5. При наличии ресурсов установить PyTorch и Transformers, задать RUN_BERT=True и повторно выполнить соответствующую ячейку.",
        "6. Проверить artifacts/results/all_results.csv и реальные примеры ошибок.",
        "7. Повторно создать документ командой python scripts/generate_report.py.",
        "8. Открыть DOCX в Word и обновить поля оглавления клавишей F9, если клиент не сделал это автоматически.",
    ]:
        add_body(document, line, no_indent=True)

    output = paths.report_dir / "coursework.docx"
    output.parent.mkdir(parents=True, exist_ok=True)
    document.save(output)
    return output
