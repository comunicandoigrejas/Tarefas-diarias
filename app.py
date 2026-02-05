import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date, time, timedelta
import time as t_time
import uuid

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Tarefas Diárias - Comunicando Igrejas", layout="wide", page_icon="📅")

# --- ESTILO VISUAL (Roxo, Azul, Verde, Laranja e Amarelo) ---
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

def carregar_tarefas():
    try:
        aba = conectar_google("Página1")
        dados = aba.get_all_records()
        if not dados:
            return pd.DataFrame(columns=['id', 'titulo', 'descricao', 'responsavel', 'data_prazo', 'hora_prazo', 'status', 'observacoes', 'motivo_adiamento', 'criado_por', 'recorrencia'])
        df = pd.DataFrame(dados)
        df.columns = [c.strip().lower() for c in df.columns]
        
        # Limpeza forçada de dados para garantir o filtro
        df['responsavel'] = df['responsavel'].astype(str).str.strip()
        df['status'] = df['status'].astype(str).str.strip()
        
        # --- AQUI É A TRAVA DE SEGURANÇA MÁXIMA ---
        if st.session_state.get('role') == 'Padrão':
            nome_usuario = str(st.session_state.get('user')).strip()
            # Filtra o DataFrame para conter APENAS as tarefas dela antes de mostrar qualquer coisa
            df = df[df['responsavel'].str.lower() == nome_usuario.lower()].copy()
            
        return df
    except: return pd.DataFrame()

def atualizar_tarefa_planilha(id_t, status, n_data=""):
    try:
        aba = conectar_google("Página1")
        celula = aba.find(str(id_t))
        row = celula.row
        aba.update_cell(row, 7, status) # Coluna Status
        if n_data:
            aba.update_cell(row, 5, str(n_data)) # Coluna Data
    except: pass

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
    st.markdown("<h1 style='text-align:center;'>🙏 Comunicando Igrejas</h1>", unsafe_allow_html=True)
    with st.container():
        u = st.text_input("Usuário")
        s = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            user_data = validar_login(u, s)
            if user_data:
                st.session_state.update({
                    'logged_in': True, 
                    'user': user_data['nome'], 
                    'role': user_data['perfil'], 
                    'page': 'home'
                })
                st.rerun()
            else: st.error("Erro no login.")
else:
    # Navegação
    col1, col2, col3, col4 = st.columns(4)
    with col1: 
        if st.button("🏠 Início"): st.session_state['page'] = 'home'
    with col2: 
        if st.button("📝 Agendar"): st.session_state['page'] = 'add'
    with col3: 
        if st.button("📋 Pendências"): st.session_state['page'] = 'list'
    with col4: 
        if st.button("🚪 Sair"): 
            st.session_state.clear()
            st.rerun()

    # Carrega as tarefas (já filtradas pela função carregar_tarefas caso seja aprendiz)
    df_geral = carregar_tarefas()

    # --- PÁGINA: HOME ---
    if st.session_state['page'] == 'home':
        st.title("☀️ Missões de Hoje")
        hoje = date.today().strftime('%Y-%m-%d')
        df_hoje = df_geral[(df_geral['status'].isin(['Pendente', 'Adiado'])) & (df_geral['data_prazo'].astype(str) == hoje)]
        
        if not df_hoje.empty:
            for _, row in df_hoje.iterrows():
                st.markdown(f"<div class='card-tarefa'><h4 style='color:yellow;'>🕒 {row['hora_prazo']} - {row['titulo']}</h4><p>Responsável: {row['responsavel']}</p></div>", unsafe_allow_html=True)
        else:
            st.success("Glória a Deus! Tudo em ordem para hoje.")

    # --- PÁGINA: AGENDAR ---
    elif st.session_state['page'] == 'add':
        st.title("📝 Agendar")
        with st.form("add_tarefa"):
            titulo = st.text_input("Missão")
            desc = st.text_area("Descrição")
            if st.session_state['role'] == 'Administrador':
                resp = st.selectbox("Para quem?", ["Willian", "Aprendiz"])
            else:
                resp = st.session_state['user']
            dt = st.date_input("Data", date.today())
            hr = st.time_input("Hora", time(9,0))
            if st.form_submit_button("Salvar"):
                if salvar_tarefa(titulo, desc, resp, dt, hr, st.session_state['user']):
                    st.success("Agendado!")
                    st.rerun()

    # --- PÁGINA: PENDÊNCIAS ---
    elif st.session_state['page'] == 'list':
        st.title("📋 Minhas Pendências")
        df_p = df_geral[df_geral['status'].isin(['Pendente', 'Adiado'])]
        
        if df_p.empty:
            st.info("Nenhuma pendência encontrada.")
        else:
            for _, row in df_p.iterrows():
                with st.expander(f"📌 {row['titulo']} ({row['data_prazo']})"):
                    st.write(f"Descrição: {row['descricao']}")
                    # Se for Admin, mostra botão de delegar, se não apenas concluir
                    if st.button("✅ Concluir", key=f"c_{row['id']}"):
                        atualizar_tarefa_planilha(row['id'], 'Concluído')
                        st.rerun()
                    
                    if st.button("📅 Adiar p/ Amanhã", key=f"a_{row['id']}"):
                        nova = date.today() + timedelta(days=1)
                        atualizar_tarefa_planilha(row['id'], 'Adiado', n_data=nova)
                        st.rerun()

                    if st.session_state['role'] == 'Administrador':
                        if st.button("➡️ Enviar para Aprendiz", key=f"d_{row['id']}"):
                            aba = conectar_google("Página1")
                            cel = aba.find(str(row['id']))
                            aba.update_cell(cel.row, 4, "Aprendiz")
                            st.rerun()
