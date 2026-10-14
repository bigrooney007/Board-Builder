/* Parse actual V2 JSX without a network install. A CRA build remains separate. */
const fs = require("fs");
const path = require("path");
const root = path.resolve(__dirname, "..");
const candidates = [
  process.env.V2_BABEL_BUNDLE,
  "/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/lib/transform/babelBundle.js",
].filter(Boolean);
let parse;
for (const candidate of candidates) {
  if (fs.existsSync(candidate)) {
    const babel = require(candidate);
    parse = (source, file) => babel.babelParse(source, file, true);
    break;
  }
}
if (!parse) {
  try {
    const parser = require(path.join(root, "frontend/node_modules/@babel/parser"));
    parse = (source) => parser.parse(source, { sourceType: "module", plugins: ["jsx"] });
  } catch {
    throw new Error("No local JSX parser. Install the frontend dependencies or set V2_BABEL_BUNDLE.");
  }
}
const directory = path.join(root, "frontend/src/v2");
if (!fs.existsSync(directory)) throw new Error("V2 frontend has not been implemented.");
const files = fs.readdirSync(directory).filter((file) => /\.(jsx|js)$/.test(file));
files.push("../App.js");
files.push("../pages/AdminPage.jsx", "../funnels/BoardRecommitmentFormPage.jsx", "../funnels/GuidedPrepaymentQuestionsPage.jsx", "../member/RecruitmentGameIntake.jsx", "../public/OpportunityPages.jsx");
let failed = 0;
for (const file of files) {
  const full = path.join(directory, file);
  try {
    parse(fs.readFileSync(full, "utf8"), full);
    process.stdout.write(`PASS JSX syntax ${path.relative(root, full)}\n`);
  } catch (error) {
    failed += 1;
    process.stderr.write(`FAIL ${path.relative(root, full)}: ${error.message}\n`);
  }
}
if (failed) process.exit(1);
process.stdout.write(`Parsed ${files.length} actual frontend source files. This is a syntax check, not a browser or production-build result.\n`);
