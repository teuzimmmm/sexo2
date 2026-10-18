'use strict';
// Prova que um commit só reformatou JavaScript: cada arquivo muda de texto, mas
// o AST (sem posições, comentários e aspas/raw de literais) é idêntico.
// Uso: node scripts/js_ast_equal.cjs BASE HEAD caminho [caminho...]
// Saída 1 se algum arquivo diferir. Requer acorn (repo, NODE_PATH ou /opt/node-tools).
const { execFileSync } = require('node:child_process');

function loadAcorn() {
  for (const spec of ['acorn', '/opt/node-tools/node_modules/acorn']) {
    try {
      return require(spec);
    } catch (_) {
      /* tenta o próximo */
    }
  }
  throw new Error('acorn não encontrado');
}

const acorn = loadAcorn();
const DROP = new Set(['start', 'end', 'loc', 'range']);

function normalize(node) {
  if (Array.isArray(node)) return node.map(normalize);
  if (node && typeof node === 'object') {
    const out = {};
    for (const key of Object.keys(node)) {
      if (DROP.has(key)) continue;
      if (key === 'raw' && node.type === 'Literal') continue;
      out[key] = normalize(node[key]);
    }
    return out;
  }
  if (typeof node === 'bigint') return `${node}n`;
  return node;
}

function tree(text) {
  const ast = acorn.parse(text, { ecmaVersion: 'latest', sourceType: 'script', allowHashBang: true });
  return JSON.stringify(normalize(ast), (_, v) => (v instanceof RegExp ? String(v) : v));
}

function show(rev, file) {
  return execFileSync('git', ['show', `${rev}:${file}`], { encoding: 'utf8', maxBuffer: 1 << 28 });
}

const [base, head, ...files] = process.argv.slice(2);
if (!base || !head || !files.length) {
  console.error('uso: node scripts/js_ast_equal.cjs BASE HEAD caminho...');
  process.exit(2);
}
let bad = 0;
for (const file of files) {
  const same = tree(show(base, file)) === tree(show(head, file));
  console.log(`${same ? 'OK  ' : 'DIFF'} ${file}`);
  if (!same) bad = 1;
}
process.exit(bad);
