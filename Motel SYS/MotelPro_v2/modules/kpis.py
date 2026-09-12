"""
===============================================================================
SISTEMA DE GESTIÓN DE MOTELES (EXECUTIVE SUITE)
Módulo: modules/kpis.py (DASHBOARD DE BUSINESS INTELLIGENCE & ANALYTICS)
Diseño: Dark Luxury con Acabado Profesional y Gráficos Vectoriales
===============================================================================
"""

import customtkinter as ctk
from tkcalendar import DateEntry
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patches as patches

from database.db_manager import (
    obtener_metricas_kpis, formatear_bs, formatear_usd, obtener_tasa_bcv
)


class FrameKPIs(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#11100E")
        self.controller = controller

        # Colores de Marca y UI Profesional
        self.BG_MAIN = "#11100E"
        self.BG_PANEL = "#1A1816"
        self.BG_CARD = "#211E1B"
        self.BORDER_COLOR = "#332E29"
        self.ACCENT_GOLD = "#D4AF37"
        self.TEXT_PRIMARY = "#F5EFEB"
        self.TEXT_MUTED = "#8E8880"
        self.ACCENT_GREEN = "#2ECC71"
        self.ACCENT_BLUE = "#3498DB"
        self.ACCENT_PURPLE = "#9B59B6"

        # =====================================================================
        # 1. HEADER Y CONTROL DE FILTRO TEMPORAL
        # =====================================================================
        self.frame_header = ctk.CTkFrame(
            self, fg_color=self.BG_PANEL, corner_radius=14,
            border_width=1, border_color=self.BORDER_COLOR
        )
        self.frame_header.pack(fill="x", padx=20, pady=(15, 10))

        # Título y subtítulo
        f_titulos = ctk.CTkFrame(self.frame_header, fg_color="transparent")
        f_titulos.pack(side="left", padx=20, pady=12)

        ctk.CTkLabel(
            f_titulos, text="INTELIGENCIA DE NEGOCIOS Y RENDIMIENTO",
            font=("Montserrat", 16, "bold"), text_color=self.ACCENT_GOLD
        ).pack(anchor="w")

        ctk.CTkLabel(
            f_titulos, text="Métricas consolidadas de caja, ocupación y ventas de piso en tiempo real",
            font=("Arial", 10), text_color=self.TEXT_MUTED
        ).pack(anchor="w")

        # Controles de Fecha a la derecha
        f_fechas = ctk.CTkFrame(self.frame_header, fg_color="transparent")
        f_fechas.pack(side="right", padx=20, pady=12)

        ctk.CTkLabel(f_fechas, text="Rango:", font=("Arial", 11, "bold"), text_color=self.TEXT_MUTED).pack(side="left", padx=4)
        
        self.cal_ini = DateEntry(f_fechas, date_pattern='yyyy-mm-dd', background="#211E1B", foreground="white", headersbackground="#D4AF37")
        self.cal_ini.set_date(datetime.now().date().replace(day=1))
        self.cal_ini.pack(side="left", padx=4)

        ctk.CTkLabel(f_fechas, text="➔", font=("Arial", 11), text_color=self.TEXT_MUTED).pack(side="left", padx=4)

        self.cal_fin = DateEntry(f_fechas, date_pattern='yyyy-mm-dd', background="#211E1B", foreground="white", headersbackground="#D4AF37")
        self.cal_fin.pack(side="left", padx=4)

        self.btn_refresh = ctk.CTkButton(
            f_fechas, text="Analizar Período", fg_color=self.ACCENT_GOLD,
            hover_color="#B89228", text_color="#11100E",
            font=("Arial", 11, "bold"), height=32, corner_radius=8,
            command=self.cargar_dashboard
        )
        self.btn_refresh.pack(side="left", padx=(12, 0))

        # =====================================================================
        # 2. CONTENEDOR PRINCIPAL SCROLLABLE
        # =====================================================================
        self.scroll_dash = ctk.CTkScrollableFrame(self, fg_color=self.BG_MAIN)
        self.scroll_dash.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        # Panel de tarjetas KPI
        self.frame_kpis = ctk.CTkFrame(self.scroll_dash, fg_color="transparent")
        self.frame_kpis.pack(fill="x", pady=(0, 15))

        # Panel de gráficos en rejilla 2x2
        self.frame_graficos = ctk.CTkFrame(self.scroll_dash, fg_color="transparent")
        self.frame_graficos.pack(fill="both", expand=True)
        self.frame_graficos.grid_columnconfigure((0, 1), weight=1)

        self.canvas_list = []
        self.cargar_dashboard()

    def cargar_dashboard(self):
        # 1. Limpieza rigurosa de memoria gráfica
        for c in self.canvas_list:
            c.get_tk_widget().destroy()
        self.canvas_list.clear()

        for w in self.frame_kpis.winfo_children():
            w.destroy()

        f1 = self.cal_ini.get_date().strftime("%Y-%m-%d")
        f2 = self.cal_fin.get_date().strftime("%Y-%m-%d")

        data = obtener_metricas_kpis(f1, f2)
        tasa = obtener_tasa_bcv()

        # =====================================================================
        # TARJETAS DE KPIS MODERNAS CON BADGES DE CONVERSIÓN
        # =====================================================================
        self.frame_kpis.grid_columnconfigure((0, 1, 2, 3), weight=1)

        def render_kpi(col, titulo, valor_primario, sub_texto, tag_text, color_tag, icono=""):
            card = ctk.CTkFrame(
                self.frame_kpis, fg_color=self.BG_CARD, corner_radius=12,
                border_width=1, border_color=self.BORDER_COLOR
            )
            card.grid(row=0, column=col, padx=6, sticky="nsew")

            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=14, pady=(12, 4))

            ctk.CTkLabel(top_row, text=f"{icono} {titulo}".strip(), font=("Montserrat", 9, "bold"), text_color=self.TEXT_MUTED).pack(side="left")
            
            # Badge
            badge = ctk.CTkFrame(top_row, fg_color="#181614", corner_radius=6, border_width=1, border_color=color_tag)
            badge.pack(side="right")
            ctk.CTkLabel(badge, text=tag_text, font=("Arial", 8, "bold"), text_color=color_tag).pack(padx=6, pady=1)

            # Valor Destacado
            ctk.CTkLabel(card, text=valor_primario, font=("Georgia", 18, "bold"), text_color=self.TEXT_PRIMARY).pack(anchor="w", padx=14, pady=(2, 0))
            ctk.CTkLabel(card, text=sub_texto, font=("Arial", 9), text_color=self.TEXT_MUTED).pack(anchor="w", padx=14, pady=(2, 12))

        render_kpi(0, "INGRESOS TOTALES", f"${data['total_ingresos_usd']:,.2f}", formatear_bs(data['total_ingresos_bs']), "Caja Neta", self.ACCENT_GREEN, "💎")
        render_kpi(1, "ESTANCIAS TOTALES", f"{data['total_estancias']}", f"Tasa BCV Ref: {tasa:.2f} Bs", "Rotación", self.ACCENT_GOLD, "🛎️")
        render_kpi(2, "TICKET PROMEDIO", f"${data['ticket_promedio_usd']:,.2f}", f"{formatear_bs(data['ticket_promedio_usd'] * tasa)} / Estancia", "Consumo", self.ACCENT_BLUE, "📊")
        render_kpi(3, "UTILIDAD MINI-BAR", f"${data['utilidad_minibar_usd']:,.2f}", f"Margen neto sobre CPP", "Ganancia Pura", self.ACCENT_PURPLE, "📦")

        # =====================================================================
        # ESTILO Y GRÁFICOS VISUALES TOP-NOTCH
        # =====================================================================
        plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
        plt.rcParams['axes.edgecolor'] = '#332E29'
        plt.rcParams['axes.linewidth'] = 0.8

        def estilizar_ejes(ax, titulo):
            ax.set_facecolor('#1A1816')
            ax.set_title(titulo, color=self.TEXT_PRIMARY, fontsize=11, fontweight='bold', pad=12, loc='left')
            ax.tick_params(colors=self.TEXT_MUTED, labelsize=8, length=0)
            for spine in ['top', 'right']:
                ax.spines[spine].set_visible(False)
            ax.spines['left'].set_color('#332E29')
            ax.spines['bottom'].set_color('#332E29')
            ax.grid(color='#26231F', linestyle='--', linewidth=0.6, alpha=0.9, zorder=1)

        # ---------------------------------------------------------------------
        # GRÁFICO 1: ROTACIÓN POR HABITACIÓN (Barras Estilizadas)
        # ---------------------------------------------------------------------
        fig1, ax1 = plt.subplots(figsize=(4.8, 3.4), facecolor='#1A1816')
        if data['rotacion_hab']:
            habs = list(data['rotacion_hab'].keys())
            cants = list(data['rotacion_hab'].values())
            
            # Barras con borde suave y sombra
            barras = ax1.bar(habs, cants, color='#D4AF37', width=0.55, zorder=3, edgecolor='#EED382', linewidth=0.7)
            
            # Etiqueta de valor encima de cada barra
            for b in barras:
                h = b.get_height()
                ax1.text(b.get_x() + b.get_width()/2., h + 0.1, f'{int(h)}', ha='center', va='bottom', color=self.TEXT_PRIMARY, fontsize=8, fontweight='bold')
                
            estilizar_ejes(ax1, "Rotación y Frecuencia por Habitación")
        else:
            ax1.text(0.5, 0.5, "Sin estancias registradas en este período", color=self.TEXT_MUTED, ha='center', va='center')
            estilizar_ejes(ax1, "Rotación por Habitación")

        fig1.tight_layout()
        c1 = FigureCanvasTkAgg(fig1, master=self.frame_graficos)
        c1.draw()
        c1.get_tk_widget().grid(row=0, column=0, padx=8, pady=8, sticky="nsew")
        self.canvas_list.append(c1)

        # ---------------------------------------------------------------------
        # GRÁFICO 2: CURVA DE HORAS PICO (Área Suave)
        # ---------------------------------------------------------------------
        fig2, ax2 = plt.subplots(figsize=(4.8, 3.4), facecolor='#1A1816')
        horas = list(data['horas_pico'].keys())
        afluencia = list(data['horas_pico'].values())
        
        ax2.plot(horas, afluencia, color='#2ECC71', linewidth=2.2, zorder=3, marker='o', markersize=3, markerfacecolor='#FFFFFF')
        ax2.fill_between(horas, afluencia, color='#2ECC71', alpha=0.12, zorder=2)
        
        ax2.set_xticks(range(0, 24, 3))
        ax2.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 3)])
        estilizar_ejes(ax2, "Afluencia por Hora (Curva de Pico 24h)")

        fig2.tight_layout()
        c2 = FigureCanvasTkAgg(fig2, master=self.frame_graficos)
        c2.draw()
        c2.get_tk_widget().grid(row=0, column=1, padx=8, pady=8, sticky="nsew")
        self.canvas_list.append(c2)

        # ---------------------------------------------------------------------
        # GRÁFICO 3: DONA DE MÉTODOS DE PAGO CONSOLIDADO (Donut Chart)
        # ---------------------------------------------------------------------
        fig3, ax3 = plt.subplots(figsize=(4.8, 3.4), facecolor='#1A1816')
        metodos_activos = {k: v for k, v in data['metodos_pago'].items() if v > 0}
        total_pago = sum(metodos_activos.values())

        if metodos_activos and total_pago > 0:
            paleta = ['#2ECC71', '#3498DB', '#D4AF37', '#E67E22', '#9B59B6']
            wedges, texts, autotexts = ax3.pie(
                metodos_activos.values(),
                autopct='%1.1f%%',
                startangle=140,
                pctdistance=0.75,
                colors=paleta[:len(metodos_activos)],
                wedgeprops=dict(width=0.38, edgecolor='#1A1816', linewidth=2)
            )

            for t in autotexts:
                t.set_color('#FFFFFF')
                t.set_fontsize(8)
                t.set_weight('bold')

            # Centro de dona con total
            ax3.text(0, 0, f"${total_pago:,.0f}\nTOTAL", ha='center', va='center',
                     color=self.TEXT_PRIMARY, fontsize=9, fontweight='bold')

            # Leyenda elegante abajo
            ax3.legend(
                wedges, metodos_activos.keys(),
                loc="lower center", bbox_to_anchor=(0.5, -0.08),
                ncol=2, frameon=False, fontsize=7.5,
                labelcolor=self.TEXT_MUTED
            )
            ax3.set_title("Distribución de Ingresos (Alquiler + MiniBar + Daños)",
                          color=self.TEXT_PRIMARY, fontsize=10, fontweight='bold', pad=10, loc='center')
        else:
            ax3.text(0.5, 0.5, "Sin movimientos de caja registrados", color=self.TEXT_MUTED, ha='center', va='center')
            ax3.set_title("Distribución de Ingresos", color=self.TEXT_PRIMARY, fontsize=10, fontweight='bold', loc='left')

        fig3.tight_layout()
        c3 = FigureCanvasTkAgg(fig3, master=self.frame_graficos)
        c3.draw()
        c3.get_tk_widget().grid(row=1, column=0, padx=8, pady=8, sticky="nsew")
        self.canvas_list.append(c3)

        # ---------------------------------------------------------------------
        # GRÁFICO 4: TOP PRODUCTOS MINI-BAR (Barras Horizontales Modernas)
        # ---------------------------------------------------------------------
        fig4, ax4 = plt.subplots(figsize=(4.8, 3.4), facecolor='#1A1816')
        if data['top_productos']:
            nombres = [p[0][:18] for p in data['top_productos']]
            cantidades = [p[1] for p in data['top_productos']]

            y_pos = range(len(nombres))
            barras_h = ax4.barh(y_pos, cantidades, color='#3498DB', height=0.55, edgecolor='#5DADE2', linewidth=0.7, zorder=3)
            ax4.set_yticks(y_pos)
            ax4.set_yticklabels(nombres, color=self.TEXT_PRIMARY, fontsize=8)
            ax4.invert_yaxis()  # El producto #1 arriba

            for b in barras_h:
                w = b.get_width()
                ax4.text(w + 0.1, b.get_y() + b.get_height()/2., f'{int(w)} uds',
                         ha='left', va='center', color=self.TEXT_MUTED, fontsize=8, fontweight='bold')

            estilizar_ejes(ax4, "Top 5 Productos Vendidos (Mini-Bar)")
        else:
            ax4.text(0.5, 0.5, "Sin ventas de mini-bar en el período", color=self.TEXT_MUTED, ha='center', va='center')
            estilizar_ejes(ax4, "Top Productos Mini-Bar")

        fig4.tight_layout()
        c4 = FigureCanvasTkAgg(fig4, master=self.frame_graficos)
        c4.draw()
        c4.get_tk_widget().grid(row=1, column=1, padx=8, pady=8, sticky="nsew")
        self.canvas_list.append(c4)

        plt.close('all')