"""
===============================================================================
SISTEMA DE GESTIÓN DE MOTELES
Módulo: modules/mantenimiento.py (CONTROL DE AVERÍAS, INFRAESTRUCTURA Y DAÑOS)
Diseño: Dark Luxury & Enterprise Grade Maintenance Suite
===============================================================================
"""

import os
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from fpdf import FPDF

# Importaciones desde la Capa de Datos (database/db_manager.py)
from database.db_manager import (
    obtener_habitaciones, enviar_habitacion_mantenimiento,
    finalizar_mantenimiento_habitacion, obtener_ordenes_mantenimiento,
    registrar_cobro_dano, registrar_auditoria, formatear_bs, formatear_usd,
    obtener_tasa_bcv, obtener_ruta_recurso
)


def centrar_ventana(win, ancho: int, alto: int):
    """Centra geométricamente las ventanas modales emergentes."""
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = max(0, (sw - ancho) // 2)
    y = max(0, (sh - alto) // 2)
    win.geometry(f"{ancho}x{alto}+{x}+{y}")


# =============================================================================
# GENERADOR DE REPORTES PDF (AUDITORÍA DE INFRAESTRUCTURA)
# =============================================================================
class PDFReporteMantenimiento(FPDF):
    def __init__(self):
        super().__init__(orientation='L', unit='mm', format='A4')
        self.set_margins(12, 12, 12)
        self.set_auto_page_break(auto=True, margin=14)

    def header(self):
        logo = obtener_ruta_recurso("logo_hotel.png")
        if os.path.exists(logo):
            self.image(logo, x=12, y=8, w=18)

        self.set_font("Helvetica", "B", 13)
        self.cell(0, 5, "INFORME DE MANTENIMIENTO, AVERÍAS Y COSTOS", 0, 1, "C")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 4.5, "AUDITORÍA TÉCNICA Y CONTROL DE ACTIVOS HOTEL & SUITES", 0, 1, "C")
        self.set_y(26)

        # Encabezado de la tabla
        self.set_fill_color(33, 30, 27)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 8)
        self.cell(28, 7, "FECHA", 1, 0, "C", fill=True)
        self.cell(22, 7, "HABITACIÓN", 1, 0, "C", fill=True)
        self.cell(38, 7, "TIPO DE AVERÍA", 1, 0, "L", fill=True)
        self.cell(80, 7, "DESCRIPCIÓN DE LA FALLA", 1, 0, "L", fill=True)
        self.cell(40, 7, "TÉCNICO ENCARGADO", 1, 0, "L", fill=True)
        self.cell(25, 7, "COSTO ($)", 1, 0, "R", fill=True)
        self.cell(36, 7, "COSTO (BS)", 1, 0, "R", fill=True)
        self.cell(20, 7, "ESTADO", 1, 1, "C", fill=True)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 8, f"Auditoría de Activos e Infraestructura  •  Página {self.page_no()}", 0, 0, "C")


