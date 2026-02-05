import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date, time, timedelta
import time as t_time
import uuid

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Tarefas Diárias - Comunicando Igrejas", layout="wide", page_icon="📅")

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
        # Tenta abrir a aba específica, se falhar tenta a primeira disponível
        try:
            return client.open("Tarefas Diarias DB").worksheet(aba_nome)
        except:
            return client.open("Tarefas Diarias DB").get_get_worksheet(0)
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
        aba.update_cell(celula.row, 3, str(nova_senha)) # Coluna 3 = Senha
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
    except: st.error("Erro ao atualizar planilha.")

# --- INICIALIZAÇÃO DO ESTADO ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- TELA DE LOGIN ---
if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align:center;'>🙏 Tarefas Diárias</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Comunicando Igrejas</p>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        u = st.text_input("Usuário", placeholder="Digite seu login")
        s = st.text_input("Senha", type="password", placeholder="Digite sua senha")
        if st.button("Entrar no Sistema"):
            user_data = validar_login(u, s)
            if user_data:
                st.session_state.update({
                    'logged_in': True, 
                    'user': user_data['nome'], 
                    'role': user_data['perfil'], 
                    'login_user': u, 
                    'page': 'home'
                })
                st.rerun()
            else: st.error("Vigiai! Usuário ou senha incorretos.")

