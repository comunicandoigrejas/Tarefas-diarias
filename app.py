import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date, time, timedelta
import time as t_time
import uuid

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Tarefas Diárias - Comunicando Igrejas", layout="wide", page_icon="📅")

# --- ESTILO VISUAL ---
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
        if not dados:
            return pd.DataFrame(columns=['id', 'titulo', 'descricao', 'responsavel', 'data_prazo', 'hora_prazo', 'status', 'observacoes', 'motivo_adiamento', 'criado_por', 'recorrencia'])
        df = pd.DataFrame(dados)
        df.columns = [c.strip().lower() for c in df.columns]
        if 'responsavel' in df.columns:
            df['responsavel'] = df['responsavel'].astype(str).str.strip()
        return df
    except: return pd.DataFrame()

def salvar_tarefa(titulo, desc, resp, d_prazo, h_prazo, criador, recorrencia="Única"):
    try:
        aba = conectar_google("Página1")
        novo_id = str(uuid.uuid4())[:8]
        aba.append_row([novo_id, titulo, desc, resp, str(d_prazo), str(h_prazo), 'Pendente', '', '', criador, recorrencia])
        return True
    except: return False

def atualizar_tarefa_planilha(id_t, status, obs="", motivo="", n_data="", n_hora=""):
    try:
        aba = conectar_google("Página1")
        celula = aba.find(str(id_t))
        row = celula.row
        aba.update_cell(row, 7, status)
        if status == 'Concluído': aba.update_cell(row, 8, obs)
        elif status == 'Adiado':
            aba.update_cell(row, 9, motivo)
            aba.update_cell(row, 5, str(n_data))
            aba.update_cell(row, 6, str(n_hora))
    except: pass

# --- CONTROLE DE ACESSO ---
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
                st.session_state.update({'logged_in': True, 'user': user_data['nome'], 'role': user_data['perfil'], 'login_user': u, 'page': 'home'})
                st.rerun()
            else: st.error("Credenciais incorretas!")

else:
    # Menu Superior
    cols_nav = st.columns(5)
    with cols_nav[0]: 
        if st.button("🏠 Início"): st.session_state['page'] = 'home'
    with cols_nav[1]: 
        if st.button("📝 Agendar"): st.session_state['page'] = 'add'
    with cols_nav[2]: 
        if st.button("📋 Pendências"): st.session_state['page'] = 'list'
    with cols_nav[3]: 
        if st.button("📊 Relatório"): st.session_state['page'] = 'report'
    with cols_nav[4]: 
        if st.button("👤 Perfil"): st.session_state['page'] = 'profile'

    df = carregar_tarefas()

    # --- PÁGINA: HOME ---
    if st.session_state['page'] == 'home':
        st.title("☀️ Missões de Hoje")
        if not df.empty:
            hoje = date.today().strftime('%Y-%m-%d')
            # Filtra o dia
            df_hoje = df[(df['status'].isin(['Pendente', 'Adiado'])) & (df['data_prazo'].astype(str) == hoje)].copy()
            
            # FILTRO DE SEGURANÇA REFORÇADO
            if st.session_state['role'] == 'Padrão':
                # Forçamos o nome do usuário e do responsável a serem texto limpo e minúsculo
                usuario_atual = str(st.session_state['user']).strip().lower()
                df_hoje = df_hoje[df_hoje['responsavel'].astype(str).str.strip().str.lower() == usuario_atual]
            
            if not df_hoje.empty:
                for _, row in df_hoje.iterrows():
                    st.markdown(f"<div class='card-tarefa'><h4 style='color:yellow;'>🕒 {row['hora_prazo']} - {row['titulo']}</h4><p>Responsável: {row['responsavel']}</p></div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='em-dia-card'>✅ Tudo em ordem! Nenhuma missão para hoje.</div>", unsafe_allow_html=True)
    # --- PÁGINA: AGENDAR ---
    elif st.session_state['page'] == 'add':
        st.title("📝 Novo Agendamento")
        with st.form("form_novo"):
            titulo = st.text_input("Título")
            desc = st.text_area("Descrição")
            resp = st.selectbox("Para quem?", ["Willian", "Aprendiz"]) if st.session_state['role'] == 'Administrador' else st.session_state['user']
            c1, c2, c3 = st.columns(3)
            dt = c1.date_input("Data", date.today())
            hr = c2.time_input("Hora", time(9, 0))
            rec = c3.selectbox("Repetir?", ["Única", "Diário"])
            if st.form_submit_button("Agendar"):
                if salvar_tarefa(titulo, desc, resp, dt, hr, st.session_state['user'], rec):
                    st.success("Tarefa registrada!")

    # --- PÁGINA: PENDÊNCIAS ---
   # --- PÁGINA: PENDÊNCIAS ---
    elif st.session_state['page'] == 'list':
        st.title("📋 Gestão de Pendências")
        if not df.empty:
            df_p = df[df['status'].isin(['Pendente', 'Adiado'])].copy()
            
            # FILTRO DE PRIVACIDADE REFORÇADO (AQUI É ONDE ESTAVA VAZANDO)
            if st.session_state['role'] == 'Padrão':
                usuario_atual = str(st.session_state['user']).strip().lower()
                # O filtro abaixo garante que ela só veja se o nome for IGUAL ao dela
                df_p = df_p[df_p['responsavel'].astype(str).str.strip().str.lower() == usuario_atual]
            
            if df_p.empty:
                st.info("Não há pendências registradas para você.")
            else:
                for _, row in df_p.iterrows():
                    with st.expander(f"📌 {row['titulo']} ({row['data_prazo']})"):
                        # ... lógica dos botões de concluir/adiar ...
                        # (O restante do código das colunas que já ajustamos antes)
    # --- PÁGINA: PERFIL ---
    elif st.session_state['page'] == 'profile':
        st.title("👤 Configurações")
        st.write(f"Usuário: **{st.session_state.get('login_user', '---')}**")
        with st.form("f_senha"):
            n_s = st.text_input("Nova Senha", type="password")
            if st.form_submit_button("Alterar Senha"):
                if atualizar_senha_planilha(st.session_state['login_user'], n_s):
                    st.success("Senha atualizada!")
        if st.button("🚪 Sair"):
            st.session_state.clear()
            st.rerun()

    # --- PÁGINA: REPORT ---
    elif st.session_state['page'] == 'report':
        st.title("📊 Relatório")
        if not df.empty:
            df_c = df[df['status'] == 'Concluído']
            if st.session_state['role'] == 'Padrão':
                df_c = df_c[df_c['responsavel'].str.lower() == st.session_state['user'].lower()]
            st.dataframe(df_c)
