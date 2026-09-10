"""
===============================================================================
SISTEMA DE GESTIÓN DE MOTELES - MOTEL PRO v2.0
Módulo: modules/reportes.py (CENTRO DE REPORTES: SAIME, P2P, CPP Y LIMPIEZA)
===============================================================================
"""

import os
import openpyxl
import customtkinter as ctk
from tkinter import messagebox
from tkcalendar import DateEntry
from fpdf import FPDF
from datetime import datetime

# IMPORTACIONES COMPLETAS Y UTILIZADAS AL 100%
from database.db_manager import (
    obtener_historial_saime, obtener_reporte_p2p, obtener_reporte_utilidad_inventario,
    obtener_historial_limpieza, obtener_tasa_bcv, formatear_bs, formatear_usd,
    obtener_ruta_recurso
)


# =============================================================================
# PDF: PLANILLA SAIME
# =============================================================================
class PDFPlanillaSAIME(FPDF):
    def __init__(self):
        super().__init__(orientation='L', unit='mm', format='A4')
        self.set_margins(10, 10, 10)
        self.set_auto_page_break(auto=True, margin=10)

    def header(self):
        logo_h = obtener_ruta_recurso("logo_hotel.png")
        logo_s = obtener_ruta_recurso("logo_saime.png")
        if os.path.exists(logo_h): self.image(logo_h, x=10, y=6, w=22)
        if os.path.exists(logo_s): self.image(logo_s, x=256, y=6, w=30)

        self.set_font("Arial", "B", 9)
        self.cell(0, 4, "REPÚBLICA BOLIVARIANA DE VENEZUELA", 0, 1, "C")
        self.cell(0, 4, "MINISTERIO DEL PODER POPULAR PARA RELACIONES INTERIORES, JUSTICIA Y PAZ", 0, 1, "C")
        self.set_font("Arial", "B", 10)
        self.cell(0, 4.5, "DIRECCIÓN GENERAL DE MIGRACIÓN Y EXTRANJERÍA - SAIME", 0, 1, "C")
        self.set_font("Arial", "B", 11)
        self.cell(0, 5, "INVERSIONES SAIBABA C.A. - MOTEL EL EDEN | RIF: J-30250227-6", 0, 1, "C")
        self.set_font("Arial", "I", 8)
        self.cell(0, 4, "REGISTRO DIARIO DE HUÉSPEDES Y CONTROL DE EXTRANJERÍA", 0, 1, "C")
        self.set_y(32)

        self.set_fill_color(220, 220, 220)
        self.set_font("Arial", "B", 8)
        self.cell(12, 7, "N° PER", 1, 0, "C", fill=True)
        self.cell(22, 7, "FECHA", 1, 0, "C", fill=True)
        self.cell(65, 7, "NOMBRE Y APELLIDO", 1, 0, "C", fill=True)
        self.cell(12, 7, "EDAD", 1, 0, "C", fill=True)
        self.cell(22, 7, "ESTADO CIVIL", 1, 0, "C", fill=True)
        self.cell(10, 7, "NC", 1, 0, "C", fill=True)
        self.cell(45, 7, "PROCEDENCIA", 1, 0, "C", fill=True)
        self.cell(27, 7, "CÉDULA", 1, 0, "C", fill=True)
        self.cell(62, 7, "DESTINO", 1, 0, "C", fill=True)
        self.ln()

    def footer(self):
        self.set_y(-12); self.set_font("Arial", "I", 8)
        self.cell(0, 8, f"Planilla Oficial para Inspección Policial / SAIME - Página {self.page_no()}", 0, 0, "C")


