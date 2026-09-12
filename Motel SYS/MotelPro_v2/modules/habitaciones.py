"""
===============================================================================
SISTEMA DE GESTIÓN DE MOTELES - MOTEL PRO v2.0
Módulo: modules/habitaciones.py (VISTA/CONTROLADOR DE ALTO RENDIMIENTO)
Diseño: Dark Luxury Responsive con Scroll Fluido y Cero Bloqueo de UI
===============================================================================
"""
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime, timedelta

# Importaciones desde la Capa de Datos (MODELO: database/db_manager.py)
from database.db_manager import (
    obtener_habitaciones, obtener_tasa_bcv, actualizar_tasa_bcv,
    consultar_moroso, registrar_estancia, finalizar_estancia_checkout,
    actualizar_estado_habitacion, registrar_pago_ingreso,
    obtener_estancias_activas, extender_estancia_habitacion, agregar_habitacion,
    registrar_auditoria, registrar_liberacion_limpieza,
    actualizar_tarifas_habitacion, eliminar_habitacion_segura,
    liquidar_deuda_moroso_y_rehabilitar, agregar_moroso, formatear_bs
)


def centrar_ventana(win, ancho: int, alto: int):
    """Calcula y posiciona cualquier ventana modal en el centro exacto del monitor."""
    win.update_idletasks()
    pantalla_ancho = win.winfo_screenwidth()
    pantalla_alto = win.winfo_screenheight()
    x = max(0, (pantalla_ancho - ancho) // 2)
    y = max(0, (pantalla_alto - alto) // 2)
    win.geometry(f"{ancho}x{alto}+{x}+{y}")


class FrameHabitaciones(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#100F0D")
        self.controller = controller

        # =====================================================================
        # CONSTANTES DE DISEÑO - PALETA LUXURY BOUTIQUE
        # =====================================================================
        self.COLOR_BG = "#100F0D"
        self.COLOR_PANEL = "#181614"
        self.COLOR_CARD_BASE = "#1F1C19"
        self.COLOR_BORDER = "#2E2A25"
        self.COLOR_GOLD = "#D4AF37"
        self.COLOR_TEXT_MUTED = "#8E8880"
        self.COLOR_TEXT_MAIN = "#F5EFEB"

        # Estados con colores de alto contraste operativo
        self.STATUS_THEME = {
            "Limpia": {
                "bg": "#12251A", "border": "#2ECC71", "badge_bg": "#1B3B2B",
                "badge_txt": "#2ECC71", "txt": "DISPONIBLE", "dot": "●"
            },
            "Ocupada": {
                "bg": "#2B1614", "border": "#E74C3C", "badge_bg": "#441D19",
                "badge_txt": "#E74C3C", "txt": "OCUPADA", "dot": "●"
            },
            "Sucia": {
                "bg": "#281D10", "border": "#E67E22", "badge_bg": "#422810",
                "badge_txt": "#E67E22", "txt": "POR LIMPIAR", "dot": "●"
            },
            "Tiempo_Vencido": {
                "bg": "#2A132D", "border": "#9B59B6", "badge_bg": "#431849",
                "badge_txt": "#AF7AC5", "txt": "TIEMPO VENCIDO", "dot": "▲"
            },
            "Mantenimiento": {
                "bg": "#1C1D20", "border": "#7F8C8D", "badge_bg": "#2C2F33",
                "badge_txt": "#BDC3C7", "txt": "MANTENIMIENTO", "dot": "■"
            }
        }

        # Parámetros del motor de interfaz
        self.filtro_estado = "TODAS"
        self.filtro_busqueda = ""
        self.columnas_actuales = 4
        self.ancho_min_card = 230
        self.cache_cards = {}
        self.data_cache = []
        self._resize_job = None

        # =====================================================================
        # 1. HEADER EJECUTIVO (SUPERIOR)
        # =====================================================================
        self.frame_header = ctk.CTkFrame(
            self, height=62, fg_color=self.COLOR_PANEL,
            corner_radius=12, border_width=1, border_color=self.COLOR_BORDER
        )
        self.frame_header.pack(fill="x", padx=16, pady=(12, 6))

        # Tasa e Indicador en Vivo
        f_left_head = ctk.CTkFrame(self.frame_header, fg_color="transparent")
        f_left_head.pack(side="left", padx=16)

        ctk.CTkLabel(
            f_left_head, text="PANEL DE HABITACIONES",
            font=("Montserrat", 14, "bold"), text_color=self.COLOR_TEXT_MAIN
        ).pack(anchor="w")

        self.lbl_tasa = ctk.CTkLabel(
            f_left_head, text="Sincronizando tasa BCV...",
            font=("Arial", 11, "bold"), text_color=self.COLOR_GOLD
        )
        self.lbl_tasa.pack(anchor="w")

        # Botones RBAC de Administrador
        if self.controller.usuario_actual and self.controller.usuario_actual.get('rol') == 'admin':
            ctk.CTkButton(
                self.frame_header, text="+ Nueva Habitación", fg_color=self.COLOR_GOLD, hover_color="#B89228",
                text_color="#100F0D", font=("Arial", 11, "bold"), height=32, corner_radius=8,
                command=self.modal_nueva_habitacion
            ).pack(side="right", padx=10)

            ctk.CTkButton(
                self.frame_header, text="⚙️ Tarifas y Ajustes", fg_color="#26221D", hover_color="#38322B",
                text_color=self.COLOR_GOLD, font=("Arial", 11, "bold"), height=32, corner_radius=8,
                border_width=1, border_color=self.COLOR_BORDER, command=self.modal_administrar_habitaciones
            ).pack(side="right", padx=6)

            ctk.CTkButton(
                self.frame_header, text="Ajustar BCV", fg_color="#26221D", hover_color="#38322B",
                text_color=self.COLOR_TEXT_MAIN, font=("Arial", 11), height=32, corner_radius=8,
                border_width=1, border_color=self.COLOR_BORDER, command=self.modal_tasa_bcv
            ).pack(side="right", padx=6)

        # =====================================================================
        # 2. BARRA DE HERRAMIENTAS Y FILTROS INTERACTIVOS
        # =====================================================================
        self.frame_tools = ctk.CTkFrame(self, height=48, fg_color="transparent")
        self.frame_tools.pack(fill="x", padx=16, pady=(0, 8))

        # Buscador interactivo
        self.entry_search = ctk.CTkEntry(
            self.frame_tools, placeholder_text="🔍 Filtrar por código (ej: P-101)...",
            width=250, height=34, fg_color=self.COLOR_CARD_BASE, border_color=self.COLOR_BORDER,
            text_color=self.COLOR_TEXT_MAIN, font=("Arial", 11)
        )
        self.entry_search.pack(side="left")
        self.entry_search.bind("<KeyRelease>", self.on_search_key)

        # Chips de filtrado con conteo dinámico
        self.filtros_container = ctk.CTkFrame(self.frame_tools, fg_color="transparent")
        self.filtros_container.pack(side="right")

        self.btn_filtros = {}
        estados_chips = [
            ("TODAS", "Todas (0)"),
            ("Limpia", "Disponibles (0)"),
            ("Ocupada", "Ocupadas (0)"),
            ("Sucia", "Por Limpiar (0)"),
            ("Mantenimiento", "Mantenimiento (0)")
        ]

        for clave, texto in estados_chips:
            btn = ctk.CTkButton(
                self.filtros_container, text=texto, height=30, corner_radius=15,
                font=("Arial", 10, "bold"),
                fg_color=self.COLOR_GOLD if clave == "TODAS" else self.COLOR_PANEL,
                text_color="#100F0D" if clave == "TODAS" else self.COLOR_TEXT_MUTED,
                border_width=1, border_color=self.COLOR_BORDER,
                hover_color="#322C26",
                command=lambda k=clave: self.seleccionar_filtro(k)
            )
            btn.pack(side="left", padx=3)
            self.btn_filtros[clave] = {"btn": btn, "base_txt": texto.split(" (")[0]}

        # =====================================================================
        # 3. CONTENEDOR SCROLLABLE ROBUSTO
        # =====================================================================
        self.scroll_grid = ctk.CTkScrollableFrame(self, fg_color=self.COLOR_BG)
        self.scroll_grid.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        # Vinculación segura de redimensionamiento
        self.scroll_grid.bind("<Configure>", self.on_frame_configure)

        # Cargar datos iniciales
        self.actualizar_tasa_label()
        self.cargar_datos_y_renderizar(forzar_redibujado=True)
        self.iniciar_auto_refresco()

    # =========================================================================
    # ENLACE DE SCROLL DEL RATÓN (MOUSEWHEEL UNIVERSAL)
    # =========================================================================
    def vincular_scroll_recursivo(self, widget):
        """Permite que el mousewheel funcione incluso si el cursor está sobre tarjetas o botones."""
        canvas = self.scroll_grid._parent_canvas
        def _scroll_handler(event):
            if event.num == 4 or event.delta > 0:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5 or event.delta < 0:
                canvas.yview_scroll(1, "units")

        widget.bind("<MouseWheel>", _scroll_handler)
        widget.bind("<Button-4>", _scroll_handler)
        widget.bind("<Button-5>", _scroll_handler)
        for child in widget.winfo_children():
            self.vincular_scroll_recursivo(child)

    def refrescar_geometria_scroll(self):
        """Recalcula el scrollregion del canvas para evitar que las tarjetas se corten."""
        self.scroll_grid.update_idletasks()
        canvas = self.scroll_grid._parent_canvas
        bbox = canvas.bbox("all")
        if bbox:
            canvas.configure(scrollregion=(0, 0, bbox[2], bbox[3] + 40))

    # =========================================================================
    # MOTOR DE RESPONSIVIDAD DINÁMICA
    # =========================================================================
    def on_frame_configure(self, event):
        """Ajusta las columnas sin parpadeos mediante debounce."""
        if self._resize_job is not None:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(80, self._aplicar_recalculo_columnas, event.width)

    def _aplicar_recalculo_columnas(self, ancho_actual):
        self._resize_job = None
        if ancho_actual <= 100:
            return
        nuevas_cols = max(1, ancho_actual // (self.ancho_min_card + 16))
        if nuevas_cols != self.columnas_actuales:
            self.columnas_actuales = nuevas_cols
            self.reorganizar_grid()

    # =========================================================================
    # OPTIMIZACIÓN: CERO LAG Y COMPARACIÓN DIFERENCIAL
    # =========================================================================
    def iniciar_auto_refresco(self):
        """Verificación pasiva cada 8 segundos sin bloquear el hilo principal."""
        if self.winfo_exists():
            self.actualizar_tasa_label()
            self.cargar_datos_y_renderizar(forzar_redibujado=False)
            self.after(8000, self.iniciar_auto_refresco)

    def actualizar_tasa_label(self):
        try:
            tasa = obtener_tasa_bcv()
            self.lbl_tasa.configure(text=f"Tasa Oficial BCV: {tasa:.2f} Bs / USD")
        except Exception:
            pass

    def on_search_key(self, event=None):
        self.filtro_busqueda = self.entry_search.get().strip().upper()
        self.reorganizar_grid()

    def seleccionar_filtro(self, nuevo_filtro: str):
        self.filtro_estado = nuevo_filtro
        for clave, d in self.btn_filtros.items():
            btn = d["btn"]
            if clave == nuevo_filtro:
                btn.configure(fg_color=self.COLOR_GOLD, text_color="#100F0D")
            else:
                btn.configure(fg_color=self.COLOR_PANEL, text_color=self.COLOR_TEXT_MUTED)
        self.reorganizar_grid()

    def actualizar_contadores_chips(self):
        conteo = {"TODAS": len(self.data_cache), "Limpia": 0, "Ocupada": 0, "Sucia": 0, "Mantenimiento": 0}
        for item in self.data_cache:
            est = item["estado"]
            if est in ["Ocupada", "Tiempo_Vencido"]:
                conteo["Ocupada"] += 1
            elif est in conteo:
                conteo[est] += 1

        for clave, d in self.btn_filtros.items():
            cnt = conteo.get(clave, 0)
            d["btn"].configure(text=f"{d['base_txt']} ({cnt})")

    # =========================================================================
    # RENDERIZADO Y CONTROL DE TARJETAS
    # =========================================================================
    def cargar_datos_y_renderizar(self, forzar_redibujado=False):
        habitaciones = obtener_habitaciones()
        estancias = {e["hab_codigo"]: e for e in obtener_estancias_activas()}

        data_actual = []
        for h in habitaciones:
            cod = h["codigo"]
            est = estancias.get(cod)
            data_actual.append({
                "id": h["id"],
                "codigo": cod,
                "estado": h["estado"],
                "precio_4h": h["precio_4h"],
                "precio_24h": h["precio_24h"],
                "camarera": h.get("ultima_camarera", "N/A"),
                "f_in": est["fecha_entrada"] if est else None,
                "f_out": est["fecha_salida_estimada"] if est else None,
                "huesped": f"{est['nombre']} {est['apellido']}" if est else None
            })

        if not forzar_redibujado and data_actual == self.data_cache:
            return

        self.data_cache = data_actual
        self.actualizar_contadores_chips()
        self.sincronizar_cards()
        self.reorganizar_grid()

    def sincronizar_cards(self):
        codigos_bd = {h["codigo"] for h in self.data_cache}

        for cod in list(self.cache_cards.keys()):
            if cod not in codigos_bd:
                self.cache_cards[cod]["frame"].destroy()
                del self.cache_cards[cod]

        for item in self.data_cache:
            cod = item["codigo"]
            estado = item["estado"]
            th = self.STATUS_THEME.get(estado, self.STATUS_THEME["Limpia"])

            # Formateo de información
            if estado in ["Ocupada", "Tiempo_Vencido"] and item["f_out"]:
                try:
                    f_out_dt = datetime.strptime(item["f_out"], "%Y-%m-%d %H:%M:%S")
                    hora_txt = f"Vence: {f_out_dt.strftime('%I:%M %p')}"
                    sub_txt = f"Huésped: {item['huesped'][:18]}" if item['huesped'] else "Ocupante Activo"
                except Exception:
                    hora_txt = "Ocupada"
                    sub_txt = "En Uso"
            elif estado == "Sucia":
                hora_txt = "Requiere Camarera"
                sub_txt = "Bloqueada por Limpieza"
            elif estado == "Mantenimiento":
                hora_txt = "Avería / Reparación"
                sub_txt = "Fuera de Servicio"
            else:
                hora_txt = f"4h: ${item['precio_4h']:.2f}  •  24h: ${item['precio_24h']:.2f}"
                sub_txt = f"Última camarera: {item['camarera']}"

            if cod not in self.cache_cards:
                # Estructura de la tarjeta con altura fija para evitar solapamientos
                card = ctk.CTkFrame(
                    self.scroll_grid, fg_color=th["bg"], corner_radius=12,
                    border_width=1.5, border_color=th["border"], height=160
                )
                card.grid_propagate(False)

                # Fila Superior: Código + Badge
                f_top = ctk.CTkFrame(card, fg_color="transparent")
                f_top.pack(fill="x", padx=12, pady=(10, 4))

                lbl_cod = ctk.CTkLabel(
                    f_top, text=cod, font=("Montserrat", 16, "bold"), text_color=self.COLOR_TEXT_MAIN
                )
                lbl_cod.pack(side="left")

                badge = ctk.CTkFrame(f_top, fg_color=th["badge_bg"], corner_radius=6, border_width=1, border_color=th["border"])
                badge.pack(side="right")
                lbl_badge = ctk.CTkLabel(
                    badge, text=f"{th['dot']} {th['txt']}", font=("Arial", 8, "bold"), text_color=th["badge_txt"]
                )
                lbl_badge.pack(padx=6, pady=2)

                # Separador sutil
                sep = ctk.CTkFrame(card, height=1, fg_color=self.COLOR_BORDER)
                sep.pack(fill="x", padx=12, pady=4)

                # Textos informativos
                lbl_info = ctk.CTkLabel(card, text=hora_txt, font=("Arial", 11, "bold"), text_color=self.COLOR_TEXT_MAIN)
                lbl_info.pack(pady=(2, 1))

                lbl_sub = ctk.CTkLabel(card, text=sub_txt, font=("Arial", 9), text_color=self.COLOR_TEXT_MUTED)
                lbl_sub.pack(pady=(0, 6))

                # Botón de Gestión
                btn_action = ctk.CTkButton(
                    card, text="Gestionar", fg_color=self.COLOR_PANEL, text_color=self.COLOR_TEXT_MAIN,
                    hover_color="#302B24", border_width=1, border_color=self.COLOR_BORDER,
                    height=28, corner_radius=8, font=("Arial", 10, "bold"),
                    command=lambda h=item: self.procesar_click_habitacion(h)
                )
                btn_action.pack(fill="x", padx=12, pady=(0, 10))

                self.vincular_scroll_recursivo(card)

                self.cache_cards[cod] = {
                    "frame": card, "lbl_badge": lbl_badge, "badge_frame": badge,
                    "lbl_info": lbl_info, "lbl_sub": lbl_sub, "btn": btn_action, "data": item
                }
            else:
                c = self.cache_cards[cod]
                c["data"] = item
                c["frame"].configure(fg_color=th["bg"], border_color=th["border"])
                c["badge_frame"].configure(fg_color=th["badge_bg"], border_color=th["border"])
                c["lbl_badge"].configure(text=f"{th['dot']} {th['txt']}", text_color=th["badge_txt"])
                c["lbl_info"].configure(text=hora_txt)
                c["lbl_sub"].configure(text=sub_txt)
                c["btn"].configure(command=lambda h=item: self.procesar_click_habitacion(h))

    def reorganizar_grid(self):
        """Ubica las tarjetas en el grid calculando espacio exacto y padding final."""
        for card_obj in self.cache_cards.values():
            card_obj["frame"].grid_forget()

        for col_idx in range(self.columnas_actuales):
            self.scroll_grid.grid_columnconfigure(col_idx, weight=1, uniform="col_hab")

        idx_visible = 0
        elementos_a_mostrar = []
        for item in self.data_cache:
            cod = item["codigo"]
            estado = item["estado"]

            if self.filtro_busqueda and (self.filtro_busqueda not in cod):
                continue

            if self.filtro_estado != "TODAS":
                if self.filtro_estado == "Ocupada" and estado in ["Ocupada", "Tiempo_Vencido"]:
                    pass
                elif estado != self.filtro_estado:
                    continue

            elementos_a_mostrar.append(cod)

        for cod in elementos_a_mostrar:
            r = idx_visible // self.columnas_actuales
            c = idx_visible % self.columnas_actuales
            
            # Padding inferior extra en la última fila para asegurar visibilidad total
            es_ultima_fila = (idx_visible >= len(elementos_a_mostrar) - self.columnas_actuales)
            pad_y = (6, 25) if es_ultima_fila else (6, 6)

            self.cache_cards[cod]["frame"].grid(row=r, column=c, padx=6, pady=pad_y, sticky="nsew")
            idx_visible += 1

        self.refrescar_geometria_scroll()

    def procesar_click_habitacion(self, hab: dict):
        estado = hab["estado"]
        if estado == "Limpia":
            self.modal_checkin(hab)
        elif estado in ["Ocupada", "Tiempo_Vencido"]:
            self.modal_gestionar_ocupada(hab)
        elif estado == "Sucia":
            self.modal_limpieza(hab)
        elif estado == "Mantenimiento":
            messagebox.showinfo(
                "Mantenimiento Activo",
                f"La habitación {hab['codigo']} está en reparación.\nConsulte o libere la orden en el Módulo de Mantenimiento."
            )

    # =========================================================================
    # MODAL 1: CHECK-IN INTELIGENTE (INDIVIDUAL / PAREJA + RECUPERACIÓN DE DEUDA)
    # =========================================================================
    def modal_checkin(self, hab: dict):
        win = ctk.CTkToplevel(self)
        win.title(f"Check-In - Habitación {hab['codigo']}")
        centrar_ventana(win, 920, 720)
        win.grab_set()

        tasa = obtener_tasa_bcv()

        frame_modalidad = ctk.CTkFrame(win, fg_color="#1F1C19", corner_radius=10)
        frame_modalidad.pack(fill="x", padx=16, pady=(12, 6))

        sw_individual = ctk.CTkSwitch(
            frame_modalidad, text="👤 Huésped Individual (Sin Acompañante)",
            font=("Arial", 12, "bold"), text_color=self.COLOR_TEXT_MAIN, progress_color=self.COLOR_GOLD,
            command=lambda: toggle_acompanante()
        )
        sw_individual.pack(side="left", padx=16, pady=8)

        frame_dual = ctk.CTkFrame(win, fg_color="#181614", corner_radius=12)
        frame_dual.pack(fill="both", expand=True, padx=16, pady=6)

        meses_es = [
            "01 - Enero", "02 - Febrero", "03 - Marzo", "04 - Abril",
            "05 - Mayo", "06 - Junio", "07 - Julio", "08 - Agosto",
            "09 - Septiembre", "10 - Octubre", "11 - Noviembre", "12 - Diciembre"
        ]
        dias = [f"{i:02d}" for i in range(1, 32)]
        anio_actual = datetime.now().year
        anios = [str(y) for y in range(anio_actual - 18, 1930, -1)]

        # --- Columna Titular ---
        col_titular = ctk.CTkFrame(frame_dual, fg_color="#24201C", corner_radius=10)
        col_titular.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        ctk.CTkLabel(col_titular, text="TITULAR PRINCIPAL", font=("Montserrat", 12, "bold"), text_color=self.COLOR_GOLD).pack(pady=5)

        e_ced = ctk.CTkEntry(col_titular, placeholder_text="Cédula (Sólo números)", fg_color="#1A1816")
        e_ced.pack(pady=3, fill="x", padx=10)
        e_nom = ctk.CTkEntry(col_titular, placeholder_text="Nombre", fg_color="#1A1816")
        e_nom.pack(pady=3, fill="x", padx=10)
        e_ape = ctk.CTkEntry(col_titular, placeholder_text="Apellido", fg_color="#1A1816")
        e_ape.pack(pady=3, fill="x", padx=10)
        e_tel = ctk.CTkEntry(col_titular, placeholder_text="Teléfono", fg_color="#1A1816")
        e_tel.pack(pady=3, fill="x", padx=10)

        ctk.CTkLabel(col_titular, text="Fecha de Nacimiento:", font=("Arial", 10, "bold"), text_color=self.COLOR_TEXT_MUTED).pack(anchor="w", padx=10, pady=(4, 0))
        f_nac_t = ctk.CTkFrame(col_titular, fg_color="transparent")
        f_nac_t.pack(fill="x", padx=10, pady=2)

        c_dia_t = ctk.CTkComboBox(f_nac_t, values=dias, width=65); c_dia_t.set("15"); c_dia_t.pack(side="left", padx=1)
        c_mes_t = ctk.CTkComboBox(f_nac_t, values=meses_es, width=120); c_mes_t.set(meses_es[0]); c_mes_t.pack(side="left", padx=1)
        c_anio_t = ctk.CTkComboBox(f_nac_t, values=anios, width=80); c_anio_t.set("2000"); c_anio_t.pack(side="left", padx=1)

        lbl_edad_t = ctk.CTkLabel(col_titular, text="Edad: 24 años", font=("Arial", 11, "bold"), text_color=self.COLOR_GOLD)
        lbl_edad_t.pack(pady=2)

        c_eciv = ctk.CTkComboBox(col_titular, values=["Soltero/a", "Casado/a", "Divorciado/a", "Viudo/a"])
        c_eciv.pack(pady=3, fill="x", padx=10)
        c_nac = ctk.CTkComboBox(col_titular, values=["V", "E"])
        c_nac.pack(pady=3, fill="x", padx=10)
        e_proc = ctk.CTkEntry(col_titular, placeholder_text="Procedencia", fg_color="#1A1816")
        e_proc.pack(pady=3, fill="x", padx=10)
        e_dest = ctk.CTkEntry(col_titular, placeholder_text="Destino", fg_color="#1A1816")
        e_dest.pack(pady=3, fill="x", padx=10)

        # --- Columna Acompañante ---
        col_acomp = ctk.CTkFrame(frame_dual, fg_color="#24201C", corner_radius=10)
        col_acomp.pack(side="right", fill="both", expand=True, padx=8, pady=8)
        lbl_acomp_tit = ctk.CTkLabel(col_acomp, text="ACOMPAÑANTE", font=("Montserrat", 12, "bold"), text_color=self.COLOR_GOLD)
        lbl_acomp_tit.pack(pady=5)

        ac_ced = ctk.CTkEntry(col_acomp, placeholder_text="Cédula Acompañante", fg_color="#1A1816")
        ac_ced.pack(pady=3, fill="x", padx=10)
        ac_nom = ctk.CTkEntry(col_acomp, placeholder_text="Nombre Acompañante", fg_color="#1A1816")
        ac_nom.pack(pady=3, fill="x", padx=10)
        ac_ape = ctk.CTkEntry(col_acomp, placeholder_text="Apellido Acompañante", fg_color="#1A1816")
        ac_ape.pack(pady=3, fill="x", padx=10)

        lbl_f_nac_a = ctk.CTkLabel(col_acomp, text="Fecha de Nacimiento:", font=("Arial", 10, "bold"), text_color=self.COLOR_TEXT_MUTED)
        lbl_f_nac_a.pack(anchor="w", padx=10, pady=(4, 0))
        f_nac_a = ctk.CTkFrame(col_acomp, fg_color="transparent")
        f_nac_a.pack(fill="x", padx=10, pady=2)

        c_dia_a = ctk.CTkComboBox(f_nac_a, values=dias, width=65); c_dia_a.set("20"); c_dia_a.pack(side="left", padx=1)
        c_mes_a = ctk.CTkComboBox(f_nac_a, values=meses_es, width=120); c_mes_a.set(meses_es[0]); c_mes_a.pack(side="left", padx=1)
        c_anio_a = ctk.CTkComboBox(f_nac_a, values=anios, width=80); c_anio_a.set("2000"); c_anio_a.pack(side="left", padx=1)

        lbl_edad_a = ctk.CTkLabel(col_acomp, text="Edad: 24 años", font=("Arial", 11, "bold"), text_color=self.COLOR_GOLD)
        lbl_edad_a.pack(pady=2)

        ac_eciv = ctk.CTkComboBox(col_acomp, values=["Soltero/a", "Casado/a", "Divorciado/a", "Viudo/a"])
        ac_eciv.pack(pady=3, fill="x", padx=10)
        ac_nac = ctk.CTkComboBox(col_acomp, values=["V", "E"])
        ac_nac.pack(pady=3, fill="x", padx=10)
        ac_proc = ctk.CTkEntry(col_acomp, placeholder_text="Procedencia", fg_color="#1A1816")
        ac_proc.pack(pady=3, fill="x", padx=10)
        ac_dest = ctk.CTkEntry(col_acomp, placeholder_text="Destino", fg_color="#1A1816")
        ac_dest.pack(pady=3, fill="x", padx=10)

        def toggle_acompanante():
            es_individual = sw_individual.get()
            estado = "disabled" if es_individual else "normal"
            color_fondo = "#181614" if es_individual else "#24201C"

            col_acomp.configure(fg_color=color_fondo)
            for widget in [ac_ced, ac_nom, ac_ape, c_dia_a, c_mes_a, c_anio_a, ac_eciv, ac_nac, ac_proc, ac_dest]:
                widget.configure(state=estado)
                if es_individual and hasattr(widget, 'delete'):
                    widget.delete(0, 'end')

        def calcular_edad_desde_combos(d_str, m_str, y_str):
            try:
                mes_num = int(m_str.split(" - ")[0])
                dia_num = int(d_str)
                anio_num = int(y_str)
                f_nac = datetime(anio_num, mes_num, dia_num).date()
                hoy = datetime.now().date()
                return hoy.year - f_nac.year - ((hoy.month, hoy.day) < (f_nac.month, f_nac.day))
            except Exception:
                return 18

        def actualizar_edades(v=None):
            e1 = calcular_edad_desde_combos(c_dia_t.get(), c_mes_t.get(), c_anio_t.get())
            lbl_edad_t.configure(text=f"Edad: {e1} años")
            if not sw_individual.get():
                e2 = calcular_edad_desde_combos(c_dia_a.get(), c_mes_a.get(), c_anio_a.get())
                lbl_edad_a.configure(text=f"Edad: {e2} años")
            else:
                lbl_edad_a.configure(text="N/A")

        for combo in [c_dia_t, c_mes_t, c_anio_t, c_dia_a, c_mes_a, c_anio_a]:
            combo.configure(command=actualizar_edades)

        actualizar_edades()

        # Marco de Cobro Inferior
        frame_pagos = ctk.CTkFrame(win, fg_color="#181614", corner_radius=12)
        frame_pagos.pack(fill="x", padx=16, pady=(0, 10))

        lbl_monto_calc = ctk.CTkLabel(frame_pagos, text="Monto: $0.00", font=("Montserrat", 13, "bold"), text_color=self.COLOR_GOLD)
        lbl_monto_calc.grid(row=0, column=0, columnspan=2, pady=6)

        c_tipo = ctk.CTkComboBox(frame_pagos, values=["4h", "24h"], command=lambda v: recalcular())
        c_tipo.grid(row=1, column=0, padx=10, pady=5)

        c_metodo = ctk.CTkComboBox(
            frame_pagos, values=["EFECTIVO USD", "EFECTIVO BS", "PAGO MOVIL", "PUNTO DE VENTA"],
            command=lambda v: toggle_p2p(v)
        )
        c_metodo.grid(row=1, column=1, padx=10, pady=5)

        frame_p2p = ctk.CTkFrame(frame_pagos, fg_color="transparent")
        e_p2p_ref = ctk.CTkEntry(frame_p2p, placeholder_text="Ref (4 dígitos)", fg_color="#24201C")
        e_p2p_ref.pack(side="left", padx=2)
        e_p2p_ci = ctk.CTkEntry(frame_p2p, placeholder_text="C.I Titular Pago", fg_color="#24201C")
        e_p2p_ci.pack(side="left", padx=2)
        e_p2p_tel = ctk.CTkEntry(frame_p2p, placeholder_text="Teléfono Emisor", fg_color="#24201C")
        e_p2p_tel.pack(side="left", padx=2)

        def recalcular():
            duracion = c_tipo.get()
            precio_usd = hab["precio_4h"] if duracion == "4h" else hab["precio_24h"]
            precio_bs = precio_usd * tasa
            lbl_monto_calc.configure(text=f"Total: ${precio_usd:.2f}  |  {formatear_bs(precio_bs)}")

        def toggle_p2p(metodo):
            if metodo == "PAGO MOVIL":
                frame_p2p.grid(row=2, column=0, columnspan=2, pady=6)
            else:
                frame_p2p.grid_forget()

        recalcular()

        def confirmar_checkin():
            es_individual = sw_individual.get()

            if not all([e_ced.get(), e_nom.get(), e_ape.get()]):
                messagebox.showerror("Error", "Los datos del titular son de ingreso obligatorio.")
                return
            if not e_ced.get().isdigit():
                messagebox.showerror("Error", "La cédula del titular debe contener sólo dígitos.")
                return

            if not es_individual:
                if not all([ac_ced.get(), ac_nom.get(), ac_ape.get()]):
                    messagebox.showerror("Error", "Complete datos del acompañante o active 'Huésped Individual'.")
                    return
                if not ac_ced.get().isdigit():
                    messagebox.showerror("Error", "La cédula del acompañante debe ser numérica.")
                    return

            # Consulta inteligente de Morosos
            moroso_titular = consultar_moroso(e_ced.get().strip())
            if moroso_titular:
                self.modal_recuperar_deuda_moroso(moroso_titular, ejecutar_guardado_final)
                return

            if not es_individual:
                moroso_acomp = consultar_moroso(ac_ced.get().strip())
                if moroso_acomp:
                    self.modal_recuperar_deuda_moroso(moroso_acomp, ejecutar_guardado_final)
                    return

            ejecutar_guardado_final()

        def ejecutar_guardado_final():
            metodo_pago = c_metodo.get()
            es_individual = sw_individual.get()
            usr_act = self.controller.usuario_actual["usuario"]
            rol_act = self.controller.usuario_actual["rol"]

            if metodo_pago == "PAGO MOVIL":
                if not (e_p2p_ref.get() and e_p2p_ci.get() and e_p2p_tel.get()):
                    messagebox.showerror("Error", "Debe completar la referencia, cédula y teléfono del Pago Móvil.")
                    return

            ahora = datetime.now()
            horas = 4 if c_tipo.get() == "4h" else 24
            salida_estimada = ahora + timedelta(hours=horas)
            precio_usd = hab["precio_4h"] if c_tipo.get() == "4h" else hab["precio_24h"]
            edad_t = str(calcular_edad_desde_combos(c_dia_t.get(), c_mes_t.get(), c_anio_t.get()))

            ac_n = ac_nom.get().strip() if not es_individual else ""
            ac_a = ac_ape.get().strip() if not es_individual else ""
            ac_c = ac_ced.get().strip() if not es_individual else ""
            ac_e = str(calcular_edad_desde_combos(c_dia_a.get(), c_mes_a.get(), c_anio_a.get())) if not es_individual else ""
            ac_ec = ac_eciv.get() if not es_individual else ""
            ac_nc = ac_nac.get() if not es_individual else ""
            ac_pr = ac_proc.get().strip() if not es_individual else ""
            ac_ds = ac_dest.get().strip() if not es_individual else ""

            datos_estancia = {
                "hab_codigo": hab["codigo"], "nombre": e_nom.get().strip(), "apellido": e_ape.get().strip(),
                "cedula": e_ced.get().strip(), "telefono": e_tel.get().strip(), "edad": edad_t,
                "estado_civil": c_eciv.get(), "nacionalidad": c_nac.get(),
                "procedencia": e_proc.get().strip(), "destino": e_dest.get().strip(),
                "ac_nombre": ac_n, "ac_apellido": ac_a, "ac_cedula": ac_c,
                "ac_edad": ac_e, "ac_estado_civil": ac_ec,
                "ac_nacionalidad": ac_nc, "ac_procedencia": ac_pr, "ac_destino": ac_ds,
                "tipo_estancia": c_tipo.get(), "fecha_entrada": ahora.strftime("%Y-%m-%d %H:%M:%S"),
                "fecha_salida_estimada": salida_estimada.strftime("%Y-%m-%d %H:%M:%S")
            }

            datos_pago = {
                "hab_codigo": hab["codigo"], "monto": precio_usd, "metodo": metodo_pago,
                "p2p_referencia": e_p2p_ref.get(), "p2p_ci": e_p2p_ci.get(), "p2p_telefono": e_p2p_tel.get(),
                "cliente_nombre": f"{e_nom.get()} {e_ape.get()}", "cliente_cedula": e_ced.get(),
                "ac_nombre": f"{ac_n} {ac_a}".strip() if not es_individual else "SIN ACOMPAÑANTE",
                "ac_cedula": ac_c if not es_individual else "N/A",
                "fecha": ahora.strftime("%Y-%m-%d %H:%M:%S"),
                "turno": "MAÑANA" if 8 <= ahora.hour < 17 else "NOCHE",
                "recepcionista": usr_act,
                "bebidas_usd": 0.0, "bebidas_bs": 0.0
            }

            if registrar_estancia(datos_estancia) and registrar_pago_ingreso(datos_pago):
                desc_huespedes = "Huésped Individual" if es_individual else f"Acompañante: {ac_n} {ac_a}"
                registrar_auditoria(
                    usr_act, rol_act, "CHECK_IN",
                    f"Check-In en Hab {hab['codigo']} ({c_tipo.get()}) a {e_nom.get()} {e_ape.get()} (C.I: {e_ced.get()}) [{desc_huespedes}]. Monto: ${precio_usd:.2f} [{metodo_pago}]."
                )
                messagebox.showinfo("Operación Exitosa", f"Check-In procesado en habitación {hab['codigo']}.")
                win.destroy()
                self.cargar_datos_y_renderizar(forzar_redibujado=True)

        ctk.CTkButton(
            win, text="Confirmar Entrada y Procesar Pago", fg_color=self.COLOR_GOLD, hover_color="#B8892E",
            text_color="#100F0D", font=("Arial", 12, "bold"), height=36, corner_radius=8,
            command=confirmar_checkin
        ).pack(pady=(0, 15))

    # =========================================================================
    # MODAL 1.1: RECUPERACIÓN DE DEUDA DE MOROSO
    # =========================================================================
    def modal_recuperar_deuda_moroso(self, moroso_data: dict, callback_continuar_checkin):
        win_deuda = ctk.CTkToplevel(self)
        win_deuda.title("⚠️ Notificación de Deuda Activa")
        centrar_ventana(win_deuda, 480, 560)
        win_deuda.grab_set()

        tasa = obtener_tasa_bcv()
        cedula = moroso_data["cedula"]
        nombre = moroso_data["nombre"]
        motivo = moroso_data["motivo"]

        ctk.CTkLabel(win_deuda, text="⚠️ Huésped en Lista de Morosos", font=("Montserrat", 14, "bold"), text_color="#E74C3C").pack(pady=(16, 2))
        ctk.CTkLabel(win_deuda, text=f"{nombre}  |  C.I: {cedula}", font=("Arial", 12, "bold"), text_color=self.COLOR_TEXT_MAIN).pack(pady=2)

        f_info = ctk.CTkFrame(win_deuda, fg_color="#24201C", corner_radius=8, border_width=1, border_color="#78281F")
        f_info.pack(fill="x", padx=16, pady=8)

        ctk.CTkLabel(f_info, text="Antecedente Registrado:", font=("Arial", 10, "bold"), text_color=self.COLOR_GOLD).pack(anchor="w", padx=10, pady=(6, 1))
        ctk.CTkLabel(f_info, text=f'"{motivo}"', font=("Arial", 10, "italic"), text_color="#FADBD8", wraplength=420, justify="left").pack(anchor="w", padx=10, pady=(0, 6))

        f_cobro = ctk.CTkFrame(win_deuda, fg_color="#181614", corner_radius=10)
        f_cobro.pack(fill="both", expand=True, padx=16, pady=6)

        ctk.CTkLabel(f_cobro, text="Monto Pendiente a Cobrar ($ USD):", font=("Arial", 11, "bold"), text_color=self.COLOR_GOLD).pack(anchor="w", padx=14, pady=(8, 1))
        e_monto_d = ctk.CTkEntry(f_cobro, placeholder_text="Ej: 20.00", fg_color="#24201C")
        e_monto_d.pack(fill="x", padx=14, pady=2)

        lbl_bs_d = ctk.CTkLabel(f_cobro, text="Equivalente en Bs: 0,00 Bs", font=("Arial", 11, "bold"), text_color="#2ECC71")
        lbl_bs_d.pack(anchor="w", padx=14, pady=2)

        def act_bs(event=None):
            try:
                v = float(e_monto_d.get().replace(",", "."))
                lbl_bs_d.configure(text=f"Equivalente en Bs: {formatear_bs(v * tasa)}")
            except ValueError:
                lbl_bs_d.configure(text="Equivalente en Bs: 0,00 Bs")

        e_monto_d.bind("<KeyRelease>", act_bs)

        ctk.CTkLabel(f_cobro, text="Método de Pago:", font=("Arial", 11, "bold"), text_color=self.COLOR_TEXT_MUTED).pack(anchor="w", padx=14, pady=(6, 1))
        c_met_d = ctk.CTkComboBox(
            f_cobro, values=["EFECTIVO USD", "EFECTIVO BS", "PAGO MOVIL", "PUNTO DE VENTA"],
            command=lambda v: toggle_p2p_deuda(v)
        )
        c_met_d.pack(fill="x", padx=14, pady=2)

        f_p2p_d = ctk.CTkFrame(f_cobro, fg_color="transparent")
        e_ref_d = ctk.CTkEntry(f_p2p_d, placeholder_text="Ref (4 dígitos)", fg_color="#24201C")
        e_ref_d.pack(side="left", padx=2, fill="x", expand=True)
        e_ci_d = ctk.CTkEntry(f_p2p_d, placeholder_text="C.I. Emisor", fg_color="#24201C")
        e_ci_d.pack(side="left", padx=2, fill="x", expand=True)
        e_tel_d = ctk.CTkEntry(f_p2p_d, placeholder_text="Teléfono Emisor", fg_color="#24201C")
        e_tel_d.pack(side="left", padx=2, fill="x", expand=True)

        def toggle_p2p_deuda(metodo):
            if metodo == "PAGO MOVIL":
                f_p2p_d.pack(fill="x", padx=14, pady=4)
            else:
                f_p2p_d.pack_forget()

        def procesar_pago_deuda():
            m_str = e_monto_d.get().strip()
            met = c_met_d.get()
            if not m_str:
                messagebox.showwarning("Campo Requerido", "Ingrese el monto recibido de la deuda.")
                return

            ref, ci_em, tel = None, None, None
            if met == "PAGO MOVIL":
                ref = e_ref_d.get().strip(); ci_em = e_ci_d.get().strip(); tel = e_tel_d.get().strip()
                if not (ref and ci_em and tel):
                    messagebox.showerror("Error", "Debe llenar los datos completos de Pago Móvil.")
                    return

            try:
                m_flt = float(m_str.replace(",", "."))
                usr = self.controller.usuario_actual["usuario"]
                if liquidar_deuda_moroso_y_rehabilitar(cedula, nombre, motivo, m_flt, met, usr, ref, ci_em, tel):
                    messagebox.showinfo("Éxito", f"Deuda de ${m_flt:.2f} solventada. Cliente rehabilitado.")
                    win_deuda.destroy()
                    callback_continuar_checkin()
                else:
                    messagebox.showerror("Error", "Ocurrió un error al liquidar la deuda en base de datos.")
            except ValueError:
                messagebox.showerror("Error", "El monto ingresado no es válido.")

        f_btns = ctk.CTkFrame(win_deuda, fg_color="transparent")
        f_btns.pack(fill="x", padx=16, pady=10)

        ctk.CTkButton(
            f_btns, text="❌ Rechazar Ingreso", fg_color="#78281F", hover_color="#943126",
            width=140, command=win_deuda.destroy
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            f_btns, text="💵 Cobrar y Habilitar", fg_color="#1E5F38", hover_color="#2E7D32",
            text_color="#F4EFE6", font=("Arial", 11, "bold"), command=procesar_pago_deuda
        ).pack(side="right", fill="x", expand=True, padx=5)

    # =========================================================================
    # MODAL 2: GESTIÓN DE HABITACIÓN OCUPADA (EXTENSIÓN Y CHECK-OUT)
    # =========================================================================
    def modal_gestionar_ocupada(self, hab: dict):
        estancias = {e["hab_codigo"]: e for e in obtener_estancias_activas()}
        estancia = estancias.get(hab["codigo"])

        if not estancia:
            messagebox.showerror("Error", "No se encontró registro de la estancia activa.")
            return

        win = ctk.CTkToplevel(self)
        win.title(f"Gestión - {hab['codigo']}")
        centrar_ventana(win, 520, 560)
        win.grab_set()

        tasa = obtener_tasa_bcv()
        usr_act = self.controller.usuario_actual["usuario"]
        rol_act = self.controller.usuario_actual["rol"]

        ctk.CTkLabel(win, text=f"Habitación: {hab['codigo']}", font=("Montserrat", 18, "bold"), text_color=self.COLOR_GOLD).pack(pady=(16, 2))
        ctk.CTkLabel(win, text=f"Huésped: {estancia['nombre']} {estancia['apellido']} (C.I: {estancia['cedula']})", font=("Arial", 11)).pack(pady=1)

        f_in = datetime.strptime(estancia["fecha_entrada"], "%Y-%m-%d %H:%M:%S").strftime("%I:%M %p")
        f_out = datetime.strptime(estancia["fecha_salida_estimada"], "%Y-%m-%d %H:%M:%S").strftime("%I:%M %p")
        ctk.CTkLabel(win, text=f"Ingreso: {f_in}   •   Vencimiento: {f_out}", font=("Arial", 10, "italic"), text_color=self.COLOR_TEXT_MUTED).pack(pady=4)

        # Extensión de Estancia
        frame_ext = ctk.CTkFrame(win, fg_color="#181614", corner_radius=12)
        frame_ext.pack(fill="x", padx=20, pady=8)

        ctk.CTkLabel(frame_ext, text="⏱️ Extensión de Tiempo de Estancia", font=("Arial", 12, "bold"), text_color=self.COLOR_GOLD).pack(pady=6)

        combo_tiempo = ctk.CTkComboBox(frame_ext, values=["+4 Horas", "+24 Horas"], command=lambda v: recalcular_ext())
        combo_tiempo.pack(pady=3)

        lbl_costo_ext = ctk.CTkLabel(frame_ext, text="Costo Extensión: $0.00", font=("Arial", 11, "bold"), text_color=self.COLOR_TEXT_MAIN)
        lbl_costo_ext.pack(pady=3)

        combo_pago_ext = ctk.CTkComboBox(
            frame_ext, values=["EFECTIVO USD", "EFECTIVO BS", "PAGO MOVIL", "PUNTO DE VENTA"],
            command=lambda v: toggle_p2p_ext(v)
        )
        combo_pago_ext.pack(pady=3)

        frame_p2p_ext = ctk.CTkFrame(frame_ext, fg_color="transparent")
        e_ref_ext = ctk.CTkEntry(frame_p2p_ext, placeholder_text="Ref (4 dígitos)", fg_color="#24201C")
        e_ref_ext.pack(side="left", padx=2)
        e_ci_ext = ctk.CTkEntry(frame_p2p_ext, placeholder_text="C.I. Emisor", fg_color="#24201C")
        e_ci_ext.pack(side="left", padx=2)
        e_tel_ext = ctk.CTkEntry(frame_p2p_ext, placeholder_text="Teléfono Emisor", fg_color="#24201C")
        e_tel_ext.pack(side="left", padx=2)

        def toggle_p2p_ext(metodo):
            if metodo == "PAGO MOVIL":
                frame_p2p_ext.pack(fill="x", padx=10, pady=4)
            else:
                frame_p2p_ext.pack_forget()

        def recalcular_ext():
            horas = 4 if combo_tiempo.get() == "+4 Horas" else 24
            p_usd = hab["precio_4h"] if horas == 4 else hab["precio_24h"]
            p_bs = p_usd * tasa
            lbl_costo_ext.configure(text=f"Monto: ${p_usd:.2f}  |  {formatear_bs(p_bs)}")

        recalcular_ext()

        def ejecutar_extension():
            horas_extra = 4 if combo_tiempo.get() == "+4 Horas" else 24
            precio_usd = hab["precio_4h"] if horas_extra == 4 else hab["precio_24h"]
            metodo = combo_pago_ext.get()

            ref, ci, tel = None, None, None
            if metodo == "PAGO MOVIL":
                ref = e_ref_ext.get().strip(); ci = e_ci_ext.get().strip(); tel = e_tel_ext.get().strip()
                if not (ref and ci and tel):
                    messagebox.showerror("Error", "Complete los datos requeridos para el Pago Móvil.")
                    return

            ahora = datetime.now()
            salida_actual = datetime.strptime(estancia["fecha_salida_estimada"], "%Y-%m-%d %H:%M:%S")
            nueva_salida = (ahora if ahora >= salida_actual else salida_actual) + timedelta(hours=horas_extra)

            datos_pago = {
                "hab_codigo": hab["codigo"], "monto": precio_usd, "metodo": metodo,
                "p2p_referencia": ref, "p2p_ci": ci, "p2p_telefono": tel,
                "cliente_nombre": f"{estancia['nombre']} {estancia['apellido']} (EXTENSIÓN)",
                "cliente_cedula": estancia["cedula"], "ac_nombre": estancia.get("ac_nombre"),
                "ac_cedula": estancia.get("ac_cedula"), "fecha": ahora.strftime("%Y-%m-%d %H:%M:%S"),
                "turno": "MAÑANA" if 8 <= ahora.hour < 17 else "NOCHE",
                "recepcionista": usr_act
            }

            if extender_estancia_habitacion(hab["codigo"], nueva_salida.strftime("%Y-%m-%d %H:%M:%S"), datos_pago):
                registrar_auditoria(
                    usr_act, rol_act, "EXTENSION",
                    f"Extensión en Hab {hab['codigo']} ({combo_tiempo.get()}) a {estancia['nombre']} {estancia['apellido']}. Monto: ${precio_usd:.2f}. Nueva salida: {nueva_salida.strftime('%I:%M %p')}."
                )
                messagebox.showinfo("Operación Exitosa", f"Estancia extendida hasta las {nueva_salida.strftime('%I:%M %p')}.")
                win.destroy()
                self.cargar_datos_y_renderizar(forzar_redibujado=True)

        ctk.CTkButton(
            frame_ext, text="Confirmar Extensión", fg_color=self.COLOR_GOLD,
            hover_color="#B8892E", text_color="#100F0D", font=("Arial", 11, "bold"),
            command=ejecutar_extension
        ).pack(fill="x", padx=14, pady=(6, 12))

        # Check-Out Seguro con Opción de Lista Negra
        sw_bloquear_salida = ctk.CTkCheckBox(
            win, text="🚫 Agregar a Lista Negra por morosidad o conducta inapropiada",
            font=("Arial", 10, "bold"), text_color="#E74C3C",
            fg_color="#78281F", hover_color="#943126", checkmark_color="#FFFFFF"
        )
        sw_bloquear_salida.pack(padx=20, pady=(8, 4), anchor="w")

        def ejecutar_checkout():
            if messagebox.askyesno("Confirmación de Salida", f"¿Desea procesar el Check-Out de la habitación {hab['codigo']}?"):
                if sw_bloquear_salida.get():
                    motivo_txt = f"Bloqueado al salir de Hab {hab['codigo']} por incidencias o morosidad."
                    agregar_moroso(estancia["cedula"], f"{estancia['nombre']} {estancia['apellido']}", motivo_txt)
                    registrar_auditoria(usr_act, rol_act, "BLOQUEAR_CLIENTE", f"Huésped {estancia['nombre']} {estancia['apellido']} (C.I: {estancia['cedula']}) enviado a Lista Negra en Check-Out.")

                if finalizar_estancia_checkout(hab["codigo"]):
                    registrar_auditoria(usr_act, rol_act, "CHECK_OUT", f"Check-Out completado en Hab {hab['codigo']}. Pasa a estado 'Sucia'.")
                    messagebox.showinfo("Check-Out Listo", "Habitación liberada y marcada para camareras (Sucia).")
                    win.destroy()
                    self.cargar_datos_y_renderizar(forzar_redibujado=True)

        ctk.CTkButton(
            win, text="🚪 Procesar Check-Out", fg_color="#78281F", hover_color="#943126",
            text_color="#F4EFE6", font=("Arial", 11, "bold"), height=36, corner_radius=8,
            command=ejecutar_checkout
        ).pack(fill="x", padx=20, pady=(6, 15))

    # =========================================================================
    # MODAL 3: LIMPIEZA
    # =========================================================================
    def modal_limpieza(self, hab: dict):
        win = ctk.CTkToplevel(self)
        win.title(f"Control de Calidad - Hab {hab['codigo']}")
        centrar_ventana(win, 380, 260)
        win.grab_set()

        ctk.CTkLabel(win, text=f"Liberación de Habitación {hab['codigo']}", font=("Montserrat", 13, "bold"), text_color=self.COLOR_GOLD).pack(pady=12)
        e_cam = ctk.CTkEntry(win, placeholder_text="Nombre de la Camarera Responsable", fg_color="#24201C")
        e_cam.pack(pady=5, padx=20, fill="x")

        c_turno = ctk.CTkComboBox(win, values=["MAÑANA", "NOCHE"])
        c_turno.pack(pady=5, padx=20, fill="x")

        def liberar():
            camarera = e_cam.get().strip()
            turno = c_turno.get()
            if not camarera:
                messagebox.showwarning("Atención", "Debe registrar el nombre de la camarera.")
                return

            if registrar_liberacion_limpieza(hab["codigo"], camarera, turno):
                registrar_auditoria(
                    self.controller.usuario_actual["usuario"], self.controller.usuario_actual["rol"], "LIMPIEZA_HABITACION",
                    f"Habitación {hab['codigo']} limpiada por {camarera.upper()} (Turno {turno})."
                )
                messagebox.showinfo("Habitación Disponible", f"Habitación {hab['codigo']} lista y disponible.")
                win.destroy()
                self.cargar_datos_y_renderizar(forzar_redibujado=True)
            else:
                messagebox.showerror("Error", "No se pudo actualizar el registro de limpieza.")

        ctk.CTkButton(
            win, text="✅ Marcar Disponible (Verde)", fg_color="#1E5F38", hover_color="#2E7D32",
            font=("Arial", 11, "bold"), height=34, corner_radius=8, command=liberar
        ).pack(pady=18, padx=20, fill="x")

    # =========================================================================
    # MODAL 4: ADMINISTRACIÓN DE HABITACIONES
    # =========================================================================
    def modal_administrar_habitaciones(self):
        win = ctk.CTkToplevel(self)
        win.title("Tarifas y Habitaciones")
        centrar_ventana(win, 720, 520)
        win.grab_set()

        usr_act = self.controller.usuario_actual["usuario"]
        rol_act = self.controller.usuario_actual["rol"]

        ctk.CTkLabel(win, text="⚙️ Configuración y Catálogo de Tarifas", font=("Montserrat", 15, "bold"), text_color=self.COLOR_GOLD).pack(pady=(16, 2))
        ctk.CTkLabel(win, text="Administre los costos en USD de estancias y habitaciones", font=("Arial", 10), text_color=self.COLOR_TEXT_MUTED).pack(pady=(0, 10))

        scroll_habs = ctk.CTkScrollableFrame(win, fg_color="#181614")
        scroll_habs.pack(fill="both", expand=True, padx=20, pady=10)

        def cargar_lista():
            for w in scroll_habs.winfo_children():
                w.destroy()
            habs = obtener_habitaciones()
            for h in habs:
                card = ctk.CTkFrame(scroll_habs, fg_color="#24201C", corner_radius=8)
                card.pack(fill="x", pady=3, padx=5)

                txt_info = f"{h['codigo']}  |  4 Horas: ${h['precio_4h']:.2f}  |  24 Horas: ${h['precio_24h']:.2f}  |  [{h['estado']}]"
                ctk.CTkLabel(card, text=txt_info, font=("Arial", 11, "bold"), text_color=self.COLOR_TEXT_MAIN).pack(side="left", padx=12, pady=8)

                btn_del = ctk.CTkButton(card, text="🗑️", fg_color="#78281F", hover_color="#943126", width=40, command=lambda cod=h["codigo"]: ejecutar_eliminar(cod))
                btn_del.pack(side="right", padx=6)

                btn_edit = ctk.CTkButton(card, text="✏️ Modificar", fg_color="#302B24", hover_color="#453E34", width=100, command=lambda hab_data=h: abrir_editor_tarifa(hab_data))
                btn_edit.pack(side="right", padx=6)

        def ejecutar_eliminar(cod):
            if messagebox.askyesno("Confirmación", f"¿Desea eliminar la habitación '{cod}'?"):
                exito, mensaje = eliminar_habitacion_segura(cod)
                if exito:
                    registrar_auditoria(usr_act, rol_act, "ELIMINAR_HABITACION", f"Se eliminó la habitación: '{cod}'.")
                    messagebox.showinfo("Éxito", mensaje)
                    cargar_lista()
                    self.cargar_datos_y_renderizar(forzar_redibujado=True)
                else:
                    messagebox.showwarning("Bloqueo de Seguridad", mensaje)

        def abrir_editor_tarifa(h_data):
            edit_win = ctk.CTkToplevel(win)
            edit_win.title(f"Editar - {h_data['codigo']}")
            centrar_ventana(edit_win, 350, 320)
            edit_win.grab_set()

            ctk.CTkLabel(edit_win, text=f"Editar Habitación {h_data['codigo']}", font=("Montserrat", 13, "bold"), text_color=self.COLOR_GOLD).pack(pady=(15, 5))
            ed_cod = ctk.CTkEntry(edit_win, fg_color="#24201C"); ed_cod.insert(0, h_data["codigo"]); ed_cod.pack(fill="x", padx=20, pady=4)
            ed_p4 = ctk.CTkEntry(edit_win, fg_color="#24201C"); ed_p4.insert(0, f"{h_data['precio_4h']:.2f}"); ed_p4.pack(fill="x", padx=20, pady=4)
            ed_p24 = ctk.CTkEntry(edit_win, fg_color="#24201C"); ed_p24.insert(0, f"{h_data['precio_24h']:.2f}"); ed_p24.pack(fill="x", padx=20, pady=4)

            def guardar_cambios():
                cod_nuevo = ed_cod.get().strip().upper()
                p4_txt = ed_p4.get().strip()
                p24_txt = ed_p24.get().strip()
                if not all([cod_nuevo, p4_txt, p24_txt]):
                    messagebox.showwarning("Atención", "Complete todos los campos.")
                    return
                try:
                    p4_flt = float(p4_txt.replace(",", "."))
                    p24_flt = float(p24_txt.replace(",", "."))
                    if actualizar_tarifas_habitacion(h_data["id"], cod_nuevo, p4_flt, p24_flt):
                        registrar_auditoria(usr_act, rol_act, "MODIFICAR_HABITACION", f"Tarifas de Hab {cod_nuevo} modificadas: 4h=${p4_flt:.2f}, 24h=${p24_flt:.2f}.")
                        messagebox.showinfo("Éxito", f"Habitación '{cod_nuevo}' actualizada.")
                        edit_win.destroy()
                        cargar_lista()
                        self.cargar_datos_y_renderizar(forzar_redibujado=True)
                    else:
                        messagebox.showerror("Error", "El código de habitación ya se encuentra en uso.")
                except ValueError:
                    messagebox.showerror("Error", "Los precios deben ser valores numéricos.")

            ctk.CTkButton(
                edit_win, text="Guardar Cambios", fg_color=self.COLOR_GOLD,
                hover_color="#B8892E", text_color="#100F0D", font=("Arial", 11, "bold"),
                command=guardar_cambios
            ).pack(fill="x", padx=20, pady=16)

        cargar_lista()

    # =========================================================================
    # MODAL 5: AJUSTE DE TASA BCV
    # =========================================================================
    def modal_tasa_bcv(self):
        win = ctk.CTkToplevel(self)
        win.title("Tasa BCV")
        centrar_ventana(win, 300, 180)
        win.grab_set()

        ctk.CTkLabel(win, text="Nueva Tasa Oficial BCV (Bs/$):", text_color=self.COLOR_GOLD, font=("Arial", 12, "bold")).pack(pady=12)
        e_tasa = ctk.CTkEntry(win, placeholder_text="Ej: 36.50", fg_color="#24201C")
        e_tasa.pack(pady=4, padx=20, fill="x")

        def guardar():
            try:
                val = float(e_tasa.get().replace(",", "."))
                if actualizar_tasa_bcv(val):
                    registrar_auditoria(
                        self.controller.usuario_actual["usuario"], self.controller.usuario_actual["rol"], "CAMBIO_TASA",
                        f"Tasa Oficial BCV ajustada a {val:.2f} Bs/USD."
                    )
                    messagebox.showinfo("Éxito", "Tasa actualizada correctamente.")
                    win.destroy()
                    self.cargar_datos_y_renderizar(forzar_redibujado=True)
            except ValueError:
                messagebox.showerror("Error", "Ingrese un valor numérico válido.")

        ctk.CTkButton(win, text="Guardar", fg_color=self.COLOR_GOLD, hover_color="#B8892E", text_color="#100F0D", font=("Arial", 11, "bold"), command=guardar).pack(pady=14)

    # =========================================================================
    # MODAL 6: REGISTRO DE NUEVA HABITACIÓN
    # =========================================================================
    def modal_nueva_habitacion(self):
        win = ctk.CTkToplevel(self)
        win.title("Nueva Habitación")
        centrar_ventana(win, 320, 280)
        win.grab_set()

        e_cod = ctk.CTkEntry(win, placeholder_text="Código (Ej: P-111)", fg_color="#24201C")
        e_cod.pack(pady=5, padx=20, fill="x")
        e_p4 = ctk.CTkEntry(win, placeholder_text="Precio 4 Horas ($)", fg_color="#24201C")
        e_p4.pack(pady=5, padx=20, fill="x")
        e_p24 = ctk.CTkEntry(win, placeholder_text="Precio 24 Horas ($)", fg_color="#24201C")
        e_p24.pack(pady=5, padx=20, fill="x")

        def guardar():
            cod, p4, p24 = e_cod.get().strip(), e_p4.get().strip(), e_p24.get().strip()
            if not all([cod, p4, p24]):
                return
            try:
                if agregar_habitacion(cod, float(p4), float(p24)):
                    registrar_auditoria(
                        self.controller.usuario_actual["usuario"], self.controller.usuario_actual["rol"], "CREAR_HABITACION",
                        f"Habitación '{cod.upper()}' creada con tarifas: 4h=${float(p4):.2f}, 24h=${float(p24):.2f}."
                    )
                    messagebox.showinfo("Éxito", f"Habitación '{cod.upper()}' registrada correctamente.")
                    win.destroy()
                    self.cargar_datos_y_renderizar(forzar_redibujado=True)
                else:
                    messagebox.showerror("Error", "El código de habitación ya existe.")
            except ValueError:
                messagebox.showerror("Error", "Los precios deben ser numéricos.")

        ctk.CTkButton(win, text="Crear Habitación", fg_color=self.COLOR_GOLD, hover_color="#B8892E", text_color="#100F0D", font=("Arial", 11, "bold"), command=guardar).pack(pady=15)