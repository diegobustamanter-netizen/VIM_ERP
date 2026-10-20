# Cobrar con tarjeta y emitir boletas desde VIM ERP — investigación

**Fecha:** 21 de agosto de 2026
**Valor UF usado para convertir precios:** $40.860

**Contexto:** VIM ERP se distribuye gratis, se instala en el PC de cada negocio y hoy no
emite ningún documento válido ante el SII. Tampoco se comunica con la máquina de tarjetas:
el cajero teclea el monto a mano.

---

## Lo primero: son dos problemas distintos

Conviene no mezclarlos, porque tienen soluciones, costos y urgencias diferentes.

| | Qué resuelve | Cuánto cuesta | Riesgo |
|---|---|---|---|
| **A. Integrar el terminal** | Que el monto viaje del ticket a la máquina | SDK gratis | Bajo |
| **B. Emitir boleta al SII** | Documento con validez tributaria | Desde $0 hasta $120.000/año | Medio |

**Se pueden hacer por separado y en ese orden.** La A es más barata, más simple y se nota
todos los días.

---

# PARTE A — Integrar la máquina de tarjetas

## El problema actual

Hoy el cajero cobra $12.300 en VIM ERP y después teclea el monto en la máquina. Si se
equivoca y pone $12.500, **nadie se entera**: la caja queda descuadrada al cierre y no hay
forma de saber por qué. Además, el botón "Tarjeta" del POS asume que el pago salió bien;
nunca pregunta.

## Transbank — verificado, hay SDK oficial de Python

`pip install transbank-pos-sdk` · versión 1.0.1 · licencia BSD · Python 3.4+

Se conecta por puerto USB al terminal. Métodos disponibles:

```python
POS.sale(12300, "VTA-20260821-0001")   # monto y ticket de referencia
POS.refund(operacion)                   # anular
POS.totals()                            # totales del día, para el cierre de caja
POS.last_sale()                         # recuperar la última venta
```

Soporta mensajes intermedios en vivo (el cliente pasó la tarjeta, ingresó la clave) para
mostrar el avance en pantalla.

**Requisito:** el terminal debe estar en **modo POS Integrado**, que se le solicita a
Transbank. No es lo mismo que el POS suelto que usan por defecto.

**Advertencia honesta:** la última versión del SDK es de **febrero de 2023**. Puede ser
simplemente que el protocolo esté estable, pero conviene confirmar que sigue mantenido
antes de apoyarse en él.

## Las otras marcas

En Chile hoy operan varias, no solo Transbank: **Getnet** (Santander), **Klap** (ex
Multicaja), **Compraquí** (BancoEstado), **Bci Pagos**, **Mercado Pago Point**, **SumUp**
y **TUU** (Haulmer).

> **Lo que NO pude verificar:** si estas marcas ofrecen un SDK de integración local
> equivalente al de Transbank. Solo confirmé el de Transbank. **No asumir que las demás lo
> tienen ni que no lo tienen** — hay que preguntarle a cada una.

Esto importa para un programa que se distribuye a cualquiera: si solo funciona con
Transbank, un negocio con Getnet se queda sin la función.

**Cómo diseñarlo para no quedar atrapado:** que la integración con el terminal sea un
módulo aparte, opcional y desactivable, con Transbank como primera implementación. Si
mañana aparece el SDK de otra marca, se agrega sin tocar el POS. Y quien no tenga terminal
integrado sigue cobrando como hoy.

---

# PARTE B — Emitir la boleta electrónica

## Por qué no conviene el camino de "software propio"

Si VIM ERP generara el XML, lo firmara y lo enviara al SII por su cuenta, habría que pasar
la certificación del SII: set de pruebas, envíos al ambiente de prueba y aprobación formal.
Varias semanas de trámite además del desarrollo (firma XMLDSig, timbre PDF417, CAF, SOAP).

Integrando un proveedor ya certificado, **VIM ERP no necesita certificarse**.

## Lo que el NEGOCIO necesita en cualquier caso

1. Inicio de actividades vigente y resolución del SII para emitir DTE.
2. **Certificado digital** (firma electrónica), archivo `.pfx` con contraseña.
3. **Folios (CAF)** asignados por el SII. Algunos proveedores los gestionan por ti.

---

## Comparación de proveedores

### 1. OpenFactura (Haulmer) — **mejor para un negocio en marcha**

| | |
|---|---|
| Precio | **$120.000 + IVA al año** (ventas mensuales bajo $100 millones) |
| Documentos | **Ilimitados** |
| API | REST, acceso ilimitado, incluida |
| Certificación ante el SII | **Incluida**, ellos hacen el trámite |
| Firma electrónica | $14.790 + IVA por 1 año (opcional, se compra ahí mismo) |
| Multi-empresa | Sí, se cobra por empresa |
| Respaldo | 3 réplicas, respaldo cada hora, 99,99% de uptime declarado |

