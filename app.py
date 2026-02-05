import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date, time
import time as t_time
import uuid

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Tarefas Diárias", layout="wide", page_icon="📅")

# --- ESTILO VISUAL (Fundo Escuro para Máxima Visibilidade) ---
st.markdown("""
    <style>
    /* Fundo principal em Roxo Escuro */
    .stApp { 
        background-color: #1E0032; 
    }
    
    /* Textos principais em Branco e Amarelo */
    h1, h2, h3, p, span, label { 
        color: #FFFFFF !important; 
    }
    
    /* Input de texto com fundo claro para enxergar o que digita */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #ffffff !important;
        color: #000000 !important;
    }

    /* Botões em Azul com letra Branca */
    .stButton>button {
        background-color: #0000FF !important; 
        color: white !important; 
        border: 2px solid #ffffff;
        border-radius: 10px; 
        font-weight: bold; 
        height: 3em;
    }
    
    /* Hover do botão em Laranja */
    .stButton>button:hover { 
        background-color: #FFA500 !important; 
        color: black !important; 
    }

    /* Cards de Alerta */
    .atraso-card { 
        background-color: #FF4500; 
        color: white; 
        padding: 20px; 
        border-radius: 10px; 
        border: 2px solid yellow;
        font-weight: bold;
    }
    
    /* Expander (Acordeão) com fundo roxo médio */
    .streamlit-expanderHeader {
        background-color: #4B0082 !important;
        color: white !important;
        border-radius: 5px;
    }
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

# --- FUNÇÕES DE LOGIN ---
def validar_login(user_input, pass_input):
    try:
        aba = conectar_google("Usuarios")
        df_users = pd.DataFrame(aba.get_all_records())
        user_row = df_users[(df_users['usuario'] == user_input) & (df_users['senha'].astype(str) == pass_input)]
        if not user_row.empty:
            return user_row.iloc[0].to_dict()
        return None
    except:
        return None

# --- FUNÇÕES DE TAREFAS ---
def carregar_tarefas():
    aba = conectar_google("Página1")
    return pd.DataFrame(aba.get_all_records())

def salvar_tarefa(titulo, desc, resp, d_prazo, h_prazo, criador):
    aba = conectar_google("Página1")
    novo_id = str(uuid.uuid4())[:8]
    aba.append_row([novo_id, titulo, desc, resp, str(d_prazo), str(h_prazo), 'Pendente', '', '', criador])

def atualizar_tarefa_planilha(id_t, status, obs="", motivo="", n_data="", n_hora=""):
    aba = conectar_google("Página1")
    celula = aba.find(str(id_t))
    row = celula.row
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
    st.markdown("<h1 class='main-header'>🙏 Tarefas Diárias - Comunicando Igrejas</h1>", unsafe_allow_html=True)
    with st.container():
        col_l, col_r = st.columns([1, 2])
        with col_l:
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
                    st.error("Credenciais inválidas. Vigiai!")

# --- APP LOGADO ---
else:
    # Sidebar
    st.sidebar.markdown(f"### Bem-vindo, \n**{st.session_state['user']}**")
    st.sidebar.info(f"Perfil: {st.session_state['role']}")
    if st.sidebar.button("Sair"):
        st.session_state['logged_in'] = False
        st.rerun()

    # Menu Superior
    col1, col2, col3, col4 = st.columns(4)
    with col1: 
        if st.button("🏠 Início"): st.session_state['page'] = 'home'
    with col2: 
        if st.button("📝 Agendar"): st.session_state['page'] = 'add'
    with col3: 
        if st.button("📋 Pendências"): st.session_state['page'] = 'list'
    with col4: 
        if st.button("📊 Concluídas"): st.session_state['page'] = 'report'

    # --- PÁGINA: HOME (AVISOS) ---
    if st.session_state['page'] == 'home':
        st.title("🔔 Quadro de Avisos")
        df = carregar_tarefas()
        if not df.empty:
            df_p = df[df['status'].isin(['Pendente', 'Adiado'])].copy()
            df_p['data_hora'] = pd.to_datetime(df_p['data_prazo'].astype(str) + ' ' + df_p['hora_prazo'].astype(str))
            agora = datetime.now()
            
            atrasadas = df_p[df_p['data_hora'] < agora]
            # Filtro para aprendiz
            if st.session_state['role'] == 'Padrão':
                atrasadas = atrasadas[atrasadas['responsavel'] == st.session_state['user']]

            if not atrasadas.empty:
                st.markdown(f"<div class='atraso-card'>⚠️ ALERTA: {len(atrasadas)} Tarefas Atrasadas!</div>", unsafe_allow_html=True)
                for _, row in atrasadas.iterrows():
                    st.write(f"❌ **{row['titulo']}** (Prazo: {row['data_prazo']} {row['hora_prazo']})")
            else:
                st.markdown("<div class='em-dia-card'>✅ Glória a Deus! Tudo em dia.</div>", unsafe_allow_html=True)

    # --- PÁGINA: AGENDAR ---
    elif st.session_state['page'] == 'add':
        st.title("📝 Agendar Nova Missão")
        with st.form("form_add"):
            titulo = st.text_input("O que precisa ser feito?")
            desc = st.text_area("Detalhes do serviço")
            if st.session_state['role'] == 'Administrador':
                resp = st.selectbox("Responsável", ["Willian", "Aprendiz"])
            else:
                resp = st.session_state['user']
            
            c1, c2 = st.columns(2)
            d_p = c1.date_input("Data", date.today())
            h_p = c2.time_input("Hora", time(9, 0))
            
            if st.form_submit_button("Confirmar Agendamento"):
                salvar_tarefa(titulo, desc, resp, d_p, h_p, st.session_state['user'])
                st.success("Tarefa registrada com sucesso!")

    # --- PÁGINA: LISTA DE PENDÊNCIAS ---
    elif st.session_state['page'] == 'list':
        st.title("📋 Tarefas em Aberto")
        df = carregar_tarefas()
        df = df[df['status'].isin(['Pendente', 'Adiado'])]
        if st.session_state['role'] == 'Padrão':
            df = df[df['responsavel'] == st.session_state['user']]
        
        for _, row in df.iterrows():
            with st.expander(f"📌 {row['titulo']} | Para: {row['data_prazo']} às {row['hora_prazo']}"):
                st.write(f"**Descrição:** {row['descricao']}")
                st.write(f"**Criado por:** {row['criado_por']}")
                
                c1, c2 = st.columns(2)
                with c1:
                    with st.form(f"f_con_{row['id']}"):
                        obs = st.text_area("Observações")
                        if st.form_submit_button("✅ Concluir"):
                            atualizar_tarefa_planilha(row['id'], 'Concluído', obs=obs)
                            st.rerun()
                with c2:
                    with st.form(f"f_adi_{row['id']}"):
                        nd = st.date_input("Nova Data")
                        nh = st.time_input("Nova Hora")
                        mot = st.text_input("Motivo")
                        if st.form_submit_button("📅 Adiar"):
                            if mot:
                                atualizar_tarefa_planilha(row['id'], 'Adiado', motivo=mot, n_data=nd, n_hora=nh)
                                st.rerun()
                            else: st.error("Dê um motivo, varão.")

    # --- PÁGINA: RELATÓRIOS ---
    elif st.session_state['page'] == 'report':
        st.title("📊 Histórico de Tarefas Concluídas")
        df = carregar_tarefas()
        df_c = df[df['status'] == 'Concluído']
        if st.session_state['role'] == 'Padrão':
            df_c = df_c[df_c['responsavel'] == st.session_state['user']]
        
        st.dataframe(df_c, use_container_width=True)
        csv = df_c.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Exportar para Excel (CSV)", csv, "relatorio.csv", "text/csv")
