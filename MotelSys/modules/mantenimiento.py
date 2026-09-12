"""
===============================================================================
SISTEMA DE GESTIÓN DE MOTELES - MOTEL PRO v2.0
Módulo: modules/mantenimiento.py (CONTROL DE AVERÍAS, INFRAESTRUCTURA Y DAÑOS)
Diseño: Dark Luxury Boutique & Enterprise Auditing Suite
===============================================================================
"""

import os
import customtkinter as ctk
from tkinter import messagebox
from tkcalendar import DateEntry
from datetime import datetime
from fpdf import FPDF

# Importaciones desde la Capa de Datos (database/db_manager.py)
from database.db_manager import (
    obtener_habitaciones, enviar_habitacion_mantenimiento,
    finalizar_mantenimiento_habitacion, obtener_ordenes_mantenimiento,
    registrar_cobro_dano, registrar_auditoria, formatear_bs, formatear_usd,
    obtener_tasa_bcv, obtener_ruta_recurso
)


def _sanitizar_fpdf(texto: str) -> str:
    """Sanea caracteres fuera de latin-1 para evitar errores de encoding en FPDF."""
    if not texto:
        return ""
    reemplazos = {
        "\u2022": "-", "\u2013": "-", "\u2014": "-",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2794": "->", "\u2192": "->", "…": "..."
    }
    for orig, dest in reemplazos.items():
        texto = texto.replace(orig, dest)
    return texto.encode("latin-1", errors="ignore").decode("latin-1")


def centrar_ventana(win, ancho: int, alto: int):
    """Centra geométricamente las ventanas modales emergentes asegurando visibilidad."""
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    ancho_final = min(ancho, sw - 40)
    alto_final = min(alto, sh - 60)
    x = max(0, (sw - ancho_final) // 2)
    y = max(0, (sh - alto_final) // 2)
    win.geometry(f"{ancho_final}x{alto_final}+{x}+{y}")


# =============================================================================
# GENERADOR DEL REPORTE PDF CONTABLE OFICIAL
# =============================================================================
class PDFReporteMantenimiento(FPDF):
    def __init__(self, f_inicio: str = "", f_fin: str = ""):
        super().__init__(orientation='L', unit='mm', format='A4')
        self.set_margins(10, 10, 10)
        self.set_auto_page_break(auto=True, margin=14)
        self.f_inicio = f_inicio
        self.f_fin = f_fin

    def header(self):
        logo = obtener_ruta_recurso("logo_hotel.png")
        if os.path.exists(logo):
            self.image(logo, x=10, y=5, w=15)

        self.set_font("Helvetica", "B", 12)
        self.cell(0, 5, _sanitizar_fpdf("INVERSIONES SAIBABA C.A. - MOTEL EL EDEN"), 0, 1, "C")
        self.set_font("Helvetica", "B", 9)
        self.cell(0, 4.5, _sanitizar_fpdf("RIF: J-30250227-6 | ESTADO CONTABLE DE REPARACIONES, MANTENIMIENTO Y OBRAS"), 0, 1, "C")
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 4, _sanitizar_fpdf(f"Período Auditado: Desde {self.f_inicio} hasta {self.f_fin}  •  Moneda de Expresión: Dual ($ USD / Bs Oficial)"), 0, 1, "C")
        self.set_y(26)

        # Encabezado de la tabla
        self.set_fill_color(33, 30, 27)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 7.5)
        self.cell(24, 7, "FECHA", 1, 0, "C", fill=True)
        self.cell(16, 7, "HAB", 1, 0, "C", fill=True)
        self.cell(38, 7, "TIPO AVERÍA", 1, 0, "L", fill=True)
        self.cell(75, 7, "DESCRIPCIÓN DE LA INCIDENCIA", 1, 0, "L", fill=True)
        self.cell(36, 7, "RESPONSABLE", 1, 0, "L", fill=True)
        self.cell(20, 7, "TASA REG", 1, 0, "C", fill=True)
        self.cell(22, 7, "COSTO ($)", 1, 0, "R", fill=True)
        self.cell(28, 7, "COSTO (BS)", 1, 0, "R", fill=True)
        self.cell(18, 7, "ESTADO", 1, 1, "C", fill=True)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(130, 130, 130)
        self.cell(0, 8, _sanitizar_fpdf(f"Informe Contable de Infraestructura y Mantenimiento - Página {self.page_no()}"), 0, 0, "C")


