"""
===============================================================================
SISTEMA DE GESTIÓN DE MOTELES - MOTEL PRO v2.0
Módulo: modules/morosos.py (LISTA NEGRA, DESBLOQUEOS Y AUDITORÍA DE SEGURIDAD)
===============================================================================
"""

import customtkinter as ctk
from tkinter import messagebox

# Importaciones desde la Capa de Datos (Incluyendo motor de auditoría)
from database.db_manager import (
    agregar_moroso, obtener_todos_morosos, eliminar_moroso,
    registrar_auditoria
)


class FrameMorosos(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#191715")
        self.controller = controller
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # =====================================================================
        # PANEL IZQUIERDO: FORMULARIO DE INHABILITACIÓN / BLOQUEO
        # =====================================================================
        self.frame_add = ctk.CTkFrame(self, fg_color="#23201C", corner_radius=12, border_width=1, border_color="#36322C")
        self.frame_add.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")

        ctk.CTkLabel(self.frame_add, text="Registro en Lista Negra", font=("Georgia", 16, "bold"), text_color="#D4A343").pack(pady=10)

        self.e_ced = ctk.CTkEntry(self.frame_add, placeholder_text="Cédula (Sólo dígitos)", fg_color="#2D2924")
        self.e_ced.pack(pady=5, fill="x", padx=12)

        self.e_nom = ctk.CTkEntry(self.frame_add, placeholder_text="Nombre y Apellido Completo", fg_color="#2D2924")
        self.e_nom.pack(pady=5, fill="x", padx=12)

        ctk.CTkLabel(self.frame_add, text="Motivo del Bloqueo / Inhabilitación:", font=("Arial", 11, "bold"), text_color="#A89F91").pack(anchor="w", padx=12, pady=(6, 2))
        self.e_motivo = ctk.CTkTextbox(self.frame_add, height=120, fg_color="#2D2924", text_color="#F4EFE6")
        self.e_motivo.pack(pady=5, fill="x", padx=12)

        ctk.CTkButton(
            self.frame_add, text="🚫 Bloquear e Inhabilitar", fg_color="#78281F", hover_color="#943126",
            text_color="#F4EFE6", font=("Arial", 12, "bold"), command=self.guardar
        ).pack(pady=15, fill="x", padx=12)

        # =====================================================================
        # PANEL DERECHO: VISOR DE CIUDADANOS INHABILITADOS
        # =====================================================================
        self.frame_list = ctk.CTkScrollableFrame(self, fg_color="#23201C", label_text="Ciudadanos Inhabilitados / Morosos")
        self.frame_list.grid(row=0, column=1, padx=12, pady=12, sticky="nsew")

        self.cargar_tabla()

    # =========================================================================
    # GUARDAR EN LISTA NEGRA CON AUDITORÍA
    # =========================================================================
    def guardar(self):
        ced = self.e_ced.get().strip()
        nom = self.e_nom.get().strip()
        mot = self.e_motivo.get("1.0", "end-1c").strip()
        usr_act = self.controller.usuario_actual["usuario"]
        rol_act = self.controller.usuario_actual["rol"]

        if not all([ced, nom, mot]):
            messagebox.showwarning("Atención", "Todos los campos son obligatorios.")
            return

        if not ced.isdigit():
            messagebox.showwarning("Atención", "La cédula debe contener únicamente números.")
            return

        if agregar_moroso(ced, nom, mot):
            # AUDITORÍA AUTOMÁTICA DE BLOQUEO
            registrar_auditoria(
                usr_act, rol_act, "BLOQUEAR_CLIENTE",
                f"Se ingresó a Lista Negra a '{nom}' (C.I: {ced}). Motivo: {mot}."
            )
            messagebox.showinfo("Éxito", f"Ciudadano '{nom}' inhabilitado correctamente.")
            self.e_ced.delete(0, 'end')
            self.e_nom.delete(0, 'end')
            self.e_motivo.delete("1.0", "end")
            self.cargar_tabla()
        else:
            messagebox.showerror("Error", "La cédula ya se encuentra registrada en la Lista Negra.")

    # =========================================================================
    # RENDERIZADO Y DESBLOQUEO CON AUDITORÍA
    # =========================================================================
    def cargar_tabla(self):
        for widget in self.frame_list.winfo_children():
            widget.destroy()

        morosos = obtener_todos_morosos()
        if not morosos:
            ctk.CTkLabel(
                self.frame_list, text="No hay ciudadanos en la lista negra.",
                font=("Arial", 12, "italic"), text_color="#A89F91"
            ).pack(pady=30)
            return

        for m in morosos:
            card = ctk.CTkFrame(self.frame_list, fg_color="#2D2924")
            card.pack(fill="x", pady=4, padx=5)

            info = f"C.I: {m['cedula']} | {m['nombre']}\nMotivo: {m['motivo']}\nFecha de Registro: {m['fecha']}"
            ctk.CTkLabel(card, text=info, font=("Arial", 11), text_color="#F4EFE6", justify="left").pack(side="left", padx=12, pady=8)

            # Botón Desbloquear
            btn_desbloquear = ctk.CTkButton(
                card, text="🔓 Desbloquear", fg_color="#1E5F38", hover_color="#2E7D32", width=110,
                text_color="#F4EFE6", font=("Arial", 11, "bold"),
                command=lambda c=m['cedula'], n=m['nombre']: self.desbloquear_ciudadano(c, n)
            )
            btn_desbloquear.pack(side="right", padx=10, pady=8)

    def desbloquear_ciudadano(self, cedula: str, nombre: str):
        usr_act = self.controller.usuario_actual["usuario"]
        rol_act = self.controller.usuario_actual["rol"]

        if messagebox.askyesno("Confirmar Desbloqueo", f"¿Desea retirar a '{nombre}' (C.I. {cedula}) de la lista negra?"):
            if eliminar_moroso(cedula):
                # AUDITORÍA AUTOMÁTICA DE DESBLOQUEO
                registrar_auditoria(
                    usr_act, rol_act, "DESBLOQUEAR_CLIENTE",
                    f"Se retiró de Lista Negra a '{nombre}' (C.I: {cedula}). Acceso habilitado nuevamente."
                )
                messagebox.showinfo("Éxito", f"Ciudadano '{nombre}' habilitado con éxito.")
                self.cargar_tabla()
            else:
                messagebox.showerror("Error", "No se pudo eliminar el registro de la lista negra.")