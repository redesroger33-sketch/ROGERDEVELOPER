/* ==========================================================
   calculadoras.js — motor de cálculo inmobiliario
   Sin dependencias. Toda la matemática es local y verificable.
   ========================================================== */
(function () {
  'use strict';

  /* ==========================================================
     1. Utilidades de formato
     ========================================================== */
  var CUR_KEY = 'rg-moneda';
  var state = { currency: 'PEN', locale: 'es-PE' };

  try {
    var savedCur = localStorage.getItem(CUR_KEY);
    if (savedCur) state.currency = savedCur;
  } catch (e) { /* modo privado */ }

  function money(n) {
    if (!isFinite(n)) return '—';
    // Un residuo de centimos no debe mostrarse como "-S/ 0"
    if (Math.abs(n) < 0.5) n = 0;
    try {
      return new Intl.NumberFormat(state.locale, {
        style: 'currency',
        currency: state.currency,
        currencyDisplay: 'narrowSymbol',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
      }).format(n);
    } catch (e) {
      try {
        return new Intl.NumberFormat(state.locale, {
          style: 'currency', currency: state.currency,
          minimumFractionDigits: 0, maximumFractionDigits: 0
        }).format(n);
      } catch (e2) {
        return state.currency + ' ' + Math.round(n).toLocaleString('es-PE');
      }
    }
  }

  function num(n, dec) {
    if (!isFinite(n)) return '—';
    dec = dec == null ? 0 : dec;
    if (Math.abs(n) < Math.pow(10, -dec) / 2) n = 0;
    return new Intl.NumberFormat(state.locale, {
      minimumFractionDigits: dec, maximumFractionDigits: dec
    }).format(n);
  }

  function pct(n, dec) {
    if (!isFinite(n)) return '—';
    dec = dec == null ? 2 : dec;
    return num(n, dec) + ' %';
  }

  /* ==========================================================
     2. Lectura de campos
     ========================================================== */
  function val(id, fallback) {
    var el = document.getElementById(id);
    if (!el) return fallback || 0;
    var raw = String(el.value).replace(/\s/g, '').replace(/,/g, '');
    var v = parseFloat(raw);
    return isFinite(v) ? v : (fallback || 0);
  }

  function set(id, text, cls) {
    var el = document.getElementById(id);
    if (!el) return;
    el.textContent = text;
    if (cls !== undefined) {
      el.classList.remove('is-good', 'is-bad');
      if (cls) el.classList.add(cls);
    }
  }

  function verdict(id, level, title, body) {
    var el = document.getElementById(id);
    if (!el) return;
    el.className = 'verdict is-' + level;
    el.innerHTML = '<strong>' + title + '</strong>' + body;
  }

  /* ==========================================================
     3. Matemática financiera
     ========================================================== */

  // Pago mensual de un préstamo a tasa fija (sistema francés)
  function payment(principal, annualRate, years) {
    var n = Math.round(years * 12);
    if (n <= 0 || principal <= 0) return 0;
    var i = annualRate / 100 / 12;
    if (i === 0) return principal / n;
    return principal * i / (1 - Math.pow(1 + i, -n));
  }

  // Principal máximo dado un pago mensual disponible
  function principalFromPayment(pmt, annualRate, years) {
    var n = Math.round(years * 12);
    if (n <= 0 || pmt <= 0) return 0;
    var i = annualRate / 100 / 12;
    if (i === 0) return pmt * n;
    return pmt * (1 - Math.pow(1 + i, -n)) / i;
  }

  // Saldo insoluto después de k pagos
  function balanceAfter(principal, annualRate, years, k) {
    var n = Math.round(years * 12);
    if (k >= n) return 0;
    var i = annualRate / 100 / 12;
    if (i === 0) return Math.max(0, principal * (1 - k / n));
    var pmt = payment(principal, annualRate, years);
    return principal * Math.pow(1 + i, k) - pmt * (Math.pow(1 + i, k) - 1) / i;
  }

  // Tabla de amortización agregada por año
  function schedule(principal, annualRate, years) {
    var n = Math.round(years * 12);
    var i = annualRate / 100 / 12;
    var pmt = payment(principal, annualRate, years);
    var bal = principal, rows = [], totalInt = 0;
    for (var y = 1; y <= years; y++) {
      var yInt = 0, yCap = 0;
      for (var m = 0; m < 12 && (y - 1) * 12 + m < n; m++) {
        var int = bal * i;
        var cap = Math.min(pmt - int, bal);
        bal = Math.max(0, bal - cap);
        yInt += int; yCap += cap; totalInt += int;
      }
      rows.push({ year: y, interes: yInt, capital: yCap, saldo: bal });
      if (bal <= 0.01) break;
    }
    return { rows: rows, pmt: pmt, totalInt: totalInt, n: n };
  }

  /* ==========================================================
     4. Calculadora de hipoteca
     ========================================================== */
  function calcHipoteca() {
    if (!document.getElementById('h-precio')) return;

    var precio = val('h-precio');
    var engPct = val('h-enganche');
    var tasa = val('h-tasa');
    var años = val('h-plazo');
    var prediales = val('h-predial');      // anual
    var seguro = val('h-seguro');          // anual
    var hoa = val('h-hoa');                // mensual

    var enganche = precio * engPct / 100;
    var prestamo = Math.max(0, precio - enganche);
    var s = schedule(prestamo, tasa, años);
    var extras = prediales / 12 + seguro / 12 + hoa;
    var total = s.pmt + extras;

    set('h-out-pago', money(total));
    set('h-out-capint', money(s.pmt));
    set('h-out-extras', money(extras));
    set('h-out-prestamo', money(prestamo));
    set('h-out-enganche', money(enganche));
    set('h-out-interes', money(s.totalInt));
    set('h-out-total', money(prestamo + s.totalInt));
    set('h-out-costo', pct(prestamo > 0 ? (s.totalInt / prestamo) * 100 : 0, 1));

    // Tabla por año
    var tbody = document.getElementById('h-tabla');
    if (tbody) {
      tbody.innerHTML = s.rows.map(function (r) {
        return '<tr><td>Año ' + r.year + '</td><td>' + money(r.capital) +
          '</td><td>' + money(r.interes) + '</td><td>' + money(r.saldo) + '</td></tr>';
      }).join('');
    }

    // Lectura: proporción de interés en los primeros 5 años
    var int5 = 0, cap5 = 0;
    s.rows.slice(0, 5).forEach(function (r) { int5 += r.interes; cap5 += r.capital; });
    var share = int5 + cap5 > 0 ? (int5 / (int5 + cap5)) * 100 : 0;
    verdict('h-veredicto', share > 60 ? 'warn' : 'good',
      'En los primeros 5 años, ' + pct(share, 0) + ' de lo que pagas es interés.',
      ' Pagar capital adelantado en esa ventana es donde más ahorras. Cada ' +
      money(prestamo * 0.01) + ' de abono a capital hoy te quita aproximadamente ' +
      money(prestamo * 0.01 * (Math.pow(1 + tasa / 100, Math.min(años, 15)) - 1)) +
      ' de interés futuro si lo aplicas al inicio del crédito.');
  }

  /* ==========================================================
     5. Análisis de propiedad en renta
     ========================================================== */
  function calcRenta() {
    if (!document.getElementById('r-precio')) return;

    var precio = val('r-precio');
    var cierrePct = val('r-cierre');
    var remodel = val('r-remodelacion');
    var engPct = val('r-enganche');
    var tasa = val('r-tasa');
    var años = val('r-plazo');

    var rentaMes = val('r-renta');
    var vacanciaPct = val('r-vacancia');
    var adminPct = val('r-admin');
    var predial = val('r-predial');        // anual
    var seguro = val('r-seguro');          // anual
    var mantPct = val('r-mantenimiento');  // % de la renta bruta
    var hoa = val('r-hoa');                // mensual

    var enganche = precio * engPct / 100;
    var cierre = precio * cierrePct / 100;
    var capitalInicial = enganche + cierre + remodel;
    var prestamo = Math.max(0, precio - enganche);
    var pmt = payment(prestamo, tasa, años);

    var brutoAnual = rentaMes * 12;
    var vacancia = brutoAnual * vacanciaPct / 100;
    var efectivo = brutoAnual - vacancia;
    var admin = efectivo * adminPct / 100;
    var mant = brutoAnual * mantPct / 100;
    var opex = admin + mant + predial + seguro + hoa * 12;
    var noi = efectivo - opex;

    var baseValor = precio + remodel;
    var capRate = baseValor > 0 ? (noi / baseValor) * 100 : 0;
    var deudaAnual = pmt * 12;
    var flujoAnual = noi - deudaAnual;
    var flujoMes = flujoAnual / 12;
    var coc = capitalInicial > 0 ? (flujoAnual / capitalInicial) * 100 : 0;
    var dscr = deudaAnual > 0 ? noi / deudaAnual : Infinity;
    var regla1 = precio > 0 ? (rentaMes / precio) * 100 : 0;
    var grm = brutoAnual > 0 ? precio / brutoAnual : 0;
    var breakEven = brutoAnual > 0 ? ((opex + deudaAnual) / brutoAnual) * 100 : 0;

    set('r-out-flujo', money(flujoMes), flujoMes >= 0 ? 'is-good' : 'is-bad');
    set('r-out-capital', money(capitalInicial));
    set('r-out-noi', money(noi));
    set('r-out-caprate', pct(capRate));
    set('r-out-coc', pct(coc), coc >= 8 ? 'is-good' : (coc < 0 ? 'is-bad' : ''));
    set('r-out-dscr', isFinite(dscr) ? num(dscr, 2) + '×' : 'Sin deuda',
      dscr >= 1.25 ? 'is-good' : (dscr < 1 ? 'is-bad' : ''));
    set('r-out-regla1', pct(regla1));
    set('r-out-grm', num(grm, 1) + '×');
    set('r-out-opex', money(opex / 12));
    set('r-out-hipoteca', money(pmt));
    set('r-out-breakeven', pct(breakEven, 0));

    var level, title, body;
    if (flujoMes < 0) {
      level = 'bad';
      title = 'Flujo negativo: ' + money(flujoMes) + ' al mes.';
      body = ' Estás subsidiando la propiedad. Para llegar a cero necesitas subir la renta a ' +
        money(rentaMes + Math.abs(flujoMes) / (1 - vacanciaPct / 100 - adminPct / 100)) +
        ' o bajar el precio de compra a ' +
        money(precio - Math.abs(flujoAnual) / (tasa / 100 || 0.08)) + ' aproximadamente.';
    } else if (dscr < 1.25) {
      level = 'warn';
      title = 'Flujo positivo pero DSCR de ' + num(dscr, 2) + '×.';
      body = ' Muchos bancos piden 1.25× para créditos de inversión. Un mes de vacancia extra' +
        ' te deja en rojo. Aumenta el enganche o negocia el precio.';
    } else if (coc >= 8) {
      level = 'good';
      title = 'Números sólidos: ' + pct(coc, 1) + ' de cash-on-cash y DSCR ' + num(dscr, 2) + '×.';
      body = ' Recuperas el capital invertido en ~' + num(100 / coc, 1) +
        ' años solo con flujo, sin contar apreciación ni amortización del crédito.';
    } else {
      level = 'warn';
      title = 'Funciona, pero el retorno es modesto: ' + pct(coc, 1) + ' de cash-on-cash.';
      body = ' Compáralo contra lo que rinde tu alternativa sin trabajo operativo.' +
        ' El cap rate de ' + pct(capRate, 1) + ' es el número que debes contrastar con la zona.';
    }
    verdict('r-veredicto', level, title, body);
  }

  /* ==========================================================
     6. Capacidad de compra
     ========================================================== */
  function calcCapacidad() {
    if (!document.getElementById('c-ingreso')) return;

    var ingreso = val('c-ingreso');
    var deudas = val('c-deudas');
    var ahorro = val('c-ahorro');
    var tasa = val('c-tasa');
    var años = val('c-plazo');
    var dti = val('c-dti');
    var cierrePct = val('c-cierre') / 100;
    var ltvMax = val('c-ltv') / 100;

    var pagoMax = Math.max(0, ingreso * dti / 100 - deudas);
    var prestamoPorPago = principalFromPayment(pagoMax, tasa, años);

    // Restricción 1: capacidad de pago. El ahorro cubre enganche + cierre.
    var precioPorPago = (ahorro + prestamoPorPago) / (1 + cierrePct);
    // Restricción 2: LTV máximo permitido por el banco.
    var denom = (1 - ltvMax + cierrePct);
    var precioPorLtv = denom > 0 ? ahorro / denom : Infinity;

    var precio, limitante;
    if (precioPorLtv < precioPorPago) {
      precio = precioPorLtv; limitante = 'enganche';
    } else {
      precio = precioPorPago; limitante = 'ingreso';
    }
    if (!isFinite(precio) || precio < 0) precio = 0;

    var cierre = precio * cierrePct;
    var prestamo = Math.min(prestamoPorPago, precio * ltvMax);
    var enganche = Math.max(0, precio - prestamo);
    var pago = payment(prestamo, tasa, años);
    var dtiReal = ingreso > 0 ? ((pago + deudas) / ingreso) * 100 : 0;
    var sobrante = ahorro - enganche - cierre;

    set('c-out-precio', money(precio));
    set('c-out-prestamo', money(prestamo));
    set('c-out-enganche', money(enganche));
    set('c-out-engpct', pct(precio > 0 ? (enganche / precio) * 100 : 0, 1));
    set('c-out-cierre', money(cierre));
    set('c-out-pago', money(pago));
    set('c-out-pagomax', money(pagoMax));
    set('c-out-dti', pct(dtiReal, 1), dtiReal <= dti ? 'is-good' : 'is-bad');
    set('c-out-sobrante', money(sobrante), sobrante >= 0 ? 'is-good' : 'is-bad');

    if (limitante === 'enganche') {
      verdict('c-veredicto', 'warn',
        'Tu límite es el enganche, no el ingreso.',
        ' Con ' + money(ahorro) + ' ahorrados alcanzas ' + money(precio) +
        ' al ' + pct(ltvMax * 100, 0) + ' de financiamiento. Tu ingreso soportaría un préstamo de ' +
        money(prestamoPorPago) + '. Cada ' + money(ahorro * 0.1) +
        ' extra de ahorro te suben el techo unos ' + money((ahorro * 0.1) / denom) + '.');
    } else {
      verdict('c-veredicto', 'good',
        'Tu límite es la capacidad de pago.',
        ' Con ' + pct(dti, 0) + ' de DTI tienes ' + money(pagoMax) +
        ' al mes para hipoteca. Recuerda que predial, seguro, mantenimiento y cuota de' +
        ' administración van aparte: reserva 1 % anual del valor de la propiedad para eso.');
    }
  }

  /* ==========================================================
     7. Rentar vs comprar (simulación mensual)
     ========================================================== */
  function calcVersus() {
    if (!document.getElementById('v-precio')) return;

    var precio = val('v-precio');
    var engPct = val('v-enganche');
    var tasa = val('v-tasa');
    var plazo = val('v-plazo');
    var cierrePct = val('v-cierre');
    var aprec = val('v-apreciacion');
    var tenenciaPct = val('v-tenencia');    // % anual del valor: predial + seguro + mant
    var ventaPct = val('v-venta');
    var renta = val('v-renta');
    var subeRenta = val('v-suberenta');
    var rendim = val('v-rendimiento');
    var horizonte = val('v-horizonte');

    var enganche = precio * engPct / 100;
    var cierre = precio * cierrePct / 100;
    var cashInicial = enganche + cierre;
    var prestamo = Math.max(0, precio - enganche);
    var pmt = payment(prestamo, tasa, plazo);

    var rm = Math.pow(1 + rendim / 100, 1 / 12) - 1;   // rendimiento mensual equivalente
    var am = Math.pow(1 + aprec / 100, 1 / 12) - 1;    // apreciación mensual equivalente

    var meses = Math.round(horizonte * 12);
    var valor = precio;
    var rentaActual = renta;
    var cuentaComprador = 0;
    var cuentaArrendatario = cashInicial;  // quien renta invierte el enganche + cierre
    var gastoComprador = cashInicial;
    var gastoArrendatario = 0;
    var breakEvenMes = 0;
    var serie = [];

    for (var m = 1; m <= meses; m++) {
      valor *= (1 + am);
      var tenencia = valor * (tenenciaPct / 100) / 12;
      var salidaCompra = (m <= plazo * 12 ? pmt : 0) + tenencia;
      var salidaRenta = rentaActual;

      // Quien gasta menos invierte la diferencia
      if (salidaCompra > salidaRenta) {
        cuentaArrendatario = cuentaArrendatario * (1 + rm) + (salidaCompra - salidaRenta);
        cuentaComprador = cuentaComprador * (1 + rm);
      } else {
        cuentaComprador = cuentaComprador * (1 + rm) + (salidaRenta - salidaCompra);
        cuentaArrendatario = cuentaArrendatario * (1 + rm);
      }

      gastoComprador += salidaCompra;
      gastoArrendatario += salidaRenta;

      if (m % 12 === 0) {
        rentaActual *= (1 + subeRenta / 100);
        var saldo = balanceAfter(prestamo, tasa, plazo, m);
        var patComprador = valor * (1 - ventaPct / 100) - saldo + cuentaComprador;
        var patArrendatario = cuentaArrendatario;
        serie.push({ año: m / 12, comprar: patComprador, rentar: patArrendatario });
        if (!breakEvenMes && patComprador > patArrendatario) breakEvenMes = m;
      }
    }

    var saldoFinal = balanceAfter(prestamo, tasa, plazo, meses);
    var valorVenta = valor * (1 - ventaPct / 100);
    var patC = valorVenta - saldoFinal + cuentaComprador;
    var patR = cuentaArrendatario;
    var dif = patC - patR;

    set('v-out-dif', money(Math.abs(dif)), dif >= 0 ? 'is-good' : 'is-bad');
    set('v-out-titulo', dif >= 0 ? 'Comprar gana por' : 'Rentar e invertir gana por');
    set('v-out-patc', money(patC));
    set('v-out-patr', money(patR));
    set('v-out-valor', money(valor));
    set('v-out-saldo', money(saldoFinal));
    set('v-out-equity', money(valorVenta - saldoFinal));
    set('v-out-cuentac', money(cuentaComprador));
    set('v-out-gastoc', money(gastoComprador));
    set('v-out-gastor', money(gastoArrendatario));
    set('v-out-pago', money(pmt));
    set('v-out-cash', money(cashInicial));

    var tbody = document.getElementById('v-tabla');
    if (tbody) {
      tbody.innerHTML = serie.filter(function (r) {
        return serie.length <= 12 || r.año % Math.ceil(serie.length / 10) === 0 || r.año === serie.length;
      }).map(function (r) {
        var d = r.comprar - r.rentar;
        return '<tr><td>Año ' + r.año + '</td><td>' + money(r.comprar) + '</td><td>' +
          money(r.rentar) + '</td><td style="color:' + (d >= 0 ? 'var(--good)' : 'var(--bad)') +
          '">' + (d >= 0 ? '+' : '−') + money(Math.abs(d)).replace('-', '') + '</td></tr>';
      }).join('');
    }

    if (breakEvenMes) {
      verdict('v-veredicto', 'good',
        'Comprar supera a rentar a partir del año ' + Math.ceil(breakEvenMes / 12) + '.',
        ' Antes de ese punto los costos de cierre y de venta (' + pct(cierrePct + ventaPct, 1) +
        ' del valor combinados) se comen la apreciación. Si tu horizonte real en esa ciudad es' +
        ' menor, rentar es la decisión financiera correcta.');
    } else {
      verdict('v-veredicto', 'warn',
        'En ' + num(horizonte, 0) + ' años, comprar no supera a rentar e invertir.',
        ' Con apreciación de ' + pct(aprec, 1) + ' contra un rendimiento alternativo de ' +
        pct(rendim, 1) + ', el capital rinde más fuera del inmueble. Cambia el horizonte o' +
        ' revisa si la apreciación de tu zona es realmente esa.');
    }
  }

  /* ==========================================================
     8. Flip: regla del 70 % y utilidad
     ========================================================== */
  function calcFlip() {
    if (!document.getElementById('f-arv')) return;

    var arv = val('f-arv');
    var reglaPct = val('f-regla');
    var remodel = val('f-remodelacion');
    var compra = val('f-compra');
    var cierreCompra = val('f-cierrecompra');   // %
    var cierreVenta = val('f-cierreventa');     // % (incluye comisión)
    var meses = val('f-meses');
    var mantMes = val('f-mantenimiento');
    var tasaDinero = val('f-tasadinero');       // anual sobre el monto financiado
    var financiado = val('f-financiado');       // % del costo de compra

    var mao = arv * reglaPct / 100 - remodel;

    var costoCompra = compra * (1 + cierreCompra / 100);
    var deuda = compra * financiado / 100;
    var interes = deuda * (tasaDinero / 100) * (meses / 12);
    var tenencia = mantMes * meses;
    var costoVenta = arv * cierreVenta / 100;
    var costoTotal = costoCompra + remodel + interes + tenencia + costoVenta;
    var utilidad = arv - costoTotal;
    var capitalPropio = costoCompra - deuda + remodel + interes + tenencia;
    var roi = capitalPropio > 0 ? (utilidad / capitalPropio) * 100 : 0;
    var roiAnual = meses > 0 ? roi * (12 / meses) : 0;
    var margen = arv > 0 ? (utilidad / arv) * 100 : 0;

    set('f-out-mao', money(mao));
    set('f-out-utilidad', money(utilidad), utilidad >= 0 ? 'is-good' : 'is-bad');
    set('f-out-costototal', money(costoTotal));
    set('f-out-capital', money(capitalPropio));
    set('f-out-roi', pct(roi, 1), roi >= 20 ? 'is-good' : (roi < 0 ? 'is-bad' : ''));
    set('f-out-roianual', pct(roiAnual, 1));
    set('f-out-margen', pct(margen, 1));
    set('f-out-interes', money(interes));
    set('f-out-costoventa', money(costoVenta));
    set('f-out-tenencia', money(tenencia));
    // Punto de equilibrio: a qué precio de venta la utilidad es cero
    var fijos = costoCompra + remodel + interes + tenencia;
    var equilibrio = fijos / (1 - cierreVenta / 100);
    set('f-out-equilibrio', money(equilibrio));

    if (compra > mao) {
      verdict('f-veredicto', 'bad',
        'Estás pagando ' + money(compra - mao) + ' de más.',
        ' La regla del ' + pct(reglaPct, 0) + ' marca una oferta máxima de ' + money(mao) +
        '. Cada peso por encima sale de tu utilidad, no del comprador final.');
    } else if (margen < 10) {
      verdict('f-veredicto', 'warn',
        'Margen ajustado: ' + pct(margen, 1) + ' sobre el valor de venta.',
        ' Debajo de 10 % no hay colchón para sobrecostos de obra ni para un mes extra en el' +
        ' mercado. Tu punto de equilibrio es vender en ' + money(equilibrio) + '.');
    } else {
      verdict('f-veredicto', 'good',
        'Utilidad de ' + money(utilidad) + ' · ROI anualizado ' + pct(roiAnual, 1) + '.',
        ' Tienes ' + money(arv - equilibrio) + ' de colchón antes de perder dinero.' +
        ' Presupuesta 15 % extra de obra: el sobrecosto es la regla, no la excepción.');
    }
  }

  /* ==========================================================
     8b. Análisis rápido (portada): 4 datos, 3 números
     ========================================================== */
  function calcRapido() {
    if (!document.getElementById('q-precio')) return;

    var precio = val('q-precio');
    var renta = val('q-renta');
    var gastosPct = val('q-gastos');   // % de la renta bruta que se va en gastos
    var engPct = val('q-enganche');
    var tasa = val('q-tasa');
    var años = val('q-plazo');

    var brutoAnual = renta * 12;
    var opex = brutoAnual * gastosPct / 100;
    var noi = brutoAnual - opex;
    var capRate = precio > 0 ? (noi / precio) * 100 : 0;
    var enganche = precio * engPct / 100;
    var pmt = payment(Math.max(0, precio - enganche), tasa, años);
    var flujoMes = noi / 12 - pmt;
    var coc = enganche > 0 ? (flujoMes * 12 / enganche) * 100 : 0;
    var regla1 = precio > 0 ? (renta / precio) * 100 : 0;

    set('q-out-caprate', pct(capRate));
    set('q-out-flujo', money(flujoMes), flujoMes >= 0 ? 'is-good' : 'is-bad');
    set('q-out-coc', pct(coc), coc >= 8 ? 'is-good' : (coc < 0 ? 'is-bad' : ''));
    set('q-out-regla1', pct(regla1), regla1 >= 0.7 ? 'is-good' : '');
    set('q-out-cuota', money(pmt));

    var el = document.getElementById('q-nota');
    if (el) {
      el.textContent = flujoMes >= 0
        ? 'Con estos números la propiedad se paga sola y te deja ' + money(flujoMes) + ' al mes.'
        : 'Con estos números pondrías ' + money(Math.abs(flujoMes)) + ' de tu bolsillo cada mes.';
    }
  }

  /* ==========================================================
     9. Enlazado y recálculo
     ========================================================== */
  function runAll() {
    calcHipoteca();
    calcRenta();
    calcCapacidad();
    calcVersus();
    calcFlip();
    calcRapido();
  }

  function init() {
    // Selector de moneda
    var sel = document.getElementById('moneda');
    if (sel) {
      sel.value = state.currency;
      sel.addEventListener('change', function () {
        state.currency = sel.value;
        try { localStorage.setItem(CUR_KEY, state.currency); } catch (e) { /* ignorar */ }
        runAll();
      });
    }

    // Recalcular en cualquier cambio de campo de una calculadora
    document.querySelectorAll('[data-calc] input, [data-calc] select').forEach(function (el) {
      el.addEventListener('input', runAll);
      el.addEventListener('change', runAll);
    });

    // Botón de restablecer valores de ejemplo
    document.querySelectorAll('[data-calc-reset]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var form = document.getElementById(btn.getAttribute('data-calc-reset'));
        if (!form) return;
        form.querySelectorAll('input[data-default]').forEach(function (el) {
          el.value = el.getAttribute('data-default');
        });
        runAll();
      });
    });

    runAll();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expuesto para pruebas manuales en consola
  window.RG = { payment: payment, principalFromPayment: principalFromPayment,
                balanceAfter: balanceAfter, schedule: schedule, runAll: runAll };
})();
