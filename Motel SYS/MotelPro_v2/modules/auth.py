"""
===============================================================================
              SISTEMA DE GESTIÓN DE MOTELES
Módulo: modules/auth.py (CONTROL DE ACCESOS, ROLES Y TRAZABILIDAD DE SEGURIDAD)
Diseño: Dark Luxury & Enterprise Access Control Hub (PDF Exclusivo y UTF-8 Seguro)
===============================================================================
"""

import os
import customtkinter as ctk
from tkinter import messagebox
from tkcalendar import DateEntry
from fpdf import FPDF
from datetime import datetime

# Importaciones desde la Capa de Datos (database/db_manager.py)
from database.db_manager import (
    obtener_conexion, hash_clave, obtener_todos_usuarios, actualizar_usuario,
    registrar_auditoria, obtener_logs_auditoria, obtener_ruta_recurso
)


def _sanitizar_fpdf(texto: str) -> str:
    """
    Reemplaza caracteres conflictivos (como viñetas '•', flechas o comillas curvas)
    y fuerza la compatibilidad con el encoding latin-1 que exige FPDF.
    """
    if not texto:
        return ""
    reemplazos = {
        "\u2022": "-",      # Viñeta / punto medio
        "\u2013": "-",      # Guion en
        "\u2014": "-",      # Guion em
        "\u2018": "'",      # Comilla curva simple izq
        "\u2019": "'",      # Comilla curva simple der
        "\u201c": '"',      # Comilla curva doble izq
        "\u201d": '"',      # Comilla curva doble der
        "\u2794": "->",     # Flecha
        "\u2192": "->",     # Flecha derecha
        "…": "...",
    }
    for orig, dest in reemplazos.items():
        texto = texto.replace(orig, dest)

    # Forzar codificación segura para evitar caídas en caracteres extraños
    return texto.encode("latin-1", errors="ignore").decode("latin-1")


# =============================================================================
# GENERADOR DEL REPORTE PDF DE AUDITORÍA FORENSE (COMPATIBLE CON LATIN-1)
# =============================================================================
class PDFReporteAuditoria(FPDF):
    def __init__(self):
        super().__init__(orientation='L', unit='mm', format='A4')
        self.set_margins(10, 10, 10)
        self.set_auto_page_break(auto=True, margin=12)

    def header(self):
        logo = obtener_ruta_recurso("logo_hotel.png")
        if os.path.exists(logo):
            self.image(logo, x=10, y=5, w=15)

        self.set_font("Helvetica", "B", 12)
        self.cell(0, 5, _sanitizar_fpdf("INVERSIONES SAIBABA C.A. - MOTEL EL EDEN"), 0, 1, "C")
        self.set_font("Helvetica", "B", 9)
        self.cell(0, 4.5, _sanitizar_fpdf("RIF: J-30250227-6 | LIBRO DE AUDITORÍA INTERNA Y TRAZABILIDAD DE OPERACIONES"), 0, 1, "C")
        self.set_y(26)

        # Encabezado de tabla
        self.set_fill_color(33, 30, 27)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 8)
        self.cell(32, 7, "FECHA / HORA", 1, 0, "C", fill=True)
        self.cell(26, 7, "OPERADOR", 1, 0, "C", fill=True)
        self.cell(22, 7, "NIVEL ROL", 1, 0, "C", fill=True)
        self.cell(34, 7, _sanitizar_fpdf("ACCIÓN"), 1, 0, "C", fill=True)
        self.cell(163, 7, _sanitizar_fpdf("DESCRIPCIÓN DETALLADA DEL EVENTO REGISTRADO"), 1, 0, "L", fill=True)
        self.ln()
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        # Reemplazado '•' por '-' para evitar el UnicodeEncodeError
        self.cell(0, 8, _sanitizar_fpdf(f"Auditoría Forense y de Seguridad - Página {self.page_no()}"), 0, 0, "C")


