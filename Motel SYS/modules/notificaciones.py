"""
===============================================================================
SISTEMA DE GESTIÓN DE MOTELES
Módulo: modules/notificaciones.py (MOTOR MULTICANAL: WHATSAPP, TELEGRAM Y EMAIL)
===============================================================================
"""

import threading
import urllib.request
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import customtkinter as ctk
from tkinter import messagebox

from database.db_manager import (
    obtener_config_notificaciones, guardar_config_notificaciones,
    registrar_auditoria
)


# =============================================================================
# ENVIADORES ASÍNCRONOS (NO CONGELAN LA PANTALLA)
# =============================================================================

def _enviar_telegram(token: str, chat_id: str, mensaje: str):
    """Envía un mensaje formateado al bot de Telegram."""
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": mensaje, "parse_mode": "HTML"}).encode("utf-8")
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[ERROR NOTIFICACIÓN TELEGRAM]: {e}")


# =============================================================================
# ENVIADOR WHATSAPP CORREGIDO (CONVIERTE HTML A FORMATO WHATSAPP)
# =============================================================================
import re

def _enviar_whatsapp(phone: str, apikey: str, mensaje: str):
    """Convierte el formato HTML a formato nativo de WhatsApp (*negrita*) y envía el mensaje."""
    try:
        # 1. Convertir negritas y cursivas HTML al formato de WhatsApp
        msg_wa = mensaje.replace("<b>", "*").replace("</b>", "*")
        msg_wa = msg_wa.replace("<i>", "_").replace("</i>", "_")
        
        # 2. Remover cualquier otra etiqueta HTML residual
        msg_wa = re.sub(r'<[^>]+>', '', msg_wa)
        
        # 3. Limpiar número telefónico (quitar espacios o guiones)
        phone_limpio = phone.replace(" ", "").replace("-", "").replace("+", "")

        # 4. Codificar texto para URL de forma segura
        msg_codificado = urllib.parse.quote_plus(msg_wa)
        
        url = f"https://api.callmebot.com/whatsapp.php?phone={phone_limpio}&text={msg_codificado}&apikey={apikey}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        print(f"[ERROR NOTIFICACIÓN WHATSAPP]: {e}")


