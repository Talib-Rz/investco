import { cp, mkdir, rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = process.cwd();
const output = resolve(root, ".vercel/output");
const staticOutput = resolve(output, "static");

await rm(output, { recursive: true, force: true });
await mkdir(staticOutput, { recursive: true });
await writeFile(
  resolve(output, "config.json"),
  `${JSON.stringify({ version: 3 }, null, 2)}\n`,
);

for (const file of ["index.html", "app.js", "calculations.js", "styles.css"]) {
  await cp(resolve(root, file), resolve(staticOutput, file));
}