class FrameMantenimiento(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#100F0D")
        self.controller = controller

        # =====================================================================
        # CONSTANTES DE DISEÑO - PALETA LUXURY BOUTIQUE
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

        self.ordenes_cache = []

        # =====================================================================
        # 1. HEADER EJECUTIVO SUPERIOR
        # =====================================================================
        self.frame_top = ctk.CTkFrame(
            self, fg_color=self.C_PANEL, corner_radius=14,
            border_width=1, border_color=self.C_BORDER
        )
        self.frame_top.pack(fill="x", padx=16, pady=(16, 8))

        f_titulos = ctk.CTkFrame(self.frame_top, fg_color="transparent")
        f_titulos.pack(side="left", padx=18, pady=12)

        ctk.CTkLabel(
            f_titulos, text="GESTIÓN DE MANTENIMIENTO Y AVERÍAS",
            font=("Montserrat", 14, "bold"), text_color=self.C_GOLD
        ).pack(anchor="w")

        self.lbl_subtitulo = ctk.CTkLabel(
            f_titulos, text="Control técnico de habitaciones, costos y cobro de incidencias a huéspedes",
            font=("Arial", 9), text_color=self.C_TEXT_MUTED
        )
        self.lbl_subtitulo.pack(anchor="w")

        # Botones de Acción Superior
        f_acciones = ctk.CTkFrame(self.frame_top, fg_color="transparent")
        f_acciones.pack(side="right", padx=18, pady=12)

        ctk.CTkButton(
            f_acciones, text="📊 Exportar PDF", fg_color=self.C_CARD, hover_color="#2A2621",
            text_color=self.C_TEXT_MAIN, font=("Arial", 11, "bold"), height=34, corner_radius=8,
            border_width=1, border_color=self.C_BORDER, command=self.exportar_gastos_pdf
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            f_acciones, text="⚡ Cobrar Daño a Huésped", fg_color="#3A1714", hover_color=self.C_RED,
            text_color="#FADBD8", font=("Arial", 11, "bold"), height=34, corner_radius=8,
            border_width=1, border_color="#5C201A", command=self.modal_cobro_dano
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            f_acciones, text="➕ Poner en Mantenimiento", fg_color=self.C_GOLD, hover_color=self.C_GOLD_HOVER,
            text_color="#100F0D", font=("Montserrat", 11, "bold"), height=34, corner_radius=8,
            command=self.modal_nueva_orden
        ).pack(side="left", padx=4)

        # =====================================================================
        # 2. BARRA DE HERRAMIENTAS Y MÉTRICAS RÁPIDAS
        # =====================================================================
        self.frame_tools = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_tools.pack(fill="x", padx=16, pady=(0, 8))

        # Buscador en tiempo real
        self.e_buscar = ctk.CTkEntry(
            self.frame_tools, placeholder_text="🔍 Filtrar por habitación, falla o técnico...",
            width=320, height=34, fg_color=self.C_CARD, border_color=self.C_BORDER,
            text_color=self.C_TEXT_MAIN, font=("Arial", 11)
        )
        self.e_buscar.pack(side="left")
        self.e_buscar.bind("<KeyRelease>", lambda e: self.renderizar_ordenes())

        # Badges métricos
        self.f_badges = ctk.CTkFrame(self.frame_tools, fg_color="transparent")
        self.f_badges.pack(side="right")

        self.b_activas = ctk.CTkLabel(
            self.f_badges, text="Averías Activas: 0", font=("Arial", 10, "bold"),
            text_color="#E74C3C"
        )
        self.b_activas.pack(side="left", padx=8)

        self.b_costo_total = ctk.CTkLabel(
            self.f_badges, text="Gasto Estimado: $0.00", font=("Arial", 10, "bold"),
            text_color=self.C_GOLD
        )
        self.b_costo_total.pack(side="left", padx=8)

        # =====================================================================
        # 3. CONTENEDOR SCROLLABLE DE ÓRDENES
        # =====================================================================
        self.scroll_ordenes = ctk.CTkScrollableFrame(self, fg_color=self.C_BG)
        self.scroll_ordenes.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.cargar_ordenes()

    # =========================================================================
    # LÓGICA DE GESTIÓN Y RENDERIZADO
    # =========================================================================
    def cargar_ordenes(self):
        """Obtiene las órdenes activas y refresca los indicadores."""
        self.ordenes_cache = obtener_ordenes_mantenimiento(solo_activas=True)
        tasa = obtener_tasa_bcv()

        total_costo = sum(o.get("costo_reparacion_usd", 0.0) for o in self.ordenes_cache)
        self.b_activas.configure(text=f"⚠️ {len(self.ordenes_cache)} Habitación(es) en Reparación")
        self.b_costo_total.configure(text=f"Gasto Activo Estimado: ${total_costo:,.2f} ({formatear_bs(total_costo * tasa)})")

        self.renderizar_ordenes()

    def renderizar_ordenes(self):
        for w in self.scroll_ordenes.winfo_children():
            w.destroy()

        filtro = self.e_buscar.get().strip().upper()
        ordenes_filtradas = []

        for o in self.ordenes_cache:
            hab = str(o.get("hab_codigo", "")).upper()
            averia = str(o.get("tipo_averia", "")).upper()
            tec = str(o.get("tecnico_responsable", "")).upper()
            desc = str(o.get("descripcion", "")).upper()

            if filtro and not any(filtro in campo for campo in [hab, averia, tec, desc]):
                continue
            ordenes_filtradas.append(o)

        if not ordenes_filtradas:
            f_empty = ctk.CTkFrame(self.scroll_ordenes, fg_color=self.C_PANEL, corner_radius=12, border_width=1, border_color=self.C_BORDER)
            f_empty.pack(fill="x", pady=30, padx=20)
            ctk.CTkLabel(
                f_empty, text="✨ No hay órdenes de reparación pendientes",
                font=("Montserrat", 13, "bold"), text_color=self.C_GOLD
            ).pack(pady=(20, 2))
            ctk.CTkLabel(
                f_empty, text="Todas las habitaciones están completamente operativas y habilitadas.",
                font=("Arial", 10), text_color=self.C_TEXT_MUTED
            ).pack(pady=(0, 20))
            return

        for ord_item in ordenes_filtradas:
            card = ctk.CTkFrame(
                self.scroll_ordenes, fg_color=self.C_CARD, corner_radius=12,
                border_width=1, border_color=self.C_BORDER
            )
            card.pack(fill="x", pady=4, padx=4)

            # Contenedor Izquierdo: Habitación y Badges
            f_left = ctk.CTkFrame(card, fg_color="transparent", width=160)
            f_left.pack(side="left", padx=16, pady=12)

            ctk.CTkLabel(
                f_left, text=ord_item["hab_codigo"],
                font=("Montserrat", 18, "bold"), text_color=self.C_TEXT_MAIN
            ).pack(anchor="w")

            b_estado = ctk.CTkFrame(f_left, fg_color="#3A1714", corner_radius=6, border_width=1, border_color="#5C201A")
            b_estado.pack(anchor="w", pady=(4, 0))
            ctk.CTkLabel(b_estado, text="● EN PROCESO", font=("Arial", 8, "bold"), text_color="#E74C3C").pack(padx=6, pady=2)

            # Contenedor Central: Detalles y Falla
            f_center = ctk.CTkFrame(card, fg_color="transparent")
            f_center.pack(side="left", fill="both", expand=True, padx=12, pady=12)

            ctk.CTkLabel(
                f_center, text=f"Falla: {ord_item['tipo_averia']}",
                font=("Montserrat", 11, "bold"), text_color=self.C_GOLD
            ).pack(anchor="w")

            ctk.CTkLabel(
                f_center, text=f'"{ord_item["descripcion"]}"',
                font=("Arial", 10, "italic"), text_color=self.C_TEXT_MAIN, wraplength=480, justify="left"
            ).pack(anchor="w", pady=(2, 4))

            txt_meta = f"👤 Técnico: {ord_item['tecnico_responsable']}  •  Reportado: {str(ord_item['fecha_inicio'])[:16]}"
            ctk.CTkLabel(f_center, text=txt_meta, font=("Arial", 9), text_color=self.C_TEXT_MUTED).pack(anchor="w")

            # Contenedor Derecho: Costos y Botón Finalizar
            f_right = ctk.CTkFrame(card, fg_color="transparent")
            f_right.pack(side="right", padx=16, pady=12)

            ctk.CTkLabel(
                f_right, text=f"${ord_item['costo_reparacion_usd']:.2f}",
                font=("Montserrat", 14, "bold"), text_color=self.C_TEXT_MAIN
            ).pack(anchor="e")

            ctk.CTkLabel(
                f_right, text=formatear_bs(ord_item['costo_reparacion_bs']),
                font=("Arial", 9, "bold"), text_color=self.C_GREEN
            ).pack(anchor="e", pady=(0, 6))

            ctk.CTkButton(
                f_right, text="✅ Habilitar (Limpia)", fg_color="#1E5F38", hover_color="#2E7D32",
                text_color="#F4EFE6", font=("Arial", 10, "bold"), height=30, corner_radius=6,
                command=lambda oid=ord_item["id"], hcod=ord_item["hab_codigo"]: self.liberar_habitacion(oid, hcod)
            ).pack(anchor="e")

    def liberar_habitacion(self, orden_id: int, hab_codigo: str):
        usr_act = self.controller.usuario_actual["usuario"]
        rol_act = self.controller.usuario_actual["rol"]

        if messagebox.askyesno("Reactivación de Habitación", f"¿Confirmar que la habitación {hab_codigo} fue completamente reparada?\n\nPasará a estar 'Limpia' (Verde) y lista para check-in."):
            if finalizar_mantenimiento_habitacion(orden_id, hab_codigo):
                registrar_auditoria(
                    usr_act, rol_act, "FIN_MANTENIMIENTO",
                    f"Orden #{orden_id} finalizada. Habitación {hab_codigo} habilitada a estado 'Limpia'."
                )
                messagebox.showinfo("Operación Exitosa", f"Habitación {hab_codigo} dada de alta y operativa.")
                self.cargar_ordenes()
            else:
                messagebox.showerror("Error", "No se pudo actualizar el estado de la habitación.")

    # =========================================================================
    # MODAL 1: NUEVA ORDEN DE REPARACIÓN
    # =========================================================================
    def modal_nueva_orden(self):
        win = ctk.CTkToplevel(self)
        win.title("Nueva Orden de Mantenimiento")
        # 1. Se aumenta la altura de 520 a 620 para que todo respire holgadamente
        centrar_ventana(win, 500, 620)
        win.grab_set()

        tasa = obtener_tasa_bcv()
        habs_disponibles = [h["codigo"] for h in obtener_habitaciones()]

        ctk.CTkLabel(win, text="ORDEN DE REPARACIÓN & AVERÍA", font=("Montserrat", 13, "bold"), text_color=self.C_GOLD).pack(pady=(14, 2))
        ctk.CTkLabel(win, text="La habitación pasará a estado 'Mantenimiento' (Gris) y se bloqueará su venta.", font=("Arial", 9), text_color=self.C_TEXT_MUTED).pack(pady=(0, 6))

        # Botón inferior empaquetado como pie de ventana (side="bottom") para que NUNCA desaparezca
        def guardar():
            h, t, d, tec, c = c_hab.get(), c_tipo.get(), e_desc.get().strip(), e_tec.get().strip(), e_cost.get().strip()
            if not all([h, t, d, tec, c]):
                messagebox.showwarning("Atención", "Complete todos los campos de la orden.")
                return
            try:
                c_flt = float(c.replace(",", "."))
                usr = self.controller.usuario_actual["usuario"]
                rol = self.controller.usuario_actual["rol"]

                if enviar_habitacion_mantenimiento(h, t, d, tec, c_flt, usr):
                    registrar_auditoria(
                        usr, rol, "INICIO_MANTENIMIENTO",
                        f"Habitación {h} a mantenimiento ({t}). Técnico: {tec}. Costo est: ${c_flt:.2f}."
                    )
                    messagebox.showinfo("Éxito", f"Habitación {h} bloqueada y puesta en mantenimiento.")
                    win.destroy()
                    self.cargar_ordenes()
                else:
                    messagebox.showerror("Error", "No se pudo registrar la orden en base de datos.")
            except ValueError:
                messagebox.showerror("Error", "El costo debe ser numérico.")

        btn_confirmar = ctk.CTkButton(
            win, text="Confirmar y Bloquear Habitación", fg_color="#3A1714", hover_color=self.C_RED,
            text_color="#FADBD8", font=("Montserrat", 11, "bold"), height=38, corner_radius=8,
            command=guardar
        )
        btn_confirmar.pack(side="bottom", fill="x", padx=20, pady=(6, 14))

        # Contenedor de Formulario
        f_form = ctk.CTkFrame(win, fg_color=self.C_PANEL, corner_radius=12, border_width=1, border_color=self.C_BORDER)
        f_form.pack(fill="both", expand=True, padx=20, pady=(0, 6))

        ctk.CTkLabel(f_form, text="Habitación:", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", padx=16, pady=(10, 2))
        c_hab = ctk.CTkComboBox(f_form, values=habs_disponibles, height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER, text_color=self.C_TEXT_MAIN)
        c_hab.pack(fill="x", padx=16, pady=2)

        ctk.CTkLabel(f_form, text="Tipo de Avería:", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", padx=16, pady=(5, 2))
        c_tipo = ctk.CTkComboBox(
            f_form,
            values=[
                "Plomería / Baño", "Aire Acondicionado", "Jacuzzi / Bomba",
                "Electricidad / Iluminación", "Cerrajería / Puerta",
                "Televisor / Cable", "Carpintería / Cama", "Pintura / Detalle"
            ],
            height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER, text_color=self.C_TEXT_MAIN
        )
        c_tipo.pack(fill="x", padx=16, pady=2)

        ctk.CTkLabel(f_form, text="Descripción Detallada de la Falla:", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", padx=16, pady=(5, 2))
        e_desc = ctk.CTkEntry(f_form, placeholder_text="Ej: Fuga de agua debajo del lavamanos...", height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        e_desc.pack(fill="x", padx=16, pady=2)

        ctk.CTkLabel(f_form, text="Técnico / Especialista Responsable:", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", padx=16, pady=(5, 2))
        e_tec = ctk.CTkEntry(f_form, placeholder_text="Nombre del técnico", height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        e_tec.pack(fill="x", padx=16, pady=2)

        ctk.CTkLabel(f_form, text="Costo Estimado de Reparación ($ USD):", font=("Arial", 10, "bold"), text_color=self.C_GOLD).pack(anchor="w", padx=16, pady=(5, 2))
        e_cost = ctk.CTkEntry(f_form, placeholder_text="Ej: 35.00", height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        e_cost.pack(fill="x", padx=16, pady=2)

        lbl_bs = ctk.CTkLabel(f_form, text="Costo en Bs: 0,00 Bs", font=("Arial", 9, "bold"), text_color=self.C_GREEN)
        lbl_bs.pack(anchor="w", padx=16, pady=(2, 6))

        def calc_bs(event=None):
            try:
                v = float(e_cost.get().replace(",", "."))
                lbl_bs.configure(text=f"Costo en Bs: {formatear_bs(v * tasa)}")
            except ValueError:
                lbl_bs.configure(text="Costo en Bs: 0,00 Bs")

        e_cost.bind("<KeyRelease>", calc_bs)

        def guardar():
            h, t, d, tec, c = c_hab.get(), c_tipo.get(), e_desc.get().strip(), e_tec.get().strip(), e_cost.get().strip()
            if not all([h, t, d, tec, c]):
                messagebox.showwarning("Atención", "Complete todos los campos de la orden.")
                return
            try:
                c_flt = float(c.replace(",", "."))
                usr = self.controller.usuario_actual["usuario"]
                rol = self.controller.usuario_actual["rol"]

                if enviar_habitacion_mantenimiento(h, t, d, tec, c_flt, usr):
                    registrar_auditoria(
                        usr, rol, "INICIO_MANTENIMIENTO",
                        f"Habitación {h} a mantenimiento ({t}). Técnico: {tec}. Costo est: ${c_flt:.2f}."
                    )
                    messagebox.showinfo("Éxito", f"Habitación {h} bloqueada y puesta en mantenimiento.")
                    win.destroy()
                    self.cargar_ordenes()
                else:
                    messagebox.showerror("Error", "No se pudo registrar la orden en base de datos.")
            except ValueError:
                messagebox.showerror("Error", "El costo debe ser numérico.")

        #ctk.CTkButton(
        #    win, text="Confirmar y Bloquear Habitación", fg_color="#3A1714", hover_color=self.C_RED,
        #    text_color="#FADBD8", font=("Montserrat", 11, "bold"), height=38, corner_radius=8,
        #    command=guardar
        #).pack(fill="x", padx=20, pady=(10, 16))

    # =========================================================================
    # MODAL 2: COBRO DE DAÑOS A HUÉSPED
    # =========================================================================
    def modal_cobro_dano(self):
        win = ctk.CTkToplevel(self)
        win.title("Cobro de Daños a Huésped")
        centrar_ventana(win, 500, 620)
        win.grab_set()

        tasa = obtener_tasa_bcv()

        ctk.CTkLabel(win, text="REGISTRO DE INCIDENCIA Y COBRO DE DAÑO", font=("Montserrat", 13, "bold"), text_color=self.C_GOLD).pack(pady=(16, 2))
        ctk.CTkLabel(win, text=f"Tasa Oficial BCV: {tasa:.2f} Bs / USD  •  Ingreso directo a caja de turno", font=("Arial", 9), text_color=self.C_TEXT_MUTED).pack(pady=(0, 8))

        f_dano = ctk.CTkFrame(win, fg_color=self.C_PANEL, corner_radius=12, border_width=1, border_color=self.C_BORDER)
        f_dano.pack(fill="both", expand=True, padx=20, pady=5)

        # Campos en 2 columnas compactas
        f_r1 = ctk.CTkFrame(f_dano, fg_color="transparent")
        f_r1.pack(fill="x", padx=16, pady=(10, 2))
        
        f_r1_a = ctk.CTkFrame(f_r1, fg_color="transparent")
        f_r1_a.pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkLabel(f_r1_a, text="Habitación:", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w")
        e_hab = ctk.CTkEntry(f_r1_a, placeholder_text="Ej: P-101", height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        e_hab.pack(fill="x")

        f_r1_b = ctk.CTkFrame(f_r1, fg_color="transparent")
        f_r1_b.pack(side="right", fill="x", expand=True, padx=(4, 0))
        ctk.CTkLabel(f_r1_b, text="C.I. Huésped:", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w")
        e_ci_cli = ctk.CTkEntry(f_r1_b, placeholder_text="Sólo números", height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        e_ci_cli.pack(fill="x")

        ctk.CTkLabel(f_dano, text="Nombre Completo del Huésped:", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", padx=16, pady=(4, 2))
        e_cli = ctk.CTkEntry(f_dano, placeholder_text="Nombre y Apellido", height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        e_cli.pack(fill="x", padx=16, pady=2)

        ctk.CTkLabel(f_dano, text="Concepto del Daño / Avería:", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", padx=16, pady=(4, 2))
        c_dano = ctk.CTkComboBox(
            f_dano,
            values=[
                "Sábanas / Lencería Quemada o Rota", "Control de TV Dañado / Extraviado",
                "Toallas Dañadas / Extraviadas", "Vidrio / Espejo Roto",
                "Daño a Jacuzzi / Grifería", "Control de Aire Dañado", "Manchas / Daños en Colchón"
            ],
            height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER, text_color=self.C_TEXT_MAIN
        )
        c_dano.pack(fill="x", padx=16, pady=2)

        ctk.CTkLabel(f_dano, text="Monto a Cobrar ($ USD):", font=("Arial", 10, "bold"), text_color=self.C_GOLD).pack(anchor="w", padx=16, pady=(6, 2))
        e_monto = ctk.CTkEntry(f_dano, placeholder_text="Ej: 25.00", height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        e_monto.pack(fill="x", padx=16, pady=2)

        lbl_bs_calc = ctk.CTkLabel(f_dano, text="Equivalente en Bs: 0,00 Bs", font=("Arial", 10, "bold"), text_color=self.C_GREEN)
        lbl_bs_calc.pack(anchor="w", padx=16, pady=(2, 6))

        def actualizar_monto_bs(event=None):
            try:
                m_val = float(e_monto.get().replace(",", "."))
                lbl_bs_calc.configure(text=f"Equivalente en Bs: {formatear_bs(m_val * tasa)}")
            except ValueError:
                lbl_bs_calc.configure(text="Equivalente en Bs: 0,00 Bs")

        e_monto.bind("<KeyRelease>", actualizar_monto_bs)

        ctk.CTkLabel(f_dano, text="Forma de Cobro:", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", padx=16, pady=(4, 2))
        c_met = ctk.CTkComboBox(
            f_dano, values=["EFECTIVO USD", "EFECTIVO BS", "PAGO MOVIL", "PUNTO DE VENTA"],
            height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER, text_color=self.C_TEXT_MAIN,
            command=lambda v: toggle_p2p_dano(v)
        )
        c_met.pack(fill="x", padx=16, pady=2)

        frame_p2p_d = ctk.CTkFrame(f_dano, fg_color="transparent")
        e_ref_d = ctk.CTkEntry(frame_p2p_d, placeholder_text="Ref (4 dígitos)", height=30, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        e_ref_d.pack(side="left", padx=2, fill="x", expand=True)
        e_ci_p2p = ctk.CTkEntry(frame_p2p_d, placeholder_text="C.I. Emisor", height=30, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        e_ci_p2p.pack(side="left", padx=2, fill="x", expand=True)
        e_tel_d = ctk.CTkEntry(frame_p2p_d, placeholder_text="Teléfono Emisor", height=30, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        e_tel_d.pack(side="left", padx=2, fill="x", expand=True)

        def toggle_p2p_dano(metodo):
            if metodo == "PAGO MOVIL":
                frame_p2p_d.pack(fill="x", padx=16, pady=6)
            else:
                frame_p2p_d.pack_forget()

        def cobrar():
            h, cli, ci, con, m, met = e_hab.get().strip().upper(), e_cli.get().strip(), e_ci_cli.get().strip(), c_dano.get(), e_monto.get().strip(), c_met.get()

            if not all([h, cli, ci, con, m]):
                messagebox.showwarning("Atención", "Complete todos los campos del daño.")
                return

            if not ci.isdigit():
                messagebox.showwarning("Atención", "La Cédula de Identidad debe ser estrictamente numérica.")
                return

            ref, ci_emisor, tel = None, None, None
            if met == "PAGO MOVIL":
                ref, ci_emisor, tel = e_ref_d.get().strip(), e_ci_p2p.get().strip(), e_tel_d.get().strip()
                if not (ref and ci_emisor and tel):
                    messagebox.showerror("Error", "Complete los datos bancarios del Pago Móvil.")
                    return

            try:
                m_flt = float(m.replace(",", "."))
                usr = self.controller.usuario_actual["usuario"]
                rol = self.controller.usuario_actual["rol"]

                if registrar_cobro_dano(h, cli, ci, con, m_flt, met, usr, ref, ci_emisor, tel):
                    p2p_txt = f" [Ref P2P: {ref}]" if met == "PAGO MOVIL" else ""
                    registrar_auditoria(
                        usr, rol, "COBRO_DANO",
                        f"Daño cobrado en Hab {h} a {cli} (C.I: {ci}): '{con}' por ${m_flt:.2f} ({formatear_bs(m_flt * tasa)}) [{met}{p2p_txt}]."
                    )

                    try:
                        from modules.notificaciones import disparar_notificacion_multicanal
                        asunto_d = f"⚡ DAÑO COBRADO EN HAB {h}"
                        msg_d = (
                            f"🏨 <b>ALERTA DE DAÑO EN HABITACIÓN</b>\n"
                            f"🚪 <b>Habitación:</b> {h}\n"
                            f"👤 <b>Huésped:</b> {cli} (C.I: {ci})\n"
                            f"⚠️ <b>Concepto:</b> {con}\n"
                            f"💰 <b>Monto Cobrado:</b> ${m_flt:.2f} ({formatear_bs(m_flt * tasa)}) [{met}{p2p_txt}]\n"
                            f"👮 <b>Recepcionista:</b> {usr}\n"
                        )
                        disparar_notificacion_multicanal(asunto_d, msg_d)
                    except Exception:
                        pass

                    messagebox.showinfo("Éxito", "Cobro de daño registrado e ingresado al corte de caja activo.")
                    win.destroy()
                else:
                    messagebox.showerror("Error", "No se pudo registrar el cobro en la base de datos.")
            except ValueError:
                messagebox.showerror("Error", "El monto ingresado no es válido.")

        ctk.CTkButton(
            win, text="💳 Procesar Cobro e Ingresar a Caja", fg_color=self.C_GOLD,
            hover_color=self.C_GOLD_HOVER, text_color="#100F0D", font=("Montserrat", 11, "bold"),
            height=40, corner_radius=8, command=cobrar
        ).pack(fill="x", padx=20, pady=(8, 16))

    # =========================================================================
    # EXPORTACIÓN DE REPORTE PDF
    # =========================================================================
    def exportar_gastos_pdf(self):
        ordenes = obtener_ordenes_mantenimiento(solo_activas=False)
        if not ordenes:
            messagebox.showwarning("Atención", "No hay registros históricos de averías para generar el reporte.")
            return

        pdf = PDFReporteMantenimiento()
        pdf.add_page()
        pdf.set_font("Helvetica", "", 8)

        tot_usd, tot_bs = 0.0, 0.0
        for o in ordenes:
            pdf.cell(28, 6, str(o["fecha_inicio"])[:16], 1, 0, "C")
            pdf.cell(22, 6, str(o["hab_codigo"]), 1, 0, "C")
            pdf.cell(38, 6, str(o["tipo_averia"])[:20], 1, 0, "L")
            pdf.cell(80, 6, str(o["descripcion"])[:45], 1, 0, "L")
            pdf.cell(40, 6, str(o["tecnico_responsable"])[:22], 1, 0, "L")
            pdf.cell(25, 6, f"${o['costo_reparacion_usd']:.2f}", 1, 0, "R")
            pdf.cell(36, 6, formatear_bs(o["costo_reparacion_bs"]), 1, 0, "R")
            pdf.cell(20, 6, str(o["estado"]), 1, 1, "C")

            tot_usd += o["costo_reparacion_usd"]
            tot_bs += o["costo_reparacion_bs"]

        # Resumen Final Destacado
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_fill_color(240, 235, 225)
        pdf.cell(208, 7, "TOTAL GASTOS DE REPARACIÓN E INFRAESTRUCTURA:", 1, 0, "L", fill=True)
        pdf.cell(25, 7, f"${tot_usd:,.2f}", 1, 0, "R", fill=True)
        pdf.cell(36, 7, formatear_bs(tot_bs), 1, 0, "R", fill=True)
        pdf.cell(20, 7, "", 1, 1, "C", fill=True)

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        export_dir = os.path.join(base_dir, "reportes_exportados")
        os.makedirs(export_dir, exist_ok=True)

        ruta = os.path.join(export_dir, f"reporte_mantenimiento_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        pdf.output(ruta)
        os.system(f'start "" "{ruta}"' if os.name == 'nt' else f'open "{ruta}"')