// Execute the model kernel of the authors' public scenario explorer as an oracle.
//
// The explorer chunk carries no license, so oracle.py downloads it from the authors' site and it is
// only executed here; none of its code is copied into this repository. This script slices the kernel
// and the quiz mapping out of the chunk, runs one scenario, and prints the explorer's rows as JSON.
//
// Usage: node oracle.mjs <chunk.js> '<json spec>'
//   spec = {scenario, overrides, levelForm, choices, quiz, horizon}
//   scenario: "conservative" | "central" | "fast"; overrides: parameter overrides on it;
//   choices: data-source and reporting options of the explorer (shares, hazards, matrix, sepRates, tfpExact);
//   quiz: {capability, adoption, alone, gain, months}, run as the explorer runs a visitor's answers.
import fs from "node:fs";

const [chunkPath, specText] = process.argv.slice(2);
const text = fs.readFileSync(chunkPath, "utf8");
const start = text.indexOf("var E=function(){");
const stop = text.indexOf("let tu=");
if (start < 0 || stop < 0 || stop < start) throw Error("oracle: kernel markers not found in " + chunkPath);
// The module's own top-level declarations, which the sliced code assigns to.
const kernel = new Function(`let t,a,s,l,o,r,n,i,d;${text.slice(start, stop)}; return { er, eg, ek, td, ee };`)();

const spec = JSON.parse(specText || "{}");
for (const [key, value] of Object.entries(spec.choices || {})) {
  if (!(key in kernel.ee)) throw Error("oracle: unknown choice " + key);
  kernel.ee[key].def = value;
}
let params;
if (spec.quiz) {
  params = kernel.ek(kernel.td(spec.quiz));
} else {
  params = { ...kernel.er(spec.scenario || "central"), ...(spec.overrides || {}) };
}
if (spec.horizon) params.horizon = spec.horizon;
const out = kernel.eg(params, spec.levelForm || "exact");
const replacer = (_, v) => (v === Infinity ? "Infinity" : v === -Infinity ? "-Infinity" : v);
process.stdout.write(
  JSON.stringify({ params, rows: out.rows, ss: out.ss, diag: out.diag, muFitted: out.muFitted }, replacer),
);
