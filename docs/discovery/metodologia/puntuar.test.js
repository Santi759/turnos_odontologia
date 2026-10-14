const test = require('node:test');
const assert = require('node:assert/strict');
const { WEIGHTS, ITEM_IDS, validateFicha, scoreFicha, rankFichas } = require('./puntuar');

const URL = 'https://ejemplo.com/funciones';

function ficha(overrides = {}, estadoPorDefecto = 'no-evidenciado') {
  const items = {};
  for (const id of ITEM_IDS) {
    items[id] = estadoPorDefecto === 'no-evidenciado'
      ? { estado: 'no-evidenciado' }
      : { estado: estadoPorDefecto, url: URL };
  }
  return { slug: 'demo', nombre: 'Demo', nivel: 2, items: { ...items, ...overrides } };
}

test('los pesos son los exactos de la consigna y suman 100 %', () => {
  assert.deepEqual(WEIGHTS, { C1: 25, C2: 20, C3: 15, C4: 15, C5: 10, C6: 10, C7: 5 });
  assert.equal(Object.values(WEIGHTS).reduce((a, b) => a + b, 0), 100);
});

test('hay 5 ítems por criterio, 35 en total', () => {
  assert.equal(ITEM_IDS.length, 35);
  for (const c of Object.keys(WEIGHTS)) {
    assert.equal(ITEM_IDS.filter(id => id.startsWith(c + '.')).length, 5);
  }
});

test('todo comprobado-oficial da 100 puntos y cobertura total', () => {
  const r = scoreFicha(ficha({}, 'comprobado-oficial'));
  assert.equal(r.total, 100);
  assert.equal(r.cobertura, 1);
  assert.equal(r.criterios.C1, 5);
});

test('todo no-evidenciado da 0 puntos y cobertura 0', () => {
  const r = scoreFicha(ficha());
  assert.equal(r.total, 0);
  assert.equal(r.cobertura, 0);
});

test('terceros vale 0,5 y afirmacion-comercial vale 0 pero cuenta como cobertura', () => {
  const r = scoreFicha(ficha({
    'C1.1': { estado: 'comprobado-oficial', url: URL },
    'C1.2': { estado: 'terceros', url: URL },
    'C7.5': { estado: 'afirmacion-comercial', url: URL },
  }));
  assert.equal(r.criterios.C1, 1.5);
  assert.equal(r.criterios.C7, 0);
  assert.equal(r.total, 7.5); // 1,5/5 × 25
  assert.equal(r.cobertura, 3 / 35);
});

test('un criterio completo pondera según su peso', () => {
  const overrides = {};
  for (const id of ITEM_IDS.filter(i => i.startsWith('C2.'))) overrides[id] = { estado: 'comprobado-oficial', url: URL };
  assert.equal(scoreFicha(ficha(overrides)).total, 20);
});

test('validación: ficha correcta no tiene errores', () => {
  assert.deepEqual(validateFicha(ficha({}, 'comprobado-oficial')), []);
});

test('validación: rechaza ítems faltantes, estados desconocidos y evidencia sin URL', () => {
  const f = ficha({ 'C1.1': { estado: 'quizas' }, 'C1.2': { estado: 'terceros' } });
  delete f.items['C7.5'];
  const errores = validateFicha(f);
  assert.ok(errores.some(e => e.includes('C7.5')));
  assert.ok(errores.some(e => e.includes('C1.1') && e.includes('quizas')));
  assert.ok(errores.some(e => e.includes('C1.2') && e.includes('URL')));
});

test('validación: rechaza nivel fuera de 1-3', () => {
  assert.ok(validateFicha({ ...ficha(), nivel: 4 }).some(e => e.includes('nivel')));
});

test('ranking: primero por nivel, luego por puntaje y ante empate por cobertura', () => {
  const alto = ficha({}, 'comprobado-oficial');
  const a = { ...ficha(), slug: 'arg-bajo', nivel: 1 };
  const b = { ...alto, slug: 'latam-alto', nivel: 2 };
  const c = { ...ficha({ 'C7.5': { estado: 'afirmacion-comercial', url: URL } }), slug: 'latam-cero-con-cobertura', nivel: 2 };
  const d = { ...ficha(), slug: 'latam-cero', nivel: 2 };
  const orden = rankFichas([d, b, c, a]).map(r => r.slug);
  assert.deepEqual(orden, ['arg-bajo', 'latam-alto', 'latam-cero-con-cobertura', 'latam-cero']);
});
