import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date, time, timedelta
import time as t_time
import uuid
import pytz

# --- CONFIGURAÇÃO DE FUSO HORÁRIO BRASIL ---
fuso_br = pytz.timezone('America/Sao_Paulo')

def obter_agora_br():
    return datetime.now(fuso_br)

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Tarefas Diárias", layout="wide", page_icon="📅")

# --- ESTILO VISUAL (Comunicando Igrejas) ---
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
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        st.stop()

# --- FUNÇÕES DE BANCO DE DADOS ---
def carregar_tarefas():
    try:
        aba = conectar_google("Página1")
        dados = aba.get_all_records()
        if not dados: return pd.DataFrame()
        df = pd.DataFrame(dados)
        df.columns = [c.strip().lower() for c in df.columns]
        df['responsavel'] = df['responsavel'].astype(str).str.strip()
        
        # Filtro de Privacidade: Aprendiz só vê o dela, Admin vê tudo
        if st.session_state.get('role') != 'Administrador':
            nome_logado = str(st.session_state.get('user')).strip()
            df = df[df['responsavel'] == nome_logado].copy()
        return df
    except: return pd.DataFrame()

def salvar_tarefa(titulo, desc, resp, d_prazo, h_prazo, criador, recorrencia="Única"):
    try:
        aba = conectar_google("Página1")
        novo_id = str(uuid.uuid4())[:8]
        aba.append_row([novo_id, titulo, desc, resp, str(d_prazo), str(h_prazo), 'Iniciado', '', '', criador, recorrencia])
        return True
    except: return False

def atualizar_tarefa_planilha(id_t, status_final=None, responsavel=None, nova_data=None, novo_comentario=None):
    try:
        aba = conectar_google("Página1")
        celula = aba.find(str(id_t))
        row = celula.row
        agora = obter_agora_br()
        
        if novo_comentario:
            status_previo = aba.cell(row, 7).value or ""
            data_hora_str = agora.strftime('%d/%m %H:%M')
            aba.update_cell(row, 7, f"[{data_hora_str}]: {novo_comentario}\n{status_previo}")
        
        if status_final:
            status_previo = aba.cell(row, 7).value or ""
            aba.update_cell(row, 7, f"--- {status_final.upper()} em {agora.strftime('%d/%m')} ---\n{status_previo}")
            
        if responsavel: aba.update_cell(row, 4, responsavel)
        if nova_data: aba.update_cell(row, 5, str(nova_data)) # Atualiza a data na planilha
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
        role = 'Administrador' if u.lower() == 'willian' else 'Aprendiz'
        st.session_state.update({'logged_in': True, 'user': u, 'role': role, 'login_user': u, 'page': 'home'})
        st.rerun()
else:
    # --- MENU NAVEGAÇÃO ---
    cols_nav = st.columns(5)
    with cols_nav[0]: 
        if st.button("🏠 Início"): st.session_state['page'] = 'home'
    with cols_nav[1]: 
        if st.button("📝 Agendar"): st.session_state['page'] = 'add'
    with cols_nav[2]: 
        if st.button("📋 Missões"): st.session_state['page'] = 'list'
    with cols_nav[3]: 
        if st.button("📊 Relatório"): st.session_state['page'] = 'report'
    with cols_nav[4]: 
        if st.button("👤 Perfil"): st.session_state['page'] = 'profile'

    df_geral = carregar_tarefas()

    # --- PÁGINA: HOME ---
    if st.session_state['page'] == 'home':
        st.title(f"☀️ Olá, {st.session_state['user']}!")
        hoje_str = obter_agora_br().strftime('%Y-%m-%d')
        if not df_geral.empty:
            df_hoje = df_geral[(df_geral['data_prazo'].astype(str) == hoje_str) & (~df_geral['status'].str.contains('CONCLUÍDO', case=False, na=False))]
            for _, row in df_hoje.iterrows():
                st.markdown(f"<div class='card-tarefa'><h4>🕒 {row['hora_prazo']} - {row['titulo']}</h4></div>", unsafe_allow_html=True)
        else: st.info("Sem demandas para hoje.")

    # --- PÁGINA: AGENDAR ---
    elif st.session_state['page'] == 'add':
        st.title("📝 Agendar Nova Missão")
        with st.form("f_agendar"):
            t = st.text_input("Título da Missão")
            d = st.text_area("Descrição/Detalhes")
            r = st.selectbox("Responsável", ["Willian", "Aprendiz"])
            dt = st.date_input("Data Prazo", date.today())
            hr = st.time_input("Hora Prazo", time(9,0))
            if st.form_submit_button("Confirmar Agendamento"):
                if salvar_tarefa(t, d, r, dt, hr, st.session_state['user']):
                    st.success("Missão agendada!")
                    t_time.sleep(1)
                    st.rerun()

    # --- PÁGINA: MISSÕES (COM BOTÃO ADIAR) ---
    elif st.session_state['page'] == 'list':
        st.title("📋 Missões Ativas")
        if not df_geral.empty:
            df_p = df_geral[~df_geral['status'].str.contains('CONCLUÍDO', case=False, na=False)]
            for _, row in df_p.iterrows():
                label = f" | Resp: {row['responsavel']}" if st.session_state['role'] == 'Administrador' else ""
                with st.expander(f"📌 {row['titulo']} ({row['data_prazo']}){label}"):
                    st.write(f"**Descrição:** {row['descricao']}")
                    st.markdown(f"<div class='hist-box'>{row['status']}</div>", unsafe_allow_html=True)
                    
                    # Atualização de texto
                    nova_att = st.text_input("Atualizar status:", key=f"at_{row['id']}")
                    if st.button("Salvar Status", key=f"ba_{row['id']}"):
                        atualizar_tarefa_planilha(row['id'], novo_comentario=nova_att)
                        st.rerun()
                    
                    st.divider()
                    
                    # Botões de Ação
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("✅ Concluir", key=f"c_{row['id']}"):
                            atualizar_tarefa_planilha(row['id'], status_final='Concluído')
                            st.rerun()
                    
                    with col2:
                        # Seleção de nova data para adiar
                        nova_data_adiar = st.date_input("Nova data:", value=date.today() + timedelta(days=1), key=f"dt_{row['id']}")
                        if st.button("📅 Adiar", key=f"a_{row['id']}"):
                            atualizar_tarefa_planilha(row['id'], status_final='Adiado', nova_data=nova_data_adiar)
                            st.rerun()
                            
                    with col3:
                        dest = "Aprendiz" if st.session_state['role'] == 'Administrador' else "Willian"
                        if st.button(f"➡️ Para {dest}", key=f"mv_{row['id']}"):
                            atualizar_tarefa_planilha(row['id'], responsavel=dest, novo_comentario=f"Direcionado para {dest}")
                            st.rerun()

    # --- PÁGINA: RELATÓRIO ---
    elif st.session_state['page'] == 'report':
        st.title("📊 Relatório de Concluídos")
        if not df_geral.empty:
            df_hist = df_geral[df_geral['status'].str.contains('CONCLUÍDO', case=False, na=False)].copy()
            st.dataframe(df_hist[['data_prazo', 'titulo', 'responsavel', 'descricao', 'status']], use_container_width=True)

    # --- PÁGINA: PERFIL ---
    elif st.session_state['page'] == 'profile':
        if st.button("Sair"):
            st.session_state.clear()
            st.rerun()
