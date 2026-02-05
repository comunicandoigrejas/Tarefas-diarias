import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date, time, timedelta
import time as t_time
import uuid

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Tarefas Diárias", layout="wide", page_icon="📅")

# --- ESTILO VISUAL (Azul, Roxo, Verde, Laranja e Amarelo) ---
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
    .card-tarefa { background-color: #4B0082; padding: 15px; border-radius: 10px; border-left: 5px solid #0000FF; margin-bottom: 10px; }
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

# --- FUNÇÕES DE BANCO DE DADOS ---
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
    except: return None

def atualizar_senha_planilha(login_user, nova_senha):
    try:
        aba = conectar_google("Usuarios")
        celula = aba.find(str(login_user))
        aba.update_cell(celula.row, 3, str(nova_senha))
        return True
    except: return False

def carregar_tarefas():
    try:
        aba = conectar_google("Página1")
        dados = aba.get_all_records()
        if not dados: return pd.DataFrame()
        df = pd.DataFrame(dados)
        df.columns = [c.strip().lower() for c in df.columns]
        df['responsavel'] = df['responsavel'].astype(str).str.strip()
        
        if st.session_state.get('role') != 'Administrador':
            nome_logado = str(st.session_state.get('user')).strip().lower()
            df = df[df['responsavel'].str.lower() == nome_logado].copy()
        return df
    except: return pd.DataFrame()

def atualizar_tarefa_planilha(id_t, status=None, responsavel=None, nova_data=None):
    try:
        aba = conectar_google("Página1")
        celula = aba.find(str(id_t))
        row = celula.row
        if status: aba.update_cell(row, 7, status)
        if responsavel: aba.update_cell(row, 4, responsavel)
        if nova_data: aba.update_cell(row, 5, str(nova_data))
        return True
    except: return False

def salvar_tarefa(titulo, desc, resp, d_prazo, h_prazo, criador):
    try:
        aba = conectar_google("Página1")
        novo_id = str(uuid.uuid4())[:8]
        aba.append_row([novo_id, titulo, desc, resp, str(d_prazo), str(h_prazo), 'Pendente', '', '', criador, 'Única'])
        return True
    except: return False

# --- LÓGICA DE LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align:center;'>🙏 Tarefas Diárias</h1>", unsafe_allow_html=True)
    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        user_data = validar_login(u, s)
        if user_data:
            st.session_state.update({'logged_in': True, 'user': user_data['nome'], 'role': user_data['perfil'], 'login_user': u, 'page': 'home'})
            st.rerun()
else:
    # --- MENU NAVEGAÇÃO ---
    cols_nav = st.columns(4)
    with cols_nav[0]: 
        if st.button("🏠 Início"): st.session_state['page'] = 'home'
    with cols_nav[1]: 
        if st.button("📝 Agendar"): st.session_state['page'] = 'add'
    with cols_nav[2]: 
        if st.button("📋 Missões"): st.session_state['page'] = 'list'
    with cols_nav[3]: 
        if st.button("👤 Perfil"): st.session_state['page'] = 'profile'

    df_geral = carregar_tarefas()

    # --- PÁGINA: HOME ---
    if st.session_state['page'] == 'home':
        st.title(f"☀️ Olá, {st.session_state['user']}!")
        hoje = date.today().strftime('%Y-%m-%d')
        if not df_geral.empty:
            df_hoje = df_geral[(df_geral['status'] != 'Concluído') & (df_geral['data_prazo'].astype(str) == hoje)]
            if not df_hoje.empty:
                for _, row in df_hoje.iterrows():
                    st.markdown(f"<div class='card-tarefa'><h4>🕒 {row['hora_prazo']} - {row['titulo']}</h4><p>Status: {row['status']}</p></div>", unsafe_allow_html=True)
            else:
                st.info("Nenhuma missão para hoje. Glória a Deus!")

    # --- PÁGINA: AGENDAR ---
    elif st.session_state['page'] == 'add':
        st.title("📝 Agendar Missão")
        with st.form("form_add"):
            t = st.text_input("Título")
            d = st.text_area("Descrição")
            lista_resp = ["Willian", "Aprendiz"] if st.session_state['role'] == 'Administrador' else ["Aprendiz", "Willian"]
            r = st.selectbox("Responsável", lista_resp)
            dt = st.date_input("Data", date.today())
            hr = st.time_input("Hora", time(9,0))
            if st.form_submit_button("Confirmar Agendamento"):
                if salvar_tarefa(t, d, r, dt, hr, st.session_state['user']):
                    st.success("Missão registrada!")
                    st.rerun()

    # --- PÁGINA: LISTA DE MISSÕES ---
    elif st.session_state['page'] == 'list':
        st.title("📋 Gestão de Missões")
        if not df_geral.empty:
            df_p = df_geral[df_geral['status'] != 'Concluído']
            if df_p.empty:
                st.info("Nenhuma pendência encontrada.")
            else:
                for _, row in df_p.iterrows():
                    with st.expander(f"📌 {row['titulo']} (Prazo: {row['data_prazo']})"):
                        st.write(f"**Descrição:** {row['descricao']}")
                        
                        # Campo de Status
                        novo_st = st.text_input("Atualizar Status", value=row['status'], key=f"st_{row['id']}")
                        if st.button("Salvar Status", key=f"up_{row['id']}"):
                            atualizar_tarefa_planilha(row['id'], status=novo_st)
                            st.rerun()

                        st.markdown("---")
                        # Botões de Ação
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            if st.button("✅ Concluir", key=f"c_{row['id']}"):
                                atualizar_tarefa_planilha(row['id'], status='Concluído')
                                st.rerun()
                        with c2:
                            # BOTÃO ADIAR TRABALHO
                            nova_data = st.date_input("Nova Data", value=date.today() + timedelta(days=1), key=f"dt_{row['id']}")
                            if st.button("📅 Adiar", key=f"a_{row['id']}"):
                                atualizar_tarefa_planilha(row['id'], status='Adiado', nova_data=nova_data)
                                st.rerun()
                        with c3:
                            destino = "Aprendiz" if st.session_state['role'] == 'Administrador' else "Willian"
                            if st.button(f"➡️ Para {destino}", key=f"d_{row['id']}"):
                                atualizar_tarefa_planilha(row['id'], responsavel=destino)
                                st.rerun()

    # --- PÁGINA: PERFIL ---
    elif st.session_state['page'] == 'profile':
        st.title("👤 Configurações de Perfil")
        st.write(f"Usuário: **{st.session_state['login_user']}**")
        st.markdown("---")
        with st.form("f_senha"):
            st.subheader("Alterar Senha")
            n1 = st.text_input("Nova Senha", type="password")
            n2 = st.text_input("Confirme a Senha", type="password")
            if st.form_submit_button("Salvar Nova Senha"):
                if n1 == n2 and len(n1) >= 4:
                    if atualizar_senha_planilha(st.session_state['login_user'], n1):
                        st.success("Senha atualizada! Use-a no próximo login.")
                else: st.error("Senhas não conferem ou são muito curtas.")
        
        if st.button("🚪 Sair do Sistema"):
            st.session_state.clear()
            st.rerun()
