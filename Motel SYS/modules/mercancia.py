"""
===============================================================================
SISTEMA DE GESTIÓN DE MOTELES - MOTEL PRO v2.0
Módulo: modules/mercancia.py (VENTAS, TICKET PDF, INVENTARIO Y AUDITORÍA)
===============================================================================
"""

import os
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from fpdf import FPDF

# Importaciones desde la Capa de Datos (Incluyendo motor de auditoría y stock)
from database.db_manager import (
    obtener_estancias_activas, obtener_tasa_bcv, obtener_productos,
    agregar_producto, actualizar_producto, eliminar_producto,
    descontar_stock_producto, registrar_venta_mercancia_carrito,
    registrar_auditoria
)


def centrar_ventana(win, ancho: int, alto: int):
    """Centra cualquier ventana emergente en el monitor."""
    win.update_idletasks()
    pantalla_ancho = win.winfo_screenwidth()
    pantalla_alto = win.winfo_screenheight()
    x = max(0, (pantalla_ancho - ancho) // 2)
    y = max(0, (pantalla_alto - alto) // 2)
    win.geometry(f"{ancho}x{alto}+{x}+{y}")


class PDFTicketVenta(FPDF):
    """Generador de Comprobante / Ticket de Venta de Mini-Bar."""
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A5')
        self.set_margins(10, 10, 10)

    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 5, "INVERSIONES SAIBABA C.A. - MOTEL EL EDEN", 0, 1, "C")
        self.set_font("Arial", "B", 9)
        self.cell(0, 4.5, "RIF: J-30250227-6 | COMPROBANTE DE VENTA DE MINI-BAR", 0, 1, "C")
        self.ln(3)


class FrameMercancia(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#191715")
        self.controller = controller
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.carrito = []

        self.habitacion_activa = None
        # =====================================================================
        # PANEL IZQUIERDO: SELECCIÓN Y AGREGAR AL CARRITO
        # =====================================================================
        self.frame_left = ctk.CTkFrame(self, fg_color="#23201C", corner_radius=12, border_width=1, border_color="#36322C")
        self.frame_left.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")

        ctk.CTkLabel(self.frame_left, text="Venta de Mercancía", font=("Georgia", 16, "bold"), text_color="#D4A343").pack(pady=10)

        # Botón para abrir la ventana de inventario
        ctk.CTkButton(
            self.frame_left, text="📦 Administrar Inventario y Catálogo", fg_color="#3E342B", hover_color="#524539",
            text_color="#F4EFE6", font=("Arial", 11, "bold"), command=self.modal_inventario
        ).pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkLabel(self.frame_left, text="Habitación Ocupada:", font=("Arial", 11, "bold"), text_color="#A89F91").pack(anchor="w", padx=12)
        self.combo_hab = ctk.CTkComboBox(self.frame_left, values=["Cargando..."], command=self.al_cambiar_habitacion)
        self.combo_hab.pack(fill="x", padx=12, pady=4)

        ctk.CTkLabel(self.frame_left, text="Seleccionar Producto:", font=("Arial", 11, "bold"), text_color="#A89F91").pack(anchor="w", padx=12, pady=(6, 0))
        self.combo_prod = ctk.CTkComboBox(self.frame_left, values=["Cargando..."], command=self.al_seleccionar_producto)
        self.combo_prod.pack(fill="x", padx=12, pady=4)

        self.e_precio_usd = ctk.CTkEntry(self.frame_left, placeholder_text="Precio Unitario ($)", fg_color="#2D2924", state="disabled")
        self.e_precio_usd.pack(fill="x", padx=12, pady=4)

        self.lbl_stock_disp = ctk.CTkLabel(self.frame_left, text="Stock disponible: --", font=("Arial", 10, "italic"), text_color="#D4A343")
        self.lbl_stock_disp.pack(anchor="w", padx=12)

        self.e_cant = ctk.CTkEntry(self.frame_left, placeholder_text="Cantidad a Vender", fg_color="#2D2924")
        self.e_cant.pack(fill="x", padx=12, pady=4)

        ctk.CTkButton(
            self.frame_left, text="➕ Agregar al Carrito", fg_color="#D4A343", hover_color="#B8892E",
            text_color="#191715", font=("Arial", 11, "bold"), command=self.agregar_al_carrito
        ).pack(fill="x", padx=12, pady=12)

        # =====================================================================
        # PANEL DERECHO: CARRITO DE COMPRAS Y COBRO
        # =====================================================================
        self.frame_right = ctk.CTkFrame(self, fg_color="#23201C", corner_radius=12, border_width=1, border_color="#36322C")
        self.frame_right.grid(row=0, column=1, padx=12, pady=12, sticky="nsew")

        ctk.CTkLabel(self.frame_right, text="Carrito de Compras de la Habitación", font=("Georgia", 16, "bold"), text_color="#D4A343").pack(pady=10)

        self.scroll_carrito = ctk.CTkScrollableFrame(self.frame_right, fg_color="#191715", label_text="Productos en este Ticket")
        self.scroll_carrito.pack(fill="both", expand=True, padx=12, pady=5)

        self.lbl_totales = ctk.CTkLabel(self.frame_right, text="TOTAL: $0.00 | 0,00 Bs", font=("Arial", 14, "bold"), text_color="#D4A343")
        self.lbl_totales.pack(pady=4)

        frame_pago = ctk.CTkFrame(self.frame_right, fg_color="transparent")
        frame_pago.pack(fill="x", padx=12, pady=4)

        ctk.CTkLabel(frame_pago, text="Método de Pago:", font=("Arial", 11, "bold"), text_color="#A89F91").pack(side="left", padx=5)
        self.combo_metodo = ctk.CTkComboBox(
            frame_pago, values=["EFECTIVO USD", "EFECTIVO BS", "PAGO MOVIL", "PUNTO DE VENTA"],
            command=lambda v: self.toggle_p2p(v)
        )
        self.combo_metodo.pack(side="left", padx=5)

        self.frame_p2p = ctk.CTkFrame(self.frame_right, fg_color="transparent")
        self.e_ref = ctk.CTkEntry(self.frame_p2p, placeholder_text="Ref (4 dígitos)", fg_color="#2D2924")
        self.e_ref.pack(side="left", padx=2)
        self.e_ci = ctk.CTkEntry(self.frame_p2p, placeholder_text="C.I. Emisor", fg_color="#2D2924")
        self.e_ci.pack(side="left", padx=2)
        self.e_tel = ctk.CTkEntry(self.frame_p2p, placeholder_text="Teléfono Emisor", fg_color="#2D2924")
        self.e_tel.pack(side="left", padx=2)

        ctk.CTkButton(
            self.frame_right, text="💳 Procesar Venta y Generar Ticket PDF", fg_color="#1E5F38", hover_color="#2E7D32",
            text_color="#F4EFE6", font=("Arial", 12, "bold"), command=self.procesar_venta_final
        ).pack(fill="x", padx=12, pady=10)

        self.cargar_combos()

    def toggle_p2p(self, metodo):
        if metodo == "PAGO MOVIL":
            self.frame_p2p.pack(fill="x", padx=12, pady=4)
        else:
            self.frame_p2p.pack_forget()

    def cargar_combos(self):
        estancias = obtener_estancias_activas()
        habs = [e["hab_codigo"] for e in estancias] if estancias else ["Sin Habitaciones Ocupadas"]
        self.combo_hab.configure(values=habs)
        self.combo_hab.set(habs[0])
        self.habitacion_activa = habs[0]

        self.productos_db = obtener_productos()
        nombres = [p["nombre"] for p in self.productos_db]
        if nombres:
            self.combo_prod.configure(values=nombres)
            self.combo_prod.set(nombres[0])
            self.al_seleccionar_producto(nombres[0])
        else:
            self.combo_prod.configure(values=["Sin Productos (Ir a Inventario)"])
            self.combo_prod.set("Sin Productos (Ir a Inventario)")

    # =========================================================================
    # GUARDIÁN DE TRANSACCIÓN: PREVIENE MEZCLAR CONSUMOS ENTRE HABITACIONES
    # =========================================================================
    def al_cambiar_habitacion(self, nueva_seleccion):
        """Si hay productos en el carrito, solicita confirmación antes de cambiar de habitación."""
        if self.carrito and self.habitacion_activa and nueva_seleccion != self.habitacion_activa:
            confirmar = messagebox.askyesno(
                "⚠️ Carrito con Productos Activo",
                f"Actualmente tienes {len(self.carrito)} producto(s) cargados para la habitación '{self.habitacion_activa}'.\n\n"
                f"¿Deseas VACIAR el carrito para cambiar a la habitación '{nueva_seleccion}'?\n\n"
                f"(Si presionas 'No', se mantendrá la habitación '{self.habitacion_activa}' para terminar de cobrar)."
            )
            if confirmar:
                # Vaciar carrito y cambiar a la nueva habitación
                self.carrito.clear()
                self.renderizar_carrito()
                self.habitacion_activa = nueva_seleccion
            else:
                # Revertir el selector a la habitación original
                self.combo_hab.set(self.habitacion_activa)
        else:
            self.habitacion_activa = nueva_seleccion

    def al_seleccionar_producto(self, seleccion):
        """Bloquea el campo de precio para que el cajero no pueda modificarlo manualmente."""
        for p in self.productos_db:
            if p["nombre"] == seleccion:
                self.e_precio_usd.configure(state="normal")  # Habilita temporalmente para escribir
                self.e_precio_usd.delete(0, 'end')
                self.e_precio_usd.insert(0, str(p["precio_usd"]))
                self.e_precio_usd.configure(state="disabled") # BLOQUEADO (Read-Only)
                self.lbl_stock_disp.configure(text=f"Stock disponible: {p['stock']} unidades")
                return
        self.e_precio_usd.configure(state="normal")
        self.e_precio_usd.delete(0, 'end')
        self.e_precio_usd.configure(state="disabled")

    def agregar_al_carrito(self):
        prod = self.combo_prod.get()
        precio = self.e_precio_usd.get().strip()
        cant = self.e_cant.get().strip()

        if not cant or not cant.isdigit() or int(cant) <= 0:
            messagebox.showwarning("Atención", "Ingrese una cantidad válida.")
            return

        c_num = int(cant)
        prod_obj = next((p for p in self.productos_db if p["nombre"] == prod), None)
        if prod_obj and c_num > prod_obj["stock"]:
            messagebox.showerror("Stock Insuficiente", f"Solo quedan {prod_obj['stock']} unidades disponibles de '{prod}'.")
            return

        try:
            p_usd = float(precio.replace(",", "."))
            tasa = obtener_tasa_bcv()
            sub_usd = p_usd * c_num
            sub_bs = sub_usd * tasa

            self.carrito.append({
                "producto": prod, "cantidad": c_num,
                "precio_unit_usd": p_usd, "subtotal_usd": sub_usd, "subtotal_bs": sub_bs
            })
            self.e_cant.delete(0, 'end')
            self.renderizar_carrito()
        except ValueError:
            messagebox.showerror("Error", "Precio no válido.")

    def renderizar_carrito(self):
        for w in self.scroll_carrito.winfo_children():
            w.destroy()

        tot_usd, tot_bs = 0.0, 0.0
        for idx, item in enumerate(self.carrito):
            tot_usd += item["subtotal_usd"]
            tot_bs += item["subtotal_bs"]

            card = ctk.CTkFrame(self.scroll_carrito, fg_color="#2D2924")
            card.pack(fill="x", pady=2, padx=5)

            txt = f"{item['producto']} x{item['cantidad']} | ${item['subtotal_usd']:.2f} ({item['subtotal_bs']:,.2f} Bs)"
            ctk.CTkLabel(card, text=txt, font=("Arial", 11), text_color="#F4EFE6").pack(side="left", padx=10, pady=4)

            btn_del = ctk.CTkButton(card, text="🗑️", width=30, fg_color="#78281F", hover_color="#943126", command=lambda i=idx: self.quitar_item(i))
            btn_del.pack(side="right", padx=5)

        self.lbl_totales.configure(text=f"TOTAL: ${tot_usd:.2f} | {tot_bs:,.2f} Bs (Bloqueado)")

    def quitar_item(self, index):
        self.carrito.pop(index)
        self.renderizar_carrito()

    # =========================================================================
    # PROCESAMIENTO DE VENTA FINAL CON AUDITORÍA
    # =========================================================================
    def procesar_venta_final(self):
        hab = self.combo_hab.get()
        if hab in ["Sin Habitaciones Ocupadas", "Cargando..."]:
            messagebox.showerror("Error", "Seleccione una habitación ocupada.")
            return

        if not self.carrito:
            messagebox.showwarning("Atención", "El carrito está vacío.")
            return

        metodo = self.combo_metodo.get()
        ref, ci, tel = None, None, None
        if metodo == "PAGO MOVIL":
            ref, ci, tel = self.e_ref.get().strip(), self.e_ci.get().strip(), self.e_tel.get().strip()
            if not (ref and ci and tel):
                messagebox.showerror("Error", "Complete los datos del Pago Móvil.")
                return

        tot_usd = sum(i["subtotal_usd"] for i in self.carrito)
        tot_bs = sum(i["subtotal_bs"] for i in self.carrito)
        ahora = datetime.now()
        usr_act = self.controller.usuario_actual["usuario"]
        rol_act = self.controller.usuario_actual["rol"]

        cabecera = {
            "hab_codigo": hab, "total_usd": tot_usd, "total_bs": tot_bs,
            "metodo": metodo, "p2p_referencia": ref, "p2p_ci": ci, "p2p_telefono": tel,
            "fecha": ahora.strftime("%Y-%m-%d %H:%M:%S"),
            "turno": "MAÑANA" if 8 <= ahora.hour < 17 else "NOCHE",
            "recepcionista": usr_act
        }

        venta_id = registrar_venta_mercancia_carrito(cabecera, self.carrito)
        if venta_id:
            # Descontar stock de cada ítem
            for item in self.carrito:
                descontar_stock_producto(item["producto"], item["cantidad"])

            # AUDITORÍA AUTOMÁTICA DE VENTA DE MERCANCÍA
            resumen_items = ", ".join([f"{it['cantidad']}x {it['producto']}" for it in self.carrito])
            p2p_info = f" [Ref P2P: {ref}]" if metodo == "PAGO MOVIL" else ""
            registrar_auditoria(
                usr_act, rol_act, "VENTA_MINIBAR",
                f"Venta Ticket #{venta_id:06d} (Hab {hab}): {resumen_items}. Total: ${tot_usd:.2f} ({tot_bs:,.2f} Bs) [{metodo}{p2p_info}]."
            )

            # Generar comprobante PDF
            self.generar_ticket_pdf(venta_id, cabecera, self.carrito)
            messagebox.showinfo("Éxito", f"Venta #{venta_id:06d} registrada y stock actualizado.")

            # Limpiar Carrito y restablecer campos
            self.carrito.clear()
            self.renderizar_carrito()
            self.cargar_combos()

            # Limpiar campos de pago móvil y resetear método
            self.e_ref.delete(0, 'end')
            self.e_ci.delete(0, 'end')
            self.e_tel.delete(0, 'end')
            self.combo_metodo.set("EFECTIVO USD")
            self.toggle_p2p("EFECTIVO USD")
        else:
            messagebox.showerror("Error", "No se pudo registrar la venta.")

    def generar_ticket_pdf(self, venta_id, cabecera, items):
        pdf = PDFTicketVenta()
        pdf.add_page()
        pdf.set_font("Arial", "", 9)

        tasa = obtener_tasa_bcv()

        pdf.cell(0, 5, f"Ticket N°: {venta_id:06d} | Habitación: {cabecera['hab_codigo']}", 0, 1)
        pdf.cell(0, 5, f"Fecha: {cabecera['fecha']} | Turno: {cabecera['turno']}", 0, 1)
        pdf.cell(0, 5, f"Atendido por: {cabecera['recepcionista']} | Pago: {cabecera['metodo']}", 0, 1)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(0, 5, f"Tasa BCV Aplicada: {tasa:.2f} Bs / USD", 0, 1)
        pdf.ln(3)

        pdf.set_font("Arial", "B", 8)
        pdf.cell(60, 6, "Producto", 1)
        pdf.cell(15, 6, "Cant", 1, 0, "C")
        pdf.cell(25, 6, "P.Unit ($)", 1, 0, "C")
        pdf.cell(30, 6, "Subtotal ($)", 1, 0, "C")
        pdf.ln()

        pdf.set_font("Arial", "", 8)
        for item in items:
            pdf.cell(60, 5, item["producto"][:30], 1)
            pdf.cell(15, 5, str(item["cantidad"]), 1, 0, "C")
            pdf.cell(25, 5, f"${item['precio_unit_usd']:.2f}", 1, 0, "C")
            pdf.cell(30, 5, f"${item['subtotal_usd']:.2f}", 1, 0, "C")
            pdf.ln()

        pdf.ln(3)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 6, f"TOTAL USD ($): ${cabecera['total_usd']:.2f}", 0, 1, "R")
        pdf.cell(0, 6, f"TOTAL BOLÍVARES (Bs): {cabecera['total_bs']:,.2f} Bs", 0, 1, "R")

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        export_dir = os.path.join(base_dir, "reportes_exportados")
        os.makedirs(export_dir, exist_ok=True)

        filename = os.path.join(export_dir, f"ticket_mercancia_{venta_id:06d}.pdf")
        pdf.output(filename)
        os.system(f'start "" "{filename}"' if os.name == 'nt' else f'open "{filename}"')

    # =========================================================================
    # VENTANA DE INVENTARIO Y CATÁLOGO (CON AUDITORÍA DE PRODUCTOS)
    # =========================================================================
    def modal_inventario(self):
        win = ctk.CTkToplevel(self)
        win.title("Inventario de Mercancía")
        centrar_ventana(win, 780, 560)
        win.grab_set()

        usr_act = self.controller.usuario_actual["usuario"]
        rol_act = self.controller.usuario_actual["rol"]

        frame_add = ctk.CTkFrame(win, fg_color="#23201C", corner_radius=12)
        frame_add.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(frame_add, text="➕ Agregar Nuevo Producto al Inventario", font=("Georgia", 13, "bold"), text_color="#D4A343").pack(anchor="w", padx=10, pady=4)

        f_inputs = ctk.CTkFrame(frame_add, fg_color="transparent")
        f_inputs.pack(fill="x", padx=5, pady=5)

        e_nom = ctk.CTkEntry(f_inputs, placeholder_text="Nombre del Producto", width=190, fg_color="#2D2924")
        e_nom.pack(side="left", padx=3)

        # NUEVO CAMPO: Costo de Compra
        e_cost = ctk.CTkEntry(f_inputs, placeholder_text="Costo Compra $", width=105, fg_color="#2D2924")
        e_cost.pack(side="left", padx=3)

        e_pre = ctk.CTkEntry(f_inputs, placeholder_text="Precio Venta $", width=105, fg_color="#2D2924")
        e_pre.pack(side="left", padx=3)

        e_stk = ctk.CTkEntry(f_inputs, placeholder_text="Stock Inicial", width=85, fg_color="#2D2924")
        e_stk.pack(side="left", padx=3)

        e_min = ctk.CTkEntry(f_inputs, placeholder_text="Alerta Mínimo", width=85, fg_color="#2D2924")
        e_min.pack(side="left", padx=3)

        def guardar_nuevo():
            nom = e_nom.get().strip()
            cost = e_cost.get().strip()
            pre = e_pre.get().strip()
            stk = e_stk.get().strip()
            min_stk = e_min.get().strip()

            if not all([nom, cost, pre, stk, min_stk]):
                messagebox.showwarning("Atención", "Complete todos los campos, incluyendo el Costo de Compra.")
                return
            try:
                c_usd = float(cost.replace(",", "."))
                p_usd = float(pre.replace(",", "."))
                s_num = int(stk)
                m_num = int(min_stk)

                if agregar_producto(nom, p_usd, s_num, m_num, c_usd):
                    registrar_auditoria(
                        usr_act, rol_act, "CREAR_PRODUCTO",
                        f"Nuevo producto: '{nom}'. Costo: ${c_usd:.2f}, Venta: ${p_usd:.2f}, Stock: {s_num} un. (Mín: {m_num})."
                    )
                    messagebox.showinfo("Éxito", f"Producto '{nom}' creado con Costo CPP de ${c_usd:.2f}.")
                    e_nom.delete(0, 'end'); e_cost.delete(0, 'end'); e_pre.delete(0, 'end'); e_stk.delete(0, 'end'); e_min.delete(0, 'end')
                    cargar_lista_inventario()
                    self.cargar_combos()
                else:
                    messagebox.showerror("Error", "El producto ya existe en el catálogo.")
            except ValueError:
                messagebox.showerror("Error", "Los costos, precios y cantidades deben ser números válidos.")

        ctk.CTkButton(f_inputs, text="Guardar", fg_color="#D4A343", hover_color="#B8892E", text_color="#191715", font=("Arial", 11, "bold"), width=80, command=guardar_nuevo).pack(side="left", padx=4)

        scroll_inv = ctk.CTkScrollableFrame(win, fg_color="#23201C", label_text="Inventario de Productos Guardados")
        scroll_inv.pack(fill="both", expand=True, padx=15, pady=10)

        def cargar_lista_inventario():
            for w in scroll_inv.winfo_children():
                w.destroy()

            productos = obtener_productos()
            for p in productos:
                es_bajo = p["stock"] <= p["stock_minimo"]
                bg_color = "#78281F" if es_bajo else "#2D2924"
                alerta_txt = " ⚠️ ¡STOCK BAJO!" if es_bajo else ""

                card = ctk.CTkFrame(scroll_inv, fg_color=bg_color)
                card.pack(fill="x", pady=3, padx=5)

                info_txt = f"{p['nombre']} | Precio: ${p['precio_usd']:.2f} | Stock: {p['stock']} un. (Mín: {p['stock_minimo']}){alerta_txt}"
                ctk.CTkLabel(card, text=info_txt, font=("Arial", 11, "bold" if es_bajo else "normal"), text_color="#F4EFE6").pack(side="left", padx=10, pady=6)

                btn_del = ctk.CTkButton(
                    card, text="🗑️ Eliminar", fg_color="#78281F", hover_color="#943126", width=80,
                    command=lambda pid=p["id"], pnom=p["nombre"]: eliminar_prod(pid, pnom)
                )
                btn_del.pack(side="right", padx=5)

                btn_edit = ctk.CTkButton(
                    card, text="✏️ Modificar", fg_color="#3E342B", hover_color="#524539", width=80,
                    command=lambda prod_data=p: abrir_editor(prod_data)
                )
                btn_edit.pack(side="right", padx=5)

        def eliminar_prod(pid, pnom):
            if messagebox.askyesno("Confirmar", f"¿Desea eliminar '{pnom}' del inventario?"):
                if eliminar_producto(pid):
                    # AUDITORÍA DE ELIMINACIÓN DE PRODUCTO
                    registrar_auditoria(usr_act, rol_act, "ELIMINAR_PRODUCTO", f"Producto eliminado del catálogo: '{pnom}' (ID #{pid}).")
                    cargar_lista_inventario()
                    self.cargar_combos()

        def abrir_editor(prod_data):
            """Ventana profesional de reabastecimiento con suma automática y cálculo CPP."""
            edit_win = ctk.CTkToplevel(win)
            edit_win.title(f"Reabastecer / Modificar - {prod_data['nombre']}")
            centrar_ventana(edit_win, 440, 560)
            edit_win.grab_set()

            ctk.CTkLabel(edit_win, text=f"Entrada de Mercancía / Modificación", font=("Georgia", 15, "bold"), text_color="#D4A343").pack(pady=(15, 2))
            ctk.CTkLabel(edit_win, text=f"Artículo: {prod_data['nombre']}", font=("Arial", 11, "bold"), text_color="#F4EFE6").pack(pady=(0, 8))

            f_form = ctk.CTkFrame(edit_win, fg_color="#23201C", corner_radius=10)
            f_form.pack(fill="both", expand=True, padx=15, pady=5)

            # Nombre
            ctk.CTkLabel(f_form, text="Nombre del Producto:", font=("Arial", 10, "bold"), text_color="#A89F91").pack(anchor="w", padx=15, pady=(6, 1))
            ed_nom = ctk.CTkEntry(f_form, fg_color="#2D2924")
            ed_nom.insert(0, prod_data["nombre"])
            ed_nom.pack(fill="x", padx=15, pady=2)

            # Stock Actual (Bloqueado)
            stock_actual = prod_data["stock"]
            costo_actual = prod_data.get("costo_unitario_usd", 0.0)

            f_stock_info = ctk.CTkFrame(f_form, fg_color="#2D2924", corner_radius=6)
            f_stock_info.pack(fill="x", padx=15, pady=6)
            lbl_stock_previo = ctk.CTkLabel(
                f_stock_info, text=f"📦 Stock en Almacén: {stock_actual} un. | Costo CPP Actual: ${costo_actual:.2f}",
                font=("Arial", 10, "bold"), text_color="#7DCEA0"
            )
            lbl_stock_previo.pack(pady=4)

            # Unidades a Sumar (+)
            ctk.CTkLabel(f_form, text="➕ Unidades Nuevas a Ingresar (Sumar al Stock):", font=("Arial", 10, "bold"), text_color="#D4A343").pack(anchor="w", padx=15, pady=(4, 1))
            ed_cant_nueva = ctk.CTkEntry(f_form, placeholder_text="Ej: 5 (Dejar 0 si no ingresa mercancía)", fg_color="#2D2924")
            ed_cant_nueva.insert(0, "0")
            ed_cant_nueva.pack(fill="x", padx=15, pady=2)

            # Costo de Compra de las nuevas unidades
            ctk.CTkLabel(f_form, text="💵 Costo Unitario de Compra de este Lote ($):", font=("Arial", 10, "bold"), text_color="#A89F91").pack(anchor="w", padx=15, pady=(4, 1))
            ed_costo_lote = ctk.CTkEntry(f_form, placeholder_text="Ej: 1.20", fg_color="#2D2924")
            ed_costo_lote.insert(0, f"{costo_actual:.2f}")
            ed_costo_lote.pack(fill="x", padx=15, pady=2)

            # Precio de Venta
            ctk.CTkLabel(f_form, text="🏷️ Precio de Venta al Huésped ($):", font=("Arial", 10, "bold"), text_color="#D4A343").pack(anchor="w", padx=15, pady=(4, 1))
            ed_pre_venta = ctk.CTkEntry(f_form, fg_color="#2D2924")
            ed_pre_venta.insert(0, f"{prod_data['precio_usd']:.2f}")
            ed_pre_venta.pack(fill="x", padx=15, pady=2)

            # Stock Mínimo de Alerta
            ctk.CTkLabel(f_form, text="⚠️ Alerta de Stock Mínimo:", font=("Arial", 10, "bold"), text_color="#A89F91").pack(anchor="w", padx=15, pady=(4, 1))
            ed_min = ctk.CTkEntry(f_form, fg_color="#2D2924")
            ed_min.insert(0, str(prod_data["stock_minimo"]))
            ed_min.pack(fill="x", padx=15, pady=2)

            # Etiqueta de Stock Total Resultante
            lbl_resumen = ctk.CTkLabel(f_form, text=f"Stock Total Resultante: {stock_actual} unidades", font=("Arial", 11, "bold"), text_color="#F4EFE6")
            lbl_resumen.pack(pady=4)

            def recalcular_preview(event=None):
                try:
                    c_add = int(ed_cant_nueva.get().strip() or "0")
                    lbl_resumen.configure(text=f"Stock Total Resultante: {stock_actual + c_add} unidades")
                except ValueError:
                    lbl_resumen.configure(text="Stock Total Resultante: --")

            ed_cant_nueva.bind("<KeyRelease>", recalcular_preview)

            def guardar_cambios():
                try:
                    nom_act = ed_nom.get().strip()
                    c_nuevas = int(ed_cant_nueva.get().strip() or "0")
                    costo_lote = float(ed_costo_lote.get().replace(",", "."))
                    pre_venta = float(ed_pre_venta.get().replace(",", "."))
                    min_stk = int(ed_min.get().strip() or "5")

                    if not nom_act:
                        messagebox.showwarning("Atención", "El nombre es obligatorio.")
                        return

                    # 1. Suma automática de stock
                    stock_final = stock_actual + c_nuevas

                    # 2. Recálculo CPP automático
                    if c_nuevas > 0:
                        costo_total_previo = stock_actual * costo_actual
                        costo_total_nuevo = c_nuevas * costo_lote
                        nuevo_costo_cpp = (costo_total_previo + costo_total_nuevo) / stock_final
                    else:
                        nuevo_costo_cpp = costo_lote

                    if actualizar_producto(prod_data["id"], nom_act, pre_venta, nuevo_costo_cpp, stock_final, min_stk):
                        registrar_auditoria(
                            usr_act, rol_act, "MODIFICAR_PRODUCTO",
                            f"Producto #{prod_data['id']} '{nom_act}' actualizado. Stock anterior: {stock_actual} + {c_nuevas} = {stock_final} un. Nuevo Costo CPP: ${nuevo_costo_cpp:.2f}."
                        )
                        messagebox.showinfo("Éxito", f"Inventario actualizado. Nuevo Stock: {stock_final} un. (Costo CPP: ${nuevo_costo_cpp:.2f})")
                        edit_win.destroy()
                        cargar_lista_inventario()
                        self.cargar_combos()
                except ValueError:
                    messagebox.showerror("Error", "Cantidades, costos y precios deben ser números válidos.")

            ctk.CTkButton(
                edit_win, text="💾 Guardar Cambios y Sumar Stock", fg_color="#D4A343", hover_color="#B8892E",
                text_color="#191715", font=("Arial", 12, "bold"), command=guardar_cambios
            ).pack(pady=12, padx=20, fill="x")

        cargar_lista_inventario()