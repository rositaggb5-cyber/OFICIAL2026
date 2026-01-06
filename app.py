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
    conn.commit()
    conn.close()

init_db()
st.set_page_config(page_title="Oficialía Elite V22", layout="wide")

# Estilos visuales solicitados
st.markdown("""<style>
    [data-testid="stSidebar"] {background-color: #f0f2f6; border-right: 2px solid #d1d5db;}
    .stButton>button {border-radius: 8px;}
    .stExpander {border: 1px solid #e5e7eb; border-radius: 10px; margin-bottom: 10px; background-color: #ffffff;}
</style>""", unsafe_allow_html=True)

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
                conn.commit(); st.rerun()
            else: st.error("Acceso denegado")
            conn.close()
    else:
        u_id, u_pw, u_nom, u_rol, u_depto, u_avatar, _ = st.session_state.u_dat
        st.sidebar.title(f"{u_avatar} {u_nom}")
        
        opcs = ["📊 Dashboard", "🚨 Alertas Rápidas", "📥 Nuevo Folio (IA)", "📑 Registro Maestro", "✉️ Mensajería", "👤 Mi Perfil"]
        if u_rol in ['Director', 'Administradora']: opcs.insert(4, "👥 Monitor de Personal")
        mod = st.sidebar.selectbox("Módulo:", opcs)

        # --- MONITOR DE PERSONAL ---
        if mod == "👥 Monitor de Personal":
            st.title("👥 Monitor de Estatus del Personal")
            conn = get_db_connection()
            df_u = pd.read_sql_query("SELECT nombre, depto, rol, online FROM usuarios", conn)
            c1, c2 = st.columns(2)
            with c1: st.success("🟢 En Línea"); st.table(df_u[df_u['online']=='ONLINE'][['nombre','depto']])
            with c2: st.info("⚪ Desconectados"); st.table(df_u[df_u['online']=='OFFLINE'][['nombre','depto']])
            conn.close()

        # --- DASHBOARD ---
        elif mod == "📊 Dashboard":
            st.title("📊 Control de Gestión")
            conn = get_db_connection()
            df = pd.read_sql_query("SELECT * FROM correspondencia" if u_rol in ['Director', 'Administradora'] else "SELECT * FROM correspondencia WHERE departamento = ?", conn, params=(u_depto,) if u_rol not in ['Director', 'Administradora'] else None)
            if not df.empty:
                col1, col2 = st.columns(2)
                with col1: st.plotly_chart(px.pie(df, names='status', title="Estatus General", hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe))
                with col2: 
                    res_ent = df['entregado_a'].value_counts().reset_index()
                    res_ent.columns = ['empleado', 'count']
                    st.plotly_chart(px.bar(res_ent, x='empleado', y='count', title="Productividad por Personal", color='count'))
            else: st.info("Sin datos para mostrar.")
            conn.close()

        # --- ALERTAS RÁPIDAS (RESTAURADO) ---
        elif mod == "🚨 Alertas Rápidas":
            st.title("🚨 Centro de Notificaciones")
            conn = get_db_connection()
            query_p = "SELECT folio_dir, asunto, departamento, fecha_ingreso FROM correspondencia WHERE status='PENDIENTE'"
            if u_rol not in ['Director', 'Administradora']:
                query_p += f" AND departamento='{u_depto}'"
            df_pend = pd.read_sql_query(query_p, conn)
            st.subheader(f"Trámites Pendientes ({len(df_pend)})")
            st.dataframe(df_pend, use_container_width=True)
            conn.close()

        # --- NUEVO FOLIO CON LIMPIEZA ---
        elif mod == "📥 Nuevo Folio (IA)":
            st.title("📥 Registro de Documentos")
            if 'ia_data' not in st.session_state:
                st.session_state.ia_data = {"folio":"", "cuenta":"", "sicamdtr":"", "ext":"", "dep":"", "asunto":""}
            
            foto_cap = st.camera_input("Capturar Oficio")
            c_ia1, c_ia2 = st.columns(2)
            with c_ia1:
                if foto_cap and st.button("🤖 IA: Analizar"):
                    img = Image.open(foto_cap)
                    response = model.generate_content(["Extraer: Folio, Cuenta, SICAMDTR, Externo, Dependencia, Asunto. Formato F:x|C:x|S:x|E:x|D:x|A:x", img])
                    res = response.text.split("|")
                    st.session_state.ia_data = {"folio": res[0].split(":")[1], "cuenta": res[1].split(":")[1], "sicamdtr": res[2].split(":")[1], "ext": res[3].split(":")[1], "dep": res[4].split(":")[1], "asunto": res[5].split(":")[1]}
            with c_ia2:
                if st.button("🧹 Limpiar Formulario"):
                    st.session_state.ia_data = {"folio":"", "cuenta":"", "sicamdtr":"", "ext":"", "dep":"", "asunto":""}
                    st.rerun()

            with st.form("nuevo_registro"):
                c1, c2 = st.columns(2)
                with c1:
                    f1=st.text_input("Folio", value=st.session_state.ia_data["folio"]); f2=st.text_input("Cuenta", value=st.session_state.ia_data["cuenta"])
                    f3=st.text_input("SICAMDTR", value=st.session_state.ia_data["sicamdtr"]); f4=st.text_input("Folio Ext", value=st.session_state.ia_data["ext"])
                    f5=st.text_input("Dependencia", value=st.session_state.ia_data["dep"]); f6=st.text_area("Asunto", value=st.session_state.ia_data["asunto"])
                    f7=st.text_input("Ubicación Predio"); f8=st.text_input("Fecha", value=str(date.today()))
                with c2:
                    f9=st.selectbox("Área Destino", AREAS); f10=st.text_input("Asignado a"); f11=st.text_input("Recibe")
                    f12=st.selectbox("Estatus", ["PENDIENTE", "EN PROCESO", "FINALIZADO"]); f13=st.text_area("Seguimiento")
                    f14=st.text_input("Ubicación Física"); f15=st.text_input("Firma"); f16=st.text_input("Capturista", value=u_nom, disabled=True)
                
                if st.form_submit_button("💾 Guardar"):
                    img_bytes = foto_cap.getvalue() if foto_cap else None
                    conn = get_db_connection()
                    conn.execute("INSERT INTO correspondencia VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                 (f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, img_bytes))
                    conn.commit(); conn.close(); st.success("Guardado"); st.rerun()

        # --- REGISTRO MAESTRO (EDITAR, TURNAR Y BORRAR) ---
        elif mod == "📑 Registro Maestro":
            st.title("📑 Gestión de Folios")
            conn = get_db_connection()

            if u_rol == 'Administradora':
                with st.expander("🗑️ ZONA DE ELIMINACIÓN (ADMIN)"):
                    f_del = st.text_input("Ingrese Folio para borrar:")
                    if st.button("ELIMINAR PERMANENTEMENTE"):
                        if f_del:
                            conn.execute("DELETE FROM correspondencia WHERE folio_dir=?", (f_del,))
                            conn.commit(); st.warning("Eliminado."); st.rerun()

            # Panel de Edición y Turnado
            df_sel = pd.read_sql_query("SELECT folio_dir FROM correspondencia", conn)
            sel_f = st.selectbox("🔍 Seleccionar Folio para Editar o Turnar:", [""] + df_sel['folio_dir'].tolist())
            
            if sel_f:
                datos = conn.execute("SELECT * FROM correspondencia WHERE folio_dir=?", (sel_f,)).fetchone()
                with st.form("editar_folio"):
                    st.subheader(f"Editando: {sel_f}")
                    ce1, ce2 = st.columns(2)
                    with ce1:
                        ne9 = st.selectbox("Turnar a Área", AREAS, index=AREAS.index(datos['departamento']))
                        ne12 = st.selectbox("Nuevo Estatus", ["PENDIENTE", "EN PROCESO", "FINALIZADO"], index=0)
                    with ce2:
                        ne10 = st.text_input("Reasignar a Persona", value=datos['entregado_a'])
                        ne13 = st.text_area("Actualizar Seguimiento", value=datos['seguimiento'])
                    if st.form_submit_button("🔄 Actualizar y Turnar"):
                        conn.execute("UPDATE correspondencia SET departamento=?, status=?, entregado_a=?, seguimiento=? WHERE folio_dir=?", (ne9, ne12, ne10, ne13, sel_f))
                        conn.commit(); st.success("Actualizado"); st.rerun()

            # Visualización de Tablas
            if u_rol in ['Director', 'Administradora']:
                tabs = st.tabs(["🌎 Global"] + AREAS)
                for i, area in enumerate(["Global"] + AREAS):
                    with tabs[i]:
                        q = "SELECT * FROM correspondencia" if area == "Global" else f"SELECT * FROM correspondencia WHERE departamento='{area}'"
                        st.dataframe(pd.read_sql_query(q, conn).drop(columns=['foto'], errors='ignore'))
            else:
                st.dataframe(pd.read_sql_query("SELECT * FROM correspondencia WHERE departamento=?", conn, params=(u_depto,)).drop(columns=['foto'], errors='ignore'))
            conn.close()

        # --- MENSAJERÍA CON RECIBIDOS ---
        elif mod == "✉️ Mensajería":
            st.title("✉️ Buzón")
            conn = get_db_connection()
            mt1, mt2 = st.tabs(["📤 Enviar Mensaje", "📥 Mensajes Recibidos"])
            with mt1:
                dest = st.selectbox("Para:", [x['nombre'] for x in conn.execute("SELECT nombre FROM usuarios").fetchall()])
                txt = st.text_area("Escribir...")
                if st.button("Enviar"):
                    conn.execute("INSERT INTO mensajes (remitente, destinatario, texto, fecha) VALUES (?,?,?,?)", (u_nom, dest, txt, datetime.now().strftime("%d/%m %H:%M")))
                    conn.commit(); st.success("Enviado")
            with mt2:
                m_rec = pd.read_sql_query("SELECT remitente, texto, fecha FROM mensajes WHERE destinatario=? ORDER BY id DESC", conn, params=(u_nom,))
                for _, m in m_rec.iterrows():
                    with st.chat_message("user"):
                        st.write(f"**De:** {m['remitente']} ({m['fecha']})"); st.write(m['texto'])
            conn.close()

        # --- MI PERFIL CON CAMBIO DE CLAVE ---
        elif mod == "👤 Mi Perfil":
            st.title("👤 Configuración")
            st.write(f"Nombre: **{u_nom}** | Rol: **{u_rol}**")
            st.divider()
            st.subheader("🔑 Cambiar Contraseña")
            with st.form("pass_form"):
                n_p = st.text_input("Nueva Contraseña", type="password")
                c_p = st.text_input("Confirmar", type="password")
                if st.form_submit_button("Cambiar"):
                    if n_p == c_p and n_p != "":
                        conn = get_db_connection()
                        conn.execute("UPDATE usuarios SET password=? WHERE user=?", (n_p, u_id))
                        conn.commit(); conn.close(); st.success("Contraseña cambiada.")
                    else: st.error("No coinciden.")

        if st.sidebar.button("Cerrar Sesión"):
            conn = get_db_connection()
            conn.execute("UPDATE usuarios SET online='OFFLINE' WHERE user=?", (u_id,))
            conn.commit(); conn.close(); st.session_state.auth = False; st.rerun()