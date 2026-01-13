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
import os  # <--- VITAL PARA QUE NO SE BORREN LOS DATOS
import streamlit.components.v1 as components

# ==========================================
# 1. CONFIGURACIÓN Y CONEXIÓN SEGURA
# ==========================================
API_KEY_GOOGLE = "AIzaSyAZZrX6EfJ8G7c9doA3cGuAi6LibdqrPrE"
genai.configure(api_key=API_KEY_GOOGLE)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- RUTA EXACTA DE LA BASE DE DATOS ---
# Esto obliga al sistema a guardar el archivo .db en la misma carpeta del script
# y evita que se cree en carpetas temporales que se borran al reiniciar.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'oficialia_v22_FINAL.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. Tabla de Correspondencia (Entradas y Salidas)
    c.execute('''CREATE TABLE IF NOT EXISTS correspondencia 
                  (folio_dir TEXT PRIMARY KEY, cuenta TEXT, sicamdtr TEXT, folio_ext TEXT, 
                  dependencia TEXT, asunto TEXT, nombre_ubica TEXT, fecha_ingreso TEXT, 
                  departamento TEXT, entregado_a TEXT, recibe_investiga TEXT, status TEXT, 
                  seguimiento TEXT, ubicacion_fisica TEXT, quien_firma TEXT, capturista TEXT, foto BLOB)''')
    
    # Columnas extra que se agregan si no existen
    try: c.execute("ALTER TABLE correspondencia ADD COLUMN confirmado INTEGER DEFAULT 0")
    except: pass
    try: c.execute("ALTER TABLE correspondencia ADD COLUMN metodo_entrega TEXT")
    except: pass

    # 2. Tabla de Usuarios
    c.execute("CREATE TABLE IF NOT EXISTS usuarios (user TEXT PRIMARY KEY, password TEXT, nombre TEXT, rol TEXT, depto TEXT, avatar TEXT, online TEXT)")
    
    # 3. Tabla de Mensajes (Chat)
    c.execute("CREATE TABLE IF NOT EXISTS mensajes (id INTEGER PRIMARY KEY AUTOINCREMENT, remitente TEXT, destinatario TEXT, texto TEXT, fecha TEXT, leido INTEGER DEFAULT 0)")
    try: c.execute("ALTER TABLE mensajes ADD COLUMN leido INTEGER DEFAULT 0")
    except: pass 

    # 4. Tabla de Consejo Técnico
    c.execute("CREATE TABLE IF NOT EXISTS consejo_asistencia (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre_asiste TEXT, institucion TEXT, tipo TEXT, carta_blob BLOB, fecha TEXT)")
    
    # 5. NUEVO: Tabla de Citas Hernán
    c.execute("CREATE TABLE IF NOT EXISTS citas_hernan (id INTEGER PRIMARY KEY AUTOINCREMENT, solicitante TEXT, fecha TEXT, hora TEXT, asunto TEXT)")

    # Crear Usuario Administrador por defecto si no existe ninguno
    try:
        # Solo inserta si la tabla está vacía o el admin no existe
        c.execute("INSERT OR IGNORE INTO usuarios VALUES ('ADMIN', '1234', 'ROSA GUTIERREZ', 'Administradora', 'DIRECCIÓN', '👩🏻‍💼', 'OFFLINE')")
        conn.commit()
    except: pass
    
    conn.commit(); conn.close()

init_db()
st.set_page_config(page_title="SIGC V22 PRO", layout="wide")

