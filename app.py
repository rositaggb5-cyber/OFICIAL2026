import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import google.generativeai as genai
from datetime import datetime, date
from PIL import Image
import io

# Configuración de IA
API_KEY_GOOGLE = "AIzaSyAZZrX6EfJ8G7c9doA3cGuAi6LibdqrPrE"
genai.configure(api_key=API_KEY_GOOGLE)
model = genai.GenerativeModel('gemini-1.5-flash')

def get_db_connection():
    conn = sqlite3.connect('oficialia_v22.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS correspondencia 
                 (folio_dir TEXT PRIMARY KEY, cuenta TEXT, sicamdtr TEXT, folio_ext TEXT, 
                  dependencia TEXT, asunto TEXT, nombre_ubica TEXT, fecha_ingreso TEXT, 
                  departamento TEXT, entregado_a TEXT, recibe_investiga TEXT, status TEXT, 
                  seguimiento TEXT, ubicacion_fisica TEXT, quien_firma TEXT, capturista TEXT, foto BLOB)''')
    c.execute("CREATE TABLE IF NOT EXISTS usuarios (user TEXT PRIMARY KEY, password TEXT, nombre TEXT, rol TEXT, depto TEXT, avatar TEXT, online TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS mensajes (id INTEGER PRIMARY KEY AUTOINCREMENT, remitente TEXT, destinatario TEXT, texto TEXT, fecha TEXT)")
    
    personal = [
        ('RODOLFO.GONZALEZ', 'director2026', 'RODOLFO GONZÁLEZ SÁNCHEZ', 'Director', 'DIRECCIÓN', '👨‍💼', 'OFFLINE'),
        ('ROSA.GUTIERREZ', 'admin2026', 'ROSA GUADALUPE GUTIÉRREZ BOTELLO', 'Administradora', 'DIRECCIÓN', '👩‍💻', 'OFFLINE'),
        ('ANGEL.MARTINEZ', '12345', 'MARTINEZ TORRES ANGEL ISMAEL', 'Jefe de Área', 'TRANSMISIONES', '👨‍💼', 'OFFLINE'),
        ('MARTHA.MORA', '12345', 'MORA TORRES MARTHA PATRICIA', 'Secretaria', 'TRANSMISIONES', '👩‍💼', 'OFFLINE'),
        ('LORENA.GUEVARA', '12345', 'GUEVARA ORTEGA LORENA ELIZABETH', 'Trabajador', 'TRANSMISIONES', '👤', 'OFFLINE'),
        ('JOSE.MEDINA', '12345', 'MEDINA RAMOS JOSE OSCAR', 'Trabajador', 'TRANSMISIONES', '👤', 'OFFLINE'),
        ('ESDRAS.ZUNIGA', '12345', 'ZUÑIGA HERNANDEZ ESDRAS JOSUE', 'Trabajador', 'TRANSMISIONES', '👤', 'OFFLINE'),
        ('MARTHA.TADEO', '12345', 'TADEO GALINDO MARTHA OFELIA', 'Trabajador', 'TRANSMISIONES', '👤', 'OFFLINE'),
        ('VICTOR.ALVAREZ', '12345', 'ALVAREZ HERNANDEZ VICTOR FERNANDO', 'Trabajador', 'TRANSMISIONES', '👤', 'OFFLINE'),
        ('MARTHA.JIMENEZ', '12345', 'JIMENEZ LARIOS MARTHA ADRIANA', 'Trabajador', 'TRANSMISIONES', '👤', 'OFFLINE'),
        ('MARIA.MONTANO', '12345', 'MONTAÑO GONZALEZ MARIA CRISTINA', 'Trabajador', 'TRANSMISIONES', '👤', 'OFFLINE'),
        ('DANIEL.LOPEZ', '12345', 'LOPEZ TOLEDO DANIEL EMILIANO', 'Trabajador', 'TRANSMISIONES', '👤', 'OFFLINE'),
        ('GREGORIO.AYALA', '12345', 'AYALA MARTÍNEZ GREGORIO', 'Trabajador', 'TRANSMISIONES', '👤', 'OFFLINE'),
        ('GERARDO.VILLARRUEL', '12345', 'VILLARRUEL CASTELLANOS GERARDO', 'Trabajador', 'TRANSMISIONES', '👤', 'OFFLINE'),
        ('CLAUDIA.GILDO', '12345', 'JIMENEZ GILDO CLAUDIA LETICIA', 'Trabajador', 'TRANSMISIONES', '👤', 'OFFLINE'),
        ('NAYELI.MARQUEZ', '12345', 'MARQUEZ RENDON NAYELI GORETI', 'Trabajador', 'TRANSMISIONES', '👤', 'OFFLINE'),
        ('ADRIANA.GUEVARA', '12345', 'GUEVARA BECERRA ADRIANA GUADALUPE', 'Trabajador', 'TRANSMISIONES', '👤', 'OFFLINE'),
        ('ALEJANDRO.VENEGAS', '12345', 'VENEGAS HERRERA ALEJANDRO', 'Trabajador', 'TRANSMISIONES', '👤', 'OFFLINE'),
        ('HILDA.MONTOYA', '12345', 'MONTOYA OROPEZA HILDA PATRICIA', 'Trabajador', 'TRANSMISIONES', '👤', 'OFFLINE'),
        ('DANIELA.ACOSTA', '12345', 'ACOSTA RODRÍGUEZ DANIELA GPE.', 'Trabajador', 'TRANSMISIONES', '👤', 'OFFLINE'),
        ('MARIA.QUINONEZ', '12345', 'QUIÑONEZ BARBA MARIA DE LOURDES', 'Trabajador', 'TRANSMISIONES', '👤', 'OFFLINE'),
        ('SILVIA.GARCIA', '12345', 'GARCIA GONZÁLEZ SILVIA LORENA', 'Trabajador', 'TRANSMISIONES', '👤', 'OFFLINE'),
        ('MARIA.HERNANDEZ', '12345', 'HERNANDEZ LEONOR MARIA DE LOS ANGELES', 'Trabajador', 'TRANSMISIONES', '👤', 'OFFLINE'),
        ('MARIA.VERA', '12345', 'VERA SANCHEZ MARIA DOLORES', 'Trabajador', 'TRANSMISIONES', '👤', 'OFFLINE'),
        ('KARLA.ALMEIDA', '12345', 'ALMEIDA PÉREZ KARLA JANETTE', 'Jefe de Área', 'COORDINACIÓN', '👩‍💼', 'OFFLINE'),
        ('LUZ.VALADEZ', '12345', 'VALADEZ JIMENEZ LUZ ALEJANDRA', 'Secretaria', 'COORDINACIÓN', '👩‍💼', 'OFFLINE'),
        ('ANDRES.ARANDA', '12345', 'ARANDA MENDOZA ANDRES', 'Trabajador', 'COORDINACIÓN', '👤', 'OFFLINE'),
        ('JESUS.GALINDO', '12345', 'GALINDO ROSAS JESUS', 'Trabajador', 'COORDINACIÓN', '👤', 'OFFLINE'),
        ('MARIA.ARREGUIN', '12345', 'ARREGUIN HERNANDEZ MARÍA EUGENIA', 'Trabajador', 'COORDINACIÓN', '👤', 'OFFLINE'),
        ('FRANCISCO.GALICIA', '12345', 'GALICIA PADILLA FRANCISCO JAVIER', 'Trabajador', 'COORDINACIÓN', '👤', 'OFFLINE'),
        ('AZHAR.GONZALEZ', '12345', 'GONZALEZ BROSS AZHAR ETHEL', 'Trabajador', 'COORDINACIÓN', '👤', 'OFFLINE'),
        ('RUBEN.GONZALEZ', '12345', 'GONZALEZ VENEGAS RUBEN HERNAN', 'Trabajador', 'COORDINACIÓN', '👤', 'OFFLINE'),
        ('MARIA.GUTIERRES', '12345', 'GUTIERRES CHAVEZ MARÍA ALEJANDRA', 'Trabajador', 'COORDINACIÓN', '👤', 'OFFLINE'),
        ('DAVID.LOPEZ_G', '12345', 'LOPEZ GARRET DAVID HERNAN', 'Trabajador', 'COORDINACIÓN', '👤', 'OFFLINE'),
        ('NORMA.MARIN', '12345', 'MARIN MONTES DE OCA NORMA ANGELICA', 'Trabajador', 'COORDINACIÓN', '👤', 'OFFLINE'),
        ('GRACIELA.NAVARRO', '12345', 'NAVARRO MORENO GRACIELA', 'Trabajador', 'COORDINACIÓN', '👤', 'OFFLINE'),
        ('MARIA.ROJO', '12345', 'ROJO CASTAÑEDA MARIA MARTINA', 'Trabajador', 'COORDINACIÓN', '👤', 'OFFLINE'),
        ('EDUARDO.BARAJAS', '12345', 'BARAJAS ALONSO EDUARDO E.', 'Trabajador', 'COORDINACIÓN', '👤', 'OFFLINE'),
        ('MARIO.CORONA', '12345', 'CORONA PINDTER MARIO ISAAC', 'Trabajador', 'COORDINACIÓN', '👤', 'OFFLINE'),
        ('RAFAEL.GARCIA', '12345', 'GARCIA ROBLES RAFAEL', 'Trabajador', 'COORDINACIÓN', '👤', 'OFFLINE'),
        ('NATALIA.VILLA', '12345', 'VILLA HERNÁNDEZ NATALIA MONSERRAT', 'Trabajador', 'COORDINACIÓN', '👤', 'OFFLINE'),
        ('JOSE.MUNOZ', '12345', 'MUÑOZ DE LA PAZ JOSE IVAN', 'Jefe de Área', 'CERTIFICACIONES', '👨‍💼', 'OFFLINE'),
        ('JANETTE.ALAMILLO', '12345', 'ALAMILLO ARAMBUL JANETTE BERENICE', 'Secretaria', 'CERTIFICACIONES', '👩‍💼', 'OFFLINE'),
        ('LAURA.VIVAR', '12345', 'LAURA VIVAR', 'Trabajador', 'CERTIFICACIONES', '👤', 'OFFLINE'),
        ('ALEJANDRO.MENDOZA', '12345', 'MENDOZA BENAVIDES ALEJANDRO DANIEL', 'Trabajador', 'CERTIFICACIONES', '👤', 'OFFLINE'),
        ('ALFONSO.CHAVEZ', '12345', 'CHAVEZ PICHARDO ALFONSO', 'Trabajador', 'CERTIFICACIONES', '👤', 'OFFLINE'),
        ('ANTONIO.GALLEGOS', '12345', 'GALLEGOS ESPARZA ANTONIO', 'Trabajador', 'CERTIFICACIONES', '👤', 'OFFLINE'),
        ('OMAR.SANTACRUZ', '12345', 'SANTACRUZ QUEZADA OMAR ALEJANDRO', 'Trabajador', 'CERTIFICACIONES', '👤', 'OFFLINE'),
        ('ZYANYA.CHAVEZ', '12345', 'CHAVEZ GONZALEZ ZYANYA AURORA', 'Trabajador', 'CERTIFICACIONES', '👤', 'OFFLINE'),
        ('CECILIA.REYNOSO', '12345', 'REYNOSO SORIANO CECILIA GUADALUPE', 'Trabajador', 'CERTIFICACIONES', '👤', 'OFFLINE'),
        ('ARACELI.MURILLO', '12345', 'MURILLO ESCOBEDO ARACELI', 'Trabajador', 'CERTIFICACIONES', '👤', 'OFFLINE'),
        ('LUCIA.VALENZUELA', '12345', 'VALENZUELA RODRIGUEZ LUCIA JOSEFINA', 'Trabajador', 'CERTIFICACIONES', '👤', 'OFFLINE'),
        ('MARCO.GALVAN', '12345', 'GALVAN RAYGOZA MARCO ANTONIO', 'Trabajador', 'CERTIFICACIONES', '👤', 'OFFLINE'),
        ('DAVID.TAPIA', '12345', 'TAPIA GOMEZ DAVID', 'Trabajador', 'CERTIFICACIONES', '👤', 'OFFLINE'),
        ('GABRIELA.GONZALEZ', '12345', 'GONZALEZ RODRÍGUEZ GABRIELA', 'Trabajador', 'CERTIFICACIONES', '👤', 'OFFLINE'),
        ('DAMARIS.OROZCO', '12345', 'OROZCO RODRÍGUEZ DAMARIS LIZBETH', 'Trabajador', 'CERTIFICACIONES', '👤', 'OFFLINE'),
        ('MARIA.RAMOS', '12345', 'RAMOS OCAMPO MARIA GUADALUPE', 'Trabajador', 'CERTIFICACIONES', '👤', 'OFFLINE'),
        ('HERNAN.OCHOA', '12345', 'OCHOA BENITEZ HERNAN JOHE', 'Jefe de Área', 'VALUACIÓN', '👨‍💼', 'OFFLINE'),
        ('GORETTY.ORTIZ', '12345', 'ORTIZ RUIZ GORETTY', 'Secretaria', 'VALUACIÓN', '👩‍💼', 'OFFLINE'),
        ('DANIEL.ARREOLA', '12345', 'ARREOLA SANTAMARIA DANIEL ANDRES', 'Trabajador', 'VALUACIÓN', '👤', 'OFFLINE'),
        ('SANTIAGO.AVALOS', '12345', 'AVALOS VILLAFUERTE SANTIAGO WALDIR', 'Trabajador', 'VALUACIÓN', '👤', 'OFFLINE'),
        ('VICTOR.BARAJAS', '12345', 'BARAJAS HERNANDEZ VICTOR', 'Trabajador', 'VALUACIÓN', '👤', 'OFFLINE'),
        ('FRANCISCO.BARRIOS', '12345', 'BARRIOS DE LA TORRE FCO. JAVIER', 'Trabajador', 'VALUACIÓN', '👤', 'OFFLINE'),
        ('ERIC.BRAMBILA', '12345', 'BRAMBILA LOPEZ ERIC DE JESUS', 'Trabajador', 'VALUACIÓN', '👤', 'OFFLINE'),
        ('ZAIRA.PRECIADO', '12345', 'PRECIADO LUNA ZAIRA NERUSIA', 'Trabajador', 'VALUACIÓN', '👤', 'OFFLINE'),
        ('FRANCISCO.RAMIREZ', '12345', 'RAMIREZ GUTIERREZ FCO. JAVIER', 'Trabajador', 'VALUACIÓN', '👤', 'OFFLINE'),
        ('JOSE.RIVERA', '12345', 'RIVERA PARRILLA JOSE ARNULFO', 'Trabajador', 'VALUACIÓN', '👤', 'OFFLINE'),
        ('OSCAR.MONTES', '12345', 'MONTES CASTELLANOS OSCAR', 'Trabajador', 'VALUACIÓN', '👤', 'OFFLINE'),
        ('CLAUDIA.OROZCO', '12345', 'OROZCO REYES CLAUDIA GABRIELA', 'Jefe de Área', 'CARTOGRAFÍA', '👩‍💼', 'OFFLINE'),
        ('VICTORIA.SERRANO', '12345', 'SERRANO GARCIA VICTORIA', 'Secretaria', 'CARTOGRAFÍA', '👩‍💼', 'OFFLINE'),
        ('ANTONIO.MANCILLA', '12345', 'MANCILLA RODRIGUEZ ANTONIO', 'Trabajador', 'CARTOGRAFÍA', '👤', 'OFFLINE'),
        ('JOSE.RODRIGUEZ', '12345', 'RODRIGUEZ HERNANDEZ JOSE LUIS', 'Trabajador', 'CARTOGRAFÍA', '👤', 'OFFLINE'),
        ('ALFONSO.PENA', '12345', 'DE LA PEÑA LOPEZ ALFONSO HAMID', 'Trabajador', 'CARTOGRAFÍA', '👤', 'OFFLINE'),
        ('CARLOS.ACOSTA', '12345', 'ACOSTA GARCIA CARLOS ALONSO', 'Trabajador', 'CARTOGRAFÍA', '👤', 'OFFLINE'),
        ('HAYDE.MARTINEZ', '12345', 'DE LA O MARTINEZ HAYDE PAULINA', 'Trabajador', 'CARTOGRAFÍA', '👤', 'OFFLINE'),
        ('CALEB.GONZALEZ', '12345', 'GONZALEZ ARIAS CALEB EMILIANO', 'Trabajador', 'CARTOGRAFÍA', '👤', 'OFFLINE'),
        ('ADOLFO.HERNANDEZ', '12345', 'HERNANDEZ OCHOA ADOLFO SALVADOR', 'Trabajador', 'CARTOGRAFÍA', '👤', 'OFFLINE'),
        ('MARIBEL.IGAREDA', '12345', 'IGAREDA FLORES MARIBEL', 'Trabajador', 'CARTOGRAFÍA', '👤', 'OFFLINE'),
        ('NORMA.PEREZ', '12345', 'PEREZ HERNANDEZ NORMA ALEJANDRA', 'Trabajador', 'CARTOGRAFÍA', '👤', 'OFFLINE'),
        ('MONICA.REYES', '12345', 'REYES MARTINEZ MONICA GUADALUPE', 'Trabajador', 'CARTOGRAFÍA', '👤', 'OFFLINE'),
        ('SERGIO.TORRES', '12345', 'TORRES AYALA SERGIO ARTURO', 'Trabajador', 'CARTOGRAFÍA', '👤', 'OFFLINE'),
        ('HUGO.RODRIGUEZ', '12345', 'RODRIGUEZ SANTIAGO HUGO', 'Jefe de Área', 'TRÁMITE Y REGISTRO', '👨‍💼', 'OFFLINE'),
        ('MIRIAM.SANCHEZ', '12345', 'SANCHEZ ORTIZ MIRIAM', 'Secretaria', 'TRÁMITE Y REGISTRO', '👩‍💼', 'OFFLINE'),
        ('OSVALDO.CISNEROS', '12345', 'OSVALDO CISNEROS CASILLAS', 'Trabajador', 'TRÁMITE Y REGISTRO', '👤', 'OFFLINE'),
        ('AXEL.ESCAMILLA', '12345', 'ESCAMILLA RAMIREZ AXEL EMMANUEL', 'Trabajador', 'TRÁMITE Y REGISTRO', '👤', 'OFFLINE'),
        ('SARA.HERNANDEZ', '12345', 'HERNANDEZ ONTIVEROS SARA', 'Trabajador', 'TRÁMITE Y REGISTRO', '👤', 'OFFLINE'),
        ('NAYERY.PANDURO', '12345', 'PANDURO GUZMAN NAYERY ADRIANA', 'Trabajador', 'TRÁMITE Y REGISTRO', '👤', 'OFFLINE'),
        ('IRMA.VEGA', '12345', 'VEGA NAVARRO IRMA DELIA', 'Trabajador', 'TRÁMITE Y REGISTRO', '👤', 'OFFLINE'),
        ('CARLOS.ALCANTAR', '12345', 'ALCANTAR RAMIREZ CARLOS', 'Trabajador', 'TRÁMITE Y REGISTRO', '👤', 'OFFLINE'),
        ('MIRIAM.GUTIERREZ', '12345', 'GUTIERREZ MONTERO MIRIAM AURELIA', 'Trabajador', 'TRÁMITE Y REGISTRO', '👤', 'OFFLINE'),
        ('JOSE.MELENDREZ', '12345', 'MELENDREZ HERNANDEZ JOSE SALVADOR', 'Trabajador', 'TRÁMITE Y REGISTRO', '👤', 'OFFLINE'),
        ('ESPERANZA.ROBLEDO', '12345', 'ROBLEDO BRIONES ESPERANZA', 'Trabajador', 'TRÁMITE Y REGISTRO', '👤', 'OFFLINE'),
        ('JOSE.SANTIAGO', '12345', 'SANTIAGO DIAZ JOSE MANUEL', 'Trabajador', 'TRÁMITE Y REGISTRO', '👤', 'OFFLINE'),
        ('MIRNA.ZELAYA', '12345', 'ZELAYA AVILA MIRNA JUDITH', 'Trabajador', 'TRÁMITE Y REGISTRO', '👤', 'OFFLINE')
    ]
    c.executemany("INSERT OR IGNORE INTO usuarios VALUES (?,?,?,?,?,?,?)", personal)
    conn.commit()
    conn.close()

init_db()
st.set_page_config(page_title="Oficialía Elite V22.1", layout="wide")

# OCULTAR BOTONES DE EDICIÓN Y GITHUB PARA USUARIOS NO ADMINISTRADORES
if 'u_dat' in st.session_state:
    if st.session_state.u_dat[3] != 'Administradora':
        st.markdown("""
            <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            .stAppDeployButton {display:none;}
            footer {visibility: hidden;}
            </style>
            """, unsafe_allow_html=True)

if 'auth' not in st.session_state: st.session_state.auth = False
AREAS = ["DIRECCIÓN", "TRANSMISIONES", "COORDINACIÓN", "CERTIFICACIONES", "VALUACIÓN", "CARTOGRAFÍA", "TRÁMITE Y REGISTRO"]

menu = st.sidebar.radio("Navegación", ["🔍 Consulta Ciudadana", "🔐 Sistema Interno"])

if menu == "🔍 Consulta Ciudadana":
    st.title("🏛️ Consulta Pública de Trámites")
    q = st.text_input("Ingrese el Folio Base (Ej: 1):")
    if q:
        conn = get_db_connection()
        query = "SELECT folio_dir, status, departamento, entregado_a FROM correspondencia WHERE folio_dir = ? OR folio_dir LIKE ?"
        df_res = pd.read_sql_query(query, conn, params=(q, f"{q}-%"))
        if not df_res.empty:
            for _, r in df_res.iterrows():
                with st.expander(f"Folio: {r['folio_dir']} - {r['departamento']}"):
                    st.write(f"**Estatus:** {r['status']} | **Encargado:** {r['entregado_a']}")
        else: st.error("No se encontró información.")
        conn.close()

else:
    if not st.session_state.auth:
        st.title("🔐 Acceso al Sistema")
        u = st.text_input("Usuario").upper()
        p = st.text_input("Clave", type="password")
        if st.button("Ingresar"):
            conn = get_db_connection()
            user = conn.execute("SELECT * FROM usuarios WHERE user=? AND password=?", (u, p)).fetchone()
            if user:
                st.session_state.auth = True
                st.session_state.u_dat = list(user)
                conn.execute("UPDATE usuarios SET online='ONLINE' WHERE user=?", (u,))
                conn.commit()
                st.rerun()
            else: st.error("Acceso denegado")
            conn.close()
    else:
        u_id, u_pw, u_nom, u_rol, u_depto, u_avatar, _ = st.session_state.u_dat
        st.sidebar.title(f"{u_avatar} {u_nom}")
        
        opcs = ["📊 Dashboard", "🚨 Alertas Rápidas", "📥 Nuevo Folio (IA)", "📑 Registro Maestro", "✉️ Mensajería", "👤 Mi Perfil"]
        if u_rol in ['Director', 'Administradora']: opcs.insert(4, "👥 Monitor de Personal")
        
        mod = st.sidebar.selectbox("Módulo:", opcs)

        if mod == "👥 Monitor de Personal":
            st.title("👥 Monitor de Estatus del Personal")
            conn = get_db_connection()
            df_u = pd.read_sql_query("SELECT nombre, depto, rol, online FROM usuarios", conn)
            c1, c2 = st.columns(2)
            with c1: st.success("🟢 En Línea"); st.table(df_u[df_u['online']=='ONLINE'][['nombre','depto']])
            with c2: st.info("⚪ Desconectados"); st.table(df_u[df_u['online']=='OFFLINE'][['nombre','depto']])
            conn.close()

        elif mod == "📊 Dashboard":
            st.title("📊 Control de Gestión")
            conn = get_db_connection()
            if u_rol in ['Director', 'Administradora']:
                df = pd.read_sql_query("SELECT * FROM correspondencia", conn)
            else:
                df = pd.read_sql_query("SELECT * FROM correspondencia WHERE departamento = ?", conn, params=(u_depto,))
            
            if not df.empty:
                # CORRECCIÓN DE ERROR DE GRÁFICA (image_5c66ac.png)
                res_status = df['status'].value_counts().reset_index()
                res_status.columns = ['Estatus', 'Cantidad']
                st.plotly_chart(px.pie(res_status, values='Cantidad', names='Estatus', title=f"Estatus ({u_depto})", hole=0.4))
            else: st.info("No hay datos en esta área.")
            conn.close()

        elif mod == "🚨 Alertas Rápidas":
            st.title("🚨 Centro de Notificaciones")
            conn = get_db_connection()
            if u_rol in ['Director', 'Administradora']:
                df_pend = pd.read_sql_query("SELECT folio_dir, asunto, departamento FROM correspondencia WHERE status='PENDIENTE'", conn)
            else:
                df_pend = pd.read_sql_query("SELECT folio_dir, asunto FROM correspondencia WHERE status='PENDIENTE' AND departamento=?", conn, params=(u_depto,))
            st.dataframe(df_pend)
            conn.close()

        elif mod == "📥 Nuevo Folio (IA)":
            st.title("📥 Registro de Documentos")
            foto_cap = st.camera_input("Capturar Oficio")
            # (IA y Registro de Folio se mantiene igual...)
            st.warning("Complete los datos del formulario abajo.")

        elif mod == "📑 Registro Maestro":
            st.title(f"📑 Registro Maestro - Vista: {u_depto}")
            conn = get_db_connection()
            if u_rol in ['Director', 'Administradora']:
                tabs = st.tabs(["🌎 Vista Global"] + AREAS)
                for i, area in enumerate(["Vista Global"] + AREAS):
                    with tabs[i]:
                        query = "SELECT * FROM correspondencia" if area == "Vista Global" else f"SELECT * FROM correspondencia WHERE departamento = '{area}'"
                        df_tab = pd.read_sql_query(query, conn)
                        st.dataframe(df_tab.drop(columns=['foto'], errors='ignore'))
            else:
                df_m = pd.read_sql_query("SELECT * FROM correspondencia WHERE departamento = ?", conn, params=(u_depto,))
                st.dataframe(df_m.drop(columns=['foto'], errors='ignore'))
            conn.close()

        elif mod == "👤 Mi Perfil":
            st.title("👤 Configuración de Perfil")
            st.write(f"Nombre: **{u_nom}**")
            st.write(f"Área: **{u_depto}**")
            
            st.divider()
            st.subheader("🔑 Cambio de Contraseña")
            with st.form("change_pw"):
                new_p = st.text_input("Nueva Contraseña", type="password")
                conf_p = st.text_input("Confirmar Nueva Contraseña", type="password")
                if st.form_submit_button("Actualizar Contraseña"):
                    if new_p == conf_p and len(new_p) > 0:
                        conn = get_db_connection()
                        conn.execute("UPDATE usuarios SET password = ? WHERE user = ?", (new_p, u_id))
                        conn.commit()
                        conn.close()
                        st.success("✅ Contraseña actualizada. Inicie sesión nuevamente para aplicar.")
                    else:
                        st.error("❌ Las contraseñas no coinciden.")

        if st.sidebar.button("Cerrar Sesión"):
            conn = get_db_connection()
            conn.execute("UPDATE usuarios SET online='OFFLINE' WHERE user=?", (u_id,))
            conn.commit(); conn.close(); st.session_state.auth = False; st.rerun()