"""
===============================================================================
SISTEMA DE GESTIÓN DE MOTELES - MOTEL PRO v2.0
Módulo: modules/morosos.py (LISTA NEGRA, SEGURIDAD Y CONTROL DE INCIDENCIAS)
Diseño: Dark Luxury & Enterprise Security Hub
===============================================================================
"""

import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime

# Importaciones desde la Capa de Datos (database/db_manager.py)
from database.db_manager import (
    agregar_moroso, obtener_todos_morosos, eliminar_moroso,
    registrar_auditoria
)


class FrameMorosos(ctk.CTkFrame):
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
        self.C_RED_BG = "#3A1714"
        self.C_TEXT_MAIN = "#F5EFEB"
        self.C_TEXT_MUTED = "#8E8880"

        # Configuración de Grid Principal (32% Izquierda - 68% Derecha)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=7)
        self.grid_rowconfigure(0, weight=1)

        self.morosos_cache = []

        # =====================================================================
        # PANEL IZQUIERDO: FORMULARIO DE INHABILITACIÓN / LISTA NEGRA
        # =====================================================================
        self.frame_add = ctk.CTkFrame(
            self, fg_color=self.C_PANEL, corner_radius=14,
            border_width=1, border_color=self.C_BORDER
        )
        self.frame_add.grid(row=0, column=0, padx=(16, 8), pady=16, sticky="nsew")

        # Header del Formulario
        f_top_add = ctk.CTkFrame(self.frame_add, fg_color="transparent")
        f_top_add.pack(fill="x", padx=18, pady=(18, 10))

        ctk.CTkLabel(
            f_top_add, text="REGISTRO DE INHABILITACIÓN",
            font=("Montserrat", 13, "bold"), text_color=self.C_GOLD
        ).pack(anchor="w")

        ctk.CTkLabel(
            f_top_add, text="Restricción de acceso y control de clientes no deseados",
            font=("Arial", 9), text_color=self.C_TEXT_MUTED
        ).pack(anchor="w")

        # Tarjeta de Advertencia
        card_aviso = ctk.CTkFrame(
            self.frame_add, fg_color="#241412", corner_radius=8,
            border_width=1, border_color="#5C201A"
        )
        card_aviso.pack(fill="x", padx=18, pady=(0, 14))

        ctk.CTkLabel(
            card_aviso,
            text="⚠️ Al inhabilitar a un huésped, el sistema bloqueará automáticamente cualquier intento de Check-In futuro.",
            font=("Arial", 9, "italic"), text_color="#FADBD8", wraplength=260, justify="left"
        ).pack(padx=12, pady=8)

        # Campos de Entrada
        f_fields = ctk.CTkFrame(self.frame_add, fg_color="transparent")
        f_fields.pack(fill="both", expand=True, padx=18)

        ctk.CTkLabel(f_fields, text="CÉDULA DE IDENTIDAD", font=("Montserrat", 9, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", pady=(2, 2))
        self.e_ced = ctk.CTkEntry(
            f_fields, placeholder_text="Sólo números (ej: 18450123)", height=34,
            fg_color=self.C_INPUT, border_color=self.C_BORDER, text_color=self.C_TEXT_MAIN,
            font=("Arial", 11)
        )
        self.e_ced.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(f_fields, text="NOMBRE Y APELLIDO", font=("Montserrat", 9, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", pady=(2, 2))
        self.e_nom = ctk.CTkEntry(
            f_fields, placeholder_text="Nombre completo del ciudadano", height=34,
            fg_color=self.C_INPUT, border_color=self.C_BORDER, text_color=self.C_TEXT_MAIN,
            font=("Arial", 11)
        )
        self.e_nom.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(f_fields, text="MOTIVO DEL BLOQUEO / ANTECEDENTE", font=("Montserrat", 9, "bold"), text_color=self.C_TEXT_MUTED).pack(anchor="w", pady=(2, 2))
        self.e_motivo = ctk.CTkTextbox(
            f_fields, height=130, fg_color=self.C_INPUT,
            border_width=1, border_color=self.C_BORDER, text_color=self.C_TEXT_MAIN,
            font=("Arial", 11)
        )
        self.e_motivo.pack(fill="x", pady=(0, 14))

        # Botón Acción de Bloqueo
        self.btn_bloquear = ctk.CTkButton(
            self.frame_add, text="🚫 Bloquear e Ingresar a Lista Negra",
            fg_color=self.C_RED_BG, hover_color=self.C_RED, text_color="#FADBD8",
            font=("Montserrat", 11, "bold"), height=42, corner_radius=8,
            border_width=1, border_color="#5C201A", command=self.guardar
        )
        self.btn_bloquear.pack(fill="x", padx=18, pady=(0, 18))

        # =====================================================================
        # PANEL DERECHO: VISOR AUDITABLE Y BUSCADOR EN TIEMPO REAL
        # =====================================================================
        self.frame_right = ctk.CTkFrame(
            self, fg_color=self.C_PANEL, corner_radius=14,
            border_width=1, border_color=self.C_BORDER
        )
        self.frame_right.grid(row=0, column=1, padx=(8, 16), pady=16, sticky="nsew")

        # Header del Visor
        f_top_der = ctk.CTkFrame(self.frame_right, fg_color="transparent")
        f_top_der.pack(fill="x", padx=18, pady=(16, 8))

        ctk.CTkLabel(
            f_top_der, text="LISTA NEGRA & CIUDADANOS INHABILITADOS",
            font=("Montserrat", 14, "bold"), text_color=self.C_GOLD
        ).pack(side="left")

        self.lbl_contador = ctk.CTkLabel(
            f_top_der, text="0 Inhabilitados", font=("Arial", 10, "bold"),
            text_color=self.C_RED
        )
        self.lbl_contador.pack(side="right")

        # Barra de Herramientas con Buscador Rápido
        f_tools = ctk.CTkFrame(self.frame_right, fg_color="transparent")
        f_tools.pack(fill="x", padx=18, pady=(4, 8))

        self.e_buscar = ctk.CTkEntry(
            f_tools, placeholder_text="🔍 Buscar por cédula, nombre o motivo...",
            height=34, fg_color=self.C_CARD, border_color=self.C_BORDER,
            text_color=self.C_TEXT_MAIN, font=("Arial", 11)
        )
        self.e_buscar.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.e_buscar.bind("<KeyRelease>", lambda e: self.renderizar_tabla())

        ctk.CTkButton(
            f_tools, text="🔄 Refrescar", width=95, height=34, corner_radius=8,
            fg_color=self.C_CARD, hover_color="#2A2621", text_color=self.C_TEXT_MAIN,
            font=("Arial", 11, "bold"), border_width=1, border_color=self.C_BORDER,
            command=self.cargar_tabla
        ).pack(side="right")

        # Contenedor Scrollable de Tarjetas
        self.scroll_list = ctk.CTkScrollableFrame(self.frame_right, fg_color=self.C_BG)
        self.scroll_list.pack(fill="both", expand=True, padx=18, pady=(0, 16))

        self.cargar_tabla()

    # =========================================================================
    # LÓGICA DE REGISTRO CON AUDITORÍA
    # =========================================================================
    def guardar(self):
        ced = self.e_ced.get().strip()
        nom = self.e_nom.get().strip()
        mot = self.e_motivo.get("1.0", "end-1c").strip()
        usr_act = self.controller.usuario_actual["usuario"]
        rol_act = self.controller.usuario_actual["rol"]

        if not all([ced, nom, mot]):
            messagebox.showwarning("Atención", "Todos los campos son obligatorios para asentar el bloqueo.")
            return

        if not ced.isdigit():
            messagebox.showwarning("Atención", "La cédula debe contener únicamente números sin puntos ni letras.")
            return

        if messagebox.askyesno(
            "Confirmación de Bloqueo",
            f"¿Confirma ingresar a la Lista Negra a:\n\n{nom.upper()} (C.I: {ced})?\n\nMotivo: '{mot}'"
        ):
            if agregar_moroso(ced, nom, mot):
                registrar_auditoria(
                    usr_act, rol_act, "BLOQUEAR_CLIENTE",
                    f"Se ingresó a Lista Negra a '{nom}' (C.I: {ced}). Motivo: {mot}."
                )
                messagebox.showinfo("Registro Exitoso", f"El ciudadano '{nom}' ha sido inhabilitado.")
                self.e_ced.delete(0, 'end')
                self.e_nom.delete(0, 'end')
                self.e_motivo.delete("1.0", "end")
                self.cargar_tabla()
            else:
                messagebox.showerror("Error", "La cédula ya se encuentra registrada en la Lista Negra.")

    # =========================================================================
    # RENDERIZADO Y DESBLOQUEO SEGURO
    # =========================================================================
    def cargar_tabla(self):
        self.morosos_cache = obtener_todos_morosos()
        self.lbl_contador.configure(text=f"🚫 {len(self.morosos_cache)} Inhabilitado(s)")
        self.renderizar_tabla()

    def renderizar_tabla(self):
        for widget in self.scroll_list.winfo_children():
            widget.destroy()

        filtro = self.e_buscar.get().strip().upper()
        filtrados = []

        for m in self.morosos_cache:
            ced = str(m.get("cedula", "")).upper()
            nom = str(m.get("nombre", "")).upper()
            mot = str(m.get("motivo", "")).upper()

            if filtro and not any(filtro in campo for campo in [ced, nom, mot]):
                continue
            filtrados.append(m)

        if not filtrados:
            f_empty = ctk.CTkFrame(
                self.scroll_list, fg_color=self.C_PANEL, corner_radius=12,
                border_width=1, border_color=self.C_BORDER
            )
            f_empty.pack(fill="x", pady=30, padx=10)

            msg_title = "✨ Lista Negra Limpia" if not self.morosos_cache else "🔍 Sin coincidencias"
            msg_sub = "No hay ciudadanos inhabilitados registrados en el sistema." if not self.morosos_cache else "Ningún registro coincide con el criterio de búsqueda ingresado."

            ctk.CTkLabel(f_empty, text=msg_title, font=("Montserrat", 13, "bold"), text_color=self.C_GOLD).pack(pady=(20, 2))
            ctk.CTkLabel(f_empty, text=msg_sub, font=("Arial", 10), text_color=self.C_TEXT_MUTED).pack(pady=(0, 20))
            return

        for m in filtrados:
            card = ctk.CTkFrame(
                self.scroll_list, fg_color=self.C_CARD, corner_radius=10,
                border_width=1, border_color=self.C_BORDER
            )
            card.pack(fill="x", pady=3, padx=2)

            # Contenedor Izquierdo: Datos y Antecedente
            f_izq = ctk.CTkFrame(card, fg_color="transparent")
            f_izq.pack(side="left", fill="both", expand=True, padx=14, pady=10)

            # Cabecera de la Tarjeta (Nombre + Badge)
            f_row_head = ctk.CTkFrame(f_izq, fg_color="transparent")
            f_row_head.pack(fill="x")

            ctk.CTkLabel(
                f_row_head, text=f"{m['nombre']}  •  C.I: {m['cedula']}",
                font=("Montserrat", 12, "bold"), text_color=self.C_TEXT_MAIN
            ).pack(side="left")

            badge_inhab = ctk.CTkFrame(f_row_head, fg_color=self.C_RED_BG, corner_radius=5, border_width=1, border_color="#5C201A")
            badge_inhab.pack(side="left", padx=10)
            ctk.CTkLabel(badge_inhab, text="🚫 INHABILITADO", font=("Arial", 8, "bold"), text_color="#FADBD8").pack(padx=6, pady=1)

            # Antecedente / Causa
            ctk.CTkLabel(
                f_izq, text=f'"{m["motivo"]}"',
                font=("Arial", 10, "italic"), text_color="#F5B7B1", wraplength=480, justify="left"
            ).pack(anchor="w", pady=(4, 2))

            # Fecha de Registro
            fecha_str = str(m.get("fecha", ""))[:16]
            ctk.CTkLabel(
                f_izq, text=f"📅 Fecha de Registro: {fecha_str}",
                font=("Arial", 9), text_color=self.C_TEXT_MUTED
            ).pack(anchor="w")

            # Botón Desbloquear / Rehabilitar
            btn_desbloquear = ctk.CTkButton(
                card, text="🔓 Rehabilitar", fg_color="#1E5F38", hover_color="#2E7D32",
                width=115, height=32, corner_radius=6, text_color="#F4EFE6",
                font=("Arial", 10, "bold"),
                command=lambda c=m['cedula'], n=m['nombre']: self.desbloquear_ciudadano(c, n)
            )
            btn_desbloquear.pack(side="right", padx=14, pady=10)

    def desbloquear_ciudadano(self, cedula: str, nombre: str):
        usr_act = self.controller.usuario_actual["usuario"]
        rol_act = self.controller.usuario_actual["rol"]

        confirmar = messagebox.askyesno(
            "Confirmar Desbloqueo",
            f"¿Desea retirar a:\n\n{nombre} (C.I. {cedula})\n\nde la Lista Negra?\n\nPodrá volver a hospedarse normalmente."
        )

        if confirmar:
            if eliminar_moroso(cedula):
                registrar_auditoria(
                    usr_act, rol_act, "DESBLOQUEAR_CLIENTE",
                    f"Se retiró de Lista Negra a '{nombre}' (C.I: {cedula}). Acceso habilitado nuevamente."
                )
                messagebox.showinfo("Operación Exitosa", f"Ciudadano '{nombre}' habilitado con éxito.")
                self.cargar_tabla()
            else:
                messagebox.showerror("Error", "No se pudo actualizar el registro en la base de datos.")