# ==========================================
# 2. ESTILOS Y FUNCIONES ÚTILES
# ==========================================
st.markdown("""<style>
    .hoja-oficial { background-color: white !important; color: black !important; border: 1px solid #ccc; padding: 20px; font-family: 'Times New Roman'; margin-bottom: 20px; font-size: 14px; }
    .alerta-box { padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid #ff4b4b; background-color: rgba(255, 75, 75, 0.1); }
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

# --- FUNCIÓN DE TUTORIALES (RECUPERADA) ---
def mostrar_tutorial(modulo):
    with st.expander(f"❓ Ayuda: ¿Cómo funciona {modulo}?"):
        if modulo == "Dashboard":
            st.info("📊 **Tablero:** Muestra gráficas de carga de trabajo y estatus de documentos.")
        elif modulo == "Nuevo Folio":
            st.info("""📥 **Registro:** 1. Escribe los datos o toma foto para usar la IA.
            2. El folio se asigna consecutivo automáticamente si usas la sugerencia.
            3. Al guardar, el estatus es 'PENDIENTE' hasta que el usuario lo revise.""")
        elif modulo == "Registro Maestro":
            st.info("""📑 **Maestro:** - **Ver:** Filtra y busca cualquier documento.
            - **Editar:** Cambia estatus o asignación (según tus permisos).
            - **Turnar:** Crea sub-folios (ej. 100-A) desde un folio padre.""")
        elif modulo == "Salidas":
            st.info("📄 **Salidas:** Genera oficios internos (TES/DCAT). El sistema lleva el control numérico.")
        elif modulo == "Citas":
            st.info("📅 **Agenda:** Selecciona un día. El sistema ocultará las horas que ya están ocupadas.")

AREAS = ["DIRECCIÓN", "TRANSMISIONES", "COORDINACIÓN", "CERTIFICACIONES", "VALUACIÓN", "CARTOGRAFÍA", "TRÁMITE Y REGISTRO"]
ROLES = ["Administradora", "Director", "Oficialía", "Jefe de Área", "Secretaria", "Operativo", "Consejero"]

if 'auth' not in st.session_state: st.session_state.auth = False
if 'last_msg_count' not in st.session_state: st.session_state.last_msg_count = 0
if 'form_defaults' not in st.session_state: st.session_state.form_defaults = {}

# ==========================================
# 3. NAVEGACIÓN PRINCIPAL
# ==========================================
menu = st.sidebar.radio("Navegación:", ["🔍 Consulta Pública", "📅 Citas Hernán", "🔐 Sistema Interno"])

# ------------------------------------------
# MÓDULO PÚBLICO: CONSULTA
# ------------------------------------------
if menu == "🔍 Consulta Pública":
    st.title("🏛️ Consulta de Trámites")
    st.markdown("Ingrese su número de folio para ver el estado en tiempo real.")
    q = st.text_input("Número de Folio:", placeholder="Ej. 1234")
    if q:
        conn = get_db_connection()
        # Filtramos para no mostrar documentos internos (TES/DCAT)
        df = pd.read_sql_query("SELECT folio_dir, status, departamento, entregado_a, seguimiento, confirmado, metodo_entrega FROM correspondencia WHERE folio_dir LIKE ? AND folio_dir NOT LIKE 'TES/DCAT/%'", conn, params=(f"%{q}%",))
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
        else:
            st.warning("No se encontró ese folio o es un documento interno.")
        conn.close()

# ------------------------------------------
# MÓDULO PÚBLICO: CITAS HERNÁN
# ------------------------------------------
elif menu == "📅 Citas Hernán":
    mostrar_tutorial("Citas")
    st.title("📅 Agenda de Citas: Hernán")
    st.markdown("### Horarios de Atención:")
    st.info("🕗 **Mañanas:** 08:30 - 09:30  |  🕑 **Tardes:** 14:00 - 15:00")
    
    conn = get_db_connection()
    
    # Visualización de calendario simple
    c_cal, c_form = st.columns([1, 2])
    
    with c_form:
        st.subheader("Agendar Nueva Cita")
        with st.form("form_citas"):
            col_a, col_b = st.columns(2)
            with col_a:
                nom_solicita = st.text_input("Nombre del Solicitante / Perito")
                fecha_sel = st.date_input("Fecha de la cita", min_value=date.today())
            with col_b:
                # Buscar horas ocupadas en esa fecha
                citas_dia = conn.execute("SELECT hora FROM citas_hernan WHERE fecha=?", (str(fecha_sel),)).fetchall()
                ocupadas = [c['hora'] for c in citas_dia]
                
                # Generar slots
                bloques = ["08:30", "08:45", "09:00", "09:15", "14:00", "14:15", "14:30", "14:45"]
                libres = [h for h in bloques if h not in ocupadas]
                
                if libres:
                    hora_sel = st.selectbox("Horarios Disponibles", libres)
                else:
                    hora_sel = st.selectbox("Horarios", ["SIN CUPO - ELIJA OTRA FECHA"])
                
                asunto_cita = st.text_input("Asunto breve")
            
            btn_cita = st.form_submit_button("Confirmar Cita")
            
            if btn_cita:
                if hora_sel != "SIN CUPO - ELIJA OTRA FECHA" and nom_solicita and asunto_cita:
                    conn.execute("INSERT INTO citas_hernan (solicitante, fecha, hora, asunto) VALUES (?,?,?,?)", 
                                 (nom_solicita, str(fecha_sel), hora_sel, asunto_cita))
                    conn.commit()
                    st.success(f"✅ Cita agendada para {nom_solicita} el {fecha_sel} a las {hora_sel}")
                    st.rerun()
                else:
                    st.error("Faltan datos o no hay cupo.")

    with c_cal:
        st.subheader("📆 Citas Próximas")
        df_c = pd.read_sql_query(f"SELECT fecha, hora, solicitante FROM citas_hernan WHERE fecha >= '{date.today()}' ORDER BY fecha, hora LIMIT 10", conn)
        if not df_c.empty:
            st.dataframe(df_c, use_container_width=True, hide_index=True)
        else:
            st.write("No hay citas próximas.")
            
    conn.close()

# ------------------------------------------
# MÓDULO PRIVADO: SISTEMA INTERNO
# ------------------------------------------
else:
    # --- LOGIN ---
    if not st.session_state.auth:
        st.title("🔐 Acceso Administrativo")
        col_login1, col_login2 = st.columns(2)
        u_input = col_login1.text_input("Usuario").upper()
        p_input = col_login2.text_input("Contraseña", type="password")
        
        if st.button("Iniciar Sesión"):
            conn = get_db_connection()
            user_data = conn.execute("SELECT * FROM usuarios WHERE user=? AND password=?", (u_input, p_input)).fetchone()
            if user_data:
                st.session_state.auth = True
                st.session_state.u_dat = list(user_data)
                # Marcar online
                conn.execute("UPDATE usuarios SET online='ONLINE' WHERE user=?", (u_input,))
                conn.commit()
                st.toast(f"Bienvenido/a {user_data['nombre']}")
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
            conn.close()
            
            st.info("Nota: Si es la primera vez, usa ADMIN / 1234")

    # --- SISTEMA DENTRO ---
    else:
        # Desempaquetar datos del usuario
        u_id, u_pw, u_nom, u_rol, u_depto, u_avatar, _ = st.session_state.u_dat
        
        # Verificar mensajes no leídos
        conn = get_db_connection()
        try:
            msgs_pend = conn.execute("SELECT COUNT(*) FROM mensajes WHERE destinatario=? AND leido=0", (u_nom,)).fetchone()[0]
            if msgs_pend > st.session_state.last_msg_count:
                play_sound()
                st.toast(f"🔔 Tienes {msgs_pend} mensajes nuevos")
            st.session_state.last_msg_count = msgs_pend
        except: pass
        
        # Sidebar Info
        st.sidebar.title(f"{u_avatar} {u_nom}")
        st.sidebar.caption(f"Rol: {u_rol}")
        st.sidebar.caption(f"Área: {u_depto}")
        if st.sidebar.button("Cerrar Sesión"):
            conn.execute("UPDATE usuarios SET online='OFFLINE' WHERE user=?", (u_id,))
            conn.commit()
            st.session_state.auth = False
            st.rerun()

        # Menú Interno
        opciones_menu = ["📊 Dashboard", "🚨 Alertas Rápidas", "📥 Nuevo Folio (IA)", "📑 Registro Maestro"]
        
        # Opciones extra según rol
        if u_rol in ["Administradora", "Director", "Oficialía", "Jefe de Área", "Secretaria", "Operativo"]:
            opciones_menu.extend(["📄 Oficios Salida", "📑 Maestro Salidas"])
            
        opciones_menu.extend(["👥 Monitor de Personal", "✉️ Mensajería", "👤 Mi Perfil"])
        
        if u_rol in ["Administradora", "Oficialía"]:
            opciones_menu.extend(["⚙️ Admin Usuarios", "🏛️ Consejo Técnico"])
            
        seleccion = st.sidebar.selectbox("Ir a:", opciones_menu)

        # ----------------------------------
        # 1. DASHBOARD
        # ----------------------------------
        if seleccion == "📊 Dashboard":
            mostrar_tutorial("Dashboard")
            st.title("📊 Tablero de Control")
            conn = get_db_connection()
            
            # Filtro: Admin ve todo, los demás solo su depto
            if u_rol in ["Administradora", "Director", "Oficialía"]:
                query_dash = "SELECT status, entregado_a, departamento FROM correspondencia"
            else:
                query_dash = f"SELECT status, entregado_a, departamento FROM correspondencia WHERE departamento='{u_depto}'"
                
            df_dash = pd.read_sql_query(query_dash, conn)
            
            if not df_dash.empty:
                k1, k2, k3 = st.columns(3)
                with k1:
                    st.plotly_chart(px.pie(df_dash, names='status', title="Estatus General"), use_container_width=True)
                with k2:
                    conteo_area = df_dash['departamento'].value_counts().reset_index()
                    conteo_area.columns = ['Depto', 'Cantidad']
                    st.plotly_chart(px.bar(conteo_area, x='Depto', y='Cantidad', title="Documentos por Área"), use_container_width=True)
                with k3:
                    if 'entregado_a' in df_dash.columns:
                        conteo_pers = df_dash['entregado_a'].value_counts().reset_index()
                        conteo_pers.columns = ['Usuario', 'Carga']
                        st.plotly_chart(px.bar(conteo_pers, x='Usuario', y='Carga', title="Carga por Persona"), use_container_width=True)
            else:
                st.info("No hay datos suficientes para mostrar gráficas.")
            conn.close()

        # ----------------------------------
        # 2. ALERTAS
        # ----------------------------------
        elif seleccion == "🚨 Alertas Rápidas":
            st.title("🚨 Centro de Alertas")
            st.caption("Solo se muestran documentos Pendientes o con Faltantes.")
            conn = get_db_connection()
            df_alert = pd.read_sql_query("SELECT folio_dir, asunto, fecha_ingreso, status, entregado_a FROM correspondencia WHERE status LIKE '%PENDIENTE%' OR status LIKE '%FALTAN DOCUMENTOS%'", conn)
            
            if not df_alert.empty:
                for idx, row in df_alert.iterrows():
                    icono = "🔴" if "FALTA" in row['status'] else "🟡"
                    st.markdown(f"""
                    <div class="alerta-box">
                        <h4>{icono} {row['folio_dir']}</h4>
                        <p><b>Asunto:</b> {row['asunto']}</p>
                        <p><b>Responsable:</b> {row['entregado_a']} | <b>Ingreso:</b> {row['fecha_ingreso']}</p>
                        <p><i>Estatus: {row['status']}</i></p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("¡Excelente! No hay alertas pendientes.")
            conn.close()

        # ----------------------------------
        # 3. NUEVO FOLIO
        # ----------------------------------
        elif seleccion == "📥 Nuevo Folio (IA)":
            mostrar_tutorial("Nuevo Folio")
            st.title("📥 Registro de Entrada")
            
            # Variables de sesión para IA
            if 'ia_data' not in st.session_state: 
                st.session_state.ia_data = {"folio":"", "cuenta":"", "sicamdtr":"", "ext":"", "dep":"", "asunto":""}
            
            conn = get_db_connection()
            lista_usuarios = [r['nombre'] for r in conn.execute("SELECT nombre FROM usuarios").fetchall()]
            
            # Calcular siguiente folio sugerido
            folios_existentes = [r['folio_dir'] for r in conn.execute("SELECT folio_dir FROM correspondencia WHERE folio_dir NOT LIKE 'TES/DCAT/%'").fetchall()]
            numeros = sorted([extract_number(f) for f in folios_existentes if extract_number(f) > 0])
            siguiente_folio = numeros[-1] + 1 if numeros else 1
            
            conn.close()
            
            defaults = st.session_state.form_defaults

            with st.form("form_entrada"):
                c1, c2 = st.columns(2)
                with c1:
                    f_folio = st.text_input("1. Folio", st.session_state.ia_data["folio"], placeholder=f"Sugerido: {siguiente_folio}")
                    f_cuenta = st.text_input("2. Cuenta", st.session_state.ia_data["cuenta"])
                    f_sicam = st.text_input("3. SICAMDTR", st.session_state.ia_data["sicamdtr"])
                    f_ext = st.text_input("4. Ext", st.session_state.ia_data["ext"])
                    f_dep = st.text_input("5. Dependencia", st.session_state.ia_data["dep"])
                    f_asunto = st.text_area("6. Asunto", st.session_state.ia_data["asunto"])
                    f_ubica = st.text_input("7. Ubicación (Remitente)", value=defaults.get('ubi', ''))
                    f_fecha = st.text_input("8. Fecha Recepción", str(date.today()))
                    
                    # Recuperar índice del método
                    idx_m = ["Ventanilla","Correo","Otro"].index(defaults.get('metodo','Ventanilla')) if defaults.get('metodo') in ["Ventanilla","Correo","Otro"] else 0
                    f_metodo = st.selectbox("8.1 Método", ["Ventanilla","Correo","Otro"], index=idx_m)
                    
                with c2:
                    idx_a = AREAS.index(defaults.get('area', AREAS[0])) if defaults.get('area') in AREAS else 0
                    f_area = st.selectbox("9. Área Destino", AREAS, index=idx_a)
                    
                    idx_u = ([""]+lista_usuarios).index(defaults.get('asig', '')) if defaults.get('asig') in ([""]+lista_usuarios) else 0
                    f_asignado = st.selectbox("10. Asignado a", [""]+lista_usuarios, index=idx_u)
                    
                    f_recibe = st.selectbox("11. Recibe", [""]+lista_usuarios)
                    f_status = st.selectbox("12. Estatus Inicial", ["PENDIENTE","EN PROCESO","TERMINADO","FALTAN DOCUMENTOS"])
                    f_seg = st.text_area("13. Seguimiento Inicial")
                    f_fisica = st.text_input("14. Ubicación Física Archivo", value=defaults.get('fisica',''))
                    f_firma = st.text_input("15. Quien Firma")
                    f_captura = st.text_input("16. Capturista", value=u_nom, disabled=True)
                
                btn_guardar = st.form_submit_button("💾 GUARDAR REGISTRO")

            # Sección IA
            st.divider()
            col_cam, col_btn = st.columns([3, 1])
            with col_cam:
                imagen_cam = st.camera_input("📸 Foto del Oficio (Opcional)")
            with col_btn:
                st.write(" ")
                st.write(" ")
                if imagen_cam and st.button("🤖 Auto-llenar con IA"):
                    try:
                        # Prompt para Gemini
                        prompt = "Extrae los datos de este oficio. Formato respuesta: Folio:x|Cuenta:x|Sicam:x|Ext:x|Dependencia:x|Asunto:x"
                        respuesta = model.generate_content([prompt, Image.open(imagen_cam)]).text
                        # Procesar respuesta
                        partes = respuesta.split("|")
                        st.session_state.ia_data = {
                            "folio": partes[0].split(":")[1].strip(),
                            "cuenta": partes[1].split(":")[1].strip(),
                            "sicamdtr": partes[2].split(":")[1].strip(),
                            "ext": partes[3].split(":")[1].strip(),
                            "dep": partes[4].split(":")[1].strip(),
                            "asunto": partes[5].split(":")[1].strip()
                        }
                        st.rerun()
                    except:
                        st.error("No se pudo leer la imagen. Intenta que sea más clara.")

            if btn_guardar:
                blob_img = imagen_cam.getvalue() if imagen_cam else None
                conn = get_db_connection()
                try:
                    # Insert completo
                    conn.execute("""INSERT INTO correspondencia 
                        (folio_dir, cuenta, sicamdtr, folio_ext, dependencia, asunto, nombre_ubica, fecha_ingreso, 
                         departamento, entregado_a, recibe_investiga, status, seguimiento, ubicacion_fisica, 
                         quien_firma, capturista, foto, confirmado, metodo_entrega) 
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?)""", 
                        (f_folio, f_cuenta, f_sicam, f_ext, f_dep, f_asunto, f_ubica, f_fecha, 
                         f_area, f_asignado, f_recibe, f_status, f_seg, f_fisica, f_firma, f_captura, blob_img, f_metodo))
                    conn.commit()
                    
                    # Guardar preferencias para el siguiente registro
                    st.session_state.form_defaults = {'area':f_area,'asig':f_asignado,'ubi':f_ubica,'fisica':f_fisica,'metodo':f_metodo}
                    # Limpiar datos IA
                    st.session_state.ia_data = {"folio":"", "cuenta":"", "sicamdtr":"", "ext":"", "dep":"", "asunto":""}
                    
                    st.success(f"✅ Folio {f_folio} guardado exitosamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar (¿Folio duplicado?): {e}")
                conn.close()

        # ----------------------------------
        # 4. REGISTRO MAESTRO
        # ----------------------------------
        elif seleccion == "📑 Registro Maestro":
            mostrar_tutorial("Registro Maestro")
            st.title("📑 Maestro de Correspondencia")
            
            conn = get_db_connection()
            lista_usuarios = [r['nombre'] for r in conn.execute("SELECT nombre FROM usuarios").fetchall()]
            
            # Filtros
            c_filt1, c_filt2, c_print = st.columns([2, 2, 1])
            filtro_area = c_filt1.selectbox("Filtrar por Área:", ["TODAS"] + AREAS)
            filtro_txt = c_filt2.text_input("Buscar (Folio o Asunto):")
            
            # Query base
            query = "SELECT * FROM correspondencia WHERE folio_dir NOT LIKE 'TES/DCAT/%'"
            if filtro_area != "TODAS":
                query += f" AND departamento='{filtro_area}'"
            if filtro_txt:
                query += f" AND (folio_dir LIKE '%{filtro_txt}%' OR asunto LIKE '%{filtro_txt}%')"
            
            df_maestro = pd.read_sql_query(query, conn)
            
            # Botón imprimir
            with c_print:
                st.write("")
                if st.button("🖨️ Imprimir Reporte"):
                    html_table = df_maestro.drop(columns=['foto'], errors='ignore').to_html(classes='hoja-oficial', index=False)
                    st.components.v1.html(f"<h2>Reporte de Correspondencia</h2>{html_table}<script>window.print()</script>", height=600, scrolling=True)

            tab_ver, tab_edit, tab_turnar = st.tabs(["👁️ Ver Tabla", "✏️ Editar / Borrar", "🔄 Turnar (Derivar)"])
            
            with tab_ver:
                st.dataframe(df_maestro.drop(columns=['foto','confirmado'], errors='ignore'), use_container_width=True)
                
            with tab_edit:
                sel_folio = st.selectbox("Seleccione Folio para Editar:", [""] + df_maestro['folio_dir'].tolist())
                if sel_folio:
                    row = df_maestro[df_maestro['folio_dir'] == sel_folio].iloc[0]
                    
                    # Permisos
                    puede_editar = False
                    if u_rol in ["Administradora", "Director", "Oficialía"]: puede_editar = True
                    elif u_rol in ["Jefe de Área", "Secretaria"] and row['departamento'] == u_depto: puede_editar = True
                    elif u_rol == "Operativo" and row['entregado_a'] == u_nom: puede_editar = True
                    
                    with st.form("form_edit"):
                        ce1, ce2 = st.columns(2)
                        with ce1:
                            ne_folio = st.text_input("Folio", row['folio_dir'], disabled=True)
                            ne_cuenta = st.text_input("Cuenta", row['cuenta'], disabled=not puede_editar)
                            ne_sicam = st.text_input("SICAMDTR", row['sicamdtr'], disabled=not puede_editar)
                            ne_asunto = st.text_area("Asunto", row['asunto'], disabled=not puede_editar)
                            
                            idx_m = ["Ventanilla","Correo","Otro"].index(row['metodo_entrega']) if row['metodo_entrega'] in ["Ventanilla","Correo","Otro"] else 0
                            ne_metodo = st.selectbox("Método", ["Ventanilla","Correo","Otro"], index=idx_m, disabled=not puede_editar)

                        with ce2:
                            idx_area = AREAS.index(row['departamento']) if row['departamento'] in AREAS else 0
                            ne_area = st.selectbox("Área", AREAS, index=idx_area, disabled=not puede_editar)
                            
                            idx_asig = ([""]+lista_usuarios).index(row['entregado_a']) if row['entregado_a'] in lista_usuarios else 0
                            ne_asig = st.selectbox("Asignado A", [""]+lista_usuarios, index=idx_asig, disabled=not puede_editar)
                            
                            idx_stat = ["PENDIENTE","EN PROCESO","TERMINADO","FALTAN DOCUMENTOS"].index(row['status']) if row['status'] in ["PENDIENTE","EN PROCESO","TERMINADO","FALTAN DOCUMENTOS"] else 0
                            ne_status = st.selectbox("Estatus", ["PENDIENTE","EN PROCESO","TERMINADO","FALTAN DOCUMENTOS"], index=idx_stat, disabled=not puede_editar)
                            
                            ne_seg = st.text_area("Seguimiento", row['seguimiento'], disabled=not puede_editar)
                        
                        col_upd, col_del = st.columns(2)
                        if puede_editar and col_upd.form_submit_button("Actualizar Datos"):
                            conn.execute("""UPDATE correspondencia SET 
                                         cuenta=?, sicamdtr=?, asunto=?, departamento=?, entregado_a=?, status=?, seguimiento=?, metodo_entrega=? 
                                         WHERE folio_dir=?""", 
                                         (ne_cuenta, ne_sicam, ne_asunto, ne_area, ne_asig, ne_status, ne_seg, ne_metodo, sel_folio))
                            conn.commit()
                            st.success("Actualizado")
                            st.rerun()
                        
                        # Solo Admin y Oficialía borran
                        if u_rol in ["Administradora", "Oficialía"]:
                            if col_del.form_submit_button("❌ BORRAR FOLIO"):
                                conn.execute("DELETE FROM correspondencia WHERE folio_dir=?", (sel_folio,))
                                conn.commit()
                                st.warning("Eliminado")
                                st.rerun()
                                
            with tab_turnar:
                st.markdown("### Generar Turno / Derivación")
                p_folio = st.selectbox("Folio Padre:", [""] + df_maestro['folio_dir'].tolist())
                if p_folio:
                    padre = df_maestro[df_maestro['folio_dir'] == p_folio].iloc[0]
                    st.info(f"Creando derivación de: {padre['asunto']}")
                    
                    c_t1, c_t2 = st.columns(2)
                    t_area = c_t1.selectbox("Nueva Área", AREAS)
                    t_resp = c_t2.selectbox("Nuevo Responsable", [""]+lista_usuarios)
                    
                    if st.button("Generar Turno"):
                        # Logica A, B, C...
                        base = p_folio.split("-")[0]
                        count_hijos = conn.execute(f"SELECT COUNT(*) FROM correspondencia WHERE folio_dir LIKE '{base}-%'").fetchone()[0]
                        abc = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                        sufijo = abc[count_hijos] if count_hijos < 26 else str(count_hijos)
                        nuevo_folio = f"{base}-{sufijo}"
                        
                        conn.execute("""INSERT INTO correspondencia 
                            (folio_dir, cuenta, sicamdtr, folio_ext, dependencia, asunto, nombre_ubica, fecha_ingreso, 
                            departamento, entregado_a, status, capturista, confirmado, metodo_entrega) 
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", 
                            (nuevo_folio, padre['cuenta'], padre['sicamdtr'], padre['folio_ext'], padre['dependencia'], 
                             padre['asunto'], padre['nombre_ubica'], str(date.today()), t_area, t_resp, "PENDIENTE", u_nom, 0, padre['metodo_entrega']))
                        conn.commit()
                        st.success(f"Turno generado: {nuevo_folio}")
                        st.rerun()
            conn.close()

        # ----------------------------------
        # 5. OFICIOS SALIDA
        # ----------------------------------
        elif seleccion == "📄 Oficios Salida":
            mostrar_tutorial("Salidas")
            st.title("📄 Registro de Salidas")
            conn = get_db_connection()
            lista_usuarios = [r['nombre'] for r in conn.execute("SELECT nombre FROM usuarios").fetchall()]
            
            # Calcular consecutivo
            total_salidas = conn.execute("SELECT COUNT(*) FROM correspondencia WHERE folio_dir LIKE 'TES/DCAT/%'").fetchone()[0]
            consecutivo = total_salidas + 1
            nuevo_folio_sal = f"TES/DCAT/{consecutivo:03d}/2026"
            
            st.info(f"Generando Folio: **{nuevo_folio_sal}**")
            
            with st.form("form_salida"):
                c1, c2 = st.columns(2)
                with c1:
                    s_folio = st.text_input("Folio Salida", value=nuevo_folio_sal)
                    s_asunto = st.text_area("Asunto")
                    s_fecha = st.text_input("Fecha", str(date.today()))
                with c2:
                    s_area = st.selectbox("Área Emisora", AREAS)
                    s_resp = st.selectbox("Responsable", [""]+lista_usuarios)
                    s_stat = st.selectbox("Estatus", ["ENVIADO", "PENDIENTE", "ENTREGADO"])
                
                if st.form_submit_button("Registrar Salida"):
                    conn.execute("""INSERT INTO correspondencia 
                        (folio_dir, asunto, fecha_ingreso, departamento, entregado_a, status, capturista, confirmado, metodo_entrega) 
                        VALUES (?,?,?,?,?,?,?,1,'Interno')""", 
                        (s_folio, s_asunto, s_fecha, s_area, s_resp, s_stat, u_nom))
                    conn.commit()
                    st.success("Salida registrada")
                    st.rerun()
            conn.close()

        # ----------------------------------
        # 6. MAESTRO SALIDAS
        # ----------------------------------
        elif seleccion == "📑 Maestro Salidas":
            st.title("📑 Control de Salidas")
            conn = get_db_connection()
            df_sal = pd.read_sql_query("SELECT * FROM correspondencia WHERE folio_dir LIKE 'TES/DCAT/%'", conn)
            
            if st.button("🖨️ Imprimir Listado Salidas"):
                html = df_sal.drop(columns=['foto'], errors='ignore').to_html(classes='hoja-oficial', index=False)
                st.components.v1.html(f"<h2>Reporte Salidas</h2>{html}<script>window.print()</script>", height=600, scrolling=True)
            
            st.dataframe(df_sal.drop(columns=['foto'], errors='ignore'), use_container_width=True)
            conn.close()

        # ----------------------------------
        # 7. MONITOR DE PERSONAL
        # ----------------------------------
        elif seleccion == "👥 Monitor de Personal":
            st.title("👥 Actividad de Usuarios")
            conn = get_db_connection()
            df_users = pd.read_sql_query("SELECT nombre, depto, online FROM usuarios", conn)
            
            c1, c2 = st.columns(2)
            with c1:
                st.success("🟢 ONLINE")
                st.dataframe(df_users[df_users['online']=='ONLINE'], use_container_width=True)
            with c2:
                st.write("⚪ OFFLINE")
                st.dataframe(df_users[df_users['online']!='ONLINE'], use_container_width=True)
            conn.close()

        # ----------------------------------
        # 8. MENSAJERÍA
        # ----------------------------------
        elif seleccion == "✉️ Mensajería":
            st.title("✉️ Chat Interno")
            conn = get_db_connection()
            
            # Marcar leídos
            conn.execute("UPDATE mensajes SET leido=1 WHERE destinatario=?", (u_nom,))
            conn.commit()
            
            c_chat, c_hist = st.columns([1, 2])
            with c_chat:
                st.subheader("Nuevo Mensaje")
                l_users = [r['nombre'] for r in conn.execute("SELECT nombre FROM usuarios").fetchall()]
                dest = st.selectbox("Para:", l_users)
                txt = st.text_area("Mensaje:")
                if st.button("Enviar"):
                    conn.execute("INSERT INTO mensajes (remitente,destinatario,texto,fecha) VALUES (?,?,?,?)",
                                 (u_nom, dest, txt, str(datetime.now())))
                    conn.commit()
                    st.success("Enviado")
                    st.rerun()
                    
            with c_hist:
                st.subheader("Tu Historial")
                df_m = pd.read_sql_query(f"SELECT fecha, remitente, destinatario, texto FROM mensajes WHERE destinatario='{u_nom}' OR remitente='{u_nom}' ORDER BY id DESC", conn)
                st.dataframe(df_m, use_container_width=True)
            conn.close()

        # ----------------------------------
        # 9. MI PERFIL
        # ----------------------------------
        elif seleccion == "👤 Mi Perfil":
            st.title(f"Hola, {u_nom}")
            conn = get_db_connection()
            
            # Pendientes de confirmar
            pendientes = pd.read_sql_query("SELECT folio_dir, asunto FROM correspondencia WHERE entregado_a=? AND confirmado=0", conn, params=(u_nom,))
            
            if not pendientes.empty:
                st.error(f"⚠️ Tienes {len(pendientes)} documentos nuevos sin aceptar.")
                for i, row in pendientes.iterrows():
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.info(f"**{row['folio_dir']}**: {row['asunto']}")
                    with c2:
                        if st.button(f"Aceptar {row['folio_dir']}"):
                            conn.execute("UPDATE correspondencia SET confirmado=1 WHERE folio_dir=?", (row['folio_dir'],))
                            conn.commit()
                            st.rerun()
            else:
                st.success("Estás al día. No hay recepciones pendientes.")

            st.divider()
            st.subheader("Cambiar Contraseña")
            new_pass = st.text_input("Nueva Contraseña", type="password")
            if st.button("Actualizar Clave"):
                conn.execute("UPDATE usuarios SET password=? WHERE user=?", (new_pass, u_id))
                conn.commit()
                st.success("Contraseña actualizada.")
            
            conn.close()

        # ----------------------------------
        # 10. ADMIN USUARIOS
        # ----------------------------------
        elif seleccion == "⚙️ Admin Usuarios":
            st.title("Gestión de Usuarios")
            conn = get_db_connection()
            
            tab_crear, tab_mod = st.tabs(["Crear Nuevo", "Modificar Existente"])
            
            with tab_crear:
                with st.form("new_user"):
                    nu_user = st.text_input("Usuario (Login)")
                    nu_pass = st.text_input("Contraseña")
                    nu_nom = st.text_input("Nombre Completo")
                    nu_rol = st.selectbox("Rol", ROLES)
                    nu_dep = st.selectbox("Departamento", AREAS)
                    if st.form_submit_button("Crear Usuario"):
                        try:
                            conn.execute("INSERT INTO usuarios VALUES (?,?,?,?,?,?,?)", 
                                         (nu_user, nu_pass, nu_nom, nu_rol, nu_dep, "👤", "OFFLINE"))
                            conn.commit()
                            st.success("Usuario creado")
                        except:
                            st.error("El usuario ya existe.")
            
            with tab_mod:
                all_users = pd.read_sql_query("SELECT * FROM usuarios", conn)
                st.dataframe(all_users)
                
                u_sel = st.selectbox("Seleccionar Usuario a Editar", all_users['user'].tolist())
                if u_sel:
                    u_data = all_users[all_users['user']==u_sel].iloc[0]
                    col_a, col_b = st.columns(2)
                    new_rol = col_a.selectbox("Nuevo Rol", ROLES, index=ROLES.index(u_data['rol']) if u_data['rol'] in ROLES else 0)
                    new_dep = col_b.selectbox("Nuevo Depto", AREAS, index=AREAS.index(u_data['depto']) if u_data['depto'] in AREAS else 0)
                    if st.button("Guardar Cambios Usuario"):
                        conn.execute("UPDATE usuarios SET rol=?, depto=? WHERE user=?", (new_rol, new_dep, u_sel))
                        conn.commit()
                        st.success("Modificado")
                        st.rerun()
            conn.close()

        # ----------------------------------
        # 11. CONSEJO TÉCNICO
        # ----------------------------------
        elif seleccion == "🏛️ Consejo Técnico":
            st.title("🏛️ Gestión del Consejo")
            conn = get_db_connection()
            
            t1, t2, t3 = st.tabs(["📝 Generar Acta (IA)", "✅ Asistencia", "📂 Descargar Todo"])
            
            with t1:
                st.write("Generador de Actas Automático")
                if st.button("Generar Borrador de Acta"):
                    texto_acta = model.generate_content("Redacta un acta formal de consejo técnico catastral municipal, con espacios para firmas.").text
                    st.text_area("Borrador:", value=texto_acta, height=300)
            
            with t2:
                st.write("Registro de Asistencia")
                with st.form("asis"):
                    a_nom = st.text_input("Nombre Asistente")
                    a_tipo = st.selectbox("Tipo", ["Titular", "Suplente", "Invitado"])
                    a_file = st.file_uploader("Subir Nombramiento/Ine (PDF)")
                    if st.form_submit_button("Registrar"):
                        blob = a_file.getvalue() if a_file else None
                        conn.execute("INSERT INTO consejo_asistencia (nombre_asiste, tipo, carta_blob, fecha) VALUES (?,?,?,?)",
                                     (a_nom, a_tipo, blob, str(date.today())))
                        conn.commit()
                        st.success("Registrado")
            
            with t3:
                st.write("Descargar Documentación")
                if st.button("Generar ZIP de Asistencias"):
                    b_io = io.BytesIO()
                    docs = conn.execute("SELECT nombre_asiste, carta_blob FROM consejo_asistencia").fetchall()
                    with zipfile.ZipFile(b_io, "w") as z:
                        for d in docs:
                            if d['carta_blob']:
                                z.writestr(f"{d['nombre_asiste']}.pdf", d['carta_blob'])
                    st.download_button("Descargar ZIP", b_io.getvalue(), "consejo_tecnico.zip")
            
            conn.close()