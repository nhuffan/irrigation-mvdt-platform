import { cp, mkdir } from "node:fs/promises";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
const require = createRequire(import.meta.url);
const root = dirname(require.resolve("cesium/package.json"));
await mkdir("public/cesium", { recursive: true });
await cp(join(root, "Build/Cesium"), "public/cesium", { recursive: true });
