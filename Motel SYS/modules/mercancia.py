"""
===============================================================================
SISTEMA DE GESTIÓN DE MOTELES
Módulo: modules/mercancia.py (POS MINI-BAR, CONTROL DE INVENTARIO Y AUDITORÍA)
Diseño: Dark Luxury Boutique POS & Enterprise Stock Engine
===============================================================================
"""

import os
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from fpdf import FPDF

# Importaciones desde la Capa de Datos (Modelo SQLite)
from database.db_manager import (
    obtener_estancias_activas, obtener_tasa_bcv, obtener_productos,
    agregar_producto, actualizar_producto, eliminar_producto,
    descontar_stock_producto, registrar_venta_mercancia_carrito,
    registrar_auditoria, formatear_bs, formatear_usd
)


def centrar_ventana(win, ancho: int, alto: int):
    """Centra con precisión milimétrica cualquier ventana modal emergente."""
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = max(0, (sw - ancho) // 2)
    y = max(0, (sh - alto) // 2)
    win.geometry(f"{ancho}x{alto}+{x}+{y}")


class PDFTicketVenta(FPDF):
    """Comprobante formal para auditoría contable y entrega al huésped."""
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A5')
        self.set_margins(12, 10, 12)

    def header(self):
        self.set_font("Helvetica", "B", 13)
        self.cell(0, 6, "COMPROBANTE DE CONSUMO MINI-BAR", 0, 1, "C")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 4, "SISTEMA INTEGRAL DE CONTROL HOTELERO", 0, 1, "C")
        self.ln(4)


class FrameMercancia(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#100F0D")
        self.controller = controller

        # =====================================================================
        # PALETA DARK LUXURY CORPORATIVA
        # =====================================================================
        self.C_BG = "#100F0D"
        self.C_PANEL = "#161513"
        self.C_CARD = "#1E1C19"
        self.C_INPUT = "#26231F"
        self.C_BORDER = "#2E2A25"
        self.C_GOLD = "#D4AF37"
        self.C_GOLD_HOVER = "#B89228"
        self.C_GREEN = "#2ECC71"
        self.C_RED = "#E74C3C"
        self.C_TEXT_MAIN = "#F5EFEB"
        self.C_TEXT_MUTED = "#8E8880"

        # Configuración de Grid Principal (35% Izquierda - 65% Derecha)
        self.grid_columnconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=6)
        self.grid_rowconfigure(0, weight=1)

        self.carrito = []
        self.habitacion_activa = None
        self.productos_db = []
        self.prod_seleccionado_obj = None

        # =====================================================================
        # PANEL IZQUIERDO: SELECCIÓN RÁPIDA Y AÑADIR A ORDEN
        # =====================================================================
        self.frame_left = ctk.CTkFrame(
            self, fg_color=self.C_PANEL, corner_radius=14,
            border_width=1, border_color=self.C_BORDER
        )
        self.frame_left.grid(row=0, column=0, padx=(16, 8), pady=16, sticky="nsew")

        # Header del panel izquierdo
        f_top_izq = ctk.CTkFrame(self.frame_left, fg_color="transparent")
        f_top_izq.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(
            f_top_izq, text="PUNTO DE VENTA (POS)",
            font=("Montserrat", 14, "bold"), text_color=self.C_GOLD
        ).pack(anchor="w")

        ctk.CTkLabel(
            f_top_izq, text="Carga de consumos y mini-bar a habitaciones",
            font=("Arial", 9), text_color=self.C_TEXT_MUTED
        ).pack(anchor="w")

        # Botón de Administración de Catálogo
        ctk.CTkButton(
            self.frame_left, text="📦 Catálogo & Entradas de Stock",
            fg_color=self.C_CARD, hover_color="#2A2621", text_color=self.C_GOLD,
            font=("Arial", 11, "bold"), border_width=1, border_color=self.C_BORDER,
            height=34, corner_radius=8, command=self.modal_inventario
        ).pack(fill="x", padx=16, pady=(0, 12))

        # Selector de Habitación
        f_box_hab = ctk.CTkFrame(self.frame_left, fg_color=self.C_CARD, corner_radius=10, border_width=1, border_color=self.C_BORDER)
        f_box_hab.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(f_box_hab, text="HABITACIÓN DESTINO", font=("Montserrat", 9, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", padx=12, pady=(8, 2))
        self.combo_hab = ctk.CTkComboBox(
            f_box_hab, values=["Cargando..."], height=34,
            fg_color=self.C_INPUT, border_color=self.C_BORDER,
            text_color=self.C_TEXT_MAIN, dropdown_fg_color=self.C_CARD,
            command=self.al_cambiar_habitacion
        )
        self.combo_hab.pack(fill="x", padx=12, pady=(0, 10))

        # Selector Predictivo de Producto
        f_box_prod = ctk.CTkFrame(self.frame_left, fg_color=self.C_CARD, corner_radius=10, border_width=1, border_color=self.C_BORDER)
        f_box_prod.pack(fill="x", padx=16, pady=(8, 4))

        ctk.CTkLabel(f_box_prod, text="SELECCIÓN DE PRODUCTO", font=("Montserrat", 9, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", padx=12, pady=(8, 2))
        
        # Buscador predictivo
        self.entry_busqueda_prod = ctk.CTkEntry(
            f_box_prod, placeholder_text="🔍 Filtrar por nombre...", height=32,
            fg_color=self.C_INPUT, border_color=self.C_BORDER, text_color=self.C_TEXT_MAIN
        )
        self.entry_busqueda_prod.pack(fill="x", padx=12, pady=(0, 6))
        self.entry_busqueda_prod.bind("<KeyRelease>", self.filtrar_combo_productos)

        self.combo_prod = ctk.CTkComboBox(
            f_box_prod, values=["Cargando..."], height=34,
            fg_color=self.C_INPUT, border_color=self.C_BORDER,
            text_color=self.C_TEXT_MAIN, dropdown_fg_color=self.C_CARD,
            command=self.al_seleccionar_producto
        )
        self.combo_prod.pack(fill="x", padx=12, pady=(0, 8))

        # Tarjeta de Datos del Producto (Precio y Stock)
        self.card_info_prod = ctk.CTkFrame(self.frame_left, fg_color=self.C_CARD, corner_radius=10, border_width=1, border_color=self.C_BORDER)
        self.card_info_prod.pack(fill="x", padx=16, pady=6)

        f_row_precios = ctk.CTkFrame(self.card_info_prod, fg_color="transparent")
        f_row_precios.pack(fill="x", padx=12, pady=(8, 2))

        ctk.CTkLabel(f_row_precios, text="Precio Unitario:", font=("Arial", 10), text_color=self.C_TEXT_MUTED).pack(side="left")
        self.lbl_precio_display = ctk.CTkLabel(f_row_precios, text="$0.00", font=("Montserrat", 13, "bold"), text_color=self.C_GOLD)
        self.lbl_precio_display.pack(side="right")

        f_row_stock = ctk.CTkFrame(self.card_info_prod, fg_color="transparent")
        f_row_stock.pack(fill="x", padx=12, pady=(2, 8))

        ctk.CTkLabel(f_row_stock, text="Disponibilidad:", font=("Arial", 10), text_color=self.C_TEXT_MUTED).pack(side="left")
        self.lbl_stock_badge = ctk.CTkLabel(f_row_stock, text="-- un.", font=("Arial", 10, "bold"), text_color=self.C_GREEN)
        self.lbl_stock_badge.pack(side="right")

        # Cantidad con Botones de Incremento Táctil
        f_cant_box = ctk.CTkFrame(self.frame_left, fg_color="transparent")
        f_cant_box.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(f_cant_box, text="Cantidad:", font=("Arial", 11, "bold"), text_color=self.C_TEXT_MAIN).pack(side="left", padx=(0, 8))

        self.e_cant = ctk.CTkEntry(
            f_cant_box, width=70, height=34, fg_color=self.C_INPUT,
            border_color=self.C_BORDER, text_color=self.C_TEXT_MAIN, font=("Arial", 12, "bold")
        )
        self.e_cant.insert(0, "1")
        self.e_cant.pack(side="left")

        # Botones rápidos +1, +2, +5
        for plus in [1, 2, 5]:
            ctk.CTkButton(
                f_cant_box, text=f"+{plus}", width=36, height=32,
                fg_color=self.C_CARD, hover_color="#2D2822", text_color=self.C_TEXT_MAIN,
                font=("Arial", 10, "bold"), border_width=1, border_color=self.C_BORDER,
                command=lambda p=plus: self.sumar_cantidad_rapida(p)
            ).pack(side="left", padx=3)

        # Botón Acción Principal: Agregar
        ctk.CTkButton(
            self.frame_left, text="➕ Agregar a la Cuenta", fg_color=self.C_GOLD,
            hover_color=self.C_GOLD_HOVER, text_color="#100F0D",
            font=("Montserrat", 11, "bold"), height=40, corner_radius=8,
            command=self.agregar_al_carrito
        ).pack(fill="x", padx=16, pady=(12, 16))

        # =====================================================================
        # PANEL DERECHO: CARRITO, AUDITORÍA DE FACTURACIÓN Y COBRO
        # =====================================================================
        self.frame_right = ctk.CTkFrame(
            self, fg_color=self.C_PANEL, corner_radius=14,
            border_width=1, border_color=self.C_BORDER
        )
        self.frame_right.grid(row=0, column=1, padx=(8, 16), pady=16, sticky="nsew")

        # Header Carrito
        f_top_der = ctk.CTkFrame(self.frame_right, fg_color="transparent")
        f_top_der.pack(fill="x", padx=18, pady=(16, 8))

        ctk.CTkLabel(
            f_top_der, text="TICKET DE CONSUMO EN CURSO",
            font=("Montserrat", 14, "bold"), text_color=self.C_GOLD
        ).pack(side="left")

        self.lbl_items_badge = ctk.CTkLabel(
            f_top_der, text="0 Artículos", font=("Arial", 10, "bold"),
            text_color=self.C_TEXT_MUTED
        )
        self.lbl_items_badge.pack(side="right")

        # Lista Scrollable con Encabezados Claros
        f_encabezados = ctk.CTkFrame(self.frame_right, height=26, fg_color=self.C_CARD, corner_radius=6)
        f_encabezados.pack(fill="x", padx=18, pady=(4, 2))
        
        ctk.CTkLabel(f_encabezados, text="PRODUCTO / ARTÍCULO", font=("Arial", 9, "bold"), text_color=self.C_TEXT_MUTED).pack(side="left", padx=12)
        ctk.CTkLabel(f_encabezados, text="SUBTOTAL ($ / BS)", font=("Arial", 9, "bold"), text_color=self.C_TEXT_MUTED).pack(side="right", padx=45)
        ctk.CTkLabel(f_encabezados, text="CANT", font=("Arial", 9, "bold"), text_color=self.C_TEXT_MUTED).pack(side="right", padx=15)

        self.scroll_carrito = ctk.CTkScrollableFrame(self.frame_right, fg_color=self.C_BG)
        self.scroll_carrito.pack(fill="both", expand=True, padx=18, pady=4)

        # Panel de Totales Consolidado
        self.card_totales = ctk.CTkFrame(self.frame_right, fg_color=self.C_CARD, corner_radius=10, border_width=1, border_color=self.C_BORDER)
        self.card_totales.pack(fill="x", padx=18, pady=8)

        f_tot_row = ctk.CTkFrame(self.card_totales, fg_color="transparent")
        f_tot_row.pack(fill="x", padx=16, pady=10)

        f_txts = ctk.CTkFrame(f_tot_row, fg_color="transparent")
        f_txts.pack(side="left")
        ctk.CTkLabel(f_txts, text="TOTAL A PAGAR", font=("Montserrat", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w")
        self.lbl_tot_bs = ctk.CTkLabel(f_txts, text="0,00 Bs", font=("Arial", 11, "bold"), text_color=self.C_GREEN)
        self.lbl_tot_bs.pack(anchor="w")

        self.lbl_tot_usd = ctk.CTkLabel(f_tot_row, text="$0.00", font=("Montserrat", 20, "bold"), text_color=self.C_GOLD)
        self.lbl_tot_usd.pack(side="right")

        # Pasarela de Pago
        f_metodos = ctk.CTkFrame(self.frame_right, fg_color="transparent")
        f_metodos.pack(fill="x", padx=18, pady=(4, 6))

        ctk.CTkLabel(f_metodos, text="Forma de Pago:", font=("Arial", 11, "bold"), text_color=self.C_TEXT_MAIN).pack(side="left", padx=(0, 10))
        self.combo_metodo = ctk.CTkComboBox(
            f_metodos, values=["EFECTIVO USD", "EFECTIVO BS", "PAGO MOVIL", "PUNTO DE VENTA"],
            height=34, width=180, fg_color=self.C_INPUT, border_color=self.C_BORDER,
            text_color=self.C_TEXT_MAIN, dropdown_fg_color=self.C_CARD,
            command=self.toggle_p2p
        )
        self.combo_metodo.pack(side="left")

        # Despliegue Dinámico para Pago Móvil (P2P)
        self.frame_p2p = ctk.CTkFrame(self.frame_right, fg_color=self.C_CARD, corner_radius=8, border_width=1, border_color=self.C_BORDER)
        
        self.e_ref = ctk.CTkEntry(self.frame_p2p, placeholder_text="Últimos 4 dígitos", height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        self.e_ref.pack(side="left", padx=6, pady=8, fill="x", expand=True)
        self.e_ci = ctk.CTkEntry(self.frame_p2p, placeholder_text="C.I. Titular Pago", height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        self.e_ci.pack(side="left", padx=6, pady=8, fill="x", expand=True)
        self.e_tel = ctk.CTkEntry(self.frame_p2p, placeholder_text="Teléfono Emisor", height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        self.e_tel.pack(side="left", padx=6, pady=8, fill="x", expand=True)

        # Botón de Facturación Final
        self.btn_procesar = ctk.CTkButton(
            self.frame_right, text="💳 Facturar Venta e Imprimir Comprobante",
            fg_color="#1E5F38", hover_color="#2E7D32", text_color="#F4EFE6",
            font=("Montserrat", 12, "bold"), height=42, corner_radius=8,
            command=self.procesar_venta_final
        )
        self.btn_procesar.pack(fill="x", padx=18, pady=(6, 16))

        self.cargar_combos()

    # =========================================================================
    # LÓGICA DE CONTROL DEL POS
    # =========================================================================
    def sumar_cantidad_rapida(self, delta: int):
        try:
            val = int(self.e_cant.get().strip() or "0")
            self.e_cant.delete(0, 'end')
            self.e_cant.insert(0, str(max(1, val + delta)))
        except ValueError:
            self.e_cant.delete(0, 'end')
            self.e_cant.insert(0, str(delta))

    def toggle_p2p(self, metodo):
        if metodo == "PAGO MOVIL":
            self.frame_p2p.pack(fill="x", padx=18, pady=(0, 8), before=self.btn_procesar)
        else:
            self.frame_p2p.pack_forget()

    def filtrar_combo_productos(self, event=None):
        query = self.entry_busqueda_prod.get().strip().upper()
        if not query:
            nombres = [p["nombre"] for p in self.productos_db]
        else:
            nombres = [p["nombre"] for p in self.productos_db if query in p["nombre"].upper()]

        if nombres:
            self.combo_prod.configure(values=nombres)
            self.combo_prod.set(nombres[0])
            self.al_seleccionar_producto(nombres[0])
        else:
            self.combo_prod.configure(values=["No coincide ningún producto"])
            self.combo_prod.set("No coincide ningún producto")
            self.lbl_precio_display.configure(text="$0.00")
            self.lbl_stock_badge.configure(text="0 un.", text_color=self.C_RED)

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
            self.combo_prod.configure(values=["Sin Productos en Almacén"])
            self.combo_prod.set("Sin Productos en Almacén")

    def al_cambiar_habitacion(self, nueva_seleccion):
        if self.carrito and self.habitacion_activa and nueva_seleccion != self.habitacion_activa:
            confirmar = messagebox.askyesno(
                "Atención",
                f"Hay {len(self.carrito)} artículo(s) preparados para la habitación '{self.habitacion_activa}'.\n\n"
                f"¿Desea descartar este ticket para iniciar la venta en la habitación '{nueva_seleccion}'?"
            )
            if confirmar:
                self.carrito.clear()
                self.renderizar_carrito()
                self.habitacion_activa = nueva_seleccion
            else:
                self.combo_hab.set(self.habitacion_activa)
        else:
            self.habitacion_activa = nueva_seleccion

    def al_seleccionar_producto(self, seleccion):
        self.prod_seleccionado_obj = next((p for p in self.productos_db if p["nombre"] == seleccion), None)
        if self.prod_seleccionado_obj:
            p = self.prod_seleccionado_obj
            self.lbl_precio_display.configure(text=f"${p['precio_usd']:.2f}")

            stk = p['stock']
            min_stk = p['stock_minimo']
            if stk <= 0:
                self.lbl_stock_badge.configure(text="AGOTADO (0 un.)", text_color=self.C_RED)
            elif stk <= min_stk:
                self.lbl_stock_badge.configure(text=f"BAJO ({stk} un.)", text_color="#E67E22")
            else:
                self.lbl_stock_badge.configure(text=f"{stk} disponibles", text_color=self.C_GREEN)
        else:
            self.lbl_precio_display.configure(text="$0.00")
            self.lbl_stock_badge.configure(text="-- un.", text_color=self.C_TEXT_MUTED)

    def agregar_al_carrito(self):
        if not self.prod_seleccionado_obj:
            messagebox.showwarning("Aviso", "Seleccione un producto válido.")
            return

        p_obj = self.prod_seleccionado_obj
        cant_str = self.e_cant.get().strip()

        if not cant_str.isdigit() or int(cant_str) <= 0:
            messagebox.showwarning("Aviso", "Ingrese una cantidad entera positiva.")
            return

        cant_num = int(cant_str)
        cant_ya_en_carrito = sum(i["cantidad"] for i in self.carrito if i["producto"] == p_obj["nombre"])

        if (cant_ya_en_carrito + cant_num) > p_obj["stock"]:
            messagebox.showerror(
                "Stock Insuficiente",
                f"Existencia insuficiente de '{p_obj['nombre']}'.\n"
                f"Disponibles en inventario: {p_obj['stock']} un.\n"
                f"Actualmente en carrito: {cant_ya_en_carrito} un."
            )
            return

        tasa = obtener_tasa_bcv()
        sub_usd = p_obj["precio_usd"] * cant_num
        sub_bs = sub_usd * tasa

        # Si ya existe en la orden, incrementar la cantidad en lugar de duplicar la fila
        item_existente = next((i for i in self.carrito if i["producto"] == p_obj["nombre"]), None)
        if item_existente:
            item_existente["cantidad"] += cant_num
            item_existente["subtotal_usd"] += sub_usd
            item_existente["subtotal_bs"] += sub_bs
        else:
            self.carrito.append({
                "producto": p_obj["nombre"],
                "cantidad": cant_num,
                "precio_unit_usd": p_obj["precio_usd"],
                "subtotal_usd": sub_usd,
                "subtotal_bs": sub_bs
            })

        self.e_cant.delete(0, 'end')
        self.e_cant.insert(0, "1")
        self.renderizar_carrito()

    def renderizar_carrito(self):
        for w in self.scroll_carrito.winfo_children():
            w.destroy()

        tot_usd, tot_bs = 0.0, 0.0
        total_items_count = sum(i["cantidad"] for i in self.carrito)

        for idx, item in enumerate(self.carrito):
            tot_usd += item["subtotal_usd"]
            tot_bs += item["subtotal_bs"]

            row = ctk.CTkFrame(self.scroll_carrito, fg_color=self.C_CARD, corner_radius=8, height=40)
            row.pack(fill="x", pady=2, padx=2)

            # Nombre
            ctk.CTkLabel(row, text=item['producto'][:24], font=("Arial", 11, "bold"), text_color=self.C_TEXT_MAIN).pack(side="left", padx=10)

            # Botón Eliminar Fila
            btn_del = ctk.CTkButton(
                row, text="✕", width=26, height=26, fg_color="#2A1614", hover_color=self.C_RED,
                text_color="#F1948A", font=("Arial", 10, "bold"), corner_radius=5,
                command=lambda i=idx: self.quitar_item(i)
            )
            btn_del.pack(side="right", padx=6)

            # Subtotales
            txt_precio = f"${item['subtotal_usd']:.2f} ({formatear_bs(item['subtotal_bs'])})"
            ctk.CTkLabel(row, text=txt_precio, font=("Arial", 10, "bold"), text_color=self.C_GOLD).pack(side="right", padx=8)

            # Cantidad Badge
            b_cant = ctk.CTkFrame(row, fg_color=self.C_INPUT, corner_radius=4)
            b_cant.pack(side="right", padx=6)
            ctk.CTkLabel(b_cant, text=f"x{item['cantidad']}", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MAIN).pack(padx=6, pady=1)

        self.lbl_tot_usd.configure(text=f"${tot_usd:,.2f}")
        self.lbl_tot_bs.configure(text=formatear_bs(tot_bs))
        self.lbl_items_badge.configure(text=f"{total_items_count} Artículo(s)")

    def quitar_item(self, index):
        self.carrito.pop(index)
        self.renderizar_carrito()

    # =========================================================================
    # FACTURACIÓN Y TICKET
    # =========================================================================
    def procesar_venta_final(self):
        hab = self.combo_hab.get()
        if hab in ["Sin Habitaciones Ocupadas", "Cargando..."]:
            messagebox.showerror("Error", "Debe existir al menos una habitación activa para cargar el consumo.")
            return

        if not self.carrito:
            messagebox.showwarning("Aviso", "El ticket no contiene ningún artículo.")
            return

        metodo = self.combo_metodo.get()
        ref, ci, tel = None, None, None
        if metodo == "PAGO MOVIL":
            ref = self.e_ref.get().strip()
            ci = self.e_ci.get().strip()
            tel = self.e_tel.get().strip()
            if not (ref and ci and tel):
                messagebox.showerror("Atención", "Complete todos los campos de auditoría del Pago Móvil.")
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
            for item in self.carrito:
                descontar_stock_producto(item["producto"], item["cantidad"])

            resumen_items = ", ".join([f"{it['cantidad']}x {it['producto']}" for it in self.carrito])
            p2p_info = f" [Ref P2P: {ref}]" if metodo == "PAGO MOVIL" else ""
            registrar_auditoria(
                usr_act, rol_act, "VENTA_MINIBAR",
                f"Ticket #{venta_id:06d} (Hab {hab}): {resumen_items}. Total: ${tot_usd:.2f} ({tot_bs:,.2f} Bs) [{metodo}{p2p_info}]."
            )

            self.generar_ticket_pdf(venta_id, cabecera, self.carrito)
            messagebox.showinfo("Operación Exitosa", f"Venta #{venta_id:06d} completada con éxito.")

            self.carrito.clear()
            self.renderizar_carrito()
            self.cargar_combos()

            self.e_ref.delete(0, 'end')
            self.e_ci.delete(0, 'end')
            self.e_tel.delete(0, 'end')
            self.combo_metodo.set("EFECTIVO USD")
            self.toggle_p2p("EFECTIVO USD")
        else:
            messagebox.showerror("Error", "Ocurrió una falla al procesar la venta en la base de datos.")

    def generar_ticket_pdf(self, venta_id, cabecera, items):
        pdf = PDFTicketVenta()
        pdf.add_page()
        tasa = obtener_tasa_bcv()

        # Ficha Resumen
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 5, f"TICKET NRO: #{venta_id:06d}  |  HABITACION: {cabecera['hab_codigo']}", 0, 1)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.cell(0, 4.5, f"Fecha: {cabecera['fecha']}  |  Turno: {cabecera['turno']}  |  Atendido por: {cabecera['recepcionista']}", 0, 1)
        pdf.cell(0, 4.5, f"Metodo de Pago: {cabecera['metodo']}  |  Tasa Oficial BCV: {tasa:.2f} Bs/USD", 0, 1)
        pdf.ln(3)

        # Tabla de Detalles
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(64, 6, "Descripcion del Producto", 1)
        pdf.cell(14, 6, "Cant", 1, 0, "C")
        pdf.cell(24, 6, "P.Unit ($)", 1, 0, "C")
        pdf.cell(24, 6, "Total ($)", 1, 0, "C")
        pdf.ln()

        pdf.set_font("Helvetica", "", 8)
        for item in items:
            pdf.cell(64, 5, item["producto"][:30], 1)
            pdf.cell(14, 5, str(item["cantidad"]), 1, 0, "C")
            pdf.cell(24, 5, f"${item['precio_unit_usd']:.2f}", 1, 0, "C")
            pdf.cell(24, 5, f"${item['subtotal_usd']:.2f}", 1, 0, "C")
            pdf.ln()

        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, f"TOTAL USD: ${cabecera['total_usd']:.2f}", 0, 1, "R")
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 5, f"TOTAL BS: {cabecera['total_bs']:,.2f} Bs", 0, 1, "R")

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        export_dir = os.path.join(base_dir, "reportes_exportados")
        os.makedirs(export_dir, exist_ok=True)

        filename = os.path.join(export_dir, f"ticket_mercancia_{venta_id:06d}.pdf")
        pdf.output(filename)
        os.system(f'start "" "{filename}"' if os.name == 'nt' else f'open "{filename}"')

    # =========================================================================
    # CATÁLOGO DE MERCANCÍA & ENTRADAS DE INVENTARIO
    # =========================================================================
    def modal_inventario(self):
        win = ctk.CTkToplevel(self)
        win.title("Gestión de Inventario y Catálogo")
        centrar_ventana(win, 840, 620)
        win.grab_set()

        usr_act = self.controller.usuario_actual["usuario"]
        rol_act = self.controller.usuario_actual["rol"]

        # Formulario Superior para Crear Producto
        f_nuevo = ctk.CTkFrame(win, fg_color=self.C_PANEL, corner_radius=12, border_width=1, border_color=self.C_BORDER)
        f_nuevo.pack(fill="x", padx=16, pady=(16, 10))

        ctk.CTkLabel(f_nuevo, text="➕ REGISTRAR NUEVO ARTÍCULO EN CATÁLOGO", font=("Montserrat", 11, "bold"), text_color=self.C_GOLD).pack(anchor="w", padx=14, pady=(10, 6))

        f_inputs = ctk.CTkFrame(f_nuevo, fg_color="transparent")
        f_inputs.pack(fill="x", padx=10, pady=(0, 12))

        e_nom = ctk.CTkEntry(f_inputs, placeholder_text="Nombre del Producto", width=220, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        e_nom.pack(side="left", padx=4)

        e_cost = ctk.CTkEntry(f_inputs, placeholder_text="Costo ($)", width=90, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        e_cost.pack(side="left", padx=4)

        e_pre = ctk.CTkEntry(f_inputs, placeholder_text="P. Venta ($)", width=90, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        e_pre.pack(side="left", padx=4)

        e_stk = ctk.CTkEntry(f_inputs, placeholder_text="Stock", width=75, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        e_stk.pack(side="left", padx=4)

        e_min = ctk.CTkEntry(f_inputs, placeholder_text="Mínimo", width=75, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        e_min.pack(side="left", padx=4)

        def guardar_nuevo():
            nom, cost, pre, stk, min_stk = e_nom.get().strip(), e_cost.get().strip(), e_pre.get().strip(), e_stk.get().strip(), e_min.get().strip()
            if not all([nom, cost, pre, stk, min_stk]):
                messagebox.showwarning("Atención", "Complete todos los campos.")
                return
            try:
                c_usd = float(cost.replace(",", "."))
                p_usd = float(pre.replace(",", "."))
                s_num, m_num = int(stk), int(min_stk)

                if agregar_producto(nom, p_usd, s_num, m_num, c_usd):
                    registrar_auditoria(
                        usr_act, rol_act, "CREAR_PRODUCTO",
                        f"Producto creado: '{nom}'. Costo: ${c_usd:.2f}, Venta: ${p_usd:.2f}, Stock: {s_num} un."
                    )
                    messagebox.showinfo("Éxito", f"Producto '{nom}' registrado con éxito.")
                    for e in [e_nom, e_cost, e_pre, e_stk, e_min]: e.delete(0, 'end')
                    cargar_lista()
                    self.cargar_combos()
                else:
                    messagebox.showerror("Error", "El producto ya existe en la base de datos.")
            except ValueError:
                messagebox.showerror("Error", "Verifique que los precios, costos y stock sean numéricos.")

        ctk.CTkButton(
            f_inputs, text="Guardar", fg_color=self.C_GOLD, hover_color=self.C_GOLD_HOVER,
            text_color="#100F0D", font=("Arial", 11, "bold"), width=85, command=guardar_nuevo
        ).pack(side="left", padx=4)

        # Buscador en Inventario
        f_search_bar = ctk.CTkFrame(win, fg_color="transparent")
        f_search_bar.pack(fill="x", padx=16, pady=(0, 4))

        e_filtro_inv = ctk.CTkEntry(f_search_bar, placeholder_text="🔍 Buscar en inventario por nombre...", fg_color=self.C_PANEL, border_color=self.C_BORDER)
        e_filtro_inv.pack(fill="x")

        # Lista de Inventario Scrollable
        scroll_inv = ctk.CTkScrollableFrame(win, fg_color=self.C_BG)
        scroll_inv.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        def cargar_lista():
            for w in scroll_inv.winfo_children(): w.destroy()
            query = e_filtro_inv.get().strip().upper()
            prods = obtener_productos()

            for p in prods:
                if query and query not in p["nombre"].upper():
                    continue

                es_bajo = p["stock"] <= p["stock_minimo"]
                bg_col = "#2B1614" if es_bajo else self.C_CARD
                border_col = self.C_RED if es_bajo else self.C_BORDER

                card = ctk.CTkFrame(scroll_inv, fg_color=bg_col, corner_radius=8, border_width=1, border_color=border_col)
                card.pack(fill="x", pady=3, padx=4)

                f_inf = ctk.CTkFrame(card, fg_color="transparent")
                f_inf.pack(side="left", padx=12, pady=8)

                ctk.CTkLabel(f_inf, text=p['nombre'], font=("Montserrat", 11, "bold"), text_color=self.C_TEXT_MAIN).pack(anchor="w")
                
                txt_detalle = f"Venta: ${p['precio_usd']:.2f}  |  Costo CPP: ${p.get('costo_unitario_usd', 0):.2f}  |  Stock: {p['stock']} un. (Alerta: {p['stock_minimo']})"
                if es_bajo:
                    txt_detalle += "  •  ⚠️ STOCK CRÍTICO"
                ctk.CTkLabel(f_inf, text=txt_detalle, font=("Arial", 9), text_color="#E74C3C" if es_bajo else self.C_TEXT_MUTED).pack(anchor="w")

                ctk.CTkButton(
                    card, text="🗑️", width=34, height=30, fg_color="#3A1714", hover_color=self.C_RED,
                    text_color="#F5B7B1", font=("Arial", 11),
                    command=lambda pid=p["id"], pnom=p["nombre"]: eliminar_p(pid, pnom)
                ).pack(side="right", padx=6)

                ctk.CTkButton(
                    card, text="✏️ Entrada / Editar", width=120, height=30, fg_color=self.C_INPUT,
                    hover_color="#38332C", text_color=self.C_GOLD, font=("Arial", 10, "bold"),
                    border_width=1, border_color=self.C_BORDER,
                    command=lambda pdata=p: abrir_editor(pdata)
                ).pack(side="right", padx=6)

        def eliminar_p(pid, pnom):
            if messagebox.askyesno("Confirmación", f"¿Desea eliminar '{pnom}' del catálogo?"):
                if eliminar_producto(pid):
                    registrar_auditoria(usr_act, rol_act, "ELIMINAR_PRODUCTO", f"Producto '{pnom}' (ID #{pid}) eliminado.")
                    cargar_lista()
                    self.cargar_combos()

        def abrir_editor(prod_data):
            edit_win = ctk.CTkToplevel(win)
            edit_win.title(f"Reabastecer - {prod_data['nombre']}")
            centrar_ventana(edit_win, 460, 580)
            edit_win.grab_set()

            ctk.CTkLabel(edit_win, text="ENTRADA DE MERCANCÍA & CPP", font=("Montserrat", 13, "bold"), text_color=self.C_GOLD).pack(pady=(16, 2))
            ctk.CTkLabel(edit_win, text=f"Artículo: {prod_data['nombre']}", font=("Arial", 10), text_color=self.C_TEXT_MUTED).pack(pady=(0, 10))

            f_form = ctk.CTkFrame(edit_win, fg_color=self.C_PANEL, corner_radius=10, border_width=1, border_color=self.C_BORDER)
            f_form.pack(fill="both", expand=True, padx=20, pady=5)

            ctk.CTkLabel(f_form, text="Nombre:", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", padx=16, pady=(10, 2))
            ed_nom = ctk.CTkEntry(f_form, fg_color=self.C_INPUT, border_color=self.C_BORDER); ed_nom.insert(0, prod_data["nombre"]); ed_nom.pack(fill="x", padx=16)

            stock_act = prod_data["stock"]
            costo_act = prod_data.get("costo_unitario_usd", 0.0)

            # Badge informativo
            f_res = ctk.CTkFrame(f_form, fg_color=self.C_CARD, corner_radius=6)
            f_res.pack(fill="x", padx=16, pady=8)
            ctk.CTkLabel(f_res, text=f"Stock Actual: {stock_act} un.  |  Costo CPP: ${costo_act:.2f}", font=("Arial", 10, "bold"), text_color=self.C_GOLD).pack(pady=4)

            ctk.CTkLabel(f_form, text="➕ Unidades que ingresan al depósito:", font=("Arial", 10, "bold"), text_color=self.C_GREEN).pack(anchor="w", padx=16, pady=(4, 2))
            ed_add = ctk.CTkEntry(f_form, fg_color=self.C_INPUT, border_color=self.C_BORDER); ed_add.insert(0, "0"); ed_add.pack(fill="x", padx=16)

            ctk.CTkLabel(f_form, text="Costo Unitario de compra nuevo lote ($):", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", padx=16, pady=(6, 2))
            ed_cost_lote = ctk.CTkEntry(f_form, fg_color=self.C_INPUT, border_color=self.C_BORDER); ed_cost_lote.insert(0, f"{costo_act:.2f}"); ed_cost_lote.pack(fill="x", padx=16)

            ctk.CTkLabel(f_form, text="Precio de Venta al Huésped ($):", font=("Arial", 10, "bold"), text_color=self.C_GOLD).pack(anchor="w", padx=16, pady=(6, 2))
            ed_pre = ctk.CTkEntry(f_form, fg_color=self.C_INPUT, border_color=self.C_BORDER); ed_pre.insert(0, f"{prod_data['precio_usd']:.2f}"); ed_pre.pack(fill="x", padx=16)

            ctk.CTkLabel(f_form, text="Stock Mínimo de Alerta:", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", padx=16, pady=(6, 2))
            ed_min_s = ctk.CTkEntry(f_form, fg_color=self.C_INPUT, border_color=self.C_BORDER); ed_min_s.insert(0, str(prod_data["stock_minimo"])); ed_min_s.pack(fill="x", padx=16)

            def guardar_cambios():
                try:
                    nom = ed_nom.get().strip()
                    c_nuevas = int(ed_add.get().strip() or "0")
                    costo_lote = float(ed_cost_lote.get().replace(",", "."))
                    pre_venta = float(ed_pre.get().replace(",", "."))
                    min_stk = int(ed_min_s.get().strip() or "5")

                    if not nom: return
                    stock_final = stock_act + c_nuevas

                    if c_nuevas > 0:
                        cpp_nuevo = ((stock_act * costo_act) + (c_nuevas * costo_lote)) / stock_final
                    else:
                        cpp_nuevo = costo_lote

                    if actualizar_producto(prod_data["id"], nom, pre_venta, cpp_nuevo, stock_final, min_stk):
                        registrar_auditoria(
                            usr_act, rol_act, "MODIFICAR_PRODUCTO",
                            f"Producto #{prod_data['id']} '{nom}' actualizado. Stock: {stock_act} + {c_nuevas} = {stock_final} un. CPP: ${cpp_nuevo:.2f}."
                        )
                        messagebox.showinfo("Éxito", f"Inventario actualizado. Stock total: {stock_final} un.")
                        edit_win.destroy()
                        cargar_lista()
                        self.cargar_combos()
                except ValueError:
                    messagebox.showerror("Error", "Datos numéricos no válidos.")

            ctk.CTkButton(
                edit_win, text="💾 Registrar Entrada y Guardar", fg_color=self.C_GOLD,
                hover_color=self.C_GOLD_HOVER, text_color="#100F0D", font=("Arial", 11, "bold"),
                height=38, command=guardar_cambios
            ).pack(fill="x", padx=20, pady=14)

        e_filtro_inv.bind("<KeyRelease>", lambda e: cargar_lista())
        cargar_lista()