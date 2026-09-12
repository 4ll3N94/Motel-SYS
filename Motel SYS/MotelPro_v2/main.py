"""
===============================================================================
SISTEMA DE GESTIÓN DE MOTELES - SUITE EJECUTIVA (CORE CONTROLLER)
Módulo: main.py (CONTROLADOR PRINCIPAL, NAVEGACIÓN, RELOJ Y AUDITORÍA DE SESIÓN)
Diseño: Dark Luxury & Enterprise Grade UI
===============================================================================
"""

import os
import shutil
import sys
import customtkinter as ctk
from PIL import Image
from datetime import datetime
from tkinter import messagebox, filedialog

# =============================================================================
# BLINDAJE NIVEL 3: CONTROL DE DEMOSTRACIÓN COMERCIAL (TIME-BOMB)
# =============================================================================
# Define la fecha límite de la demo (Año, Mes, Día, Hora, Minuto)
FECHA_EXPIRACION_DEMO = datetime(2026, 9, 14, 00, 00)  # Ajusta según tu presentación


def verificar_licencia_demo():
    ahora = datetime.now()
    archivo_marca = os.path.join(os.path.expanduser("~"), ".sys_motel_lock.dat")

    # 1. Verificar si la fecha actual ya superó la fecha límite
    if ahora > FECHA_EXPIRACION_DEMO:
        messagebox.showerror(
            "Versión de Demostración Expirada",
            "El período de prueba comercial para este establecimiento ha finalizado.\n\n"
            "Para activar la licencia anual o definitiva y continuar operando,\n"
            "contacte a su proveedor de software.",
        )
        sys.exit(0)

    # 2. Protección contra manipulación del reloj de Windows
    if os.path.exists(archivo_marca):
        try:
            with open(archivo_marca, "r") as f:
                ultima_fecha_str = f.read().strip()
                ultima_fecha = datetime.strptime(ultima_fecha_str, "%Y-%m-%d %H:%M:%S")
                if ahora < ultima_fecha:
                    messagebox.showerror(
                        "Alerta de Seguridad",
                        "Se ha detectado una alteración en la fecha/hora del sistema operativo.\n"
                        "Por motivos de integridad contable y de auditoría, el sistema ha sido bloqueado.",
                    )
                    sys.exit(0)
        except Exception:
            pass

    # Guardar marca de agua temporal oculta
    try:
        with open(archivo_marca, "w") as f:
            f.write(ahora.strftime("%Y-%m-%d %H:%M:%S"))
    except Exception:
        pass


# Ejecutar verificación antes de levantar la interfaz gráfica
verificar_licencia_demo()


# Importaciones de la Capa de Base de Datos
from database.db_manager import (
    inicializar_bd,
    obtener_estancias_activas,
    actualizar_estado_habitacion,
    obtener_ruta_recurso,
    resetear_base_datos,
    registrar_auditoria,
)

# Importaciones de Módulos Operativos
from modules.auth import AuthManager, FrameUsuarios
from modules.habitaciones import FrameHabitaciones
from modules.mercancia import FrameMercancia
from modules.mantenimiento import FrameMantenimiento
from modules.morosos import FrameMorosos
from modules.caja import FrameCaja
from modules.kpis import FrameKPIs
from modules.reportes import FrameReportes
from modules.notificaciones import FrameNotificaciones

# Configuración Global de Apariencia
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")


