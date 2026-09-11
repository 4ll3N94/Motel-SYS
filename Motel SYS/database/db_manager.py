"""
===============================================================================
SISTEMA DE GESTIÓN DE MOTELES 
Módulo: database/db_manager.py
Descripción: Manejo centralizado de tablas, consultas parametrizadas,
             soporte para Alarma Violeta, Historial SAIME y Módulo Mercancía.
===============================================================================
"""

import os
import sqlite3
import hashlib
import logging
#mport sys
from datetime import datetime

# Configuración de Logging para auditoría de base de datos
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (DB_MANAGER): %(message)s"
)

# Determinación dinámica de la ruta de la Base de Datos (Portabilidad absoluta)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "motel_profesional.db")


def obtener_conexion():
    """Establece conexión a SQLite con WAL mode activado para concurrencia."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row  # Acceso a columnas por nombre
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn
    except sqlite3.Error as e:
        logging.error(f"Error al conectar con la base de datos: {e}")
        raise e


def hash_clave(clave: str) -> str:
    """Encriptación SHA-256 para contraseñas de usuarios."""
    return hashlib.sha256(clave.encode("utf-8")).hexdigest()



def inicializar_bd():
    """
    Crea y verifica la existencia de todas las tablas del sistema de forma independiente.
    Si una tabla no existe (como cierres_turno), la crea automáticamente.
    """
    conn = obtener_conexion()
    cursor = conn.cursor()

    # Lista de consultas para asegurar que todas las tablas existan
    tablas_sql = [
        # 1. Usuarios
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cedula TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            correo TEXT NOT NULL,
            telefono TEXT NOT NULL,
            usuario TEXT UNIQUE NOT NULL,
            clave TEXT NOT NULL,
            rol TEXT CHECK(rol IN ('admin', 'recepcionista')) NOT NULL
        );
        """,
        # 2. Habitaciones
        """
        CREATE TABLE IF NOT EXISTS habitaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            estado TEXT DEFAULT 'Limpia' CHECK(estado IN ('Limpia', 'Ocupada', 'Sucia', 'Tiempo_Vencido', 'Mantenimiento')),
            precio_4h REAL NOT NULL,
            precio_24h REAL NOT NULL
        );
        """,
        # 3. Morosos
        """
        CREATE TABLE IF NOT EXISTS morosos (
            cedula TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            motivo TEXT NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        # 4. Estancias Activas
        """
        CREATE TABLE IF NOT EXISTS estancias_activas (
            hab_codigo TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            cedula TEXT NOT NULL,
            telefono TEXT NOT NULL,
            edad TEXT NOT NULL,
            estado_civil TEXT NOT NULL,
            nacionalidad TEXT NOT NULL,
            procedencia TEXT NOT NULL,
            destino TEXT NOT NULL,
            ac_nombre TEXT NOT NULL,
            ac_apellido TEXT NOT NULL,
            ac_cedula TEXT NOT NULL,
            ac_edad TEXT NOT NULL,
            ac_estado_civil TEXT NOT NULL,
            ac_nacionalidad TEXT NOT NULL,
            ac_procedencia TEXT NOT NULL,
            ac_destino TEXT NOT NULL,
            tipo_estancia TEXT NOT NULL CHECK(tipo_estancia IN ('4h', '24h')),
            fecha_entrada TIMESTAMP NOT NULL,
            fecha_salida_estimada TIMESTAMP NOT NULL,
            FOREIGN KEY (hab_codigo) REFERENCES habitaciones (codigo) ON DELETE CASCADE
        );
        """,
        # 5. Historial Estancias SAIME
        """
        CREATE TABLE IF NOT EXISTS historial_estancias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hab_codigo TEXT NOT NULL,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            cedula TEXT NOT NULL,
            telefono TEXT NOT NULL,
            edad TEXT NOT NULL,
            estado_civil TEXT NOT NULL,
            nacionalidad TEXT NOT NULL,
            procedencia TEXT NOT NULL,
            destino TEXT NOT NULL,
            ac_nombre TEXT NOT NULL,
            ac_apellido TEXT NOT NULL,
            ac_cedula TEXT NOT NULL,
            ac_edad TEXT NOT NULL,
            ac_estado_civil TEXT NOT NULL,
            ac_nacionalidad TEXT NOT NULL,
            ac_procedencia TEXT NOT NULL,
            ac_destino TEXT NOT NULL,
            tipo_estancia TEXT NOT NULL,
            fecha_entrada TIMESTAMP NOT NULL
        );
        """,
        # 6. Pagos
        """
        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hab_codigo TEXT NOT NULL,
            monto REAL NOT NULL,
            metodo TEXT NOT NULL,
            p2p_referencia TEXT,
            p2p_ci TEXT,
            p2p_telefono TEXT,
            cliente_nombre TEXT NOT NULL,
            cliente_cedula TEXT NOT NULL,
            ac_nombre TEXT,
            ac_cedula TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            turno TEXT NOT NULL CHECK(turno IN ('MAÑANA', 'NOCHE')),
            recepcionista TEXT NOT NULL,
            bebidas_usd REAL DEFAULT 0,
            bebidas_bs REAL DEFAULT 0
        );
        """,
        # 7. Productos Mercancía
        """
        CREATE TABLE IF NOT EXISTS productos_mercancia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            precio_usd REAL NOT NULL
        );
        """,
        # 8. Ventas Mercancía Cabecera
        """
        CREATE TABLE IF NOT EXISTS ventas_mercancia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hab_codigo TEXT NOT NULL,
            total_usd REAL NOT NULL,
            total_bs REAL NOT NULL,
            metodo TEXT NOT NULL,
            p2p_referencia TEXT,
            p2p_ci TEXT,
            p2p_telefono TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            turno TEXT NOT NULL CHECK(turno IN ('MAÑANA', 'NOCHE')),
            recepcionista TEXT NOT NULL
        );
        """,
        # 9. Ventas Mercancía Detalle
        """
        CREATE TABLE IF NOT EXISTS ventas_mercancia_detalle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id INTEGER NOT NULL,
            producto TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            precio_unit_usd REAL NOT NULL,
            subtotal_usd REAL NOT NULL,
            subtotal_bs REAL NOT NULL,
            FOREIGN KEY (venta_id) REFERENCES ventas_mercancia (id) ON DELETE CASCADE
        );
        """,
        # 10. Cierres de Turno
        """
        CREATE TABLE IF NOT EXISTS cierres_turno (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            turno TEXT NOT NULL CHECK(turno IN ('MAÑANA', 'NOCHE')),
            total_bs REAL NOT NULL,
            total_usd REAL NOT NULL,
            total_p2p REAL NOT NULL,
            total_punto REAL NOT NULL,
            recepcionista TEXT NOT NULL,
            UNIQUE(fecha, turno)
        );
        """,
        # 11. Configuración
        """
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        );
        """
        # 12. TABLA: auditoria_logs (TRAZABILIDAD DE ACCIONES DE USUARIOS)
        """
        CREATE TABLE IF NOT EXISTS auditoria_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            rol TEXT NOT NULL,
            accion TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    ]

    try:
        # Ejecutar cada tabla de forma independiente para garantizar que existan
        for query in tablas_sql:
            cursor.execute(query)
        
        conn.commit()

        # Insertar Usuario Admin por defecto si no existe
        cursor.execute("SELECT COUNT(*) FROM usuarios;")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO usuarios (cedula, nombre, apellido, correo, telefono, usuario, clave, rol)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ("V-00000000", "Administrador", "Principal", "admin@motel.com", "04120000000", "admin", hash_clave("admin123"), "admin"))
            conn.commit()

        # Insertar Tasa BCV por defecto si no existe
        cursor.execute("SELECT valor FROM configuracion WHERE clave = 'tasa_bcv';")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO configuracion (clave, valor) VALUES (?, ?);", ("tasa_bcv", "36.50"))
            conn.commit()

    except sqlite3.Error as e:
        conn.rollback()
        logging.error(f"Error al verificar e inicializar tablas: {e}")
    finally:
        conn.close()


# =============================================================================
# FUNCIONES DE EDICIÓN DE USUARIOS
# =============================================================================