# =============================================================================
# PDF: AUDITORÍA PAGO MÓVIL (P2P)
# =============================================================================
class PDFReporteP2P(FPDF):
    def __init__(self):
        super().__init__(orientation='L', unit='mm', format='A4')
        self.set_margins(10, 10, 10)
        self.set_auto_page_break(auto=True, margin=12)

    def header(self):
        logo = obtener_ruta_recurso("logo_hotel.png")
        if os.path.exists(logo): self.image(logo, x=10, y=6, w=20)
        self.set_font("Arial", "B", 12)
        self.cell(0, 5, "INVERSIONES SAIBABA C.A. - MOTEL EL EDEN", 0, 1, "C")
        self.set_font("Arial", "B", 9)
        self.cell(0, 4.5, "RIF: J-30250227-6 | REPORTE DE AUDITORÍA DE TRANSACCIONES PAGO MÓVIL (P2P)", 0, 1, "C")
        self.set_y(26)

        self.set_fill_color(220, 230, 242)
        self.set_font("Arial", "B", 8)
        self.cell(30, 7, "FECHA / HORA", 1, 0, "C", fill=True)
        self.cell(28, 7, "HABITACIÓN", 1, 0, "C", fill=True)
        self.cell(38, 7, "CONCEPTO", 1, 0, "C", fill=True)
        self.cell(50, 7, "CLIENTE / TITULAR", 1, 0, "C", fill=True)
        self.cell(24, 7, "C.I. EMISOR", 1, 0, "C", fill=True)
        self.cell(28, 7, "TELÉFONO", 1, 0, "C", fill=True)
        self.cell(22, 7, "REF (P2P)", 1, 0, "C", fill=True)
        self.cell(32, 7, "MONTO (BS)", 1, 0, "C", fill=True)
        self.cell(25, 7, "MONTO ($)", 1, 0, "C", fill=True)
        self.ln()

    def footer(self):
        self.set_y(-12); self.set_font("Arial", "I", 8)
        self.cell(0, 8, f"Auditoría Contable Bancaria P2P - Página {self.page_no()}", 0, 0, "C")


# =============================================================================
# PDF: REPORTE DE UTILIDAD CPP (BIMONETARIO)
# =============================================================================
class PDFReporteUtilidadCPP(FPDF):
    def __init__(self):
        super().__init__(orientation='L', unit='mm', format='A4')
        self.set_margins(10, 10, 10)
        self.set_auto_page_break(auto=True, margin=12)

    def header(self):
        logo = obtener_ruta_recurso("logo_hotel.png")
        if os.path.exists(logo): self.image(logo, x=10, y=6, w=20)
        self.set_font("Arial", "B", 12)
        self.cell(0, 5, "INVERSIONES SAIBABA C.A. - MOTEL EL EDEN", 0, 1, "C")
        self.set_font("Arial", "B", 9)
        self.cell(0, 4.5, "RIF: J-30250227-6 | ESTADO DE RESULTADOS: UTILIDAD Y GANANCIAS MINI-BAR (CPP)", 0, 1, "C")
        self.set_y(26)

        self.set_fill_color(220, 242, 225)
        self.set_font("Arial", "B", 7.5)
        self.cell(42, 7, "PRODUCTO", 1, 0, "L", fill=True)
        self.cell(14, 7, "CANT", 1, 0, "C", fill=True)
        self.cell(24, 7, "COSTO ($)", 1, 0, "R", fill=True)
        self.cell(24, 7, "VENTA ($)", 1, 0, "R", fill=True)
        self.cell(28, 7, "TOT. COSTO ($)", 1, 0, "R", fill=True)
        self.cell(28, 7, "TOT. VENTA ($)", 1, 0, "R", fill=True)
        self.cell(38, 7, "TOT. VENTA (BS)", 1, 0, "R", fill=True)
        self.cell(28, 7, "UTILIDAD ($)", 1, 0, "R", fill=True)
        self.cell(34, 7, "UTILIDAD (BS)", 1, 0, "R", fill=True)
        self.cell(17, 7, "MARGEN", 1, 0, "C", fill=True)
        self.ln()

    def footer(self):
        self.set_y(-12); self.set_font("Arial", "I", 8)
        self.cell(0, 8, f"Auditoría Contable de Rentabilidad - Página {self.page_no()}", 0, 0, "C")


