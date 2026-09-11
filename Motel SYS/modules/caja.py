"""
===============================================================================
SISTEMA DE GESTIÓN DE MOTELES - MOTEL PRO v2.0
Módulo: modules/caja.py (CONCILIACIÓN DE CAJA, ARQUEO DE TURNO Y AUDITORÍA)
Diseño: Dark Luxury & Enterprise Grade Financial Suite (5 KPIs de Arqueo)
===============================================================================
"""

import os
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from fpdf import FPDF

# Importaciones desde la Capa de Datos (database/db_manager.py)
from database.db_manager import (
    verificar_cierre_existente, registrar_cierre_turno, obtener_detalle_cierre_turno,
    registrar_auditoria, formatear_bs, formatear_usd, obtener_ruta_recurso
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
# GENERADOR DEL COMPROBANTE CONTABLE PDF (190 MM EXACTOS)
# =============================================================================
class PDFCierreContable(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_margins(10, 10, 10)
        self.set_auto_page_break(auto=True, margin=12)

    def header(self):
        logo = obtener_ruta_recurso("logo_hotel.png")
        if os.path.exists(logo):
            self.image(logo, x=10, y=8, w=18)

        self.set_font("Helvetica", "B", 12)
        self.cell(0, 5, "INVERSIONES SAIBABA C.A.", 0, 1, "C")
        self.set_font("Helvetica", "B", 8.5)
        self.cell(0, 4, "RIF: J-30250227-6  •  MOTEL EL EDEN", 0, 1, "C")
        self.set_font("Helvetica", "B", 10.5)
        self.cell(0, 5, "COMPROBANTE DETALLADO DE CIERRE DE CAJA Y ARQUEO", 0, 1, "C")

        self.set_draw_color(180, 180, 180)
        self.line(10, 29, 200, 29)
        self.set_y(32)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(130, 130, 130)
        self.cell(0, 8, f"Documento Contable y de Auditoría Interna  •  Página {self.page_no()}", 0, 0, "C")


class FrameCaja(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#100F0D")
        self.controller = controller

        # =====================================================================
        # CONSTANTES DE DISEÑO - PALETA LUXURY BOUTIQUE
        # =====================================================================
        self.C_BG = "#100F0D"
        self.C_PANEL = "#161513"
        self.C_CARD = "#1E1C19"
        self.C_BORDER = "#2E2A25"
        self.C_GOLD = "#D4AF37"
        self.C_GOLD_HOVER = "#B89228"
        self.C_GREEN = "#2ECC71"
        self.C_BLUE = "#3498DB"
        self.C_RED = "#E74C3C"
        self.C_TEXT_MAIN = "#F5EFEB"
        self.C_TEXT_MUTED = "#8E8880"

        self.datos_turno = None

        # =====================================================================
        # 1. HEADER Y BARRA DE CONTROL DEL TURNO
        # =====================================================================
        self.frame_header = ctk.CTkFrame(
            self, fg_color=self.C_PANEL, corner_radius=14,
            border_width=1, border_color=self.C_BORDER
        )
        self.frame_header.pack(fill="x", padx=16, pady=(16, 8))

        # Título y Subtítulo
        f_titulos = ctk.CTkFrame(self.frame_header, fg_color="transparent")
        f_titulos.pack(side="left", padx=18, pady=12)

        ctk.CTkLabel(
            f_titulos, text="CONCILIACIÓN Y CIERRE DE CAJA",
            font=("Montserrat", 14, "bold"), text_color=self.C_GOLD
        ).pack(anchor="w")

        self.lbl_estado_cierre = ctk.CTkLabel(
            f_titulos, text="Verificando disponibilidad de turno...",
            font=("Arial", 9), text_color=self.C_TEXT_MUTED
        )
        self.lbl_estado_cierre.pack(anchor="w")

        # Controles a la derecha
        f_controles = ctk.CTkFrame(self.frame_header, fg_color="transparent")
        f_controles.pack(side="right", padx=18, pady=12)

        ctk.CTkLabel(f_controles, text="Turno:", font=("Arial", 11, "bold"), text_color=self.C_TEXT_MUTED).pack(side="left", padx=4)

        ahora_hora = datetime.now().hour
        turno_defecto = "MAÑANA" if 8 <= ahora_hora < 17 else "NOCHE"

        self.c_turno = ctk.CTkComboBox(
            f_controles, values=["MAÑANA", "NOCHE"], width=110, height=32,
            fg_color=self.C_CARD, border_color=self.C_BORDER, text_color=self.C_TEXT_MAIN,
            dropdown_fg_color=self.C_CARD, command=lambda v: self.cargar_detalle()
        )
        self.c_turno.set(turno_defecto)
        self.c_turno.pack(side="left", padx=4)

        ctk.CTkButton(
            f_controles, text="🔄 Recalcular", width=100, height=32, corner_radius=8,
            fg_color=self.C_CARD, hover_color="#2A2621", text_color=self.C_TEXT_MAIN,
            font=("Arial", 11, "bold"), border_width=1, border_color=self.C_BORDER,
            command=self.cargar_detalle
        ).pack(side="left", padx=6)

        self.btn_cerrar = ctk.CTkButton(
            f_controles, text="🔒 Asentar Cierre & PDF", height=34, corner_radius=8,
            fg_color=self.C_GOLD, hover_color=self.C_GOLD_HOVER, text_color="#100F0D",
            font=("Montserrat", 11, "bold"), command=self.cerrar_turno
        )
        self.btn_cerrar.pack(side="left", padx=(4, 0))

        # =====================================================================
        # 2. PANEL RESUMEN: 5 TARJETAS DE ARQUEO BIMONETARIO
        # =====================================================================
        self.frame_cards = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_cards.pack(fill="x", padx=16, pady=(0, 10))
        self.frame_cards.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        def crear_tarjeta_resumen(col, titulo, icono, tag_text, tag_color):
            card = ctk.CTkFrame(
                self.frame_cards, fg_color=self.C_PANEL, corner_radius=12,
                border_width=1, border_color=self.C_BORDER
            )
            card.grid(row=0, column=col, padx=4, sticky="nsew")

            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=10, pady=(10, 2))

            ctk.CTkLabel(top, text=f"{icono} {titulo}", font=("Montserrat", 9, "bold"), text_color=self.C_TEXT_MUTED).pack(side="left")
            
            badge = ctk.CTkFrame(top, fg_color="#100F0D", corner_radius=5, border_width=1, border_color=tag_color)
            badge.pack(side="right")
            ctk.CTkLabel(badge, text=tag_text, font=("Arial", 9, "bold"), text_color=tag_color).pack(padx=4, pady=1)

            lbl_val = ctk.CTkLabel(card, text="$0.00", font=("Montserrat", 14, "bold"), text_color=self.C_TEXT_MAIN)
            lbl_val.pack(anchor="w", padx=10, pady=(2, 0))

            lbl_sub = ctk.CTkLabel(card, text="--", font=("Arial", 9), text_color=self.C_TEXT_MUTED)
            lbl_sub.pack(anchor="w", padx=10, pady=(0, 10))

            return lbl_val, lbl_sub

        self.kpi_usd, self.kpi_usd_sub = crear_tarjeta_resumen(0, "EFECTIVO USD", "💵", "Gaveta $", self.C_GREEN)
        self.kpi_bs_efectivo, self.kpi_bs_efectivo_sub = crear_tarjeta_resumen(1, "EFECTIVO BS", "🇻🇪", "Gaveta Bs", "#48C9B0")
        self.kpi_p2p, self.kpi_p2p_sub = crear_tarjeta_resumen(2, "PAGO MÓVIL", "📱", "Banco P2P", self.C_BLUE)
        self.kpi_punto, self.kpi_punto_sub = crear_tarjeta_resumen(3, "PUNTO DE VENTA", "💳", "Datáfono", "#AF7AC5")
        self.kpi_bs_tot, self.kpi_bs_sub = crear_tarjeta_resumen(4, "TOTAL GENERAL", "💰", "Consolidado", self.C_GOLD)

        # =====================================================================
        # 3. TABVIEW DE OPERACIONES DEL TURNO
        # =====================================================================
        self.tabview = ctk.CTkTabview(
            self, fg_color=self.C_PANEL, segmented_button_fg_color=self.C_CARD,
            segmented_button_selected_color=self.C_GOLD,
            segmented_button_selected_hover_color=self.C_GOLD_HOVER,
            segmented_button_unselected_hover_color="#2A2621",
            text_color="#100F0D"
        )
        self.tabview.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        # Crear Pestañas
        self.tab_hab = self.tabview.add("🏨 Alquileres de Habitaciones")
        self.tab_mer = self.tabview.add("🛒 Ventas Mini-Bar")
        self.tab_dan = self.tabview.add("⚡ Daños Cobrados")

        # Scrollable frames internos para cada pestaña
        self.scroll_hab = ctk.CTkScrollableFrame(self.tab_hab, fg_color=self.C_BG)
        self.scroll_hab.pack(fill="both", expand=True, padx=4, pady=4)

        self.scroll_mer = ctk.CTkScrollableFrame(self.tab_mer, fg_color=self.C_BG)
        self.scroll_mer.pack(fill="both", expand=True, padx=4, pady=4)

        self.scroll_dan = ctk.CTkScrollableFrame(self.tab_dan, fg_color=self.C_BG)
        self.scroll_dan.pack(fill="both", expand=True, padx=4, pady=4)

        self.cargar_detalle()

    # =========================================================================
    # LÓGICA DE AUDITORÍA Y CARGA DE DATOS
    # =========================================================================
    def cargar_detalle(self):
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        turno = self.c_turno.get()

        self.datos_turno = obtener_detalle_cierre_turno(fecha_hoy, turno)
        self.datos_turno["recepcionista"] = self.controller.usuario_actual["usuario"]

        # 1. Comprobar si ya está cerrado
        ya_cerrado = verificar_cierre_existente(fecha_hoy, turno)
        if ya_cerrado:
            self.lbl_estado_cierre.configure(text=f"🔒 Turno {turno} del día {fecha_hoy} ya está CERRADO y auditado.", text_color=self.C_RED)
            self.btn_cerrar.configure(state="disabled", fg_color="#3A1714", text="Turno Ya Cerrado")
        else:
            self.lbl_estado_cierre.configure(text=f"🟢 Turno {turno} en Curso  •  Tasa BCV: {self.datos_turno['tasa_bcv']:.2f} Bs/USD", text_color=self.C_GREEN)
            self.btn_cerrar.configure(state="normal", fg_color=self.C_GOLD, text="🔒 Asentar Cierre & PDF")

        # 2. Refrescar las 5 Tarjetas KPI
        d = self.datos_turno
        
        # KPI 0: Efectivo USD
        self.kpi_usd.configure(text=f"${d['total_efectivo_usd']:,.2f}")
        self.kpi_usd_sub.configure(text="Arqueo físico obligatorio")

        # KPI 1: Efectivo Bs (NUEVO)
        self.kpi_bs_efectivo.configure(text=formatear_bs(d['total_efectivo_bs']))
        self.kpi_bs_efectivo_sub.configure(text="Efectivo en billetes Bs")

        # KPI 2: Pago Móvil
        self.kpi_p2p.configure(text=formatear_bs(d['total_p2p_bs']))
        self.kpi_p2p_sub.configure(text="Verificar en cuenta bancaria")

        # KPI 3: Punto de Venta
        self.kpi_punto.configure(text=formatear_bs(d['total_punto_bs']))
        self.kpi_punto_sub.configure(text="Cotejar cierre de lote")

        # KPI 4: Total Consolidado en Bolívares
        self.kpi_bs_tot.configure(text=formatear_bs(d['total_bs_consolidado']))
        self.kpi_bs_sub.configure(text="Recaudación global del turno")

        # 3. Renderizar Pestaña Habitaciones
        for w in self.scroll_hab.winfo_children(): w.destroy()
        if not d["habitaciones"]:
            self._render_empty(self.scroll_hab, "Sin alquileres registrados en este turno.")
        else:
            for h in d["habitaciones"]:
                card = ctk.CTkFrame(self.scroll_hab, fg_color=self.C_CARD, corner_radius=8, border_width=1, border_color=self.C_BORDER)
                card.pack(fill="x", pady=3, padx=2)

                f_izq = ctk.CTkFrame(card, fg_color="transparent")
                f_izq.pack(side="left", padx=12, pady=8)
                ctk.CTkLabel(f_izq, text=f"Habitación {h['habitacion']}", font=("Montserrat", 11, "bold"), text_color=self.C_TEXT_MAIN).pack(anchor="w")
                
                det_alq = self.formatear_metodos_str(h["alq_usd"], h["alq_bs"], h["alq_p2p"], h["alq_punto"])
                ctk.CTkLabel(f_izq, text=f"Alquileres: {det_alq}  •  Frecuencia: {h['cantidad']} vez(ces)", font=("Arial", 9), text_color=self.C_TEXT_MUTED).pack(anchor="w")

                f_der = ctk.CTkFrame(card, fg_color="transparent")
                f_der.pack(side="right", padx=12, pady=8)
                ctk.CTkLabel(f_der, text=f"${h['total_usd']:.2f}", font=("Montserrat", 12, "bold"), text_color=self.C_GOLD).pack(anchor="e")
                ctk.CTkLabel(f_der, text=formatear_bs(h['total_bs']), font=("Arial", 9, "bold"), text_color=self.C_GREEN).pack(anchor="e")

        # 4. Renderizar Pestaña Mercancía
        for w in self.scroll_mer.winfo_children(): w.destroy()
        if not d["mercancia"]:
            self._render_empty(self.scroll_mer, "Sin ventas de mini-bar registradas en este turno.")
        else:
            for m in d["mercancia"]:
                card = ctk.CTkFrame(self.scroll_mer, fg_color=self.C_CARD, corner_radius=8, border_width=1, border_color=self.C_BORDER)
                card.pack(fill="x", pady=3, padx=2)

                f_izq = ctk.CTkFrame(card, fg_color="transparent")
                f_izq.pack(side="left", padx=12, pady=8)
                ctk.CTkLabel(f_izq, text=m['producto'], font=("Montserrat", 11, "bold"), text_color=self.C_TEXT_MAIN).pack(anchor="w")
                
                det_mer = self.formatear_metodos_str(m["usd"], m["bs"], m["p2p"], m["punto"])
                ctk.CTkLabel(f_izq, text=f"Métodos: {det_mer}", font=("Arial", 9), text_color=self.C_TEXT_MUTED).pack(anchor="w")

                f_der = ctk.CTkFrame(card, fg_color="transparent")
                f_der.pack(side="right", padx=12, pady=8)
                ctk.CTkLabel(f_der, text=f"{m['cantidad']} un.  |  ${m['total_usd']:.2f}", font=("Montserrat", 11, "bold"), text_color=self.C_GOLD).pack(anchor="e")
                ctk.CTkLabel(f_der, text=formatear_bs(m['total_bs']), font=("Arial", 9, "bold"), text_color=self.C_GREEN).pack(anchor="e")

        # 5. Renderizar Pestaña Daños
        for w in self.scroll_dan.winfo_children(): w.destroy()
        if not d["danos"]:
            self._render_empty(self.scroll_dan, "No se registraron cobros de daños en este turno.")
        else:
            for dn in d["danos"]:
                card = ctk.CTkFrame(self.scroll_dan, fg_color="#231A18", corner_radius=8, border_width=1, border_color="#5C201A")
                card.pack(fill="x", pady=3, padx=2)

                f_izq = ctk.CTkFrame(card, fg_color="transparent")
                f_izq.pack(side="left", padx=12, pady=8)
                ctk.CTkLabel(f_izq, text=f"Hab {dn['hab_codigo']}  •  Huésped: {dn['cliente_nombre']} (C.I: {dn.get('cliente_ci', 'N/A')})", font=("Montserrat", 10, "bold"), text_color="#FADBD8").pack(anchor="w")
                ctk.CTkLabel(f_izq, text=f"Incidencia: {dn['concepto_dano']}  [{dn['metodo']}]", font=("Arial", 9, "italic"), text_color=self.C_TEXT_MUTED).pack(anchor="w")

                f_der = ctk.CTkFrame(card, fg_color="transparent")
                f_der.pack(side="right", padx=12, pady=8)
                ctk.CTkLabel(f_der, text=f"${dn['monto_usd']:.2f}", font=("Montserrat", 12, "bold"), text_color=self.C_RED).pack(anchor="e")
                ctk.CTkLabel(f_der, text=formatear_bs(dn['monto_bs']), font=("Arial", 9, "bold"), text_color=self.C_GREEN).pack(anchor="e")

    def _render_empty(self, parent, msg: str):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", pady=20)
        ctk.CTkLabel(f, text=msg, font=("Arial", 10, "italic"), text_color=self.C_TEXT_MUTED).pack()

    def formatear_metodos_str(self, usd: float, bs: float, p2p: float, punto: float) -> str:
        """Construye una cadena contable compacta y legible sin amontonar textos."""
        partes = []
        if usd > 0: partes.append(f"${usd:.2f}")
        if bs > 0: partes.append(f"{bs:,.2f} Bs".replace(",", "X").replace(".", ",").replace("X", "."))
        if p2p > 0: partes.append(f"{p2p:,.2f} P2P".replace(",", "X").replace(".", ",").replace("X", "."))
        if punto > 0: partes.append(f"{punto:,.2f} Punto".replace(",", "X").replace(".", ",").replace("X", "."))
        return " / ".join(partes) if partes else "0,00"

    # =========================================================================
    # CIERRE DEFINITIVO Y DISPARO DE NOTIFICACIONES
    # =========================================================================
    def cerrar_turno(self):
        if not self.datos_turno:
            return

        fecha = self.datos_turno["fecha"]
        turno = self.datos_turno["turno"]
        usr_act = self.controller.usuario_actual["usuario"]
        rol_act = self.controller.usuario_actual["rol"]

        if verificar_cierre_existente(fecha, turno):
            registrar_auditoria(usr_act, rol_act, "CIERRE_DUPLICADO_BLOQUEADO", f"Intento de cerrar el turno {turno} ({fecha}) que ya estaba cerrado.")
            messagebox.showerror("Cierre Duplicado", f"El turno {turno} del día {fecha} YA fue cerrado previamente.")
            return

        # Confirmación interactiva de seguridad
        msg_confirmacion = (
            f"¿Confirma el cierre definitivo del Turno {turno}?\n\n"
            f"💵 Efectivo en Divisas ($): ${self.datos_turno['total_efectivo_usd']:.2f}\n"
            f"🇻🇪 Efectivo en Bolívares (Bs): {formatear_bs(self.datos_turno['total_efectivo_bs'])}\n"
            f"📱 Pago Móvil (P2P): {formatear_bs(self.datos_turno['total_p2p_bs'])}\n"
            f"💳 Punto de Venta: {formatear_bs(self.datos_turno['total_punto_bs'])}\n\n"
            f"💰 TOTAL GENERAL RECAUDADO: {formatear_bs(self.datos_turno['total_bs_consolidado'])}\n\n"
            f"⚠️ Esta acción fijará la contabilidad del turno y no podrá deshacerse."
        )

        if not messagebox.askyesno("Confirmación de Arqueo y Cierre", msg_confirmacion):
            return

        datos_guardar = {
            "fecha": fecha, "turno": turno,
            "total_bs": self.datos_turno["total_bs_consolidado"],
            "total_usd": self.datos_turno["total_efectivo_usd"],
            "total_p2p": self.datos_turno["total_p2p_bs"],
            "total_punto": self.datos_turno["total_punto_bs"],
            "recepcionista": usr_act
        }

        if registrar_cierre_turno(datos_guardar):
            registrar_auditoria(
                usr_act, rol_act, "CIERRE_TURNO",
                f"Cierre Turno {turno} ({fecha}). Total Bs: {formatear_bs(datos_guardar['total_bs'])}, Total USD: ${datos_guardar['total_usd']:.2f}."
            )

            # Notificación Multicanal Compatible con WhatsApp y Telegram
            try:
                from modules.notificaciones import disparar_notificacion_multicanal
                asunto_notif = f"CIERRE DE CAJA - Turno {turno} ({fecha})"
                msg_notif = (
                    f"🏨 <b>MOTEL EL EDEN - CIERRE DE TURNO</b>\n"
                    f"📅 <b>Fecha:</b> {fecha} | <b>Turno:</b> {turno}\n"
                    f"👤 <b>Responsable:</b> {usr_act}\n\n"
                    f"💵 <b>TOTAL EFECTIVO USD:</b> ${datos_guardar['total_usd']:.2f}\n"
                    f"🇻🇪 <b>EFECTIVO BOLÍVARES:</b> {formatear_bs(self.datos_turno['total_efectivo_bs'])}\n"
                    f"📱 <b>Pago Móvil:</b> {formatear_bs(datos_guardar['total_p2p'])}\n"
                    f"💳 <b>Punto de Venta:</b> {formatear_bs(datos_guardar['total_punto'])}\n"
                    f"💰 <b>TOTAL BOLÍVARES:</b> {formatear_bs(datos_guardar['total_bs'])}\n"
                )
                disparar_notificacion_multicanal(asunto_notif, msg_notif)
            except Exception as e:
                print(f"Error enviando notificación de cierre: {e}")

            self.exportar_pdf_cierre()
            messagebox.showinfo("Éxito", "Cierre contable registrado, notificado y exportado a PDF.")
            self.cargar_detalle()
        else:
            messagebox.showerror("Error", "No se pudo registrar el cierre en la base de datos.")

    # =========================================================================
    # GENERADOR DEL REPORTE PDF SIN TEXTOS CORTADOS (ANCHO 190 MM EXACTO)
    # =========================================================================
    def exportar_pdf_cierre(self):
        pdf = PDFCierreContable()
        pdf.add_page()
        pdf.set_text_color(0, 0, 0)
        pdf.set_draw_color(0, 0, 0)

        # ---------------------------------------------------------------------
        # 1. BLOQUE DE METADATOS SEPARADOS Y ALINEADOS
        # ---------------------------------------------------------------------
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(35, 5, "FECHA DE CIERRE:", 0, 0, "L")
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(60, 5, self.datos_turno['fecha'], 0, 0, "L")

        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(20, 5, "TURNO:", 0, 0, "L")
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(75, 5, self.datos_turno['turno'], 0, 1, "L")

        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(35, 5, "RECEPCIONISTA:", 0, 0, "L")
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(60, 5, self.datos_turno['recepcionista'].upper(), 0, 0, "L")

        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(20, 5, "TASA BCV:", 0, 0, "L")
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(75, 5, f"{self.datos_turno['tasa_bcv']:.2f} Bs / USD", 0, 1, "L")
        pdf.ln(4)

        # ---------------------------------------------------------------------
        # 2. CUADRO 1: RESUMEN DE HABITACIONES (Ancho Total: 190 mm)
        # ---------------------------------------------------------------------
        pdf.set_fill_color(220, 220, 220)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(28, 6, "HABITACIÓN", 1, 0, "C", fill=True)
        pdf.cell(14, 6, "CANT", 1, 0, "C", fill=True)
        pdf.cell(52, 6, "SUBTOTAL (ALQUILER)", 1, 0, "C", fill=True)
        pdf.cell(42, 6, "MERCANCÍA", 1, 0, "C", fill=True)
        pdf.cell(30, 6, "TOTAL BS", 1, 0, "C", fill=True)
        pdf.cell(24, 6, "TOTAL $", 1, 0, "C", fill=True)
        pdf.ln()

        pdf.set_font("Helvetica", "", 7.5)
        for h in self.datos_turno["habitaciones"]:
            sub_alq_str = self.formatear_metodos_str(h["alq_usd"], h["alq_bs"], h["alq_p2p"], h["alq_punto"])
            sub_mer_str = self.formatear_metodos_str(h["mer_usd"], h["mer_bs"], h["mer_p2p"], h["mer_punto"])

            pdf.cell(28, 5.5, h["habitacion"][:16], 1, 0, "C")
            pdf.cell(14, 5.5, str(h["cantidad"]), 1, 0, "C")
            pdf.cell(52, 5.5, sub_alq_str[:34], 1, 0, "C")
            pdf.cell(42, 5.5, sub_mer_str[:28], 1, 0, "C")
            pdf.cell(30, 5.5, formatear_bs(h["total_bs"]).replace(" Bs", ""), 1, 0, "R")
            pdf.cell(24, 5.5, f"${h['total_usd']:.2f}", 1, 0, "R")
            pdf.ln()

        pdf.ln(3)

        # ---------------------------------------------------------------------
        # 3. CUADRO 2: DETALLE DE MERCANCÍA VENDIDA (Ancho Total: 190 mm)
        # ---------------------------------------------------------------------
        pdf.set_fill_color(220, 220, 220)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(48, 6, "PRODUCTO", 1, 0, "C", fill=True)
        pdf.cell(16, 6, "CANT", 1, 0, "C", fill=True)
        pdf.cell(66, 6, "SUBTOTAL (MÉTODOS)", 1, 0, "C", fill=True)
        pdf.cell(34, 6, "TOTAL BS", 1, 0, "C", fill=True)
        pdf.cell(26, 6, "TOTAL $", 1, 0, "C", fill=True)
        pdf.ln()

        pdf.set_font("Helvetica", "", 7.5)
        if not self.datos_turno["mercancia"]:
            pdf.cell(190, 5.5, "No se registraron ventas de mercancía en este turno.", 1, 1, "C")
        else:
            for m in self.datos_turno["mercancia"]:
                metodos_prod = self.formatear_metodos_str(m["usd"], m["bs"], m["p2p"], m["punto"])
                pdf.cell(48, 5.5, m["producto"][:28], 1, 0, "L")
                pdf.cell(16, 5.5, str(m["cantidad"]), 1, 0, "C")
                pdf.cell(66, 5.5, metodos_prod[:42], 1, 0, "C")
                pdf.cell(34, 5.5, formatear_bs(m["total_bs"]), 1, 0, "R")
                pdf.cell(26, 5.5, f"${m['total_usd']:.2f}", 1, 0, "R")
                pdf.ln()

        pdf.ln(3)

        # ---------------------------------------------------------------------
        # 4. CUADRO 3: COBROS POR DAÑOS A HUÉSPEDES (SIN CORTES)
        # ---------------------------------------------------------------------
        if self.datos_turno["danos"]:
            pdf.set_fill_color(245, 230, 230)
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(18, 6, "HAB", 1, 0, "C", fill=True)
            pdf.cell(46, 6, "HUÉSPED RESPONSABLE", 1, 0, "L", fill=True)
            pdf.cell(56, 6, "CONCEPTO DEL DAÑO", 1, 0, "L", fill=True)
            pdf.cell(26, 6, "MÉTODO", 1, 0, "C", fill=True)
            pdf.cell(24, 6, "MONTO (BS)", 1, 0, "R", fill=True)
            pdf.cell(20, 6, "MONTO ($)", 1, 0, "R", fill=True)
            pdf.ln()

            pdf.set_font("Helvetica", "", 7.5)
            for d in self.datos_turno["danos"]:
                met_raw = d["metodo"]
                if "PAGO MOVIL" in met_raw:
                    ref_txt = f" Ref:{d['p2p_referencia']}" if d.get("p2p_referencia") else ""
                    met_str = f"P2P{ref_txt}"
                elif "EFECTIVO USD" in met_raw:
                    met_str = "Efectivo $"
                elif "EFECTIVO BS" in met_raw:
                    met_str = "Efectivo Bs"
                elif "PUNTO" in met_raw:
                    met_str = "Punto Venta"
                else:
                    met_str = met_raw[:14]

                ci_str = f" (CI: {d['cliente_ci']})" if d.get("cliente_ci") else ""
                huesped_txt = f"{d['cliente_nombre']}{ci_str}"

                pdf.cell(18, 5.5, d["hab_codigo"][:10], 1, 0, "C")
                pdf.cell(46, 5.5, huesped_txt[:28], 1, 0, "L")
                pdf.cell(56, 5.5, d["concepto_dano"][:36], 1, 0, "L")
                pdf.cell(26, 5.5, met_str[:16], 1, 0, "C")
                pdf.cell(24, 5.5, formatear_bs(d["monto_bs"]).replace(" Bs", ""), 1, 0, "R")
                pdf.cell(20, 5.5, f"${d['monto_usd']:.2f}", 1, 0, "R")
                pdf.ln()

            pdf.ln(3)

        # ---------------------------------------------------------------------
        # 5. CONCILIACIÓN POR MÉTODO DE PAGO
        # ---------------------------------------------------------------------
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(190, 6, "CONCILIACIÓN POR MÉTODO DE PAGO", 1, 1, "C", fill=True)

        pdf.set_font("Helvetica", "", 8.5)
        pdf.cell(130, 5, "  Total Efectivo Dólares ($):", 1, 0, "L")
        pdf.cell(60, 5, f"${self.datos_turno['total_efectivo_usd']:.2f}", 1, 1, "R")

        pdf.cell(130, 5, "  Total Efectivo Bolívares:", 1, 0, "L")
        pdf.cell(60, 5, formatear_bs(self.datos_turno['total_efectivo_bs']), 1, 1, "R")

        pdf.cell(130, 5, "  Total Pago Móvil (Bs):", 1, 0, "L")
        pdf.cell(60, 5, formatear_bs(self.datos_turno['total_p2p_bs']), 1, 1, "R")

        pdf.cell(130, 5, "  Total Punto de Venta (Bs):", 1, 0, "L")
        pdf.cell(60, 5, formatear_bs(self.datos_turno['total_punto_bs']), 1, 1, "R")
        pdf.ln(4)

        # ---------------------------------------------------------------------
        # 6. TOTALES GENERALES DESTACADOS (FUERA DEL CUADRO)
        # ---------------------------------------------------------------------
        pdf.set_fill_color(220, 230, 242)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.cell(130, 7, "TOTAL GENERAL EN BOLÍVARES (BS) RECAUDADOS:", 1, 0, "L", fill=True)
        pdf.set_font("Helvetica", "B", 10.5)
        pdf.cell(60, 7, formatear_bs(self.datos_turno['total_bs_consolidado']), 1, 1, "R", fill=True)

        pdf.set_fill_color(220, 242, 225)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.cell(130, 7, "TOTAL GENERAL EN DIVISAS ($) EN EFECTIVO:", 1, 0, "L", fill=True)
        pdf.set_font("Helvetica", "B", 10.5)
        pdf.cell(60, 7, f"${self.datos_turno['total_efectivo_usd']:.2f}", 1, 1, "R", fill=True)
        
        pdf.ln(12)

        # ---------------------------------------------------------------------
        # 7. BLOQUE DE FIRMAS
        # ---------------------------------------------------------------------
        pdf.set_font("Helvetica", "", 8)
        pos_y = pdf.get_y()
        pdf.line(20, pos_y, 80, pos_y)
        pdf.set_xy(20, pos_y + 1)
        pdf.cell(60, 4, "ENTREGADO POR", 0, 0, "C")

        pdf.line(130, pos_y, 190, pos_y)
        pdf.set_xy(130, pos_y + 1)
        pdf.cell(60, 4, "RECIBIDO POR (ADMINISTRACIÓN)", 0, 0, "C")

        # Guardar archivo
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        export_dir = os.path.join(base_dir, "reportes_exportados")
        os.makedirs(export_dir, exist_ok=True)

        filename = os.path.join(export_dir, f"cierre_{self.datos_turno['fecha']}_{self.datos_turno['turno']}.pdf")
        pdf.output(filename)
        os.system(f'start "" "{filename}"' if os.name == 'nt' else f'open "{filename}"')