class FrameMantenimiento(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#100F0D")
        self.controller = controller

        # Paleta Luxury
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

        self.ordenes_raw = []

        # =====================================================================
        # 1. HEADER SUPERIOR CON FILTRO DE FECHAS
        # =====================================================================
        self.frame_top = ctk.CTkFrame(
            self, fg_color=self.C_PANEL, corner_radius=14,
            border_width=1, border_color=self.C_BORDER
        )
        self.frame_top.pack(fill="x", padx=16, pady=(16, 8))

        f_titulos = ctk.CTkFrame(self.frame_top, fg_color="transparent")
        f_titulos.pack(side="left", padx=18, pady=12)

        ctk.CTkLabel(
            f_titulos, text="GESTIÓN DE MANTENIMIENTO Y OBRAS",
            font=("Montserrat", 14, "bold"), text_color=self.C_GOLD
        ).pack(anchor="w")

        self.lbl_subtitulo = ctk.CTkLabel(
            f_titulos, text="Control técnico de habitaciones, costos y cobro de incidencias a huéspedes",
            font=("Arial", 9), text_color=self.C_TEXT_MUTED
        )
        self.lbl_subtitulo.pack(anchor="w")

        # Controles y Filtros a la Derecha
        f_derecha = ctk.CTkFrame(self.frame_top, fg_color="transparent")
        f_derecha.pack(side="right", padx=18, pady=12)

        # Filtros de Fecha para el Reporte y Auditoría
        ctk.CTkLabel(f_derecha, text="Desde:", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(side="left", padx=4)
        self.cal_ini = DateEntry(
            f_derecha, date_pattern='yyyy-mm-dd',
            background="#211E1B", foreground="white", headersbackground="#D4AF37"
        )
        self.cal_ini.set_date(datetime.now().date().replace(day=1))
        self.cal_ini.pack(side="left", padx=4)

        ctk.CTkLabel(f_derecha, text="Hasta:", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(side="left", padx=4)
        self.cal_fin = DateEntry(
            f_derecha, date_pattern='yyyy-mm-dd',
            background="#211E1B", foreground="white", headersbackground="#D4AF37"
        )
        self.cal_fin.pack(side="left", padx=4)

        ctk.CTkButton(
            f_derecha, text="📄 Exportar PDF", fg_color=self.C_CARD, hover_color="#2A2621",
            text_color=self.C_GOLD, font=("Arial", 11, "bold"), height=34, corner_radius=8,
            border_width=1, border_color=self.C_BORDER, command=self.exportar_gastos_pdf
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            f_derecha, text="⚡ Cobrar Daño", fg_color="#3A1714", hover_color=self.C_RED,
            text_color="#FADBD8", font=("Arial", 11, "bold"), height=34, corner_radius=8,
            border_width=1, border_color="#5C201A", command=self.modal_cobro_dano
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            f_derecha, text="➕ Nueva Avería", fg_color=self.C_GOLD, hover_color=self.C_GOLD_HOVER,
            text_color="#100F0D", font=("Montserrat", 11, "bold"), height=34, corner_radius=8,
            command=self.modal_nueva_orden
        ).pack(side="left", padx=4)

        # =====================================================================
        # 2. BARRA DE HERRAMIENTAS Y MÉTRICAS
        # =====================================================================
        self.frame_tools = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_tools.pack(fill="x", padx=16, pady=(0, 8))

        self.e_buscar = ctk.CTkEntry(
            self.frame_tools, placeholder_text="🔍 Filtrar por habitación, avería o técnico...",
            width=320, height=34, fg_color=self.C_CARD, border_color=self.C_BORDER,
            text_color=self.C_TEXT_MAIN, font=("Arial", 11)
        )
        self.e_buscar.pack(side="left")
        self.e_buscar.bind("<KeyRelease>", lambda e: self.renderizar_ordenes())

        self.f_badges = ctk.CTkFrame(self.frame_tools, fg_color="transparent")
        self.f_badges.pack(side="right")

        self.b_activas = ctk.CTkLabel(self.f_badges, text="Averías Activas: 0", font=("Arial", 10, "bold"), text_color="#E74C3C")
        self.b_activas.pack(side="left", padx=8)

        self.b_costo_total = ctk.CTkLabel(self.f_badges, text="Gasto Estimado: $0.00", font=("Arial", 10, "bold"), text_color=self.C_GOLD)
        self.b_costo_total.pack(side="left", padx=8)

        # =====================================================================
        # 3. CONTENEDOR SCROLLABLE
        # =====================================================================
        self.scroll_ordenes = ctk.CTkScrollableFrame(self, fg_color=self.C_BG)
        self.scroll_ordenes.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.cargar_ordenes()

    def cargar_ordenes(self):
        self.ordenes_raw = obtener_ordenes_mantenimiento(solo_activas=False)
        activas = [o for o in self.ordenes_raw if o.get("estado") == "EN_PROCESO"]
        tasa = obtener_tasa_bcv()

        total_costo = sum(o.get("costo_reparacion_usd", 0.0) for o in activas)
        self.b_activas.configure(text=f"⚠️ {len(activas)} Avería(s) en Proceso")
        self.b_costo_total.configure(text=f"Provisión Activa: ${total_costo:,.2f} ({formatear_bs(total_costo * tasa)})")

        self.renderizar_ordenes()

    def renderizar_ordenes(self):
        for w in self.scroll_ordenes.winfo_children():
            w.destroy()

        filtro = self.e_buscar.get().strip().upper()
        # En pantalla mostramos las que están EN_PROCESO o que coincidan con la búsqueda
        filtradas = []
        for o in self.ordenes_raw:
            hab = str(o.get("hab_codigo", "")).upper()
            averia = str(o.get("tipo_averia", "")).upper()
            tec = str(o.get("tecnico_responsable", "")).upper()
            desc = str(o.get("descripcion", "")).upper()
            estado = str(o.get("estado", "")).upper()

            if filtro:
                if any(filtro in campo for campo in [hab, averia, tec, desc, estado]):
                    filtradas.append(o)
            elif estado == "EN_PROCESO":
                filtradas.append(o)

        if not filtradas:
            f_empty = ctk.CTkFrame(self.scroll_ordenes, fg_color=self.C_PANEL, corner_radius=12, border_width=1, border_color=self.C_BORDER)
            f_empty.pack(fill="x", pady=30, padx=20)
            ctk.CTkLabel(f_empty, text="✨ No hay reparaciones pendientes en curso", font=("Montserrat", 13, "bold"), text_color=self.C_GOLD).pack(pady=(20, 2))
            ctk.CTkLabel(f_empty, text="Todas las habitaciones están habilitadas o no hay registros para el filtro ingresado.", font=("Arial", 10), text_color=self.C_TEXT_MUTED).pack(pady=(0, 20))
            return

        for ord_item in filtradas:
            es_proceso = ord_item.get("estado") == "EN_PROCESO"
            card = ctk.CTkFrame(
                self.scroll_ordenes, fg_color=self.C_CARD, corner_radius=12,
                border_width=1, border_color=self.C_BORDER
            )
            card.pack(fill="x", pady=4, padx=4)

            # Contenedor Izquierdo
            f_left = ctk.CTkFrame(card, fg_color="transparent", width=140)
            f_left.pack(side="left", padx=16, pady=12)

            ctk.CTkLabel(f_left, text=ord_item["hab_codigo"], font=("Montserrat", 17, "bold"), text_color=self.C_TEXT_MAIN).pack(anchor="w")

            b_estado = ctk.CTkFrame(
                f_left, fg_color="#3A1714" if es_proceso else "#14251B",
                corner_radius=6, border_width=1, border_color="#5C201A" if es_proceso else "#1F4E34"
            )
            b_estado.pack(anchor="w", pady=(4, 0))
            txt_badge = "● EN PROCESO" if es_proceso else "✓ FINALIZADA"
            col_badge = "#E74C3C" if es_proceso else "#2ECC71"
            ctk.CTkLabel(b_estado, text=txt_badge, font=("Arial", 8, "bold"), text_color=col_badge).pack(padx=6, pady=2)

            # Contenedor Central
            f_center = ctk.CTkFrame(card, fg_color="transparent")
            f_center.pack(side="left", fill="both", expand=True, padx=12, pady=12)

            ctk.CTkLabel(f_center, text=f"Falla: {ord_item['tipo_averia']}", font=("Montserrat", 11, "bold"), text_color=self.C_GOLD).pack(anchor="w")
            ctk.CTkLabel(f_center, text=f'"{ord_item["descripcion"]}"', font=("Arial", 10, "italic"), text_color=self.C_TEXT_MAIN, wraplength=480, justify="left").pack(anchor="w", pady=(2, 4))
            txt_meta = f"👤 Técnico: {ord_item['tecnico_responsable']}  •  Fecha: {str(ord_item['fecha_inicio'])[:16]}"
            ctk.CTkLabel(f_center, text=txt_meta, font=("Arial", 9), text_color=self.C_TEXT_MUTED).pack(anchor="w")

            # Contenedor Derecho
            f_right = ctk.CTkFrame(card, fg_color="transparent")
            f_right.pack(side="right", padx=16, pady=12)

            ctk.CTkLabel(f_right, text=f"${ord_item['costo_reparacion_usd']:.2f}", font=("Montserrat", 14, "bold"), text_color=self.C_TEXT_MAIN).pack(anchor="e")
            ctk.CTkLabel(f_right, text=formatear_bs(ord_item['costo_reparacion_bs']), font=("Arial", 9, "bold"), text_color=self.C_GREEN).pack(anchor="e", pady=(0, 6))

            if es_proceso:
                ctk.CTkButton(
                    f_right, text="✅ Habilitar (Limpia)", fg_color="#1E5F38", hover_color="#2E7D32",
                    text_color="#F4EFE6", font=("Arial", 10, "bold"), height=30, corner_radius=6,
                    command=lambda oid=ord_item["id"], hcod=ord_item["hab_codigo"]: self.liberar_habitacion(oid, hcod)
                ).pack(anchor="e")

    def liberar_habitacion(self, orden_id: int, hab_codigo: str):
        usr_act = self.controller.usuario_actual["usuario"]
        rol_act = self.controller.usuario_actual["rol"]

        if messagebox.askyesno("Reactivación de Habitación", f"¿Confirmar que la habitación {hab_codigo} fue reparada?\n\nPasará a estar 'Limpia' (Verde) y disponible."):
            if finalizar_mantenimiento_habitacion(orden_id, hab_codigo):
                registrar_auditoria(
                    usr_act, rol_act, "FIN_MANTENIMIENTO",
                    f"Orden #{orden_id} finalizada. Habitación {hab_codigo} habilitada a 'Limpia'."
                )
                messagebox.showinfo("Operación Exitosa", f"Habitación {hab_codigo} operativa.")
                self.cargar_ordenes()
            else:
                messagebox.showerror("Error", "No se pudo actualizar el estado de la habitación.")

    # =========================================================================
    # MODAL 1: NUEVA ORDEN (RESPONSIVO Y CON SCROLL INTEGRADO)
    # =========================================================================
    def modal_nueva_orden(self):
        win = ctk.CTkToplevel(self)
        win.title("Nueva Orden de Mantenimiento")
        centrar_ventana(win, 520, 600)
        win.minsize(450, 480)
        win.grab_set()

        tasa = obtener_tasa_bcv()
        habs_disponibles = [h["codigo"] for h in obtener_habitaciones()]

        # Encabezado
        f_top_m = ctk.CTkFrame(win, fg_color="transparent")
        f_top_m.pack(fill="x", padx=20, pady=(16, 6))
        ctk.CTkLabel(f_top_m, text="ORDEN DE REPARACIÓN & AVERÍA", font=("Montserrat", 13, "bold"), text_color=self.C_GOLD).pack(anchor="w")
        ctk.CTkLabel(f_top_m, text="La habitación pasará a 'Mantenimiento' (Gris) y se bloqueará su venta.", font=("Arial", 9), text_color=self.C_TEXT_MUTED).pack(anchor="w")

        # Contenedor central con scroll para adaptarse a cualquier resolución
        f_scroll = ctk.CTkScrollableFrame(win, fg_color=self.C_PANEL, corner_radius=12, border_width=1, border_color=self.C_BORDER)
        f_scroll.pack(fill="both", expand=True, padx=20, pady=6)

        ctk.CTkLabel(f_scroll, text="Habitación:", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", padx=16, pady=(8, 2))
        c_hab = ctk.CTkComboBox(f_scroll, values=habs_disponibles, height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER, text_color=self.C_TEXT_MAIN)
        c_hab.pack(fill="x", padx=16, pady=2)

        ctk.CTkLabel(f_scroll, text="Tipo de Avería:", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", padx=16, pady=(6, 2))
        c_tipo = ctk.CTkComboBox(
            f_scroll,
            values=[
                "Plomería / Baño", "Aire Acondicionado", "Jacuzzi / Bomba",
                "Electricidad / Iluminación", "Cerrajería / Puerta",
                "Televisor / Cable", "Carpintería / Cama", "Pintura / Detalle"
            ],
            height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER, text_color=self.C_TEXT_MAIN
        )
        c_tipo.pack(fill="x", padx=16, pady=2)

        ctk.CTkLabel(f_scroll, text="Descripción de la Falla:", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", padx=16, pady=(6, 2))
        e_desc = ctk.CTkEntry(f_scroll, placeholder_text="Ej: Fuga de agua debajo del lavamanos...", height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        e_desc.pack(fill="x", padx=16, pady=2)

        ctk.CTkLabel(f_scroll, text="Técnico / Responsable:", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", padx=16, pady=(6, 2))
        e_tec = ctk.CTkEntry(f_scroll, placeholder_text="Nombre del técnico o cuadrilla", height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        e_tec.pack(fill="x", padx=16, pady=2)

        ctk.CTkLabel(f_scroll, text="Costo Estimado ($ USD):", font=("Arial", 10, "bold"), text_color=self.C_GOLD).pack(anchor="w", padx=16, pady=(6, 2))
        e_cost = ctk.CTkEntry(f_scroll, placeholder_text="Ej: 35.00", height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        e_cost.pack(fill="x", padx=16, pady=2)

        lbl_bs = ctk.CTkLabel(f_scroll, text="Costo en Bs: 0,00 Bs", font=("Arial", 9, "bold"), text_color=self.C_GREEN)
        lbl_bs.pack(anchor="w", padx=16, pady=(2, 8))

        def calc_bs(event=None):
            try:
                v = float(e_cost.get().replace(",", "."))
                lbl_bs.configure(text=f"Costo en Bs: {formatear_bs(v * tasa)}")
            except ValueError:
                lbl_bs.configure(text="Costo en Bs: 0,00 Bs")

        e_cost.bind("<KeyRelease>", calc_bs)

        # Barra inferior fija para que el botón NUNCA se corte
        f_bottom = ctk.CTkFrame(win, fg_color="transparent")
        f_bottom.pack(fill="x", padx=20, pady=(6, 16))

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
                        f"Habitación {h} enviada a mantenimiento ({t}). Costo est: ${c_flt:.2f}."
                    )
                    messagebox.showinfo("Éxito", f"Habitación {h} bloqueada y puesta en mantenimiento.")
                    win.destroy()
                    self.cargar_ordenes()
                else:
                    messagebox.showerror("Error", "No se pudo registrar la orden en la base de datos.")
            except ValueError:
                messagebox.showerror("Error", "El costo debe ser un valor numérico.")

        ctk.CTkButton(
            f_bottom, text="Confirmar y Bloquear Habitación", fg_color="#3A1714", hover_color=self.C_RED,
            text_color="#FADBD8", font=("Montserrat", 11, "bold"), height=42, corner_radius=8,
            command=guardar
        ).pack(fill="x")

    # =========================================================================
    # MODAL 2: COBRO DE DAÑOS A HUÉSPED
    # =========================================================================
    def modal_cobro_dano(self):
        win = ctk.CTkToplevel(self)
        win.title("Cobro de Daños a Huésped")
        centrar_ventana(win, 520, 620)
        win.minsize(460, 500)
        win.grab_set()

        tasa = obtener_tasa_bcv()

        f_top_d = ctk.CTkFrame(win, fg_color="transparent")
        f_top_d.pack(fill="x", padx=20, pady=(16, 6))
        ctk.CTkLabel(f_top_d, text="REGISTRO Y COBRO DE DAÑO", font=("Montserrat", 13, "bold"), text_color=self.C_GOLD).pack(anchor="w")
        ctk.CTkLabel(f_top_d, text=f"Tasa BCV: {tasa:.2f} Bs/USD  •  Ingreso directo al corte de caja activo", font=("Arial", 9), text_color=self.C_TEXT_MUTED).pack(anchor="w")

        f_scroll_d = ctk.CTkScrollableFrame(win, fg_color=self.C_PANEL, corner_radius=12, border_width=1, border_color=self.C_BORDER)
        f_scroll_d.pack(fill="both", expand=True, padx=20, pady=6)

        f_r1 = ctk.CTkFrame(f_scroll_d, fg_color="transparent")
        f_r1.pack(fill="x", padx=16, pady=(8, 2))

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

        ctk.CTkLabel(f_scroll_d, text="Nombre del Huésped:", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", padx=16, pady=(4, 2))
        e_cli = ctk.CTkEntry(f_scroll_d, placeholder_text="Nombre y Apellido", height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        e_cli.pack(fill="x", padx=16, pady=2)

        ctk.CTkLabel(f_scroll_d, text="Concepto del Daño:", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", padx=16, pady=(4, 2))
        c_dano = ctk.CTkComboBox(
            f_scroll_d,
            values=[
                "Sábanas / Lencería Quemada o Rota", "Control de TV Dañado / Extraviado",
                "Toallas Dañadas / Extraviadas", "Vidrio / Espejo Roto",
                "Daño a Jacuzzi / Grifería", "Control de Aire Dañado", "Manchas / Daños en Colchón"
            ],
            height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER, text_color=self.C_TEXT_MAIN
        )
        c_dano.pack(fill="x", padx=16, pady=2)

        ctk.CTkLabel(f_scroll_d, text="Monto a Cobrar ($ USD):", font=("Arial", 10, "bold"), text_color=self.C_GOLD).pack(anchor="w", padx=16, pady=(6, 2))
        e_monto = ctk.CTkEntry(f_scroll_d, placeholder_text="Ej: 25.00", height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        e_monto.pack(fill="x", padx=16, pady=2)

        lbl_bs_calc = ctk.CTkLabel(f_scroll_d, text="Equivalente en Bs: 0,00 Bs", font=("Arial", 10, "bold"), text_color=self.C_GREEN)
        lbl_bs_calc.pack(anchor="w", padx=16, pady=(2, 6))

        def act_bs(event=None):
            try:
                m_val = float(e_monto.get().replace(",", "."))
                lbl_bs_calc.configure(text=f"Equivalente en Bs: {formatear_bs(m_val * tasa)}")
            except ValueError:
                lbl_bs_calc.configure(text="Equivalente en Bs: 0,00 Bs")

        e_monto.bind("<KeyRelease>", act_bs)

        ctk.CTkLabel(f_scroll_d, text="Forma de Cobro:", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", padx=16, pady=(4, 2))
        c_met = ctk.CTkComboBox(
            f_scroll_d, values=["EFECTIVO USD", "EFECTIVO BS", "PAGO MOVIL", "PUNTO DE VENTA"],
            height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER, text_color=self.C_TEXT_MAIN,
            command=lambda v: toggle_p2p_d(v)
        )
        c_met.pack(fill="x", padx=16, pady=2)

        frame_p2p_d = ctk.CTkFrame(f_scroll_d, fg_color="transparent")
        e_ref_d = ctk.CTkEntry(frame_p2p_d, placeholder_text="Ref (4 dígitos)", height=30, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        e_ref_d.pack(side="left", padx=2, fill="x", expand=True)
        e_ci_p2p = ctk.CTkEntry(frame_p2p_d, placeholder_text="C.I. Emisor", height=30, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        e_ci_p2p.pack(side="left", padx=2, fill="x", expand=True)
        e_tel_d = ctk.CTkEntry(frame_p2p_d, placeholder_text="Teléfono", height=30, fg_color=self.C_INPUT, border_color=self.C_BORDER)
        e_tel_d.pack(side="left", padx=2, fill="x", expand=True)

        def toggle_p2p_d(metodo):
            if metodo == "PAGO MOVIL":
                frame_p2p_d.pack(fill="x", padx=16, pady=6)
            else:
                frame_p2p_d.pack_forget()

        f_bot_d = ctk.CTkFrame(win, fg_color="transparent")
        f_bot_d.pack(fill="x", padx=20, pady=(6, 16))

        def cobrar():
            h, cli, ci, con, m, met = e_hab.get().strip().upper(), e_cli.get().strip(), e_ci_cli.get().strip(), c_dano.get(), e_monto.get().strip(), c_met.get()
            if not all([h, cli, ci, con, m]):
                messagebox.showwarning("Atención", "Complete todos los campos del daño.")
                return

            ref, ci_emisor, tel = None, None, None
            if met == "PAGO MOVIL":
                ref, ci_emisor, tel = e_ref_d.get().strip(), e_ci_p2p.get().strip(), e_tel_d.get().strip()
                if not (ref and ci_emisor and tel):
                    messagebox.showerror("Error", "Complete los datos del Pago Móvil.")
                    return

            try:
                m_flt = float(m.replace(",", "."))
                usr = self.controller.usuario_actual["usuario"]
                rol = self.controller.usuario_actual["rol"]

                if registrar_cobro_dano(h, cli, ci, con, m_flt, met, usr, ref, ci_emisor, tel):
                    p2p_txt = f" [Ref: {ref}]" if met == "PAGO MOVIL" else ""
                    registrar_auditoria(
                        usr, rol, "COBRO_DANO",
                        f"Daño en Hab {h} a {cli} (C.I: {ci}): '{con}' por ${m_flt:.2f} ({formatear_bs(m_flt * tasa)}) [{met}{p2p_txt}]."
                    )
                    messagebox.showinfo("Éxito", "Cobro registrado e ingresado al corte de caja activo.")
                    win.destroy()
                else:
                    messagebox.showerror("Error", "No se pudo registrar el cobro en base de datos.")
            except ValueError:
                messagebox.showerror("Error", "El monto ingresado no es válido.")

        ctk.CTkButton(
            f_bot_d, text="💳 Procesar Cobro e Ingresar a Caja", fg_color=self.C_GOLD,
            hover_color=self.C_GOLD_HOVER, text_color="#100F0D", font=("Montserrat", 11, "bold"),
            height=42, corner_radius=8, command=cobrar
        ).pack(fill="x")

    # =========================================================================
    # EXPORTACIÓN CONTABLE PDF (CONCORDANCIA CON FILTRO Y MODELO OFICIAL)
    # =========================================================================
    def exportar_gastos_pdf(self):
        f1 = self.cal_ini.get_date().strftime("%Y-%m-%d")
        f2 = self.cal_fin.get_date().strftime("%Y-%m-%d")

        # Refrescar datos desde la base de datos
        self.ordenes_raw = obtener_ordenes_mantenimiento(solo_activas=False)

        # Filtrar exactamente para el reporte contable
        ordenes_periodo = [
            o for o in self.ordenes_raw 
            if f1 <= str(o.get("fecha_inicio", ""))[:10] <= f2
        ]

        if not ordenes_periodo:
            messagebox.showwarning("Atención", "No hay registros de averías en el período seleccionado para exportar.")
            return

        f1_fmt = self.cal_ini.get_date().strftime("%d/%m/%Y")
        f2_fmt = self.cal_fin.get_date().strftime("%d/%m/%Y")
        tasa_emision = obtener_tasa_bcv()

        pdf = PDFReporteMantenimiento(f_inicio=f1_fmt, f_fin=f2_fmt)
        pdf.add_page()
        pdf.set_font("Helvetica", "", 7.5)

        tot_usd_finalizado, tot_bs_finalizado = 0.0, 0.0
        tot_usd_proceso, tot_bs_proceso = 0.0, 0.0
        por_rubro = {}

        fill = False
        for o in ordenes_periodo:
            f_inicio = _sanitizar_fpdf(str(o["fecha_inicio"])[:16])
            hab = _sanitizar_fpdf(str(o["hab_codigo"]))
            rubro = _sanitizar_fpdf(str(o["tipo_averia"])[:22])
            desc = _sanitizar_fpdf(str(o["descripcion"])[:45])
            tec = _sanitizar_fpdf(str(o["tecnico_responsable"])[:20])
            c_usd = float(o.get("costo_reparacion_usd", 0.0))
            c_bs = float(o.get("costo_reparacion_bs", 0.0))
            estado = _sanitizar_fpdf(str(o["estado"])).upper()

            tasa_reg = (c_bs / c_usd) if c_usd > 0 else tasa_emision

            es_fin = "FINALIZADO" in estado
            if es_fin:
                tot_usd_finalizado += c_usd
                tot_bs_finalizado += c_bs
                por_rubro[rubro] = por_rubro.get(rubro, 0.0) + c_usd
            else:
                tot_usd_proceso += c_usd
                tot_bs_proceso += c_bs

            pdf.set_fill_color(248, 246, 242) if fill else pdf.set_fill_color(255, 255, 255)

            pdf.cell(24, 6, f_inicio, 1, 0, "C", fill=True)
            pdf.cell(16, 6, hab, 1, 0, "C", fill=True)
            pdf.cell(38, 6, rubro, 1, 0, "L", fill=True)
            pdf.cell(75, 6, desc, 1, 0, "L", fill=True)
            pdf.cell(36, 6, tec, 1, 0, "L", fill=True)
            pdf.cell(20, 6, f"{tasa_reg:,.2f}", 1, 0, "C", fill=True)
            pdf.cell(22, 6, f"${c_usd:.2f}", 1, 0, "R", fill=True)
            pdf.cell(28, 6, _sanitizar_fpdf(formatear_bs(c_bs).replace(" Bs", "")), 1, 0, "R", fill=True)

            if es_fin:
                pdf.set_text_color(39, 174, 96)
                pdf.cell(18, 6, "PAGADO", 1, 1, "C", fill=True)
            else:
                pdf.set_text_color(192, 57, 43)
                pdf.cell(18, 6, "PENDIENTE", 1, 1, "C", fill=True)

            pdf.set_text_color(0, 0, 0)
            fill = not fill

        # Resumen Contable
        pdf.ln(4)
        pdf.set_fill_color(230, 225, 215)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(209, 6, _sanitizar_fpdf("TOTAL GASTOS CAUSADOS / PAGADOS (FINALIZADOS):"), 1, 0, "R", fill=True)
        pdf.cell(22, 6, f"${tot_usd_finalizado:,.2f}", 1, 0, "R", fill=True)
        pdf.cell(28, 6, _sanitizar_fpdf(formatear_bs(tot_bs_finalizado).replace(" Bs", "")), 1, 0, "R", fill=True)
        pdf.cell(18, 6, "CAUSADO", 1, 1, "C", fill=True)

        if tot_usd_proceso > 0:
            pdf.set_fill_color(245, 235, 235)
            pdf.cell(209, 6, _sanitizar_fpdf("TOTAL GASTOS EN PROCESO (PROVISIÓN POR PAGAR):"), 1, 0, "R", fill=True)
            pdf.cell(22, 6, f"${tot_usd_proceso:,.2f}", 1, 0, "R", fill=True)
            pdf.cell(28, 6, _sanitizar_fpdf(formatear_bs(tot_bs_proceso).replace(" Bs", "")), 1, 0, "R", fill=True)
            pdf.cell(18, 6, "PROVISIÓN", 1, 1, "C", fill=True)

        pdf.ln(4)
        y_pos = pdf.get_y()

        # Cuadro 1: Centros de Costo
        pdf.set_xy(10, y_pos)
        pdf.set_fill_color(248, 246, 242)
        pdf.rect(10, y_pos, 85, 34, "F")
        pdf.rect(10, y_pos, 85, 34, "D")

        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_xy(13, y_pos + 2)
        pdf.cell(79, 4, _sanitizar_fpdf("IMPUTACIÓN POR CENTRO DE COSTO:"), 0, 1)

        pdf.set_font("Helvetica", "", 7)
        y_rub = y_pos + 7
        for rub, m_usd in list(por_rubro.items())[:5]:
            pdf.set_xy(13, y_rub)
            pct = (m_usd / tot_usd_finalizado * 100) if tot_usd_finalizado > 0 else 0
            pdf.cell(55, 3.5, _sanitizar_fpdf(f"- {rub}:"), 0, 0)
            pdf.cell(24, 3.5, f"${m_usd:,.2f} ({pct:.0f}%)", 0, 1, "R")
            y_rub += 4

        # Cuadro 2: Asiento Contable
        pdf.set_xy(98, y_pos)
        pdf.set_fill_color(248, 246, 242)
        pdf.rect(98, y_pos, 85, 34, "F")
        pdf.rect(98, y_pos, 85, 34, "D")

        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_xy(101, y_pos + 2)
        pdf.cell(79, 4, _sanitizar_fpdf("ASIENTO DE DIARIO SUGERIDO:"), 0, 1)

        pdf.set_font("Helvetica", "", 7)
        pdf.set_xy(101, y_pos + 7)
        pdf.cell(50, 4, _sanitizar_fpdf("Gastos Mantenimiento (Debe):"), 0, 0)
        pdf.cell(28, 4, _sanitizar_fpdf(formatear_bs(tot_bs_finalizado)), 0, 1, "R")

        pdf.set_xy(101, y_pos + 12)
        pdf.cell(50, 4, _sanitizar_fpdf("Caja / Banco (Haber):"), 0, 0)
        pdf.cell(28, 4, _sanitizar_fpdf(formatear_bs(tot_bs_finalizado)), 0, 1, "R")

        if tot_usd_proceso > 0:
            pdf.set_xy(101, y_pos + 18)
            pdf.cell(50, 4, _sanitizar_fpdf("Provisión Pasivo (Haber):"), 0, 0)
            pdf.cell(28, 4, _sanitizar_fpdf(formatear_bs(tot_bs_proceso)), 0, 1, "R")

        # Cuadro 3: Total General
        pdf.set_xy(186, y_pos)
        pdf.set_fill_color(26, 24, 22)
        pdf.rect(186, y_pos, 101, 34, "F")

        pdf.set_text_color(212, 175, 55)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_xy(188, y_pos + 3)
        pdf.cell(97, 4, _sanitizar_fpdf("TOTAL EGRESOS CAUSADOS EN EL PERÍODO"), 0, 1, "C")

        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_xy(188, y_pos + 8)
        pdf.cell(97, 6, f"${tot_usd_finalizado:,.2f} USD", 0, 1, "C")

        pdf.set_text_color(180, 225, 190)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_xy(188, y_pos + 16)
        pdf.cell(97, 5, _sanitizar_fpdf(formatear_bs(tot_bs_finalizado)), 0, 1, "C")

        pdf.set_font("Helvetica", "I", 7)
        pdf.set_text_color(180, 180, 180)
        pdf.set_xy(188, y_pos + 24)
        pdf.cell(97, 4, _sanitizar_fpdf(f"Tasa BCV al cierre de emisión: {tasa_emision:.2f} Bs/USD"), 0, 1, "C")
        pdf.set_text_color(0, 0, 0)

        # Firmas
        pdf.set_y(y_pos + 48)
        pdf.set_font("Helvetica", "B", 7)

        pdf.line(20, pdf.get_y(), 80, pdf.get_y())
        pdf.set_x(20)
        pdf.cell(60, 4, _sanitizar_fpdf("SUPERVISOR DE MANTENIMIENTO"), 0, 0, "C")

        pdf.line(115, pdf.get_y(), 175, pdf.get_y())
        pdf.set_x(115)
        pdf.cell(60, 4, _sanitizar_fpdf("REVISADO POR (CONTABILIDAD)"), 0, 0, "C")

        pdf.line(210, pdf.get_y(), 270, pdf.get_y())
        pdf.set_x(210)
        pdf.cell(60, 4, _sanitizar_fpdf("APROBADO POR (GERENCIA GENERAL)"), 0, 1, "C")

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        export_dir = os.path.join(base_dir, "reportes_exportados")
        os.makedirs(export_dir, exist_ok=True)

        ruta = os.path.join(export_dir, f"informe_contable_mantenimiento_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        pdf.output(ruta)
        os.system(f'start "" "{ruta}"' if os.name == 'nt' else f'open "{ruta}"')