class AuthManager:
    @staticmethod
    def validar_login(usuario: str, clave: str) -> dict | None:
        if not usuario or not clave:
            messagebox.showwarning("Atención", "Ingrese usuario y contraseña.")
            return None

        clave_hash = hash_clave(clave)
        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT id, cedula, nombre, apellido, usuario, rol 
                FROM usuarios 
                WHERE usuario = ? AND clave = ?;
            """, (usuario.strip(), clave_hash))
            user = cursor.fetchone()
            if user:
                user_dict = dict(user)
                registrar_auditoria(user_dict["usuario"], user_dict["rol"], "LOGIN", "Inicio de sesión regular y autenticación satisfactoria.")
                return user_dict
            else:
                registrar_auditoria(usuario.strip(), "DESCONOCIDO", "LOGIN_FALLIDO", f"Intento fallido de autenticación para la cuenta: '{usuario}'.")
                messagebox.showerror("Acceso Denegado", "Usuario o credenciales de acceso inválidas.")
                return None
        finally:
            conn.close()


class FrameUsuarios(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#100F0D")
        self.controller = controller

        # =====================================================================
        # CONSTANTES DE DISEÑO - PALETA LUXURY BOUTIQUE
        # =====================================================================
        self.C_BG = "#100F0D"
        self.C_PANEL = "#161513"
        self.C_CARD = "#1E1C19"
        self.C_INPUT = "#26231F"
        self.C_BORDER = "#2E2A25"
        self.C_GOLD = "#D4AF37"
        self.C_GOLD_HOVER = "#B89228"
        self.C_GREEN = "#2ECC71"
        self.C_RED = "#E74C3C"
        self.C_BLUE = "#3498DB"
        self.C_TEXT_MAIN = "#F5EFEB"
        self.C_TEXT_MUTED = "#8E8880"

        # Barra Superior: Segmented Control
        self.frame_nav = ctk.CTkFrame(self, fg_color=self.C_PANEL, corner_radius=14, border_width=1, border_color=self.C_BORDER)
        self.frame_nav.pack(fill="x", padx=16, pady=(16, 8))

        f_tit = ctk.CTkFrame(self.frame_nav, fg_color="transparent")
        f_tit.pack(side="left", padx=18, pady=12)

        ctk.CTkLabel(
            f_tit, text="SEGURIDAD, PERSONAL Y AUDITORÍA",
            font=("Montserrat", 14, "bold"), text_color=self.C_GOLD
        ).pack(anchor="w")

        ctk.CTkLabel(
            f_tit, text="Gestión de operadores, niveles RBAC y trazabilidad histórica de eventos",
            font=("Arial", 9), text_color=self.C_TEXT_MUTED
        ).pack(anchor="w")

        self.tab_selector = ctk.CTkSegmentedButton(
            self.frame_nav, values=["👥 Gestión de Usuarios", "🛡️ Bitácora de Auditoría"],
            selected_color=self.C_GOLD, selected_hover_color=self.C_GOLD_HOVER,
            unselected_color=self.C_CARD, unselected_hover_color="#B9680B",
            text_color="#F5F4F2", font=("Arial", 11, "bold"),
            command=self.cambiar_pestana
        )
        self.tab_selector.set("👥 Gestión de Usuarios")
        self.tab_selector.pack(side="right", padx=18, pady=12)

        # Contenedor Dinámico
        self.container_pestanas = ctk.CTkFrame(self, fg_color="transparent")
        self.container_pestanas.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        self.usuario_id_edicion = None
        self.ver_clave_activa = False
        self.usuarios_cache = []

        self.construir_pestana_usuarios()

    def cambiar_pestana(self, pestana):
        for w in self.container_pestanas.winfo_children():
            w.destroy()

        if "Usuarios" in pestana:
            self.construir_pestana_usuarios()
        else:
            self.construir_pestana_auditoria()

    # =========================================================================
    # PESTAÑA 1: GESTIÓN DE PERSONAL Y OPERADORES
    # =========================================================================
    def construir_pestana_usuarios(self):
        self.container_pestanas.grid_columnconfigure(0, weight=4)
        self.container_pestanas.grid_columnconfigure(1, weight=6)
        self.container_pestanas.grid_rowconfigure(0, weight=1)

        # ---------------------------------------------------------------------
        # FORMULARIO IZQUIERDO: ALTA Y MODIFICACIÓN
        # ---------------------------------------------------------------------
        self.frame_form = ctk.CTkFrame(
            self.container_pestanas, fg_color=self.C_PANEL, corner_radius=14,
            border_width=1, border_color=self.C_BORDER
        )
        self.frame_form.grid(row=0, column=0, padx=(0, 8), pady=4, sticky="nsew")

        f_top_f = ctk.CTkFrame(self.frame_form, fg_color="transparent")
        f_top_f.pack(fill="x", padx=18, pady=(16, 6))

        self.lbl_titulo_form = ctk.CTkLabel(
            f_top_f, text="REGISTRAR NUEVO OPERADOR",
            font=("Montserrat", 12, "bold"), text_color=self.C_GOLD
        )
        self.lbl_titulo_form.pack(anchor="w")

        ctk.CTkLabel(
            f_top_f, text="Defina credenciales y nivel de acceso en el sistema",
            font=("Arial", 9), text_color=self.C_TEXT_MUTED
        ).pack(anchor="w")

        f_body = ctk.CTkFrame(self.frame_form, fg_color="transparent")
        f_body.pack(fill="both", expand=True, padx=18, pady=(4, 8))

        ctk.CTkLabel(f_body, text="CÉDULA DE IDENTIDAD", font=("Montserrat", 8, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", pady=(2, 1))
        self.txt_cedula = ctk.CTkEntry(f_body, placeholder_text="Sólo números (ej: 19450123)", height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER, font=("Arial", 11))
        self.txt_cedula.pack(pady=(0, 6), fill="x")

        # Fila Nombre y Apellido
        f_row_nom = ctk.CTkFrame(f_body, fg_color="transparent")
        f_row_nom.pack(fill="x", pady=(0, 6))

        f_nom = ctk.CTkFrame(f_row_nom, fg_color="transparent")
        f_nom.pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkLabel(f_nom, text="NOMBRE", font=("Montserrat", 8, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", pady=(0, 1))
        self.txt_nombre = ctk.CTkEntry(f_nom, placeholder_text="Nombre", height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER, font=("Arial", 11))
        self.txt_nombre.pack(fill="x")

        f_ape = ctk.CTkFrame(f_row_nom, fg_color="transparent")
        f_ape.pack(side="right", fill="x", expand=True, padx=(4, 0))
        ctk.CTkLabel(f_ape, text="APELLIDO", font=("Montserrat", 8, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", pady=(0, 1))
        self.txt_apellido = ctk.CTkEntry(f_ape, placeholder_text="Apellido", height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER, font=("Arial", 11))
        self.txt_apellido.pack(fill="x")

        ctk.CTkLabel(f_body, text="CORREO ELECTRÓNICO", font=("Montserrat", 8, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", pady=(2, 1))
        self.txt_correo = ctk.CTkEntry(f_body, placeholder_text="ejemplo@motel.com", height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER, font=("Arial", 11))
        self.txt_correo.pack(pady=(0, 6), fill="x")

        ctk.CTkLabel(f_body, text="TELÉFONO DE CONTACTO", font=("Montserrat", 8, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", pady=(2, 1))
        self.txt_telefono = ctk.CTkEntry(f_body, placeholder_text="04120000000", height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER, font=("Arial", 11))
        self.txt_telefono.pack(pady=(0, 6), fill="x")

        ctk.CTkLabel(f_body, text="USUARIO DE SISTEMA", font=("Montserrat", 8, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", pady=(2, 1))
        self.txt_usuario = ctk.CTkEntry(f_body, placeholder_text="Identificador único para login", height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER, font=("Arial", 11))
        self.txt_usuario.pack(pady=(0, 6), fill="x")

        ctk.CTkLabel(f_body, text="CONTRASEÑA", font=("Montserrat", 8, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", pady=(2, 1))
        f_pass = ctk.CTkFrame(f_body, fg_color="transparent")
        f_pass.pack(fill="x", pady=(0, 6))

        self.txt_clave = ctk.CTkEntry(
            f_pass, placeholder_text="Contraseña segura (Vacío = Mantener)",
            show="*", height=32, fg_color=self.C_INPUT, border_color=self.C_BORDER, font=("Arial", 11)
        )
        self.txt_clave.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.btn_ojito = ctk.CTkButton(
            f_pass, text="👁️", width=38, height=32, fg_color=self.C_CARD,
            hover_color="#2F2A24", border_width=1, border_color=self.C_BORDER,
            command=self.toggle_ver_clave
        )
        self.btn_ojito.pack(side="right")

        ctk.CTkLabel(f_body, text="ROL / PRIVILEGIO OPERATIVO", font=("Montserrat", 8, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", pady=(2, 1))
        self.combo_rol = ctk.CTkComboBox(
            f_body, values=["recepcionista", "admin"], height=32,
            fg_color=self.C_INPUT, border_color=self.C_BORDER, text_color=self.C_TEXT_MAIN,
            dropdown_fg_color=self.C_CARD
        )
        self.combo_rol.set("recepcionista")
        self.combo_rol.pack(pady=(0, 10), fill="x")

        # Botones de Acción
        self.btn_guardar = ctk.CTkButton(
            f_body, text="Crear Operador", fg_color=self.C_GOLD, hover_color=self.C_GOLD_HOVER,
            text_color="#100F0D", font=("Montserrat", 11, "bold"), height=38, corner_radius=8,
            command=self.guardar_usuario
        )
        self.btn_guardar.pack(pady=(4, 4), fill="x")

        self.btn_cancelar = ctk.CTkButton(
            f_body, text="❌ Descartar Edición", fg_color="#3A1714", hover_color=self.C_RED,
            text_color="#FADBD8", font=("Arial", 10, "bold"), height=30, corner_radius=8,
            border_width=1, border_color="#5C201A", command=self.limpiar_campos
        )

        # ---------------------------------------------------------------------
        # DIRECTORIO DERECHO: BUSCADOR Y LISTA SCROLLABLE
        # ---------------------------------------------------------------------
        self.frame_dir = ctk.CTkFrame(
            self.container_pestanas, fg_color=self.C_PANEL, corner_radius=14,
            border_width=1, border_color=self.C_BORDER
        )
        self.frame_dir.grid(row=0, column=1, padx=(8, 0), pady=4, sticky="nsew")

        f_top_dir = ctk.CTkFrame(self.frame_dir, fg_color="transparent")
        f_top_dir.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(
            f_top_dir, text="PLANTILLA DE PERSONAL REGISTRADO",
            font=("Montserrat", 12, "bold"), text_color=self.C_GOLD
        ).pack(side="left")

        self.lbl_cant_usr = ctk.CTkLabel(
            f_top_dir, text="0 Operadores", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED
        )
        self.lbl_cant_usr.pack(side="right")

        # Barra de búsqueda reactiva
        self.e_search_usr = ctk.CTkEntry(
            self.frame_dir, placeholder_text="🔍 Filtrar por nombre, usuario, cédula o rol...",
            height=34, fg_color=self.C_INPUT, border_color=self.C_BORDER,
            text_color=self.C_TEXT_MAIN, font=("Arial", 11)
        )
        self.e_search_usr.pack(fill="x", padx=16, pady=(0, 8))
        self.e_search_usr.bind("<KeyRelease>", lambda e: self.renderizar_lista_usuarios())

        self.scroll_usuarios = ctk.CTkScrollableFrame(self.frame_dir, fg_color=self.C_BG)
        self.scroll_usuarios.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.cargar_usuarios()

    def toggle_ver_clave(self):
        self.ver_clave_activa = not self.ver_clave_activa
        if self.ver_clave_activa:
            self.txt_clave.configure(show="")
            self.btn_ojito.configure(text="🔒")
        else:
            self.txt_clave.configure(show="*")
            self.btn_ojito.configure(text="👁️")

    def guardar_usuario(self):
        cedula = self.txt_cedula.get().strip()
        nombre = self.txt_nombre.get().strip()
        apellido = self.txt_apellido.get().strip()
        correo = self.txt_correo.get().strip()
        telefono = self.txt_telefono.get().strip()
        usuario = self.txt_usuario.get().strip()
        clave = self.txt_clave.get().strip()
        rol = self.combo_rol.get()

        if not all([cedula, nombre, apellido, correo, telefono, usuario]):
            messagebox.showwarning("Atención", "Complete todos los campos obligatorios.")
            return

        if not cedula.isdigit():
            messagebox.showwarning("Atención", "La cédula debe ser estrictamente numérica.")
            return

        admin_act = self.controller.usuario_actual["usuario"]
        rol_act = self.controller.usuario_actual["rol"]

        if self.usuario_id_edicion:
            clave_hash = hash_clave(clave) if clave else None
            if actualizar_usuario(self.usuario_id_edicion, cedula, nombre, apellido, correo, telefono, usuario, clave_hash, rol):
                registrar_auditoria(
                    admin_act, rol_act, "MODIFICAR_USUARIO",
                    f"Datos actualizados del operador '{usuario}' (C.I: {cedula}, Rol: {rol})."
                )
                messagebox.showinfo("Éxito", f"Operador '{usuario}' actualizado correctamente.")
                self.limpiar_campos()
                self.cargar_usuarios()
            else:
                messagebox.showerror("Error", "La cédula o nombre de usuario ya está asignado.")
        else:
            if not clave:
                messagebox.showwarning("Atención", "Debe asignar una contraseña para el nuevo operador.")
                return

            conn = obtener_conexion()
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO usuarios (cedula, nombre, apellido, correo, telefono, usuario, clave, rol)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """, (cedula, nombre, apellido, correo, telefono, usuario, hash_clave(clave), rol))
                conn.commit()
                registrar_auditoria(
                    admin_act, rol_act, "CREAR_USUARIO",
                    f"Nuevo operador creado: '{usuario}' (C.I: {cedula}, Rol: {rol})."
                )
                messagebox.showinfo("Éxito", f"Operador '{usuario}' dado de alta exitosamente.")
                self.limpiar_campos()
                self.cargar_usuarios()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo completar el registro: {e}")
            finally:
                conn.close()

    def seleccionar_para_editar(self, user: dict):
        self.usuario_id_edicion = user["id"]
        for txt, val in [
            (self.txt_cedula, user["cedula"]), (self.txt_nombre, user["nombre"]),
            (self.txt_apellido, user["apellido"]), (self.txt_correo, user["correo"]),
            (self.txt_telefono, user["telefono"]), (self.txt_usuario, user["usuario"])
        ]:
            txt.delete(0, 'end')
            txt.insert(0, val)

        self.txt_clave.delete(0, 'end')
        self.combo_rol.set(user["rol"])

        self.lbl_titulo_form.configure(text=f"MODIFICANDO: {user['usuario'].upper()}")
        self.btn_guardar.configure(text="💾 Guardar Modificaciones", fg_color=self.C_GREEN, hover_color="#27AE60")
        self.btn_cancelar.pack(fill="x", pady=(2, 6))

    def limpiar_campos(self):
        self.usuario_id_edicion = None
        for txt in [self.txt_cedula, self.txt_nombre, self.txt_apellido, self.txt_correo, self.txt_telefono, self.txt_usuario, self.txt_clave]:
            txt.delete(0, 'end')
        self.combo_rol.set("recepcionista")
        self.lbl_titulo_form.configure(text="REGISTRAR NUEVO OPERADOR")
        self.btn_guardar.configure(text="Crear Operador", fg_color=self.C_GOLD, hover_color=self.C_GOLD_HOVER)
        self.btn_cancelar.pack_forget()

    def cargar_usuarios(self):
        self.usuarios_cache = obtener_todos_usuarios()
        self.lbl_cant_usr.configure(text=f"{len(self.usuarios_cache)} Operadores")
        self.renderizar_lista_usuarios()

    def renderizar_lista_usuarios(self):
        for w in self.scroll_usuarios.winfo_children():
            w.destroy()

        query = self.e_search_usr.get().strip().upper()
        filtrados = []

        for u in self.usuarios_cache:
            nom_c = f"{u['nombre']} {u['apellido']}".upper()
            usr = u['usuario'].upper()
            ci = str(u['cedula']).upper()
            rol = u['rol'].upper()

            if query and not any(query in campo for campo in [nom_c, usr, ci, rol]):
                continue
            filtrados.append(u)

        if not filtrados:
            f_empty = ctk.CTkFrame(self.scroll_usuarios, fg_color=self.C_PANEL, corner_radius=10, border_width=1, border_color=self.C_BORDER)
            f_empty.pack(fill="x", pady=25, padx=10)
            ctk.CTkLabel(f_empty, text="🔍 No se encontraron operadores con ese criterio.", font=("Arial", 10, "italic"), text_color=self.C_TEXT_MUTED).pack(pady=15)
            return

        for u in filtrados:
            es_admin = u["rol"].lower() == "admin"
            color_rol = self.C_GOLD if es_admin else self.C_GREEN
            bg_badge = "#2A2416" if es_admin else "#14251B"
            border_badge = "#5C4A21" if es_admin else "#1F4E34"

            card = ctk.CTkFrame(self.scroll_usuarios, fg_color=self.C_CARD, corner_radius=10, border_width=1, border_color=self.C_BORDER)
            card.pack(fill="x", pady=3, padx=2)

            f_izq = ctk.CTkFrame(card, fg_color="transparent")
            f_izq.pack(side="left", fill="both", expand=True, padx=14, pady=10)

            f_top_card = ctk.CTkFrame(f_izq, fg_color="transparent")
            f_top_card.pack(fill="x")

            ctk.CTkLabel(
                f_top_card, text=f"👤 {u['usuario']}",
                font=("Montserrat", 12, "bold"), text_color=self.C_TEXT_MAIN
            ).pack(side="left")

            badge_r = ctk.CTkFrame(f_top_card, fg_color=bg_badge, corner_radius=5, border_width=1, border_color=border_badge)
            badge_r.pack(side="left", padx=10)
            ctk.CTkLabel(badge_r, text=u["rol"].upper(), font=("Arial", 8, "bold"), text_color=color_rol).pack(padx=6, pady=1)

            txt_personal = f"{u['nombre']} {u['apellido']} - C.I: {u['cedula']} - Tel: {u['telefono']}"
            ctk.CTkLabel(f_izq, text=txt_personal, font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", pady=(3, 1))
            ctk.CTkLabel(f_izq, text=f"✉ {u['correo']}", font=("Arial", 9), text_color=self.C_TEXT_MUTED).pack(anchor="w")

            ctk.CTkButton(
                card, text="✏️ Editar", fg_color=self.C_INPUT, hover_color="#363028",
                text_color=self.C_GOLD, font=("Arial", 10, "bold"), width=75, height=30,
                corner_radius=6, border_width=1, border_color=self.C_BORDER,
                command=lambda usr=u: self.seleccionar_para_editar(usr)
            ).pack(side="right", padx=14, pady=10)

    # =========================================================================
    # PESTAÑA 2: AUDITORÍA AVANZADA Y TRAZABILIDAD (SOLO PDF)
    # =========================================================================
    def construir_pestana_auditoria(self):
        frame_filtros = ctk.CTkFrame(
            self.container_pestanas, fg_color=self.C_PANEL, corner_radius=14,
            border_width=1, border_color=self.C_BORDER
        )
        frame_filtros.pack(fill="x", padx=0, pady=(4, 8))

        f_controles = ctk.CTkFrame(frame_filtros, fg_color="transparent")
        f_controles.pack(fill="x", padx=16, pady=12)

        # Filtros de Fecha
        ctk.CTkLabel(f_controles, text="Desde:", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(side="left", padx=4)
        self.cal_aud_ini = DateEntry(
            f_controles, date_pattern='yyyy-mm-dd',
            background="#211E1B", foreground="white", headersbackground="#D4AF37"
        )
        self.cal_aud_ini.pack(side="left", padx=4)

        ctk.CTkLabel(f_controles, text="Hasta:", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(side="left", padx=4)
        self.cal_aud_fin = DateEntry(
            f_controles, date_pattern='yyyy-mm-dd',
            background="#211E1B", foreground="white", headersbackground="#D4AF37"
        )
        self.cal_aud_fin.pack(side="left", padx=4)

        # Filtro de Usuario Dinámico
        ctk.CTkLabel(f_controles, text="Operador:", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(side="left", padx=(10, 4))
        usuarios_lista = ["TODOS"] + [u["usuario"] for u in obtener_todos_usuarios()]
        self.combo_filtro_usuario = ctk.CTkComboBox(
            f_controles, values=usuarios_lista, width=120, height=32,
            fg_color=self.C_INPUT, border_color=self.C_BORDER, text_color=self.C_TEXT_MAIN,
            dropdown_fg_color=self.C_CARD
        )
        self.combo_filtro_usuario.set("TODOS")
        self.combo_filtro_usuario.pack(side="left", padx=4)

        # Filtro de Tipo de Acción
        ctk.CTkLabel(f_controles, text="Acción:", font=("Arial", 10, "bold"), text_color=self.C_TEXT_MUTED).pack(side="left", padx=(10, 4))
        self.combo_filtro_accion = ctk.CTkComboBox(
            f_controles, width=150, height=32,
            fg_color=self.C_INPUT, border_color=self.C_BORDER, text_color=self.C_TEXT_MAIN,
            dropdown_fg_color=self.C_CARD,
            values=[
                "TODAS", "LOGIN", "LOGIN_FALLIDO", "CHECK_IN", "CHECK_OUT",
                "EXTENSION", "VENTA_MINIBAR", "CAMBIO_TASA", "CREAR_USUARIO",
                "MODIFICAR_USUARIO", "BLOQUEAR_CLIENTE", "DESBLOQUEAR_CLIENTE",
                "COBRO_DANO", "CIERRE_TURNO", "CREAR_RESPALDO", "RESETEO_BD"
            ]
        )
        self.combo_filtro_accion.set("TODAS")
        self.combo_filtro_accion.pack(side="left", padx=4)

        ctk.CTkButton(
            f_controles, text="🔍 Filtrar", fg_color=self.C_CARD, hover_color="#2A2621",
            text_color=self.C_GOLD, width=85, height=32, corner_radius=8,
            border_width=1, border_color=self.C_BORDER, font=("Arial", 11, "bold"),
            command=self.cargar_logs_pantalla
        ).pack(side="left", padx=10)

        # Único botón de Exportación (PDF Exclusivo)
        ctk.CTkButton(
            f_controles, text="📄 Exportar a PDF", fg_color="#3A1714", hover_color=self.C_RED,
            text_color="#FADBD8", width=140, height=32, corner_radius=8,
            border_width=1, border_color="#5C201A", font=("Arial", 11, "bold"),
            command=self.exportar_auditoria_pdf
        ).pack(side="right", padx=4)

        # Contenedor Scrollable
        self.scroll_logs = ctk.CTkScrollableFrame(self.container_pestanas, fg_color=self.C_BG)
        self.scroll_logs.pack(fill="both", expand=True, padx=0, pady=(0, 10))

        self.logs_cargados = []
        self.cargar_logs_pantalla()

    def cargar_logs_pantalla(self):
        for w in self.scroll_logs.winfo_children():
            w.destroy()

        f1 = self.cal_aud_ini.get_date().strftime("%Y-%m-%d")
        f2 = self.cal_aud_fin.get_date().strftime("%Y-%m-%d")
        acc = self.combo_filtro_accion.get()
        usr = self.combo_filtro_usuario.get()

        self.logs_cargados = obtener_logs_auditoria(f1, f2, acc, usr)

        if not self.logs_cargados:
            f_empty = ctk.CTkFrame(self.scroll_logs, fg_color=self.C_PANEL, corner_radius=10, border_width=1, border_color=self.C_BORDER)
            f_empty.pack(fill="x", pady=25, padx=10)
            ctk.CTkLabel(f_empty, text="🛡️ No hay eventos de auditoría para los criterios seleccionados.", font=("Arial", 10, "italic"), text_color=self.C_TEXT_MUTED).pack(pady=15)
            return

        badges_temas = {
            "LOGIN": {"bg": "#14251B", "border": "#1F4E34", "txt": "#2ECC71"},
            "LOGIN_FALLIDO": {"bg": "#3A1714", "border": "#5C201A", "txt": "#E74C3C"},
            "CHECK_IN": {"bg": "#2A2416", "border": "#5C4A21", "txt": "#D4AF37"},
            "CHECK_OUT": {"bg": "#2A1D13", "border": "#54331C", "txt": "#E67E22"},
            "EXTENSION": {"bg": "#23182B", "border": "#46225B", "txt": "#9B59B6"},
            "VENTA_MINIBAR": {"bg": "#142028", "border": "#1E3B4C", "txt": "#3498DB"},
            "CIERRE_TURNO": {"bg": "#271629", "border": "#4C1C52", "txt": "#AF7AC5"},
            "COBRO_DANO": {"bg": "#32161B", "border": "#591E28", "txt": "#F1948A"},
            "RESETEO_BD": {"bg": "#3D1313", "border": "#661A1A", "txt": "#FF6B6B"},
            "BLOQUEAR_CLIENTE": {"bg": "#3A1714", "border": "#5C201A", "txt": "#E74C3C"}
        }

        for log in self.logs_cargados:
            accion_txt = log["accion"]
            th = badges_temas.get(accion_txt, {"bg": "#1F1D1A", "border": self.C_BORDER, "txt": self.C_TEXT_MAIN})

            card = ctk.CTkFrame(self.scroll_logs, fg_color=self.C_CARD, corner_radius=8, border_width=1, border_color=self.C_BORDER)
            card.pack(fill="x", pady=2, padx=4)

            # Badge de Acción a la izquierda
            f_tag = ctk.CTkFrame(card, fg_color=th["bg"], corner_radius=6, border_width=1, border_color=th["border"], width=130, height=28)
            f_tag.pack(side="left", padx=10, pady=8)
            f_tag.pack_propagate(False)
            ctk.CTkLabel(f_tag, text=accion_txt, font=("Arial", 8, "bold"), text_color=th["txt"]).place(relx=0.5, rely=0.5, anchor="center")

            # Cuerpo del Evento
            f_info = ctk.CTkFrame(card, fg_color="transparent")
            f_info.pack(side="left", fill="both", expand=True, padx=6, pady=8)

            txt_header = f"{log['fecha']} - Operador: {log['usuario']} ({str(log['rol']).upper()})"
            ctk.CTkLabel(f_info, text=txt_header, font=("Montserrat", 9, "bold"), text_color=self.C_GOLD).pack(anchor="w")

            ctk.CTkLabel(
                f_info, text=log['descripcion'],
                font=("Arial", 10), text_color=self.C_TEXT_MAIN, wraplength=760, justify="left"
            ).pack(anchor="w", pady=(1, 0))

    def exportar_auditoria_pdf(self):
        if not self.logs_cargados:
            messagebox.showwarning("Atención", "No hay eventos para exportar.")
            return

        pdf = PDFReporteAuditoria()
        pdf.add_page()
        pdf.set_font("Helvetica", "", 7.5)

        for l in self.logs_cargados:
            fecha_txt = _sanitizar_fpdf(str(l["fecha"])[:16])
            user_txt = _sanitizar_fpdf(str(l["usuario"])[:14])
            rol_txt = _sanitizar_fpdf(str(l["rol"]).upper()[:10])
            acc_txt = _sanitizar_fpdf(str(l["accion"])[:18])
            desc_txt = _sanitizar_fpdf(str(l["descripcion"])[:105])

            pdf.cell(32, 6, fecha_txt, 1, 0, "C")
            pdf.cell(26, 6, user_txt, 1, 0, "C")
            pdf.cell(22, 6, rol_txt, 1, 0, "C")
            pdf.cell(34, 6, acc_txt, 1, 0, "C")
            pdf.cell(163, 6, desc_txt, 1, 0, "L")
            pdf.ln()

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        export_dir = os.path.join(base_dir, "reportes_exportados")
        os.makedirs(export_dir, exist_ok=True)

        ruta = os.path.join(export_dir, f"auditoria_personal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        pdf.output(ruta)
        os.system(f'start "" "{ruta}"' if os.name == 'nt' else f'open "{ruta}"')