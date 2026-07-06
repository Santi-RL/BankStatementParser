const fs = require("fs");
const path = require("path");
const { test, expect } = require("@playwright/test");

const fixtureTextPath = path.join(
  __dirname,
  "..",
  "..",
  "parser_specs",
  "galicia_ar",
  "default",
  "fixtures",
  "sample_text.txt",
);

function escapePdfText(value) {
  return value
    .replace(/[\\()]/g, (character) => `\\${character}`)
    .replace(/[^\x09\x0a\x0d\x20-\x7e\xa0-\xff]/g, "?");
}

function createTextPdf(text, outputPath) {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  const linesPerPage = 55;
  const pageLines = [];
  for (let index = 0; index < lines.length; index += linesPerPage) {
    pageLines.push(lines.slice(index, index + linesPerPage));
  }

  const objects = [];
  const addObject = (body) => {
    objects.push(body);
    return objects.length;
  };

  const pagesId = 2;
  const fontId = 3;
  const pageIds = [];

  addObject("<< /Type /Catalog /Pages 2 0 R >>");
  addObject("PAGES_PLACEHOLDER");
  addObject("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>");

  for (const page of pageLines) {
    const commands = ["BT", "/F1 9 Tf", "50 780 Td"];
    for (const line of page) {
      commands.push(`(${escapePdfText(line)}) Tj`);
      commands.push("0 -12 Td");
    }
    commands.push("ET");

    const stream = commands.join("\n");
    const contentId = addObject(
      `<< /Length ${Buffer.byteLength(stream, "latin1")} >>\nstream\n${stream}\nendstream`,
    );
    const pageId = addObject(
      `<< /Type /Page /Parent ${pagesId} 0 R /MediaBox [0 0 612 792] /CropBox [0 0 612 792] /Resources << /Font << /F1 ${fontId} 0 R >> >> /Contents ${contentId} 0 R >>`,
    );
    pageIds.push(pageId);
  }

  objects[pagesId - 1] = `<< /Type /Pages /Kids [${pageIds
    .map((id) => `${id} 0 R`)
    .join(" ")}] /Count ${pageIds.length} >>`;

  let pdf = "%PDF-1.4\n";
  const offsets = [0];
  for (let index = 0; index < objects.length; index += 1) {
    offsets.push(Buffer.byteLength(pdf, "latin1"));
    pdf += `${index + 1} 0 obj\n${objects[index]}\nendobj\n`;
  }

  const xrefOffset = Buffer.byteLength(pdf, "latin1");
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (let index = 1; index < offsets.length; index += 1) {
    pdf += `${String(offsets[index]).padStart(10, "0")} 00000 n \n`;
  }
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF\n`;

  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, pdf, "latin1");
}

test("production-test procesa una fixture PDF sanitizada", async ({ page }, testInfo) => {
  const pdfPath = testInfo.outputPath("galicia-sanitized.pdf");
  createTextPdf(fs.readFileSync(fixtureTextPath, "utf8"), pdfPath);

  await page.goto("/");

  await expect(page.getByText("Aprender Formatos")).toHaveCount(0);

  await page.locator('input[type="file"]').setInputFiles(pdfPath);
  await expect(page.getByText(/1 archivos PDF válidos cargados/)).toBeVisible();

  await page.getByRole("button", { name: /Analizar Extractos/ }).click();
  await expect(page.getByText("Análisis previo")).toBeVisible({ timeout: 45_000 });
  await expect(page.getByText(/Banco detectado:/)).toBeVisible();
  await expect(page.getByText("Documento simple: se procesará completo sin selección adicional.")).toBeVisible();

  await page.getByRole("button", { name: /Procesar Extractos/ }).click();
  await expect(page.getByRole("button", { name: /Descargar Archivo Excel/ })).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole("button", { name: /Descargar Archivo CSV/ })).toBeVisible();
  await expect(page.getByText("Resumen del Proceso")).toBeVisible();
  await expect(page.getByText("Vista Previa de Transacciones")).toBeVisible();
  await expect(page.locator('[data-testid="stMetric"]').filter({ hasText: "Transacciones Totales" })).toContainText("3");
});
