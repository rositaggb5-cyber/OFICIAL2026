import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import google.generativeai as genai
from datetime import datetime, date
from PIL import Image
import io
import re
import zipfile
import os
import streamlit.components.v1 as components
import qrcode

# ==========================================
# 1. CONFIGURACIÓN Y CONEXIÓN
# ==========================================
try:
    API_KEY_GOOGLE = "AIzaSyAZZrX6EfJ8G7c9doA3cGuAi6LibdqrPrE"
    genai.configure(api_key=API_KEY_GOOGLE)
    model = genai.GenerativeModel('gemini-1.5-flash')
except: pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# ESTE ES EL NOMBRE FIJO - YA NO CREARÁ MÁS ARCHIVOS DISTINTOS
DB_PATH = os.path.join(BASE_DIR, 'sistema_oficialia_master.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. Correspondencia (Original + Campos nuevos si faltan)
    c.execute('''CREATE TABLE IF NOT EXISTS correspondencia 
                  (folio_dir TEXT PRIMARY KEY, cuenta TEXT, sicamdtr TEXT, folio_ext TEXT, 
                  dependencia TEXT, asunto TEXT, nombre_ubica TEXT, fecha_ingreso TEXT, 
                  departamento TEXT, entregado_a TEXT, recibe_investiga TEXT, status TEXT, 
                  seguimiento TEXT, ubicacion_fisica TEXT, quien_firma TEXT, capturista TEXT, foto BLOB)''')
    
    # Actualizaciones de estructura (Sin borrar datos)
    try: c.execute("ALTER TABLE correspondencia ADD COLUMN confirmado INTEGER DEFAULT 0")
    except: pass
    try: c.execute("ALTER TABLE correspondencia ADD COLUMN metodo_entrega TEXT")
    except: pass
    try: c.execute("ALTER TABLE correspondencia ADD COLUMN tipo_tramite TEXT")
    except: pass

    # 2. Usuarios
    c.execute("CREATE TABLE IF NOT EXISTS usuarios (user TEXT PRIMARY KEY, password TEXT, nombre TEXT, rol TEXT, depto TEXT, avatar TEXT, online TEXT)")
    
    # 3. Mensajes
    c.execute("CREATE TABLE IF NOT EXISTS mensajes (id INTEGER PRIMARY KEY AUTOINCREMENT, remitente TEXT, destinatario TEXT, texto TEXT, fecha TEXT, leido INTEGER DEFAULT 0)")
    try: c.execute("ALTER TABLE mensajes ADD COLUMN leido INTEGER DEFAULT 0")
    except: pass 

    # 4. Consejo (Recuperado)
    c.execute("CREATE TABLE IF NOT EXISTS consejo_asistencia (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre_asiste TEXT, institucion TEXT, tipo TEXT, carta_blob BLOB, fecha TEXT)")
    
    # 5. Citas Hernán
    c.execute("CREATE TABLE IF NOT EXISTS citas_hernan (id INTEGER PRIMARY KEY AUTOINCREMENT, solicitante TEXT, fecha TEXT, hora TEXT, asunto TEXT)")

    # 6. Buzón de Quejas
    c.execute("CREATE TABLE IF NOT EXISTS quejas (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT, fecha TEXT, mensaje TEXT)")

    # USUARIOS (Tu lista completa)
    users_list = [
        ("RODOLFO.GONZALEZ", "director2026", "RODOLFO GONZÁLEZ SÁNCHEZ", "Director", "DIRECCIÓN"),
        ("ROSA.GUTIERREZ", "admin2026", "ROSA GUADALUPE GUTIÉRREZ BOTELLO", "Administradora", "DIRECCIÓN"),
        ("ANGEL.MARTINEZ", "12345", "MARTINEZ TORRES ANGEL ISMAEL", "Jefe de Área", "TRANSMISIONES"),
        ("MARTHA.MORA", "12345", "MORA TORRES MARTHA PATRICIA", "Secretaria", "TRANSMISIONES"),
        ("LORENA.GUEVARA", "12345", "GUEVARA ORTEGA LORENA ELIZABETH", "Trabajador", "TRANSMISIONES"),
        ("JOSE.MEDINA", "12345", "MEDINA RAMOS JOSE OSCAR", "Trabajador", "TRANSMISIONES"),
        ("ESDRAS.ZUNIGA", "12345", "ZUÑIGA HERNANDEZ ESDRAS JOSUE", "Trabajador", "TRANSMISIONES"),
        ("MARTHA.TADEO", "12345", "TADEO GALINDO MARTHA OFELIA", "Trabajador", "TRANSMISIONES"),
        ("VICTOR.ALVAREZ", "12345", "ALVAREZ HERNANDEZ VICTOR FERNANDO", "Trabajador", "TRANSMISIONES"),
        ("MARTHA.JIMENEZ", "12345", "JIMENEZ LARIOS MARTHA ADRIANA", "Trabajador", "TRANSMISIONES"),
        ("MARIA.MONTANO", "12345", "MONTAÑO GONZALEZ MARIA CRISTINA", "Trabajador", "TRANSMISIONES"),
        ("DANIEL.LOPEZ", "12345", "LOPEZ TOLEDO DANIEL EMILIANO", "Trabajador", "TRANSMISIONES"),
        ("GREGORIO.AYALA", "12345", "AYALA MARTÍNEZ GREGORIO", "Trabajador", "TRANSMISIONES"),
        ("GERARDO.VILLARRUEL", "12345", "VILLARRUEL CASTELLANOS GERARDO", "Trabajador", "TRANSMISIONES"),
        ("CLAUDIA.GILDO", "12345", "JIMENEZ GILDO CLAUDIA LETICIA", "Trabajador", "TRANSMISIONES"),
        ("NAYELI.MARQUEZ", "12345", "MARQUEZ RENDON NAYELI GORETI", "Trabajador", "TRANSMISIONES"),
        ("ADRIANA.GUEVARA", "12345", "GUEVARA BECERRA ADRIANA GUADALUPE", "Trabajador", "TRANSMISIONES"),
        ("ALEJANDRO.VENEGAS", "12345", "VENEGAS HERRERA ALEJANDRO", "Trabajador", "TRANSMISIONES"),
        ("HILDA.MONTOYA", "12345", "MONTOYA OROPEZA HILDA PATRICIA", "Trabajador", "TRANSMISIONES"),
        ("DANIELA.ACOSTA", "12345", "ACOSTA RODRÍGUEZ DANIELA GPE.", "Trabajador", "TRANSMISIONES"),
        ("MARIA.QUINONEZ", "12345", "QUIÑONEZ BARBA MARIA DE LOURDES", "Trabajador", "TRANSMISIONES"),
        ("SILVIA.GARCIA", "12345", "GARCIA GONZÁLEZ SILVIA LORENA", "Trabajador", "TRANSMISIONES"),
        ("MARIA.HERNANDEZ", "12345", "HERNANDEZ LEONOR MARIA DE LOS ANGELES", "Trabajador", "TRANSMISIONES"),
        ("MARIA.VERA", "12345", "VERA SANCHEZ MARIA DOLORES", "Trabajador", "TRANSMISIONES"),
        ("KARLA.ALMEIDA", "12345", "ALMEIDA PÉREZ KARLA JANETTE", "Jefe de Área", "COORDINACIÓN"),
        ("LUZ.VALADEZ", "12345", "VALADEZ JIMENEZ LUZ ALEJANDRA", "Trabajador", "COORDINACIÓN"),
        ("ANDRES.ARANDA", "12345", "ARANDA MENDOZA ANDRES", "Jefe de Área", "COORDINACIÓN"),
        ("JESUS.GALINDO", "12345", "GALINDO ROSAS JESUS", "Trabajador", "COORDINACIÓN"),
        ("MARIA.ARREGUIN", "12345", "ARREGUIN HERNANDEZ MARÍA EUGENIA", "Trabajador", "COORDINACIÓN"),
        ("FRANCISCO.GALICIA", "12345", "GALICIA PADILLA FRANCISCO JAVIER", "Trabajador", "COORDINACIÓN"),
        ("AZHAR.GONZALEZ", "12345", "GONZALEZ BROSS AZHAR ETHEL", "Trabajador", "COORDINACIÓN"),
        ("RUBEN.GONZALEZ", "12345", "GONZALEZ VENEGAS RUBEN HERNAN", "Trabajador", "COORDINACIÓN"),
        ("MARIA.GUTIERRES", "12345", "GUTIERRES CHAVEZ MARÍA ALEJANDRA", "Trabajador", "COORDINACIÓN"),
        ("DAVID.LOPEZ", "12345", "LOPEZ GARRET DAVID HERNAN", "Trabajador", "COORDINACIÓN"),
        ("NORMA.MARIN", "12345", "MARIN MONTES DE OCA NORMA ANGELICA", "Trabajador", "COORDINACIÓN"),
        ("GRACIELA.NAVARRO", "12345", "NAVARRO MORENO GRACIELA", "Trabajador", "COORDINACIÓN"),
        ("MARIA.ROJO", "12345", "ROJO CASTAÑEDA MARIA MARTINA", "Trabajador", "COORDINACIÓN"),
        ("EDUARDO.BARAJAS", "12345", "BARAJAS ALONSO EDUARDO E.", "Trabajador", "COORDINACIÓN"),
        ("MARIO.CORONA", "12345", "CORONA PINDTER MARIO ISAAC", "Trabajador", "COORDINACIÓN"),
        ("RAFAEL.GARCIA", "12345", "GARCIA ROBLES RAFAEL", "Trabajador", "COORDINACIÓN"),
        ("NATALIA.VILLA", "12345", "VILLA HERNÁNDEZ NATALIA MONSERRAT", "Trabajador", "COORDINACIÓN"),
        ("JOSE.MUNOZ", "12345", "MUÑOZ DE LA PAZ JOSE IVAN", "Jefe de Área", "CERTIFICACIONES"),
        ("JANETTE.ALAMILLO", "12345", "ALAMILLO ARAMBUL JANETTE BERENICE", "Secretaria", "CERTIFICACIONES"),
        ("LAURA.VIVAR", "12345", "LAURA VIVAR", "Oficialia", "CERTIFICACIONES"),
        ("ALEJANDRO.MENDOZA", "12345", "MENDOZA BENAVIDES ALEJANDRO DANIEL", "Trabajador", "CERTIFICACIONES"),
        ("ALFONSO.CHAVEZ", "12345", "CHAVEZ PICHARDO ALFONSO", "Trabajador", "CERTIFICACIONES"),
        ("ANTONIO.GALLEGOS", "12345", "GALLEGOS ESPARZA ANTONIO", "Trabajador", "CERTIFICACIONES"),
        ("OMAR.SANTACRUZ", "12345", "SANTACRUZ QUEZADA OMAR ALEJANDRO", "Trabajador", "CERTIFICACIONES"),
        ("ZYANYA.CHAVEZ", "12345", "CHAVEZ GONZALEZ ZYANYA AURORA", "Trabajador", "CERTIFICACIONES"),
        ("CECILIA.REYNOSO", "12345", "REYNOSO SORIANO CECILIA GUADALUPE", "Trabajador", "CERTIFICACIONES"),
        ("ARACELI.MURILLO", "12345", "MURILLO ESCOBEDO ARACELI", "Trabajador", "CERTIFICACIONES"),
        ("LUCIA.VALENZUELA", "12345", "VALENZUELA RODRIGUEZ LUCIA JOSEFINA", "Trabajador", "CERTIFICACIONES"),
        ("MARCO.GALVAN", "12345", "GALVAN RAYGOZA MARCO ANTONIO", "Trabajador", "CERTIFICACIONES"),
        ("DAVID.TAPIA", "12345", "TAPIA GOMEZ DAVID", "Trabajador", "CERTIFICACIONES"),
        ("GABRIELA.GONZALEZ", "12345", "GONZALEZ RODRÍGUEZ GABRIELA", "Trabajador", "CERTIFICACIONES"),
        ("DAMARIS.OROZCO", "12345", "OROZCO RODRÍGUEZ DAMARIS LIZBETH", "Trabajador", "CERTIFICACIONES"),
        ("MARIA.RAMOS", "12345", "RAMOS OCAMPO MARIA GUADALUPE", "Trabajador", "CERTIFICACIONES"),
        ("HERNAN.OCHOA", "12345", "OCHOA BENITEZ HERNAN JOHE", "Jefe de Área", "VALUACIÓN"),
        ("GORETTY.ORTIZ", "12345", "ORTIZ RUIZ GORETTY", "Secretaria", "VALUACIÓN"),
        ("DANIEL.ARREOLA", "12345", "ARREOLA SANTAMARIA DANIEL ANDRES", "Trabajador", "VALUACIÓN"),
        ("SANTIAGO.AVALOS", "12345", "AVALOS VILLAFUERTE SANTIAGO WALDIR", "Trabajador", "VALUACIÓN"),
        ("VICTOR.BARAJAS", "12345", "BARAJAS HERNANDEZ VICTOR", "Trabajador", "VALUACIÓN"),
        ("FRANCISCO.BARRIOS", "12345", "BARRIOS DE LA TORRE FCO. JAVIER", "Trabajador", "VALUACIÓN"),
        ("ERIC.BRAMBILA", "12345", "BRAMBILA LOPEZ ERIC DE JESÚS", "Trabajador", "VALUACIÓN"),
        ("ZAIRA.PRECIADO", "12345", "PRECIADO LUNA ZAIRA NERUSIA", "Trabajador", "VALUACIÓN"),
        ("FRANCISCO.RAMIREZ", "12345", "RAMIREZ GUTIERREZ FCO. JAVIER", "Trabajador", "VALUACIÓN"),
        ("JOSE.RIVERA", "12345", "RIVERA PARRILLA JOSE ARNULFO", "Trabajador", "VALUACIÓN"),
        ("OSCAR.MONTES", "12345", "MONTES CASTELLANOS OSCAR", "Trabajador", "VALUACIÓN"),
        ("CLAUDIA.OROZCO", "12345", "OROZCO REYES CLAUDIA GABRIELA", "Jefe de Área", "CARTOGRAFÍA"),
        ("VICTORIA.SERRANO", "12345", "SERRANO GARCIA VICTORIA", "Secretaria", "CARTOGRAFÍA"),
        ("ANTONIO.MANCILLA", "12345", "MANCILLA RODRIGUEZ ANTONIO", "Trabajador", "CARTOGRAFÍA"),
        ("JOSE.RODRIGUEZ", "12345", "RODRIGUEZ HERNANDEZ JOSE LUIS", "Trabajador", "CARTOGRAFÍA"),
        ("ALFONSO.PENA", "12345", "DE LA PEÑA LOPEZ ALFONSO HAMID", "Trabajador", "CARTOGRAFÍA"),
        ("CARLOS.ACOSTA", "12345", "ACOSTA GARCIA CARLOS ALONSO", "Trabajador", "CARTOGRAFÍA"),
        ("HAYDE.MARTINEZ", "12345", "DE LA O MARTINEZ HAYDE PAULINA", "Trabajador", "CARTOGRAFÍA"),
        ("CALEB.GONZALEZ", "12345", "GONZALEZ ARIAS CALEB EMILIANO", "Trabajador", "CARTOGRAFÍA"),
        ("ADOLFO.HERNANDEZ", "12345", "HERNANDEZ OCHOA ADOLFO SALVADOR", "Trabajador", "CARTOGRAFÍA"),
        ("MARIBEL.IGAREDA", "12345", "IGAREDA FLORES MARIBEL", "Trabajador", "CARTOGRAFÍA"),
        ("NORMA.PEREZ", "12345", "PEREZ HERNANDEZ NORMA ALEJANDRA", "Trabajador", "CARTOGRAFÍA"),
        ("MONICA.REYES", "12345", "REYES MARTINEZ MONICA GUADALUPE", "Trabajador", "CARTOGRAFÍA"),
        ("SERGIO.TORRES", "12345", "TORRES AYALA SERGIO ARTURO", "Trabajador", "CARTOGRAFÍA"),
        ("HUGO.RODRIGUEZ", "12345", "RODRIGUEZ SANTIAGO HUGO", "Jefe de Área", "TRÁMITE Y REGISTRO"),
        ("MIRIAM.SANCHEZ", "12345", "SANCHEZ ORTIZ MIRIAM", "Secretaria", "TRÁMITE Y REGISTRO"),
        ("OSVALDO.CISNEROS", "12345", "OSVALDO CISNEROS CASILLAS", "Trabajador", "TRÁMITE Y REGISTRO"),
        ("AXEL.ESCAMILLA", "12345", "ESCAMILLA RAMIREZ AXEL EMMANUEL", "Trabajador", "TRÁMITE Y REGISTRO"),
        ("SARA.HERNANDEZ", "12345", "HERNANDEZ ONTIVEROS SARA", "Trabajador", "TRÁMITE Y REGISTRO"),
        ("NAYERY.PANDURO", "12345", "PANDURO GUZMAN NAYERY ADRIANA", "Trabajador", "TRÁMITE Y REGISTRO"),
        ("IRMA.VEGA", "12345", "VEGA NAVARRO IRMA DELIA", "Trabajador", "TRÁMITE Y REGISTRO"),
        ("CARLOS.ALCANTAR", "12345", "ALCANTAR RAMIREZ CARLOS", "Trabajador", "TRÁMITE Y REGISTRO"),
        ("MIRIAM.GUTIERREZ", "12345", "GUTIERREZ MONTERO MIRIAM AURELIA", "Trabajador", "TRÁMITE Y REGISTRO"),
        ("JOSE.MELENDREZ", "12345", "MELENDREZ HERNANDEZ JOSE SALVADOR", "Trabajador", "TRÁMITE Y REGISTRO"),
        ("ESPERANZA.ROBLEDO", "12345", "ROBLEDO BRIONES ESPERANZA", "Trabajador", "TRÁMITE Y REGISTRO"),
        ("JOSE.SANTIAGO", "12345", "SANTIAGO DIAZ JOSE MANUEL", "Trabajador", "TRÁMITE Y REGISTRO"),
        ("MIRNA.ZELAYA", "12345", "ZELAYA AVILA MIRNA JUDITH", "Trabajador", "TRÁMITE Y REGISTRO")
    ]
    
    for u, p, n, r, d in users_list:
        try:
            c.execute("INSERT OR IGNORE INTO usuarios (user, password, nombre, rol, depto, avatar, online) VALUES (?, ?, ?, ?, ?, '👤', 'OFFLINE')", (u, p, n, r, d))
        except: pass

    conn.commit(); conn.close()

init_db()
st.set_page_config(page_title="SIGC 2026", layout="wide")

# ==========================================
# 2. ESTILOS Y FUNCIONES
# ==========================================
st.markdown("""<style>
    .hoja-oficial { background-color: white !important; color: black !important; border: 1px solid #ccc; padding: 20px; font-family: 'Times New Roman'; margin-bottom: 20px; font-size: 14px; }
    .alerta-box { padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid #ff4b4b; background-color: rgba(255, 75, 75, 0.1); }
    .alerta-roja { background-color: #ffebee; border-left: 5px solid #d32f2f; padding: 10px; margin-bottom: 5px; color: #b71c1c; }
    .alerta-amarilla { background-color: #fffde7; border-left: 5px solid #fbc02d; padding: 10px; margin-bottom: 5px; color: #f57f17; }
    .confirm-box { background-color: #e6fffa; border: 1px solid #004d40; padding: 10px; border-radius: 5px; margin-bottom: 5px; }
    .stExpander { border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; background-color: rgba(240,240,240,0.3); }
    @media print {
        .stSidebar, header, footer, .stButton, .stForm { display: none !important; }
        .hoja-oficial { border: none; box-shadow: none; width: 100%; margin: 0; }
    }
</style>""", unsafe_allow_html=True)

def play_sound():
    components.html("""<audio autoplay><source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mp3"></audio>""", height=0)

def extract_number(text):
    nums = re.findall(r'\d+', str(text))
    return int(nums[0]) if nums else 0

def mostrar_tutorial(modulo):
    with st.expander(f"❓ Ayuda: {modulo}"):
        if modulo == "Salidas": st.info("📄 **Salidas:** Ahora puedes registrar todos los detalles del oficio.")
        elif modulo == "Maestro Salidas": st.info("📑 **Maestro:** Puedes Ver, Editar y Borrar salidas.")
        else: st.info("Sistema de Gestión Catastral.")

AREAS = ["DIRECCIÓN", "TRANSMISIONES", "COORDINACIÓN", "CERTIFICACIONES", "VALUACIÓN", "CARTOGRAFÍA", "TRÁMITE Y REGISTRO"]
ROLES = ["Administradora", "Director", "Oficialía", "Jefe de Área", "Secretaria", "Trabajador", "Consejero"]

if 'auth' not in st.session_state: st.session_state.auth = False
if 'last_msg_count' not in st.session_state: st.session_state.last_msg_count = 0
if 'form_defaults' not in st.session_state: st.session_state.form_defaults = {}

# ==========================================
# 3. NAVEGACIÓN
# ==========================================
menu = st.sidebar.radio("Navegación:", ["🔍 Consulta Pública", "📅 Citas Hernán", "🔐 Sistema Interno"])

# ------------------------------------------
# MÓDULO PÚBLICO: CONSULTA (Actualizado para ver REZAGO por Cuenta)
# ------------------------------------------
if menu == "🔍 Consulta Pública":
    st.title("🏛️ Consulta de Trámites")
    st.markdown("Ingrese su número de folio (o Cuenta si es Rezago) para ver el estado.")
    q = st.text_input("Número de Folio / Cuenta:", placeholder="Ej. 1234")
    if q:
        conn = get_db_connection()
        # Modificación para buscar también por Cuenta
        df = pd.read_sql_query("SELECT folio_dir, status, departamento, entregado_a, seguimiento, confirmado, metodo_entrega, tipo_tramite FROM correspondencia WHERE (folio_dir LIKE ? OR (cuenta LIKE ? AND tipo_tramite='REZAGO')) AND folio_dir NOT LIKE 'TES/DCAT/%'", conn, params=(f"%{q}%",f"%{q}%"))
        if not df.empty:
            for i, r in df.iterrows():
                with st.expander(f"📂 Resultado: {r['folio_dir']}", expanded=True):
                    encargado = r['entregado_a']
                    if r['confirmado'] == 0 and encargado: encargado += " (Por Confirmar Recepción)"
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**📍 Ubicación Actual:** {r['departamento']}")
                        st.write(f"**👤 Atendido por:** {encargado}")
                    with c2:
                        stat = r['status'].upper()
                        if "FALTA" in stat: st.error(f"ESTADO: {stat}")
                        elif "TERMINADO" in stat: st.success(f"ESTADO: {stat}")
                        else: st.info(f"ESTADO: {stat}")
                    st.write(f"**📝 Notas:** {r['seguimiento']}")
                    if r['metodo_entrega']: st.caption(f"Método de recepción: {r['metodo_entrega']}")
                    if r.get('tipo_tramite') == 'REZAGO': st.success("✅ Trámite Histórico (Rezago)")
        else: st.warning("No se encontró información.")
        conn.close()

# ------------------------------------------
# MÓDULO PÚBLICO: CITAS HERNÁN
# ------------------------------------------
elif menu == "📅 Citas Hernán":
    st.title("📅 Agenda de Citas: Hernán")
    st.info("🕗 **Mañanas:** 08:30 - 09:30  |  🕑 **Tardes:** 14:00 - 15:00")
    conn = get_db_connection()
    c_cal, c_form = st.columns([1, 2])
    with c_form:
        st.subheader("Agendar Nueva Cita")
        with st.form("form_citas"):
            col_a, col_b = st.columns(2)
            with col_a:
                nom_solicita = st.text_input("Nombre del Solicitante / Perito")
                fecha_sel = st.date_input("Fecha de la cita", min_value=date.today())
            with col_b:
                citas_dia = conn.execute("SELECT hora FROM citas_hernan WHERE fecha=?", (str(fecha_sel),)).fetchall()
                ocupadas = [c['hora'] for c in citas_dia]
                bloques = ["08:30", "08:45", "09:00", "09:15", "14:00", "14:15", "14:30", "14:45"]
                libres = [h for h in bloques if h not in ocupadas]
                if libres: hora_sel = st.selectbox("Horarios Disponibles", libres)
                else: hora_sel = st.selectbox("Horarios", ["SIN CUPO - ELIJA OTRA FECHA"])
                asunto_cita = st.text_input("Asunto breve")
            if st.form_submit_button("Confirmar Cita"):
                if hora_sel != "SIN CUPO - ELIJA OTRA FECHA" and nom_solicita and asunto_cita:
                    conn.execute("INSERT INTO citas_hernan (solicitante, fecha, hora, asunto) VALUES (?,?,?,?)", (nom_solicita, str(fecha_sel), hora_sel, asunto_cita))
                    conn.commit(); st.success(f"✅ Cita agendada: {fecha_sel} a las {hora_sel}"); st.rerun()
                else: st.error("Faltan datos o no hay cupo.")
    with c_cal:
        st.subheader("📆 Citas Próximas")
        df_c = pd.read_sql_query(f"SELECT fecha, hora, solicitante FROM citas_hernan WHERE fecha >= '{date.today()}' ORDER BY fecha, hora LIMIT 10", conn)
        if not df_c.empty: st.dataframe(df_c, use_container_width=True, hide_index=True)
        else: st.write("No hay citas próximas.")
    conn.close()

# ------------------------------------------
# MÓDULO PRIVADO: SISTEMA INTERNO
# ------------------------------------------
else:
    if not st.session_state.auth:
        st.title("🔐 Acceso Administrativo")
        c1, c2 = st.columns(2)
        with c1:
            u_input = st.text_input("Usuario").upper()
            p_input = st.text_input("Contraseña", type="password")
            if st.button("Iniciar Sesión"):
                conn = get_db_connection()
                user_data = conn.execute("SELECT * FROM usuarios WHERE user=? AND password=?", (u_input, p_input)).fetchone()
                if user_data:
                    st.session_state.auth = True; st.session_state.u_dat = list(user_data)
                    conn.execute("UPDATE usuarios SET online='ONLINE' WHERE user=?", (u_input,)); conn.commit(); st.rerun()
                else: st.error("Usuario o contraseña incorrectos.")
                conn.close()
        with c2:
            st.info("📱 **Acceso Móvil:** Escanea para abrir")
            # QR
            try:
                url_app = "https://super-fortnight-pj4v9xwvv6qxfrrj7-8501.app.github.dev/"
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(url_app)
                qr.make(fit=True)
                img = qr.make_image(fill='black', back_color='white')
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                st.image(img_byte_arr, width=200)
            except: st.warning("Instala qrcode[pil] en terminal")

    else:
        u_id, u_pw, u_nom, u_rol, u_depto, u_avatar, _ = st.session_state.u_dat
        conn = get_db_connection()
        try:
            msgs = conn.execute("SELECT COUNT(*) FROM mensajes WHERE destinatario=? AND leido=0", (u_nom,)).fetchone()[0]
            if msgs > st.session_state.last_msg_count: play_sound(); st.toast(f"🔔 Tienes {msgs} mensajes nuevos")
            st.session_state.last_msg_count = msgs
        except: pass
        
        st.sidebar.title(f"{u_avatar} {u_nom}"); st.sidebar.caption(f"{u_rol} | {u_depto}")
        if st.sidebar.button("Cerrar Sesión"):
            conn.execute("UPDATE usuarios SET online='OFFLINE' WHERE user=?", (u_id,)); conn.commit(); st.session_state.auth = False; st.rerun()

        opciones = ["📊 Dashboard", "🚨 Alertas Rápidas", "📥 Nuevo Folio (IA)", "📑 Registro Maestro"]
        
        # --- REGLA ESPECIAL HERNÁN ---
        if u_nom == "OCHOA BENITEZ HERNAN JOHE":
            opciones.insert(0, "📅 Citas Valuación")
        
        # --- NUEVO: REZAGO (Solo Transmisiones o Jefes) ---
        if u_depto == "TRANSMISIONES" or u_rol in ["Administradora", "Director"]:
            opciones.insert(2, "📚 Rezago Transmisiones")

        if u_rol in ["Administradora", "Director", "Oficialía", "Jefe de Área", "Secretaria", "Trabajador", "Operativo"]:
            opciones.extend(["📄 Oficios Salida", "📑 Maestro Salidas"])
        opciones.extend(["👥 Monitor de Personal", "✉️ Mensajería", "👤 Mi Perfil"])
        if u_rol in ["Administradora", "Oficialía", "Director"]: opciones.extend(["⚙️ Admin Usuarios", "🏛️ Consejo Técnico"])
        
        sel = st.sidebar.selectbox("Ir a:", opciones)

        # -----------------------------------------------------------
        # MODULO ALERTAS (NUEVO)
        # -----------------------------------------------------------
        if sel == "🚨 Alertas Rápidas":
            st.title("🚨 Centro de Alertas")
            conn = get_db_connection()
            # Alertas originales + Semáforo de tiempo
            st.subheader("Semáforo de Tiempos")
            df = pd.read_sql_query("SELECT folio_dir, asunto, fecha_ingreso, status FROM correspondencia WHERE status NOT LIKE '%TERMINADO%'", conn)
            if not df.empty:
                df['fecha_ingreso'] = pd.to_datetime(df['fecha_ingreso'], errors='coerce')
                now = pd.to_datetime(date.today())
                for i, r in df.iterrows():
                    dias = (now - r['fecha_ingreso']).days if pd.notnull(r['fecha_ingreso']) else 0
                    if dias > 20:
                         st.markdown(f"<div class='alerta-roja'>🔴 <b>{r['folio_dir']}</b> - {dias} días (URGENTE)</div>", unsafe_allow_html=True)
                    elif dias > 10:
                         st.markdown(f"<div class='alerta-amarilla'>🟡 <b>{r['folio_dir']}</b> - {dias} días (Atención)</div>", unsafe_allow_html=True)
                    
            st.subheader("Pendientes Generales")
            df2 = pd.read_sql_query("SELECT folio_dir, asunto, status FROM correspondencia WHERE status LIKE '%PENDIENTE%' OR status LIKE '%FALTAN DOCUMENTOS%'", conn)
            for i, r in df2.iterrows():
                ico = "🔴" if "FALTA" in r['status'] else "🟡"
                st.markdown(f"""<div class="alerta-box"><h4>{ico} {r['folio_dir']}</h4><p>{r['asunto']}</p></div>""", unsafe_allow_html=True)
            conn.close()

        # -----------------------------------------------------------
        # MODULO CONSEJO TÉCNICO (NUEVO)
        # -----------------------------------------------------------
        elif sel == "🏛️ Consejo Técnico":
            st.title("Consejo Técnico"); conn=get_db_connection()
            t1,t2=st.tabs(["Acta IA","Asistencia"])
            with t1:
                tem = st.text_input("Tema de la sesión")
                if st.button("Generar Acta") and tem: 
                    try: st.text_area("Borrador:", model.generate_content(f"Acta Consejo Catastral sobre {tem}").text, height=300)
                    except: st.error("Error API")
            with t2:
                with st.form("asist"):
                    nm=st.text_input("Nombre"); tp=st.selectbox("Tipo",["Titular","Suplente"]); fl=st.file_uploader("PDF")
                    if st.form_submit_button("Registrar"): conn.execute("INSERT INTO consejo_asistencia (nombre_asiste,tipo,carta_blob,fecha) VALUES (?,?,?,?)",(nm,tp,fl.getvalue() if fl else None,str(date.today()))); conn.commit(); st.success("Ok")
                if st.button("Descargar ZIP"):
                    b=io.BytesIO()
                    with zipfile.ZipFile(b,"w") as z:
                        for r in conn.execute("SELECT nombre_asiste, carta_blob FROM consejo_asistencia").fetchall():
                            if r['carta_blob']: z.writestr(f"{r['nombre_asiste']}.pdf", r['carta_blob'])
                    st.download_button("ZIP", b.getvalue(), "consejo.zip")
            conn.close()

        # -----------------------------------------------------------
        # MODULO REZAGO (NUEVO - CUENTA ES FOLIO)
        # -----------------------------------------------------------
        elif sel == "📚 Rezago Transmisiones":
            st.title("📚 Registro de Rezago")
            st.info("La CUENTA será el identificador.")
            with st.form("rez"):
                cta = st.text_input("Número de Cuenta")
                asu = st.text_input("Asunto")
                resp = st.selectbox("Asignar a:", [x['nombre'] for x in get_db_connection().execute("SELECT nombre FROM usuarios WHERE depto='TRANSMISIONES'").fetchall()])
                if st.form_submit_button("Registrar"):
                    conn = get_db_connection()
                    try:
                        # Guarda como REZAGO
                        conn.execute("INSERT INTO correspondencia (folio_dir, cuenta, asunto, departamento, entregado_a, status, fecha_ingreso, tipo_tramite) VALUES (?,?,?,?,?,?,?,?)",
                                     (f"REZ-{cta}", cta, asu, "TRANSMISIONES", resp, "EN PROCESO", str(date.today()), "REZAGO"))
                        conn.commit(); st.success(f"Guardado. Consultar con cuenta: {cta}")
                    except: st.error("Error al guardar")
                    conn.close()

        # 0. CITAS VALUACIÓN
        elif sel == "📅 Citas Valuación":
            st.title("📅 Citas Valuación (Vista Jefe)")
            st.subheader("Agenda de Valuaciones Asignadas")
            df_h = pd.read_sql_query("SELECT fecha, hora, solicitante, asunto FROM citas_hernan ORDER BY fecha, hora", conn)
            if not df_h.empty:
                st.dataframe(df_h, use_container_width=True, hide_index=True)
                st.success("Sincronizado con Base de Datos")
            else:
                st.warning("No tienes citas asignadas.")
            conn.close()

        # 1. DASHBOARD
        elif sel == "📊 Dashboard":
            st.title("📊 Tablero de Control")
            conn = get_db_connection()
            q_d = "SELECT status, entregado_a, departamento FROM correspondencia" if u_rol in ["Administradora", "Director", "Oficialía"] else f"SELECT status, entregado_a, departamento FROM correspondencia WHERE departamento='{u_depto}'"
            df = pd.read_sql_query(q_d, conn)
            if not df.empty:
                c1,c2,c3 = st.columns(3)
                with c1: st.plotly_chart(px.pie(df, names='status', title="Estatus General"), use_container_width=True)
                with c2: st.plotly_chart(px.bar(df['departamento'].value_counts().reset_index(), x='departamento', y='count', title="Por Área"), use_container_width=True)
                with c3: st.plotly_chart(px.bar(df['entregado_a'].value_counts().reset_index(), x='entregado_a', y='count', title="Por Persona"), use_container_width=True)
            else: st.info("Sin datos.")
            conn.close()

        # 3. NUEVO FOLIO
        elif sel == "📥 Nuevo Folio (IA)":
            st.title("📥 Registro de Entrada")
            if 'ia' not in st.session_state: st.session_state.ia = {"f":"","c":"","s":"","e":"","d":"","a":""}
            conn = get_db_connection(); users = [r['nombre'] for r in conn.execute("SELECT nombre FROM usuarios").fetchall()]
            exist = [r['folio_dir'] for r in conn.execute("SELECT folio_dir FROM correspondencia WHERE folio_dir NOT LIKE 'TES/DCAT/%'").fetchall()]
            nums = sorted([extract_number(f) for f in exist if extract_number(f)>0])
            sug = nums[-1] + 1 if nums else 1
            conn.close(); defs = st.session_state.form_defaults

            with st.form("in"):
                c1,c2 = st.columns(2)
                with c1:
                    f1=st.text_input("1. Folio", st.session_state.ia["f"], placeholder=f"Sugerido: {sug}")
                    f2=st.text_input("2. Cuenta", st.session_state.ia["c"]); f3=st.text_input("3. SICAM", st.session_state.ia["s"])
                    f4=st.text_input("4. Ext", st.session_state.ia["e"]); f5=st.text_input("5. Dependencia", st.session_state.ia["d"])
                    f6=st.text_area("6. Asunto", st.session_state.ia["a"]); f7=st.text_input("7. Ubicación", value=defs.get('ubi',''))
                    f8=st.text_input("8. Fecha", str(date.today()))
                    idx_m = ["Ventanilla","Correo","Otro"].index(defs.get('metodo','Ventanilla')) if defs.get('metodo') in ["Ventanilla","Correo","Otro"] else 0
                    f_met=st.selectbox("8.1 Método", ["Ventanilla","Correo","Otro"], index=idx_m)
                with c2:
                    idx_a = AREAS.index(defs.get('area',AREAS[0])) if defs.get('area') in AREAS else 0
                    f9=st.selectbox("9. Área", AREAS, index=idx_a)
                    idx_u = ([""]+users).index(defs.get('asig','')) if defs.get('asig') in ([""]+users) else 0
                    f10=st.selectbox("10. Asignado", [""]+users, index=idx_u)
                    f11=st.selectbox("11. Recibe", [""]+users); f12=st.selectbox("12. Estatus", ["PENDIENTE","EN PROCESO","TERMINADO","FALTAN DOCUMENTOS"])
                    f13=st.text_area("13. Seguimiento"); f14=st.text_input("14. Ub. Física", value=defs.get('fisica',''))
                    f15=st.text_input("15. Firma"); f16=st.text_input("16. Capturista", u_nom, disabled=True)
                save = st.form_submit_button("💾 GUARDAR")
            
            cam = st.camera_input("Foto Oficio")
            if cam and st.button("🤖 IA Auto-llenar"):
                try:
                    res = model.generate_content(["Formato F:x|C:x|S:x|E:x|D:x|A:x", Image.open(cam)]).text.split("|")
                    st.session_state.ia = {"f":res[0].split(":")[1],"c":res[1].split(":")[1],"s":res[2].split(":")[1],"e":res[3].split(":")[1],"d":res[4].split(":")[1],"a":res[5].split(":")[1]}
                    st.rerun()
                except: st.error("Error IA")
            
            if save:
                conn = get_db_connection()
                try:
                    conn.execute("INSERT INTO correspondencia VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?,?)", (f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13,f14,f15,f16,cam.getvalue() if cam else None, f_met, "NORMAL"))
                    conn.commit(); st.session_state.form_defaults={'area':f9,'asig':f10,'ubi':f7,'fisica':f14,'metodo':f_met}
                    st.session_state.ia={"f":"","c":"","s":"","e":"","d":"","a":""}; st.success("Guardado"); st.rerun()
                except Exception as e: st.error(f"Error: {e}")
                conn.close()

        # 4. MAESTRO ENTRADAS (CON BOTÓN DE RESPALDO)
        elif sel == "📑 Registro Maestro":
            st.title("📑 Maestro Correspondencia")
            conn = get_db_connection(); users = [r['nombre'] for r in conn.execute("SELECT nombre FROM usuarios").fetchall()]
            c1,c2,c3 = st.columns([2,2,1])
            fa = c1.selectbox("Área:", ["TODAS"]+AREAS); ft = c2.text_input("Buscar:"); 
            q = "SELECT * FROM correspondencia WHERE folio_dir NOT LIKE 'TES/DCAT/%'"
            if fa!="TODAS": q+=f" AND departamento='{fa}'"
            if ft: q+=f" AND (folio_dir LIKE '%{ft}%' OR asunto LIKE '%{ft}%')"
            df = pd.read_sql_query(q, conn)
            with c3:
                if st.button("🖨️ Imprimir"):
                    html = df.drop(columns=['foto'], errors='ignore').to_html(classes='hoja-oficial', index=False)
                    st.components.v1.html(f"{html}<script>window.print()</script>", height=600, scrolling=True)
            
            t1, t2, t3 = st.tabs(["👁️ Ver", "✏️ Editar/Borrar", "🔄 Turnar"])
            with t1: st.dataframe(df.drop(columns=['foto','confirmado'], errors='ignore'), use_container_width=True)
            with t2:
                s = st.selectbox("Editar:", [""]+df['folio_dir'].tolist())
                if s:
                    r = df[df['folio_dir']==s].iloc[0]
                    with st.form("ed"):
                        ok = u_rol in ["Administradora","Director","Oficialía"] or (u_rol in ["Jefe de Área","Secretaria"] and r['departamento']==u_depto) or (u_rol=="Operativo" and r['entregado_a']==u_nom)
                        c1,c2 = st.columns(2)
                        with c1:
                            e1=st.text_input("Folio", r['folio_dir'], disabled=True)
                            e2=st.text_input("Cuenta", r['cuenta'], disabled=not ok)
                            e3=st.text_input("SICAM", r['sicamdtr'], disabled=not ok)
                            e6=st.text_area("Asunto", r['asunto'], disabled=not ok)
                            im = ["Ventanilla","Correo","Otro"].index(r['metodo_entrega']) if r['metodo_entrega'] in ["Ventanilla","Correo","Otro"] else 0
                            em = st.selectbox("Método", ["Ventanilla","Correo","Otro"], index=im, disabled=not ok)
                        with c2:
                            ia = AREAS.index(r['departamento']) if r['departamento'] in AREAS else 0
                            e9=st.selectbox("Área", AREAS, index=ia, disabled=not ok)
                            iu = ([""]+users).index(r['entregado_a']) if r['entregado_a'] in users else 0
                            e10=st.selectbox("Asignado", [""]+users, index=iu, disabled=not ok)
                            ist = ["PENDIENTE","EN PROCESO","TERMINADO","FALTAN DOCUMENTOS"].index(r['status']) if r['status'] in ["PENDIENTE","EN PROCESO","TERMINADO","FALTAN DOCUMENTOS"] else 0
                            e12=st.selectbox("Estatus", ["PENDIENTE","EN PROCESO","TERMINADO","FALTAN DOCUMENTOS"], index=ist, disabled=not ok)
                            e13=st.text_area("Seguimiento", r['seguimiento'], disabled=not ok)
                        
                        cupd, cdel = st.columns(2)
                        if ok and cupd.form_submit_button("Actualizar"):
                            conn.execute("UPDATE correspondencia SET cuenta=?, sicamdtr=?, asunto=?, departamento=?, entregado_a=?, status=?, seguimiento=?, metodo_entrega=? WHERE folio_dir=?", (e2,e3,e6,e9,e10,e12,e13,em,s))
                            conn.commit(); st.success("Listo"); st.rerun()
                        if u_rol in ["Administradora","Oficialía"] and cdel.form_submit_button("❌ BORRAR"):
                            conn.execute("DELETE FROM correspondencia WHERE folio_dir=?",(s,)); conn.commit(); st.rerun()
            with t3:
                pf = st.selectbox("Padre:", [""]+df['folio_dir'].tolist())
                if pf and st.button("Generar Turno"):
                    p = df[df['folio_dir']==pf].iloc[0]; b = pf.split("-")[0]
                    cn = conn.execute(f"SELECT COUNT(*) FROM correspondencia WHERE folio_dir LIKE '{b}-%'").fetchone()[0]
                    abc="ABCDEFGHIJKLMNOPQRSTUVWXYZ"; nf = f"{b}-{abc[cn]}" if cn<26 else f"{b}-{cn}"
                    conn.execute("INSERT INTO correspondencia (folio_dir,cuenta,sicamdtr,folio_ext,dependencia,asunto,nombre_ubica,fecha_ingreso,departamento,entregado_a,status,capturista,confirmado,metodo_entrega,tipo_tramite) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (nf,p['cuenta'],p['sicamdtr'],p['folio_ext'],p['dependencia'],p['asunto'],p['nombre_ubica'],str(date.today()),p['departamento'],p['entregado_a'],"PENDIENTE",u_nom,0,p['metodo_entrega'],"TURNO"))
                    conn.commit(); st.success(f"Turno: {nf}"); st.rerun()
            
            # --- BOTÓN RESPALDO (SOLUCIÓN SEGURA) ---
            st.divider()
            with open(DB_PATH, "rb") as fp:
                st.download_button("💾 DESCARGAR COPIA DE SEGURIDAD (DB)", fp, "respaldo_seguro.db", "application/octet-stream")
            conn.close()

        # 5. OFICIOS SALIDA
        elif sel == "📄 Oficios Salida":
            mostrar_tutorial("Salidas")
            st.title("📄 Registro de Salidas")
            conn = get_db_connection(); users = [r['nombre'] for r in conn.execute("SELECT nombre FROM usuarios").fetchall()]
            try: cnt = conn.execute("SELECT COUNT(*) FROM correspondencia WHERE folio_dir LIKE 'TES/DCAT/%'").fetchone()[0] + 1
            except: cnt = 1
            nf = f"TES/DCAT/{cnt:03d}/2026"; st.info(f"Generando Folio: **{nf}**")
            
            with st.form("sal"):
                c1,c2 = st.columns(2)
                with c1:
                    s1=st.text_input("1. Folio Salida", value=nf)
                    s2=st.text_input("2. Cuenta"); s3=st.text_input("3. SICAMDTR")
                    s4=st.text_input("4. Ext"); s5=st.text_input("5. Destinatario (Dependencia/Persona)")
                    s6=st.text_area("6. Asunto"); s7=st.text_input("7. Ubicación (Destino)", value="")
                    s8=st.text_input("8. Fecha Salida", str(date.today()))
                with c2:
                    s9=st.selectbox("9. Área Emisora", AREAS)
                    s10=st.selectbox("10. Responsable (Quién elabora)", [""]+users)
                    s11=st.text_input("11. Recibe (Externo/Acuse)", "")
                    s12=st.selectbox("12. Estatus", ["ENVIADO", "ENTREGADO", "PENDIENTE", "CANCELADO"])
                    s13=st.text_area("13. Observaciones / Seguimiento")
                    s14=st.text_input("14. Ubicación Física Copia")
                    s15=st.text_input("15. Quién Firma")
                    s16=st.text_input("16. Capturista", u_nom, disabled=True)
                
                if st.form_submit_button("💾 REGISTRAR SALIDA"):
                    conn.execute("""INSERT INTO correspondencia 
                        (folio_dir, cuenta, sicamdtr, folio_ext, dependencia, asunto, nombre_ubica, fecha_ingreso, 
                         departamento, entregado_a, recibe_investiga, status, seguimiento, ubicacion_fisica, 
                         quien_firma, capturista, confirmado, metodo_entrega, tipo_tramite) 
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,'Interno','SALIDA')""", 
                        (s1,s2,s3,s4,s5,s6,s7,s8,s9,s10,s11,s12,s13,s14,s15,s16))
                    conn.commit(); st.success("Salida Registrada Completamente"); st.rerun()
            conn.close()

        # 6. MAESTRO SALIDAS
        elif sel == "📑 Maestro Salidas":
            mostrar_tutorial("Maestro Salidas")
            st.title("📑 Control de Salidas")
            conn = get_db_connection(); users = [r['nombre'] for r in conn.execute("SELECT nombre FROM usuarios").fetchall()]
            df = pd.read_sql_query("SELECT * FROM correspondencia WHERE folio_dir LIKE 'TES/DCAT/%'", conn)
            
            if st.button("🖨️ Imprimir Lista"):
                html = df.drop(columns=['foto'], errors='ignore').to_html(classes='hoja-oficial', index=False)
                st.components.v1.html(f"{html}<script>window.print()</script>", height=600, scrolling=True)
            
            t1, t2 = st.tabs(["👁️ Ver Tabla", "✏️ Editar / Borrar"])
            with t1: st.dataframe(df.drop(columns=['foto'], errors='ignore'), use_container_width=True)
            with t2:
                s = st.selectbox("Editar Salida:", [""]+df['folio_dir'].tolist())
                if s:
                    r = df[df['folio_dir']==s].iloc[0]
                    with st.form("ed_sal"):
                        ok = u_rol in ["Administradora","Director","Oficialía"] or r['capturista']==u_nom or r['entregado_a']==u_nom
                        c1,c2 = st.columns(2)
                        with c1:
                            e1=st.text_input("Folio", r['folio_dir'], disabled=True)
                            e2=st.text_input("Cuenta", r['cuenta'], disabled=not ok)
                            e3=st.text_input("SICAM", r['sicamdtr'], disabled=not ok)
                            e5=st.text_input("Destinatario", r['dependencia'], disabled=not ok)
                            e6=st.text_area("Asunto", r['asunto'], disabled=not ok)
                        with c2:
                            ia = AREAS.index(r['departamento']) if r['departamento'] in AREAS else 0
                            e9=st.selectbox("Área", AREAS, index=ia, disabled=not ok)
                            iu = ([""]+users).index(r['entregado_a']) if r['entregado_a'] in users else 0
                            e10=st.selectbox("Responsable", [""]+users, index=iu, disabled=not ok)
                            ist = ["ENVIADO", "ENTREGADO", "PENDIENTE", "CANCELADO"].index(r['status']) if r['status'] in ["ENVIADO", "ENTREGADO", "PENDIENTE", "CANCELADO"] else 0
                            e12=st.selectbox("Estatus", ["ENVIADO", "ENTREGADO", "PENDIENTE", "CANCELADO"], index=ist, disabled=not ok)
                            e13=st.text_area("Observaciones", r['seguimiento'], disabled=not ok)

                        cupd, cdel = st.columns(2)
                        if ok and cupd.form_submit_button("Actualizar Salida"):
                            conn.execute("UPDATE correspondencia SET cuenta=?, sicamdtr=?, dependencia=?, asunto=?, departamento=?, entregado_a=?, status=?, seguimiento=? WHERE folio_dir=?", (e2,e3,e5,e6,e9,e10,e12,e13,s))
                            conn.commit(); st.success("Actualizado"); st.rerun()
                        if u_rol in ["Administradora","Oficialía"] and cdel.form_submit_button("❌ BORRAR SALIDA"):
                            conn.execute("DELETE FROM correspondencia WHERE folio_dir=?",(s,)); conn.commit(); st.rerun()
            conn.close()

        # 7. MONITOR
        elif sel == "👥 Monitor de Personal":
            st.title("👥 Actividad")
            conn = get_db_connection(); df = pd.read_sql_query("SELECT nombre, depto, online FROM usuarios", conn)
            c1,c2=st.columns(2)
            with c1: st.success("🟢 ONLINE"); st.dataframe(df[df['online']=='ONLINE'], use_container_width=True)
            with c2: st.write("⚪ OFFLINE"); st.dataframe(df[df['online']!='ONLINE'], use_container_width=True)
            conn.close()

        # 8. MENSAJERÍA
        elif sel == "✉️ Mensajería":
            st.title("✉️ Chat"); conn = get_db_connection()
            conn.execute("UPDATE mensajes SET leido=1 WHERE destinatario=?",(u_nom,)); conn.commit()
            c1,c2=st.columns([1,2])
            with c1:
                to=st.selectbox("Para:", [r['nombre'] for r in conn.execute("SELECT nombre FROM usuarios").fetchall()])
                tx=st.text_area("Mensaje:")
                if st.button("Enviar"): conn.execute("INSERT INTO mensajes (remitente,destinatario,texto,fecha) VALUES (?,?,?,?)",(u_nom,to,tx,str(datetime.now()))); conn.commit(); st.success("Enviado"); st.rerun()
            with c2:
                st.dataframe(pd.read_sql_query(f"SELECT fecha, remitente, texto FROM mensajes WHERE destinatario='{u_nom}' OR remitente='{u_nom}' ORDER BY id DESC", conn), use_container_width=True)
            conn.close()

        # 9. PERFIL (CON BUZÓN)
        elif sel == "👤 Mi Perfil":
            st.title(f"Hola, {u_nom}"); conn = get_db_connection()
            pen = pd.read_sql_query("SELECT folio_dir, asunto FROM correspondencia WHERE entregado_a=? AND confirmado=0", conn, params=(u_nom,))
            if not pen.empty:
                st.error(f"Tienes {len(pen)} documentos por aceptar."); 
                for i,r in pen.iterrows():
                    if st.button(f"Aceptar {r['folio_dir']}"): conn.execute("UPDATE correspondencia SET confirmado=1 WHERE folio_dir=?",(r['folio_dir'],)); conn.commit(); st.rerun()
            else: st.success("Estás al día.")
            
            if st.button("Cambiar Clave"): conn.execute("UPDATE usuarios SET password=? WHERE user=?",(st.text_input("Nueva Clave",type="password"),u_id)); conn.commit(); st.success("Listo")

            # --- BUZÓN DE QUEJAS ---
            st.divider()
            st.subheader("📩 Buzón de Quejas y Sugerencias")
            with st.form("form_quejas", clear_on_submit=True):
                msg = st.text_area("Escriba su comentario aquí...")
                if st.form_submit_button("Enviar"):
                    if msg:
                        conn.execute("INSERT INTO quejas (usuario, fecha, mensaje) VALUES (?,?,?)", (u_nom, str(datetime.now()), msg))
                        conn.commit(); st.success("Queja enviada permanentemente al sistema.")

            # Mostrar quejas solo a directivos
            if u_rol in ["Director", "Administradora"]:
                st.divider()
                st.subheader("📋 Registro de Quejas (Vista Admin)")
                quejas_df = pd.read_sql_query("SELECT * FROM quejas", conn)
                st.table(quejas_df)

            conn.close()

        # 10. ADMIN USUARIOS
        elif sel == "⚙️ Admin Usuarios":
            st.title("Admin Usuarios"); conn=get_db_connection()
            t1,t2=st.tabs(["Crear","Editar"])
            with t1:
                with st.form("nu"):
                    u=st.text_input("User"); p=st.text_input("Pass"); n=st.text_input("Nombre"); r=st.selectbox("Rol", ROLES); d=st.selectbox("Depto", AREAS)
                    if st.form_submit_button("Crear"): 
                        try: conn.execute("INSERT INTO usuarios VALUES (?,?,?,?,?,?,?)",(u,p,n,r,d,"👤","OFF")); conn.commit(); st.success("Creado")
                        except: st.error("Ya existe")
            with t2:
                allu=pd.read_sql_query("SELECT * FROM usuarios", conn); st.dataframe(allu)
                us=st.selectbox("Usuario:", allu['user'].tolist())
                if us:
                    ud=allu[allu['user']==us].iloc[0]
                    nr=st.selectbox("Rol", ROLES, index=ROLES.index(ud['rol']) if ud['rol'] in ROLES else 0)
                    if st.button("Guardar"): conn.execute("UPDATE usuarios SET rol=? WHERE user=?",(nr,us)); conn.commit(); st.success("Listo"); st.rerun()
            conn.close()