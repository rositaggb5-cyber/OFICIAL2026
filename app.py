import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import google.generativeai as genai
from datetime import datetime, date
from PIL import Image
import io
import re  # Para analizar los números de los folios
import zipfile
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
API_KEY_GOOGLE = "AIzaSyAZZrX6EfJ8G7c9doA3cGuAi6LibdqrPrE"
genai.configure(api_key=API_KEY_GOOGLE)
model = genai.GenerativeModel('gemini-1.5-flash')

def get_db_connection():
    # check_same_thread=False permite concurrencia básica
    conn = sqlite3.connect('oficialia_v22.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. Correspondencia
    # Se agrega metodo_entrega
    c.execute('''CREATE TABLE IF NOT EXISTS correspondencia 
                  (folio_dir TEXT PRIMARY KEY, cuenta TEXT, sicamdtr TEXT, folio_ext TEXT, 
                  dependencia TEXT, asunto TEXT, nombre_ubica TEXT, fecha_ingreso TEXT, 
                  departamento TEXT, entregado_a TEXT, recibe_investiga TEXT, status TEXT, 
                  seguimiento TEXT, ubicacion_fisica TEXT, quien_firma TEXT, capturista TEXT, foto BLOB)''')
    
    # Actualizaciones de esquema (Columnas nuevas)
    try: c.execute("ALTER TABLE correspondencia ADD COLUMN confirmado INTEGER DEFAULT 0")
    except: pass
    
    try: c.execute("ALTER TABLE correspondencia ADD COLUMN metodo_entrega TEXT")
    except: pass

    # 2. Usuarios
    c.execute("CREATE TABLE IF NOT EXISTS usuarios (user TEXT PRIMARY KEY, password TEXT, nombre TEXT, rol TEXT, depto TEXT, avatar TEXT, online TEXT)")
    
    # 3. Mensajes
    c.execute("CREATE TABLE IF NOT EXISTS mensajes (id INTEGER PRIMARY KEY AUTOINCREMENT, remitente TEXT, destinatario TEXT, texto TEXT, fecha TEXT, leido INTEGER DEFAULT 0)")
    try: c.execute("ALTER TABLE mensajes ADD COLUMN leido INTEGER DEFAULT 0")
    except: pass 

    # 4. Consejo
    c.execute("CREATE TABLE IF NOT EXISTS consejo_asistencia (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre_asiste TEXT, institucion TEXT, tipo TEXT, carta_blob BLOB, fecha TEXT)")
    
    # Usuario Admin por defecto
    try:
        c.execute("INSERT INTO usuarios VALUES ('ADMIN', '1234', 'ROSA GUTIERREZ', 'Administradora', 'DIRECCIÓN', '👩🏻‍💼', 'OFFLINE')")
        conn.commit()
    except: pass
    conn.commit(); conn.close()

init_db()
st.set_page_config(page_title="SIGC V22 PRO", layout="wide")

# --- ESTILOS ---
st.markdown("""<style>
    .hoja-oficial { background-color: white !important; color: black !important; border: 1px solid #ccc; padding: 20px; font-family: 'Times New Roman'; margin-bottom: 20px; }
    .alerta-box { padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid #ff4b4b; background-color: rgba(255, 75, 75, 0.1); }
    .confirm-box { background-color: #e6fffa; border: 1px solid #004d40; padding: 10px; border-radius: 5px; margin-bottom: 5px; }
    .stExpander { border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; background-color: rgba(240,240,240,0.3); }
    
    /* Estilo para impresión */
    @media print {
        .stSidebar, header, footer, .stButton { display: none !important; }
        .hoja-oficial { border: none; box-shadow: none; }
    }
</style>""", unsafe_allow_html=True)

def play_sound():
    components.html("""<audio autoplay><source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mp3"></audio>""", height=0)

# --- UTILERÍAS ---
def extract_number(text):
    # Extrae el primer número que encuentre en el folio para calcular consecutivos
    nums = re.findall(r'\d+', str(text))
    return int(nums[0]) if nums else 0

AREAS = ["DIRECCIÓN", "TRANSMISIONES", "COORDINACIÓN", "CERTIFICACIONES", "VALUACIÓN", "CARTOGRAFÍA", "TRÁMITE Y REGISTRO"]
# ROLES ACTUALIZADOS: Se agrega "Oficialía"
ROLES = ["Administradora", "Director", "Oficialía", "Jefe de Área", "Secretaria", "Operativo", "Consejero"]

if 'auth' not in st.session_state: st.session_state.auth = False
if 'last_msg_count' not in st.session_state: st.session_state.last_msg_count = 0
# Estado para recomendaciones de llenado
if 'form_defaults' not in st.session_state: st.session_state.form_defaults = {}

# --- NAVEGACIÓN ---
menu = st.sidebar.radio("Navegación:", ["🔍 Consulta Pública", "🔐 Sistema Interno"])

# ==============================================================================
# MÓDULO 1: CONSULTA PÚBLICA
# ==============================================================================
if menu == "🔍 Consulta Pública":
    st.title("🏛️ Consulta de Trámites")
    q = st.text_input("Ingrese número de Folio:")
    if q:
        conn = get_db_connection()
        # Filtro de seguridad: No mostrar salidas internas
        df = pd.read_sql_query("SELECT folio_dir, status, departamento, entregado_a, seguimiento, confirmado, metodo_entrega FROM correspondencia WHERE folio_dir LIKE ? AND folio_dir NOT LIKE 'TES/DCAT/%'", conn, params=(f"%{q}%",))
        if not df.empty:
            for i, r in df.iterrows():
                with st.expander(f"📂 {r['folio_dir']}"):
                    encargado = r['entregado_a']
                    if r['confirmado'] == 0 and encargado:
                        encargado += " (Por Confirmar)"
                    
                    st.write(f"**Atendido por:** {encargado}")
                    st.write(f"**Ubicación:** {r['departamento']}")
                    if r['metodo_entrega']: st.write(f"**Recepción:** {r['metodo_entrega']}")
                    
                    stat = r['status'].upper()
                    seg = r['seguimiento'].upper() if r['seguimiento'] else ""
                    if "FALTA" in stat or "ACUDIR" in seg:
                        st.error(f"⚠️ ESTADO: {stat} (Acudir a Ventanilla)")
                    elif "TERMINADO" in stat or "FINALIZADO" in stat:
                         st.success(f"✅ ESTADO: {stat}")
                    else:
                        st.info(f"🕒 ESTADO: {stat}")
                    st.caption(f"Detalles: {r['seguimiento']}")
        else: st.error("No encontrado.")
        conn.close()

# ==============================================================================
# MÓDULO 2: SISTEMA INTERNO
# ==============================================================================
else:
    if not st.session_state.auth:
        st.title("🔐 Acceso al Sistema")
        c1, c2 = st.columns(2)
        u = c1.text_input("Usuario").upper()
        p = c2.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            conn = get_db_connection()
            user = conn.execute("SELECT * FROM usuarios WHERE user=? AND password=?", (u, p)).fetchone()
            if user:
                st.session_state.auth = True; st.session_state.u_dat = list(user)
                conn.execute("UPDATE usuarios SET online='ONLINE' WHERE user=?", (u,))
                conn.commit()
                st.rerun()
            else: st.error("Credenciales incorrectas.")
            conn.close()
    else:
        u_id, u_pw, u_nom, u_rol, u_depto, u_avatar, _ = st.session_state.u_dat
        
        conn = get_db_connection()
        try:
            msgs = conn.execute("SELECT COUNT(*) FROM mensajes WHERE destinatario=? AND leido=0", (u_nom,)).fetchone()[0]
            if msgs > st.session_state.last_msg_count:
                play_sound(); st.toast(f"🔔 {msgs} Mensajes Nuevos")
            st.session_state.last_msg_count = msgs
        except: pass
        
        st.sidebar.title(f"{u_avatar} {u_nom}")
        st.sidebar.caption(f"{u_rol} | {u_depto}")

        opcs = ["📊 Dashboard", "🚨 Alertas Rápidas", "📥 Nuevo Folio (IA)"]
        opcs.append("📑 Registro Maestro")
        
        # Oficialía tiene acceso a Salidas también
        if u_rol in ["Administradora", "Director", "Oficialía", "Jefe de Área", "Secretaria", "Operativo"]:
            opcs.append("📄 Oficios Salida") 
            opcs.append("📑 Maestro Salidas")

        opcs.append("👥 Monitor de Personal")
        opcs.append("✉️ Mensajería")
        opcs.append("👤 Mi Perfil")
        
        # Oficialía tiene acceso a Admin también
        if u_rol in ["Administradora", "Oficialía"]:
            opcs.append("⚙️ Admin Usuarios")
            opcs.append("🏛️ Consejo Técnico")
        
        mod = st.sidebar.selectbox("Ir a:", opcs)

        # 1. DASHBOARD
        if mod == "📊 Dashboard":
            st.title("📊 Tablero de Control")
            conn = get_db_connection()
            if u_rol in ["Administradora", "Director", "Oficialía"]:
                df = pd.read_sql_query("SELECT status, entregado_a, departamento FROM correspondencia", conn)
            else:
                df = pd.read_sql_query(f"SELECT status, entregado_a, departamento FROM correspondencia WHERE departamento='{u_depto}'", conn)
            if not df.empty:
                c1, c2, c3 = st.columns(3)
                with c1: st.plotly_chart(px.pie(df, names='status', title="1. Estatus Global"), use_container_width=True)
                with c2: 
                    counts = df['departamento'].value_counts().reset_index(); counts.columns=['Área','Total']
                    st.plotly_chart(px.bar(counts, x='Área', y='Total', title="2. Por Área"), use_container_width=True)
                with c3:
                    if 'entregado_a' in df.columns:
                        cp = df['entregado_a'].value_counts().reset_index(); cp.columns=['Usuario','Carga']
                        st.plotly_chart(px.bar(cp, x='Usuario', y='Carga', title="3. Carga Personal"), use_container_width=True)
            else: st.info("Sin datos.")
            conn.close()

        # 2. ALERTAS
        elif mod == "🚨 Alertas Rápidas":
            st.title("🚨 Centro de Alertas")
            conn = get_db_connection()
            pendientes = pd.read_sql_query("SELECT folio_dir, asunto, fecha_ingreso, status FROM correspondencia WHERE status LIKE '%PENDIENTE%' OR status LIKE '%FALTAN DOCUMENTOS%'", conn)
            if not pendientes.empty:
                for i, r in pendientes.iterrows():
                    color = "🔴" if "FALTA" in r['status'] else "🟡"
                    st.markdown(f"""<div class="alerta-box"><h4>{color} Folio: {r['folio_dir']}</h4><p><b>Asunto:</b> {r['asunto']}</p><p><i>Ingresó: {r['fecha_ingreso']} | Estatus: {r['status']}</i></p></div>""", unsafe_allow_html=True)
            else: st.success("¡Todo al día!")
            conn.close()

        # 3. NUEVO FOLIO
        elif mod == "📥 Nuevo Folio (IA)":
            st.title("📥 Registro de Entrada")
            
            # Inicialización de IA Data
            if 'ia_data' not in st.session_state: 
                st.session_state.ia_data = {"folio":"", "cuenta":"", "sicamdtr":"", "ext":"", "dep":"", "asunto":""}

            conn = get_db_connection()
            users = [r['nombre'] for r in conn.execute("SELECT nombre FROM usuarios").fetchall()]
            
            # --- LÓGICA DE CONSECUTIVOS ---
            all_folios = [r['folio_dir'] for r in conn.execute("SELECT folio_dir FROM correspondencia WHERE folio_dir NOT LIKE 'TES/DCAT/%'").fetchall()]
            nums = sorted([extract_number(f) for f in all_folios if extract_number(f) > 0])
            max_fol = nums[-1] if nums else 0
            # -------------------------------
            conn.close()

            # Recuperar valores "recomendados" (defaults) si existen
            defs = st.session_state.form_defaults

            with st.form("reg"):
                c1,c2=st.columns(2)
                with c1:
                    # Folio: No se recomienda valor previo (debe ser único)
                    ni1=st.text_input("1. Folio", st.session_state.ia_data["folio"], placeholder=f"Sugerencia: Siguiente es {max_fol + 1}")
                    
                    # Verificación de huecos en vivo (mientras escribe si refresca) o al cargar
                    curr_num = extract_number(ni1)
                    if curr_num > (max_fol + 1):
                        missing = list(range(max_fol + 1, curr_num))
                        if len(missing) < 10: # Solo mostrar si son pocos para no llenar pantalla
                             st.warning(f"⚠️ ¡OJO! Te estás saltando los folios: {missing}")
                        else:
                             st.warning(f"⚠️ ¡OJO! Hay un salto grande. Del {max_fol} pasaste al {curr_num}.")

                    ni2=st.text_input("2. Cuenta", st.session_state.ia_data["cuenta"])
                    ni3=st.text_input("3. SICAMDTR", st.session_state.ia_data["sicamdtr"])
                    ni4=st.text_input("4. Ext", st.session_state.ia_data["ext"])
                    ni5=st.text_input("5. Dependencia", st.session_state.ia_data["dep"])
                    ni6=st.text_area("6. Asunto", st.session_state.ia_data["asunto"])
                    ni7=st.text_input("7. Ubicación", value=defs.get('ubi', ''))
                    
                    # Fecha por defecto hoy
                    ni8=st.text_input("8. Fecha", str(date.today()))
                    
                    # Nuevo campo Método
                    idx_met = ["Ventanilla", "Correo", "Mensajería", "Otro"].index(defs.get('metodo', 'Ventanilla')) if defs.get('metodo') in ["Ventanilla", "Correo", "Mensajería", "Otro"] else 0
                    ni_met=st.selectbox("8.1 Método Entrega", ["Ventanilla", "Correo", "Mensajería", "Otro"], index=idx_met)

                with c2:
                    # Usamos defaults para índices
                    idx_area = AREAS.index(defs.get('area', AREAS[0])) if defs.get('area') in AREAS else 0
                    ni9=st.selectbox("9. Área", AREAS, index=idx_area)
                    
                    idx_asig = ([""]+users).index(defs.get('asig', '')) if defs.get('asig') in ([""]+users) else 0
                    ni10=st.selectbox("10. Asignado", [""]+users, index=idx_asig)
                    
                    ni11=st.selectbox("11. Recibe", [""]+users)
                    ni12=st.selectbox("12. Estatus", ["PENDIENTE","EN PROCESO","TERMINADO","FALTAN DOCUMENTOS"])
                    ni13=st.text_area("13. Seguimiento")
                    ni14=st.text_input("14. Ub. Física", value=defs.get('fisica', '')); 
                    ni15=st.text_input("15. Firma")
                    ni16=st.text_input("16. Capturista", u_nom, disabled=True)
                
                save = st.form_submit_button("💾 GUARDAR Y LIMPIAR")
            
            foto = st.camera_input("Evidencia")
            if foto and st.button("🤖 IA Auto-llenado"):
                try:
                    res = model.generate_content(["Formato F:x|C:x|S:x|E:x|D:x|A:x", Image.open(foto)]).text.split("|")
                    st.session_state.ia_data = {"folio":res[0].split(":")[1],"cuenta":res[1].split(":")[1],"sicamdtr":res[2].split(":")[1],"ext":res[3].split(":")[1],"dep":res[4].split(":")[1],"asunto":res[5].split(":")[1]}
                    st.rerun()
                except Exception as e: st.error(f"Error IA: {e}")
            
            if save:
                blob = foto.getvalue() if foto else None
                conn = get_db_connection()
                try:
                    conn.execute("""INSERT INTO correspondencia 
                        (folio_dir, cuenta, sicamdtr, folio_ext, dependencia, asunto, nombre_ubica, fecha_ingreso, 
                         departamento, entregado_a, recibe_investiga, status, seguimiento, ubicacion_fisica, 
                         quien_firma, capturista, foto, confirmado, metodo_entrega) 
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?)""", 
                        (ni1,ni2,ni3,ni4,ni5,ni6,ni7,ni8,ni9,ni10,ni11,ni12,ni13,ni14,ni15,ni16,blob,ni_met))
                    conn.commit()
                    
                    # --- AUTO-LIMPIEZA Y RECOMENDACIÓN ---
                    # Guardamos selecciones útiles para el siguiente
                    st.session_state.form_defaults = {
                        'area': ni9,
                        'asig': ni10,
                        'ubi': ni7,
                        'fisica': ni14,
                        'metodo': ni_met
                    }
                    # Limpiamos los datos únicos de IA
                    st.session_state.ia_data = {"folio":"", "cuenta":"", "sicamdtr":"", "ext":"", "dep":"", "asunto":""}
                    
                    st.success("Entrada Guardada. Formulario listo para el siguiente.")
                    st.rerun()
                    
                except Exception as e: st.error(f"Error al guardar: {e}")
                conn.close()

        # 4. REGISTRO MAESTRO
        elif mod == "📑 Registro Maestro":
            st.title("📑 Registro Maestro")
            conn = get_db_connection()
            users = [r['nombre'] for r in conn.execute("SELECT nombre FROM usuarios").fetchall()]

            col_f1, col_f2, col_f3 = st.columns([1,1,1])
            filtro_area = col_f1.selectbox("Filtrar Área:", ["TODAS"]+AREAS)
            filtro_txt = col_f2.text_input("Buscar texto:")
            
            q_sql = "SELECT * FROM correspondencia WHERE folio_dir NOT LIKE 'TES/DCAT/%'"
            if filtro_area != "TODAS": q_sql += f" AND departamento='{filtro_area}'"
            if filtro_txt: q_sql += f" AND (folio_dir LIKE '%{filtro_txt}%' OR asunto LIKE '%{filtro_txt}%')"
            df = pd.read_sql_query(q_sql, conn)
            
            # --- SECCIÓN DE REPORTES / IMPRESIÓN ---
            with col_f3:
                st.write("") # Espacio
                if st.button("🖨️ Generar Reporte Imprimible"):
                    # Crear una versión limpia en HTML para imprimir
                    html_table = df[['folio_dir','fecha_ingreso','asunto','departamento','entregado_a','status','metodo_entrega']].to_html(classes='hoja-oficial', index=False)
                    st.components.v1.html(f"""
                        <h2 style='font-family:sans-serif;'>Reporte de Correspondencia - {date.today()}</h2>
                        {html_table}
                        <script>window.print()</script>
                    """, height=600, scrolling=True)
            # ---------------------------------------

            t1, t2, t3 = st.tabs(["👁️ Ver Tabla", "✏️ Editar (Total)", "🔄 Turnar"])
            with t1: 
                df_view = df.copy()
                df_view['entregado_a'] = df_view.apply(lambda x: f"{x['entregado_a']} (Por Confirmar)" if x['entregado_a'] and x['confirmado']==0 else x['entregado_a'], axis=1)
                st.dataframe(df_view.drop(columns=['foto', 'confirmado'], errors='ignore'), use_container_width=True)
            
            with t2:
                sel_e = st.selectbox("Folio a Editar:", [""]+df['folio_dir'].tolist())
                if sel_e:
                    d = df[df['folio_dir']==sel_e].iloc[0]
                    with st.form("edit"):
                        # --- PERMISOS DE EDICIÓN ---
                        can_edit = False
                        # Admin, Director y OFICIALÍA
                        if u_rol in ["Administradora", "Director", "Oficialía"]: 
                            can_edit = True
                        elif u_rol in ["Jefe de Área", "Secretaria"] and d['departamento'] == u_depto: 
                            can_edit = True
                        elif u_rol == "Operativo" and d['entregado_a'] == u_nom: 
                            can_edit = True
                            
                        disabled_field = not can_edit
                        if not can_edit: st.warning("🔒 Solo lectura.")

                        c1, c2 = st.columns(2)
                        with c1:
                            e1=st.text_input("1. Folio (Protegido)", d['folio_dir'], disabled=True)
                            e2=st.text_input("2. Cuenta", d['cuenta'], disabled=disabled_field)
                            e3=st.text_input("3. SICAMDTR", d['sicamdtr'], disabled=disabled_field)
                            e4=st.text_input("4. Ext", d['folio_ext'], disabled=disabled_field)
                            e5=st.text_input("5. Dependencia", d['dependencia'], disabled=disabled_field)
                            e6=st.text_area("6. Asunto", d['asunto'], disabled=disabled_field)
                            e7=st.text_input("7. Nombre Ubica", d['nombre_ubica'], disabled=disabled_field)
                            e8=st.text_input("8. Fecha Ingreso", d['fecha_ingreso'], disabled=disabled_field)
                            e_met = st.selectbox("8.1 Método", ["Ventanilla", "Correo", "Mensajería", "Otro"], index=["Ventanilla", "Correo", "Mensajería", "Otro"].index(d['metodo_entrega']) if d['metodo_entrega'] in ["Ventanilla", "Correo", "Mensajería", "Otro"] else 0, disabled=disabled_field)

                        with c2:
                            e9=st.selectbox("9. Departamento", AREAS, index=AREAS.index(d['departamento']) if d['departamento'] in AREAS else 0, disabled=disabled_field)
                            e10=st.selectbox("10. Entregado A", [""]+users, index=([""]+users).index(d['entregado_a']) if d['entregado_a'] in users else 0, disabled=disabled_field)
                            e11=st.text_input("11. Recibe/Investiga", d['recibe_investiga'], disabled=disabled_field)
                            e12=st.selectbox("12. Estatus", ["PENDIENTE","EN PROCESO","TERMINADO","FALTAN DOCUMENTOS"], index=["PENDIENTE","EN PROCESO","TERMINADO","FALTAN DOCUMENTOS"].index(d['status']) if d['status'] in ["PENDIENTE","EN PROCESO","TERMINADO","FALTAN DOCUMENTOS"] else 0, disabled=disabled_field)
                            e13=st.text_area("13. Seguimiento", d['seguimiento'], disabled=disabled_field)
                            e14=st.text_input("14. Ub. Física", d['ubicacion_fisica'], disabled=disabled_field)
                            e15=st.text_input("15. Quien Firma", d['quien_firma'], disabled=disabled_field)
                            e16=st.text_input("16. Capturista", d['capturista'], disabled=True)
                        
                        del_ck = False
                        if u_rol in ["Administradora", "Oficialía"]: 
                            st.divider(); del_ck = st.checkbox("Habilitar Borrado (Admin/Oficialía)")

                        if can_edit and st.form_submit_button("💾 ACTUALIZAR DATOS"):
                            conn.execute("""UPDATE correspondencia SET 
                                cuenta=?, sicamdtr=?, folio_ext=?, dependencia=?, asunto=?, nombre_ubica=?, fecha_ingreso=?, 
                                departamento=?, entregado_a=?, recibe_investiga=?, status=?, seguimiento=?, ubicacion_fisica=?, quien_firma=?, metodo_entrega=?
                                WHERE folio_dir=?""", 
                                (e2,e3,e4,e5,e6,e7,e8,e9,e10,e11,e12,e13,e14,e15,e_met,sel_e))
                            conn.commit(); st.success("Datos Actualizados"); st.rerun()
                        
                        if del_ck and st.form_submit_button("❌ ELIMINAR FOLIO"):
                            conn.execute("DELETE FROM correspondencia WHERE folio_dir=?", (sel_e,))
                            conn.commit(); st.warning("Eliminado"); st.rerun()
            with t3:
                padre = st.selectbox("Padre:", [""]+df['folio_dir'].tolist())
                if padre:
                    dd = df[df['folio_dir']==padre].iloc[0]
                    st.info(f"Generando turno desde: **{padre}**")
                    idx_dep = AREAS.index(dd['departamento']) if dd['departamento'] in AREAS else 0
                    idx_usr = ([""]+users).index(dd['entregado_a']) if dd['entregado_a'] in ([""]+users) else 0
                    
                    col_t1, col_t2 = st.columns(2)
                    new_depto = col_t1.selectbox("Turnar a Área:", AREAS, index=idx_dep)
                    new_user = col_t2.selectbox("Asignar Persona:", [""]+users, index=idx_usr)

                    if st.button("Generar Derivación (Turnar)"):
                        base = padre.split("-")[0]
                        cnt = conn.execute(f"SELECT COUNT(*) FROM correspondencia WHERE folio_dir LIKE '{base}-%'").fetchone()[0]
                        abc = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                        new_folio = f"{base}-{abc[cnt]}" if cnt<26 else f"{base}-{cnt}"
                        
                        conn.execute("""INSERT INTO correspondencia 
                            (folio_dir, cuenta, sicamdtr, folio_ext, dependencia, asunto, nombre_ubica, fecha_ingreso, 
                            departamento, entregado_a, recibe_investiga, status, seguimiento, ubicacion_fisica, 
                            quien_firma, capturista, foto, confirmado, metodo_entrega) 
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL,0,?)""",
                            (new_folio, dd['cuenta'], dd['sicamdtr'], dd['folio_ext'], dd['dependencia'], dd['asunto'], 
                             dd['nombre_ubica'], str(date.today()), new_depto, new_user, dd['recibe_investiga'], 
                             "PENDIENTE", "", dd['ubicacion_fisica'], dd['quien_firma'], u_nom, dd['metodo_entrega']))
                        conn.commit(); st.success(f"Turno creado correctamente: {new_folio}"); st.rerun()
            conn.close()

        # 5. OFICIOS SALIDA
        elif mod == "📄 Oficios Salida":
            st.title("📄 Registro de Salida")
            conn = get_db_connection()
            users = [r['nombre'] for r in conn.execute("SELECT nombre FROM usuarios").fetchall()]
            try: cnt = conn.execute("SELECT COUNT(*) FROM correspondencia WHERE folio_dir LIKE 'TES/DCAT/%'").fetchone()[0] + 1
            except: cnt = 1
            nuevo_fol_salida = f"TES/DCAT/{cnt:03d}/2026"
            st.info(f"Registrando Folio de Salida: **{nuevo_fol_salida}**")
            with st.form("reg_salida"):
                c1,c2=st.columns(2)
                with c1:
                    ns1=st.text_input("1. Folio Salida", value=nuevo_fol_salida) 
                    ns2=st.text_input("2. Cuenta")
                    ns3=st.text_input("3. SICAMDTR")
                    ns4=st.text_input("4. Ext")
                    ns5=st.text_input("5. Dependencia Destino")
                    ns6=st.text_area("6. Asunto")
                    ns7=st.text_input("7. Ubicación")
                    ns8=st.text_input("8. Fecha Salida", str(date.today()))
                with c2:
                    ns9=st.selectbox("9. Área", AREAS)
                    ns10=st.selectbox("10. Responsable", [""]+users)
                    ns11=st.selectbox("11. Destinatario", [""]+users)
                    ns12=st.selectbox("12. Estatus", ["TERMINADO", "ENVIADO", "ACUSE PENDIENTE"])
                    ns13=st.text_area("13. Observaciones")
                    ns14=st.text_input("14. Archivo Físico")
                    ns15=st.text_input("15. Firma")
                    ns16=st.text_input("16. Capturista", u_nom, disabled=True)
                save_salida = st.form_submit_button("💾 GUARDAR SALIDA")
            if save_salida:
                try:
                    conn.execute("""INSERT INTO correspondencia 
                        (folio_dir, cuenta, sicamdtr, folio_ext, dependencia, asunto, nombre_ubica, fecha_ingreso, 
                         departamento, entregado_a, recibe_investiga, status, seguimiento, ubicacion_fisica, 
                         quien_firma, capturista, foto, confirmado, metodo_entrega) 
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL,1, 'Interno')""", 
                        (ns1,ns2,ns3,ns4,ns5,ns6,ns7,ns8,ns9,ns10,ns11,ns12,ns13,ns14,ns15,ns16))
                    conn.commit(); st.success(f"Salida Registrada: {ns1}"); st.rerun()
                except Exception as e: st.error(f"Error al guardar: {e}")
            conn.close()

        # 6. MAESTRO SALIDAS
        elif mod == "📑 Maestro Salidas":
            st.title("📑 Maestro de Folios de Salida")
            conn = get_db_connection()
            users = [r['nombre'] for r in conn.execute("SELECT nombre FROM usuarios").fetchall()]
            df = pd.read_sql_query("SELECT * FROM correspondencia WHERE folio_dir LIKE 'TES/DCAT/%'", conn)
            
            # --- BOTÓN DE IMPRESIÓN PARA SALIDAS ---
            if st.button("🖨️ Imprimir Lista Salidas"):
                    html_table = df[['folio_dir','fecha_ingreso','asunto','departamento','entregado_a','status']].to_html(classes='hoja-oficial', index=False)
                    st.components.v1.html(f"""<h2 style='font-family:sans-serif;'>Reporte Salidas - {date.today()}</h2>{html_table}<script>window.print()</script>""", height=600, scrolling=True)
            # ---------------------------------------

            t1, t2 = st.tabs(["👁️ Ver Salidas", "✏️ Editar Salida (Total)"])
            with t1: st.dataframe(df.drop(columns=['foto'], errors='ignore'), use_container_width=True)
            with t2:
                sel_e = st.selectbox("Editar Salida:", [""]+df['folio_dir'].tolist())
                if sel_e:
                    d = df[df['folio_dir']==sel_e].iloc[0]
                    with st.form("edit_salida"):
                        # --- PERMISOS SALIDAS ---
                        can_edit = False
                        if u_rol in ["Administradora", "Director", "Oficialía"]: can_edit = True
                        elif u_rol in ["Jefe de Área", "Secretaria"] and d['departamento'] == u_depto: can_edit = True
                        elif d['capturista'] == u_nom: can_edit = True
                        
                        disabled_field = not can_edit
                        if not can_edit: st.warning("🔒 Solo lectura.")

                        c1, c2 = st.columns(2)
                        with c1:
                            e1=st.text_input("1. Folio Salida", d['folio_dir'], disabled=True)
                            e2=st.text_input("2. Cuenta", d['cuenta'], disabled=disabled_field)
                            e3=st.text_input("3. SICAMDTR", d['sicamdtr'], disabled=disabled_field)
                            e4=st.text_input("4. Ext", d['folio_ext'], disabled=disabled_field)
                            e5=st.text_input("5. Dependencia Destino", d['dependencia'], disabled=disabled_field)
                            e6=st.text_area("6. Asunto", d['asunto'], disabled=disabled_field)
                            e7=st.text_input("7. Ubicación", d['nombre_ubica'], disabled=disabled_field)
                            e8=st.text_input("8. Fecha Salida", d['fecha_ingreso'], disabled=disabled_field)
                        with c2:
                            e9=st.selectbox("9. Área", AREAS, index=AREAS.index(d['departamento']) if d['departamento'] in AREAS else 0, disabled=disabled_field)
                            e10=st.selectbox("10. Responsable", [""]+users, index=([""]+users).index(d['entregado_a']) if d['entregado_a'] in users else 0, disabled=disabled_field)
                            e11=st.selectbox("11. Destinatario", [""]+users, index=([""]+users).index(d['recibe_investiga']) if d['recibe_investiga'] in users else 0, disabled=disabled_field)
                            e12=st.selectbox("12. Estatus", ["TERMINADO", "ENVIADO", "ACUSE PENDIENTE"], index=["TERMINADO", "ENVIADO", "ACUSE PENDIENTE"].index(d['status']) if d['status'] in ["TERMINADO", "ENVIADO", "ACUSE PENDIENTE"] else 0, disabled=disabled_field)
                            e13=st.text_area("13. Observaciones", d['seguimiento'], disabled=disabled_field)
                            e14=st.text_input("14. Archivo Físico", d['ubicacion_fisica'], disabled=disabled_field)
                            e15=st.text_input("15. Firma", d['quien_firma'], disabled=disabled_field)
                            e16=st.text_input("16. Capturista", d['capturista'], disabled=True)
                        
                        del_ck = False
                        if u_rol in ["Administradora", "Oficialía"]: st.divider(); del_ck = st.checkbox("Habilitar Borrado (Admin/Oficialía)")

                        if can_edit and st.form_submit_button("💾 ACTUALIZAR SALIDA"):
                            conn.execute("""UPDATE correspondencia SET 
                                cuenta=?, sicamdtr=?, folio_ext=?, dependencia=?, asunto=?, nombre_ubica=?, fecha_ingreso=?, 
                                departamento=?, entregado_a=?, recibe_investiga=?, status=?, seguimiento=?, ubicacion_fisica=?, quien_firma=? 
                                WHERE folio_dir=?""", 
                                (e2,e3,e4,e5,e6,e7,e8,e9,e10,e11,e12,e13,e14,e15,sel_e))
                            conn.commit(); st.success("Actualizado"); st.rerun()
                        if del_ck and st.form_submit_button("❌ ELIMINAR SALIDA"):
                            conn.execute("DELETE FROM correspondencia WHERE folio_dir=?", (sel_e,))
                            conn.commit(); st.warning("Eliminado"); st.rerun()
            conn.close()

        # 7. MONITOR
        elif mod == "👥 Monitor de Personal":
            st.title("👥 Monitor de Actividad")
            conn = get_db_connection()
            df_u = pd.read_sql_query("SELECT nombre, depto, online FROM usuarios ORDER BY nombre", conn)
            c1, c2 = st.columns(2)
            with c1:
                st.success(f"🟢 EN LÍNEA ({len(df_u[df_u['online']=='ONLINE'])})")
                st.dataframe(df_u[df_u['online']=='ONLINE'][['nombre','depto']], use_container_width=True)
            with c2:
                st.write(f"⚫ DESCONECTADOS ({len(df_u[df_u['online']!='ONLINE'])})")
                st.dataframe(df_u[df_u['online']!='ONLINE'][['nombre','depto']], use_container_width=True)
            conn.close()

        # 8. MENSAJERÍA
        elif mod == "✉️ Mensajería":
            st.title("✉️ Chat Interno")
            conn = get_db_connection()
            try:
                conn.execute("UPDATE mensajes SET leido=1 WHERE destinatario=?", (u_nom,))
                conn.commit()
            except: pass
            c1, c2 = st.columns([3, 1])
            with c1:
                users = [r['nombre'] for r in conn.execute("SELECT nombre FROM usuarios").fetchall()]
                to = st.selectbox("Para:", users)
                tx = st.text_area("Mensaje:")
                if st.button("Enviar"):
                    conn.execute("INSERT INTO mensajes (remitente,destinatario,texto,fecha) VALUES (?,?,?,?,?)", (u_nom,to,tx,str(datetime.now())))
                    conn.commit(); st.success("Enviado"); st.rerun()
            st.write("---")
            st.subheader("Historial")
            try:
                df_msg = pd.read_sql_query(f"SELECT fecha, remitente, texto FROM mensajes WHERE destinatario='{u_nom}' OR remitente='{u_nom}' ORDER BY id DESC", conn)
                st.dataframe(df_msg, use_container_width=True)
            except: st.info("Bandeja vacía")
            conn.close()

        # 9. PERFIL
        elif mod == "👤 Mi Perfil":
            st.title(f"Perfil: {u_nom}")
            conn = get_db_connection()
            
            # --- CONFIRMACIÓN ---
            pendientes_conf = pd.read_sql_query("SELECT folio_dir, asunto FROM correspondencia WHERE entregado_a=? AND confirmado=0", conn, params=(u_nom,))
            if not pendientes_conf.empty:
                st.warning(f"⚠️ Tienes {len(pendientes_conf)} folios sin confirmar.")
                st.write("Acepta el trabajo para que quede registrado:")
                for i, r in pendientes_conf.iterrows():
                    st.markdown(f"<div class='confirm-box'><b>Folio: {r['folio_dir']}</b><br>{r['asunto']}</div>", unsafe_allow_html=True)
                    if st.button(f"✅ ACEPTAR {r['folio_dir']}"):
                        conn.execute("UPDATE correspondencia SET confirmado=1 WHERE folio_dir=?", (r['folio_dir'],))
                        conn.commit(); st.success("Confirmado"); st.rerun()
                st.divider()

            st.subheader("📂 Mis Folios Activos")
            mf = pd.read_sql_query("SELECT folio_dir, asunto, status FROM correspondencia WHERE entregado_a=? AND confirmado=1", conn, params=(u_nom,))
            if not mf.empty: st.dataframe(mf, use_container_width=True)
            else: st.info("No tienes folios activos.")
            
            with st.expander("🔑 Seguridad"):
                np = st.text_input("Nueva Clave:", type="password")
                if st.button("Cambiar Clave"): conn.execute("UPDATE usuarios SET password=? WHERE user=?", (np,u_id)); conn.commit(); st.success("Listo")
            st.divider()
            with st.expander("🆘 Soporte"):
                st.markdown("### 🔴 Botón de Pánico")
                if st.button("🚨 NOTIFICAR FALLA A ROSA"):
                     conn.execute("INSERT INTO mensajes (remitente,destinatario,texto,fecha) VALUES (?,?,?,?,?)",(u_nom,"ROSA GUTIERREZ","AYUDA URGENTE - FALLA SISTEMA",str(datetime.now()))); conn.commit(); st.error("Alerta Enviada")
            if st.button("Salir"):
                conn.execute("UPDATE usuarios SET online='OFFLINE' WHERE user=?",(u_id,)); conn.commit(); st.session_state.auth=False; st.rerun()
            conn.close()

        # 10. ADMIN USUARIOS
        elif mod == "⚙️ Admin Usuarios":
            st.title("⚙️ Usuarios")
            conn=get_db_connection()
            t_c, t_e = st.tabs(["Crear", "Modificar"])
            with t_c:
                with st.form("nu"):
                    u=st.text_input("User"); p=st.text_input("Pass"); n=st.text_input("Nom"); r=st.selectbox("Rol", ROLES); d=st.selectbox("Depto", AREAS)
                    if st.form_submit_button("Crear"): conn.execute("INSERT INTO usuarios VALUES (?,?,?,?,?,?,?)",(u,p,n,r,d,"👤","OFF")); conn.commit(); st.success("Ok")
            with t_e:
                us = st.selectbox("User:", [r['user'] for r in conn.execute("SELECT user FROM usuarios").fetchall()])
                if us:
                    curr = conn.execute("SELECT * FROM usuarios WHERE user=?",(us,)).fetchone()
                    na = st.selectbox("Área:", AREAS, index=AREAS.index(curr['depto']) if curr['depto'] in AREAS else 0)
                    nr = st.selectbox("Rol:", ROLES, index=ROLES.index(curr['rol']) if curr['rol'] in ROLES else 0)
                    if st.button("Guardar"): conn.execute("UPDATE usuarios SET depto=?, rol=? WHERE user=?",(na,nr,us)); conn.commit(); st.success("Ok"); st.rerun()
            st.dataframe(pd.read_sql_query("SELECT user, nombre, rol, depto FROM usuarios", conn)); conn.close()

        # 11. CONSEJO
        elif mod == "🏛️ Consejo Técnico":
            st.title("🏛️ Consejo")
            t1, t2, t3 = st.tabs(["IA", "Asistencia", "ZIP"])
            with t1:
                if st.button("Generar Acta"): st.text_area("Acta:", model.generate_content("Acta Consejo").text)
            with t2:
                with st.form("a"):
                    n=st.text_input("Nombre"); t=st.selectbox("Tipo",["Titular","Suplente"]); f=st.file_uploader("PDF")
                    if st.form_submit_button("Guardar"):
                        b=f.getvalue() if f else None
                        conn=get_db_connection(); conn.execute("INSERT INTO consejo_asistencia (nombre_asiste,tipo,carta_blob,fecha) VALUES (?,?,?,?)",(n,t,b,str(date.today()))); conn.commit(); conn.close(); st.success("Ok")
            with t3:
                if st.button("Bajar ZIP"):
                    b=io.BytesIO(); conn=get_db_connection(); fs=conn.execute("SELECT nombre_asiste, carta_blob FROM consejo_asistencia").fetchall()
                    with zipfile.ZipFile(b,"w") as z:
                        for f in fs: 
                            if f['carta_blob']: z.writestr(f"{f['nombre_asiste']}.pdf", f['carta_blob'])
                    st.download_button("ZIP", b.getvalue(), "consejo.zip")