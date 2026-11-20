import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = process.cwd();
const output = resolve(root, ".vercel/output");
const staticOutput = resolve(output, "static");

const [html, css, app, calculations] = await Promise.all([
  readFile(resolve(root, "index.html"), "utf8"),
  readFile(resolve(root, "styles.css"), "utf8"),
  readFile(resolve(root, "app.js"), "utf8"),
  readFile(resolve(root, "calculations.js"), "utf8"),
]);

const standaloneHtml = html
  .replace(/    <link rel="preconnect"[^>]*>\n/g, "")
  .replace(/    <link href="https:\/\/fonts\.googleapis\.com[^>]*>\n/g, "")
  .replace('    <link rel="stylesheet" href="styles.css">', `    <style>\n${css}\n    </style>`)
  .replace(
    '    <script type="module" src="app.js"></script>',
    `    <script>\n${calculations.replace(/^export /gm, "")}\n${app.replace(/^import .*;\n/, "")}\n    </script>`,
  );

if (
  standaloneHtml === html
  || standaloneHtml.includes('href="styles.css"')
  || standaloneHtml.includes('src="app.js"')
  || standaloneHtml.includes('href="https://fonts.googleapis.com')
  || standaloneHtml.includes('import { calculate')
) {
  throw new Error("Could not generate a self-contained calculator HTML file.");
}

await writeFile(resolve(root, "investco-mobile.html"), standaloneHtml);

await rm(output, { recursive: true, force: true });
await mkdir(staticOutput, { recursive: true });
await writeFile(
  resolve(output, "config.json"),
  `${JSON.stringify({ version: 3 }, null, 2)}\n`,
);

for (const file of ["index.html", "app.js", "calculations.js", "styles.css", "investco-mobile.html"]) {
  await cp(resolve(root, file), resolve(staticOutput, file));
}