def centrar_ventana(win, ancho: int, alto: int):
    """Calcula y posiciona la ventana en el centro geométrico del monitor."""
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = max(0, (sw - ancho) // 2)
    y = max(0, (sh - alto) // 2)
    win.geometry(f"{ancho}x{alto}+{x}+{y}")


class Application(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Inicialización de Tablas y Esquemas
        inicializar_bd()

        # Configuración de Ventana Principal
        self.title("SISTEMA DE GESTIÓN HOTELERA & MOTELES - EXECUTIVE SUITE")
        centrar_ventana(self, 1340, 800)
        self.minsize(1180, 720)

        # Paleta de Colores Dark Luxury Corporativa
        self.C_BG_APP = "#0D0C0B"  # Fondo exterior profundo
        self.C_BG_SIDEBAR = "#141311"  # Sidebar ejecutiva
        self.C_BG_CONTENT = "#181614"  # Panel de contenido
        self.C_BORDER = "#292520"  # Bordes sutiles
        self.C_GOLD = "#D4AF37"  # Dorado Champagne
        self.C_GOLD_HOVER = "#B89228"
        self.C_TEXT_MAIN = "#F5EFEB"
        self.C_TEXT_MUTED = "#8E8880"
        self.C_CARD = "#1D1B18"

        self.usuario_actual = None
        self.nav_buttons = {}
        self.vista_actual_nombre = ""

        # Contenedor Base
        self.main_container = ctk.CTkFrame(self, fg_color=self.C_BG_APP)
        self.main_container.pack(fill="both", expand=True)

        self.mostrar_login()

    # =========================================================================
    # PANTALLA DE ACCESO (LOGIN DE ALTO IMPACTO)
    # =========================================================================
    def mostrar_login(self):
        if self.usuario_actual:
            try:
                registrar_auditoria(
                    self.usuario_actual["usuario"],
                    self.usuario_actual["rol"],
                    "LOGOUT",
                    "Cierre de sesión regular del usuario.",
                )
            except Exception:
                pass
            self.usuario_actual = None

        for w in self.main_container.winfo_children():
            w.destroy()

        self.main_container.unbind("<Configure>")

        # =====================================================================
        # 1. LOCALIZACIÓN EXACTA DE LA IMAGEN (RUTA ABSOLUTA)
        # =====================================================================
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        ruta_fondo = os.path.join(directorio_actual, "fondo_login.jpg")

        # Verificación alternativa si tiene extensión .png o mayúsculas
        if not os.path.exists(ruta_fondo):
            for alternativa in [
                "fondo_login.png",
                "fondo_login.jpeg",
                "FONDO_LOGIN.JPG",
            ]:
                posible_ruta = os.path.join(directorio_actual, alternativa)
                if os.path.exists(posible_ruta):
                    ruta_fondo = posible_ruta
                    break

        self.lbl_fondo = None
        self._img_pil_original = None

        if os.path.exists(ruta_fondo):
            try:
                self._img_pil_original = Image.open(ruta_fondo)

                # Label que cubrirá todo el fondo
                self.lbl_fondo = ctk.CTkLabel(
                    self.main_container, text="", fg_color="transparent"
                )
                self.lbl_fondo.place(x=0, y=0, relwidth=1, relheight=1)

                def redimensionar_fondo(event):
                    if (
                        event.width > 50
                        and event.height > 50
                        and self._img_pil_original
                    ):
                        # Escalado de alta calidad
                        self._img_tk = ctk.CTkImage(
                            light_image=self._img_pil_original,
                            dark_image=self._img_pil_original,
                            size=(event.width, event.height),
                        )
                        self.lbl_fondo.configure(image=self._img_tk)

                self.main_container.bind("<Configure>", redimensionar_fondo)
            except Exception as e:
                messagebox.showwarning(
                    "Aviso de Imagen", f"Error al abrir la imagen:\n{e}"
                )
        else:
            # Mensaje de ayuda si el archivo está en otra carpeta
            print(f"⚠️ [AVISO]: No se encontró la imagen en: {ruta_fondo}")

        # =====================================================================
        # 2. TARJETA DE LOGIN FLOTANTE
        # =====================================================================
        center_box = ctk.CTkFrame(self.main_container, fg_color="transparent")
        center_box.place(relx=0.5, rely=0.5, anchor="center")

        card_login = ctk.CTkFrame(
            center_box,
            width=440,
            height=520,
            fg_color="#141311",
            corner_radius=18,
            border_width=1.5,
            border_color=self.C_GOLD,
        )
        card_login.pack()
        card_login.pack_propagate(False)

        # Logotipo / Escudo Simbólico
        f_badge = ctk.CTkFrame(
            card_login,
            width=56,
            height=56,
            fg_color="#201C16",
            corner_radius=28,
            border_width=1.2,
            border_color=self.C_GOLD,
        )
        f_badge.pack(pady=(35, 10))
        f_badge.pack_propagate(False)
        ctk.CTkLabel(
            f_badge, text="⚜", font=("Georgia", 24), text_color=self.C_GOLD
        ).place(relx=0.5, rely=0.5, anchor="center")

        # Títulos
        ctk.CTkLabel(
            card_login,
            text="SISTEMA DE GESTIÓN",
            font=("Montserrat", 20, "bold"),
            text_color=self.C_GOLD,
        ).pack(pady=(2, 0))
        ctk.CTkLabel(
            card_login,
            text="CONTROL HOTELERO & MOTELES",
            font=("Montserrat", 9, "bold"),
            text_color=self.C_TEXT_MUTED,
        ).pack(pady=(0, 22))

        # Inputs
        f_inputs = ctk.CTkFrame(card_login, fg_color="transparent")
        f_inputs.pack(fill="x", padx=45)

        ctk.CTkLabel(
            f_inputs,
            text="USUARIO DEL SISTEMA",
            font=("Arial", 9, "bold"),
            text_color=self.C_TEXT_MUTED,
        ).pack(anchor="w", pady=(0, 3))
        e_user = ctk.CTkEntry(
            f_inputs,
            placeholder_text="Nombre de usuario",
            height=42,
            corner_radius=8,
            fg_color="#1D1B18",
            border_color=self.C_BORDER,
            text_color=self.C_TEXT_MAIN,
            font=("Arial", 11),
        )
        e_user.pack(fill="x", pady=(0, 14))
        e_user.focus_set()

        ctk.CTkLabel(
            f_inputs,
            text="CONTRASEÑA DE ACCESO",
            font=("Arial", 9, "bold"),
            text_color=self.C_TEXT_MUTED,
        ).pack(anchor="w", pady=(0, 3))
        e_pass = ctk.CTkEntry(
            f_inputs,
            placeholder_text="••••••••••••",
            show="*",
            height=42,
            corner_radius=8,
            fg_color="#1D1B18",
            border_color=self.C_BORDER,
            text_color=self.C_TEXT_MAIN,
            font=("Arial", 11),
        )
        e_pass.pack(fill="x", pady=(0, 18))

        lbl_error = ctk.CTkLabel(
            f_inputs, text="", font=("Arial", 10, "bold"), text_color="#E74C3C"
        )
        lbl_error.pack(anchor="w")

        def intentar_login(event=None):
            if not e_user.winfo_exists() or not e_pass.winfo_exists():
                return
            u = e_user.get().strip()
            p = e_pass.get().strip()

            if not u or not p:
                lbl_error.configure(text="⚠️ Complete ambos campos para ingresar.")
                return

            user_data = AuthManager.validar_login(u, p)
            if user_data:
                self.unbind("<Return>")
                self.usuario_actual = user_data
                self.construir_dashboard()
            else:
                lbl_error.configure(
                    text="❌ Credenciales incorrectas o usuario inactivo."
                )
                e_pass.delete(0, "end")

        e_user.bind("<Return>", intentar_login)
        e_pass.bind("<Return>", intentar_login)
        self.bind("<Return>", intentar_login)

        btn_login = ctk.CTkButton(
            card_login,
            text="Iniciar Turno / Sesión  ➔",
            height=44,
            corner_radius=8,
            fg_color=self.C_GOLD,
            hover_color=self.C_GOLD_HOVER,
            text_color="#100F0D",
            font=("Montserrat", 12, "bold"),
            command=intentar_login,
        )
        btn_login.pack(fill="x", padx=45, pady=(5, 15))

        ctk.CTkLabel(
            card_login,
            text="● BASE DE DATOS LOCAL CIFRADA Y PROTEGIDA",
            font=("Arial", 8, "bold"),
            text_color="#3E8E5A",
        ).pack(side="bottom", pady=12)

    # =========================================================================
    # SUITE DE NAVEGACIÓN Y DASHBOARD PRINCIPAL
    # =========================================================================
    def construir_dashboard(self):
        for w in self.main_container.winfo_children():
            w.destroy()

        # ---------------------------------------------------------------------
        # 1. SIDEBAR LATERAL DE CONTROL
        # ---------------------------------------------------------------------
        self.sidebar = ctk.CTkFrame(
            self.main_container,
            width=270,
            fg_color=self.C_BG_SIDEBAR,
            corner_radius=0,
            border_width=1,
            border_color=self.C_BORDER,
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # ---------------------------------------------------------------------
        # 2. ÁREA DE CONTENIDO DINÁMICO
        # ---------------------------------------------------------------------
        self.content_area = ctk.CTkFrame(
            self.main_container, fg_color=self.C_BG_CONTENT, corner_radius=0
        )
        self.content_area.pack(side="right", fill="both", expand=True)

        # Marca de la Barra Lateral
        f_brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        f_brand.pack(fill="x", padx=16, pady=(18, 10))

        ctk.CTkLabel(
            f_brand,
            text="HOTEL & SUITES",
            font=("Montserrat", 15, "bold"),
            text_color=self.C_GOLD,
        ).pack(anchor="w")
        ctk.CTkLabel(
            f_brand,
            text="Sistema Integral de Control",
            font=("Arial", 9),
            text_color=self.C_TEXT_MUTED,
        ).pack(anchor="w")

        # Tarjeta de Usuario + Turno + Reloj
        card_session = ctk.CTkFrame(
            self.sidebar,
            fg_color=self.C_CARD,
            corner_radius=10,
            border_width=1,
            border_color=self.C_BORDER,
        )
        card_session.pack(fill="x", padx=14, pady=(5, 12))

        # Identificación del Usuario
        f_user_row = ctk.CTkFrame(card_session, fg_color="transparent")
        f_user_row.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            f_user_row,
            text=f"👤 {self.usuario_actual['usuario']}",
            font=("Montserrat", 11, "bold"),
            text_color=self.C_TEXT_MAIN,
        ).pack(side="left")

        rol_tag = self.usuario_actual["rol"].upper()
        col_rol = "#E67E22" if rol_tag == "ADMIN" else "#2ECC71"
        b_rol = ctk.CTkFrame(
            f_user_row,
            fg_color="#181614",
            corner_radius=5,
            border_width=1,
            border_color=col_rol,
        )
        b_rol.pack(side="right")
        ctk.CTkLabel(
            b_rol, text=rol_tag, font=("Arial", 8, "bold"), text_color=col_rol
        ).pack(padx=5, pady=1)

        # Reloj Dinámico con Fecha
        self.lbl_fecha = ctk.CTkLabel(
            card_session, text="", font=("Arial", 9), text_color=self.C_TEXT_MUTED
        )
        self.lbl_fecha.pack(anchor="w", padx=12, pady=(0, 1))

        self.lbl_reloj = ctk.CTkLabel(
            card_session,
            text="",
            font=("Montserrat", 14, "bold"),
            text_color=self.C_GOLD,
        )
        self.lbl_reloj.pack(anchor="w", padx=12, pady=(0, 2))

        # Badge de Turno
        self.lbl_turno = ctk.CTkLabel(
            card_session, text="", font=("Arial", 9, "bold"), text_color="#3498DB"
        )
        self.lbl_turno.pack(anchor="w", padx=12, pady=(0, 10))

        self.actualizar_reloj_y_turno()

        # Menú Scrollable (Para resoluciones compactas)
        self.menu_scroll = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.menu_scroll.pack(fill="both", expand=True, padx=4, pady=0)

        # Generador de Botones de Navegación
        self.nav_buttons = {}

        def crear_boton_menu(texto, frame_class, icon):
            # Usamos un frame contenedor o un botón con padding compuesto
            btn = ctk.CTkButton(
                self.menu_scroll,
                text=f"{icon:<3} {texto}",
                anchor="w",
                height=38,
                corner_radius=8,
                fg_color="transparent",
                hover_color="#26221D",
                text_color=self.C_TEXT_MAIN,
                font=("Arial", 11, "bold"),
                command=lambda f=frame_class, t=texto: self.navegar_a(f, t),
            )
            btn.pack(fill="x", padx=8, pady=2)
            self.nav_buttons[texto] = btn

        # Sección Operativa
        ctk.CTkLabel(
            self.menu_scroll,
            text="OPERACIONES PRINCIPALES",
            font=("Montserrat", 8, "bold"),
            text_color=self.C_TEXT_MUTED,
        ).pack(anchor="w", padx=14, pady=(8, 4))
        crear_boton_menu("Habitaciones", FrameHabitaciones, "🏨")
        crear_boton_menu("Mini-Bar / Mercancía", FrameMercancia, "🛒")
        crear_boton_menu("Mantenimiento y Averías", FrameMantenimiento, "⚙️")
        crear_boton_menu("Lista de Morosos", FrameMorosos, "🚫")
        crear_boton_menu("Cierre de Caja", FrameCaja, "🔒")

        # Sección Gerencial / Auditoría
        ctk.CTkLabel(
            self.menu_scroll,
            text="AUDITORÍA & GERENCIA",
            font=("Montserrat", 8, "bold"),
            text_color=self.C_TEXT_MUTED,
        ).pack(anchor="w", padx=14, pady=(14, 4))
        crear_boton_menu("Inteligencia de Negocios (BI)", FrameKPIs, "📈")

        if self.usuario_actual["rol"] == "admin":
            crear_boton_menu("Personal y Accesos", FrameUsuarios, "👥")
            crear_boton_menu("Reportes y Libros SAIME", FrameReportes, "📊")
            crear_boton_menu("Notificaciones y Alertas", FrameNotificaciones, "📲")

            # Herramientas de Mantenimiento de BD
            ctk.CTkLabel(
                self.menu_scroll,
                text="SISTEMA & DATOS",
                font=("Montserrat", 8, "bold"),
                text_color=self.C_TEXT_MUTED,
            ).pack(anchor="w", padx=14, pady=(14, 4))

            ctk.CTkButton(
                self.menu_scroll,
                text="  💾   Respaldar Base Datos",
                anchor="w",
                height=34,
                corner_radius=8,
                fg_color="#211E1B",
                hover_color="#2F2A25",
                text_color=self.C_GOLD,
                font=("Arial", 10, "bold"),
                border_width=1,
                border_color=self.C_BORDER,
                command=self.crear_respaldo_bd,
            ).pack(fill="x", padx=8, pady=3)

            ctk.CTkButton(
                self.menu_scroll,
                text="  ⚠️   Resetear Fábrica",
                anchor="w",
                height=34,
                corner_radius=8,
                fg_color="#2D1715",
                hover_color="#451E1A",
                text_color="#F1948A",
                font=("Arial", 10, "bold"),
                border_width=1,
                border_color="#5B2C27",
                command=self.ejecutar_reseteo_bd,
            ).pack(fill="x", padx=8, pady=3)

        # Botón de Cerrar Sesión Fijo Abajo
        f_bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        f_bottom.pack(side="bottom", fill="x", padx=14, pady=14)

        ctk.CTkButton(
            f_bottom,
            text="🚪  Cerrar Sesión",
            height=38,
            corner_radius=8,
            fg_color="#24201C",
            hover_color="#78281F",
            text_color=self.C_TEXT_MAIN,
            font=("Arial", 11, "bold"),
            border_width=1,
            border_color=self.C_BORDER,
            command=self.mostrar_login,
        ).pack(fill="x")

        # Cargar vista por defecto e iniciar monitores
        self.navegar_a(FrameHabitaciones, "Habitaciones")
        self.verificar_tiempos_vencidos()

    # =========================================================================
    # NAVEGACIÓN Y CONTROLADOR DE VISTAS
    # =========================================================================
    def navegar_a(self, FrameClass, texto_btn):
        self.vista_actual_nombre = texto_btn

        for t, btn in self.nav_buttons.items():
            if t == texto_btn:
                btn.configure(
                    fg_color=self.C_GOLD,
                    text_color="#100F0D",
                    hover_color=self.C_GOLD_HOVER,
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=self.C_TEXT_MAIN,
                    hover_color="#26221D",
                )

        for w in self.content_area.winfo_children():
            w.destroy()

        frame = FrameClass(self.content_area, self)
        frame.pack(fill="both", expand=True)

    # =========================================================================
    # RELOJ Y DETERMINACIÓN DINÁMICA DE TURNO
    # =========================================================================
    def actualizar_reloj_y_turno(self):
        try:
            if hasattr(self, "lbl_reloj") and self.lbl_reloj.winfo_exists():
                ahora = datetime.now()

                # 1. Mapeo en español garantizado
                dias_es = [
                    "Lunes",
                    "Martes",
                    "Miércoles",
                    "Jueves",
                    "Viernes",
                    "Sábado",
                    "Domingo",
                ]
                meses_es = [
                    "Ene",
                    "Feb",
                    "Mar",
                    "Abr",
                    "May",
                    "Jun",
                    "Jul",
                    "Ago",
                    "Sep",
                    "Oct",
                    "Nov",
                    "Dic",
                ]

                nombre_dia = dias_es[ahora.weekday()]
                nombre_mes = meses_es[ahora.month - 1]

                # Formato resultante: "Jueves, 12 Oct 2026"
                fecha_espanol = (
                    f"{nombre_dia}, {ahora.day:02d} {nombre_mes} {ahora.year}"
                )

                # 2. Actualizar etiquetas en la interfaz
                self.lbl_reloj.configure(text=ahora.strftime("%I:%M:%S %p"))
                self.lbl_fecha.configure(text=fecha_espanol)

                # 3. Turno contable
                turno = "☀️ TURNO MAÑANA" if 8 <= ahora.hour < 17 else "🌙 TURNO NOCHE"
                self.lbl_turno.configure(text=turno)

                self.after(1000, self.actualizar_reloj_y_turno)
        except Exception:
            pass

    # =========================================================================
    # ALERTA VIOLETA Y REVISIÓN PERIÓDICA DE TIEMPOS
    # =========================================================================
    def verificar_tiempos_vencidos(self):
        """Monitorea habitaciones activas y activa 'Tiempo_Vencido' si superan el check-out."""
        try:
            if (
                not self.usuario_actual
                or not hasattr(self, "content_area")
                or not self.content_area.winfo_exists()
            ):
                return

            estancias = obtener_estancias_activas()
            ahora = datetime.now()
            cambio_detectado = False

            for est in estancias:
                try:
                    salida_est = datetime.strptime(
                        est["fecha_salida_estimada"], "%Y-%m-%d %H:%M:%S"
                    )
                    if ahora >= salida_est:
                        actualizar_estado_habitacion(
                            est["hab_codigo"], "Tiempo_Vencido"
                        )
                        cambio_detectado = True
                except Exception:
                    pass

            # Si la vista activa es Habitaciones y hubo cambios, invocar refresco
            if cambio_detectado and self.vista_actual_nombre == "Habitaciones":
                hijos = self.content_area.winfo_children()
                if hijos and hasattr(hijos[0], "cargar_datos_y_renderizar"):
                    hijos[0].cargar_datos_y_renderizar(forzar_redibujado=True)

            self.after(6000, self.verificar_tiempos_vencidos)
        except Exception:
            pass

    # =========================================================================
    # RESPALDO SEGURO Y RESTAURACIÓN DE BASE DE DATOS
    # =========================================================================
    def crear_respaldo_bd(self):
        usr_act = self.usuario_actual["usuario"]
        rol_act = self.usuario_actual["rol"]

        # Importamos la función segura
        from database.db_manager import generar_respaldo_seguro

        # Nombre sugerido con fecha y hora contable
        nombre_sugerido = (
            f"Respaldo_Motel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        )

        # Diálogo nativo de Windows / SO
        ruta_destino = filedialog.asksaveasfilename(
            title="Seleccionar Ubicación para Copia de Seguridad",
            initialfile=nombre_sugerido,
            defaultextension=".db",
            filetypes=[
                ("Base de Datos SQLite (*.db)", "*.db"),
                ("Todos los archivos", "*.*"),
            ],
        )

        # Si el usuario presiona Cancelar
        if not ruta_destino:
            return

        try:
            # Ejecutamos el respaldo en caliente
            if generar_respaldo_seguro(ruta_destino):
                registrar_auditoria(
                    usr_act,
                    rol_act,
                    "CREAR_RESPALDO",
                    f"Respaldo de BD generado exitosamente en: '{os.path.basename(ruta_destino)}'.",
                )
                messagebox.showinfo(
                    "Copia de Seguridad Exitosa",
                    f"El respaldo íntegro del sistema se ha generado con éxito en:\n\n{ruta_destino}",
                )
            else:
                messagebox.showerror(
                    "Error de Respaldo",
                    "No se pudo completar el volcado de la base de datos. Verifique los permisos del directorio seleccionado.",
                )
        except Exception as e:
            messagebox.showerror(
                "Error al Respaldar", f"Ocurrió un error inesperado:\n{e}"
            )

    def ejecutar_reseteo_bd(self):
        usr_act = self.usuario_actual["usuario"]
        rol_act = self.usuario_actual["rol"]

        confirmar = messagebox.askyesno(
            "ADVERTENCIA CRÍTICA DE RESETEO",
            "¿Está seguro de querer RESTABLECER DE FÁBRICA la base de datos?\n\n"
            "⚠️ Esta acción eliminará todas las transacciones, auditorías, clientes y ventas registradas.\n"
            "Esta operación NO se puede deshacer.",
            icon="warning",
        )

        if confirmar:
            registrar_auditoria(
                usr_act,
                rol_act,
                "RESETEO_BD",
                "Restablecimiento de fábrica ejecutado por Administrador.",
            )
            if resetear_base_datos():
                messagebox.showinfo(
                    "Sistema Restaurado",
                    "La base de datos fue reinicializada con los valores por defecto.",
                )
                self.mostrar_login()
            else:
                messagebox.showerror(
                    "Error", "Ocurrió una falla al intentar resetear la base de datos."
                )


if __name__ == "__main__":
    app = Application()
    app.mainloop()