def obtener_todos_usuarios() -> list:
    """Retorna la lista completa de usuarios registrados en el sistema."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, cedula, nombre, apellido, correo, telefono, usuario, rol FROM usuarios ORDER BY id DESC;")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def actualizar_usuario(user_id: int, cedula: str, nombre: str, apellido: str, correo: str, telefono: str, usuario: str, clave_hash: str | None, rol: str) -> bool:
    """
    Actualiza los datos de un usuario existente en la base de datos.
    Si clave_hash es None, mantiene la contraseña anterior.
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        if clave_hash:
            cursor.execute("""
                UPDATE usuarios 
                SET cedula = ?, nombre = ?, apellido = ?, correo = ?, telefono = ?, usuario = ?, clave = ?, rol = ?
                WHERE id = ?;
            """, (cedula.strip(), nombre.strip(), apellido.strip(), correo.strip(), telefono.strip(), usuario.strip(), clave_hash, rol, user_id))
        else:
            cursor.execute("""
                UPDATE usuarios 
                SET cedula = ?, nombre = ?, apellido = ?, correo = ?, telefono = ?, usuario = ?, rol = ?
                WHERE id = ?;
            """, (cedula.strip(), nombre.strip(), apellido.strip(), correo.strip(), telefono.strip(), usuario.strip(), rol, user_id))
        
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        conn.rollback()
        return False
    except sqlite3.Error as e:
        conn.rollback()
        logging.error(f"Error al actualizar usuario #{user_id}: {e}")
        return False
    finally:
        conn.close()


# =============================================================================
# FUNCIONES: CONFIGURACIÓN Y TASA BCV
# =============================================================================

def obtener_tasa_bcv() -> float:
    """Retorna la tasa BCV activa."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT valor FROM configuracion WHERE clave = 'tasa_bcv';")
        row = cursor.fetchone()
        return float(row["valor"]) if row else 36.50
    finally:
        conn.close()


def actualizar_tasa_bcv(nueva_tasa: float) -> bool:
    """Guarda la nueva Tasa BCV."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO configuracion (clave, valor) VALUES ('tasa_bcv', ?)
            ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor;
        """, (str(nueva_tasa),))
        conn.commit()
        return True
    except sqlite3.Error:
        conn.rollback()
        return False
    finally:
        conn.close()


# =============================================================================
# FUNCIONES: MOROSOS / LISTA NEGRA
# =============================================================================

def consultar_moroso(cedula: str) -> dict | None:
    """Busca un moroso por cédula."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM morosos WHERE cedula = ?;", (cedula.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def agregar_moroso(cedula: str, nombre: str, motivo: str) -> bool:
    """Agrega a la lista negra."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO morosos (cedula, nombre, motivo) VALUES (?, ?, ?);",
                       (cedula.strip(), nombre.strip(), motivo.strip()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def eliminar_moroso(cedula: str) -> bool:
    """Elimina / Desbloquea un ciudadano de la lista negra."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM morosos WHERE cedula = ?;", (cedula.strip(),))
        conn.commit()
        return True
    except sqlite3.Error:
        conn.rollback()
        return False
    finally:
        conn.close()


def obtener_todos_morosos() -> list:
    """Retorna la lista completa de morosos."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT cedula, nombre, motivo, fecha FROM morosos ORDER BY fecha DESC;")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


# =============================================================================
# FUNCIONES: HABITACIONES Y ESTANCIAS ACTIVAS
# =============================================================================

def obtener_habitaciones() -> list:
    """Obtiene todas las habitaciones ordenadas por código."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM habitaciones ORDER BY codigo ASC;")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def actualizar_estado_habitacion(codigo: str, nuevo_estado: str) -> bool:
    """
    Actualiza el estado de la habitación ('Limpia', 'Ocupada', 'Sucia', 'Tiempo_Vencido', 'Mantenimiento').
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE habitaciones SET estado = ? WHERE codigo = ?;", (nuevo_estado, codigo))
        conn.commit()
        return True
    except sqlite3.Error as e:
        conn.rollback()
        logging.error(f"Error al actualizar estado de habitacion {codigo}: {e}")
        return False
    finally:
        conn.close()


def registrar_estancia(datos: dict) -> bool:
    """Registra estancia activa y guarda copia permanente para el SAIME."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        conn.execute("BEGIN TRANSACTION;")

        cursor.execute("""
            INSERT INTO estancias_activas (
                hab_codigo, nombre, apellido, cedula, telefono, edad, estado_civil, nacionalidad, procedencia, destino,
                ac_nombre, ac_apellido, ac_cedula, ac_edad, ac_estado_civil, ac_nacionalidad, ac_procedencia, ac_destino,
                tipo_estancia, fecha_entrada, fecha_salida_estimada
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            datos["hab_codigo"], datos["nombre"], datos["apellido"], datos["cedula"], datos["telefono"],
            datos["edad"], datos["estado_civil"], datos["nacionalidad"], datos["procedencia"], datos["destino"],
            datos["ac_nombre"], datos["ac_apellido"], datos["ac_cedula"], datos["ac_edad"], datos["ac_estado_civil"],
            datos["ac_nacionalidad"], datos["ac_procedencia"], datos["ac_destino"], datos["tipo_estancia"],
            datos["fecha_entrada"], datos["fecha_salida_estimada"]
        ))

        cursor.execute("""
            INSERT INTO historial_estancias (
                hab_codigo, nombre, apellido, cedula, telefono, edad, estado_civil, nacionalidad, procedencia, destino,
                ac_nombre, ac_apellido, ac_cedula, ac_edad, ac_estado_civil, ac_nacionalidad, ac_procedencia, ac_destino,
                tipo_estancia, fecha_entrada
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            datos["hab_codigo"], datos["nombre"], datos["apellido"], datos["cedula"], datos["telefono"],
            datos["edad"], datos["estado_civil"], datos["nacionalidad"], datos["procedencia"], datos["destino"],
            datos["ac_nombre"], datos["ac_apellido"], datos["ac_cedula"], datos["ac_edad"], datos["ac_estado_civil"],
            datos["ac_nacionalidad"], datos["ac_procedencia"], datos["ac_destino"], datos["tipo_estancia"],
            datos["fecha_entrada"]
        ))

        cursor.execute("UPDATE habitaciones SET estado = 'Ocupada' WHERE codigo = ?;", (datos["hab_codigo"],))
        conn.commit()
        return True
    except sqlite3.Error as e:
        conn.rollback()
        logging.error(f"Error al registrar estancia: {e}")
        return False
    finally:
        conn.close()


def obtener_estancias_activas() -> list:
    """Obtiene estancias de las habitaciones actualmente ocupadas."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM estancias_activas;")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def obtener_historial_saime(fecha_inicio: str, fecha_fin: str) -> list:
    """Obtiene el historial para la planilla de extranjería del SAIME."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT * FROM historial_estancias 
            WHERE DATE(fecha_entrada) BETWEEN ? AND ? 
            ORDER BY fecha_entrada ASC;
        """, (fecha_inicio, fecha_fin))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def finalizar_estancia_checkout(hab_codigo: str) -> bool:
    """Procesa el Check-Out liberando la estancia activa a estado 'Sucia'."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn.execute("BEGIN TRANSACTION;")
        cursor.execute("DELETE FROM estancias_activas WHERE hab_codigo = ?;", (hab_codigo,))
        # Guarda fecha_sucia al momento del checkout
        cursor.execute("UPDATE habitaciones SET estado = 'Sucia', fecha_sucia = ? WHERE codigo = ?;", (ahora, hab_codigo))
        conn.commit()
        return True
    except sqlite3.Error:
        conn.rollback()
        return False
    finally:
        conn.close()


# =============================================================================
# FUNCIONES: MERCANCÍA Y MINI-BAR
# =============================================================================

def obtener_productos() -> list:
    """Obtiene el catálogo de productos con niveles de inventario y costo CPP."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        # Migración automática si falta la columna
        cursor.execute("PRAGMA table_info(productos_mercancia);")
        cols = [c["name"] for c in cursor.fetchall()]
        if "costo_unitario_usd" not in cols:
            cursor.execute("ALTER TABLE productos_mercancia ADD COLUMN costo_unitario_usd REAL DEFAULT 0.0;")
            conn.commit()

        # CONSULTA CORREGIDA: INCLUYE costo_unitario_usd
        cursor.execute("""
            SELECT id, nombre, precio_usd, costo_unitario_usd, stock, stock_minimo 
            FROM productos_mercancia 
            ORDER BY nombre ASC;
        """)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def agregar_habitacion(codigo: str, precio_4h: float, precio_24h: float) -> bool:
    """Registra una nueva habitación en el sistema."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO habitaciones (codigo, precio_4h, precio_24h) VALUES (?, ?, ?);",
            (codigo.strip().upper(), precio_4h, precio_24h)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    except sqlite3.Error as e:
        logging.error(f"Error al agregar habitación: {e}")
        return False
    finally:
        conn.close()