**A favor:** ilimitado por menos plata que el plan más barato de SimpleAPI. Se hacen cargo
del trámite de certificación del contribuyente, que es justo lo que un almacenero no sabe
hacer. Es el mismo grupo que **TUU**, así que terminal y boleta quedarían en un ecosistema.

**En contra:** no hay plan gratuito. $120.000 al año es plata para un negocio muy chico.

---

### 2. SimpleAPI (Chilesystems) — **mejor para empezar y para negocios muy chicos**

| Plan | Precio | Documentos |
|---|---|---|
| **Gratuito** | **$0** (12 meses) | **500 peticiones/mes**, sirve en producción |
| Básico | 5 UF + IVA/año ≈ **$204.300 + IVA** | 10.000/mes |
| Estándar | 9 UF + IVA/año ≈ $367.700 + IVA | 50.000/mes |
| Código fuente | 70 UF ≈ $2.860.000, pago único | Sin límite, en tu servidor |

Certificado digital propio: $11.990 + IVA (1 año) · $17.990 (2 años) · $23.990 (3 años)

**A favor:** **el plan gratuito de 500 al mes es único en el mercado** y sirve en
producción, no solo en pruebas. Ideal para probar y para negocios de bajo volumen. REST,
usable desde Python. Multi-RUT. Documentación en Postman, videos, soporte por WhatsApp.

**En contra:** el negocio administra su propio CAF y certificado. Es más bajo nivel: hay
más que programar. Y **si el negocio crece, el plan Básico cuesta casi el doble que
OpenFactura por muchos menos documentos.**

⚠️ **A confirmar antes de prometer nada:** el plan dice "500 **peticiones**", no "500
boletas". Si emitir una boleta consume tres llamadas, el límite real son ~166 al mes.

---

### 3. SimpleFactura (misma empresa que SimpleAPI)

Todo resumido en un solo endpoint: asigna folios, envía al SII y al cliente, hace
seguimiento, incluye portal web.

| Plan | Mensual | Anual equivalente | Documentos |
|---|---|---|---|
| Independiente | $15.000 | $180.000 | 500 DTEs |
| Pyme | $30.000 | $360.000 | 2.000 DTEs |

**Veredicto:** hace más trabajo por ti que SimpleAPI, pero **OpenFactura cuesta menos y no
tiene tope**. Difícil de justificar salvo que el portal web les resulte imprescindible.

---

### 4. LibreDTE — código abierto

Biblioteca PHP con licencia AGPL.

- **Autoalojado:** gratis, pero hay que levantar y mantener un servidor PHP. Nadie que
  instale VIM ERP en el PC del local va a hacer eso.
- **Servicio Plus:** desde **$40.000 + IVA al mes** ($480.000 al año) por hasta 2.000
  documentos. El más caro de la lista.

**A favor:** es libre y auditable; no dependés de que la empresa siga existiendo.

---

### 5. BaseAPI — ❌ DESCARTADO

**Cierra el 11 de diciembre de 2026.** La capa gratuita y el registro de cuentas nuevas ya
están discontinuados.

> Esto es una advertencia, no solo un dato. Si hubiéramos integrado BaseAPI hace seis meses,
> hoy habría que rehacer todo y avisarle a cada negocio que instaló VIM ERP.
> **Al elegir proveedor pesa tanto su continuidad como su precio.**

---

## Comparación final, en plata

| Proveedor | Costo anual | Documentos | Certificación incluida |
|---|---|---|---|
| SimpleAPI Gratuito | **$0** | 500/mes | No |
| OpenFactura | $120.000 + IVA | **Ilimitados** | **Sí** |
| SimpleFactura Independiente | $180.000 | 500/mes | Sí |
| SimpleAPI Básico | ~$204.300 + IVA | 10.000/mes | No |
| SimpleFactura Pyme | $360.000 | 2.000/mes | Sí |
| LibreDTE Plus | $480.000 + IVA | 2.000/mes | — |

---

# Recomendación

**Soportar dos proveedores, no uno.** Son APIs REST parecidas y el trabajo extra es chico
si desde el principio se diseña con eso en mente:

- **SimpleAPI** para arrancar y para negocios chicos → **$0**.
- **OpenFactura** para negocios en marcha → ilimitado y con la certificación incluida.

Así el almacén de barrio no paga nada y el que crece tiene a dónde ir sin cambiar de
programa. Y si uno de los dos cierra —como pasó con BaseAPI— el otro sigue.

**Orden de trabajo sugerido:**

