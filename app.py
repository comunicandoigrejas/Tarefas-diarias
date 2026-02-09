import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date, time, timedelta
import time as t_time
import uuid
import pytz

# --- CONFIGURAÇÃO DE FUSO HORÁRIO ---
fuso_br = pytz.timezone('America/Sao_Paulo')
def obter_agora_br():
    return datetime.now(fuso_br)

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Comunicando Igrejas - Gestão", layout="wide", page_icon="📅")

# --- ESTILO VISUAL COM CORES SOLICITADAS ---
st.markdown("""
    <style>
    .stApp { background-color: #1E0032; } /* Roxo Escuro */
    h1, h2, h3, p, span, label, .stMarkdown { color: #FFFFFF !important; }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        background-color: #ffffff !important; color: #000000 !important;
    }
    .stButton>button {
        background-color: #0000FF !important; color: white !important; /* Azul */
        border: 2px solid #ffffff; border-radius: 10px; font-weight: bold; width: 100%;
    }
    .stButton>button:hover { background-color: #FFA500 !important; color: black !important; } /* Laranja */
    .card-tarefa { background-color: #4B0082; padding: 15px; border-radius: 10px; border-left: 5px solid #0000FF; margin-bottom: 10px; }
    .hist-box { background-color: #2D004B; padding: 10px; border-radius: 5px; border: 1px solid #5D008B; margin-bottom: 10px; font-size: 0.9em; white-space: pre-wrap; }
    .chat-msg { padding: 10px; border-radius: 10px; margin-bottom: 5px; color: white; }
    .msg-eu { background-color: #006400; align-self: flex-end; border-right: 5px solid #FFFF00; } /* Verde com detalhe Amarelo */
    .msg-outro { background-color: #4B0082; align-self: flex-start; border-left: 5px solid #FFA500; } /* Roxo com detalhe Laranja */
    </style>
""", unsafe_allow_html=True)

# --- CONEXÃO GOOGLE SHEETS ---
def conectar_google(aba_nome):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("Tarefas Diarias DB").worksheet(aba_nome)
    except:
        st.error("Erro de conexão. Verifique os Secrets.")
        st.stop()

# --- FUNÇÕES DE DADOS ---
def carregar_tarefas():
    try:
        aba = conectar_google("Página1")
        df = pd.DataFrame(aba.get_all_records())
        df.columns = [c.strip().lower() for c in df.columns]
        df['responsavel_limpo'] = df['responsavel'].astype(str).str.strip().str.lower()
        if st.session_state.get('role') != 'Administrador':
            u_logado = str(st.session_state.get('user')).strip().lower()
            df = df[df['responsavel_limpo'] == u_logado].copy()
        return df
    except: return pd.DataFrame()

def salvar_tarefa(titulo, desc, resp, d_prazo, h_prazo, criador, recorrencia):
    try:
        aba = conectar_google("Página1")
        aba.append_row([str(uuid.uuid4())[:8], titulo, desc, resp, str(d_prazo), str(h_prazo), 'Iniciado', '', '', criador, recorrencia])
        return True
    except: return False

def atualizar_tarefa(id_t, status_final=None, responsavel=None, nova_data=None, novo_comentario=None):
    try:
        aba = conectar_google("Página1")
        celula = aba.find(str(id_t))
        row = celula.row
        agora = obter_agora_br()
        if novo_comentario:
            s_p = aba.cell(row, 7).value or ""
            aba.update_cell(row, 7, f"[{agora.strftime('%d/%m %H:%M')}]: {novo_comentario}\n{s_p}")
        if status_final:
            s_p = aba.cell(row, 7).value or ""
            aba.update_cell(row, 7, f"--- {status_final.upper()} em {agora.strftime('%d/%m')} ---\n{s_p}")
        if responsavel: aba.update_cell(row, 4, responsavel)
        if nova_data: aba.update_cell(row, 5, str(nova_data))
        return True
    except: return False

# --- LÓGICA DE NAVEGAÇÃO ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align:center;'>🙏 A paz do Senhor</h1>", unsafe_allow_html=True)
    u = st.text_input("Usuário").strip()
    s = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        role = 'Administrador' if u.lower() == 'willian' else 'Aprendiz'
        st.session_state.update({'logged_in': True, 'user': u, 'role': role, 'page': 'home'})
        st.rerun()
