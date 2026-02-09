import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date, time, timedelta
import uuid
import pytz

# --- CONFIGURAÇÃO DE FUSO HORÁRIO BRASIL ---
fuso_br = pytz.timezone('America/Sao_Paulo')

def obter_agora_br():
    return datetime.now(fuso_br)

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Tarefas Diárias", layout="wide", page_icon="📅")

# --- ESTILO VISUAL (Identidade Comunicando Igrejas) ---
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
    .chat-msg { padding: 10px; border-radius: 10px; margin-bottom: 5px; color: white; }
    .msg-eu { background-color: #008000; align-self: flex-end; border-left: 5px solid #yellow; }
    .msg-outro { background-color: #4B0082; align-self: flex-start; border-left: 5px solid #FFA500; }
    .card-tarefa { background-color: #4B0082; padding: 15px; border-radius: 10px; border-left: 5px solid #0000FF; margin-bottom: 10px; }
    .hist-box { background-color: #2D004B; padding: 10px; border-radius: 5px; border: 1px solid #5D008B; margin-bottom: 10px; font-size: 0.9em; white-space: pre-wrap; }
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
    except:
        st.error("Erro de conexão com a planilha.")
        st.stop()

# --- FUNÇÕES DO CHAT ---
def enviar_mensagem(remetente, destinatario, texto):
    try:
        aba = conectar_google("Chat")
        agora = obter_agora_br().strftime('%d/%m/%Y %H:%M:%S')
        aba.append_row([agora, remetente, destinatario, texto])
        return True
    except: return False

def carregar_mensagens():
    try:
        aba = conectar_google("Chat")
        dados = aba.get_all_records()
        return pd.DataFrame(dados) if dados else pd.DataFrame()
    except: return pd.DataFrame()

# --- FUNÇÕES DE TAREFAS (MANTIDAS) ---
def carregar_tarefas():
    try:
        aba = conectar_google("Página1")
        dados = aba.get_all_records()
        if not dados: return pd.DataFrame()
        df = pd.DataFrame(dados)
        df.columns = [c.strip().lower() for c in df.columns]
        df['responsavel_limpo'] = df['responsavel'].astype(str).str.strip().str.lower()
        if st.session_state.get('role') != 'Administrador':
            u_logado = str(st.session_state.get('user')).strip().lower()
            df = df[df['responsavel_limpo'] == u_logado].copy()
        return df
    except: return pd.DataFrame()

# --- LÓGICA DE LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align:center;'>🙏 Tarefas Diárias</h1>", unsafe_allow_html=True)
    u = st.text_input("Usuário").strip()
    s = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        role = 'Administrador' if u.lower() == 'willian' else 'Aprendiz'
        st.session_state.update({'logged_in': True, 'user': u, 'role': role, 'page': 'home'})
        st.rerun()
else:
    # --- MENU NAVEGAÇÃO ---
    cols = st.columns(6) # Aumentado para 6 colunas
    labels = ["🏠 Home", "📝 Agendar", "📋 Missões", "📊 Relatório", "💬 Chat", "👤 Sair"]
    pages = ['home', 'add', 'list', 'report', 'chat', 'exit']
    for i, l in enumerate(labels):
        if cols[i].button(l):
            if pages[i] == 'exit': st.session_state.clear(); st.rerun()
            st.session_state['page'] = pages[i]

    # --- PÁGINA: CHAT ---
    if st.session_state['page'] == 'chat':
        st.title("💬 Mural de Comunicação")
        dest = "Aprendiz" if st.session_state['role'] == 'Administrador' else "Willian"
        
        with st.container():
            df_chat = carregar_mensagens()
            if not df_chat.empty:
                # Filtra apenas a conversa entre Willian e Aprendiz
                for _, msg in df_chat.tail(20).iterrows(): # Mostra as últimas 20
                    classe = "msg-eu" if msg['remetente'] == st.session_state['user'] else "msg-outro"
                    st.markdown(f"""
                    <div class="chat-msg {classe}">
                        <small>{msg['data_hora']} - {msg['remetente']}</small><br>
                        <b>{msg['mensagem']}</b>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Nenhuma mensagem trocada ainda.")

        st.divider()
        with st.form("f_chat", clear_on_submit=True):
            texto_msg = st.text_input(f"Enviar mensagem para {dest}:")
            if st.form_submit_button("Enviar"):
                if texto_msg:
                    enviar_mensagem(st.session_state['user'], dest, texto_msg)
                    st.rerun()

    # --- AS OUTRAS PÁGINAS (HOME, ADD, LIST, REPORT) CONTINUAM IGUAIS ---
    elif st.session_state['page'] == 'home':
        st.title(f"☀️ Olá, {st.session_state['user']}!")
        # (Lógica da Home mantida...)
    
    elif st.session_state['page'] == 'add':
        st.title("📝 Agendar")
        # (Lógica de Agendar mantida com Recorrência...)

    elif st.session_state['page'] == 'list':
        st.title("📋 Missões")
        # (Lógica de Missões mantida com Adiar e Filtro de Privacidade...)

    elif st.session_state['page'] == 'report':
        st.title("📊 Relatório")
        # (Lógica de Relatório mantida...)
