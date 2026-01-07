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

        # --- DASHBOARD ---
        if mod == "📊 Dashboard":
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
                    st.plotly_chart(px.pie(df, names='status', title="Estatus", hole=0.4), use_container_width=True)
                with col2:
                    res_ent = df['entregado_a'].value_counts().reset_index()
                    res_ent.columns = ['Personal', 'Cantidad']
                    st.plotly_chart(px.bar(res_ent, x='Personal', y='Cantidad', title="Carga de Trabajo"), use_container_width=True)
            else: st.info("Sin datos para gráficas.")

        # --- REGISTRO ---
        elif mod == "📥 Nuevo Folio (IA)":
            st.title("📥 Registro de Documentos")
            if 'ia_data' not in st.session_state:
                st.session_state.ia_data = {"folio":"", "cuenta":"", "sicamdtr":"", "ext":"", "dep":"", "asunto":""}
            
            conn = get_db_connection()
            lista_95 = [r['nombre'] for r in conn.execute("SELECT nombre FROM usuarios ORDER BY nombre ASC").fetchall()]
            conn.close()

            with st.form("nuevo_registro"):
                c1, c2 = st.columns(2)
                with c1:
                    ni1=st.text_input("Folio", value=st.session_state.ia_data["folio"]); ni2=st.text_input("Cuenta", value=st.session_state.ia_data["cuenta"])
                    ni3=st.text_input("SICAMDTR", value=st.session_state.ia_data["sicamdtr"]); ni4=st.text_input("Folio Ext", value=st.session_state.ia_data["ext"])
                    ni5=st.text_input("Dependencia", value=st.session_state.ia_data["dep"]); ni6=st.text_area("Asunto", value=st.session_state.ia_data["asunto"])
                    ni7=st.text_input("Ubicación Predio"); ni8=st.text_input("Fecha", value=str(date.today()))
                with c2:
                    ni9=st.selectbox("Área", AREAS)
                    ni10=st.selectbox("Asignado a", lista_95)
                    ni11=st.selectbox("Recibe / Investiga", [""] + lista_95)
                    ni12=st.selectbox("Estatus", ["PENDIENTE", "EN PROCESO"]); ni13=st.text_area("Seguimiento")
                    ni14=st.text_input("Ubicación Física"); ni15=st.text_input("Firma"); ni16=st.text_input("Capturista", value=u_nom, disabled=True)
                
                f_save = st.form_submit_button("💾 Guardar Registro")

            st.divider()
            st.subheader("🤖 Asistente IA (Opcional)")
            foto_cap = st.camera_input("Capturar Oficio")
            if foto_cap and st.button("🤖 Analizar con IA"):
                img = Image.open(foto_cap)
                response = model.generate_content(["Analiza: Folio, Cuenta, SICAMDTR, Externo, Dependencia, Asunto. Formato F:x|C:x|S:x|E:x|D:x|A:x", img])
                res = response.text.split("|")
                st.session_state.ia_data = {"folio": res[0].split(":")[1], "cuenta": res[1].split(":")[1], "sicamdtr": res[2].split(":")[1], "ext": res[3].split(":")[1], "dep": res[4].split(":")[1], "asunto": res[5].split(":")[1]}
                st.rerun()

            if f_save:
                img_bytes = foto_cap.getvalue() if foto_cap else None
                conn = get_db_connection()
                conn.execute("INSERT INTO correspondencia VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (ni1, ni2, ni3, ni4, ni5, ni6, ni7, ni8, ni9, ni10, ni11, ni12, ni13, ni14, ni15, ni16, img_bytes))
                conn.commit(); conn.close(); st.success("Guardado"); st.rerun()

        # --- REGISTRO MAESTRO ---
        elif mod == "📑 Registro Maestro":
            st.title("📑 Gestión de Folios")
            conn = get_db_connection()
            tab_turnar, tab_editar, tab_admin = st.tabs(["🔄 Turnar", "📝 Ver/Editar Datos", "⚙️ Administración"])
            
            lista_95 = [r['nombre'] for r in conn.execute("SELECT nombre FROM usuarios ORDER BY nombre ASC").fetchall()]
            df_folios = pd.read_sql_query("SELECT folio_dir FROM correspondencia", conn)
            lista_f = [""] + df_folios['folio_dir'].tolist()
            
            with tab_turnar:
                sel_t = st.selectbox("Folio Base:", lista_f, key="s_t")
                if sel_t:
                    d_t = conn.execute("SELECT * FROM correspondencia WHERE folio_dir=?", (sel_t,)).fetchone()
                    ct1, ct2 = st.columns(2)
                    with ct1:
                        nt_depto = st.selectbox("Turnar a:", AREAS); nt_status = st.selectbox("Estatus:", ["PENDIENTE", "EN PROCESO"])
                    with ct2:
                        nt_pers = st.selectbox("Asignado a (Personal):", lista_95)
                    if st.button("Confirmar Turnado"):
                        base = sel_t.split("-")[0]
                        count = conn.execute("SELECT COUNT(*) FROM correspondencia WHERE folio_dir LIKE ?", (f"{base}-%",)).fetchone()[0]
                        letras = ["A", "B", "C", "D", "E", "F", "G"]
                        n_folio = f"{base}-{letras[count]}" if count < len(letras) else f"{base}-Z"
                        conn.execute("INSERT INTO correspondencia VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                     (n_folio, d_t['cuenta'], d_t['sicamdtr'], d_t['folio_ext'], d_t['dependencia'], d_t['asunto'], d_t['nombre_ubica'], d_t['fecha_ingreso'], nt_depto, nt_pers, d_t['recibe_investiga'], nt_status, d_t['seguimiento'], d_t['ubicacion_fisica'], d_t['quien_firma'], u_nom, d_t['foto']))
                        conn.commit(); st.success(f"Creado: {n_folio}"); st.rerun()

            with tab_editar:
                sel_e = st.selectbox("Seleccione Folio para Editar:", lista_f, key="s_e")
                if sel_e:
                    d = conn.execute("SELECT * FROM correspondencia WHERE folio_dir=?", (sel_e,)).fetchone()
                    with st.form("form_edit"):
                        col_a, col_b = st.columns(2)
                        with col_a:
                            e1=st.text_input("Folio", d['folio_dir']); e2=st.text_input("Cuenta", d['cuenta']); e3=st.text_input("SICAMDTR", d['sicamdtr'])
                            e4=st.text_input("Externo", d['folio_ext']); e5=st.text_input("Dependencia", d['dependencia']); e6=st.text_area("Asunto", d['asunto'])
                            e7=st.text_input("Predio", d['nombre_ubica']); e8=st.text_input("Fecha", d['fecha_ingreso'])
                        with col_b:
                            e9=st.selectbox("Área", AREAS, index=AREAS.index(d['departamento']))
                            e10=st.selectbox("Asignado", lista_95, index=lista_95.index(d['entregado_a']) if d['entregado_a'] in lista_95 else 0)
                            e11=st.selectbox("Investiga", lista_95, index=lista_95.index(d['recibe_investiga']) if d['recibe_investiga'] in lista_95 else 0)
                            e12=st.selectbox("Estatus", ["PENDIENTE", "EN PROCESO", "FINALIZADO"], index=0); e13=st.text_area("Seguimiento", d['seguimiento'])
                            e14=st.text_input("Ubi. Física", d['ubicacion_fisica']); e15=st.text_input("Firma", d['quien_firma']); e16=st.text_input("Capturista", d['capturista'], disabled=True)
                        if st.form_submit_button("📝 Actualizar Todo"):
                            conn.execute("UPDATE correspondencia SET folio_dir=?, cuenta=?, sicamdtr=?, folio_ext=?, dependencia=?, asunto=?, nombre_ubica=?, fecha_ingreso=?, departamento=?, entregado_a=?, recibe_investiga=?, status=?, seguimiento=?, ubicacion_fisica=?, quien_firma=? WHERE folio_dir=?", 
                                         (e1,e2,e3,e4,e5,e6,e7,e8,e9,e10,e11,e12,e13,e14,e15,sel_e))
                            conn.commit(); st.success("Actualizado"); st.rerun()

            with tab_admin:
                if u_rol in ['Director', 'Administradora']:
                    sel_del = st.selectbox("❌ Eliminar Folio:", lista_f, key="s_del")
                    if sel_del and st.button("⚠️ BORRAR DEFINITIVAMENTE"):
                        conn.execute("DELETE FROM correspondencia WHERE folio_dir=?", (sel_del,))
                        conn.commit(); st.warning("Folio Eliminado"); st.rerun()
                else: st.info("Acceso solo para administradores")

            st.dataframe(pd.read_sql_query("SELECT * FROM correspondencia", conn).drop(columns=['foto'], errors='ignore'))
            conn.close()

        # --- MONITOR DE PERSONAL (ACTUALIZADO VISUALMENTE) ---
        elif mod == "👥 Monitor de Personal":
            st.title("👥 Monitor de Estatus del Personal")
            conn = get_db_connection()
            # Obtenemos todos los usuarios
            df_users = pd.read_sql_query("SELECT nombre, depto, rol, online FROM usuarios ORDER BY nombre", conn)
            
            col_on, col_off = st.columns(2)
            
            with col_on:
                st.success(f"🟢 En Línea ({len(df_users[df_users['online'] == 'ONLINE'])})")
                st.dataframe(df_users[df_users['online'] == 'ONLINE'][['nombre', 'depto']], use_container_width=True)
            
            with col_off:
                st.info(f"🔵 Desconectados ({len(df_users[df_users['online'] != 'ONLINE'])})")
                st.dataframe(df_users[df_users['online'] != 'ONLINE'][['nombre', 'depto']], use_container_width=True)
            conn.close()

        # --- MI PERFIL (POTENCIADO CON FOLIOS Y RANGOS) ---
        elif mod == "👤 Mi Perfil":
            st.title("👤 Mi Perfil")
            st.write(f"**Usuario:** {u_nom} | **Rol:** {u_rol}")
            
            # 1. MIS FOLIOS ASIGNADOS
            st.divider()
            st.subheader("📂 Mis Folios Asignados")
            conn = get_db_connection()
            mis_folios = pd.read_sql_query("SELECT folio_dir, asunto, status, fecha_ingreso FROM correspondencia WHERE entregado_a = ?", conn, params=(u_nom,))
            if not mis_folios.empty:
                st.dataframe(mis_folios, use_container_width=True)
            else:
                st.info("No tienes folios asignados actualmente.")
            
            # 2. CAMBIAR CONTRASEÑA
            st.divider()
            with st.expander("🔑 Cambiar mi Contraseña"):
                new_p = st.text_input("Nueva Clave", type="password")
                conf_p = st.text_input("Confirmar Clave", type="password")
                if st.button("Actualizar Clave"):
                    if new_p == conf_p and new_p != "":
                        conn.execute("UPDATE usuarios SET password=? WHERE user=?", (new_p, u_id))
                        conn.commit(); st.success("Clave cambiada exitosamente.")
                    else: st.error("Las claves no coinciden.")

            # 3. DESCARGAR BASE DE DATOS POR RANGO
            st.divider()
            st.subheader("💾 Descargas Avanzadas")
            
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                # Respaldo Completo
                try:
                    with open("oficialia_v22.db", "rb") as f:
                        st.download_button("📥 Descargar Base Completa (.db)", f, file_name=f"respaldo_{date.today()}.db")
                except: pass
            
            with col_d2:
                # Descarga por Rango
                st.write("**Descargar Reporte por Rango de Folios**")
                r_inicio = st.number_input("Del Folio:", min_value=1, value=1)
                r_fin = st.number_input("Al Folio:", min_value=1, value=100)
                
                if st.button("📥 Generar Excel del Rango"):
                    # Lógica para filtrar folios numéricos (ej. '1' a '100', ignorando letras por ahora para el rango simple)
                    df_all = pd.read_sql_query("SELECT * FROM correspondencia", conn)
                    # Creamos una columna auxiliar numérica para filtrar
                    df_all['num_folio'] = pd.to_numeric(df_all['folio_dir'].str.split('-').str[0], errors='coerce')
                    df_rango = df_all[(df_all['num_folio'] >= r_inicio) & (df_all['num_folio'] <= r_fin)]
                    
                    if not df_rango.empty:
                        # Usamos io para generar el excel en memoria sin librerias extra complejas si es posible, o csv
                        csv = df_rango.drop(columns=['num_folio', 'foto'], errors='ignore').to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Descargar CSV (Excel)",
                            data=csv,
                            file_name=f"reporte_folios_{r_inicio}_al_{r_fin}.csv",
                            mime="text/csv",
                        )
                    else:
                        st.warning("No se encontraron folios en ese rango.")

            if st.button("Cerrar Sesión"):
                conn.execute("UPDATE usuarios SET online='OFFLINE' WHERE user=?", (u_id,))
                conn.commit(); conn.close()
                st.session_state.auth = False; st.rerun()
            
            if 'conn' in locals(): conn.close()

        # --- OTROS MÓDULOS ---
        elif mod == "🚨 Alertas Rápidas":
            st.title("🚨 Alertas"); conn = get_db_connection()
            st.dataframe(pd.read_sql_query("SELECT folio_dir, asunto FROM correspondencia WHERE status='PENDIENTE'", conn)); conn.close()

        elif mod == "✉️ Mensajería":
            st.title("✉️ Chat Interno")
            conn = get_db_connection()
            all_u = pd.read_sql_query("SELECT nombre FROM usuarios WHERE user != ?", conn, params=(u_id,))
            dest = st.selectbox("Para:", all_u['nombre'].tolist())
            txt = st.text_area("Mensaje")
            if st.button("Enviar"):
                conn.execute("INSERT INTO mensajes (remitente, destinatario, texto, fecha) VALUES (?,?,?,?)", (u_nom, dest, txt, str(datetime.now())))
                conn.commit(); st.success("Enviado")
            st.dataframe(pd.read_sql_query("SELECT remitente, texto, fecha FROM mensajes WHERE destinatario = ?", conn, params=(u_nom,)))
            conn.close()