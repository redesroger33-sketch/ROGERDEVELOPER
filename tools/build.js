#!/usr/bin/env node
/* ==========================================================
   build.js — arma las páginas HTML desde src/layout.html
   y los fragmentos de src/pages/.

   Uso:  node tools/build.js
   Edita el contenido en src/pages/*.html y vuelve a correrlo.
   ========================================================== */
'use strict';

var fs = require('fs');
var path = require('path');

var ROOT = path.resolve(__dirname, '..');
var SRC = path.join(ROOT, 'src');

/* Enlaces del menú principal (en orden) */
var NAV = [
  { href: 'index.html', label: 'Inicio' },
  { href: 'recursos.html', label: 'Recursos' },
  { href: 'calculadoras.html', label: 'Calculadoras' },
  { href: 'articulos.html', label: 'Artículos' },
  { href: 'glosario.html', label: 'Glosario' }
];

/* Páginas del sitio. `out` es la ruta final; `src` el fragmento. */
var PAGES = [
  { src: 'index.html', out: 'index.html',
    title: 'GA Desarrolladores Inmobiliarios — Recursos para invertir en bienes raíces',
    desc: 'Calculadoras, checklists y guías para analizar una propiedad antes de comprarla. Recursos gratuitos de Roger Guevara para compradores e inversionistas en Perú y Latinoamérica.',
    scripts: ['assets/js/calculadoras.js'] },

  { src: 'recursos.html', out: 'recursos.html',
    title: 'Biblioteca de recursos — GA Desarrolladores',
    desc: 'Checklists, plantillas, guías y herramientas de análisis inmobiliario, organizadas por tema: zonas y precios, casos con números, errores de compradores y contexto de mercado.' },

  { src: 'calculadoras.html', out: 'calculadoras.html',
    title: 'Calculadoras inmobiliarias — hipoteca, renta, capacidad de compra',
    desc: 'Cinco calculadoras que corren en tu navegador: cuota hipotecaria con tabla de amortización, flujo de caja de una renta, capacidad de compra, rentar vs. comprar y remodelar para vender.',
    scripts: ['assets/js/calculadoras.js'] },

  { src: 'checklist.html', out: 'checklist.html',
    title: 'Checklist de compra de propiedad — 52 puntos de verificación',
    desc: 'Los 52 puntos que se revisan antes de firmar: documentos registrales, legales, técnicos, financieros y de zona. Guarda tu progreso en el navegador.' },

  { src: 'glosario.html', out: 'glosario.html',
    title: 'Glosario inmobiliario — 42 términos explicados',
    desc: 'Cap rate, DSCR, arras, minuta, plusvalía, LTV, GRM y 35 términos más, explicados con la fórmula y un ejemplo con números.' },

  { src: 'articulos.html', out: 'articulos.html',
    title: 'Artículos — análisis y errores en inversión inmobiliaria',
    desc: 'Artículos con números concretos sobre cómo analizar una propiedad de renta, los errores que le cuestan más caro a un comprador primerizo y cómo usar IA en bienes raíces.' },

  { src: 'producto.html', out: 'producto.html',
    title: 'El Mapa de Inversión Inmobiliaria Lima — guía y mini-curso',
    desc: 'Cuatro módulos: diagnóstico de presupuesto, comparativo de zonas de Lima, proceso de compra paso a paso y plantilla de cálculo de retorno.' },

  { src: 'contacto.html', out: 'contacto.html',
    title: 'Contacto — GA Desarrolladores Inmobiliarios',
    desc: 'Escríbeme para una asesoría de compra o inversión inmobiliaria, o sígueme en Instagram, TikTok, YouTube y Facebook.' },

  { src: 'articulos/analizar-propiedad-renta.html', out: 'articulos/analizar-propiedad-renta.html',
    title: 'Cómo analizar una propiedad de renta en 15 minutos',
    desc: 'Las seis métricas que deciden si una propiedad de renta sirve o no: regla del 1 %, cap rate, NOI, cash-on-cash, DSCR y punto de equilibrio, con un ejemplo completo en soles.' },

  { src: 'articulos/errores-comprador-primerizo.html', out: 'articulos/errores-comprador-primerizo.html',
    title: 'Los 7 errores que más caro le salen a un comprador primerizo',
    desc: 'Cada error con el costo estimado en dinero: firmar arras sin verificar registros, confundir cuota con costo total, no presupuestar los gastos de cierre y cuatro más.' },

  { src: 'articulos/ia-para-bienes-raices.html', out: 'articulos/ia-para-bienes-raices.html',
    title: '9 usos de IA en bienes raíces que sí ahorran horas',
    desc: 'Prompts listos para copiar: análisis de una ficha de propiedad, comparativo de zonas, revisión de cláusulas de contrato, guiones de contenido y respuestas a objeciones.' }
];

function navHtml(current, base) {
  return NAV.map(function (item) {
    var active = item.href === current ? ' aria-current="page"' : '';
    return '<a href="' + base + item.href + '"' + active + '>' + item.label + '</a>';
  }).join('\n        ');
}

function build() {
  var layout = fs.readFileSync(path.join(SRC, 'layout.html'), 'utf8');
  var written = 0;

  PAGES.forEach(function (page) {
    var fragPath = path.join(SRC, 'pages', page.src);
    if (!fs.existsSync(fragPath)) {
      console.warn('  falta el fragmento: src/pages/' + page.src);
      return;
    }
    var depth = page.out.split('/').length - 1;
    var base = depth === 0 ? '' : '../'.repeat(depth);
    var current = depth === 0 ? page.out : '';

    var scripts = (page.scripts || []).map(function (s) {
      return '<script src="' + base + s + '"></script>';
    }).join('\n');

    var html = layout
      .replace(/\{\{TITLE\}\}/g, page.title.replace(/"/g, '&quot;'))
      .replace(/\{\{DESC\}\}/g, page.desc.replace(/"/g, '&quot;'))
      .replace(/\{\{NAV\}\}/g, navHtml(current, base))
      .replace(/\{\{CONTENT\}\}/g, fs.readFileSync(fragPath, 'utf8').trim())
      .replace(/\{\{SCRIPTS\}\}/g, scripts)
      .replace(/\{\{BASE\}\}/g, base);

    var outPath = path.join(ROOT, page.out);
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, html);
    console.log('  ' + page.out + '  (' + Math.round(html.length / 1024) + ' KB)');
    written++;
  });

  console.log('\n' + written + ' de ' + PAGES.length + ' páginas generadas.');
}

build();
