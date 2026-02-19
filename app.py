import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date, time, timedelta
import uuid
import pytz

# --- FUSO HORÁRIO ---
fuso_br = pytz.timezone('America/Sao_Paulo')
def obter_agora_br(): return datetime.now(fuso_br)

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Comunicando Igrejas", layout="wide")

# --- ESTILO VISUAL (Cores solicitadas) ---
st.markdown("""
    <style>
    .stApp { background-color: #1E0032; }
    h1, h2, h3, p, label { color: #FFFFFF !important; }
    .stButton>button { background-color: #0000FF !important; color: white !important; border-radius: 10px; width: 100%; }
    .hist-box { background-color: #2D004B; padding: 10px; border-radius: 5px; border: 1px solid #FFA500; margin-bottom: 10px; color: #FFFFFF; }
    </style>
""", unsafe_allow_html=True)

# --- CONEXÃO SHEETS ---
def conectar_google():
    creds_dict = st.secrets["gcp_service_account"]
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds).open("Tarefas Diarias DB").worksheet("Página1")

# --- FUNÇÕES DE DADOS ---
def carregar_tarefas():
    try:
        aba = conectar_google()
        df = pd.DataFrame(aba.get_all_records())
        if df.empty: return df
        df.columns = [c.strip().lower() for c in df.columns]
        df['data_prazo_dt'] = pd.to_datetime(df['data_prazo'], errors='coerce')
        df = df.sort_values(by=['data_prazo_dt', 'hora_prazo'])
        
        # Filtro Bia/Willian
        user_atual = str(st.session_state.get('user')).strip().lower()
        if st.session_state.get('role') != 'Administrador':
            df = df[df['responsavel'].str.lower() == user_atual].copy()
        return df
    except: return pd.DataFrame()

def atualizar_missao(id_t, status_final=None, nova_obs=None):
    aba = conectar_google()
    celula = aba.find(str(id_t))
    agora = obter_agora_br().strftime('%d/%m %H:%M')
    if nova_obs:
        valor_antigo = aba.cell(celula.row, 7).value or ""
        aba.update_cell(celula.row, 7, f"[{agora}]: {nova_obs}\n{valor_antigo}")
    if status_final:
        valor_antigo = aba.cell(celula.row, 7).value or ""
        aba.update_cell(celula.row, 7, f"✅ CONCLUÍDO em {agora}\n{valor_antigo}")

# --- LOGIN ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    u = st.text_input("Usuário").strip()
    if st.button("Entrar"):
        role = 'Administrador' if u.lower() == 'willian' else 'Aprendiz'
        st.session_state.update({'logged_in': True, 'user': u, 'role': role, 'page': 'list'})
        st.rerun()
else:
    # MENU SIMPLES
    c1, c2, c3 = st.columns(3)
    if c1.button("📋 Minhas Missões"): st.session_state.page = 'list'
    if c2.button("📝 Nova Missão"): st.session_state.page = 'add'
    if c3.button("👤 Sair"): st.session_state.clear(); st.rerun()

    df = carregar_tarefas()

    if st.session_state.page == 'list':
        st.header("📋 Painel de Trabalho")
        df_vivas = df[~df['status'].str.contains('CONCLUÍDO', na=False)]
        for _, row in df_vivas.iterrows():
            with st.expander(f"📌 {row['titulo']} ({row['data_prazo']})"):
                st.write(f"**Descrição:** {row['descricao']}")
                st.markdown(f"<div class='hist-box'>{row['status']}</div>", unsafe_allow_html=True)
                
                # CAMPO PARA COLAR LINK DO OUTLOOK OU DRIVE
                nova_obs = st.text_input("Cole links ou observações aqui:", key=f"obs_{row['id']}")
                if st.button("💾 Salvar Informação", key=f"btn_{row['id']}"):
                    atualizar_missao(row['id'], nova_obs=nova_obs)
                    st.success("Salvo!"); st.rerun()
                
                if st.button("✅ FINALIZAR MISSÃO", key=f"fin_{row['id']}"):
                    atualizar_missao(row['id'], status_final=True)
                    st.rerun()

    elif st.session_state.page == 'add':
        st.header("📝 Agendar Missão")
        with st.form("add"):
            t = st.text_input("Título")
            desc = st.text_area("Descrição / Links iniciais")
            resp = st.selectbox("Responsável", ["Willian", "Bia"])
            dt = st.date_input("Data", date.today())
            if st.form_submit_button("Agendar"):
                aba = conectar_google()
                aba.append_row([str(uuid.uuid4())[:8], t, desc, resp, str(dt), "09:00", "Iniciado", "", "", st.session_state.user, "Única"])
                st.success("Agendado!"); st.rerun()
