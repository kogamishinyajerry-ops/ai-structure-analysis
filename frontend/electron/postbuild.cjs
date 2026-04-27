/**
 * Electron postbuild — copy non-TS assets (renderer.html, renderer.css)
 * into the compiled-output directory so the BrowserWindow can find them
 * next to the JS bundles.
 *
 * tsc only emits .js for source .ts files; HTML/CSS need to come along
 * for the ride. Keeping this as a tiny .cjs script (instead of pulling
 * in a bundler) matches the project-wide preference for thin tooling.
 */

const fs = require("node:fs");
const path = require("node:path");

const SRC_DIR = __dirname;
const OUT_DIR = path.resolve(__dirname, "..", "dist-electron");
const ASSETS = ["renderer.html", "renderer.css"];

if (!fs.existsSync(OUT_DIR)) {
  // tsc should have created this; if it didn't, something is off.
  // Fail loud rather than silently shipping a broken bundle.
  console.error(
    `electron postbuild: ${OUT_DIR} does not exist. ` +
      `Run 'tsc -p electron/tsconfig.json' first.`
  );
  process.exit(1);
}

for (const asset of ASSETS) {
  const src = path.join(SRC_DIR, asset);
  const dst = path.join(OUT_DIR, asset);
  fs.copyFileSync(src, dst);
  console.log(`electron postbuild: copied ${asset}`);
}