def agregar_producto(nombre: str, precio_usd: float, stock: int = 10, stock_min: int = 5, costo_usd: float = 0.0) -> bool:
    """Registra un nuevo producto guardando su precio de venta y su costo de compra (CPP)."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO productos_mercancia (nombre, precio_usd, stock, stock_minimo, costo_unitario_usd)
            VALUES (?, ?, ?, ?, ?);
        """, (nombre.strip(), precio_usd, stock, stock_min, costo_usd))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def actualizar_producto(prod_id: int, nombre: str, precio_usd: float, costo_usd: float, stock: int, stock_min: int) -> bool:
    """Actualiza los datos del producto incluyendo su costo de compra (CPP)."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE productos_mercancia
            SET nombre = ?, precio_usd = ?, costo_unitario_usd = ?, stock = ?, stock_minimo = ?
            WHERE id = ?;
        """, (nombre.strip(), precio_usd, costo_usd, stock, stock_min, prod_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logging.error(f"Error actualizando producto: {e}")
        return False
    finally:
        conn.close()

def eliminar_producto(prod_id: int) -> bool:
    """Elimina un producto del catálogo."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM productos_mercancia WHERE id = ?;", (prod_id,))
        conn.commit()
        return True
    except sqlite3.Error:
        conn.rollback()
        return False
    finally:
        conn.close()

def descontar_stock_producto(nombre: str, cantidad: int) -> bool:
    """Resta unidades vendidas del inventario."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE productos_mercancia
            SET stock = MAX(0, stock - ?)
            WHERE nombre = ?;
        """, (cantidad, nombre.strip()))
        conn.commit()
        return True
    except sqlite3.Error:
        conn.rollback()
        return False
    finally:
        conn.close()

# =============================================================================
# CONSULTA DE AUDITORÍA BANCARIA P2P (PAGO MÓVIL)
# =============================================================================

def obtener_reporte_p2p(fecha_inicio: str, fecha_fin: str) -> list:
    """Consulta todas las transacciones de Pago Móvil incluyendo alquileres, mini-bar y cobro de daños."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    tasa = obtener_tasa_bcv()
    transacciones = []
    try:
        # A. Pago Móvil por Alquiler de Habitaciones
        cursor.execute("""
            SELECT fecha, hab_codigo, 'Alquiler Habitación' AS concepto, cliente_nombre,
                   p2p_ci, p2p_telefono, p2p_referencia, monto AS monto_usd, turno, recepcionista
            FROM pagos
            WHERE metodo = 'PAGO MOVIL' AND DATE(fecha) BETWEEN ? AND ?;
        """, (fecha_inicio, fecha_fin))
        for r in cursor.fetchall():
            d = dict(r)
            d["monto_bs"] = d["monto_usd"] * tasa
            d["tasa_bcv"] = tasa
            transacciones.append(d)

        # B. Pago Móvil por Venta de Mercancía / Mini-Bar
        cursor.execute("""
            SELECT fecha, hab_codigo, 'Venta Mini-Bar' AS concepto, 'Cliente Habitación' AS cliente_nombre,
                   p2p_ci, p2p_telefono, p2p_referencia, total_usd AS monto_usd, total_bs AS monto_bs, turno, recepcionista
            FROM ventas_mercancia
            WHERE metodo = 'PAGO MOVIL' AND DATE(fecha) BETWEEN ? AND ?;
        """, (fecha_inicio, fecha_fin))
        for r in cursor.fetchall():
            d = dict(r)
            d["tasa_bcv"] = tasa
            transacciones.append(d)

        # C. Pago Móvil por Cobro de Daños a Huéspedes
        cursor.execute("""
            SELECT fecha, hab_codigo, ('Daño: ' || concepto_dano) AS concepto,
                   (cliente_nombre || ' (C.I: ' || cliente_ci || ')') AS cliente_nombre,
                   p2p_ci, p2p_telefono, p2p_referencia, monto_usd, monto_bs, turno, recepcionista
            FROM cobro_danos_estancia
            WHERE metodo = 'PAGO MOVIL' AND DATE(fecha) BETWEEN ? AND ?;
        """, (fecha_inicio, fecha_fin))
        for r in cursor.fetchall():
            d = dict(r)
            d["tasa_bcv"] = tasa
            transacciones.append(d)

        # Ordenar cronológicamente
        transacciones.sort(key=lambda x: x["fecha"], reverse=True)
        return transacciones
    finally:
        conn.close()


# =============================================================================
# VENTA DE MERCANCÍA CON PERSISTENCIA DE COSTO CPP HISTÓRICO
# =============================================================================
def registrar_venta_mercancia_carrito(cabecera: dict, items: list) -> int | None:
    """Registra la venta guardando el costo CPP exacto de cada ítem en el momento de la venta."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        conn.execute("BEGIN TRANSACTION;")

        cursor.execute("""
            INSERT INTO ventas_mercancia (
                hab_codigo, total_usd, total_bs, metodo, p2p_referencia,
                p2p_ci, p2p_telefono, fecha, turno, recepcionista
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            cabecera["hab_codigo"], cabecera["total_usd"], cabecera["total_bs"],
            cabecera["metodo"], cabecera.get("p2p_referencia"), cabecera.get("p2p_ci"),
            cabecera.get("p2p_telefono"), cabecera["fecha"], cabecera["turno"],
            cabecera["recepcionista"]
        ))

        venta_id = cursor.lastrowid

        for it in items:
            # Obtener el costo CPP actual del producto
            cursor.execute("SELECT costo_unitario_usd FROM productos_mercancia WHERE nombre = ?;", (it["producto"],))
            row_prod = cursor.fetchone()
            costo_unit = row_prod["costo_unitario_usd"] if row_prod and row_prod["costo_unitario_usd"] else 0.0
            
            sub_costo = costo_unit * it["cantidad"]
            ganancia = it["subtotal_usd"] - sub_costo

            cursor.execute("""
                INSERT INTO ventas_mercancia_detalle (
                    venta_id, producto, cantidad, precio_unit_usd, subtotal_usd, subtotal_bs, costo_unitario_usd, ganancia_usd
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                venta_id, it["producto"], it["cantidad"],
                it["precio_unit_usd"], it["subtotal_usd"], it["subtotal_bs"],
                costo_unit, ganancia
            ))

        conn.commit()
        return venta_id
    except Exception as e:
        conn.rollback()
        logging.error(f"Error registrando venta con CPP: {e}")
        return None
    finally:
        conn.close()
# =============================================================================
# FUNCIONES: PAGOS Y CIERRE DE CAJA
# =============================================================================

def registrar_pago_ingreso(datos_pago: dict) -> bool:
    """Registra pago de alquiler de habitación."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO pagos (
                hab_codigo, monto, metodo, p2p_referencia, p2p_ci, p2p_telefono,
                cliente_nombre, cliente_cedula, ac_nombre, ac_cedula, fecha, turno,
                recepcionista, bebidas_usd, bebidas_bs
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            datos_pago["hab_codigo"], datos_pago["monto"], datos_pago["metodo"],
            datos_pago.get("p2p_referencia"), datos_pago.get("p2p_ci"), datos_pago.get("p2p_telefono"),
            datos_pago["cliente_nombre"], datos_pago["cliente_cedula"],
            datos_pago.get("ac_nombre"), datos_pago.get("ac_cedula"),
            datos_pago["fecha"], datos_pago["turno"], datos_pago["recepcionista"],
            datos_pago.get("bebidas_usd", 0.0), datos_pago.get("bebidas_bs", 0.0)
        ))
        conn.commit()
        return True
    except sqlite3.Error as e:
        conn.rollback()
        logging.error(f"Error al registrar pago: {e}")
        return False
    finally:
        conn.close()


