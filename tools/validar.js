#!/usr/bin/env node
/* ==========================================================
   validar.js — revisa el sitio generado:
     · enlaces internos y archivos descargables que existen
     · anclas (#id) que existen en la página destino
     · ids duplicados
     · ids que el JavaScript lee y el HTML no define (y al revés)
     · atributos for= de <label> apuntando a un campo real
   Uso: node tools/validar.js
   ========================================================== */
'use strict';
var fs = require('fs'), path = require('path');
var ROOT = path.resolve(__dirname, '..');
var errores = [], avisos = [];

function paginas(dir, acc) {
  acc = acc || [];
  fs.readdirSync(dir, { withFileTypes: true }).forEach(function (e) {
    if (e.name === 'node_modules' || e.name === '.git' || e.name === 'src' || e.name === 'tools') return;
    var full = path.join(dir, e.name);
    if (e.isDirectory()) paginas(full, acc);
    else if (e.name.endsWith('.html')) acc.push(full);
  });
  return acc;
}

var htmls = paginas(ROOT);
var idsPorPagina = {};

// --- Pasada 1: recolectar ids y detectar duplicados
htmls.forEach(function (f) {
  var rel = path.relative(ROOT, f);
  var s = fs.readFileSync(f, 'utf8');
  var ids = [], dup = [];
  var re = /\sid="([^"]+)"/g, m;
  while ((m = re.exec(s))) {
    if (ids.indexOf(m[1]) !== -1) dup.push(m[1]);
    ids.push(m[1]);
  }
  idsPorPagina[rel] = ids;
  dup.forEach(function (d) { errores.push(rel + ': id duplicado "' + d + '"'); });
});

// --- Pasada 2: enlaces, anclas y labels
htmls.forEach(function (f) {
  var rel = path.relative(ROOT, f);
  var dir = path.dirname(f);
  var s = fs.readFileSync(f, 'utf8');

  var re = /(?:href|src)="([^"]+)"/g, m;
  while ((m = re.exec(s))) {
    var href = m[1];
    if (href === '#') { avisos.push(rel + ': enlace marcador de posición href="#"'); continue; }
    if (/^(https?:|mailto:|tel:|data:)/.test(href)) continue;

    var hash = '', ruta = href;
    var i = href.indexOf('#');
    if (i !== -1) { hash = href.slice(i + 1); ruta = href.slice(0, i); }

    var destino = ruta === '' ? f : path.resolve(dir, ruta);
    if (!fs.existsSync(destino)) {
      errores.push(rel + ': destino inexistente -> ' + href);
      continue;
    }
    if (hash) {
      var relDest = path.relative(ROOT, destino);
      var ids = idsPorPagina[relDest];
      if (ids && ids.indexOf(hash) === -1) {
        errores.push(rel + ': ancla inexistente -> ' + href);
      }
    }
  }

  var reL = /<label[^>]*\sfor="([^"]+)"/g;
  while ((m = reL.exec(s))) {
    if (idsPorPagina[rel].indexOf(m[1]) === -1) {
      errores.push(rel + ': <label for="' + m[1] + '"> sin campo correspondiente');
    }
  }
});

// --- Pasada 3: ids que usa calculadoras.js
var js = fs.readFileSync(path.join(ROOT, 'assets/js/calculadoras.js'), 'utf8');
function extraer(fnNombre) {
  var i = js.indexOf('function ' + fnNombre + '(');
  if (i === -1) return [];
  var j = js.indexOf('\n  }', i);
  var cuerpo = js.slice(i, j);
  var ids = [], re = /(?:val|set|verdict)\('([^']+)'/g, m;
  while ((m = re.exec(cuerpo))) if (ids.indexOf(m[1]) === -1) ids.push(m[1]);
  var re2 = /getElementById\('([^']+)'\)/g;
  while ((m = re2.exec(cuerpo))) if (ids.indexOf(m[1]) === -1) ids.push(m[1]);
  return ids;
}
var mapa = {
  calcHipoteca: ['calculadoras.html'],
  calcRenta: ['calculadoras.html'],
  calcCapacidad: ['calculadoras.html'],
  calcVersus: ['calculadoras.html'],
  calcFlip: ['calculadoras.html'],
  calcRapido: ['index.html']
};
Object.keys(mapa).forEach(function (fn) {
  var ids = extraer(fn);
  var pagina = mapa[fn][0];
  var enPagina = idsPorPagina[pagina] || [];
  var faltan = ids.filter(function (id) { return enPagina.indexOf(id) === -1; });
  // Las tablas se llenan por getElementById y también se validan
  ['h-tabla', 'v-tabla'].forEach(function (t) {
    if (js.indexOf("'" + t + "'") !== -1 && enPagina.indexOf(t) === -1 && pagina === 'calculadoras.html') {
      if (faltan.indexOf(t) === -1) faltan.push(t);
    }
  });
  if (faltan.length) {
    errores.push(pagina + ': ' + fn + '() lee ids que el HTML no define -> ' + faltan.join(', '));
  } else {
    console.log('  ok  ' + fn + '(): ' + ids.length + ' ids encontrados en ' + pagina);
  }
});

// --- Resultado
console.log('');
console.log(htmls.length + ' páginas revisadas.');
if (avisos.length) { console.log('\nAvisos (' + avisos.length + '):'); avisos.forEach(function (a) { console.log('  · ' + a); }); }
if (errores.length) {
  console.log('\nERRORES (' + errores.length + '):');
  errores.forEach(function (e) { console.log('  ✗ ' + e); });
  process.exit(1);
}
console.log('\nSin errores.');
