// Genera las láminas 1080x1350 de los posts de GA con el diseño de la serie original.
// Uso: node render.js contenido.json carpeta_salida [n1,n2,...]
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const C = {
  claro: '#143460', oscuro: '#0B1C36', oro: '#C9A35C', linea: '#B59558',
  blanco: '#FFFFFF', texto: '#D8E0ED', sub: '#DCE3EF', pie: '#EAF1FD',
};

const ICONOS = {
  porcentaje: `<line x1="50" y1="205" x2="190" y2="25"/><circle cx="70" cy="65" r="30"/><circle cx="170" cy="165" r="30"/>`,
  casa: `<polyline points="20,110 120,22 220,110"/><polyline points="45,90 45,212 195,212 195,90"/><polyline points="85,158 112,185 160,128"/>`,
  recibo: `<polyline points="45,15 195,15 195,215 170,198 145,215 120,198 95,215 70,198 45,215 45,15"/><line x1="75" y1="65" x2="165" y2="65"/><line x1="75" y1="105" x2="165" y2="105"/><line x1="75" y1="145" x2="135" y2="145"/>`,
  llave: `<circle cx="70" cy="115" r="45"/><line x1="115" y1="115" x2="225" y2="115"/><line x1="190" y1="115" x2="190" y2="152"/><line x1="218" y1="115" x2="218" y2="142"/>`,
  auto: `<path d="M20,165 L20,130 L50,122 L80,75 L165,75 L195,122 L222,132 L222,165 Z"/><line x1="92" y1="88" x2="92" y2="122"/><line x1="58" y1="122" x2="195" y2="122"/><circle cx="65" cy="170" r="22"/><circle cx="180" cy="170" r="22"/>`,
  edificio: `<rect x="60" y="15" width="120" height="200"/><line x1="25" y1="215" x2="215" y2="215"/><rect x="85" y="45" width="22" height="22"/><rect x="133" y="45" width="22" height="22"/><rect x="85" y="90" width="22" height="22"/><rect x="133" y="90" width="22" height="22"/><rect x="85" y="135" width="22" height="22"/><rect x="133" y="135" width="22" height="22"/><rect x="105" y="178" width="30" height="37"/>`,
  balanza: `<line x1="120" y1="20" x2="120" y2="210"/><line x1="70" y1="210" x2="170" y2="210"/><line x1="35" y1="55" x2="205" y2="55"/><polyline points="35,55 10,125 60,125 35,55"/><polyline points="205,55 180,125 230,125 205,55"/><path d="M10,125 Q35,155 60,125"/><path d="M180,125 Q205,155 230,125"/>`,
  etiqueta: `<polygon points="30,30 125,30 220,125 125,220 30,125"/><circle cx="78" cy="78" r="17"/>`,
  flecha: `<line x1="20" y1="215" x2="225" y2="215"/><rect x="35" y="160" width="32" height="55"/><rect x="95" y="125" width="32" height="90"/><rect x="155" y="85" width="32" height="130"/><polyline points="30,120 95,70 140,95 215,25"/><polyline points="175,25 215,25 215,65"/>`,
  carpeta: `<path d="M20,55 L20,205 L220,205 L220,75 L115,75 L95,55 Z"/><line x1="20" y1="100" x2="220" y2="100"/>`,
  checklist: `<rect x="40" y="35" width="160" height="185"/><rect x="85" y="18" width="70" height="32"/><polyline points="70,95 85,110 110,82"/><line x1="125" y1="98" x2="170" y2="98"/><polyline points="70,150 85,165 110,137"/><line x1="125" y1="153" x2="170" y2="153"/>`,
};