# =============================================================================
# PDF: REPORTE DE LIMPIEZAS Y CAMARERAS (HOUSEKEEPING SLA)
# =============================================================================
class PDFReporteLimpieza(FPDF):
    def __init__(self):
        super().__init__(orientation='L', unit='mm', format='A4')
        self.set_margins(10, 10, 10)
        self.set_auto_page_break(auto=True, margin=12)

    def header(self):
        logo = obtener_ruta_recurso("logo_hotel.png")
        if os.path.exists(logo): self.image(logo, x=10, y=6, w=20)
        self.set_font("Arial", "B", 12)
        self.cell(0, 5, "INVERSIONES SAIBABA C.A. - MOTEL EL EDEN", 0, 1, "C")
        self.set_font("Arial", "B", 9)
        self.cell(0, 4.5, "RIF: J-30250227-6 | REGISTRO DE LIMPIEZAS Y CONTROL DE CAMARERAS (SLA)", 0, 1, "C")
        self.set_y(26)

        self.set_fill_color(220, 230, 242)
        self.set_font("Arial", "B", 8)
        self.cell(32, 7, "FECHA / HORA LIMPIA", 1, 0, "C", fill=True)
        self.cell(25, 7, "HABITACIÓN", 1, 0, "C", fill=True)
        self.cell(60, 7, "CAMARERA RESPONSABLE", 1, 0, "L", fill=True)
        self.cell(25, 7, "TURNO", 1, 0, "C", fill=True)
        self.cell(50, 7, "HORA QUE PASÓ A SUCIA", 1, 0, "C", fill=True)
        self.cell(45, 7, "TIEMPO EN SUCIA (MIN)", 1, 0, "C", fill=True)
        self.cell(40, 7, "ESTADO CALIDAD", 1, 0, "C", fill=True)
        self.ln()

    def footer(self):
        self.set_y(-12); self.set_font("Arial", "I", 8)
        self.cell(0, 8, f"Auditoría de Camareras y Housekeeping - Página {self.page_no()}", 0, 0, "C")


