# Pruebas automáticas de VIM ERP

## Cómo correrlas

Doble clic en **`test.bat`** (está en la carpeta VIM_ERP, un nivel arriba).

O desde la terminal:

```
cd tests
python -m unittest discover -v
```

Para correr un solo archivo: `python -m unittest test_ventas -v`

## Tu base de datos real nunca se toca

Cada prueba crea una base nueva y vacía en la carpeta temporal de Windows, la
llena con el esquema real y los datos semilla, y la borra al terminar.

Además hay un cinturón de seguridad: si por algún motivo las pruebas llegaran a
apuntar a una base que no es temporal, se abortan solas antes de tocar nada
(`base.py`, `_verificar_aislamiento`).

## Qué cuida cada archivo

| Archivo | Qué protege |
|---|---|
| `test_estado_resultados.py` | Que la utilidad sea la real: sin doble conteo de mercadería, sin activos fijos como gasto, sin aportes de capital inflando la ganancia. Y el cálculo del IVA |
| `test_ventas.py` | Que el precio cobrado sea el registrado, que no se venda stock inexistente y que los folios no se repitan ni con dos cajas simultáneas |
| `test_modo_negocio.py` | Que productos y servicios no se mezclen y que cambiar de modo no altere ventas ya hechas |
| `test_seguridad.py` | Contraseñas con salt y la ventana de gracia de 60 s: que expire y que no se contagie entre acciones |

## No son pruebas decorativas

**Cada prueba corresponde a un error que el sistema tuvo de verdad y que se
corrigió.** Si una falla, ese error volvió. El mensaje de cada `assert` explica
qué se estaba cuidando.

Ejemplos de lo que se rompió alguna vez y hoy está cubierto:

- La compra de mercadería se contaba como gasto **y** como costo de venta, así
  que el sistema mostraba pérdidas donde había ganancias.
- Un aporte de plata a la caja bajaba los gastos y hacía subir la utilidad sin
  haber vendido nada.
- El precio modificado a mano se mostraba en el recibo pero se guardaba el de
  catálogo: el cliente veía un número y el sistema registraba otro.
- Dos ventas en el mismo segundo generaban el mismo folio y la segunda se
  rechazaba.

## Al agregar una prueba

1. Heredá de `PruebaVIM` (`base.py`), que ya te deja una base limpia.
2. Usá los ayudantes: `abrir_caja()`, `crear_producto()`, `crear_compra()`,
   `linea_ticket()`, `pnl()`, `configurar_iva()`.
3. Poné en el `assert` un mensaje que diga **qué se rompe** si falla, no qué
   valor se esperaba.

## Cuándo correrlas

Antes de compilar con `build.bat`, y después de cualquier cambio que toque
plata: precios, ventas, reportes o stock.
