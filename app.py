import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date, time, timedelta
import time as t_time
import uuid

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
    .stButton>button:hover { background-color: #FFA500 !important; color: black !important; }
    .card-tarefa { background-color: #4B0082; padding: 15px; border-radius: 10px; border-left: 5px solid #0000FF; margin-bottom: 10px; }
    .hist-box { background-color: #2D004B; padding: 10px; border-radius: 5px; border: 1px solid #5D008B; margin-bottom: 10px; font-size: 0.9em; }
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
        if not dados: return pd.DataFrame()
        df = pd.DataFrame(dados)
        df.columns = [c.strip().lower() for c in df.columns]
        df['responsavel'] = df['responsavel'].astype(str).str.strip()
        
        if st.session_state.get('role') != 'Administrador':
            nome_logado = str(st.session_state.get('user')).strip().lower()
            df = df[df['responsavel'].str.lower() == nome_logado].copy()
        return df
    except: return pd.DataFrame()

def atualizar_tarefa_planilha(id_t, status_final=None, responsavel=None, nova_data=None, novo_comentario=None):
    try:
        aba = conectar_google("Página1")
        celula = aba.find(str(id_t))
        row = celula.row
        
        # LÓGICA DE HISTÓRICO ACUMULATIVO (Coluna 7 - Status)
        if novo_comentario:
            status_atual = aba.cell(row, 7).value or ""
            data_hora = datetime.now().strftime('%d/%m %H:%M')
            historico_novo = f"[{data_hora}]: {novo_comentario}\n{status_atual}"
            aba.update_cell(row, 7, historico_novo)
        
        if status_final:
            # Se for Concluído ou Adiado, apenas prefixa a informação no histórico
            status_atual = aba.cell(row, 7).value or ""
            aba.update_cell(row, 7, f"--- {status_final.upper()} em {datetime.now().strftime('%d/%m')} ---\n{status_atual}")
            
        if responsavel: aba.update_cell(row, 4, responsavel)
        if nova_data: aba.update_cell(row, 5, str(nova_data))
        return True
    except: return False

def salvar_tarefa(titulo, desc, resp, d_prazo, h_prazo, criador, recorrencia="Única"):
    try:
        aba = conectar_google("Página1")
        novo_id = str(uuid.uuid4())[:8]
        aba.append_row([novo_id, titulo, desc, resp, str(d_prazo), str(h_prazo), 'Iniciado', '', '', criador, recorrencia])
        return True
    except: return False

def atualizar_senha_planilha(login_user, nova_senha):
    try:
        aba = conectar_google("Usuarios")
        celula = aba.find(str(login_user))
        aba.update_cell(celula.row, 3, str(nova_senha))
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
        hoje = date.today().strftime('%Y-%m-%d')
        if not df_geral.empty:
            df_hoje = df_geral[(~df_geral['status'].str.contains('CONCLUÍDO', na=False)) & (df_geral['data_prazo'].astype(str) == hoje)]
            if not df_hoje.empty:
                for _, row in df_hoje.iterrows():
                    st.markdown(f"<div class='card-tarefa'><h4>🕒 {row['hora_prazo']} - {row['titulo']}</h4><p>Resp: {row['responsavel']}</p></div>", unsafe_allow_html=True)
            else: st.info("Sem missões para hoje.")

    # --- PÁGINA: AGENDAR ---
    elif st.session_state['page'] == 'add':
        st.title("📝 Agendar Nova Missão")
        with st.form("f_add"):
            t = st.text_input("Título")
            d = st.text_area("Descrição (Rastreabilidade Inicial)")
            r = st.selectbox("Responsável", ["Willian", "Aprendiz"]) if st.session_state['role'] == 'Administrador' else st.session_state['user']
            dt = st.date_input("Data", date.today())
            hr = st.time_input("Hora", time(9,0))
            rec = st.selectbox("Recorrência", ["Única", "Diário", "Mensal"])
            if st.form_submit_button("Confirmar Agendamento"):
                if salvar_tarefa(t, d, r, dt, hr, st.session_state['user'], rec):
                    st.success("Missão Agendada!")
                    st.rerun()

    # --- PÁGINA: GESTÃO DE MISSÕES (COM HISTÓRICO VIVO) ---
    elif st.session_state['page'] == 'list':
        st.title("📋 Gestão de Missões")
        if not df_geral.empty:
            df_p = df_geral[~df_geral['status'].str.contains('CONCLUÍDO', na=False)]
            for _, row in df_p.iterrows():
                label_resp = f" | Resp: {row['responsavel']}" if st.session_state['role'] == 'Administrador' else ""
                with st.expander(f"📌 {row['titulo']} ({row['data_prazo']}){label_resp}"):
                    st.write(f"**Descrição Inicial:** {row['descricao']}")
                    
                    st.markdown("---")
                    st.subheader("📜 Histórico de Atualizações")
                    st.markdown(f"<div class='hist-box'>{row['status']}</div>", unsafe_allow_html=True)
                    
                    # Campo para nova atualização
                    nova_att = st.text_input("Lançar novo status/atualização:", key=f"att_{row['id']}")
                    if st.button("💾 Lançar Atualização", key=f"btn_att_{row['id']}"):
                        if nova_att:
                            atualizar_tarefa_planilha(row['id'], novo_comentario=nova_att)
                            st.rerun()

                    st.markdown("---")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        if st.button("✅ Concluir", key=f"c_{row['id']}"):
                            atualizar_tarefa_planilha(row['id'], status_final='Concluído')
                            # Lógica de Recorrência
                            rec_tipo = row.get('recorrencia', 'Única')
                            if rec_tipo != 'Única':
                                data_ref = pd.to_datetime(row['data_prazo'])
                                proxima = data_ref + timedelta(days=1) if rec_tipo == 'Diário' else data_ref + timedelta(days=30)
                                salvar_tarefa(row['titulo'], row['descricao'], row['responsavel'], proxima.date(), row['hora_prazo'], st.session_state['user'], rec_tipo)
                            st.rerun()
                    with c2:
                        n_dt = st.date_input("Adiar p/:", value=date.today()+timedelta(days=1), key=f"d_{row['id']}")
                        if st.button("📅 Adiar", key=f"a_{row['id']}"):
                            atualizar_tarefa_planilha(row['id'], status_final='Adiado', nova_data=n_dt)
                            st.rerun()
                    with c3:
                        dest = "Aprendiz" if st.session_state['role'] == 'Administrador' else "Willian"
                        if st.button(f"➡️ Enviar para {dest}", key=f"mv_{row['id']}"):
                            atualizar_tarefa_planilha(row['id'], responsavel=dest, novo_comentario=f"Direcionado para {dest}")
                            st.rerun()

    # --- PÁGINA: RELATÓRIO ---
    elif st.session_state['page'] == 'report':
        st.title("📊 Relatório e Rastreabilidade")
        if not df_geral.empty:
            df_hist = df_geral[df_geral['status'].str.contains('CONCLUÍDO', na=False)].copy()
            if not df_hist.empty:
                st.dataframe(df_hist[['data_prazo', 'titulo', 'responsavel', 'descricao', 'status']], use_container_width=True)
            else: st.info("Histórico vazio.")

    # --- PÁGINA: PERFIL ---
    elif st.session_state['page'] == 'profile':
        st.title("👤 Configurações")
        with st.form("f_senha"):
            n1 = st.text_input("Nova Senha", type="password")
            n2 = st.text_input("Confirme", type="password")
            if st.form_submit_button("Alterar"):
                if n1 == n2 and len(n1) >= 4:
                    atualizar_senha_planilha(st.session_state['login_user'], n1)
                    st.success("Senha atualizada!")
        if st.button("🚪 Sair"):
            st.session_state.clear()
            st.rerun()
