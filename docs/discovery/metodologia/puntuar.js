// Matriz de puntuación de competidores. Criterios en criterios-puntuacion.md.
// Uso CLI: node puntuar.js <directorio-de-fichas-json>  → tabla Markdown por stdout.
const fs = require('fs');
const path = require('path');

const WEIGHTS = { C1: 25, C2: 20, C3: 15, C4: 15, C5: 10, C6: 10, C7: 5 };
const ITEMS_PER_CRITERION = 5;
const ITEM_IDS = Object.keys(WEIGHTS).flatMap(c =>
  Array.from({ length: ITEMS_PER_CRITERION }, (_, i) => `${c}.${i + 1}`));

const VALUE_BY_STATE = {
  'comprobado-oficial': 1,
  'terceros': 0.5,
  'afirmacion-comercial': 0,
  'no-evidenciado': 0,
};

function validateFicha(ficha) {
  const errores = [];
  if (![1, 2, 3].includes(ficha.nivel)) errores.push(`${ficha.slug}: nivel debe ser 1, 2 o 3 (recibido ${ficha.nivel})`);
  for (const id of ITEM_IDS) {
    const item = ficha.items && ficha.items[id];
    if (!item) { errores.push(`${ficha.slug}: falta el ítem ${id}`); continue; }
    if (!(item.estado in VALUE_BY_STATE)) { errores.push(`${ficha.slug}: ${id} tiene estado desconocido "${item.estado}"`); continue; }
    if (item.estado !== 'no-evidenciado' && !/^https?:\/\//.test(item.url || '')) {
      errores.push(`${ficha.slug}: ${id} con estado ${item.estado} requiere URL`);
    }
  }
  return errores;
}

function scoreFicha(ficha) {
  const criterios = {};
  let total = 0;
  let conEvidencia = 0;
  for (const [c, peso] of Object.entries(WEIGHTS)) {
    const ids = ITEM_IDS.filter(id => id.startsWith(c + '.'));
    criterios[c] = ids.reduce((s, id) => s + VALUE_BY_STATE[ficha.items[id].estado], 0);
    conEvidencia += ids.filter(id => ficha.items[id].estado !== 'no-evidenciado').length;
    total += (criterios[c] / ITEMS_PER_CRITERION) * peso;
  }
  return { criterios, total: Math.round(total * 100) / 100, cobertura: conEvidencia / ITEM_IDS.length };
}

function rankFichas(fichas) {
  return fichas
    .map(f => ({ ...f, ...scoreFicha(f) }))
    .sort((a, b) => a.nivel - b.nivel || b.total - a.total || b.cobertura - a.cobertura);
}

function toMarkdown(ranking) {
  const head = '| # | Sistema | Nivel | C1 | C2 | C3 | C4 | C5 | C6 | C7 | Total (0-100) | Cobertura |';
  const sep = '|---|---|---|---|---|---|---|---|---|---|---|---|';
  const fmt = n => String(n).replace('.', ',');
  const rows = ranking.map((r, i) => `| ${i + 1} | ${r.nombre} | ${r.nivel} | ${Object.keys(WEIGHTS).map(c => fmt(r.criterios[c])).join(' | ')} | ${fmt(r.total)} | ${Math.round(r.cobertura * 100)} % |`);
  return [head, sep, ...rows].join('\n');
}

if (require.main === module) {
  const dir = process.argv[2];
  const fichas = fs.readdirSync(dir).filter(f => f.endsWith('.json'))
    .map(f => JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')));
  const errores = fichas.flatMap(validateFicha);
  if (errores.length) { console.error(errores.join('\n')); process.exit(1); }
  console.log(toMarkdown(rankFichas(fichas)));
}

module.exports = { WEIGHTS, ITEM_IDS, VALUE_BY_STATE, validateFicha, scoreFicha, rankFichas, toMarkdown };
