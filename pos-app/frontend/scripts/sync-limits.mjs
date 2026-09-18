// shared/limits.json（正本）を src/lib/limits.json に写す。dev / build / test の前に自動実行される。
import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, "../../shared/limits.json");
const dst = resolve(here, "../src/lib/limits.json");
mkdirSync(dirname(dst), { recursive: true });
copyFileSync(src, dst);
console.log(`synced ${src} -> ${dst}`);