def verificar_cierre_existente(fecha: str, turno: str) -> bool:
    """Verifica si el turno ya fue cerrado."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM cierres_turno WHERE fecha = ? AND turno = ?;", (fecha, turno))
        return cursor.fetchone() is not None
    finally:
        conn.close()


def registrar_cierre_turno(datos_cierre: dict) -> bool:
    """Guarda el cierre del turno."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO cierres_turno (
                fecha, turno, total_bs, total_usd, total_p2p, total_punto, recepcionista
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (
            datos_cierre["fecha"], datos_cierre["turno"], datos_cierre["total_bs"],
            datos_cierre["total_usd"], datos_cierre["total_p2p"], datos_cierre["total_punto"],
            datos_cierre["recepcionista"]
        ))
        conn.commit()
        return True
    except sqlite3.Error:
        conn.rollback()
        return False
    finally:
        conn.close()


def resetear_base_datos() -> bool:
    """
    Vacía todas las tablas de forma segura desactivando temporalmente 
    las claves foráneas para evitar conflictos de integridad referencial.
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        # 1. Desactivar temporalmente restricciones de Foreign Keys
        cursor.execute("PRAGMA foreign_keys = OFF;")
        conn.execute("BEGIN TRANSACTION;")

        # 2. Vaciado de todas las tablas
        tablas_a_vaciar = [
            "estancias_activas", "historial_estancias", "pagos",
            "ventas_mercancia_detalle", "ventas_mercancia", "productos_mercancia",
            "mantenimiento_habitaciones", "cobro_danos_estancia", "cierres_turno",
            "auditoria_logs", "morosos", "habitaciones", "usuarios", "configuracion"
        ]

        for tabla in tablas_a_vaciar:
            cursor.execute(f"DELETE FROM {tabla};")

        # 3. Reiniciar contadores autoincrementales a 1
        cursor.execute("DELETE FROM sqlite_sequence;")

        conn.commit()
        
        # 4. Reactivar restricciones de Foreign Keys
        cursor.execute("PRAGMA foreign_keys = ON;")
        conn.close()

        # 5. Re-crear esquema y datos semilla (Admin y Tasa BCV)
        inicializar_bd()
        return True
    except Exception as e:
        conn.rollback()
        conn.close()
        logging.error(f"Error al resetear la BD: {e}")
        return False

# =============================================================================
# HELPER DE FORMATEO MONETARIO VENEZOLANO (PUNTO Y COMA)
# =============================================================================

def formatear_bs(monto: float) -> str:
    """Formatea montos en formato contable venezolano: 34.818,08 Bs."""
    return f"{monto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " Bs"

def formatear_usd(monto: float) -> str:
    """Formatea montos en dólares: $40.00."""
    return f"${monto:,.2f}"

# =============================================================================
# FUNCIÓN: DETALLE CONSOLIDADO PARA CIERRES DE TURNO
# =============================================================================

def obtener_detalle_cierre_turno(fecha: str, turno: str) -> dict:
    """Agrupa habitaciones, mercancía y cobros de daños para la conciliación del turno."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    tasa = obtener_tasa_bcv()
    
    try:
        # A. Alquileres de Habitaciones
        cursor.execute("""
            SELECT hab_codigo, monto, metodo, bebidas_usd, bebidas_bs
            FROM pagos
            WHERE DATE(fecha) = ? AND turno = ?;
        """, (fecha, turno))
        pagos_hab = cursor.fetchall()

        # B. Ventas de Mercancía
        cursor.execute("""
            SELECT v.id, v.hab_codigo, v.total_usd, v.total_bs, v.metodo,
                   d.producto, d.cantidad, d.subtotal_usd, d.subtotal_bs
            FROM ventas_mercancia v
            JOIN ventas_mercancia_detalle d ON v.id = d.venta_id
            WHERE DATE(v.fecha) = ? AND v.turno = ?;
        """, (fecha, turno))
        ventas_raw = cursor.fetchall()

        # C. NUEVO: Cobros por Daños en este Turno
        cursor.execute("""
            SELECT hab_codigo, cliente_nombre, cliente_ci, concepto_dano, monto_usd, monto_bs,
                   metodo, p2p_referencia, fecha
            FROM cobro_danos_estancia
            WHERE DATE(fecha) = ? AND turno = ?;
        """, (fecha, turno))
        danos_turno = [dict(r) for r in cursor.fetchall()]

        # Matriz 1: Habitaciones
        hab_resumen = {}
        for p in pagos_hab:
            cod = p["hab_codigo"]
            if cod not in hab_resumen:
                hab_resumen[cod] = {
                    "habitacion": cod, "cantidad": 0,
                    "alq_usd": 0.0, "alq_bs": 0.0, "alq_p2p": 0.0, "alq_punto": 0.0,
                    "mer_usd": 0.0, "mer_bs": 0.0, "mer_p2p": 0.0, "mer_punto": 0.0,
                    "total_bs": 0.0, "total_usd": 0.0
                }
            hab_resumen[cod]["cantidad"] += 1
            m_usd = p["monto"]
            metodo = p["metodo"]

            if metodo == "EFECTIVO USD":
                hab_resumen[cod]["alq_usd"] += m_usd; hab_resumen[cod]["total_usd"] += m_usd
            elif metodo == "EFECTIVO BS":
                m_bs = m_usd * tasa; hab_resumen[cod]["alq_bs"] += m_bs; hab_resumen[cod]["total_bs"] += m_bs
            elif metodo == "PAGO MOVIL":
                m_bs = m_usd * tasa; hab_resumen[cod]["alq_p2p"] += m_bs; hab_resumen[cod]["total_bs"] += m_bs
            elif metodo == "PUNTO DE VENTA":
                m_bs = m_usd * tasa; hab_resumen[cod]["alq_punto"] += m_bs; hab_resumen[cod]["total_bs"] += m_bs

        for v in ventas_raw:
            cod = v["hab_codigo"]
            if cod not in hab_resumen:
                hab_resumen[cod] = {
                    "habitacion": cod, "cantidad": 0,
                    "alq_usd": 0.0, "alq_bs": 0.0, "alq_p2p": 0.0, "alq_punto": 0.0,
                    "mer_usd": 0.0, "mer_bs": 0.0, "mer_p2p": 0.0, "mer_punto": 0.0,
                    "total_bs": 0.0, "total_usd": 0.0
                }
            m_usd = v["subtotal_usd"]
            m_bs = v["subtotal_bs"]
            metodo = v["metodo"]

            if metodo == "EFECTIVO USD":
                hab_resumen[cod]["mer_usd"] += m_usd; hab_resumen[cod]["total_usd"] += m_usd
            elif metodo == "EFECTIVO BS":
                hab_resumen[cod]["mer_bs"] += m_bs; hab_resumen[cod]["total_bs"] += m_bs
            elif metodo == "PAGO MOVIL":
                hab_resumen[cod]["mer_p2p"] += m_bs; hab_resumen[cod]["total_bs"] += m_bs
            elif metodo == "PUNTO DE VENTA":
                hab_resumen[cod]["mer_punto"] += m_bs; hab_resumen[cod]["total_bs"] += m_bs

        # Matriz 2: Productos Mercancía
        prod_resumen = {}
        for v in ventas_raw:
            p_nom = v["producto"]
            if p_nom not in prod_resumen:
                prod_resumen[p_nom] = {
                    "producto": p_nom, "cantidad": 0,
                    "usd": 0.0, "bs": 0.0, "p2p": 0.0, "punto": 0.0,
                    "total_bs": 0.0, "total_usd": 0.0
                }
            cant = v["cantidad"]
            m_usd = v["subtotal_usd"]
            m_bs = v["subtotal_bs"]
            metodo = v["metodo"]
            prod_resumen[p_nom]["cantidad"] += cant

            if metodo == "EFECTIVO USD":
                prod_resumen[p_nom]["usd"] += m_usd; prod_resumen[p_nom]["total_usd"] += m_usd
            elif metodo == "EFECTIVO BS":
                prod_resumen[p_nom]["bs"] += m_bs; prod_resumen[p_nom]["total_bs"] += m_bs
            elif metodo == "PAGO MOVIL":
                prod_resumen[p_nom]["p2p"] += m_bs; prod_resumen[p_nom]["total_bs"] += m_bs
            elif metodo == "PUNTO DE VENTA":
                prod_resumen[p_nom]["punto"] += m_bs; prod_resumen[p_nom]["total_bs"] += m_bs

        # Totales Globales (SUMANDO ALQUILERES + MERCANCÍA + DAÑOS)
        tot_efectivo_usd = sum(h["alq_usd"] + h["mer_usd"] for h in hab_resumen.values())
        tot_efectivo_bs = sum(h["alq_bs"] + h["mer_bs"] for h in hab_resumen.values())
        tot_p2p_bs = sum(h["alq_p2p"] + h["mer_p2p"] for h in hab_resumen.values())
        tot_punto_bs = sum(h["alq_punto"] + h["mer_punto"] for h in hab_resumen.values())

        # Sumar los Cobros por Daños en sus métodos correspondientes
        for d in danos_turno:
            d_usd = d["monto_usd"]
            d_bs = d["monto_bs"]
            d_met = d["metodo"]

            if d_met == "EFECTIVO USD":
                tot_efectivo_usd += d_usd
            elif d_met == "EFECTIVO BS":
                tot_efectivo_bs += d_bs
            elif d_met == "PAGO MOVIL":
                tot_p2p_bs += d_bs
            elif d_met == "PUNTO DE VENTA":
                tot_punto_bs += d_bs

        tot_bs_general = tot_efectivo_bs + tot_p2p_bs + tot_punto_bs

        return {
            "fecha": fecha,
            "turno": turno,
            "tasa_bcv": tasa,
            "habitaciones": list(hab_resumen.values()),
            "mercancia": list(prod_resumen.values()),
            "danos": danos_turno,  # <-- LISTA DE DAÑOS COBRADOS EN EL TURNO
            "total_efectivo_usd": tot_efectivo_usd,
            "total_efectivo_bs": tot_efectivo_bs,
            "total_p2p_bs": tot_p2p_bs,
            "total_punto_bs": tot_punto_bs,
            "total_bs_consolidado": tot_bs_general
        }
    finally:
        conn.close()