# --- SISTEMA APÓS LOGIN ---
else:
    # Menu Superior de Navegação
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: 
        if st.button("🏠 Início"): st.session_state['page'] = 'home'
    with col2: 
        if st.button("📝 Agendar"): st.session_state['page'] = 'add'
    with col3: 
        if st.button("📋 Pendências"): st.session_state['page'] = 'list'
    with col4: 
        if st.button("📊 Concluídas"): st.session_state['page'] = 'report'
    with col5:
        if st.button("👤 Perfil"): st.session_state['page'] = 'profile'

    # --- PÁGINA: HOME (MISSÕES DE HOJE) ---
    if st.session_state['page'] == 'home':
        st.title(f"☀️ Missões de Hoje - {date.today().strftime('%d/%m/%Y')}")
        df = carregar_tarefas()
        if not df.empty:
            hoje_str = date.today().strftime('%Y-%m-%d')
            # Filtro de Hoje
            df_hoje = df[(df['status'].isin(['Pendente', 'Adiado'])) & (df['data_prazo'].astype(str) == hoje_str)]
            
            # Trava de Segurança: Aprendiz só vê o dela
            if st.session_state['role'] == 'Padrão':
                df_hoje = df_hoje[df_hoje['responsavel'] == st.session_state['user']]
            
            if not df_hoje.empty:
                for _, row in df_hoje.iterrows():
                    st.markdown(f"""
                    <div class="card-tarefa">
                        <h4 style='color:yellow; margin:0;'>🕒 {row['hora_prazo']} - {row['titulo']}</h4>
                        <p style='margin:5px 0 0 0;'>Responsável: {row['responsavel']}</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("<div class='em-dia-card'>✅ Nenhuma missão pendente para hoje!</div>", unsafe_allow_html=True)

            # Alerta de Atrasos
            df_atraso = df[(df['status'].isin(['Pendente', 'Adiado'])) & (df['data_prazo'].astype(str) < hoje_str)]
            if st.session_state['role'] == 'Padrão':
                df_atraso = df_atraso[df_atraso['responsavel'] == st.session_state['user']]
            if not df_atraso.empty:
                st.markdown("---")
                st.markdown(f"<div class='atraso-card'>🚨 VIGIAI! Existem {len(df_atraso)} tarefas atrasadas.</div>", unsafe_allow_html=True)

    # --- PÁGINA: PERFIL (TROCA DE SENHA) ---
    elif st.session_state['page'] == 'profile':
        st.title("👤 Configurações de Perfil")
        # Uso do .get para evitar o erro de KeyError
        st.write(f"Usuário logado: **{st.session_state.get('login_user', 'Sessão Expirada')}**")
        
        with st.form("form_perfil"):
            nova_s = st.text_input("Nova Senha", type="password")
            conf_s = st.text_input("Confirmar Senha", type="password")
            if st.form_submit_button("Atualizar Senha"):
                if nova_s == conf_s and len(nova_s) >= 4:
                    if atualizar_senha_planilha(st.session_state.get('login_user'), nova_s):
                        st.success("Senha atualizada com sucesso!")
                    else: st.error("Erro ao salvar na planilha.")
                else: st.error("As senhas não conferem ou são muito curtas.")
        
        if st.button("🚪 Sair do Sistema"):
            st.session_state.clear()
            st.rerun()

    # --- PÁGINA: AGENDAR ---
  # --- PÁGINA: AGENDAR ---
    elif st.session_state['page'] == 'add':
        st.title("📝 Agendar Nova Missão")
        with st.form("form_add", clear_on_submit=True):
            t = st.text_input("O que fazer? (Título)")
            desc = st.text_area("Descrição da Tarefa")
            
            # AQUI ESTÁ A FUNÇÃO DE ESCOLHER PARA QUEM SERÁ AGENDADO:
            # Se você for o Administrador, você escolhe entre você ou a aprendiz.
            # Se for a aprendiz logada, o sistema define ela como responsável automaticamente.
            if st.session_state['role'] == 'Administrador':
                r = st.selectbox("Para quem será agendado?", ["Willian", "Aprendiz"])
            else:
                r = st.session_state['user']
                st.write(f"Responsável: **{r}**")
            
            c1, c2, c3 = st.columns(3)
            dt = c1.date_input("Data", date.today())
            hr = c2.time_input("Hora", time(9, 0))
            rec = c3.selectbox("Frequência", ["Única", "Diário"])
            
            if st.form_submit_button("Agendar Missão"):
                if t:
                    # Salva na planilha com o responsável escolhido (r)
                    if salvar_tarefa(t, desc, r, dt, hr, st.session_state['user'], rec):
                        st.success(f"Bênção! Tarefa agendada para {r} com sucesso.")
                        t_time.sleep(1)
                        st.rerun()
                else:
                    st.error("Varão, o título é obrigatório para registrar a obra!")
    # --- PÁGINA: PENDÊNCIAS (COM FUNÇÃO DE DELEGAR) ---
    elif st.session_state['page'] == 'list':
        st.title("📋 Minhas Pendências")
        df = carregar_tarefas()
        if not df.empty:
            df_p = df[df['status'].isin(['Pendente', 'Adiado'])]
            if st.session_state['role'] == 'Padrão':
                df_p = df_p[df_p['responsavel'] == st.session_state['user']]
            
            for _, row in df_p.iterrows():
                with st.expander(f"📌 {row['titulo']} ({row['data_prazo']})"):
                    st.write(f"**Descrição:** {row['descricao']}")
                    # Se for admin, 3 colunas (Concluir, Adiar, Delegar). Se não, 2 colunas.
                    cols = st.columns(3) if st.session_state['role'] == 'Administrador' else st.columns(2)
                    
                    with cols[0]:
                        with st.form(f"f_con_{row['id']}"):
                            obs = st.text_area("Obs")
                            if st.form_submit_button("✅ Concluir"):
                                atualizar_tarefa_planilha(row['id'], 'Concluído', obs=obs)
                                if row.get('recorrencia') == 'Diário':
                                    prox = pd.to_datetime(row['data_prazo']) + timedelta(days=1)
                                    salvar_tarefa(row['titulo'], row['descricao'], row['responsavel'], prox.date(), row['hora_prazo'], st.session_state['user'], "Diário")
                                st.rerun()
                    with cols[1]:
                        with st.form(f"f_adi_{row['id']}"):
                            nd = st.date_input("Nova Data", value=pd.to_datetime(row['data_prazo']))
                            mot = st.text_input("Motivo")
                            if st.form_submit_button("📅 Adiar"):
                                if mot:
                                    atualizar_tarefa_planilha(row['id'], 'Adiado', motivo=mot, n_data=nd)
                                    st.rerun()
                                else: st.error("Dê o motivo.")
                    
                    if st.session_state['role'] == 'Administrador':
                        with cols[2]:
                            with st.form(f"f_del_{row['id']}"):
                                st.markdown("🔗 **Direcionar**")
                                nova_d = st.date_input("Data p/ ela", value=date.today())
                                if st.form_submit_button("➡️ Enviar"):
                                    aba = conectar_google("Página1")
                                    cel = aba.find(str(row['id']))
                                    aba.update_cell(cel.row, 4, "Aprendiz") # Muda Resp
                                    aba.update_cell(cel.row, 5, str(nova_d)) # Muda Data
                                    st.success("Direcionado!")
                                    t_time.sleep(1)
                                    st.rerun()

    # --- PÁGINA: REPORT ---
    elif st.session_state['page'] == 'report':
        st.title("📊 Relatório Finalizado")
        df = carregar_tarefas()
        if not df.empty:
            df_c = df[df['status'] == 'Concluído']
            if st.session_state['role'] == 'Padrão':
                df_c = df_c[df_c['responsavel'] == st.session_state['user']]
            st.dataframe(df_c, use_container_width=True)