Object.assign(ICONOS, {
  tienda: `<polyline points="20,95 40,30 200,30 220,95"/><path d="M20,95 Q45,120 70,95 Q95,120 120,95 Q145,120 170,95 Q195,120 220,95"/><polyline points="35,110 35,215 205,215 205,110"/><rect x="60" y="140" width="45" height="75"/><rect x="130" y="140" width="55" height="45"/>`,
  plano: `<rect x="20" y="25" width="200" height="185"/><line x1="110" y1="25" x2="110" y2="105"/><line x1="20" y1="105" x2="150" y2="105"/><line x1="185" y1="105" x2="220" y2="105"/><line x1="140" y1="105" x2="140" y2="210"/><path d="M150,105 A35,35 0 0 1 185,140"/>`,
  camion: `<rect x="15" y="60" width="135" height="110"/><polyline points="150,95 195,95 225,135 225,170 150,170"/><circle cx="60" cy="180" r="22"/><circle cx="185" cy="180" r="22"/>`,
  escudo: `<path d="M120,20 L210,55 L210,120 Q210,185 120,220 Q30,185 30,120 L30,55 Z"/><polyline points="80,120 110,150 165,92"/>`,
  alcancia: `<ellipse cx="115" cy="130" rx="90" ry="65"/><line x1="95" y1="70" x2="140" y2="70"/><rect x="60" y="185" width="22" height="28"/><rect x="150" y="185" width="22" height="28"/><circle cx="160" cy="115" r="6"/><path d="M205,120 L228,110"/><circle cx="115" cy="35" r="18"/>`,
  estrella: `<polygon points="120,15 148,88 225,88 163,135 186,212 120,165 54,212 77,135 15,88 92,88"/>`,
  anillos: `<circle cx="85" cy="125" r="60"/><circle cx="155" cy="125" r="60"/>`,
  arbol: `<circle cx="120" cy="45" r="25"/><circle cx="55" cy="175" r="22"/><circle cx="120" cy="175" r="22"/><circle cx="185" cy="175" r="22"/><polyline points="120,70 120,120 55,120 55,153"/><line x1="120" y1="120" x2="120" y2="153"/><polyline points="120,120 185,120 185,153"/>`,
  camara: `<rect x="20" y="65" width="200" height="140" rx="10"/><polyline points="75,65 92,35 148,35 165,65"/><circle cx="120" cy="135" r="42"/>`,
  brocha: `<rect x="40" y="25" width="160" height="60" rx="8"/><line x1="200" y1="55" x2="222" y2="55"/><polyline points="222,55 222,110 120,110 120,140"/><rect x="105" y="140" width="30" height="75" rx="6"/>`,
  moneda: `<circle cx="85" cy="120" r="65"/><circle cx="165" cy="120" r="65"/><text x="85" y="140" font-size="60" text-anchor="middle" fill="#C9A35C" stroke="none" font-family="Liberation Sans" font-weight="700">S/</text><text x="165" y="140" font-size="60" text-anchor="middle" fill="#C9A35C" stroke="none" font-family="Liberation Sans" font-weight="700">$</text>`,
  reloj: `<circle cx="120" cy="120" r="95"/><polyline points="120,60 120,120 165,145"/>`,
});

const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const pad = (n) => String(n).padStart(2, '0');

const logo = (x, y, s = 1) => `
  <svg style="position:absolute;left:${x}px;top:${y}px" width="${90 * s}" height="${50 * s}" viewBox="0 0 90 50">
    <text x="0" y="44" font-family="Inter" font-weight="300" font-size="58" fill="#fff">G</text>
    <polyline points="52,46 69,4 86,46" fill="none" stroke="${C.oro}" stroke-width="3.2"/>
  </svg>`;

const esquinas = () => `
  <svg style="position:absolute;left:0;top:0" width="1080" height="1350">
    <g fill="none" stroke="${C.linea}" stroke-width="2.2">
      <polyline points="40,100 40,40 100,40"/><polyline points="980,40 1040,40 1040,100"/>
      <polyline points="40,1250 40,1310 100,1310"/><polyline points="980,1310 1040,1310 1040,1250"/>
    </g></svg>`;

const pie = (der) => `
  <div style="position:absolute;left:90px;top:1209px;width:900px;height:1.5px;background:${C.linea}"></div>
  <div class="pie" style="left:90px;color:${C.pie}">GA DESARROLLADORES INMOBILIARIOS</div>
  <div class="pie" style="right:90px;color:${C.oro}">${der}</div>`;

const contador = (i) => `<div class="cont">${pad(i)} / 06</div>`;

function base(fondo, cuerpo) {
  return `<!doctype html><html><head><meta charset="utf-8"><style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{width:1080px;height:1350px;background:${fondo};font-family:'Liberation Sans',Arial,sans-serif;position:relative;overflow:hidden}
  .cont{position:absolute;right:90px;top:93px;color:${C.oro};font-weight:700;font-size:23px;letter-spacing:4px}
  .pie{position:absolute;top:1243px;font-weight:700;font-size:20px;letter-spacing:5.2px}
  .cat{position:absolute;left:90px;top:306px;color:${C.oro};font-weight:700;font-size:26px;letter-spacing:7px}
  .raya{position:absolute;left:90px;width:120px;height:3px;background:${C.oro}}
  </style></head><body>${cuerpo}</body></html>`;
}

