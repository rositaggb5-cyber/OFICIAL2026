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

        if mod == "👥 Monitor de Personal":
            st.title("👥 Monitor de Estatus del Personal")
            conn = get_db_connection()
            df_u = pd.read_sql_query("SELECT nombre, depto, rol, online FROM usuarios", conn)
            c1, c2 = st.columns(2)
            with c1: st.success("🟢 En Línea"); st.table(df_u[df_u['online']=='ONLINE'][['nombre','depto']])
            with c2: st.info("⚪ Desconectados"); st.table(df_u[df_u['online']=='OFFLINE'][['nombre','depto']])
            conn.close()

        elif mod == "📊 Dashboard":
            st.title("📊 Control de Gestión Operativa")
            conn = get_db_connection()
            query_dash = "SELECT status, entregado_a, departamento FROM correspondencia"
            if u_rol not in ['Director', 'Administradora']:
                query_dash += f" WHERE departamento = '{u_depto}'"
            df = pd.read_sql_query(query_dash, conn)
            conn.close()
            if not df.empty:
                col1, col2 = st.columns(2)
                with col1:
                    fig_pie = px.pie(df, names='status', title="Estatus de los Trámites", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                    st.plotly_chart(fig_pie, use_container_width=True)
                with col2:
                    res_ent = df['entregado_a'].value_counts().reset_index()
                    res_ent.columns = ['Personal', 'Cantidad']
                    fig_bar = px.bar(res_ent, x='Personal', y='Cantidad', title="Carga de Trabajo por Personal", color='Cantidad', color_continuous_scale='Viridis')
                    st.plotly_chart(fig_bar, use_container_width=True)
                st.subheader("Trámites por Departamento")
                fig_dept = px.histogram(df, x='departamento', color='status', barmode='group', title="Distribución por Áreas")
                st.plotly_chart(fig_dept, use_container_width=True)
            else:
                st.info("Aún no hay datos registrados para generar gráficas.")

        elif mod == "🚨 Alertas Rápidas":
            st.title("🚨 Centro de Notificaciones")
            conn = get_db_connection()
            q_p = "SELECT folio_dir, asunto, departamento FROM correspondencia WHERE status='PENDIENTE'"
            if u_rol not in ['Director', 'Administradora']: q_p += f" AND departamento='{u_depto}'"
            st.dataframe(pd.read_sql_query(q_p, conn), use_container_width=True)
            conn.close()

        # MODIFICADO: FORMULARIO ARRIBA / IA ABAJO
        elif mod == "📥 Nuevo Folio (IA)":
            st.title("📥 Registro de Documentos")
            if 'ia_data' not in st.session_state:
                st.session_state.ia_data = {"folio":"", "cuenta":"", "sicamdtr":"", "ext":"", "dep":"", "asunto":""}
            
            with st.form("nuevo_registro"):
                c1, c2 = st.columns(2)
                with c1:
                    ni1=st.text_input("Folio", value=st.session_state.ia_data["folio"]); ni2=st.text_input("Cuenta", value=st.session_state.ia_data["cuenta"])
                    ni3=st.text_input("SICAMDTR", value=st.session_state.ia_data["sicamdtr"]); ni4=st.text_input("Folio Ext", value=st.session_state.ia_data["ext"])
                    ni5=st.text_input("Dependencia", value=st.session_state.ia_data["dep"]); ni6=st.text_area("Asunto", value=st.session_state.ia_data["asunto"])
                    ni7=st.text_input("Ubicación Predio"); ni8=st.text_input("Fecha", value=str(date.today()))
                with c2:
                    ni9=st.selectbox("Área", AREAS); ni10=st.text_input("Asignado"); ni11=st.text_input("Recibe")
                    ni12=st.selectbox("Estatus", ["PENDIENTE", "EN PROCESO"]); ni13=st.text_area("Seguimiento")
                    ni14=st.text_input("Ubicación Física"); ni15=st.text_input("Firma"); ni16=st.text_input("Capturista", value=u_nom, disabled=True)
                
                f_save = st.form_submit_button("💾 Guardar")

            st.divider()
            st.subheader("🤖 Asistente IA (Opcional)")
            foto_cap = st.camera_input("Capturar Oficio")
            cb1, cb2 = st.columns(2)
            with cb1:
                if foto_cap and st.button("🤖 IA: Analizar"):
                    img = Image.open(foto_cap)
                    response = model.generate_content(["Analiza: Folio, Cuenta, SICAMDTR, Externo, Dependencia, Asunto. Formato F:x|C:x|S:x|E:x|D:x|A:x", img])
                    res = response.text.split("|")
                    st.session_state.ia_data = {"folio": res[0].split(":")[1], "cuenta": res[1].split(":")[1], "sicamdtr": res[2].split(":")[1], "ext": res[3].split(":")[1], "dep": res[4].split(":")[1], "asunto": res[5].split(":")[1]}
                    st.rerun()
            with cb2:
                if st.button("🧹 Limpiar Formulario"):
                    st.session_state.ia_data = {"folio":"", "cuenta":"", "sicamdtr":"", "ext":"", "dep":"", "asunto":""}; st.rerun()

            if f_save:
                img_bytes = foto_cap.getvalue() if foto_cap else None
                conn = get_db_connection()
                conn.execute("INSERT INTO correspondencia VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (ni1, ni2, ni3, ni4, ni5, ni6, ni7, ni8, ni9, ni10, ni11, ni12, ni13, ni14, ni15, ni16, img_bytes))
                conn.commit(); conn.close(); st.success("Guardado"); st.rerun()

        # MODIFICADO: LÓGICA DE SUB-FOLIOS EN TURNAR
        elif mod == "📑 Registro Maestro":
            st.title("📑 Gestión de Folios")
            conn = get_db_connection()
            if u_rol == 'Administradora':
                with st.expander("🗑️ ZONA DE ELIMINACIÓN (ADMIN)"):
                    f_del = st.text_input("Ingrese Folio exacto para borrar:")
                    if st.button("BORRAR PERMANENTEMENTE"):
                        if f_del:
                            conn.execute("DELETE FROM correspondencia WHERE folio_dir=?", (f_del,))
                            conn.commit(); st.warning("Eliminado."); st.rerun()
            tab_turnar, tab_editar = st.tabs(["🔄 Turnar Folio", "📝 Editar Datos (16 campos)"])
            df_folios = pd.read_sql_query("SELECT folio_dir FROM correspondencia", conn)
            lista_f = [""] + df_folios['folio_dir'].tolist()
            with tab_turnar:
                sel_t = st.selectbox("Folio para Turnar:", lista_f, key="s_t")
                if sel_t:
                    d_t = conn.execute("SELECT * FROM correspondencia WHERE folio_dir=?", (sel_t,)).fetchone()
                    ct1, ct2 = st.columns(2)
                    with ct1:
                        nt_depto = st.selectbox("Nuevo Departamento:", AREAS)
                        nt_status = st.selectbox("Nuevo Estatus:", ["PENDIENTE", "EN PROCESO"])
                    with ct2:
                        nt_pers = st.text_input("Asignar a:", value=d_t['entregado_a'])
                    if st.button("Confirmar Turnado"):
                        base = sel_t.split("-")[0]
                        existentes = conn.execute("SELECT COUNT(*) FROM correspondencia WHERE folio_dir LIKE ?", (f"{base}-%",)).fetchone()[0]
                        letras = ["A", "B", "C", "D", "E", "F", "G", "H"]
                        nueva_letra = letras[existentes] if existentes < len(letras) else "Z"
                        nuevo_folio = f"{base}-{nueva_letra}"
                        conn.execute("INSERT INTO correspondencia VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                     (nuevo_folio, d_t['cuenta'], d_t['sicamdtr'], d_t['folio_ext'], d_t['dependencia'], d_t['asunto'], d_t['nombre_ubica'], d_t['fecha_ingreso'], nt_depto, nt_pers, d_t['recibe_investiga'], nt_status, d_t['seguimiento'], d_t['ubicacion_fisica'], d_t['quien_firma'], u_nom, d_t['foto']))
                        conn.commit(); st.success(f"Turnado como: {nuevo_folio}"); st.rerun()
            with tab_editar:
                sel_e = st.selectbox("Folio para Editar:", lista_f, key="s_e")
                if sel_e:
                    de = conn.execute("SELECT * FROM correspondencia WHERE folio_dir=?", (sel_e,)).fetchone()
                    with st.form("edit_total"):
                        ce1, ce2 = st.columns(2)
                        with ce1:
                            e2=st.text_input("Cuenta", de['cuenta']); e3=st.text_input("SICAMDTR", de['sicamdtr']); e4=st.text_input("Folio Ext", de['folio_ext']); e5=st.text_input("Dependencia", de['dependencia']); e6=st.text_area("Asunto", de['asunto']); e7=st.text_input("Ubicación", de['nombre_ubica']); e8=st.text_input("Fecha", de['fecha_ingreso'])
                        with ce2:
                            e9=st.selectbox("Área", AREAS, index=AREAS.index(de['departamento'])); e10=st.text_input("Asignado", de['entregado_a']); e11=st.text_input("Recibe", de['recibe_investiga']); e12=st.selectbox("Estatus", ["PENDIENTE", "EN PROCESO", "FINALIZADO"]); e13=st.text_area("Seguimiento", de['seguimiento']); e14=st.text_input("Ubicación F.", de['ubicacion_fisica']); e15=st.text_input("Firma", de['quien_firma'])
                        if st.form_submit_button("Guardar Cambios"):
                            conn.execute("UPDATE correspondencia SET cuenta=?, sicamdtr=?, folio_ext=?, dependencia=?, asunto=?, nombre_ubica=?, fecha_ingreso=?, departamento=?, entregado_a=?, recibe_investiga=?, status=?, seguimiento=?, ubicacion_fisica=?, quien_firma=? WHERE folio_dir=?", (e2, e3, e4, e5, e6, e7, e8, e9, e10, e11, e12, e13, e14, e15, sel_e))
                            conn.commit(); st.success("Datos actualizados"); st.rerun()
            if u_rol in ['Director', 'Administradora']:
                v_tabs = st.tabs(["🌎 Global"] + AREAS)
                for i, area in enumerate(["Global"] + AREAS):
                    with v_tabs[i]:
                        query = "SELECT * FROM correspondencia" if area == "Global" else f"SELECT * FROM correspondencia WHERE departamento = '{area}'"
                        st.dataframe(pd.read_sql_query(query, conn).drop(columns=['foto'], errors='ignore'), use_container_width=True)
            else:
                st.dataframe(pd.read_sql_query("SELECT * FROM correspondencia WHERE departamento = ?", conn, params=(u_depto,)).drop(columns=['foto'], errors='ignore'), use_container_width=True)
            conn.close()

        elif mod == "✉️ Mensajería":
            st.title("✉️ Buzón")
            conn = get_db_connection()
            t_m1, t_m2 = st.tabs(["📤 Enviar", "📥 Recibidos"])
            with t_m1:
                dest = st.selectbox("Para:", [x['nombre'] for x in conn.execute("SELECT nombre FROM usuarios").fetchall()])
                txt = st.text_area("Mensaje")
                if st.button("Enviar"):
                    conn.execute("INSERT INTO mensajes (remitente, destinatario, texto, fecha) VALUES (?,?,?,?)", (u_nom, dest, txt, str(datetime.now())))
                    conn.commit(); st.success("Enviado")
            with t_m2:
                m_rec = pd.read_sql_query("SELECT remitente, texto, fecha FROM mensajes WHERE destinatario=?", conn, params=(u_nom,))
                for _, m in m_rec.iterrows():
                    with st.chat_message("user"): st.write(f"**De:** {m['remitente']} ({m['fecha']})"); st.write(m['texto'])
            conn.close()

        elif mod == "👤 Mi Perfil":
            st.title("👤 Configuración")
            st.write(f"Usuario: **{u_nom}** | Rol: **{u_rol}**")
            with st.form("c_pass"):
                new_p = st.text_input("Nueva Contraseña", type="password")
                conf_p = st.text_input("Confirmar", type="password")
                if st.form_submit_button("Actualizar Clave"):
                    if new_p == conf_p and new_p != "":
                        conn = get_db_connection()
                        conn.execute("UPDATE usuarios SET password=? WHERE user=?", (new_p, u_id))
                        conn.commit(); conn.close(); st.success("Contraseña actualizada.")
                    else: st.error("Las claves no coinciden.")

        if st.sidebar.button("Cerrar Sesión"):
            conn = get_db_connection()
            conn.execute("UPDATE usuarios SET online='OFFLINE' WHERE user=?", (u_id,))
            conn.commit(); conn.close(); st.session_state.auth = False; st.rerun()