def _enviar_email(host: str, port: int, user: str, password: str, destino: str, asunto: str, cuerpo_html: str):
    """Envía un correo electrónico con formato HTML profesional vía SMTP."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = asunto
        msg["From"] = f"Motel El Edén <{user}>"
        msg["To"] = destino

        msg.attach(MIMEText(cuerpo_html, "html"))

        server = smtplib.SMTP(host, int(port), timeout=12)
        server.starttls()
        server.login(user, password)
        server.sendmail(user, destino, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"[ERROR NOTIFICACIÓN EMAIL]: {e}")


def disparar_notificacion_multicanal(asunto: str, mensaje_texto: str, mensaje_html: str = None):
    """Dispara el envío a todos los canales activos en un hilo en segundo plano."""
    def _tarea_hilo():
        cfg = obtener_config_notificaciones()

        # 1. Telegram
        if cfg["telegram_activo"] == "1" and cfg["telegram_token"] and cfg["telegram_chat_id"]:
            _enviar_telegram(cfg["telegram_token"], cfg["telegram_chat_id"], mensaje_texto)

        # 2. WhatsApp
        if cfg["whatsapp_activo"] == "1" and cfg["whatsapp_phone"] and cfg["whatsapp_apikey"]:
            _enviar_whatsapp(cfg["whatsapp_phone"], cfg["whatsapp_apikey"], mensaje_texto)

        # 3. Email
        if cfg["email_activo"] == "1" and cfg["email_user"] and cfg["email_pass"] and cfg["email_destino"]:
            html_final = mensaje_html if mensaje_html else f"<pre>{mensaje_texto}</pre>"
            _enviar_email(
                cfg["email_host"], int(cfg["email_port"] or 587),
                cfg["email_user"], cfg["email_pass"], cfg["email_destino"],
                asunto, html_final
            )

    threading.Thread(target=_tarea_hilo, daemon=True).start()


# =============================================================================
# PANEL DE CONFIGURACIÓN VISUAL
# =============================================================================

class FrameNotificaciones(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#191715")
        self.controller = controller

        # Encabezado Superior
        self.frame_top = ctk.CTkFrame(self, fg_color="#23201C", corner_radius=12, border_width=1, border_color="#36322C")
        self.frame_top.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(self.frame_top, text="📲 Alertas al Teléfono del Dueño (WhatsApp, Telegram y Email)", font=("Georgia", 16, "bold"), text_color="#D4A343").pack(side="left", padx=15, pady=10)

        ctk.CTkButton(
            self.frame_top, text="💾 Guardar Parámetros", fg_color="#D4A343", hover_color="#B8892E",
            text_color="#191715", font=("Arial", 11, "bold"), command=self.guardar_datos
        ).pack(side="right", padx=15)

        # Pestañas de Canales
        self.tabs = ctk.CTkTabview(self, fg_color="#23201C", segmented_button_selected_color="#D4A343", segmented_button_selected_hover_color="#B8892E")
        self.tabs.pack(fill="both", expand=True, padx=15, pady=5)

        self.tab_tg = self.tabs.add("📱 Telegram Bot")
        self.tab_wa = self.tabs.add("💬 WhatsApp")
        self.tab_em = self.tabs.add("📧 Correo Electrónico (SMTP)")

        self.construir_tab_telegram()
        self.construir_tab_whatsapp()
        self.construir_tab_email()

        self.cargar_datos_guardados()

    # --- PESTAÑA TELEGRAM ---
    def construir_tab_telegram(self):
        f = self.tab_tg
        self.sw_tg = ctk.CTkSwitch(f, text="Activar Notificaciones por Telegram", font=("Arial", 12, "bold"), progress_color="#D4A343")
        self.sw_tg.pack(anchor="w", padx=20, pady=(15, 10))

        ctk.CTkLabel(f, text="Bot Token (Obtenido con @BotFather en Telegram):", font=("Arial", 11, "bold"), text_color="#A89F91").pack(anchor="w", padx=20)
        self.e_tg_token = ctk.CTkEntry(f, placeholder_text="Ej: 123456789:ABCdefGhIJKlmNoPQRstUVwxyZ", fg_color="#2D2924")
        self.e_tg_token.pack(fill="x", padx=20, pady=4)

        ctk.CTkLabel(f, text="Tu Chat ID (Obtenido con @userinfobot en Telegram):", font=("Arial", 11, "bold"), text_color="#A89F91").pack(anchor="w", padx=20, pady=(8, 0))
        self.e_tg_chat = ctk.CTkEntry(f, placeholder_text="Ej: 987654321", fg_color="#2D2924")
        self.e_tg_chat.pack(fill="x", padx=20, pady=4)

        ctk.CTkButton(f, text="🔔 Probar Notificación Telegram", fg_color="#3E342B", hover_color="#524539", command=self.probar_telegram).pack(anchor="w", padx=20, pady=15)

    # --- PESTAÑA WHATSAPP ---
    def construir_tab_whatsapp(self):
        f = self.tab_wa
        self.sw_wa = ctk.CTkSwitch(f, text="Activar Notificaciones por WhatsApp", font=("Arial", 12, "bold"), progress_color="#D4A343")
        self.sw_wa.pack(anchor="w", padx=20, pady=(15, 10))

        ctk.CTkLabel(f, text="Número Telefónico del Dueño con Código de País (Ej: +584120000000):", font=("Arial", 11, "bold"), text_color="#A89F91").pack(anchor="w", padx=20)
        self.e_wa_phone = ctk.CTkEntry(f, placeholder_text="+584121234567", fg_color="#2D2924")
        self.e_wa_phone.pack(fill="x", padx=20, pady=4)

        ctk.CTkLabel(f, text="API Key de CallMeBot (Gratuito vía WhatsApp):", font=("Arial", 11, "bold"), text_color="#A89F91").pack(anchor="w", padx=20, pady=(8, 0))
        self.e_wa_key = ctk.CTkEntry(f, placeholder_text="Ej: 123456", fg_color="#2D2924")
        self.e_wa_key.pack(fill="x", padx=20, pady=4)

        ctk.CTkButton(f, text="🔔 Probar Notificación WhatsApp", fg_color="#3E342B", hover_color="#524539", command=self.probar_whatsapp).pack(anchor="w", padx=20, pady=15)

    # --- PESTAÑA EMAIL ---
    def construir_tab_email(self):
        f = self.tab_em
        self.sw_em = ctk.CTkSwitch(f, text="Activar Notificaciones por Correo Electrónico", font=("Arial", 12, "bold"), progress_color="#D4A343")
        self.sw_em.pack(anchor="w", padx=20, pady=(15, 10))

        f_srv = ctk.CTkFrame(f, fg_color="transparent")
        f_srv.pack(fill="x", padx=20, pady=4)
        
        self.e_em_host = ctk.CTkEntry(f_srv, placeholder_text="Servidor SMTP (smtp.gmail.com)", fg_color="#2D2924")
        self.e_em_host.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.e_em_port = ctk.CTkEntry(f_srv, placeholder_text="Puerto (587)", width=90, fg_color="#2D2924")
        self.e_em_port.pack(side="left")

        ctk.CTkLabel(f, text="Correo Remitente del Motel:", font=("Arial", 11, "bold"), text_color="#A89F91").pack(anchor="w", padx=20, pady=(6, 0))
        self.e_em_user = ctk.CTkEntry(f, placeholder_text="motel.eden.alertas@gmail.com", fg_color="#2D2924")
        self.e_em_user.pack(fill="x", padx=20, pady=2)

        ctk.CTkLabel(f, text="Contraseña de Aplicación (App Password):", font=("Arial", 11, "bold"), text_color="#A89F91").pack(anchor="w", padx=20, pady=(6, 0))
        self.e_em_pass = ctk.CTkEntry(f, placeholder_text="Clave de 16 letras generada en Google", show="*", fg_color="#2D2924")
        self.e_em_pass.pack(fill="x", padx=20, pady=2)

        ctk.CTkLabel(f, text="Correo Destinatario del Dueño / Gerente:", font=("Arial", 11, "bold"), text_color="#A89F91").pack(anchor="w", padx=20, pady=(6, 0))
        self.e_em_dest = ctk.CTkEntry(f, placeholder_text="dueno.motel@gmail.com", fg_color="#2D2924")
        self.e_em_dest.pack(fill="x", padx=20, pady=2)

        ctk.CTkButton(f, text="🔔 Probar Envío de Correo", fg_color="#3E342B", hover_color="#524539", command=self.probar_email).pack(anchor="w", padx=20, pady=12)

    def cargar_datos_guardados(self):
        c = obtener_config_notificaciones()
        if c["telegram_activo"] == "1": self.sw_tg.select()
        else: self.sw_tg.deselect()
        self.e_tg_token.insert(0, c["telegram_token"])
        self.e_tg_chat.insert(0, c["telegram_chat_id"])

        if c["whatsapp_activo"] == "1": self.sw_wa.select()
        else: self.sw_wa.deselect()
        self.e_wa_phone.insert(0, c["whatsapp_phone"])
        self.e_wa_key.insert(0, c["whatsapp_apikey"])

        if c["email_activo"] == "1": self.sw_em.select()
        else: self.sw_em.deselect()
        self.e_em_host.insert(0, c["email_host"])
        self.e_em_port.insert(0, c["email_port"])
        self.e_em_user.insert(0, c["email_user"])
        self.e_em_pass.insert(0, c["email_pass"])
        self.e_em_dest.insert(0, c["email_destino"])

    def guardar_datos(self):
        datos = {
            "telegram_token": self.e_tg_token.get().strip(),
            "telegram_chat_id": self.e_tg_chat.get().strip(),
            "telegram_activo": "1" if self.sw_tg.get() else "0",
            "whatsapp_phone": self.e_wa_phone.get().strip(),
            "whatsapp_apikey": self.e_wa_key.get().strip(),
            "whatsapp_activo": "1" if self.sw_wa.get() else "0",
            "email_host": self.e_em_host.get().strip() or "smtp.gmail.com",
            "email_port": self.e_em_port.get().strip() or "587",
            "email_user": self.e_em_user.get().strip(),
            "email_pass": self.e_em_pass.get().strip(),
            "email_destino": self.e_em_dest.get().strip(),
            "email_activo": "1" if self.sw_em.get() else "0"
        }
        if guardar_config_notificaciones(datos):
            registrar_auditoria(self.controller.usuario_actual["usuario"], self.controller.usuario_actual["rol"], "CONFIG_NOTIF", "Se actualizaron las credenciales de alertas (TG, WA, Email).")
            messagebox.showinfo("Éxito", "Parámetros de notificación guardados correctamente.")

    def probar_telegram(self):
        tok, chat = self.e_tg_token.get().strip(), self.e_tg_chat.get().strip()
        if not tok or not chat:
            messagebox.showwarning("Atención", "Ingrese Token y Chat ID.")
            return
        msg = "🏨 <b>MOTEL EL EDEN</b>\nPrueba de notificación exitosa vía Telegram Bot."
        threading.Thread(target=lambda: _enviar_telegram(tok, chat, msg), daemon=True).start()
        messagebox.showinfo("Prueba Enviada", "Mensaje enviado a Telegram. Verifique su aplicación.")

    def probar_whatsapp(self):
        ph, key = self.e_wa_phone.get().strip(), self.e_wa_key.get().strip()
        if not ph or not key:
            messagebox.showwarning("Atención", "Ingrese Número y API Key.")
            return
        msg = "🏨 MOTEL EL EDEN: Prueba de alerta exitosa vía WhatsApp."
        threading.Thread(target=lambda: _enviar_whatsapp(ph, key, msg), daemon=True).start()
        messagebox.showinfo("Prueba Enviada", "Mensaje enviado a WhatsApp. Verifique su teléfono.")

    def probar_email(self):
        h, p, u, pwd, d = self.e_em_host.get().strip(), self.e_em_port.get().strip(), self.e_em_user.get().strip(), self.e_em_pass.get().strip(), self.e_em_dest.get().strip()
        if not all([u, pwd, d]):
            messagebox.showwarning("Atención", "Complete los campos de correo remitente, clave y destino.")
            return
        asunto = "Prueba de Alerta - Motel El Edén"
        html = "<h3>MOTEL EL EDEN</h3><p>Este es un correo de prueba del sistema de notificaciones automáticas.</p>"
        threading.Thread(target=lambda: _enviar_email(h, int(p or 587), u, pwd, d, asunto, html), daemon=True).start()
        messagebox.showinfo("Prueba Enviada", f"Correo de prueba enviado a {d}.")