1. **Integrar el terminal de Transbank.** Barato, útil desde el primer día, sin normativa
   de por medio.
2. **Preguntar a las otras marcas** si tienen SDK, antes de prometer compatibilidad.
3. **Recién después, la boleta electrónica.**

---

# Cómo encajaría en VIM ERP

**Configuración → pestaña nueva "Facturación electrónica":**

- Casilla para activarla (apagada por defecto: quien no la necesite ni la ve).
- Elegir proveedor: SimpleAPI u OpenFactura.
- RUT y razón social del negocio.
- Certificado `.pfx` y su contraseña (solo si el proveedor lo requiere).
- Clave de API.
- Botón **"Probar conexión"** que emite un documento en el ambiente de prueba.

**Configuración → pestaña "Terminal de tarjetas":**

- Casilla para activarlo.
- Detectar puerto automáticamente (`POS.list_ports()`).
- Botón "Probar" que ejecute un `poll()`.

**Al cobrar con tarjeta en el POS:**

1. VIM ERP le manda el monto al terminal.
2. El terminal cobra y responde aprobado o rechazado.
3. **Si fue rechazado, la venta no se registra.** Hoy se registraría igual.
4. Si fue aprobado, se guarda la venta con el número de operación del terminal.

**Al emitir la boleta:**

1. La venta se registra en la base local **primero**, como hoy.
2. Después se intenta emitir.
3. Si sale bien, se guarda el folio del SII junto a la venta.
4. Si falla (sin internet, SII caído), **la venta igual queda registrada** y la boleta entra
   en una cola de pendientes que se reintenta sola.

> Esto último no es opcional. Un POS que deja de vender porque se cayó internet es un POS
> inservible. La cola de reintentos es la parte que más se subestima de este trabajo.

**Lo que habría que cambiar de lo que ya existe:**

- Los folios internos (`VTA-20260821-0001`) conviven con los del SII: son cosas distintas.
- **Anular una venta deja de ser posible** una vez emitida la boleta. Se corrige con Nota de
  Crédito, que es otro documento electrónico. Hay que reemplazar la función actual.
- El certificado va a `%LOCALAPPDATA%\VIM_ERP\certificados`, nunca a la base de datos ni a
  una carpeta sincronizada con OneDrive.

---

# Antes de escribir código

1. **Sacar la clave gratuita de SimpleAPI** y emitir en el ambiente de certificación. Gratis
   y toma minutos. Sin esto, todo lo demás es teoría.
2. **Confirmar cuántas peticiones consume UNA boleta** en el plan gratuito.
3. **Preguntar a Getnet, Klap, Compraquí y Mercado Pago** si tienen SDK de integración local.
4. **Confirmar que el SDK de Transbank sigue mantenido** (última versión: febrero 2023).
5. **Confirmar con un contador** qué documentos necesita emitir el negocio en concreto.

---

## Fuentes

**SII**
- [Sistema de facturación gratuito](https://www.sii.cl/servicios_online/1039-1183.html)
- [Proceso de certificación](https://www.sii.cl/factura_electronica/factura_mercado/proceso_certificacion.htm)
- [Certificado digital](https://www.sii.cl/destacados/factura_electronica/certificado_digital.htm)
- [Instructivo técnico Boleta Electrónica](https://www.sii.cl/servicios_online/3532-instructivo_tecnico_be-3811.html)

**Terminales**
- [Transbank — POS Integrado](https://www.transbankdevelopers.cl/documentacion/posintegrado)
- [SDK Python oficial (PyPI)](https://pypi.org/project/transbank-pos-sdk/)
- [Transbank — Boleta Electrónica](https://publico.transbank.cl/productos-y-servicios/otras-soluciones-para-negocio/boleta-electronica)
- [Comparativa de terminales en Chile 2026](https://comocobro.cl/quiero-emprender/comparativa-maquinitas-pos-chile-2026)

**Proveedores de DTE**
- [OpenFactura / Haulmer — API](https://www.haulmer.dev/factura-electronica)
- [TUU (POS de Haulmer)](https://www.tuu.cl/)
- [SimpleAPI — Precios](https://www.simpleapi.cl/Precios) · [Documentación](https://documentacion.simpleapi.cl)
- [SimpleFactura](https://www.simplefactura.cl/)
- [LibreDTE](https://www.libredte.cl/) · [Servicio Plus](https://www.libredte.cl/plus)
- [BaseAPI — aviso de cierre](https://baseapi.cl/blog/factura-electronica-chile-guia-completa-2026)

**Referencia**
- [Valor UF](https://www.calcular.cl/valor-uf)

---

*Nota: no soy asesor tributario. Los precios y condiciones cambian; verificá directamente
con cada proveedor antes de decidir.*