# =============================================================================
# VISTA PRINCIPAL CON LAS 4 PESTAÑAS ACTIVAS
# =============================================================================
class FrameReportes(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#191715")
        self.controller = controller

        # TARJETA SUPERIOR DE CONTROL
        self.frame_top = ctk.CTkFrame(self, fg_color="#23201C", corner_radius=12, border_width=1, border_color="#36322C")
        self.frame_top.pack(fill="x", padx=15, pady=10)

        # FILA 1: TÍTULO Y SELECTOR DE LAS 4 PESTAÑAS
        f_row1 = ctk.CTkFrame(self.frame_top, fg_color="transparent")
        f_row1.pack(fill="x", padx=15, pady=(10, 6))

        ctk.CTkLabel(f_row1, text="📊 Centro de Reportes y Auditoría", font=("Georgia", 16, "bold"), text_color="#D4A343").pack(side="left")

        self.tab_selector = ctk.CTkSegmentedButton(
            f_row1, values=["📑 Extranjería (SAIME)", "💳 Auditoría P2P", "📈 Utilidad Mini-Bar", "🧹 Control Camareras"],
            selected_color="#D4A343", selected_hover_color="#B8892E", font=("Arial", 11, "bold"),
            command=lambda v: self.cargar_datos()
        )
        self.tab_selector.set("📑 Extranjería (SAIME)")
        self.tab_selector.pack(side="right")

        # FILA 2: FILTROS DE FECHA Y BOTONES DE EXPORTACIÓN
        f_row2 = ctk.CTkFrame(self.frame_top, fg_color="transparent")
        f_row2.pack(fill="x", padx=15, pady=(4, 10))

        f_fechas = ctk.CTkFrame(f_row2, fg_color="transparent")
        f_fechas.pack(side="left")

        ctk.CTkLabel(f_fechas, text="Desde:", font=("Arial", 11, "bold"), text_color="#A89F91").pack(side="left", padx=4)
        self.cal_inicio = DateEntry(f_fechas, date_pattern='yyyy-mm-dd')
        self.cal_inicio.pack(side="left", padx=4)

        ctk.CTkLabel(f_fechas, text="Hasta:", font=("Arial", 11, "bold"), text_color="#A89F91").pack(side="left", padx=6)
        self.cal_fin = DateEntry(f_fechas, date_pattern='yyyy-mm-dd')
        self.cal_fin.pack(side="left", padx=4)

        ctk.CTkButton(
            f_fechas, text="🔍 Consultar", fg_color="#3E342B", hover_color="#524539",
            text_color="#F4EFE6", width=95, height=30, font=("Arial", 11, "bold"),
            command=self.cargar_datos
        ).pack(side="left", padx=10)

        f_acciones = ctk.CTkFrame(f_row2, fg_color="transparent")
        f_acciones.pack(side="right")

        self.btn_export_pdf = ctk.CTkButton(
            f_acciones, text="📄 Exportar PDF", fg_color="#78281F", hover_color="#943126",
            text_color="#F4EFE6", width=120, height=30, font=("Arial", 11, "bold"),
            command=self.exportar_pdf_actual
        )
        self.btn_export_pdf.pack(side="left", padx=4)

        self.btn_export_excel = ctk.CTkButton(
            f_acciones, text="📊 Exportar Excel", fg_color="#1E5F38", hover_color="#2E7D32",
            text_color="#F4EFE6", width=120, height=30, font=("Arial", 11, "bold"),
            command=self.exportar_excel_actual
        )
        self.btn_export_excel.pack(side="left", padx=4)

        # CONTENEDOR SCROLLABLE
        self.scroll_data = ctk.CTkScrollableFrame(self, fg_color="#23201C", corner_radius=12, border_width=1, border_color="#36322C")
        self.scroll_data.pack(fill="both", expand=True, padx=15, pady=5)

        self.datos_saime = []
        self.datos_p2p = []
        self.datos_cpp = []
        self.datos_limpieza = []
        self.cargar_datos()

    def obtener_ruta_exportacion(self, file_name: str) -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        export_dir = os.path.join(base_dir, "reportes_exportados")
        os.makedirs(export_dir, exist_ok=True)
        return os.path.join(export_dir, file_name)

    def cargar_datos(self):
        for w in self.scroll_data.winfo_children(): w.destroy()

        f1 = self.cal_inicio.get_date().strftime("%Y-%m-%d")
        f2 = self.cal_fin.get_date().strftime("%Y-%m-%d")
        tipo = self.tab_selector.get()

        if "SAIME" in tipo:
            self.datos_saime = obtener_historial_saime(f1, f2)
            if not self.datos_saime:
                ctk.CTkLabel(self.scroll_data, text="No hay registros policiales en el rango seleccionado.", font=("Arial", 12, "italic"), text_color="#A89F91").pack(pady=30)
                return

            nro = 1
            for est in self.datos_saime:
                fecha_f = datetime.strptime(est["fecha_entrada"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
                card_t = ctk.CTkFrame(self.scroll_data, fg_color="#2D2924")
                card_t.pack(fill="x", pady=2, padx=5)
                txt_t = f"N° {nro} | {fecha_f} | {est['nombre']} {est['apellido']} | Edad: {est['edad']} | C.I: {est['cedula']} | Proc: {est['procedencia']} -> Dest: {est['destino']} [TITULAR]"
                ctk.CTkLabel(card_t, text=txt_t, font=("Arial", 11, "bold"), text_color="#D4A343").pack(side="left", padx=10, pady=5)
                nro += 1

                card_a = ctk.CTkFrame(self.scroll_data, fg_color="#26221E")
                card_a.pack(fill="x", pady=2, padx=5)
                txt_a = f"N° {nro} | {fecha_f} | {est['ac_nombre']} {est['ac_apellido']} | Edad: {est['ac_edad']} | C.I: {est['ac_cedula']} | Proc: {est['ac_procedencia']} -> Dest: {est['ac_destino']} [ACOMPAÑANTE]"
                ctk.CTkLabel(card_a, text=txt_a, font=("Arial", 11), text_color="#F4EFE6").pack(side="left", padx=10, pady=4)
                nro += 1

        elif "P2P" in tipo:
            self.datos_p2p = obtener_reporte_p2p(f1, f2)
            if not self.datos_p2p:
                ctk.CTkLabel(self.scroll_data, text="No hay transacciones Pago Móvil registradas.", font=("Arial", 12, "italic"), text_color="#A89F91").pack(pady=30)
                return

            for p in self.datos_p2p:
                card = ctk.CTkFrame(self.scroll_data, fg_color="#2D2924")
                card.pack(fill="x", pady=2, padx=5)
                txt_left = f"📅 {p['fecha']} | Hab: {p['hab_codigo']} | {p['concepto']} | Ref: {p['p2p_referencia']} | C.I: {p['p2p_ci']} | Telf: {p['p2p_telefono']}"
                txt_right = f"{formatear_bs(p['monto_bs'])} (${p['monto_usd']:.2f})"
                ctk.CTkLabel(card, text=txt_left, font=("Arial", 11), text_color="#F4EFE6").pack(side="left", padx=10, pady=6)
                ctk.CTkLabel(card, text=txt_right, font=("Arial", 11, "bold"), text_color="#7DCEA0").pack(side="right", padx=10, pady=6)

        elif "Utilidad" in tipo:
            self.datos_cpp = obtener_reporte_utilidad_inventario(f1, f2)
            if not self.datos_cpp:
                ctk.CTkLabel(self.scroll_data, text="No hay ventas de mercancía registradas en este período.", font=("Arial", 12, "italic"), text_color="#A89F91").pack(pady=30)
                return

            tot_ingreso = sum(d["ingreso_total_usd"] for d in self.datos_cpp)
            tot_costo = sum(d["costo_total_usd"] for d in self.datos_cpp)
            tot_utilidad = sum(d["utilidad_neta_usd"] for d in self.datos_cpp)
            tasa_act = obtener_tasa_bcv()

            f_res = ctk.CTkFrame(self.scroll_data, fg_color="#1A1815", corner_radius=8, border_width=1, border_color="#36312B")
            f_res.pack(fill="x", pady=5, padx=5)
            ctk.CTkLabel(
                f_res,
                text=f"Ventas: ${tot_ingreso:.2f} | Costo Total (CPP): ${tot_costo:.2f} | 💰 GANANCIA NETA: ${tot_utilidad:.2f} ({formatear_bs(tot_utilidad * tasa_act)})",
                font=("Georgia", 12, "bold"), text_color="#7DCEA0"
            ).pack(pady=8)

            for d in self.datos_cpp:
                card = ctk.CTkFrame(self.scroll_data, fg_color="#2D2924")
                card.pack(fill="x", pady=2, padx=5)
                txt_left = f"🛒 {d['producto']} | Vendidos: {d['unidades_vendidas']} un. | Ingreso: ${d['ingreso_total_usd']:.2f} | Costo CPP: ${d['costo_total_usd']:.2f}"
                txt_right = f"Ganancia: +${d['utilidad_neta_usd']:.2f} ({d['margen_pct']:.1f}%)"
                ctk.CTkLabel(card, text=txt_left, font=("Arial", 11), text_color="#F4EFE6").pack(side="left", padx=10, pady=6)
                ctk.CTkLabel(card, text=txt_right, font=("Arial", 11, "bold"), text_color="#D4A343").pack(side="right", padx=10, pady=6)

        else:
            # 🧹 PESTAÑA: CONTROL DE LIMPIEZAS Y CAMARERAS (UTILIZA LA FUNCIÓN)
            self.datos_limpieza = obtener_historial_limpieza(f1, f2)
            if not self.datos_limpieza:
                ctk.CTkLabel(self.scroll_data, text="No hay registros de limpieza en este rango de fechas.", font=("Arial", 12, "italic"), text_color="#A89F91").pack(pady=30)
                return

            for lim in self.datos_limpieza:
                card = ctk.CTkFrame(self.scroll_data, fg_color="#2D2924")
                card.pack(fill="x", pady=2, padx=5)

                minutos = lim["duracion_minutos"]
                alerta_tiempo = " (⚠️ Limpieza Lenta)" if minutos > 45 else " (✅ Tiempo Óptimo)"
                txt_left = f"🧹 Habitación: {lim['hab_codigo']} | Camarera: {lim['camarera']} (Turno {lim['turno']}) | Fecha: {lim['fecha_limpia']}"
                txt_right = f"Tardó: {minutos} min{alerta_tiempo}"

                ctk.CTkLabel(card, text=txt_left, font=("Arial", 11, "bold"), text_color="#F4EFE6").pack(side="left", padx=10, pady=6)
                ctk.CTkLabel(card, text=txt_right, font=("Arial", 10), text_color="#7DCEA0" if minutos <= 45 else "#E74C3C").pack(side="right", padx=10, pady=6)

    def exportar_pdf_actual(self):
        t = self.tab_selector.get()
        if "SAIME" in t: self.exportar_saime_pdf()
        elif "P2P" in t: self.exportar_p2p_pdf()
        elif "Utilidad" in t: self.exportar_cpp_pdf()
        else: self.exportar_limpieza_pdf()

    def exportar_excel_actual(self):
        t = self.tab_selector.get()
        if "SAIME" in t: self.exportar_saime_excel()
        elif "P2P" in t: self.exportar_p2p_excel()
        elif "Utilidad" in t: self.exportar_cpp_excel()
        else: self.exportar_limpieza_excel()

    # --- EXPORTACIONES SAIME, P2P, CPP Y LIMPIEZA ---
    def exportar_saime_pdf(self):
        if not self.datos_saime: return
        pdf = PDFPlanillaSAIME(); pdf.add_page(); pdf.set_font("Arial", "", 8)
        nro = 1
        for est in self.datos_saime:
            fecha_f = datetime.strptime(est["fecha_entrada"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
            
            # 1. Fila Titular (Siempre se imprime)
            pdf.cell(12, 6, str(nro), 1, 0, "C")
            pdf.cell(22, 6, fecha_f, 1, 0, "C")
            pdf.cell(65, 6, f"{est['nombre']} {est['apellido']}".upper()[:35], 1)
            pdf.cell(12, 6, str(est["edad"]), 1, 0, "C")
            pdf.cell(22, 6, str(est["estado_civil"])[0].upper(), 1, 0, "C")
            pdf.cell(10, 6, str(est["nacionalidad"]).upper(), 1, 0, "C")
            pdf.cell(45, 6, str(est["procedencia"]).upper()[:25], 1)
            pdf.cell(27, 6, str(est["cedula"]), 1, 0, "C")
            pdf.cell(62, 6, str(est["destino"]).upper()[:30], 1)
            pdf.ln()
            nro += 1

            # 2. Fila Acompañante (SOLO SE IMPRIME SI HUBO ACOMPAÑANTE REAL)
            if est.get("ac_nombre") and est.get("ac_cedula") and est["ac_nombre"].strip():
                pdf.cell(12, 6, str(nro), 1, 0, "C")
                pdf.cell(22, 6, fecha_f, 1, 0, "C")
                pdf.cell(65, 6, f"{est['ac_nombre']} {est['ac_apellido']}".upper()[:35], 1)
                pdf.cell(12, 6, str(est["ac_edad"]), 1, 0, "C")
                pdf.cell(22, 6, str(est["ac_estado_civil"])[0].upper() if est.get("ac_estado_civil") else "S", 1, 0, "C")
                pdf.cell(10, 6, str(est["ac_nacionalidad"]).upper() if est.get("ac_nacionalidad") else "V", 1, 0, "C")
                pdf.cell(45, 6, str(est["ac_procedencia"]).upper()[:25], 1)
                pdf.cell(27, 6, str(est["ac_cedula"]), 1, 0, "C")
                pdf.cell(62, 6, str(est["ac_destino"]).upper()[:30], 1)
                pdf.ln()
                nro += 1

        ruta = self.obtener_ruta_exportacion(f"planilla_saime_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        pdf.output(ruta); os.system(f'start "" "{ruta}"' if os.name == 'nt' else f'open "{ruta}"')

    def exportar_saime_excel(self):
        if not self.datos_saime: return
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Planilla SAIME"
        ws.append(["N° PER", "FECHA", "NOMBRE Y APELLIDO", "EDAD", "ESTADO CIVIL", "NAC", "PROCEDENCIA", "CÉDULA", "DESTINO"])
        nro = 1
        for est in self.datos_saime:
            fecha_f = datetime.strptime(est["fecha_entrada"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
            ws.append([nro, fecha_f, f"{est['nombre']} {est['apellido']}".upper(), est["edad"], str(est["estado_civil"])[0].upper(), est["nacionalidad"].upper(), est["procedencia"].upper(), est["cedula"], est["destino"].upper()]); nro += 1
            ws.append([nro, fecha_f, f"{est['ac_nombre']} {est['ac_apellido']}".upper(), est["ac_edad"], str(est["ac_estado_civil"])[0].upper(), est["ac_nacionalidad"].upper(), est["ac_procedencia"].upper(), est["ac_cedula"], est["ac_destino"].upper()]); nro += 1
        ruta = self.obtener_ruta_exportacion(f"planilla_saime_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        wb.save(ruta); os.system(f'start "" "{ruta}"' if os.name == 'nt' else f'open "{ruta}"')

    def exportar_p2p_pdf(self):
        if not self.datos_p2p: return
        pdf = PDFReporteP2P(); pdf.add_page(); pdf.set_font("Arial", "", 8)
        total_bs, total_usd = 0.0, 0.0
        for p in self.datos_p2p:
            pdf.cell(30, 6, str(p["fecha"])[:16], 1, 0, "C"); pdf.cell(28, 6, str(p["hab_codigo"])[:15], 1, 0, "C"); pdf.cell(38, 6, str(p["concepto"])[:20], 1); pdf.cell(50, 6, str(p["cliente_nombre"])[:26], 1); pdf.cell(24, 6, str(p["p2p_ci"]), 1, 0, "C"); pdf.cell(28, 6, str(p["p2p_telefono"]), 1, 0, "C"); pdf.cell(22, 6, str(p["p2p_referencia"]), 1, 0, "C"); pdf.cell(32, 6, formatear_bs(p["monto_bs"]), 1, 0, "R"); pdf.cell(25, 6, f"${p['monto_usd']:.2f}", 1, 0, "R"); pdf.ln()
            total_bs += p["monto_bs"]; total_usd += p["monto_usd"]
        pdf.ln(3); pdf.set_font("Arial", "B", 9); pdf.set_fill_color(220, 230, 242)
        pdf.cell(220, 7, "TOTAL GENERAL PAGO MÓVIL (P2P):", 1, 0, "L", fill=True); pdf.cell(32, 7, formatear_bs(total_bs), 1, 0, "R", fill=True); pdf.cell(25, 7, f"${total_usd:.2f}", 1, 1, "R", fill=True)
        ruta = self.obtener_ruta_exportacion(f"reporte_p2p_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        pdf.output(ruta); os.system(f'start "" "{ruta}"' if os.name == 'nt' else f'open "{ruta}"')

    def exportar_p2p_excel(self):
        if not self.datos_p2p: return
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Auditoría P2P"
        ws.append(["Fecha/Hora", "Habitación", "Concepto", "Cliente/Titular", "C.I. Emisor", "Teléfono", "Referencia", "Monto Bs", "Monto USD", "Turno", "Recepcionista"])
        for p in self.datos_p2p: ws.append([p["fecha"], p["hab_codigo"], p["concepto"], p["cliente_nombre"], p["p2p_ci"], p["p2p_telefono"], p["p2p_referencia"], p["monto_bs"], p["monto_usd"], p["turno"], p["recepcionista"]])
        ruta = self.obtener_ruta_exportacion(f"auditoria_p2p_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        wb.save(ruta); os.system(f'start "" "{ruta}"' if os.name == 'nt' else f'open "{ruta}"')

    def exportar_cpp_pdf(self):
        if not self.datos_cpp: return
        pdf = PDFReporteUtilidadCPP(); pdf.add_page(); pdf.set_font("Arial", "", 7.5)
        tot_ing_usd, tot_cos_usd, tot_util_usd = 0.0, 0.0, 0.0
        tot_ing_bs, tot_util_bs = 0.0, 0.0

        for d in self.datos_cpp:
            pdf.cell(42, 6, str(d["producto"])[:22], 1, 0, "L")
            pdf.cell(14, 6, str(d["unidades_vendidas"]), 1, 0, "C")
            pdf.cell(24, 6, f"${d['costo_prom_usd']:.2f}", 1, 0, "R")
            pdf.cell(24, 6, f"${d['precio_prom_usd']:.2f}", 1, 0, "R")
            pdf.cell(28, 6, f"${d['costo_total_usd']:.2f}", 1, 0, "R")
            pdf.cell(28, 6, f"${d['ingreso_total_usd']:.2f}", 1, 0, "R")
            pdf.cell(38, 6, formatear_bs(d["ingreso_total_bs"]), 1, 0, "R")
            pdf.cell(28, 6, f"${d['utilidad_neta_usd']:.2f}", 1, 0, "R")
            pdf.cell(34, 6, formatear_bs(d["utilidad_neta_bs"]), 1, 0, "R")
            pdf.cell(17, 6, f"{d['margen_pct']:.1f}%", 1, 0, "C")
            pdf.ln()

            tot_ing_usd += d["ingreso_total_usd"]
            tot_cos_usd += d["costo_total_usd"]
            tot_util_usd += d["utilidad_neta_usd"]
            tot_ing_bs += d["ingreso_total_bs"]
            tot_util_bs += d["utilidad_neta_bs"]

        margen_global_pct = (tot_util_usd / tot_ing_usd * 100) if tot_ing_usd > 0 else 0.0
        tot_cos_bs = tot_cos_usd * obtener_tasa_bcv()

        pdf.ln(3); pdf.set_font("Arial", "B", 8); pdf.set_fill_color(220, 242, 225)
        pdf.cell(104, 7, "TOTALES GENERALES EN DÓLARES ($):", 1, 0, "L", fill=True)
        pdf.cell(28, 7, f"${tot_cos_usd:.2f}", 1, 0, "R", fill=True)
        pdf.cell(28, 7, f"${tot_ing_usd:.2f}", 1, 0, "R", fill=True)
        pdf.cell(38, 7, "-", 1, 0, "C", fill=True)
        pdf.cell(28, 7, f"${tot_util_usd:.2f}", 1, 0, "R", fill=True)
        pdf.cell(34, 7, "-", 1, 0, "C", fill=True)
        pdf.cell(17, 7, f"{margen_global_pct:.1f}%", 1, 1, "C", fill=True)

        pdf.set_fill_color(220, 230, 242)
        pdf.cell(104, 7, "TOTALES GENERALES EN BOLÍVARES (BS):", 1, 0, "L", fill=True)
        pdf.cell(28, 7, "-", 1, 0, "C", fill=True)
        pdf.cell(28, 7, "-", 1, 0, "C", fill=True)
        pdf.cell(38, 7, formatear_bs(tot_ing_bs), 1, 0, "R", fill=True)
        pdf.cell(28, 7, "-", 1, 0, "C", fill=True)
        pdf.cell(34, 7, formatear_bs(tot_util_bs), 1, 0, "R", fill=True)
        pdf.cell(17, 7, f"{margen_global_pct:.1f}%", 1, 1, "C", fill=True)

        ruta = self.obtener_ruta_exportacion(f"utilidad_minibar_cpp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        pdf.output(ruta); os.system(f'start "" "{ruta}"' if os.name == 'nt' else f'open "{ruta}"')

    def exportar_cpp_excel(self):
        if not self.datos_cpp: return
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Utilidad Mini-Bar CPP"
        ws.append(["Producto", "Cant", "Costo CPP ($)", "Precio Venta ($)", "Total Costo ($)", "Total Venta ($)", "Total Venta (Bs)", "Utilidad Neta ($)", "Utilidad Neta (Bs)", "Margen %"])
        for d in self.datos_cpp:
            ws.append([d["producto"], d["unidades_vendidas"], d["costo_prom_usd"], d["precio_prom_usd"], d["costo_total_usd"], d["ingreso_total_usd"], d["ingreso_total_bs"], d["utilidad_neta_usd"], d["utilidad_neta_bs"], f"{d['margen_pct']:.1f}%"])
        ruta = self.obtener_ruta_exportacion(f"utilidad_minibar_cpp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        wb.save(ruta); os.system(f'start "" "{ruta}"' if os.name == 'nt' else f'open "{ruta}"')

    # --- NUEVA EXPORTACIÓN: CONTROL DE CAMARERAS Y ROTACIÓN ---
    def exportar_limpieza_pdf(self):
        if not self.datos_limpieza:
            messagebox.showwarning("Atención", "No hay registros de limpieza para exportar.")
            return

        pdf = PDFReporteLimpieza()
        pdf.add_page()
        pdf.set_font("Arial", "", 8)

        for l in self.datos_limpieza:
            pdf.cell(32, 6, str(l["fecha_limpia"])[:16], 1, 0, "C")
            pdf.cell(25, 6, str(l["hab_codigo"]), 1, 0, "C")
            pdf.cell(60, 6, str(l["camarera"])[:30], 1, 0, "L")
            pdf.cell(25, 6, str(l["turno"]), 1, 0, "C")
            pdf.cell(50, 6, str(l["fecha_sucia"])[:16] if l["fecha_sucia"] else "N/A", 1, 0, "C")
            pdf.cell(45, 6, f"{l['duracion_minutos']} minutos", 1, 0, "C")
            
            estado_cal = "ÓPTIMO" if l["duracion_minutos"] <= 45 else "DEMORADO"
            pdf.cell(40, 6, estado_cal, 1, 0, "C")
            pdf.ln()

        ruta = self.obtener_ruta_exportacion(f"control_camareras_sla_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        pdf.output(ruta)
        os.system(f'start "" "{ruta}"' if os.name == 'nt' else f'open "{ruta}"')

    def exportar_limpieza_excel(self):
        if not self.datos_limpieza: return
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Control Camareras SLA"
        ws.append(["Fecha Limpia", "Habitación", "Camarera", "Turno", "Hora Sucia", "Duración Minutos", "Evaluación SLA"])

        for l in self.datos_limpieza:
            eval_txt = "ÓPTIMO" if l["duracion_minutos"] <= 45 else "DEMORADO"
            ws.append([l["fecha_limpia"], l["hab_codigo"], l["camarera"], l["turno"], l["fecha_sucia"] or "N/A", l["duracion_minutos"], eval_txt])

        ruta = self.obtener_ruta_exportacion(f"control_camareras_sla_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        wb.save(ruta)
        os.system(f'start "" "{ruta}"' if os.name == 'nt' else f'open "{ruta}"')