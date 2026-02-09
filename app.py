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
        
        # NORMALIZAÇÃO: Remove espaços e coloca tudo em minúsculo para comparar sem erro
        df['responsavel_limpo'] = df['responsavel'].astype(str).str.strip().str.lower()
        
        # --- FILTRO DE SEGURANÇA BLINDADO ---
        if st.session_state.get('role') != 'Administrador':
            # Se não for você (Willian), ela só vê o que está no nome dela (independente de maiúsculo/minúsculo)
            usuario_logado = str(st.session_state.get('user')).strip().lower()
            df = df[df['responsavel_limpo'] == usuario_logado].copy()
            
        return df
    except: return pd.DataFrame()

def salvar_tarefa(titulo, desc, resp, d_prazo, h_prazo, criador, recorrencia="Única"):
    try:
        aba = conectar_google("Página1")
        novo_id = str(uuid.uuid4())[:8]
        # Coluna de Recorrência é a última (índice 11 na planilha se seguir a estrutura)
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
            status_p = aba.cell(row, 7).value or ""
            aba.update_cell(row, 7, f"[{agora.strftime('%d/%m %H:%M')}]: {novo_comentario}\n{status_p}")
        if status_final:
            status_p = aba.cell(row, 7).value or ""
            aba.update_cell(row, 7, f"--- {status_final.upper()} em {agora.strftime('%d/%m')} ---\n{status_p}")
        if responsavel: aba.update_cell(row, 4, responsavel)
        if nova_data: aba.update_cell(row, 5, str(nova_data))
        return True
    except: return False

# --- LÓGICA DE NAVEGAÇÃO ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align:center;'>🙏 Tarefas Diárias</h1>", unsafe_allow_html=True)
    u = st.text_input("Usuário").strip()
    s = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        # DEFINE QUEM É ADMIN E QUEM É APRENDIZ
        role = 'Administrador' if u.lower() == 'willian' else 'Aprendiz'
        st.session_state.update({'logged_in': True, 'user': u, 'role': role, 'page': 'home'})
        st.rerun()
else:
    # MENU
    cols = st.columns(5)
    labels = ["🏠 Início", "📝 Agendar", "📋 Missões", "📊 Relatório", "👤 Sair"]
    pages = ['home', 'add', 'list', 'report', 'profile']
    for i, l in enumerate(labels):
        if cols[i].button(l): 
            if i == 4: st.session_state.clear(); st.rerun()
            st.session_state['page'] = pages[i]

    df_geral = carregar_tarefas()

    # --- PÁGINA: HOME ---
    if st.session_state['page'] == 'home':
        st.title(f"☀️ Bom dia, {st.session_state['user']}!")
        hoje = obter_agora_br().strftime('%Y-%m-%d')
        if not df_geral.empty:
            df_hoje = df_geral[(df_geral['data_prazo'].astype(str) == hoje) & (~df_geral['status'].str.contains('CONCLUÍDO', case=False, na=False))]
            for _, r in df_hoje.iterrows():
                st.markdown(f"<div class='card-tarefa'><h4>🕒 {r['hora_prazo']} - {r['titulo']}</h4></div>", unsafe_allow_html=True)
        else: st.info("Tudo em ordem por hoje!")

    # --- PÁGINA: AGENDAR (RECORRÊNCIA VOLTOU!) ---
    elif st.session_state['page'] == 'add':
        st.title("📝 Agendar Missão")
        with st.form("ag"):
            t = st.text_input("Título")
            d = st.text_area("Descrição")
            resp = st.selectbox("Responsável", ["Willian", "Aprendiz"])
            dt_p = st.date_input("Data", date.today())
            hr_p = st.time_input("Hora", time(9,0))
            # CAMPO DE RECORRÊNCIA RESTAURADO
            recor = st.selectbox("Recorrência", ["Única", "Diário", "Semanal", "Mensal"])
            if st.form_submit_button("Agendar"):
                if salvar_tarefa(t, d, resp, dt_p, hr_p, st.session_state['user'], recor):
                    st.success(f"Missão {recor} agendada!")
                    t_time.sleep(1); st.rerun()

    # --- PÁGINA: MISSÕES (COM BOTÃO ADIAR) ---
    elif st.session_state['page'] == 'list':
        st.title("📋 Minhas Missões")
        if not df_geral.empty:
            df_vivas = df_geral[~df_geral['status'].str.contains('CONCLUÍDO', case=False, na=False)]
            for _, row in df_vivas.iterrows():
                with st.expander(f"📌 {row['titulo']} ({row['data_prazo']})"):
                    st.write(f"**Descrição:** {row['descricao']}")
                    st.markdown(f"<div class='hist-box'>{row['status']}</div>", unsafe_allow_html=True)
                    
                    # Botões de Ação
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        if st.button("✅ Concluir", key=f"c_{row['id']}"):
                            atualizar_tarefa_planilha(row['id'], status_final='Concluído')
                            st.rerun()
                    with c2:
                        n_dt = st.date_input("Adiar para:", value=date.today()+timedelta(days=1), key=f"dt_{row['id']}")
                        if st.button("📅 Adiar", key=f"a_{row['id']}"):
                            atualizar_tarefa_planilha(row['id'], status_final='Adiado', nova_data=n_dt)
                            st.rerun()
                    with c3:
                        target = "Aprendiz" if st.session_state['role'] == 'Administrador' else "Willian"
                        if st.button(f"➡️ Para {target}", key=f"m_{row['id']}"):
                            atualizar_tarefa_planilha(row['id'], responsavel=target, novo_comentario=f"Enviado para {target}")
                            st.rerun()

    # --- PÁGINA: RELATÓRIO ---
    elif st.session_state['page'] == 'report':
        st.title("📊 Relatório de Concluídos")
        if not df_geral.empty:
            df_hist = df_geral[df_geral['status'].str.contains('CONCLUÍDO', case=False, na=False)]
            st.dataframe(df_hist[['data_prazo', 'titulo', 'responsavel', 'status']], use_container_width=True)
