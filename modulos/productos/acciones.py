from tkinter import messagebox

from database import registrar_movimiento, ahora, session_db
from database.productos import (
    _resolver_categoria_id, _resolver_proveedor_id,
    buscar_conflicto_de_codigo, liberar_codigos_de_eliminados,
)
from vim_logger import get_logger


class ProductosAccionesMixin:

    def guardar_o_actualizar(self):
        """Un solo botón: si hay un producto cargado se actualiza, si no se crea."""
        if self.producto_id:
            self.actualizar_producto()
        else:
            self.guardar_producto()

    def _codigos_disponibles(self, conn, codigos, excluir_id=None):
        """Avisa antes de guardar si el código ya lo usa otro producto.

        Antes solo se enteraba la base (UNIQUE) y el mensaje no decía cuál
        producto lo tenía. Además no se revisaba que un PLU coincidiera con
        el código de barras de otro producto.
        """
        conflicto = buscar_conflicto_de_codigo(conn, codigos, excluir_id)
        if conflicto and conflicto["activo"]:
            messagebox.showerror(
                "Código repetido",
                f"El código {conflicto['codigo']} ya lo usa el producto "
                f"«{conflicto['nombre']}».\n\nUsa otro código o edita ese producto."
            )
            self.entry_codigo_barras.focus_set()
            return False
        # Si solo lo tenía un producto eliminado, se le quita y queda libre
        liberar_codigos_de_eliminados(conn, codigos, excluir_id)
        return True

    def guardar_producto(self):
        datos = self.obtener_datos_formulario()
        if not datos:
            return

        try:
            with session_db() as conn:
                cursor = conn.cursor()

                categoria_texto = datos[9]
                proveedor_texto = datos[10]
                tipo_venta = datos[11]
                tipo_item = datos[12]

                codigo_barras = datos[0] or None
                codigo_pos = datos[1] or None

                if not self._codigos_disponibles(conn, [codigo_barras, codigo_pos]):
                    return

                unidad_medida = "kg" if tipo_venta == "peso" else "unidad"
                categoria_id = None
                proveedor_id = None
                permite_descuento = 1

                # Si la categoría o el proveedor escritos no existen, se crean.
                # Antes solo se buscaban y, al no encontrarlos, el producto
                # quedaba guardado sin categoría ni proveedor.
                categoria_id = _resolver_categoria_id(
                    conn, categoria_texto=categoria_texto, crear_si_no_existe=True)
                proveedor_id = _resolver_proveedor_id(
                    conn, proveedor_texto=proveedor_texto, crear_si_no_existe=True)

                cursor.execute(
                    """
                    INSERT INTO productos (
                        codigo_barras,
                        codigo_pos,
                        nombre,
                        descripcion,
                        categoria_id,
                        proveedor_id,
                        precio_compra,
                        precio_venta,
                        precio_por_kilo,
                        stock,
                        stock_minimo,
                        unidad_medida,
                        tipo_venta,
                        tipo_item,
                        permite_descuento,
                        activo,
                        fecha_creacion
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                    """,
                    (
                        codigo_barras,
                        codigo_pos,
                        datos[2],
                        datos[3],
                        categoria_id,
                        proveedor_id,
                        datos[4],
                        datos[5],
                        datos[6],
                        datos[7],
                        datos[8],
                        unidad_medida,
                        tipo_venta,
                        tipo_item,
                        permite_descuento,
                        ahora(),
                    )
                )

                detalle = (
                    f"Producto agregado: {datos[2]} | "
                    f"Categoría texto: {categoria_texto} | "
                    f"Proveedor texto: {proveedor_texto} | "
                    f"Categoria ID: {categoria_id} | "
                    f"Proveedor ID: {proveedor_id}"
                )
                registrar_movimiento(conn, "ALTA", detalle, tabla="productos", referencia_id=cursor.lastrowid)
                conn.commit()

            messagebox.showinfo("Éxito", "Producto guardado correctamente.")
            self.limpiar_formulario()
            self.cargar_productos()

        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                messagebox.showerror("Error", "El código de barras o código POS ya existe.")
            else:
                messagebox.showerror("Error", f"No se pudo guardar el producto.\n{e}")

    def actualizar_producto(self):
        if not self.producto_id:
            messagebox.showwarning("Atención", "Selecciona un producto para actualizar.")
            return

        datos = self.obtener_datos_formulario()
        if not datos:
            return

        try:
            with session_db() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT codigo_barras,
                           codigo_pos,
                           nombre,
                           descripcion,
                           categoria_id,
                           proveedor_id,
                           precio_compra,
                           precio_venta,
                           precio_por_kilo,
                           stock,
                           stock_minimo,
                           tipo_venta,
                           tipo_item
                    FROM productos
                    WHERE id = ?
                    """,
                    (self.producto_id,)
                )
                anterior = cursor.fetchone()

                if not anterior:
                    messagebox.showerror("Error", "Producto no encontrado.")
                    return

                categoria_texto = datos[9]
                proveedor_texto = datos[10]
                tipo_venta = datos[11]
                tipo_item = datos[12]

                codigo_barras = datos[0] or None
                codigo_pos = datos[1] or None

                if not self._codigos_disponibles(conn, [codigo_barras, codigo_pos],
                                                 excluir_id=self.producto_id):
                    return
                unidad_medida = "kg" if tipo_venta == "peso" else "unidad"

                categoria_id = None
                proveedor_id = None

                # Si la categoría o el proveedor escritos no existen, se crean.
                # Antes solo se buscaban y, al no encontrarlos, el producto
                # quedaba guardado sin categoría ni proveedor.
                categoria_id = _resolver_categoria_id(
                    conn, categoria_texto=categoria_texto, crear_si_no_existe=True)
                proveedor_id = _resolver_proveedor_id(
                    conn, proveedor_texto=proveedor_texto, crear_si_no_existe=True)

                cursor.execute(
                    """
                    UPDATE productos
                    SET codigo_barras = ?,
                        codigo_pos = ?,
                        nombre = ?,
                        descripcion = ?,
                        categoria_id = ?,
                        proveedor_id = ?,
                        precio_compra = ?,
                        precio_venta = ?,
                        precio_por_kilo = ?,
                        stock = ?,
                        stock_minimo = ?,
                        unidad_medida = ?,
                        tipo_venta = ?,
                        tipo_item = ?,
                        fecha_actualizacion = ?
                    WHERE id = ?
                    """,
                    (
                        codigo_barras,
                        codigo_pos,
                        datos[2],
                        datos[3],
                        categoria_id,
                        proveedor_id,
                        datos[4],
                        datos[5],
                        datos[6],
                        datos[7],
                        datos[8],
                        unidad_medida,
                        tipo_venta,
                        tipo_item,
                        ahora(),
                        self.producto_id
                    )
                )

                if cursor.rowcount == 0:
                    messagebox.showerror("Error", "No se pudo actualizar el producto.")
                    return

                nombres_campos = [
                    "Código de barras",
                    "Código POS",
                    "Nombre",
                    "Descripción",
                    "Categoría ID",
                    "Proveedor ID",
                    "Precio compra",
                    "Precio venta",
                    "Precio por kilo",
                    "Stock",
                    "Stock mínimo",
                    "Tipo venta",
                    "Tipo de ítem"
                ]

                datos_comparacion = (
                    codigo_barras,
                    codigo_pos,
                    datos[2],
                    datos[3],
                    categoria_id,
                    proveedor_id,
                    datos[4],
                    datos[5],
                    datos[6],
                    datos[7],
                    datos[8],
                    tipo_venta,
                    tipo_item
                )

                cambios = []
                for i, (valor_anterior, valor_nuevo) in enumerate(zip(anterior, datos_comparacion)):
                    va = "" if valor_anterior is None else valor_anterior
                    vn = "" if valor_nuevo is None else valor_nuevo
                    if str(va) != str(vn):
                        cambios.append(f"{nombres_campos[i]}: {va} → {vn}")

                detalle = (
                    f"Producto actualizado: {datos[2]} | "
                    + (" | ".join(cambios) if cambios else "Sin cambios detectados")
                    + f" | Categoría texto: {categoria_texto} | Proveedor texto: {proveedor_texto}"
                )

                registrar_movimiento(conn, "MODIFICACIÓN", detalle, tabla="productos", referencia_id=self.producto_id)
                conn.commit()

            messagebox.showinfo("Éxito", "Producto actualizado correctamente.")
            self.limpiar_formulario()
            self.cargar_productos()

        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                messagebox.showerror("Error", "El código de barras o código POS ya existe.")
            else:
                messagebox.showerror("Error", f"No se pudo actualizar el producto.\n{e}")

    def eliminar_producto(self):
        if not self.producto_id:
            messagebox.showwarning("Atención", "Selecciona un producto para eliminar.")
            return

        from modulos.seguridad.autorizacion_ui import (
            solicitar_autorizacion_admin, VENTANA_GRACIA_SEGUNDOS
        )
        from modulos.seguridad.sesion import Sesion

        # ambito="eliminar_producto": tras autorizar una vez, borrar otros
        # productos dentro del minuto siguiente no vuelve a pedir la clave.
        AMBITO = "eliminar_producto"
        venia_autorizado = Sesion.autorizacion_vigente(AMBITO, VENTANA_GRACIA_SEGUNDOS)

        if not solicitar_autorizacion_admin(
            self.root,
            f"Eliminar producto: {self.entry_nombre.get().strip()}",
            ambito=AMBITO,
        ):
            return

        # Si no se pidió la contraseña, avisarlo: que nadie borre creyendo
        # que el sistema se la iba a pedir.
        nota_gracia = ""
        if venia_autorizado:
            restantes = Sesion.segundos_restantes_autorizacion(AMBITO, VENTANA_GRACIA_SEGUNDOS)
            nota_gracia = (f"\n\n(Autorización de administrador vigente por "
                           f"{restantes}s más, por eso no se pidió la contraseña.)")

        confirmar = messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Deseas eliminar este producto?{nota_gracia}"
        )
        if not confirmar:
            return

        try:
            nombre_producto = self.entry_nombre.get().strip()

            with session_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE productos
                    SET activo = 0,
                        fecha_actualizacion = ?
                    WHERE id = ?
                    """,
                    (ahora(), self.producto_id)
                )

                if cursor.rowcount == 0:
                    messagebox.showerror("Error", "No se encontró el producto para eliminar.")
                    return

                registrar_movimiento(conn, "BAJA", f"Producto eliminado: {nombre_producto}", tabla="productos", referencia_id=self.producto_id)
                conn.commit()

            messagebox.showinfo("Éxito", "Producto eliminado correctamente.")
            self.limpiar_formulario()
            self.cargar_productos()

        except Exception as e:
            get_logger("productos").exception("Falló la eliminación de producto")
            messagebox.showerror("Error", f"No se pudo eliminar el producto.\n{e}")