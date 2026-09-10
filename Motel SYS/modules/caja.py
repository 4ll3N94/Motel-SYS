"""
===============================================================================
SISTEMA DE GESTIÓN DE MOTELES
Módulo: modules/caja.py (CIERRE DE CAJA: HABITACIONES, MINI-BAR Y DAÑOS)
===============================================================================
"""

import os
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from fpdf import FPDF

from database.db_manager import (
    verificar_cierre_existente, registrar_cierre_turno, obtener_detalle_cierre_turno,
    registrar_auditoria, formatear_bs, formatear_usd, obtener_ruta_recurso
)


class PDFCierreContable(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_margins(10, 10, 10)
        self.set_auto_page_break(auto=True, margin=12)

    def header(self):
        logo = obtener_ruta_recurso("logo_hotel.png")
        if os.path.exists(logo):
            self.image(logo, x=10, y=8, w=20)

        self.set_font("Arial", "B", 12)
        self.cell(0, 5, "INVERSIONES SAIBABA C.A.", 0, 1, "C")
        self.set_font("Arial", "B", 9)
        self.cell(0, 4, "RIF: J-30250227-6", 0, 1, "C")
        self.set_font("Arial", "B", 11)
        self.cell(0, 5, "MOTEL EL EDEN", 0, 1, "C")
        self.set_font("Arial", "B", 10)
        self.cell(0, 5, "COMPROBANTE DETALLADO DE CIERRE DE CAJA", 0, 1, "C")

        self.set_draw_color(180, 180, 180)
        self.line(10, 30, 200, 30)
        self.set_y(34)

    def footer(self):
        self.set_y(-12)
        self.set_font("Arial", "I", 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 8, f"Documento Contable y de Auditoría Interna - Página {self.page_no()}", 0, 0, "C")


class FrameCaja(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#191715")
        self.controller = controller

        ctk.CTkLabel(self, text="Conciliación y Cierre de Caja del Turno", font=("Georgia", 18, "bold"), text_color="#D4A343").pack(pady=10)

        # Barra Superior
        frame_top = ctk.CTkFrame(self, fg_color="#23201C", corner_radius=12, border_width=1, border_color="#36322C")
        frame_top.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(frame_top, text="Turno:", font=("Arial", 11, "bold"), text_color="#A89F91").pack(side="left", padx=10)
        self.c_turno = ctk.CTkComboBox(frame_top, values=["MAÑANA", "NOCHE"], command=lambda v: self.cargar_detalle())
        self.c_turno.pack(side="left", padx=5)

        ctk.CTkButton(frame_top, text="🔄 Recalcular Turno", fg_color="#3E342B", hover_color="#524539", text_color="#F4EFE6", command=self.cargar_detalle).pack(side="left", padx=10)
        ctk.CTkButton(frame_top, text="🔒 Registrar Cierre y Generar PDF", fg_color="#D4A343", hover_color="#B8892E", text_color="#191715", font=("Arial", 12, "bold"), command=self.cerrar_turno).pack(side="right", padx=10, pady=8)

        # Panel Resumen
        self.frame_resumen = ctk.CTkFrame(self, fg_color="#23201C", corner_radius=12, border_width=1, border_color="#36322C")
        self.frame_resumen.pack(fill="x", padx=15, pady=10)

        self.lbl_usd = ctk.CTkLabel(self.frame_resumen, text="TOTAL EFECTIVO USD ($): $0.00", font=("Arial", 13, "bold"), text_color="#7DCEA0")
        self.lbl_usd.pack(pady=2)

        self.lbl_bs = ctk.CTkLabel(self.frame_resumen, text="TOTAL BOLÍVARES (Bs): 0,00 Bs", font=("Arial", 13, "bold"), text_color="#D4A343")
        self.lbl_bs.pack(pady=2)

        self.lbl_desglose_bs = ctk.CTkLabel(self.frame_resumen, text="Efectivo Bs: 0,00 | Pago Móvil: 0,00 | Punto: 0,00", font=("Arial", 11), text_color="#A89F91")
        self.lbl_desglose_bs.pack(pady=2)

        # Scroll de Operaciones
        self.scroll_detalle = ctk.CTkScrollableFrame(self, fg_color="#191715", label_text="Resumen de Operaciones del Turno")
        self.scroll_detalle.pack(fill="both", expand=True, padx=15, pady=10)

        self.datos_turno = None
        self.cargar_detalle()

    def cargar_detalle(self):
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        turno = self.c_turno.get()

        self.datos_turno = obtener_detalle_cierre_turno(fecha_hoy, turno)
        self.datos_turno["recepcionista"] = self.controller.usuario_actual["usuario"]

        self.lbl_usd.configure(text=f"TOTAL EFECTIVO USD ($): ${self.datos_turno['total_efectivo_usd']:.2f}")
        self.lbl_bs.configure(text=f"TOTAL BOLÍVARES (Bs): {formatear_bs(self.datos_turno['total_bs_consolidado'])}")
        self.lbl_desglose_bs.configure(
            text=f"Efectivo Bs: {formatear_bs(self.datos_turno['total_efectivo_bs'])} | Pago Móvil: {formatear_bs(self.datos_turno['total_p2p_bs'])} | Punto: {formatear_bs(self.datos_turno['total_punto_bs'])}"
        )

        for w in self.scroll_detalle.winfo_children():
            w.destroy()

        # 1. Habitaciones
        ctk.CTkLabel(self.scroll_detalle, text="🏨 Habitaciones Alquiladas:", font=("Georgia", 12, "bold"), text_color="#D4A343").pack(anchor="w", padx=5, pady=(5, 2))
        for hab in self.datos_turno["habitaciones"]:
            card = ctk.CTkFrame(self.scroll_detalle, fg_color="#2D2924")
            card.pack(fill="x", pady=2, padx=5)
            txt = f"Hab: {hab['habitacion']} | Veces: {hab['cantidad']} | Total $: ${hab['total_usd']:.2f} | Total Bs: {formatear_bs(hab['total_bs'])}"
            ctk.CTkLabel(card, text=txt, font=("Arial", 11), text_color="#F4EFE6").pack(side="left", padx=10, pady=5)

        # 2. Mercancía
        ctk.CTkLabel(self.scroll_detalle, text="🛒 Mercancía Vendida:", font=("Georgia", 12, "bold"), text_color="#7DCEA0").pack(anchor="w", padx=5, pady=(10, 2))
        for m in self.datos_turno["mercancia"]:
            card = ctk.CTkFrame(self.scroll_detalle, fg_color="#2D2924")
            card.pack(fill="x", pady=2, padx=5)
            txt = f"Prod: {m['producto']} | Cantidad: {m['cantidad']} | Total $: ${m['total_usd']:.2f} | Total Bs: {formatear_bs(m['total_bs'])}"
            ctk.CTkLabel(card, text=txt, font=("Arial", 11), text_color="#F4EFE6").pack(side="left", padx=10, pady=5)

        # 3. NUEVO: Daños Cobrados en Pantalla
        if self.datos_turno["danos"]:
            ctk.CTkLabel(self.scroll_detalle, text="⚡ Daños Cobrados a Huéspedes:", font=("Georgia", 12, "bold"), text_color="#E74C3C").pack(anchor="w", padx=5, pady=(10, 2))
            for d in self.datos_turno["danos"]:
                card = ctk.CTkFrame(self.scroll_detalle, fg_color="#2D2924")
                card.pack(fill="x", pady=2, padx=5)
                txt = f"Hab: {d['hab_codigo']} | Huésped: {d['cliente_nombre']} (C.I: {d['cliente_ci']}) | {d['concepto_dano']} | ${d['monto_usd']:.2f} ({formatear_bs(d['monto_bs'])}) [{d['metodo']}]"
                ctk.CTkLabel(card, text=txt, font=("Arial", 11), text_color="#F4EFE6").pack(side="left", padx=10, pady=5)

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

            # Notificación Multicanal Compatible con WhatsApp
            try:
                from modules.notificaciones import disparar_notificacion_multicanal
                asunto_notif = f"CIERRE DE CAJA - Turno {turno} ({fecha})"
                msg_notif = (
                    f"🏨 <b>MOTEL EL EDEN - CIERRE DE TURNO</b>\n"
                    f"📅 <b>Fecha:</b> {fecha} | <b>Turno:</b> {turno}\n"
                    f"👤 <b>Responsable:</b> {usr_act}\n\n"
                    f"💵 <b>TOTAL EFECTIVO USD:</b> ${datos_guardar['total_usd']:.2f}\n"
                    f"💰 <b>TOTAL BOLÍVARES:</b> {formatear_bs(datos_guardar['total_bs'])}\n"
                    f"📱 <b>Pago Móvil:</b> {formatear_bs(datos_guardar['total_p2p'])}\n"
                    f"💳 <b>Punto de Venta:</b> {formatear_bs(datos_guardar['total_punto'])}\n"
                )
                disparar_notificacion_multicanal(asunto_notif, msg_notif)
            except Exception as e:
                print(f"Error enviando notificación de cierre: {e}")

            self.exportar_pdf_cierre()
            messagebox.showinfo("Éxito", "Cierre contable registrado, notificado y exportado a PDF.")
        else:
            messagebox.showerror("Error", "No se pudo registrar el cierre.")

    def formatear_metodos_str(self, usd: float, bs: float, p2p: float, punto: float) -> str:
        partes = []
        if usd > 0: partes.append(f"${usd:.2f}")
        if bs > 0: partes.append(f"{bs:,.2f}Bs".replace(",", "X").replace(".", ",").replace("X", "."))
        if p2p > 0: partes.append(f"{p2p:,.2f}P2P".replace(",", "X").replace(".", ",").replace("X", "."))
        if punto > 0: partes.append(f"{punto:,.2f}Punto".replace(",", "X").replace(".", ",").replace("X", "."))
        return " / ".join(partes) if partes else "0,00"

    # =========================================================================
    # FORMATEADOR DE MÉTODOS DE PAGO CON ESPACIADO ELEGANTE
    # =========================================================================
    def formatear_metodos_str(self, usd: float, bs: float, p2p: float, punto: float) -> str:
        """Construye una cadena contable compacta y legible sin amontonar textos."""
        partes = []
        if usd > 0:
            partes.append(f"${usd:.2f}")
        if bs > 0:
            partes.append(f"{bs:,.2f} Bs".replace(",", "X").replace(".", ",").replace("X", "."))
        if p2p > 0:
            partes.append(f"{p2p:,.2f} P2P".replace(",", "X").replace(".", ",").replace("X", "."))
        if punto > 0:
            partes.append(f"{punto:,.2f} Punto".replace(",", "X").replace(".", ",").replace("X", "."))
        return " / ".join(partes) if partes else "0,00"

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
        pdf.set_font("Arial", "B", 9)
        pdf.cell(35, 5, "FECHA DE CIERRE:", 0, 0, "L")
        pdf.set_font("Arial", "", 9)
        pdf.cell(60, 5, self.datos_turno['fecha'], 0, 0, "L")

        pdf.set_font("Arial", "B", 9)
        pdf.cell(20, 5, "TURNO:", 0, 0, "L")
        pdf.set_font("Arial", "", 9)
        pdf.cell(75, 5, self.datos_turno['turno'], 0, 1, "L")

        pdf.set_font("Arial", "B", 9)
        pdf.cell(35, 5, "RECEPCIONISTA:", 0, 0, "L")
        pdf.set_font("Arial", "", 9)
        pdf.cell(60, 5, self.datos_turno['recepcionista'].upper(), 0, 0, "L")

        pdf.set_font("Arial", "B", 9)
        pdf.cell(20, 5, "TASA BCV:", 0, 0, "L")
        pdf.set_font("Arial", "", 9)
        pdf.cell(75, 5, f"{self.datos_turno['tasa_bcv']:.2f} Bs / USD", 0, 1, "L")
        pdf.ln(4)

        # ---------------------------------------------------------------------
        # 2. CUADRO 1: RESUMEN DE HABITACIONES (Ancho Total: 190 mm)
        # ---------------------------------------------------------------------
        pdf.set_fill_color(220, 220, 220)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(28, 6, "HABITACIÓN", 1, 0, "C", fill=True)
        pdf.cell(14, 6, "CANT", 1, 0, "C", fill=True)
        pdf.cell(52, 6, "SUBTOTAL (ALQUILER)", 1, 0, "C", fill=True)
        pdf.cell(42, 6, "MERCANCÍA", 1, 0, "C", fill=True)
        pdf.cell(30, 6, "TOTAL BS", 1, 0, "C", fill=True)
        pdf.cell(24, 6, "TOTAL $", 1, 0, "C", fill=True)
        pdf.ln()

        pdf.set_font("Arial", "", 7.5)
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
        pdf.set_font("Arial", "B", 8)
        pdf.cell(48, 6, "PRODUCTO", 1, 0, "C", fill=True)
        pdf.cell(16, 6, "CANT", 1, 0, "C", fill=True)
        pdf.cell(66, 6, "SUBTOTAL (MÉTODOS)", 1, 0, "C", fill=True)
        pdf.cell(34, 6, "TOTAL BS", 1, 0, "C", fill=True)
        pdf.cell(26, 6, "TOTAL $", 1, 0, "C", fill=True)
        pdf.ln()

        pdf.set_font("Arial", "", 7.5)
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
        # 4. CUADRO 3: COBROS POR DAÑOS A HUÉSPEDES (REDISEÑADO SIN CORTES)
        # ---------------------------------------------------------------------
        if self.datos_turno["danos"]:
            pdf.set_fill_color(245, 230, 230)  # Fondo rojizo suave
            pdf.set_font("Arial", "B", 8)
            pdf.cell(18, 6, "HAB", 1, 0, "C", fill=True)
            pdf.cell(46, 6, "HUÉSPED RESPONSABLE", 1, 0, "L", fill=True)
            pdf.cell(56, 6, "CONCEPTO DEL DAÑO", 1, 0, "L", fill=True)
            pdf.cell(26, 6, "MÉTODO", 1, 0, "C", fill=True)
            pdf.cell(24, 6, "MONTO (BS)", 1, 0, "R", fill=True)
            pdf.cell(20, 6, "MONTO ($)", 1, 0, "R", fill=True)
            pdf.ln()

            pdf.set_font("Arial", "", 7.5)
            for d in self.datos_turno["danos"]:
                # Formateo limpio del método sin saturar la celda
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

                # Texto completo de Huésped con Cédula
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
        pdf.set_font("Arial", "B", 9)
        pdf.cell(190, 6, "CONCILIACIÓN POR MÉTODO DE PAGO", 1, 1, "C", fill=True)

        pdf.set_font("Arial", "", 8.5)
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
        pdf.set_font("Arial", "B", 9.5)
        pdf.cell(130, 7, "TOTAL GENERAL EN BOLÍVARES (BS) RECAUDADOS:", 1, 0, "L", fill=True)
        pdf.set_font("Arial", "B", 10.5)
        pdf.cell(60, 7, formatear_bs(self.datos_turno['total_bs_consolidado']), 1, 1, "R", fill=True)

        pdf.set_fill_color(220, 242, 225)
        pdf.set_font("Arial", "B", 9.5)
        pdf.cell(130, 7, "TOTAL GENERAL EN DIVISAS ($) EN EFECTIVO:", 1, 0, "L", fill=True)
        pdf.set_font("Arial", "B", 10.5)
        pdf.cell(60, 7, f"${self.datos_turno['total_efectivo_usd']:.2f}", 1, 1, "R", fill=True)
        
        pdf.ln(12)

        # ---------------------------------------------------------------------
        # 7. BLOQUE DE FIRMAS
        # ---------------------------------------------------------------------
        pdf.set_font("Arial", "", 8)
        pos_y = pdf.get_y()
        pdf.line(20, pos_y, 80, pos_y)
        pdf.set_xy(20, pos_y + 1)
        pdf.cell(60, 4, "ENTREGADA", 0, 0, "C")

        pdf.line(130, pos_y, 190, pos_y)
        pdf.set_xy(130, pos_y + 1)
        pdf.cell(60, 4, "RECIBE", 0, 0, "C")

        # Guardar archivo
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        export_dir = os.path.join(base_dir, "reportes_exportados")
        os.makedirs(export_dir, exist_ok=True)

        filename = os.path.join(export_dir, f"cierre_{self.datos_turno['fecha']}_{self.datos_turno['turno']}.pdf")
        pdf.output(filename)
        os.system(f'start "" "{filename}"' if os.name == 'nt' else f'open "{filename}"')