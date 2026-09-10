"""
===============================================================================
SISTEMA DE GESTIÓN DE MOTELES -
Módulo: main.py (CONTROLADOR PRINCIPAL, NAVEGACIÓN, RELOJ Y AUDITORÍA DE SESIÓN)
===============================================================================
"""

import shutil
import customtkinter as ctk
from datetime import datetime
from tkinter import messagebox
from modules.mantenimiento import FrameMantenimiento
from modules.kpis import FrameKPIs
from modules.notificaciones import FrameNotificaciones

# Importaciones desde la Capa de Datos (Incluyendo motor de auditoría)
from database.db_manager import (
    inicializar_bd, obtener_estancias_activas, actualizar_estado_habitacion,
    resetear_base_datos, registrar_auditoria
)
from modules.auth import AuthManager, FrameUsuarios
from modules.habitaciones import FrameHabitaciones
from modules.mercancia import FrameMercancia
from modules.morosos import FrameMorosos
from modules.caja import FrameCaja
from modules.reportes import FrameReportes

# Configuración Visual Global
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")


def centrar_ventana(win, ancho: int, alto: int):
    """Calcula y posiciona la ventana en el centro del monitor."""
    win.update_idletasks()
    pantalla_ancho = win.winfo_screenwidth()
    pantalla_alto = win.winfo_screenheight()
    x = max(0, (pantalla_ancho - ancho) // 2)
    y = max(0, (pantalla_alto - alto) // 2)
    win.geometry(f"{ancho}x{alto}+{x}+{y}")


class Application(ctk.CTk):
    def __init__(self):
        super().__init__()

        inicializar_bd()

        self.title("SISTEMA DE GESTIÓN DE MOTELES")
        centrar_ventana(self, 1320, 780)
        self.minsize(1120, 700)

        self.usuario_actual = None
        self.vista_actual_btn = None

        # Contenedor Principal (Fondo Espresso Cálido)
        self.main_container = ctk.CTkFrame(self, fg_color="#191715")
        self.main_container.pack(fill="both", expand=True)

        self.mostrar_login()

    # =========================================================================
    # LOGIN (CON ENTER Y AUDITORÍA DE ACCESO)
    # =========================================================================
    def mostrar_login(self):
        # Si había una sesión activa, auditar el cierre de sesión
        if self.usuario_actual:
            registrar_auditoria(
                self.usuario_actual["usuario"], self.usuario_actual["rol"],
                "LOGOUT", "Cierre de sesión manual del usuario."
            )
            self.usuario_actual = None

        for widget in self.main_container.winfo_children():
            widget.destroy()

        card_login = ctk.CTkFrame(
            self.main_container, width=400, height=450,
            fg_color="#23201C", corner_radius=16,
            border_width=1, border_color="#38332C"
        )
        card_login.place(relx=0.5, rely=0.5, anchor="center")
        card_login.pack_propagate(False)

        ctk.CTkLabel(card_login, text="MOTEL EL EDEN", font=("Georgia", 24, "bold"), text_color="#D4A343").pack(pady=(35, 4))
        ctk.CTkLabel(card_login, text="Inversiones Saibaba C.A. | RIF: J-30250227-6", font=("Arial", 10), text_color="#A89F91").pack(pady=(0, 25))

        e_user = ctk.CTkEntry(
            card_login, placeholder_text="Usuario de Acceso", width=290, height=42,
            corner_radius=8, fg_color="#2D2924", border_color="#443E36", text_color="#F4EFE6"
        )
        e_user.pack(pady=8)
        e_user.focus_set()

        e_pass = ctk.CTkEntry(
            card_login, placeholder_text="Contraseña", show="*", width=290, height=42,
            corner_radius=8, fg_color="#2D2924", border_color="#443E36", text_color="#F4EFE6"
        )
        e_pass.pack(pady=8)

        def intentar_login(event=None):
            # Valida que los campos existan antes de leerlos
            if not e_user.winfo_exists() or not e_pass.winfo_exists():
                return
            u_txt = e_user.get().strip()
            p_txt = e_pass.get().strip()
            user_data = AuthManager.validar_login(u_txt, p_txt)
            if user_data:
                self.unbind("<Return>")
                self.usuario_actual = user_data
                self.construir_dashboard()

        # Vinculación de Tecla Enter
        e_user.bind("<Return>", intentar_login)
        e_pass.bind("<Return>", intentar_login)
        self.bind("<Return>", intentar_login)

        ctk.CTkButton(
            card_login, text="Ingresar al Sistema (Enter ↵)", width=290, height=42,
            corner_radius=8, fg_color="#D4A343", hover_color="#B8892E",
            text_color="#191715", font=("Arial", 13, "bold"), command=intentar_login
        ).pack(pady=25)

    # =========================================================================
    # DASHBOARD EJECUTIVO
    # =========================================================================
    def construir_dashboard(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()

        self.sidebar = ctk.CTkFrame(self.main_container, width=250, fg_color="#23201C", corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.content_area = ctk.CTkFrame(self.main_container, fg_color="#191715", corner_radius=0)
        self.content_area.pack(side="right", fill="both", expand=True)

        ctk.CTkLabel(self.sidebar, text="MOTEL EL EDEN", font=("Georgia", 18, "bold"), text_color="#D4A343").pack(pady=(20, 2))
        
        # Tarjeta de Usuario y Rol
        card_user = ctk.CTkFrame(self.sidebar, fg_color="#2D2924", corner_radius=8, border_width=1, border_color="#3D372F")
        card_user.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(card_user, text=f"👤 {self.usuario_actual['usuario']}", font=("Arial", 11, "bold"), text_color="#F4EFE6").pack(pady=(6, 1))
        
        rol_color = "#E59866" if self.usuario_actual['rol'] == 'admin' else "#7DCEA0"
        ctk.CTkLabel(card_user, text=f"ROL: {self.usuario_actual['rol'].upper()}", font=("Arial", 9, "bold"), text_color=rol_color).pack(pady=(0, 6))

        # Tarjeta Reloj Digital
        card_reloj = ctk.CTkFrame(self.sidebar, fg_color="#1A1815", corner_radius=8, border_width=1, border_color="#36312B")
        card_reloj.pack(fill="x", padx=15, pady=4)
        self.lbl_reloj = ctk.CTkLabel(card_reloj, text="", font=("Arial", 13, "bold"), text_color="#F5CBA7")
        self.lbl_reloj.pack(pady=6)
        self.actualizar_reloj()

        # Botones de Navegación
        self.nav_buttons = {}

        def crear_btn_nav(texto, frame_class, icon):
            btn = ctk.CTkButton(
                self.sidebar, text=f"  {icon}  {texto}", anchor="w", height=38, corner_radius=8,
                fg_color="transparent", hover_color="#2F2B25", text_color="#E6DFD5", font=("Arial", 12),
                command=lambda f=frame_class, t=texto: self.navegar_a(f, t)
            )
            btn.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[texto] = btn

        crear_btn_nav("Habitaciones", FrameHabitaciones, "🏨")
        crear_btn_nav("Venta de Mercancía", FrameMercancia, "🛒")
        crear_btn_nav("Mantenimiento y Daños", FrameMantenimiento, "🛠️")
        crear_btn_nav("Lista Negra / Morosos", FrameMorosos, "🚫")
        crear_btn_nav("Cierre de Caja", FrameCaja, "🔒")
        crear_btn_nav("Dashboard de KPIs (BI)", FrameKPIs, "📈") 

        if self.usuario_actual["rol"] == "admin":
            crear_btn_nav("Gestión Personal", FrameUsuarios, "👥")
            crear_btn_nav("Reportes y Auditoría", FrameReportes, "📊")
            crear_btn_nav("Alertas Teléfono / Canales", FrameNotificaciones, "📲")

            ctk.CTkButton(
                self.sidebar, text="  💾  Crear Respaldo BD", anchor="w", height=35, corner_radius=8,
                fg_color="#3E342B", hover_color="#524539", text_color="#F5CBA7", command=self.crear_respaldo_bd
            ).pack(fill="x", padx=12, pady=(15, 3))

        #       self.sidebar, text="  ⚠️  Resetear Base Datos", anchor="w", height=35, corner_radius=8,
        #        fg_color="#78281F", hover_color="#943126", text_color="#FADBD8", command=self.ejecutar_reseteo_bd
        #   ).pack(fill="x", padx=12, pady=3)

        ctk.CTkButton(
            self.sidebar, text="🚪 Cerrar Sesión", height=38, corner_radius=8,
            fg_color="#2D2924", hover_color="#78281F", text_color="#E6DFD5", command=self.mostrar_login
        ).pack(side="bottom", fill="x", padx=12, pady=15)

        self.navegar_a(FrameHabitaciones, "Habitaciones")
        self.verificar_tiempos_vencidos()

    def navegar_a(self, FrameClass, texto_btn):
        for t, btn in self.nav_buttons.items():
            if t == texto_btn:
                btn.configure(fg_color="#D4A343", text_color="#191715", font=("Arial", 12, "bold"))
            else:
                btn.configure(fg_color="transparent", text_color="#E6DFD5", font=("Arial", 12))

        for widget in self.content_area.winfo_children():
            widget.destroy()

        frame = FrameClass(self.content_area, self)
        frame.pack(fill="both", expand=True)

    def actualizar_reloj(self):
        try:
            if hasattr(self, 'lbl_reloj') and self.lbl_reloj.winfo_exists():
                self.lbl_reloj.configure(text=datetime.now().strftime("%I:%M:%S %p"))
                self.after(1000, self.actualizar_reloj)
        except Exception:
            pass

    def verificar_tiempos_vencidos(self):
        """Monitorea continuamente estancias activas para activar la Alarma Violeta de forma segura."""
        try:
            # 1. Si no hay sesión activa o la pantalla fue destruida, detener el ciclo
            if not self.usuario_actual or not hasattr(self, 'content_area') or not self.content_area.winfo_exists():
                return

            estancias = obtener_estancias_activas()
            ahora = datetime.now()

            for est in estancias:
                salida_est = datetime.strptime(est["fecha_salida_estimada"], "%Y-%m-%d %H:%M:%S")
                if ahora >= salida_est:
                    actualizar_estado_habitacion(est["hab_codigo"], "Tiempo_Vencido")

            # 2. Refrescar el grid únicamente si la vista activa es Habitaciones
            hijos = self.content_area.winfo_children()
            if hijos and hasattr(hijos[0], 'actualizar_grid'):
                hijos[0].actualizar_grid()

            # 3. Re-encolar la siguiente comprobación en 5 segundos
            self.after(5000, self.verificar_tiempos_vencidos)
        except Exception:
            pass  # Evita excepciones si el usuario cambia de pantalla o cierra sesión

    def crear_respaldo_bd(self):
        usr_act = self.usuario_actual["usuario"]
        rol_act = self.usuario_actual["rol"]
        try:
            filename = f"backup_motel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copyfile("database/motel_profesional.db", filename)
            
            # AUDITORÍA DE RESPALDO
            registrar_auditoria(usr_act, rol_act, "CREAR_RESPALDO", f"Se generó una copia de seguridad exitosa del sistema: '{filename}'.")
            messagebox.showinfo("Respaldo", f"Copia de seguridad guardada como:\n'{filename}'")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear el respaldo: {e}")

    def ejecutar_reseteo_bd(self):
        usr_act = self.usuario_actual["usuario"]
        rol_act = self.usuario_actual["rol"]

        if messagebox.askyesno("CONFIRMACIÓN CRÍTICA", "¿Está seguro de vaciar la BD? Se borrarán todos los datos transaccionales."):
            # AUDITORÍA DE RESETEO DE BASE DE DATOS
            registrar_auditoria(usr_act, rol_act, "RESETEO_BD", "Se ejecutó un restablecimiento de fábrica de la base de datos.")
            if resetear_base_datos():
                messagebox.showinfo("Éxito", "Base de datos restaurada de fábrica.")
                self.mostrar_login()


if __name__ == "__main__":
    app = Application()
    app.mainloop()