# =============================================================================
# EXTENDER ESTANCIA Y REGISTRAR COBRO
# =============================================================================

def extender_estancia_habitacion(hab_codigo: str, nueva_salida: str, datos_pago: dict) -> bool:
    """
    Extiende la fecha de salida de una estancia activa, reactiva el estado a 'Ocupada' (Rojo)
    y registra el nuevo pago en la contabilidad del turno.
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        conn.execute("BEGIN TRANSACTION;")

        # 1. Actualizar fecha de salida estimada
        cursor.execute("""
            UPDATE estancias_activas 
            SET fecha_salida_estimada = ? 
            WHERE hab_codigo = ?;
        """, (nueva_salida, hab_codigo))

        # 2. Revertir estado a 'Ocupada' (en caso de que estuviese en 'Tiempo_Vencido')
        cursor.execute("UPDATE habitaciones SET estado = 'Ocupada' WHERE codigo = ?;", (hab_codigo,))

        # 3. Registrar el pago de la extensión en la caja
        cursor.execute("""
            INSERT INTO pagos (
                hab_codigo, monto, metodo, p2p_referencia, p2p_ci, p2p_telefono,
                cliente_nombre, cliente_cedula, ac_nombre, ac_cedula, fecha, turno,
                recepcionista, bebidas_usd, bebidas_bs
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            datos_pago["hab_codigo"], datos_pago["monto"], datos_pago["metodo"],
            datos_pago.get("p2p_referencia"), datos_pago.get("p2p_ci"), datos_pago.get("p2p_telefono"),
            datos_pago["cliente_nombre"], datos_pago["cliente_cedula"],
            datos_pago.get("ac_nombre"), datos_pago.get("ac_cedula"),
            datos_pago["fecha"], datos_pago["turno"], datos_pago["recepcionista"],
            0.0, 0.0
        ))

        conn.commit()
        return True
    except sqlite3.Error as e:
        conn.rollback()
        logging.error(f"Error al extender estancia en habitación {hab_codigo}: {e}")
        return False
    finally:
        conn.close()      

# =============================================================================
# FUNCIONES: MOTOR DE AUDITORÍA Y TRAZABILIDAD
# =============================================================================

