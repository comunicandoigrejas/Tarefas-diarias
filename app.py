import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date, time
import time as t_time
import uuid

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Tarefas Diárias", layout="wide", page_icon="📅")

# --- ESTILO VISUAL DE ALTO CONTRASTE (Fundo Roxo Escuro / Letras Brancas) ---
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
    </style>
""", unsafe_allow_html=True)

# --- CONEXÃO COM GOOGLE SHEETS ---
def conectar_google(aba_nome):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        # Tenta abrir a aba. Se falhar, tenta pelo nome do arquivo
        try:
            return client.open("Tarefas Diarias DB").worksheet(aba_nome)
        except:
            return client.open("Tarefas Diarias DB").sheet1
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        st.stop()

# --- FUNÇÕES DE LOGIN ---
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
    except:
        return None

# --- FUNÇÕES DE TAREFAS (COM TRATAMENTO DE COLUNAS) ---
def carregar_tarefas():
    try:
        aba = conectar_google("Página1")
        dados = aba.get_all_records()
        if not dados:
            return pd.DataFrame(columns=['id', 'titulo', 'descricao', 'responsavel', 'data_prazo', 'hora_prazo', 'status', 'observacoes', 'motivo_adiamento', 'criado_por'])
        df = pd.DataFrame(dados)
        df.columns = [c.strip().lower() for c in df.columns]
        return df
    except:
        return pd.DataFrame()

def salvar_tarefa(titulo, desc, resp, d_prazo, h_prazo, criador, recorrencia="Única"):
    try:
        aba = conectar_google("Página1")
        novo_id = str(uuid.uuid4())[:8]
        # Adicionamos a recorrência no final da linha (Coluna K)
        nova_linha = [novo_id, titulo, desc, resp, str(d_prazo), str(h_prazo), 'Pendente', '', '', criador, recorrencia]
        aba.append_row(nova_linha)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

def atualizar_tarefa_planilha(id_t, status, obs="", motivo="", n_data="", n_hora=""):
    aba = conectar_google("Página1")
    celula = aba.find(str(id_t))
    row = celula.row
    # Colunas: 7=status, 8=obs, 9=motivo, 5=data, 6=hora
    aba.update_cell(row, 7, status)
    if status == 'Concluído':
        aba.update_cell(row, 8, obs)
    elif status == 'Adiado':
        aba.update_cell(row, 9, motivo)
        aba.update_cell(row, 5, str(n_data))
        aba.update_cell(row, 6, str(n_hora))

# --- INTERFACE DE LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align:center;'>🙏 Tarefas Diárias</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;'>Comunicando Igrejas</h3>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        u = st.text_input("Usuário")
        s = st.text_input("Senha", type="password")
        if st.button("Entrar no Sistema"):
            user_data = validar_login(u, s)
            if user_data:
                st.session_state.update({
                    'logged_in': True, 'user': user_data['nome'],
                    'role': user_data['perfil'], 'page': 'home'
                })
                st.rerun()
            else:
                st.error("Credenciais inválidas. Vigiai, varão!")

# --- APP LOGADO ---
else:
    st.sidebar.markdown(f"### Olá, **{st.session_state['user']}**")
    if st.sidebar.button("Sair"):
        st.session_state['logged_in'] = False
        st.rerun()

    # Menu
    col1, col2, col3, col4 = st.columns(4)
    with col1: 
        if st.button("🏠 Início"): st.session_state['page'] = 'home'
    with col2: 
        if st.button("📝 Agendar"): st.session_state['page'] = 'add'
    with col3: 
        if st.button("📋 Pendências"): st.session_state['page'] = 'list'
    with col4: 
        if st.button("📊 Concluídas"): st.session_state['page'] = 'report'

    # --- PÁGINA: HOME ---
    if st.session_state['page'] == 'home':
        st.title("🔔 Avisos do Dia")
        df = carregar_tarefas()
        if not df.empty and 'status' in df.columns:
            df_p = df[df['status'].isin(['Pendente', 'Adiado'])].copy()
            if not df_p.empty:
                df_p['data_hora'] = pd.to_datetime(df_p['data_prazo'].astype(str) + ' ' + df_p['hora_prazo'].astype(str), errors='coerce')
                agora = datetime.now()
                atrasadas = df_p[df_p['data_hora'] < agora]
                if st.session_state['role'] == 'Padrão':
                    atrasadas = atrasadas[atrasadas['responsavel'] == st.session_state['user']]

                if not atrasadas.empty:
                    st.markdown(f"<div class='atraso-card'>⚠️ ATENÇÃO: {len(atrasadas)} Tarefas Atrasadas!</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='em-dia-card'>✅ Tudo em ordem por aqui!</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='em-dia-card'>✅ Nenhuma pendência encontrada.</div>", unsafe_allow_html=True)

    # --- PÁGINA: AGENDAR ---
    elif st.session_state['page'] == 'add':
        st.title("📝 Novo Agendamento")
        with st.form("form_add", clear_on_submit=True):
            titulo = st.text_input("Título da Tarefa")
            desc = st.text_area("Descrição Detalhada")
            
            # Define quem faz a obra
            if st.session_state['role'] == 'Administrador':
                resp = st.selectbox("Responsável", ["Willian", "Aprendiz"])
            else:
                resp = st.session_state['user']
            
            # Organiza Data, Hora e Frequência em 3 colunas
            c1, c2, c3 = st.columns(3)
            d_p = c1.date_input("Data Inicial", date.today())
            h_p = c2.time_input("Hora", time(9, 0))
            
            # AQUI ESTÁ A NOVIDADE: O campo de Frequência
            tipo_rec = c3.selectbox("Frequência", ["Única", "Diário"])
            
            if st.form_submit_button("Confirmar Agendamento"):
                if titulo:
                    # Chamamos a função de salvar passando a recorrência
                    if salvar_tarefa(titulo, desc, resp, d_p, h_p, st.session_state['user'], tipo_rec):
                        st.success(f"Bênção! Tarefa '{tipo_rec}' registrada com sucesso.")
                else:
                    st.error("Varão, o título da tarefa não pode ficar vazio!")
    # --- PÁGINA: PENDÊNCIAS ---
    # Dentro do loop de pendências, no botão Concluir:
if st.form_submit_button("✅ Concluir"):
    # 1. Atualiza a tarefa atual para Concluído
    atualizar_tarefa_planilha(row['id'], 'Concluído', obs=o)
    
    # 2. Verifica se era recorrente (Diária)
    # Se a coluna recorrencia (índice 10 no DataFrame) for "Diário"
    if 'recorrencia' in row and row['recorrencia'] == "Diário":
        from datetime import timedelta
        nova_data = pd.to_datetime(row['data_prazo']) + timedelta(days=1)
        
        # Cria a missão para o dia seguinte com os mesmos dados
        salvar_tarefa(
            row['titulo'], 
            row['descricao'], 
            row['responsavel'], 
            nova_data.date(), 
            row['hora_prazo'], 
            st.session_state['user'],
            "Diário"
        )
        st.success("Bênção! Tarefa concluída e agendada para amanhã automaticamente.")
    else:
        st.success("Tarefa concluída!")
        
    t_time.sleep(1)
    st.rerun()

    # --- PÁGINA: REPORT ---
    elif st.session_state['page'] == 'report':
        st.title("📊 Relatório")
        df = carregar_tarefas()
        if not df.empty and 'status' in df.columns:
            df_c = df[df['status'] == 'Concluído']
            st.dataframe(df_c)
