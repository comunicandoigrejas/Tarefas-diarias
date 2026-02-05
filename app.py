import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date, time, timedelta
import time as t_time
import uuid

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Tarefas Diárias", layout="wide", page_icon="📅")

# --- ESTILO VISUAL DE ALTO CONTRASTE ---
st.markdown("""
    <style>
    .stApp { background-color: #1E0032; }
    h1, h2, h3, p, span, label, .stMarkdown { color: #FFFFFF !important; }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        background-color: #ffffff !important; color: #000000 !important;
    }
    .stButton>button {
        background-color: #0000FF !important; color: white !important; 
        border: 2px solid #ffffff; border-radius: 10px; font-weight: bold; width: 100%;
    }
    .stButton>button:hover { background-color: #FFA500 !important; color: black !important; }
    .atraso-card { background-color: #FF4500; color: white; padding: 15px; border-radius: 10px; border: 2px solid yellow; }
    .em-dia-card { background-color: #32CD32; color: white; padding: 15px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- CONEXÃO COM GOOGLE SHEETS ---
def conectar_google(aba_nome):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("Tarefas Diarias DB").worksheet(aba_nome)
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        st.stop()

# --- FUNÇÕES DE LOGIN ---
def validar_login(user_input, pass_input):
    try:
        aba = conectar_google("Usuarios")
        df_users = pd.DataFrame(aba.get_all_records())
        df_users.columns = [c.strip().lower() for c in df_users.columns]
        user_row = df_users[(df_users['usuario'].astype(str) == str(user_input)) & 
                               (df_users['senha'].astype(str) == str(pass_input))]
        if not user_row.empty:
            return user_row.iloc[0].to_dict()
        return None
    except:
        return None

# --- FUNÇÕES DE TAREFAS ---
def carregar_tarefas():
    try:
        aba = conectar_google("Página1")
        dados = aba.get_all_records()
        if not dados:
            return pd.DataFrame(columns=['id', 'titulo', 'descricao', 'responsavel', 'data_prazo', 'hora_prazo', 'status', 'observacoes', 'motivo_adiamento', 'criado_por', 'recorrencia'])
        df = pd.DataFrame(dados)
        df.columns = [c.strip().lower() for c in df.columns]
        return df
    except:
        return pd.DataFrame()

def salvar_tarefa(titulo, desc, resp, d_prazo, h_prazo, criador, recorrencia="Única"):
    try:
        aba = conectar_google("Página1")
        novo_id = str(uuid.uuid4())[:8]
        nova_linha = [novo_id, titulo, desc, resp, str(d_prazo), str(h_prazo), 'Pendente', '', '', criador, recorrencia]
        aba.append_row(nova_linha)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

def atualizar_tarefa_planilha(id_t, status, obs="", motivo="", n_data="", n_hora=""):
    aba = conectar_google("Página1")
    celula = aba.find(str(id_t))
    row = celula.row
    aba.update_cell(row, 7, status)
    if status == 'Concluído':
        aba.update_cell(row, 8, obs)
    elif status == 'Adiado':
        aba.update_cell(row, 9, motivo)
        aba.update_cell(row, 5, str(n_data))
        aba.update_cell(row, 6, str(n_hora))

# --- INTERFACE DE LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align:center;'>🙏 Tarefas Diárias</h1>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        u = st.text_input("Usuário")
        s = st.text_input("Senha", type="password")
        if st.button("Entrar no Sistema"):
            user_data = validar_login(u, s)
            if user_data:
                st.session_state.update({'logged_in': True, 'user': user_data['nome'], 'role': user_data['perfil'], 'page': 'home'})
                st.rerun()
            else: st.error("Credenciais inválidas. Vigiai!")

# --- APP LOGADO ---
else:
    st.sidebar.markdown(f"### Olá, **{st.session_state['user']}**")
    if st.sidebar.button("Sair"):
        st.session_state['logged_in'] = False
        st.rerun()

    col1, col2, col3, col4 = st.columns(4)
    with col1: 
        if st.button("🏠 Início"): st.session_state['page'] = 'home'
    with col2: 
        if st.button("📝 Agendar"): st.session_state['page'] = 'add'
    with col3: 
        if st.button("📋 Pendências"): st.session_state['page'] = 'list'
    with col4: 
        if st.button("📊 Concluídas"): st.session_state['page'] = 'report'

    # --- PÁGINA: HOME ---
    if st.session_state['page'] == 'home':
        st.title("🔔 Avisos do Dia")
        df = carregar_tarefas()
        if not df.empty and 'status' in df.columns:
            df_p = df[df['status'].isin(['Pendente', 'Adiado'])].copy()
            if not df_p.empty:
                df_p['data_hora'] = pd.to_datetime(df_p['data_prazo'].astype(str) + ' ' + df_p['hora_prazo'].astype(str), errors='coerce')
                atrasadas = df_p[df_p['data_hora'] < datetime.now()]
                if st.session_state['role'] == 'Padrão':
                    atrasadas = atrasadas[atrasadas['responsavel'] == st.session_state['user']]
                if not atrasadas.empty:
                    st.markdown(f"<div class='atraso-card'>⚠️ ATENÇÃO: {len(atrasadas)} Tarefas Atrasadas!</div>", unsafe_allow_html=True)
                else: st.markdown("<div class='em-dia-card'>✅ Tudo em ordem!</div>", unsafe_allow_html=True)
            else: st.markdown("<div class='em-dia-card'>✅ Nenhuma pendência.</div>", unsafe_allow_html=True)

    # --- PÁGINA: AGENDAR ---
    elif st.session_state['page'] == 'add':
        st.title("📝 Novo Agendamento")
        with st.form("form_add", clear_on_submit=True):
            titulo = st.text_input("Título")
            desc = st.text_area("Descrição")
            resp = st.selectbox("Responsável", ["Willian", "Aprendiz"]) if st.session_state['role'] == 'Administrador' else st.session_state['user']
            c1, c2, c3 = st.columns(3)
            d_p = c1.date_input("Data", date.today())
            h_p = c2.time_input("Hora", time(9, 0))
            tipo_rec = c3.selectbox("Frequência", ["Única", "Diário"])
            if st.form_submit_button("Agendar"):
                if titulo:
                    if salvar_tarefa(titulo, desc, resp, d_p, h_p, st.session_state['user'], tipo_rec):
                        st.success("Tarefa registrada!")
                else: st.error("O título é obrigatório.")

    # --- PÁGINA: PENDÊNCIAS ---
    elif st.session_state['page'] == 'list':
        st.title("📋 Pendências")
        df = carregar_tarefas()
        if not df.empty and 'status' in df.columns:
            df_pend = df[df['status'].isin(['Pendente', 'Adiado'])]
            if st.session_state['role'] == 'Padrão':
                df_pend = df_pend[df_pend['responsavel'] == st.session_state['user']]
            
            for _, row in df_pend.iterrows():
                with st.expander(f"📌 {row['titulo']} ({row['data_prazo']})"):
                    st.write(f"**Frequência:** {row.get('recorrencia', 'Única')}")
                    c1, c2 = st.columns(2)
                    with c1:
                        with st.form(f"f_c_{row['id']}"):
                            o = st.text_area("Observações")
                            if st.form_submit_button("✅ Concluir"):
                                atualizar_tarefa_planilha(row['id'], 'Concluído', obs=o)
                                if row.get('recorrencia') == "Diário":
                                    proxima = pd.to_datetime(row['data_prazo']) + timedelta(days=1)
                                    salvar_tarefa(row['titulo'], row['descricao'], row['responsavel'], proxima.date(), row['hora_prazo'], st.session_state['user'], "Diário")
                                st.rerun()
                    with c2:
                        with st.form(f"f_a_{row['id']}"):
                            nd = st.date_input("Nova Data")
                            mot = st.text_input("Motivo")
                            if st.form_submit_button("📅 Adiar"):
                                if mot:
                                    atualizar_tarefa_planilha(row['id'], 'Adiado', motivo=mot, n_data=nd)
                                    st.rerun()

    # --- PÁGINA: REPORT ---
    elif st.session_state['page'] == 'report':
        st.title("📊 Relatório")
        df = carregar_tarefas()
        if not df.empty and 'status' in df.columns:
            df_c = df[df['status'] == 'Concluído']
            if st.session_state['role'] == 'Padrão':
                df_c = df_c[df_c['responsavel'] == st.session_state['user']]
            st.dataframe(df_c, use_container_width=True)
            csv = df_c.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Baixar CSV", csv, "relatorio.csv", "text/csv")
