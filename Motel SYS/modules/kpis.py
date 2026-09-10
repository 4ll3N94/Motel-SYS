"""
===============================================================================
SISTEMA DE GESTIÓN DE MOTELES
Módulo: modules/kpis.py (DASHBOARD DE KPIS, GRÁFICOS Y BUSINESS INTELLIGENCE)
===============================================================================
"""

import customtkinter as ctk
from tkcalendar import DateEntry
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from database.db_manager import (
    obtener_metricas_kpis, formatear_bs, formatear_usd, obtener_tasa_bcv
)


class FrameKPIs(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#191715")
        self.controller = controller

        # =====================================================================
        # 1. BARRA SUPERIOR DE FILTROS DE PERÍODO
        # =====================================================================
        self.frame_top = ctk.CTkFrame(self, fg_color="#23201C", corner_radius=12, border_width=1, border_color="#36322C")
        self.frame_top.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(self.frame_top, text="📈 Inteligencia de Negocios y Métricas (BI)", font=("Georgia", 16, "bold"), text_color="#D4A343").pack(side="left", padx=15, pady=10)

        f_fechas = ctk.CTkFrame(self.frame_top, fg_color="transparent")
        f_fechas.pack(side="right", padx=15)

        ctk.CTkLabel(f_fechas, text="Desde:", font=("Arial", 11, "bold"), text_color="#A89F91").pack(side="left", padx=4)
        self.cal_ini = DateEntry(f_fechas, date_pattern='yyyy-mm-dd')
        # Predeterminado: Primer día del mes actual
        self.cal_ini.set_date(datetime.now().date().replace(day=1))
        self.cal_ini.pack(side="left", padx=4)

        ctk.CTkLabel(f_fechas, text="Hasta:", font=("Arial", 11, "bold"), text_color="#A89F91").pack(side="left", padx=6)
        self.cal_fin = DateEntry(f_fechas, date_pattern='yyyy-mm-dd')
        self.cal_fin.pack(side="left", padx=4)

        ctk.CTkButton(
            f_fechas, text="🔄 Actualizar Gráficos", fg_color="#D4A343", hover_color="#B8892E",
            text_color="#191715", font=("Arial", 11, "bold"), command=self.cargar_dashboard
        ).pack(side="left", padx=10)

        # =====================================================================
        # 2. CONTENEDOR PRINCIPAL SCROLLABLE
        # =====================================================================
        self.scroll_dash = ctk.CTkScrollableFrame(self, fg_color="#191715")
        self.scroll_dash.pack(fill="both", expand=True, padx=15, pady=5)

        # Contenedores de Widgets
        self.frame_kpis = ctk.CTkFrame(self.scroll_dash, fg_color="transparent")
        self.frame_kpis.pack(fill="x", pady=(0, 10))

        self.frame_graficos = ctk.CTkFrame(self.scroll_dash, fg_color="transparent")
        self.frame_graficos.pack(fill="both", expand=True)
        self.frame_graficos.grid_columnconfigure((0, 1), weight=1)

        self.canvas_list = []
        self.cargar_dashboard()

    def cargar_dashboard(self):
        # Limpiar gráficos anteriores
        for c in self.canvas_list:
            c.get_tk_widget().destroy()
        self.canvas_list.clear()

        for w in self.frame_kpis.winfo_children():
            w.destroy()

        f1 = self.cal_ini.get_date().strftime("%Y-%m-%d")
        f2 = self.cal_fin.get_date().strftime("%Y-%m-%d")

        data = obtener_metricas_kpis(f1, f2)

        # =====================================================================
        # RENDER: TARJETAS DE KPIS SUPERIORES
        # =====================================================================
        self.frame_kpis.grid_columnconfigure((0, 1, 2, 3), weight=1)

        def crear_tarjeta_kpi(col, titulo, valor_primario, valor_secundario, color_acento):
            card = ctk.CTkFrame(self.frame_kpis, fg_color="#23201C", corner_radius=10, border_width=1, border_color="#36322C")
            card.grid(row=0, column=col, padx=5, sticky="nsew")
            ctk.CTkLabel(card, text=titulo, font=("Arial", 10, "bold"), text_color="#A89F91").pack(pady=(8, 2))
            ctk.CTkLabel(card, text=valor_primario, font=("Georgia", 16, "bold"), text_color=color_acento).pack(pady=1)
            ctk.CTkLabel(card, text=valor_secundario, font=("Arial", 9), text_color="#F4EFE6").pack(pady=(0, 8))

        crear_tarjeta_kpi(0, "💰 INGRESOS TOTALES", f"${data['total_ingresos_usd']:.2f}", formatear_bs(data['total_ingresos_bs']), "#7DCEA0")
        crear_tarjeta_kpi(1, "🏨 OCUPACIONES / ESTANCIAS", f"{data['total_estancias']} Alquileres", "Frecuencia en Período", "#D4A343")
        crear_tarjeta_kpi(2, "🎫 TICKET PROMEDIO", f"${data['ticket_promedio_usd']:.2f}", "Gasto Promedio / Hab", "#5DADE2")
        crear_tarjeta_kpi(3, "🛒 GANANCIA MINI-BAR (CPP)", f"${data['utilidad_minibar_usd']:.2f}", "Utilidad Neta Descontando Costos", "#AF7AC5")

        # =====================================================================
        # RENDER: GRÁFICOS CON MATPLOTLIB (TEMA OSCURO CÁLIDO)
        # =====================================================================
        plt.style.use('dark_background')

        # --- GRÁFICO 1: ROTACIÓN POR HABITACIÓN ---
        fig1, ax1 = plt.subplots(figsize=(4.5, 3.2), facecolor='#23201C')
        ax1.set_facecolor('#2D2924')
        if data['rotacion_hab']:
            habs = list(data['rotacion_hab'].keys())
            cantidades = list(data['rotacion_hab'].values())
            ax1.bar(habs, cantidades, color='#D4A343', edgecolor='#B8892E')
            ax1.set_title("Rotación por Habitación (Alquileres)", color='#F4EFE6', fontsize=10, fontweight='bold')
            ax1.tick_params(colors='#F4EFE6', labelsize=8)
            ax1.grid(color='#3D372F', linestyle='--', linewidth=0.5, alpha=0.7)
        else:
            ax1.text(0.5, 0.5, "Sin datos en el período", color='#A89F91', ha='center', va='center')
            ax1.set_title("Rotación por Habitación", color='#F4EFE6', fontsize=10)

        fig1.tight_layout()
        canvas1 = FigureCanvasTkAgg(fig1, master=self.frame_graficos)
        canvas1.draw()
        canvas1.get_tk_widget().grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.canvas_list.append(canvas1)

        # --- GRÁFICO 2: CURVA DE HORAS PICO ---
        fig2, ax2 = plt.subplots(figsize=(4.5, 3.2), facecolor='#23201C')
        ax2.set_facecolor('#2D2924')
        horas = list(data['horas_pico'].keys())
        afluencia = list(data['horas_pico'].values())
        ax2.plot(horas, afluencia, color='#7DCEA0', marker='o', linewidth=2, markersize=4)
        ax2.fill_between(horas, afluencia, color='#7DCEA0', alpha=0.15)
        ax2.set_title("Curva de Horas Pico (Afluencia 24h)", color='#F4EFE6', fontsize=10, fontweight='bold')
        ax2.set_xlabel("Hora del Día (00 a 23 hrs)", color='#A89F91', fontsize=8)
        ax2.tick_params(colors='#F4EFE6', labelsize=8)
        ax2.grid(color='#3D372F', linestyle='--', linewidth=0.5, alpha=0.7)

        fig2.tight_layout()
        canvas2 = FigureCanvasTkAgg(fig2, master=self.frame_graficos)
        canvas2.draw()
        canvas2.get_tk_widget().grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        self.canvas_list.append(canvas2)

        # --- GRÁFICO 3: MÉTODOS DE PAGO (DONA) ---
        fig3, ax3 = plt.subplots(figsize=(4.5, 3.2), facecolor='#23201C')
        ax3.set_facecolor('#23201C')
        metodos_filtrados = {k: v for k, v in data['metodos_pago'].items() if v > 0}
        if metodos_filtrados:
            colores_pie = ['#7DCEA0', '#5DADE2', '#D4A343', '#E59866']
            wedges, texts, autotexts = ax3.pie(
                metodos_filtrados.values(), labels=metodos_filtrados.keys(),
                autopct='%1.1f%%', colors=colores_pie[:len(metodos_filtrados)],
                wedgeprops=dict(width=0.45, edgecolor='#23201C'), textprops=dict(color='#F4EFE6', fontsize=7)
            )
            for autotext in autotexts:
                autotext.set_color('#191715')
                autotext.set_fontweight('bold')
            ax3.set_title("Distribución de Ingresos por Método", color='#F4EFE6', fontsize=10, fontweight='bold')
        else:
            ax3.text(0.5, 0.5, "Sin transacciones", color='#A89F91', ha='center', va='center')
            ax3.set_title("Métodos de Pago", color='#F4EFE6', fontsize=10)

        fig3.tight_layout()
        canvas3 = FigureCanvasTkAgg(fig3, master=self.frame_graficos)
        canvas3.draw()
        canvas3.get_tk_widget().grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        self.canvas_list.append(canvas3)

        # --- GRÁFICO 4: TOP 5 PRODUCTOS MÁS VENDIDOS ---
        fig4, ax4 = plt.subplots(figsize=(4.5, 3.2), facecolor='#23201C')
        ax4.set_facecolor('#2D2924')
        if data['top_productos']:
            prods = [p[0][:15] for p in data['top_productos']]
            unidades = [p[1] for p in data['top_productos']]
            ax4.barh(prods, unidades, color='#5DADE2', edgecolor='#2E86C1')
            ax4.set_title("Top 5 Productos más Vendidos", color='#F4EFE6', fontsize=10, fontweight='bold')
            ax4.tick_params(colors='#F4EFE6', labelsize=8)
            ax4.grid(color='#3D372F', linestyle='--', linewidth=0.5, alpha=0.7)
            ax4.invert_yaxis()
        else:
            ax4.text(0.5, 0.5, "Sin ventas de mini-bar", color='#A89F91', ha='center', va='center')
            ax4.set_title("Top Productos Mini-Bar", color='#F4EFE6', fontsize=10)

        fig4.tight_layout()
        canvas4 = FigureCanvasTkAgg(fig4, master=self.frame_graficos)
        canvas4.draw()
        canvas4.get_tk_widget().grid(row=1, column=1, padx=5, pady=5, sticky="nsew")
        self.canvas_list.append(canvas4)

        plt.close('all')  # Liberar memoria de Matplotlib