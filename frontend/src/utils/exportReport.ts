export function downloadJson(filename: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function printHtmlReport(title: string, bodyHtml: string) {
  const w = window.open("", "_blank", "noopener,noreferrer");
  if (!w) return;
  w.document.write(`<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8"/>
  <title>${title}</title>
  <style>
    body { font-family: Segoe UI, sans-serif; color: #111827; margin: 32px; }
    h1 { font-size: 20px; }
    h2 { font-size: 15px; margin-top: 24px; }
    table { border-collapse: collapse; width: 100%; font-size: 13px; }
    th, td { border: 1px solid #d1d5db; padding: 6px 8px; text-align: left; }
    .muted { color: #6b7280; font-size: 12px; }
    .slide { page-break-after: always; min-height: 80vh; }
  </style>
</head>
<body>
  <h1>${title}</h1>
  ${bodyHtml}
  <p class="muted">MobilitySmart · démo Antananarivo · volumes synthétiques</p>
</body>
</html>`);
  w.document.close();
  w.focus();
  w.print();
}

export function downloadSlidesHtml(filename: string, title: string, slides: string[]) {
  const html = `<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8"/>
  <title>${title}</title>
  <style>
    body { font-family: Segoe UI, sans-serif; background: #0b1220; color: #e8eef7; margin: 0; }
    .slide { min-height: 100vh; padding: 64px; box-sizing: border-box; border-bottom: 1px solid #2a3a52; }
    h1 { color: #2dd4bf; }
    table { border-collapse: collapse; }
    td, th { border: 1px solid #2a3a52; padding: 8px; }
  </style>
</head>
<body>
${slides.map((s) => `<section class="slide">${s}</section>`).join("\n")}
</body>
</html>`;
  const blob = new Blob([html], { type: "text/html" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