function portada(p) {
  const fondo = p.n % 2 === 0 ? C.claro : C.oscuro;
  return base(fondo, `
    ${esquinas()}${logo(92, 80)}${contador(1)}
    <div class="cat">${esc(p.cat)}</div>
    <div class="raya" style="top:357px"></div>
    <div style="position:absolute;right:92px;top:282px;color:${C.oro};font-weight:700;font-size:152px;letter-spacing:-4px;line-height:1">${pad(p.n)}</div>
    <div style="position:absolute;left:90px;top:424px;width:${p.titulo.length > 34 ? 900 : 760}px">
      <div style="color:#fff;font-weight:700;font-size:76px;line-height:92px;letter-spacing:-0.5px">${esc(p.titulo)}</div>
      <div style="color:${C.sub};font-size:36px;line-height:48px;margin-top:22px">${esc(p.sub)}</div>
    </div>
    <svg style="position:absolute;left:720px;top:880px" width="240" height="230" viewBox="0 0 240 230">
      <g fill="none" stroke="${C.oro}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round">${ICONOS[p.icono]}</g></svg>
    ${pie('DESLIZA &nbsp;→')}`);
}

function contenido(p, i, pt) {
  const dato = pt.dato ? `
    <div style="margin-top:46px;border:2px solid ${C.oro};padding:34px 38px 30px">
      <div style="color:${C.oro};font-weight:700;font-size:22px;letter-spacing:6px">DATO</div>
      <div style="color:#fff;font-size:32px;line-height:46px;margin-top:14px">${esc(pt.dato)}</div>
    </div>` : '';
  return base(C.oscuro, `
    ${logo(92, 80)}${contador(i + 2)}
    <div style="position:absolute;left:88px;top:290px;color:${C.oro};font-weight:700;font-size:152px;letter-spacing:-4px;line-height:1">${pad(i + 1)}</div>
    <div style="position:absolute;left:90px;top:462px;width:900px">
      <div style="color:#fff;font-weight:700;font-size:58px;line-height:72px">${esc(pt.t)}</div>
      <div style="width:90px;height:3px;background:${C.oro};margin-top:20px"></div>
      <div style="color:${C.texto};font-size:38px;line-height:58px;margin-top:44px">${esc(pt.c)}</div>
      ${dato}
    </div>
    ${pie(esc(p.pie))}`);
}

function cierre(p) {
  return base(C.oscuro, `
    ${esquinas()}
    <svg style="position:absolute;left:390px;top:320px" width="300" height="240" viewBox="0 0 300 240">
      <text x="48" y="122" font-family="Inter" font-weight="300" font-size="150" fill="#fff">G</text>
      <polyline points="178,124 216,18 254,124" fill="none" stroke="${C.oro}" stroke-width="7"/>
      <path d="M15,143 Q150,310 285,143" fill="none" stroke="${C.oro}" stroke-width="2.2"/>
    </svg>
    <div style="position:absolute;left:0;top:655px;width:1080px;text-align:center;color:#fff;font-weight:700;font-size:74px">¿Te sirvió?</div>
    <div style="position:absolute;left:140px;top:778px;width:800px;text-align:center;color:${C.sub};font-size:36px;line-height:58px">${esc(p.cierre)}</div>
    <div style="position:absolute;left:260px;top:${p.cierre.length > 80 ? 975 : 942}px;width:560px;height:96px;border:2.5px solid ${C.oro};display:flex;align-items:center;justify-content:center;color:${C.oro};font-weight:700;font-size:30px;letter-spacing:6px">ESCRÍBENOS POR DM</div>
    ${pie('SÍGUENOS')}`);
}

(async () => {
  const [, , json, salida, solo] = process.argv;
  const posts = JSON.parse(fs.readFileSync(json, 'utf8')).filter((p) => !solo || solo.split(',').map(Number).includes(p.n));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 1 });
  for (const p of posts) {
    const dir = path.join(salida, p.carpeta);
    fs.mkdirSync(dir, { recursive: true });
    const laminas = [portada(p), ...p.puntos.map((pt, i) => contenido(p, i, pt)), cierre(p)];
    for (let k = 0; k < laminas.length; k++) {
      await page.setContent(laminas[k], { waitUntil: 'load' });
      await page.evaluate(() => document.fonts.ready);
      await page.screenshot({ path: path.join(dir, `lamina_${k + 1}.png`) });
    }
    fs.writeFileSync(path.join(dir, 'caption.txt'), p.caption + '\n');
    console.log('ok', p.carpeta);
  }
  await browser.close();
})();
