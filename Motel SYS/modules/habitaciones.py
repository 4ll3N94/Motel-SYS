"""
===============================================================================
SISTEMA DE GESTIÓN DE MOTELES - MOTEL PRO v2.0
Módulo: modules/habitaciones.py (VISTA/CONTROLADOR CON AUDITORÍA TOTAL)
===============================================================================
"""
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime, timedelta

# Importaciones desde la Capa de Datos (MODELO: database/db_manager.py)
from database.db_manager import (
    obtener_habitaciones, obtener_tasa_bcv, actualizar_tasa_bcv,
    consultar_moroso, registrar_estancia, finalizar_estancia_checkout,
    actualizar_estado_habitacion, registrar_pago_ingreso, obtener_conexion,
    obtener_estancias_activas, extender_estancia_habitacion, agregar_habitacion,
    registrar_auditoria, registrar_liberacion_limpieza,
    actualizar_tarifas_habitacion, eliminar_habitacion_segura,
    liquidar_deuda_moroso_y_rehabilitar, agregar_moroso, formatear_bs
)


# =============================================================================
# FUNCIÓN AUXILIAR: CENTRADO GEOMÉTRICO DE VENTANAS
# =============================================================================
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
        super().__init__(parent, fg_color="#191715")
        self.controller = controller  # Referencia al controlador principal (main.py)

        # =====================================================================
        # 1. ENCABEZADO SUPERIOR (Información de Tasa y Acciones de Administrador)
        # =====================================================================
        self.frame_header = ctk.CTkFrame(self, height=55, fg_color="#23201C", corner_radius=12, border_width=1, border_color="#36322C")
        self.frame_header.pack(fill="x", padx=15, pady=10)

        # Etiqueta de la Tasa Oficial BCV
        self.lbl_tasa = ctk.CTkLabel(self.frame_header, text="", font=("Arial", 14, "bold"), text_color="#D4A343")
        self.lbl_tasa.pack(side="left", padx=15)

        # Acciones Exclusivas del Administrador (RBAC)
        if self.controller.usuario_actual and self.controller.usuario_actual['rol'] == 'admin':
            ctk.CTkButton(
                self.frame_header, text="⚙️ Tarifas y Habitaciones", fg_color="#3E342B", hover_color="#524539",
                text_color="#D4A343", font=("Arial", 11, "bold"), command=self.modal_administrar_habitaciones
            ).pack(side="right", padx=6, pady=8)

            ctk.CTkButton(
                self.frame_header, text="Ajustar Tasa BCV", fg_color="#3E342B", hover_color="#524539",
                text_color="#F4EFE6", command=self.modal_tasa_bcv
            ).pack(side="right", padx=6, pady=8)

            ctk.CTkButton(
                self.frame_header, text="+ Nueva Habitación", fg_color="#D4A343", hover_color="#B8892E",
                text_color="#191715", font=("Arial", 12, "bold"), command=self.modal_nueva_habitacion
            ).pack(side="right", padx=6, pady=8)

        # =====================================================================
        # 2. CONTENEDOR SCROLLABLE DEL GRID DE HABITACIONES
        # =====================================================================
        self.scroll_grid = ctk.CTkScrollableFrame(self, fg_color="#191715", label_text="Panel de Control de Habitaciones")
        self.scroll_grid.pack(fill="both", expand=True, padx=15, pady=5)

        self.actualizar_grid()
        self.iniciar_auto_refresco()

    # =========================================================================
    # MOTOR DE REFRESCO AUTOMÁTICO EN SEGUNDO PLANO
    # =========================================================================
    def iniciar_auto_refresco(self):
        """Refresca el grid cada 10 segundos de forma transparente."""
        if self.winfo_exists():
            self.actualizar_grid()
            self.after(10000, self.iniciar_auto_refresco)

    def actualizar_tasa_label(self):
        """Consulta la tasa BCV activa en la BD y actualiza el encabezado."""
        tasa = obtener_tasa_bcv()
        self.lbl_tasa.configure(text=f"Tasa BCV del Día: {tasa:.2f} Bs / USD")

    # =========================================================================
    # RENDERIZADO VISUAL DEL GRID DINÁMICO
    # =========================================================================
    def actualizar_grid(self):
        """Consulta la BD y dibuja las tarjetas con su paleta de colores y estado."""
        self.actualizar_tasa_label()
        for child in self.scroll_grid.winfo_children():
            child.destroy()

        habitaciones = obtener_habitaciones()
        estancias = {e["hab_codigo"]: e for e in obtener_estancias_activas()}
        
        columnas = 4
        for index, hab in enumerate(habitaciones):
            row = index // columnas
            col = index % columnas

            estado = hab["estado"]

            # Paleta de Colores Cálidos Boutique
            color_map = {
                "Limpia": "#1E5F38",          # Verde Olivo / Bosque
                "Ocupada": "#8A2A22",         # Rojo Ladrillo
                "Sucia": "#A05A18",           # Ámbar / Terracota
                "Tiempo_Vencido": "#632D73",    # Ciruela / Púrpura (Alarma)
                "Mantenimiento": "#4A4F55"     # Pizarra
            }
            bg_color = color_map.get(estado, "#2B2722")

            card = ctk.CTkFrame(self.scroll_grid, fg_color=bg_color, width=220, height=170, corner_radius=12)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            card.grid_propagate(False)

            ctk.CTkLabel(card, text=hab["codigo"], font=("Georgia", 18, "bold"), text_color="#F4EFE6").pack(pady=(8, 2))
            ctk.CTkLabel(card, text=f"Estado: {estado.upper()}", font=("Arial", 11, "bold"), text_color="#F4EFE6").pack(pady=1)

            # Si está ocupada o vencida, muestra horarios exactos
            if estado in ["Ocupada", "Tiempo_Vencido"] and hab["codigo"] in estancias:
                est = estancias[hab["codigo"]]
                try:
                    f_in = datetime.strptime(est["fecha_entrada"], "%Y-%m-%d %H:%M:%S").strftime("%I:%M %p")
                    f_out = datetime.strptime(est["fecha_salida_estimada"], "%Y-%m-%d %H:%M:%S").strftime("%I:%M %p")
                    info_horario = f"Entrada: {f_in}\nVence: {f_out}"
                except Exception:
                    info_horario = f"4h: ${hab['precio_4h']} | 24h: ${hab['precio_24h']}"
                ctk.CTkLabel(card, text=info_horario, font=("Arial", 10, "bold"), text_color="#F9E79F").pack(pady=2)
            else:
                # Si está limpia, muestra la tarifa y la última camarera responsable (Control de Calidad)
                cam_txt = f"Limpieza: {hab.get('ultima_camarera', 'N/A')}"
                ctk.CTkLabel(card, text=f"4h: ${hab['precio_4h']} | 24h: ${hab['precio_24h']}", font=("Arial", 10), text_color="#E5E0D8").pack(pady=1)
                ctk.CTkLabel(card, text=cam_txt, font=("Arial", 9, "italic"), text_color="#A89F91").pack(pady=1)

            btn_action = ctk.CTkButton(
                card, text="Gestionar", fg_color="#F4EFE6", text_color="#191715",
                hover_color="#E0DACF", height=26, font=("Arial", 11, "bold"),
                command=lambda h=hab: self.procesar_click_habitacion(h)
            )
            btn_action.pack(pady=6)

    def procesar_click_habitacion(self, hab: dict):
        """Enruta la acción según el estado de la habitación."""
        estado = hab["estado"]
        if estado == "Limpia":
            self.modal_checkin(hab)
        elif estado in ["Ocupada", "Tiempo_Vencido"]:
            self.modal_gestionar_ocupada(hab)
        elif estado == "Sucia":
            self.modal_limpieza(hab)

    # =========================================================================
    # MODAL 1: CHECK-IN INTELIGENTE (INDIVIDUAL / PAREJA + RECUPERACIÓN DE DEUDA)
    # =========================================================================
    def modal_checkin(self, hab: dict):
        win = ctk.CTkToplevel(self)
        win.title(f"Check-In - Habitación {hab['codigo']}")
        centrar_ventana(win, 900, 720)
        win.grab_set()

        tasa = obtener_tasa_bcv()

        # Barra Superior de Modalidad de Huéspedes
        frame_modalidad = ctk.CTkFrame(win, fg_color="#23201C", corner_radius=10)
        frame_modalidad.pack(fill="x", padx=15, pady=(10, 5))

        # Switch para Huésped Individual
        sw_individual = ctk.CTkSwitch(
            frame_modalidad, text="👤 Huésped Individual (Sin Acompañante)",
            font=("Arial", 12, "bold"), text_color="#F4EFE6", progress_color="#D4A343",
            command=lambda: toggle_acompanante()
        )
        sw_individual.pack(side="left", padx=15, pady=8)

        frame_dual = ctk.CTkFrame(win, fg_color="#23201C", corner_radius=12)
        frame_dual.pack(fill="both", expand=True, padx=15, pady=5)

        meses_es = [
            "01 - Enero", "02 - Febrero", "03 - Marzo", "04 - Abril",
            "05 - Mayo", "06 - Junio", "07 - Julio", "08 - Agosto",
            "09 - Septiembre", "10 - Octubre", "11 - Noviembre", "12 - Diciembre"
        ]
        dias = [f"{i:02d}" for i in range(1, 32)]
        anio_actual = datetime.now().year
        anios = [str(y) for y in range(anio_actual - 18, 1930, -1)]

        # --- Columna Titular ---
        col_titular = ctk.CTkFrame(frame_dual, fg_color="#2D2924", corner_radius=8)
        col_titular.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        ctk.CTkLabel(col_titular, text="TITULAR PRINCIPAL", font=("Arial", 13, "bold"), text_color="#D4A343").pack(pady=5)

        e_ced = ctk.CTkEntry(col_titular, placeholder_text="Cédula (Sólo dígitos)")
        e_ced.pack(pady=2, fill="x", padx=8)
        e_nom = ctk.CTkEntry(col_titular, placeholder_text="Nombre")
        e_nom.pack(pady=2, fill="x", padx=8)
        e_ape = ctk.CTkEntry(col_titular, placeholder_text="Apellido")
        e_ape.pack(pady=2, fill="x", padx=8)
        e_tel = ctk.CTkEntry(col_titular, placeholder_text="Teléfono")
        e_tel.pack(pady=2, fill="x", padx=8)

        ctk.CTkLabel(col_titular, text="Fecha de Nacimiento:", font=("Arial", 10, "bold"), text_color="#A89F91").pack(anchor="w", padx=8, pady=(4, 0))
        f_nac_t = ctk.CTkFrame(col_titular, fg_color="transparent")
        f_nac_t.pack(fill="x", padx=8, pady=2)

        c_dia_t = ctk.CTkComboBox(f_nac_t, values=dias, width=65); c_dia_t.set("15"); c_dia_t.pack(side="left", padx=1)
        c_mes_t = ctk.CTkComboBox(f_nac_t, values=meses_es, width=120); c_mes_t.set(meses_es[0]); c_mes_t.pack(side="left", padx=1)
        c_anio_t = ctk.CTkComboBox(f_nac_t, values=anios, width=80); c_anio_t.set("2000"); c_anio_t.pack(side="left", padx=1)

        lbl_edad_t = ctk.CTkLabel(col_titular, text="Edad: 24 años", font=("Arial", 11, "bold"), text_color="#D4A343")
        lbl_edad_t.pack(pady=2)

        c_eciv = ctk.CTkComboBox(col_titular, values=["Soltero/a", "Casado/a", "Divorciado/a", "Viudo/a"])
        c_eciv.pack(pady=2, fill="x", padx=8)
        c_nac = ctk.CTkComboBox(col_titular, values=["V", "E"])
        c_nac.pack(pady=2, fill="x", padx=8)
        e_proc = ctk.CTkEntry(col_titular, placeholder_text="Procedencia")
        e_proc.pack(pady=2, fill="x", padx=8)
        e_dest = ctk.CTkEntry(col_titular, placeholder_text="Destino")
        e_dest.pack(pady=2, fill="x", padx=8)

        # --- Columna Acompañante ---
        col_acomp = ctk.CTkFrame(frame_dual, fg_color="#2D2924", corner_radius=8)
        col_acomp.pack(side="right", fill="both", expand=True, padx=8, pady=8)
        lbl_acomp_tit = ctk.CTkLabel(col_acomp, text="ACOMPAÑANTE", font=("Arial", 13, "bold"), text_color="#D4A343")
        lbl_acomp_tit.pack(pady=5)

        ac_ced = ctk.CTkEntry(col_acomp, placeholder_text="Cédula Acompañante")
        ac_ced.pack(pady=2, fill="x", padx=8)
        ac_nom = ctk.CTkEntry(col_acomp, placeholder_text="Nombre Acompañante")
        ac_nom.pack(pady=2, fill="x", padx=8)
        ac_ape = ctk.CTkEntry(col_acomp, placeholder_text="Apellido Acompañante")
        ac_ape.pack(pady=2, fill="x", padx=8)

        lbl_f_nac_a = ctk.CTkLabel(col_acomp, text="Fecha de Nacimiento:", font=("Arial", 10, "bold"), text_color="#A89F91")
        lbl_f_nac_a.pack(anchor="w", padx=8, pady=(4, 0))
        f_nac_a = ctk.CTkFrame(col_acomp, fg_color="transparent")
        f_nac_a.pack(fill="x", padx=8, pady=2)

        c_dia_a = ctk.CTkComboBox(f_nac_a, values=dias, width=65); c_dia_a.set("20"); c_dia_a.pack(side="left", padx=1)
        c_mes_a = ctk.CTkComboBox(f_nac_a, values=meses_es, width=120); c_mes_a.set(meses_es[0]); c_mes_a.pack(side="left", padx=1)
        c_anio_a = ctk.CTkComboBox(f_nac_a, values=anios, width=80); c_anio_a.set("2000"); c_anio_a.pack(side="left", padx=1)

        lbl_edad_a = ctk.CTkLabel(col_acomp, text="Edad: 24 años", font=("Arial", 11, "bold"), text_color="#D4A343")
        lbl_edad_a.pack(pady=2)

        ac_eciv = ctk.CTkComboBox(col_acomp, values=["Soltero/a", "Casado/a", "Divorciado/a", "Viudo/a"])
        ac_eciv.pack(pady=2, fill="x", padx=8)
        ac_nac = ctk.CTkComboBox(col_acomp, values=["V", "E"])
        ac_nac.pack(pady=2, fill="x", padx=8)
        ac_proc = ctk.CTkEntry(col_acomp, placeholder_text="Procedencia")
        ac_proc.pack(pady=2, fill="x", padx=8)
        ac_dest = ctk.CTkEntry(col_acomp, placeholder_text="Destino")
        ac_dest.pack(pady=2, fill="x", padx=8)

        def toggle_acompanante():
            """Deshabilita o habilita la columna de acompañante según el switch."""
            es_individual = sw_individual.get()
            estado = "disabled" if es_individual else "normal"
            color_fondo = "#23201C" if es_individual else "#2D2924"

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

        # Panel de Cobro
        frame_pagos = ctk.CTkFrame(win, fg_color="#23201C", corner_radius=12)
        frame_pagos.pack(fill="x", padx=15, pady=5)

        lbl_monto_calc = ctk.CTkLabel(frame_pagos, text="Monto: $0.00 (0,00 Bs)", font=("Arial", 13, "bold"), text_color="#D4A343")
        lbl_monto_calc.grid(row=0, column=0, columnspan=2, pady=6)

        c_tipo = ctk.CTkComboBox(frame_pagos, values=["4h", "24h"], command=lambda v: recalcular())
        c_tipo.grid(row=1, column=0, padx=8, pady=5)

        c_metodo = ctk.CTkComboBox(
            frame_pagos, values=["EFECTIVO USD", "EFECTIVO BS", "PAGO MOVIL", "PUNTO DE VENTA"],
            command=lambda v: toggle_p2p(v)
        )
        c_metodo.grid(row=1, column=1, padx=8, pady=5)

        frame_p2p = ctk.CTkFrame(frame_pagos, fg_color="transparent")
        e_p2p_ref = ctk.CTkEntry(frame_p2p, placeholder_text="Ref (4 dígitos)")
        e_p2p_ref.pack(side="left", padx=2)
        e_p2p_ci = ctk.CTkEntry(frame_p2p, placeholder_text="C.I Titular Pago")
        e_p2p_ci.pack(side="left", padx=2)
        e_p2p_tel = ctk.CTkEntry(frame_p2p, placeholder_text="Teléfono Emisor")
        e_p2p_tel.pack(side="left", padx=2)

        def recalcular():
            duracion = c_tipo.get()
            precio_usd = hab["precio_4h"] if duracion == "4h" else hab["precio_24h"]
            precio_bs = precio_usd * tasa
            lbl_monto_calc.configure(text=f"Total: ${precio_usd:.2f} | {precio_bs:,.2f} Bs (Bloqueado)")

        def toggle_p2p(metodo):
            if metodo == "PAGO MOVIL":
                frame_p2p.grid(row=2, column=0, columnspan=2, pady=5)
            else:
                frame_p2p.grid_forget()

        recalcular()

        def confirmar_checkin():
            es_individual = sw_individual.get()

            if not all([e_ced.get(), e_nom.get(), e_ape.get()]):
                messagebox.showerror("Error", "Los datos del Titular son obligatorios.")
                return
            if not e_ced.get().isdigit():
                messagebox.showerror("Error", "La cédula del Titular debe ser numérica.")
                return

            if not es_individual:
                if not all([ac_ced.get(), ac_nom.get(), ac_ape.get()]):
                    messagebox.showerror("Error", "Complete los datos del Acompañante o active 'Huésped Individual'.")
                    return
                if not ac_ced.get().isdigit():
                    messagebox.showerror("Error", "La cédula del Acompañante debe ser numérica.")
                    return

            # =================================================================
            # INTERCEPCIÓN INTELIGENTE DE MOROSOS: COBRAR DEUDA Y REHABILITAR
            # =================================================================
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
                    messagebox.showerror("Error", "Complete los datos del Pago Móvil.")
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
                messagebox.showinfo("Éxito", f"Check-In procesado en habitación {hab['codigo']}.")
                win.destroy()
                self.actualizar_grid()

        ctk.CTkButton(
            win, text="Confirmar y Cobrar Check-In", fg_color="#D4A343", hover_color="#B8892E",
            text_color="#191715", font=("Arial", 12, "bold"), command=confirmar_checkin
        ).pack(pady=10)

    # =========================================================================
    # MODAL 1.1: RECUPERACIÓN DE DEUDA DE MOROSO EN CHECK-IN
    # =========================================================================
    def modal_recuperar_deuda_moroso(self, moroso_data: dict, callback_continuar_checkin):
        """Abre ventana para cobrar la deuda pendiente del moroso y rehabilitarlo de inmediato."""
        win_deuda = ctk.CTkToplevel(self)
        win_deuda.title("⚠️ Recuperación de Cartera - Cliente en Lista Negra")
        centrar_ventana(win_deuda, 480, 560)
        win_deuda.grab_set()

        tasa = obtener_tasa_bcv()
        cedula = moroso_data["cedula"]
        nombre = moroso_data["nombre"]
        motivo = moroso_data["motivo"]

        ctk.CTkLabel(win_deuda, text="⚠️ Huésped Registrado en Lista Negra", font=("Georgia", 15, "bold"), text_color="#E74C3C").pack(pady=(15, 2))
        ctk.CTkLabel(win_deuda, text=f"Huésped: {nombre} | C.I: {cedula}", font=("Arial", 12, "bold"), text_color="#F4EFE6").pack(pady=2)

        f_info = ctk.CTkFrame(win_deuda, fg_color="#2D2924", corner_radius=8, border_width=1, border_color="#78281F")
        f_info.pack(fill="x", padx=15, pady=8)

        ctk.CTkLabel(f_info, text="Antecedente / Deuda Registrada:", font=("Arial", 10, "bold"), text_color="#D4A343").pack(anchor="w", padx=10, pady=(6, 1))
        ctk.CTkLabel(f_info, text=f'"{motivo}"', font=("Arial", 10, "italic"), text_color="#FADBD8", wraplength=420, justify="left").pack(anchor="w", padx=10, pady=(0, 6))

        # Formulario de Cobro
        f_cobro = ctk.CTkFrame(win_deuda, fg_color="#23201C", corner_radius=10)
        f_cobro.pack(fill="both", expand=True, padx=15, pady=5)

        ctk.CTkLabel(f_cobro, text="Monto de la Deuda a Cobrar ($ USD):", font=("Arial", 11, "bold"), text_color="#D4A343").pack(anchor="w", padx=15, pady=(8, 1))
        e_monto_d = ctk.CTkEntry(f_cobro, placeholder_text="Ej: 20.00", fg_color="#2D2924")
        e_monto_d.pack(fill="x", padx=15, pady=2)

        lbl_bs_d = ctk.CTkLabel(f_cobro, text="Equivalente en Bs: 0,00 Bs", font=("Arial", 11, "bold"), text_color="#7DCEA0")
        lbl_bs_d.pack(anchor="w", padx=15, pady=2)

        def act_bs(event=None):
            try:
                v = float(e_monto_d.get().replace(",", "."))
                lbl_bs_d.configure(text=f"Equivalente en Bs: {formatear_bs(v * tasa)}")
            except ValueError:
                lbl_bs_d.configure(text="Equivalente en Bs: 0,00 Bs")

        e_monto_d.bind("<KeyRelease>", act_bs)

        ctk.CTkLabel(f_cobro, text="Método de Pago de la Deuda:", font=("Arial", 11, "bold"), text_color="#A89F91").pack(anchor="w", padx=15, pady=(6, 1))
        c_met_d = ctk.CTkComboBox(
            f_cobro, values=["EFECTIVO USD", "EFECTIVO BS", "PAGO MOVIL", "PUNTO DE VENTA"],
            command=lambda v: toggle_p2p_deuda(v)
        )
        c_met_d.pack(fill="x", padx=15, pady=2)

        f_p2p_d = ctk.CTkFrame(f_cobro, fg_color="transparent")
        e_ref_d = ctk.CTkEntry(f_p2p_d, placeholder_text="Ref (4 dígitos)", fg_color="#2D2924")
        e_ref_d.pack(side="left", padx=2, fill="x", expand=True)
        e_ci_d = ctk.CTkEntry(f_p2p_d, placeholder_text="C.I. Emisor", fg_color="#2D2924")
        e_ci_d.pack(side="left", padx=2, fill="x", expand=True)
        e_tel_d = ctk.CTkEntry(f_p2p_d, placeholder_text="Teléfono Emisor", fg_color="#2D2924")
        e_tel_d.pack(side="left", padx=2, fill="x", expand=True)

        def toggle_p2p_deuda(metodo):
            if metodo == "PAGO MOVIL":
                f_p2p_d.pack(fill="x", padx=15, pady=4)
            else:
                f_p2p_d.pack_forget()

        def procesar_pago_deuda():
            m_str = e_monto_d.get().strip()
            met = c_met_d.get()
            if not m_str:
                messagebox.showwarning("Atención", "Ingrese el monto cobrado de la deuda.")
                return

            ref, ci_em, tel = None, None, None
            if met == "PAGO MOVIL":
                ref = e_ref_d.get().strip(); ci_em = e_ci_d.get().strip(); tel = e_tel_d.get().strip()
                if not (ref and ci_em and tel):
                    messagebox.showerror("Error", "Complete los datos del Pago Móvil.")
                    return

            try:
                m_flt = float(m_str.replace(",", "."))
                usr = self.controller.usuario_actual["usuario"]
                if liquidar_deuda_moroso_y_rehabilitar(cedula, nombre, motivo, m_flt, met, usr, ref, ci_em, tel):
                    messagebox.showinfo("Éxito", f"Deuda de ${m_flt:.2f} saldada. Huésped rehabilitado en el sistema.")
                    win_deuda.destroy()
                    callback_continuar_checkin()
                else:
                    messagebox.showerror("Error", "No se pudo procesar la liquidación de la deuda.")
            except ValueError:
                messagebox.showerror("Error", "Monto inválido.")

        # Botones de Acción
        f_btns = ctk.CTkFrame(win_deuda, fg_color="transparent")
        f_btns.pack(fill="x", padx=15, pady=10)

        ctk.CTkButton(
            f_btns, text="❌ Rechazar Entrada", fg_color="#78281F", hover_color="#943126",
            width=140, command=win_deuda.destroy
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            f_btns, text="💵 Cobrar Deuda y Habilitar", fg_color="#1E5F38", hover_color="#2E7D32",
            text_color="#F4EFE6", font=("Arial", 11, "bold"), command=procesar_pago_deuda
        ).pack(side="right", fill="x", expand=True, padx=5)

    # =========================================================================
    # MODAL 2: GESTIÓN DE HABITACIÓN OCUPADA (EXTENSIÓN Y CHECK-OUT INTELIGENTE)
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

        ctk.CTkLabel(win, text=f"Habitación: {hab['codigo']}", font=("Georgia", 18, "bold"), text_color="#D4A343").pack(pady=(15, 4))
        ctk.CTkLabel(win, text=f"Huésped: {estancia['nombre']} {estancia['apellido']} (C.I. {estancia['cedula']})", font=("Arial", 11)).pack(pady=1)

        f_in = datetime.strptime(estancia["fecha_entrada"], "%Y-%m-%d %H:%M:%S").strftime("%I:%M %p")
        f_out = datetime.strptime(estancia["fecha_salida_estimada"], "%Y-%m-%d %H:%M:%S").strftime("%I:%M %p")
        ctk.CTkLabel(win, text=f"Entrada: {f_in} | Vence: {f_out}", font=("Arial", 10, "italic"), text_color="#A89F91").pack(pady=4)

        # Marco de Extensión
        frame_ext = ctk.CTkFrame(win, fg_color="#23201C", corner_radius=12)
        frame_ext.pack(fill="x", padx=20, pady=8)

        ctk.CTkLabel(frame_ext, text="⏱️ Extender Tiempo de Alquiler", font=("Arial", 12, "bold"), text_color="#D4A343").pack(pady=4)

        combo_tiempo = ctk.CTkComboBox(frame_ext, values=["+4 Horas", "+24 Horas"], command=lambda v: recalcular_ext())
        combo_tiempo.pack(pady=3)

        lbl_costo_ext = ctk.CTkLabel(frame_ext, text="Costo Extensión: $0.00", font=("Arial", 12, "bold"))
        lbl_costo_ext.pack(pady=3)

        combo_pago_ext = ctk.CTkComboBox(
            frame_ext, values=["EFECTIVO USD", "EFECTIVO BS", "PAGO MOVIL", "PUNTO DE VENTA"],
            command=lambda v: toggle_p2p_ext(v)
        )
        combo_pago_ext.pack(pady=3)

        frame_p2p_ext = ctk.CTkFrame(frame_ext, fg_color="transparent")
        e_ref_ext = ctk.CTkEntry(frame_p2p_ext, placeholder_text="Ref (4 dígitos)", fg_color="#2D2924")
        e_ref_ext.pack(side="left", padx=2)
        e_ci_ext = ctk.CTkEntry(frame_p2p_ext, placeholder_text="C.I. Emisor", fg_color="#2D2924")
        e_ci_ext.pack(side="left", padx=2)
        e_tel_ext = ctk.CTkEntry(frame_p2p_ext, placeholder_text="Teléfono Emisor", fg_color="#2D2924")
        e_tel_ext.pack(side="left", padx=2)

        def toggle_p2p_ext(metodo):
            if metodo == "PAGO MOVIL":
                frame_p2p_ext.pack(fill="x", padx=5, pady=4)
            else:
                frame_p2p_ext.pack_forget()

        def recalcular_ext():
            horas = 4 if combo_tiempo.get() == "+4 Horas" else 24
            p_usd = hab["precio_4h"] if horas == 4 else hab["precio_24h"]
            p_bs = p_usd * tasa
            lbl_costo_ext.configure(text=f"Costo: ${p_usd:.2f} | {p_bs:,.2f} Bs (Bloqueado)")

        recalcular_ext()

        def ejecutar_extension():
            horas_extra = 4 if combo_tiempo.get() == "+4 Horas" else 24
            precio_usd = hab["precio_4h"] if horas_extra == 4 else hab["precio_24h"]
            metodo = combo_pago_ext.get()

            ref, ci, tel = None, None, None
            if metodo == "PAGO MOVIL":
                ref = e_ref_ext.get().strip(); ci = e_ci_ext.get().strip(); tel = e_tel_ext.get().strip()
                if not (ref and ci and tel):
                    messagebox.showerror("Error", "Complete datos de Pago Móvil.")
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
                    f"Extensión en Hab {hab['codigo']} ({combo_tiempo.get()}) a {estancia['nombre']} {estancia['apellido']}. Monto: ${precio_usd:.2f}. Salida: {nueva_salida.strftime('%I:%M %p')}."
                )
                messagebox.showinfo("Éxito", f"Estancia extendida hasta las {nueva_salida.strftime('%I:%M %p')}.")
                win.destroy()
                self.actualizar_grid()

        ctk.CTkButton(frame_ext, text="Confirmar y Cobrar Extensión", fg_color="#D4A343", hover_color="#B8892E", text_color="#191715", font=("Arial", 11, "bold"), command=ejecutar_extension).pack(fill="x", padx=10, pady=8)

        # Sección: Check-Out con opción de Lista Negra en 1 Clic
        sw_bloquear_salida = ctk.CTkCheckBox(
            win, text="🚫 Inhabilitar Huésped en Lista Negra por mala conducta/impago",
            font=("Arial", 11, "bold"), text_color="#E74C3C",
            fg_color="#78281F", hover_color="#943126", checkmark_color="#FFFFFF"
        )
        sw_bloquear_salida.pack(padx=20, pady=(6, 2), anchor="w")

        def ejecutar_checkout():
            if messagebox.askyesno("Confirmar", f"¿Dar salida a la habitación {hab['codigo']}?"):
                if sw_bloquear_salida.get():
                    motivo_txt = f"Inhabilitado al dar salida en Hab {hab['codigo']} por incumplimiento o mala conducta."
                    agregar_moroso(estancia["cedula"], f"{estancia['nombre']} {estancia['apellido']}", motivo_txt)
                    registrar_auditoria(usr_act, rol_act, "BLOQUEAR_CLIENTE", f"Titular {estancia['nombre']} {estancia['apellido']} (C.I: {estancia['cedula']}) enviado a Lista Negra en Check-Out de Hab {hab['codigo']}.")

                if finalizar_estancia_checkout(hab["codigo"]):
                    registrar_auditoria(usr_act, rol_act, "CHECK_OUT", f"Check-Out en Hab {hab['codigo']}. Ocupante: {estancia['nombre']} {estancia['apellido']}. Pasa a estado 'Sucia'.")
                    messagebox.showinfo("Éxito", "Check-Out procesado. Habitación en estado Sucia.")
                    win.destroy()
                    self.actualizar_grid()

        ctk.CTkButton(win, text="🚪 Dar Salida (Check-Out)", fg_color="#78281F", hover_color="#943126", text_color="#F4EFE6", font=("Arial", 11, "bold"), command=ejecutar_checkout).pack(fill="x", padx=20, pady=10)

    # =========================================================================
    # MODAL 3: LIMPIEZA Y HABILITACIÓN DE HABITACIÓN (CON AUDITORÍA Y SLA)
    # =========================================================================
    def modal_limpieza(self, hab: dict):
        win = ctk.CTkToplevel(self)
        win.title(f"Limpieza - {hab['codigo']}")
        centrar_ventana(win, 380, 260)
        win.grab_set()

        ctk.CTkLabel(win, text=f"Limpieza de Habitación {hab['codigo']}", font=("Georgia", 14, "bold"), text_color="#D4A343").pack(pady=10)
        e_cam = ctk.CTkEntry(win, placeholder_text="Nombre Completo de la Camarera", fg_color="#2D2924")
        e_cam.pack(pady=5, padx=20, fill="x")

        c_turno = ctk.CTkComboBox(win, values=["MAÑANA", "NOCHE"])
        c_turno.pack(pady=5, padx=20, fill="x")

        def liberar():
            camarera = e_cam.get().strip()
            turno = c_turno.get()
            if not camarera:
                messagebox.showwarning("Atención", "Ingrese el nombre de la camarera.")
                return

            if registrar_liberacion_limpieza(hab["codigo"], camarera, turno):
                registrar_auditoria(
                    self.controller.usuario_actual["usuario"], self.controller.usuario_actual["rol"], "LIMPIEZA_HABITACION",
                    f"Habitación {hab['codigo']} limpiada y habilitada a 'Limpia'. Camarera: {camarera.upper()} (Turno {turno})."
                )
                messagebox.showinfo("Éxito", f"Habitación {hab['codigo']} lista y asignada a {camarera.upper()}.")
                win.destroy()
                self.actualizar_grid()
            else:
                messagebox.showerror("Error", "No se pudo registrar la limpieza.")

        ctk.CTkButton(win, text="✅ Habilitar como Limpia (Verde)", fg_color="#1E5F38", hover_color="#2E7D32", font=("Arial", 11, "bold"), command=liberar).pack(pady=15, padx=20, fill="x")

    # =========================================================================
    # MODAL 4: ADMINISTRACIÓN DE TARIFAS Y HABITACIONES (ADMINISTRADOR)
    # =========================================================================
    def modal_administrar_habitaciones(self):
        win = ctk.CTkToplevel(self)
        win.title("Administración de Tarifas y Habitaciones")
        centrar_ventana(win, 700, 520)
        win.grab_set()

        usr_act = self.controller.usuario_actual["usuario"]
        rol_act = self.controller.usuario_actual["rol"]

        ctk.CTkLabel(win, text="⚙️ Tarifario y Configuración de Habitaciones", font=("Georgia", 16, "bold"), text_color="#D4A343").pack(pady=(15, 2))
        ctk.CTkLabel(win, text="Modifique precios base en USD ($) o gestione habitaciones existentes", font=("Arial", 10), text_color="#A89F91").pack(pady=(0, 10))

        scroll_habs = ctk.CTkScrollableFrame(win, fg_color="#23201C", label_text="Habitaciones Registradas en el Sistema")
        scroll_habs.pack(fill="both", expand=True, padx=20, pady=10)

        def cargar_lista():
            for w in scroll_habs.winfo_children(): w.destroy()
            habs = obtener_habitaciones()
            for h in habs:
                card = ctk.CTkFrame(scroll_habs, fg_color="#2D2924")
                card.pack(fill="x", pady=3, padx=5)

                txt_info = f"Habitación: {h['codigo']} | Tarifa 4h: ${h['precio_4h']:.2f} | Tarifa 24h: ${h['precio_24h']:.2f} | Estado: {h['estado']}"
                ctk.CTkLabel(card, text=txt_info, font=("Arial", 11, "bold"), text_color="#F4EFE6").pack(side="left", padx=12, pady=8)

                btn_del = ctk.CTkButton(card, text="🗑️ Eliminar", fg_color="#78281F", hover_color="#943126", width=75, command=lambda cod=h["codigo"]: ejecutar_eliminar(cod))
                btn_del.pack(side="right", padx=6)

                btn_edit = ctk.CTkButton(card, text="✏️ Modificar Tarifas", fg_color="#3E342B", hover_color="#524539", width=120, command=lambda hab_data=h: abrir_editor_tarifa(hab_data))
                btn_edit.pack(side="right", padx=6)

        def ejecutar_eliminar(cod):
            if messagebox.askyesno("Confirmar", f"¿Está seguro de intentar eliminar la habitación '{cod}'?"):
                exito, mensaje = eliminar_habitacion_segura(cod)
                if exito:
                    registrar_auditoria(usr_act, rol_act, "ELIMINAR_HABITACION", f"Se eliminó la habitación sin historial: '{cod}'.")
                    messagebox.showinfo("Éxito", mensaje)
                    cargar_lista()
                    self.actualizar_grid()
                else:
                    messagebox.showwarning("Acción Bloqueada por Seguridad", mensaje)

        def abrir_editor_tarifa(h_data):
            edit_win = ctk.CTkToplevel(win)
            edit_win.title(f"Tarifas - {h_data['codigo']}")
            centrar_ventana(edit_win, 350, 320)
            edit_win.grab_set()

            ctk.CTkLabel(edit_win, text=f"Modificar Habitación: {h_data['codigo']}", font=("Georgia", 13, "bold"), text_color="#D4A343").pack(pady=(15, 5))
            ed_cod = ctk.CTkEntry(edit_win, fg_color="#2D2924"); ed_cod.insert(0, h_data["codigo"]); ed_cod.pack(fill="x", padx=20, pady=4)
            ed_p4 = ctk.CTkEntry(edit_win, fg_color="#2D2924"); ed_p4.insert(0, f"{h_data['precio_4h']:.2f}"); ed_p4.pack(fill="x", padx=20, pady=4)
            ed_p24 = ctk.CTkEntry(edit_win, fg_color="#2D2924"); ed_p24.insert(0, f"{h_data['precio_24h']:.2f}"); ed_p24.pack(fill="x", padx=20, pady=4)

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
                        registrar_auditoria(usr_act, rol_act, "MODIFICAR_HABITACION", f"Tarifas de Hab {cod_nuevo} actualizadas: 4h=${p4_flt:.2f}, 24h=${p24_flt:.2f}.")
                        messagebox.showinfo("Éxito", f"Tarifas de '{cod_nuevo}' actualizadas correctamente.")
                        edit_win.destroy()
                        cargar_lista()
                        self.actualizar_grid()
                    else:
                        messagebox.showerror("Error", "El código de habitación ya existe.")
                except ValueError:
                    messagebox.showerror("Error", "Los precios deben ser valores numéricos.")

            ctk.CTkButton(edit_win, text="💾 Guardar Nuevas Tarifas", fg_color="#D4A343", hover_color="#B8892E", text_color="#191715", font=("Arial", 11, "bold"), command=guardar_cambios).pack(fill="x", padx=20, pady=15)

        cargar_lista()

    # =========================================================================
    # MODAL 5: AJUSTAR TASA OFICIAL BCV (ADMINISTRADOR)
    # =========================================================================
    def modal_tasa_bcv(self):
        win = ctk.CTkToplevel(self)
        win.title("Ajustar Tasa BCV")
        centrar_ventana(win, 300, 180)
        win.grab_set()

        ctk.CTkLabel(win, text="Nueva Tasa Oficial BCV (Bs/$):", text_color="#D4A343").pack(pady=10)
        e_tasa = ctk.CTkEntry(win, placeholder_text="Ej: 36.50", fg_color="#2D2924")
        e_tasa.pack(pady=5, padx=20, fill="x")

        def guardar():
            try:
                val = float(e_tasa.get().replace(",", "."))
                if actualizar_tasa_bcv(val):
                    registrar_auditoria(
                        self.controller.usuario_actual["usuario"], self.controller.usuario_actual["rol"], "CAMBIO_TASA",
                        f"Actualización de Tasa Oficial BCV establecida en {val:.2f} Bs / USD."
                    )
                    messagebox.showinfo("Éxito", "Tasa BCV actualizada.")
                    win.destroy()
                    self.actualizar_grid()
            except ValueError:
                messagebox.showerror("Error", "Ingrese un valor numérico válido.")

        ctk.CTkButton(win, text="Guardar Tasa", fg_color="#D4A343", hover_color="#B8892E", text_color="#191715", font=("Arial", 11, "bold"), command=guardar).pack(pady=10)

    # =========================================================================
    # MODAL 6: NUEVA HABITACIÓN (ADMINISTRADOR)
    # =========================================================================
    def modal_nueva_habitacion(self):
        win = ctk.CTkToplevel(self)
        win.title("Nueva Habitación")
        centrar_ventana(win, 320, 280)
        win.grab_set()

        e_cod = ctk.CTkEntry(win, placeholder_text="Código (Ej: VIP-01)", fg_color="#2D2924")
        e_cod.pack(pady=5, padx=20, fill="x")
        e_p4 = ctk.CTkEntry(win, placeholder_text="Precio 4 Horas ($)", fg_color="#2D2924")
        e_p4.pack(pady=5, padx=20, fill="x")
        e_p24 = ctk.CTkEntry(win, placeholder_text="Precio 24 Horas ($)", fg_color="#2D2924")
        e_p24.pack(pady=5, padx=20, fill="x")

        def guardar():
            cod, p4, p24 = e_cod.get().strip(), e_p4.get().strip(), e_p24.get().strip()
            if not all([cod, p4, p24]):
                return
            try:
                if agregar_habitacion(cod, float(p4), float(p24)):
                    registrar_auditoria(
                        self.controller.usuario_actual["usuario"], self.controller.usuario_actual["rol"], "CREAR_HABITACION",
                        f"Se creó la habitación '{cod.upper()}' con tarifas: 4h=${float(p4):.2f}, 24h=${float(p24):.2f}."
                    )
                    messagebox.showinfo("Éxito", f"Habitación '{cod.upper()}' creada correctamente.")
                    win.destroy()
                    self.actualizar_grid()
                else:
                    messagebox.showerror("Error", "Código de habitación ya existe.")
            except ValueError:
                messagebox.showerror("Error", "Precios deben ser numéricos.")

        ctk.CTkButton(win, text="Crear Habitación", fg_color="#D4A343", hover_color="#B8892E", text_color="#191715", font=("Arial", 11, "bold"), command=guardar).pack(pady=15)