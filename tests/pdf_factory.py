from pathlib import Path
from typing import Iterable


TextItem = tuple[float, float, str, float]


def _escape_pdf_text(value: str) -> str:
    latin1_value = value.encode("latin-1", errors="replace").decode("latin-1")
    return latin1_value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def create_positioned_text_pdf(
    pages: Iterable[Iterable[TextItem]],
    output_path: Path,
) -> Path:
    page_items = [list(items) for items in pages]
    if not page_items:
        page_items = [[]]

    objects: list[str] = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "PAGES_PLACEHOLDER",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    page_ids: list[int] = []

    for items in page_items:
        commands: list[str] = []
        for x, y, value, font_size in items:
            commands.extend(
                [
                    "BT",
                    f"/F1 {font_size:g} Tf",
                    f"1 0 0 1 {x:g} {y:g} Tm",
                    f"({_escape_pdf_text(value)}) Tj",
                    "ET",
                ]
            )

        stream = "\n".join(commands)
        stream_length = len(stream.encode("latin-1"))
        objects.append(f"<< /Length {stream_length} >>\nstream\n{stream}\nendstream")
        content_id = len(objects)
        objects.append(
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            "/CropBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
        )
        page_ids.append(len(objects))

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>"

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n{body}\nendobj\n".encode("latin-1"))

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(bytes(pdf))
    return output_path


def create_text_pdf(
    text: str,
    output_path: Path,
    *,
    x: float = 50,
    start_y: float = 780,
    line_height: float = 12,
    lines_per_page: int = 55,
    font_size: float = 9,
) -> Path:
    lines = text.replace("\r\n", "\n").split("\n")
    pages: list[list[TextItem]] = []
    for start in range(0, len(lines), lines_per_page):
        page_lines = lines[start:start + lines_per_page]
        pages.append(
            [
                (x, start_y - index * line_height, line, font_size)
                for index, line in enumerate(page_lines)
            ]
        )
    return create_positioned_text_pdf(pages, output_path)