else:
    # --- MENU PRINCIPAL (TODAS AS ABAS) ---
    menu = st.columns(6)
    botoes = ["🏠 Início", "📝 Agendar", "📋 Missões", "📊 Relatório", "💬 Chat", "👤 Sair"]
    paginas = ['home', 'add', 'list', 'report', 'chat', 'exit']
    for i, nome_botao in enumerate(botoes):
        if menu[i].button(nome_botao):
            if paginas[i] == 'exit': st.session_state.clear(); st.rerun()
            st.session_state['page'] = paginas[i]

    df_geral = carregar_tarefas()

    # --- PÁGINA: HOME ---
    if st.session_state['page'] == 'home':
        st.title(f"☀️ Bem-vindo, {st.session_state['user']}!")
        hoje = obter_agora_br().strftime('%Y-%m-%d')
        df_hoje = df_geral[(df_geral['data_prazo'].astype(str) == hoje) & (~df_geral['status'].str.contains('CONCLUÍDO', case=False, na=False))]
        if not df_hoje.empty:
            for _, r in df_hoje.iterrows():
                st.markdown(f"<div class='card-tarefa'><h4>🕒 {r['hora_prazo']} - {r['titulo']}</h4></div>", unsafe_allow_html=True)
        else: st.success("Nenhuma pendência para hoje!")

    # --- PÁGINA: AGENDAR ---
    elif st.session_state['page'] == 'add':
        st.title("📝 Nova Missão")
        with st.form("form_add"):
            t = st.text_input("Título")
            d = st.text_area("Descrição")
            r = st.selectbox("Responsável", ["Willian", "Aprendiz"])
            dt = st.date_input("Data", date.today())
            hr = st.time_input("Hora", time(9,0))
            recor = st.selectbox("Recorrência", ["Única", "Diário", "Semanal", "Mensal"])
            if st.form_submit_button("Agendar"):
                if salvar_tarefa(t, d, r, dt, hr, st.session_state['user'], recor):
                    st.success("Salvo com sucesso!"); t_time.sleep(1); st.rerun()

    # --- PÁGINA: MISSÕES ---
    elif st.session_state['page'] == 'list':
        st.title("📋 Minhas Missões")
        df_vivas = df_geral[~df_geral['status'].str.contains('CONCLUÍDO', case=False, na=False)]
        for _, row in df_vivas.iterrows():
            with st.expander(f"📌 {row['titulo']} ({row['data_prazo']})"):
                st.markdown(f"<div class='hist-box'>{row['status']}</div>", unsafe_allow_html=True)
                nova_att = st.text_input("Atualizar:", key=f"att_{row['id']}")
                if st.button("Salvar Status", key=f"btn_{row['id']}"):
                    atualizar_tarefa(row['id'], novo_comentario=nova_att); st.rerun()
                c1, c2, c3 = st.columns(3)
                with c1: 
                    if st.button("✅ Concluir", key=f"c_{row['id']}"):
                        atualizar_tarefa(row['id'], status_final='Concluído'); st.rerun()
                with c2:
                    adiar_p = st.date_input("Adiar p/:", value=date.today()+timedelta(days=1), key=f"dt_{row['id']}")
                    if st.button("📅 Adiar", key=f"a_{row['id']}"):
                        atualizar_tarefa(row['id'], status_final='Adiado', nova_data=adiar_p); st.rerun()
                with c3:
                    dest = "Aprendiz" if st.session_state['role'] == 'Administrador' else "Willian"
                    if st.button(f"➡️ Para {dest}", key=f"m_{row['id']}"):
                        atualizar_tarefa(row['id'], responsavel=dest, novo_comentario=f"Enviado para {dest}"); st.rerun()

    # --- PÁGINA: RELATÓRIO ---
    elif st.session_state['page'] == 'report':
        st.title("📊 Histórico de Missões")
        df_hist = df_geral[df_geral['status'].str.contains('CONCLUÍDO', case=False, na=False)]
        st.dataframe(df_hist[['data_prazo', 'titulo', 'responsavel', 'status']], use_container_width=True)

    # --- PÁGINA: CHAT ---
    elif st.session_state['page'] == 'chat':
        st.title("💬 Chat Comunicando Igrejas")
        try:
            aba_chat = conectar_google("Chat")
            df_c = pd.DataFrame(aba_chat.get_all_records())
            for _, msg in df_c.tail(15).iterrows():
                classe = "msg-eu" if msg['remetente'] == st.session_state['user'] else "msg-outro"
                st.markdown(f"<div class='chat-msg {classe}'><small>{msg['remetente']}</small><br>{msg['mensagem']}</div>", unsafe_allow_html=True)
        except: st.info("Crie a aba 'Chat' na planilha para ativar.")
        with st.form("chat_f", clear_on_submit=True):
            txt = st.text_input("Mensagem:")
            if st.form_submit_button("Enviar"):
                if txt:
                    conectar_google("Chat").append_row([obter_agora_br().strftime('%d/%m %H:%M'), st.session_state['user'], "Todos", txt])
                    st.rerun()