def registrar_auditoria(usuario: str, rol: str, accion: str, descripcion: str):
    """Inserta automáticamente un evento en la bitácora de auditoría."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO auditoria_logs (usuario, rol, accion, descripcion, fecha)
            VALUES (?, ?, ?, ?, ?);
        """, (usuario, rol, accion.upper(), descripcion, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    except Exception as e:
        logging.error(f"Error al registrar auditoría: {e}")
    finally:
        conn.close()

# =============================================================================
# HELPER: LOCALIZADOR UNIVERSAL DE RECURSOS (COMPATIBLE CON .EXE PYINSTALLER)
# =============================================================================
import sys

def obtener_ruta_recurso(nombre_archivo: str) -> str:
    """
    Retorna la ruta absoluta del recurso. Funciona en desarrollo y dentro del ejecutable .exe
    """
    # 1. Si está corriendo como ejecutable de PyInstaller
    if hasattr(sys, '_MEIPASS'):
        ruta_bundle = os.path.join(sys._MEIPASS, nombre_archivo)
        if os.path.exists(ruta_bundle):
            return ruta_bundle

    # 2. Si está al lado del ejecutable .exe o en la carpeta raíz
    ruta_directa = os.path.join(os.path.abspath("."), nombre_archivo)
    if os.path.exists(ruta_directa):
        return ruta_directa

    # 3. Ruta relativa al directorio base del proyecto
    ruta_base = os.path.join(BASE_DIR, "..", nombre_archivo)
    if os.path.exists(ruta_base):
        return ruta_base

    return nombre_archivo


# =============================================================================
# CONSULTA DE AUDITORÍA CON FILTRO POR USUARIO Y ACCIÓN
# =============================================================================
def _garantizar_tabla_auditoria(cursor):
    """Crea la tabla auditoria_logs de inmediato si no existe en la base de datos."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auditoria_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            rol TEXT NOT NULL,
            accion TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)


def registrar_auditoria(usuario: str, rol: str, accion: str, descripcion: str):
    """Inserta un evento en la bitácora de auditoría asegurando la existencia de la tabla."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        _garantizar_tabla_auditoria(cursor)
        cursor.execute("""
            INSERT INTO auditoria_logs (usuario, rol, accion, descripcion, fecha)
            VALUES (?, ?, ?, ?, ?);
        """, (usuario, rol, accion.upper(), descripcion, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    except Exception as e:
        logging.error(f"Error al registrar auditoría: {e}")
    finally:
        conn.close()


def obtener_logs_auditoria(fecha_inicio: str, fecha_fin: str, accion_filtro: str = "TODAS", usuario_filtro: str = "TODOS") -> list:
    """Consulta la bitácora de auditoría creando la tabla automáticamente si faltaba."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        _garantizar_tabla_auditoria(cursor)
        conn.commit()

        query = "SELECT id, usuario, rol, accion, descripcion, fecha FROM auditoria_logs WHERE DATE(fecha) >= DATE(?) AND DATE(fecha) <= DATE(?)"
        params = [fecha_inicio, fecha_fin]

        if accion_filtro and accion_filtro != "TODAS":
            query += " AND accion = ?"
            params.append(accion_filtro)

        if usuario_filtro and usuario_filtro != "TODOS":
            query += " AND usuario = ?"
            params.append(usuario_filtro)

        query += " ORDER BY fecha DESC;"
        cursor.execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
# =============================================================================
# ESQUEMAS Y FUNCIONES: CPP (COSTO PROMEDIO) Y MANTENIMIENTO DE HABITACIONES
# =============================================================================

def inicializar_tablas_avanzadas():
    """Crea las tablas avanzadas usando executescript para evitar errores de múltiples sentencias."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        # Migraciones individuales de columnas
        cursor.execute("PRAGMA table_info(productos_mercancia);")
        cols = [c["name"] for c in cursor.fetchall()]
        if "costo_unitario_usd" not in cols:
            cursor.execute("ALTER TABLE productos_mercancia ADD COLUMN costo_unitario_usd REAL DEFAULT 0.0;")

        cursor.execute("PRAGMA table_info(ventas_mercancia_detalle);")
        cols_det = [c["name"] for c in cursor.fetchall()]
        if "costo_unitario_usd" not in cols_det:
            cursor.execute("ALTER TABLE ventas_mercancia_detalle ADD COLUMN costo_unitario_usd REAL DEFAULT 0.0;")
            cursor.execute("ALTER TABLE ventas_mercancia_detalle ADD COLUMN ganancia_usd REAL DEFAULT 0.0;")

        # Creación de tablas avanzadas
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS mantenimiento_habitaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hab_codigo TEXT NOT NULL,
                tipo_averia TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                tecnico_responsable TEXT NOT NULL,
                costo_reparacion_usd REAL DEFAULT 0,
                costo_reparacion_bs REAL DEFAULT 0,
                fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_fin TIMESTAMP,
                estado TEXT CHECK(estado IN ('EN_PROCESO', 'FINALIZADO')) DEFAULT 'EN_PROCESO',
                reportado_por TEXT NOT NULL,
                FOREIGN KEY (hab_codigo) REFERENCES habitaciones (codigo)
            );

            CREATE TABLE IF NOT EXISTS cobro_danos_estancia (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hab_codigo TEXT NOT NULL,
                cliente_nombre TEXT NOT NULL,
                cliente_ci TEXT DEFAULT '',
                concepto_dano TEXT NOT NULL,
                monto_usd REAL NOT NULL,
                monto_bs REAL NOT NULL,
                metodo TEXT NOT NULL,
                p2p_referencia TEXT DEFAULT '',
                p2p_ci TEXT DEFAULT '',
                p2p_telefono TEXT DEFAULT '',
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                turno TEXT NOT NULL,
                recepcionista TEXT NOT NULL
            );
        """)
        conn.commit()
    except Exception as e:
        conn.rollback()
        logging.error(f"Error al inicializar tablas avanzadas: {e}")
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# MOTOR CONTABLE: REGISTRO DE COMPRAS CON COSTO PROMEDIO PONDERADO (CPP)
# -----------------------------------------------------------------------------
def registrar_compra_inventario_cpp(prod_id: int, cant_comprada: int, costo_unit_compra_usd: float) -> bool:
    """
    Aplica el método de Costo Promedio Ponderado (CPP) al ingresar mercancía nueva.
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT stock, costo_unitario_usd FROM productos_mercancia WHERE id = ?;", (prod_id,))
        row = cursor.fetchone()
        if not row:
            return False

        stock_actual = row["stock"]
        costo_actual = row["costo_unitario_usd"]

        # Fórmula CPP
        costo_total_previo = stock_actual * costo_actual
        costo_total_nuevo = cant_comprada * costo_unit_compra_usd
        nuevo_stock = stock_actual + cant_comprada

        nuevo_costo_promedio = (costo_total_previo + costo_total_nuevo) / nuevo_stock if nuevo_stock > 0 else costo_unit_compra_usd

        cursor.execute("""
            UPDATE productos_mercancia
            SET stock = ?, costo_unitario_usd = ?
            WHERE id = ?;
        """, (nuevo_stock, round(nuevo_costo_promedio, 4), prod_id))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logging.error(f"Error calculando CPP: {e}")
        return False
    finally:
        conn.close()


# =============================================================================
# REPORTE DE UTILIDAD Y GANANCIAS (DUAL $ Y BS)
# =============================================================================
def obtener_reporte_utilidad_inventario(fecha_inicio: str, fecha_fin: str) -> list:
    """Calcula la matriz contable de ingresos, costos y ganancias en ambas monedas."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    tasa = obtener_tasa_bcv()
    try:
        cursor.execute("""
            SELECT d.producto,
                   SUM(d.cantidad) AS unidades_vendidas,
                   AVG(d.precio_unit_usd) AS precio_prom_usd,
                   AVG(d.costo_unitario_usd) AS costo_prom_usd,
                   SUM(d.subtotal_usd) AS ingreso_total_usd,
                   SUM(d.cantidad * d.costo_unitario_usd) AS costo_total_usd,
                   SUM(d.subtotal_usd - (d.cantidad * d.costo_unitario_usd)) AS utilidad_neta_usd
            FROM ventas_mercancia_detalle d
            JOIN ventas_mercancia v ON d.venta_id = v.id
            WHERE DATE(v.fecha) BETWEEN ? AND ?
            GROUP BY d.producto
            ORDER BY utilidad_neta_usd DESC;
        """, (fecha_inicio, fecha_fin))

        reporte = []
        for r in cursor.fetchall():
            d = dict(r)
            d["ingreso_total_bs"] = d["ingreso_total_usd"] * tasa
            d["costo_total_bs"] = d["costo_total_usd"] * tasa
            d["utilidad_neta_bs"] = d["utilidad_neta_usd"] * tasa
            d["margen_pct"] = (d["utilidad_neta_usd"] / d["ingreso_total_usd"] * 100) if d["ingreso_total_usd"] > 0 else 0.0
            reporte.append(d)
        return reporte
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# CRUD: MANTENIMIENTO, AVERÍAS Y CONTROL DE DAÑOS
# -----------------------------------------------------------------------------
def enviar_habitacion_mantenimiento(hab_codigo: str, tipo_averia: str, descripcion: str, tecnico: str, costo_usd: float, user: str) -> bool:
    """Bloquea la habitación a estado 'Mantenimiento' y registra la orden de reparación."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    tasa = obtener_tasa_bcv()
    try:
        conn.execute("BEGIN TRANSACTION;")
        cursor.execute("""
            INSERT INTO mantenimiento_habitaciones (
                hab_codigo, tipo_averia, descripcion, tecnico_responsable,
                costo_reparacion_usd, costo_reparacion_bs, reportado_por
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (hab_codigo, tipo_averia, descripcion, tecnico, costo_usd, costo_usd * tasa, user))

        cursor.execute("UPDATE habitaciones SET estado = 'Mantenimiento' WHERE codigo = ?;", (hab_codigo,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logging.error(f"Error al enviar habitación a mantenimiento: {e}")
        return False
    finally:
        conn.close()


def finalizar_mantenimiento_habitacion(mant_id: int, hab_codigo: str) -> bool:
    """Finaliza la reparación y regresa la habitación al estado 'Limpia' (Verde)."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        conn.execute("BEGIN TRANSACTION;")
        cursor.execute("""
            UPDATE mantenimiento_habitaciones
            SET estado = 'FINALIZADO', fecha_fin = ?
            WHERE id = ?;
        """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), mant_id))

        cursor.execute("UPDATE habitaciones SET estado = 'Limpia' WHERE codigo = ?;", (hab_codigo,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logging.error(f"Error al finalizar mantenimiento: {e}")
        return False
    finally:
        conn.close()


def obtener_ordenes_mantenimiento(solo_activas: bool = False) -> list:
    """Retorna las órdenes de mantenimiento registradas."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        if solo_activas:
            cursor.execute("SELECT * FROM mantenimiento_habitaciones WHERE estado = 'EN_PROCESO' ORDER BY fecha_inicio DESC;")
        else:
            cursor.execute("SELECT * FROM mantenimiento_habitaciones ORDER BY fecha_inicio DESC;")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def registrar_cobro_dano(hab_codigo: str, cliente: str, cliente_ci: str, concepto: str, monto_usd: float, metodo: str, user: str, p2p_ref=None, p2p_ci=None, p2p_tel=None) -> bool:
    """Registra el cobro de daños con C.I. del huésped y soporte para Pago Móvil."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    tasa = obtener_tasa_bcv()
    ahora = datetime.now()
    turno = "MAÑANA" if 8 <= ahora.hour < 17 else "NOCHE"
    try:
        # Auto-migración por si falta columna cliente_ci o p2p
        cursor.execute("PRAGMA table_info(cobro_danos_estancia);")
        cols = [c["name"] for c in cursor.fetchall()]
        if "cliente_ci" not in cols:
            cursor.execute("ALTER TABLE cobro_danos_estancia ADD COLUMN cliente_ci TEXT DEFAULT '';")
            cursor.execute("ALTER TABLE cobro_danos_estancia ADD COLUMN p2p_referencia TEXT DEFAULT '';")
            cursor.execute("ALTER TABLE cobro_danos_estancia ADD COLUMN p2p_ci TEXT DEFAULT '';")
            cursor.execute("ALTER TABLE cobro_danos_estancia ADD COLUMN p2p_telefono TEXT DEFAULT '';")

        cursor.execute("""
            INSERT INTO cobro_danos_estancia (
                hab_codigo, cliente_nombre, cliente_ci, concepto_dano, monto_usd, monto_bs,
                metodo, p2p_referencia, p2p_ci, p2p_telefono, fecha, turno, recepcionista
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (hab_codigo, cliente, cliente_ci, concepto, monto_usd, monto_usd * tasa, metodo, p2p_ref, p2p_ci, p2p_tel, ahora.strftime("%Y-%m-%d %H:%M:%S"), turno, user))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logging.error(f"Error al registrar cobro de daño: {e}")
        return False
    finally:
        conn.close()

# =============================================================================
# MOTOR DE BUSINESS INTELLIGENCE: CONSULTA DE MÉTRICAS Y KPIS
# =============================================================================

def obtener_metricas_kpis(fecha_inicio: str, fecha_fin: str) -> dict:
    """
    Agrupa y calcula todas las métricas estadísticas y financieras
    para el Dashboard de KPIs y Gráficos Gerenciales.
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    tasa = obtener_tasa_bcv()
    try:
        # 1. Ingresos por Alquiler de Habitaciones
        cursor.execute("""
            SELECT hab_codigo, monto, metodo, fecha
            FROM pagos
            WHERE DATE(fecha) BETWEEN ? AND ?;
        """, (fecha_inicio, fecha_fin))
        pagos = [dict(r) for r in cursor.fetchall()]

        # 2. Ventas de Mercancía
        cursor.execute("""
            SELECT v.hab_codigo, v.total_usd, v.total_bs, v.metodo, v.fecha,
                   d.producto, d.cantidad, d.subtotal_usd, d.costo_unitario_usd
            FROM ventas_mercancia v
            JOIN ventas_mercancia_detalle d ON v.id = d.venta_id
            WHERE DATE(v.fecha) BETWEEN ? AND ?;
        """, (fecha_inicio, fecha_fin))
        ventas_mer = [dict(r) for r in cursor.fetchall()]

        # 3. Cobro de Daños
        cursor.execute("""
            SELECT monto_usd, monto_bs, metodo, fecha
            FROM cobro_danos_estancia
            WHERE DATE(fecha) BETWEEN ? AND ?;
        """, (fecha_inicio, fecha_fin))
        danos = [dict(r) for r in cursor.fetchall()]

        # --- CÁLCULO DE TOTALES ---
        total_ingresos_usd = sum(p["monto"] for p in pagos) + sum(v["subtotal_usd"] for v in ventas_mer) + sum(d["monto_usd"] for d in danos)
        total_ingresos_bs = total_ingresos_usd * tasa
        total_estancias = len(pagos)
        ticket_promedio_usd = (total_ingresos_usd / total_estancias) if total_estancias > 0 else 0.0

        # Utilidad Mini-Bar (Ingreso - Costo)
        costo_total_minibar = sum(v["cantidad"] * v["costo_unitario_usd"] for v in ventas_mer)
        ingreso_minibar = sum(v["subtotal_usd"] for v in ventas_mer)
        utilidad_minibar_usd = ingreso_minibar - costo_total_minibar

        # --- ROTACIÓN POR HABITACIÓN ---
        rotacion_hab = {}
        for p in pagos:
            h = p["hab_codigo"]
            rotacion_hab[h] = rotacion_hab.get(h, 0) + 1

        # --- CURVA DE HORAS PICO (0 a 23 hrs) ---
        horas_pico = {h: 0 for h in range(24)}
        for p in pagos:
            try:
                hora = datetime.strptime(p["fecha"], "%Y-%m-%d %H:%M:%S").hour
                horas_pico[hora] += 1
            except Exception:
                pass

        # --- DESGLOSE POR MÉTODO DE PAGO ---
        metodos_pago = {"EFECTIVO USD": 0.0, "EFECTIVO BS": 0.0, "PAGO MOVIL": 0.0, "PUNTO DE VENTA": 0.0}
        
        # 1. Alquileres
        for p in pagos:
            met = p["metodo"]
            if met in metodos_pago:
                metodos_pago[met] += p["monto"]

        # 2. Mini-Bar / Mercancía (Total USD por factura)
        # Usamos un set o agrupamos para no duplicar si la consulta trae joins de detalles
        ventas_unicas = {}
        for v in ventas_mer:
            ventas_unicas[v["id"] if "id" in v else (v["fecha"], v["hab_codigo"])] = (v["metodo"], v["total_usd"])
        
        for met, monto in ventas_unicas.values():
            if met in metodos_pago:
                metodos_pago[met] += monto

        # 3. Cobros de Daños
        for d in danos:
            met = d["metodo"]
            if met in metodos_pago:
                metodos_pago[met] += d["monto_usd"]

        # --- TOP 5 PRODUCTOS MÁS VENDIDOS ---
        productos_vendidos = {}
        for v in ventas_mer:
            prod = v["producto"]
            productos_vendidos[prod] = productos_vendidos.get(prod, 0) + v["cantidad"]

        top_productos = sorted(productos_vendidos.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "total_ingresos_usd": total_ingresos_usd,
            "total_ingresos_bs": total_ingresos_bs,
            "total_estancias": total_estancias,
            "ticket_promedio_usd": ticket_promedio_usd,
            "utilidad_minibar_usd": utilidad_minibar_usd,
            "rotacion_hab": rotacion_hab,
            "horas_pico": horas_pico,
            "metodos_pago": metodos_pago,
            "top_productos": top_productos
        }
    finally:
        conn.close()

# =============================================================================
# CONFIGURACIÓN PERSISTENTE DE NOTIFICACIONES (TELEGRAM, WHATSAPP Y EMAIL)
# =============================================================================

def obtener_config_notificaciones() -> dict:
    """Obtiene las credenciales y estado activo de los canales de notificación."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT clave, valor FROM configuracion WHERE clave LIKE 'notif_%';")
        rows = cursor.fetchall()
        config = {r["clave"]: r["valor"] for r in rows}
        return {
            # Telegram
            "telegram_token": config.get("notif_tg_token", ""),
            "telegram_chat_id": config.get("notif_tg_chat_id", ""),
            "telegram_activo": config.get("notif_tg_activo", "0"),
            # WhatsApp (CallMeBot)
            "whatsapp_phone": config.get("notif_wa_phone", ""),
            "whatsapp_apikey": config.get("notif_wa_apikey", ""),
            "whatsapp_activo": config.get("notif_wa_activo", "0"),
            # Email (SMTP)
            "email_host": config.get("notif_em_host", "smtp.gmail.com"),
            "email_port": config.get("notif_em_port", "587"),
            "email_user": config.get("notif_em_user", ""),
            "email_pass": config.get("notif_em_pass", ""),
            "email_destino": config.get("notif_em_destino", ""),
            "email_activo": config.get("notif_em_activo", "0")
        }
    finally:
        conn.close()


def guardar_config_notificaciones(datos: dict) -> bool:
    """Guarda las claves y credenciales de los canales de notificación."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        mapeo = {
            "notif_tg_token": datos.get("telegram_token", ""),
            "notif_tg_chat_id": datos.get("telegram_chat_id", ""),
            "notif_tg_activo": datos.get("telegram_activo", "0"),
            "notif_wa_phone": datos.get("whatsapp_phone", ""),
            "notif_wa_apikey": datos.get("whatsapp_apikey", ""),
            "notif_wa_activo": datos.get("whatsapp_activo", "0"),
            "notif_em_host": datos.get("email_host", "smtp.gmail.com"),
            "notif_em_port": datos.get("email_port", "587"),
            "notif_em_user": datos.get("email_user", ""),
            "notif_em_pass": datos.get("email_pass", ""),
            "notif_em_destino": datos.get("email_destino", ""),
            "notif_em_activo": datos.get("email_activo", "0")
        }
        for clave, valor in mapeo.items():
            cursor.execute("""
                INSERT INTO configuracion (clave, valor) VALUES (?, ?)
                ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor;
            """, (clave, str(valor)))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logging.error(f"Error guardando configuración de notificaciones: {e}")
        return False
    finally:
        conn.close()

# =============================================================================
# CONTROL DE CALIDAD DE CAMARERAS Y TIEMPOS DE ROTACIÓN (SLA)
# =============================================================================

def inicializar_tabla_limpieza():
    """Crea la tabla historial_limpieza y migra las columnas de última limpieza."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        # 1. Columnas en habitaciones
        cursor.execute("PRAGMA table_info(habitaciones);")
        cols = [c["name"] for c in cursor.fetchall()]
        if "ultima_camarera" not in cols:
            cursor.execute("ALTER TABLE habitaciones ADD COLUMN ultima_camarera TEXT DEFAULT 'N/A';")
            cursor.execute("ALTER TABLE habitaciones ADD COLUMN ultima_limpieza TIMESTAMP;")
            cursor.execute("ALTER TABLE habitaciones ADD COLUMN fecha_sucia TIMESTAMP;")

        # 2. Tabla historial de limpieza
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historial_limpieza (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hab_codigo TEXT NOT NULL,
                camarera TEXT NOT NULL,
                turno TEXT NOT NULL,
                fecha_sucia TIMESTAMP,
                fecha_limpia TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duracion_minutos INTEGER DEFAULT 0,
                FOREIGN KEY (hab_codigo) REFERENCES habitaciones (codigo)
            );
        """)
        conn.commit()
    except Exception as e:
        conn.rollback()
        logging.error(f"Error inicializando tabla de limpieza: {e}")
    finally:
        conn.close()

inicializar_tabla_limpieza()


def registrar_liberacion_limpieza(hab_codigo: str, camarera: str, turno: str) -> bool:
    """
    Registra la limpieza calculando los minutos que estuvo sucia la habitación
    y actualiza la última camarera responsable en la habitación.
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    ahora = datetime.now()
    try:
        conn.execute("BEGIN TRANSACTION;")

        # 1. Obtener cuándo pasó a sucia
        cursor.execute("SELECT fecha_sucia FROM habitaciones WHERE codigo = ?;", (hab_codigo,))
        row = cursor.fetchone()
        fecha_sucia_str = row["fecha_sucia"] if row and row["fecha_sucia"] else None

        duracion_minutos = 0
        if fecha_sucia_str:
            try:
                f_sucia = datetime.strptime(fecha_sucia_str, "%Y-%m-%d %H:%M:%S")
                duracion_minutos = max(1, int((ahora - f_sucia).total_seconds() / 60))
            except Exception:
                duracion_minutos = 15

        # 2. Insertar en historial de limpieza
        cursor.execute("""
            INSERT INTO historial_limpieza (
                hab_codigo, camarera, turno, fecha_sucia, fecha_limpia, duracion_minutos
            ) VALUES (?, ?, ?, ?, ?, ?);
        """, (hab_codigo, camarera.strip().upper(), turno, fecha_sucia_str, ahora.strftime("%Y-%m-%d %H:%M:%S"), duracion_minutos))

        # 3. Actualizar habitación a Limpia con la camarera responsable
        cursor.execute("""
            UPDATE habitaciones 
            SET estado = 'Limpia', 
                ultima_camarera = ?, 
                ultima_limpieza = ?,
                fecha_sucia = NULL
            WHERE codigo = ?;
        """, (camarera.strip().upper(), ahora.strftime("%Y-%m-%d %H:%M:%S"), hab_codigo))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logging.error(f"Error registrando limpieza: {e}")
        return False
    finally:
        conn.close()


def obtener_historial_limpieza(fecha_inicio: str, fecha_fin: str) -> list:
    """Consulta el historial de limpiezas con tiempos de rotación."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, hab_codigo, camarera, turno, fecha_sucia, fecha_limpia, duracion_minutos
            FROM historial_limpieza
            WHERE DATE(fecha_limpia) BETWEEN ? AND ?
            ORDER BY fecha_limpia DESC;
        """, (fecha_inicio, fecha_fin))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

# =============================================================================
# ADMINISTRACIÓN SEGURA DE HABITACIONES Y TARIFAS
# =============================================================================

def actualizar_tarifas_habitacion(hab_id: int, codigo: str, precio_4h: float, precio_24h: float) -> bool:
    """Actualiza el código y las tarifas en USD de una habitación."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE habitaciones
            SET codigo = ?, precio_4h = ?, precio_24h = ?
            WHERE id = ?;
        """, (codigo.strip().upper(), precio_4h, precio_24h, hab_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        logging.error(f"Error actualizando habitación: {e}")
        return False
    finally:
        conn.close()


def eliminar_habitacion_segura(codigo: str) -> tuple[bool, str]:
    """
    Intenta eliminar una habitación. Si ya tiene historial de pagos o estancias,
    bloquea el borrado para proteger la contabilidad y el libro del SAIME.
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        # 1. Verificar si tiene historial en pagos o SAIME
        cursor.execute("SELECT COUNT(*) FROM pagos WHERE hab_codigo = ?;", (codigo,))
        if cursor.fetchone()[0] > 0:
            return False, "No se puede eliminar: Esta habitación tiene pagos históricos asociados. Debe conservarse para auditoría contable."

        cursor.execute("SELECT COUNT(*) FROM historial_estancias WHERE hab_codigo = ?;", (codigo,))
        if cursor.fetchone()[0] > 0:
            return False, "No se puede eliminar: Esta habitación tiene registros en el Libro SAIME. Debe conservarse por ley."

        # 2. Si es una habitación sin estrenar, permite borrarla
        cursor.execute("DELETE FROM habitaciones WHERE codigo = ?;", (codigo,))
        conn.commit()
        return True, "Habitación eliminada correctamente."
    except Exception as e:
        conn.rollback()
        return False, f"Error: {e}"
    finally:
        conn.close()
# =============================================================================
# MOTOR CONTABLE: RECUPERACIÓN DE DEUDA DE MOROSO Y DESBLOQUEO AUTOMÁTICO
# =============================================================================
def liquidar_deuda_moroso_y_rehabilitar(cedula: str, nombre: str, motivo_original: str, monto_usd: float, metodo: str, user: str, p2p_ref=None, p2p_ci=None, p2p_tel=None) -> bool:
    """
    Registra el ingreso de la deuda recuperada en la caja del turno activo,
    retira al ciudadano de la lista negra y genera la auditoría de seguridad.
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    tasa = obtener_tasa_bcv()
    ahora = datetime.now()
    turno = "MAÑANA" if 8 <= ahora.hour < 17 else "NOCHE"
    concepto = f"Recuperación Deuda: {motivo_original}"
    try:
        conn.execute("BEGIN TRANSACTION;")

        # 1. Registrar el ingreso extraordinario en la contabilidad de caja
        cursor.execute("""
            INSERT INTO cobro_danos_estancia (
                hab_codigo, cliente_nombre, cliente_ci, concepto_dano, monto_usd, monto_bs,
                metodo, p2p_referencia, p2p_ci, p2p_telefono, fecha, turno, recepcionista
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, ("RECUPERACIÓN_DEUDA", nombre, cedula, concepto, monto_usd, monto_usd * tasa, metodo, p2p_ref, p2p_ci, p2p_tel, ahora.strftime("%Y-%m-%d %H:%M:%S"), turno, user))

        # 2. Retirar automáticamente al ciudadano de la lista negra
        cursor.execute("DELETE FROM morosos WHERE cedula = ?;", (cedula.strip(),))

        conn.commit()

        # 3. Trazabilidad en Auditoría de Seguridad
        p2p_txt = f" [Ref P2P: {p2p_ref}]" if metodo == "PAGO MOVIL" else ""
        registrar_auditoria(
            user, "RECEPCION", "RECUPERACION_DEUDA",
            f"Deuda saldada por '{nombre}' (C.I: {cedula}). Monto recuperado: ${monto_usd:.2f} ({formatear_bs(monto_usd * tasa)}) [{metodo}{p2p_txt}]. Motivo previo: '{motivo_original}'. Ciudadano rehabilitado."
        )
        return True
    except Exception as e:
        conn.rollback()
        logging.error(f"Error al liquidar deuda de moroso: {e}")
        return False
    finally:
        conn.close()

def generar_respaldo_seguro(ruta_destino: str) -> bool:
    """
    Realiza un respaldo consistente en caliente usando el API nativo de SQLite.
    Garantiza compatibilidad absoluta con WAL Mode y entornos compilados (.exe).
    """
    try:
        # Abre conexión directa a la base de datos activa
        conn_origen = obtener_conexion()
        
        # Abre o crea la base de datos de destino elegida por el usuario
        conn_destino = sqlite3.connect(ruta_destino)
        
        # Vuelco nativo página por página (incluye cambios en WAL pendientes)
        with conn_destino:
            conn_origen.backup(conn_destino, pages=100)
            
        conn_destino.close()
        conn_origen.close()
        return True
    except Exception as e:
        logging.error(f"Falla al ejecutar backup nativo de SQLite: {e}")
        return False