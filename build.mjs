import { cp, mkdir, rm } from "node:fs/promises";
import { resolve } from "node:path";

const root = process.cwd();
const output = resolve(root, ".vercel/output");
const staticOutput = resolve(output, "static");

await rm(output, { recursive: true, force: true });
await mkdir(staticOutput, { recursive: true });

for (const file of ["index.html", "app.js", "calculations.js", "styles.css"]) {
  await cp(resolve(root, file), resolve(staticOutput, file));
}
