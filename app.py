import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date, time
import time as t_time
import uuid

# --- Configuração da Página ---
st.set_page_config(page_title="Tarefas Diárias", layout="wide", page_icon="📅")

# --- Cores e Estilo (CSS Personalizado) ---
st.markdown("""
    <style>
    .main-header {color: #4B0082; text-align: center; font-weight: bold;} 
    .stButton>button {
        background-color: #0000FF; color: white; border-radius: 10px; font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #FFA500; color: black;
    }
    .success-box {background-color: #32CD32; padding: 10px; border-radius: 5px; color: white;}
    .warning-box {background-color: #FFA500; padding: 10px; border-radius: 5px; color: black;}
    .danger-box {background-color: #FF4500; padding: 10px; border-radius: 5px; color: white;}
    </style>
""", unsafe_allow_html=True)

# --- Conexão com Google Sheets ---
def conectar_google_sheets():
    # Define o escopo (permissões)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Pega as credenciais dos Segredos do Streamlit (vamos configurar isso já já)
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    
    client = gspread.authorize(creds)
    
    # Abre a planilha pelo nome (tem que criar uma planilha com esse nome exato no Google)
    try:
        sheet = client.open("Tarefas Diarias DB").sheet1
        return sheet
    except Exception as e:
        st.error("Varão, não achei a planilha 'Tarefas Diarias DB'. Verifique se criou ela e compartilhou com o email do robô.")
        st.stop()

# --- Funções de Dados ---
def carregar_dados():
    sheet = conectar_google_sheets()
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def adicionar_tarefa(titulo, descricao, responsavel, data_prazo, hora_prazo, criado_por):
    sheet = conectar_google_sheets()
    # Gera um ID único
    novo_id = str(uuid.uuid4())[:8]
    nova_linha = [novo_id, titulo, descricao, responsavel, str(data_prazo), str(hora_prazo), 'Pendente', '', '', criado_por]
    sheet.append_row(nova_linha)

def atualizar_status(id_tarefa, novo_status, observacao="", motivo="", nova_data="", nova_hora=""):
    sheet = conectar_google_sheets()
    # Busca a célula que contém o ID
    cell = sheet.find(str(id_tarefa))
    row_num = cell.row
    
    # Colunas: 1=id, 2=titulo, 3=desc, 4=resp, 5=data, 6=hora, 7=status, 8=obs, 9=motivo, 10=criado
    sheet.update_cell(row_num, 7, novo_status) # Atualiza Status
    
    if novo_status == 'Concluído':
        sheet.update_cell(row_num, 8, observacao) # Obs
    elif novo_status == 'Adiado':
        sheet.update_cell(row_num, 9, motivo) # Motivo
        sheet.update_cell(row_num, 5, str(nova_data)) # Nova Data
        sheet.update_cell(row_num, 6, str(nova_hora)) # Nova Hora

# --- Login ---
def login():
    st.sidebar.title("🔐 Acesso Restrito")
    usuario = st.sidebar.text_input("Usuário")
    senha = st.sidebar.text_input("Senha", type="password")
    
    if st.sidebar.button("Entrar"):
        # Login do Willian (Admin)
        if usuario == "willian" and senha == "admin123":
            st.session_state['logged_in'] = True
            st.session_state['user'] = "Willian"
            st.session_state['role'] = "Administrador"
            st.rerun()
        # Login da Aprendiz (Padrão)
        elif usuario == "aprendiz" and senha == "ap123":
            st.session_state['logged_in'] = True
            st.session_state['user'] = "Aprendiz"
            st.session_state['role'] = "Padrão"
            st.rerun()
        else:
            st.sidebar.error("Usuário ou senha incorretos. Vigiai!")

def logout():
    if st.sidebar.button("Sair"):
        st.session_state['logged_in'] = False
        st.rerun()

# --- App Principal ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h1 class='main-header'>Tarefas Diárias - Login</h1>", unsafe_allow_html=True)
    login()
else:
    logout()
    user_name = st.session_state['user']
    user_role = st.session_state['role']
    
    st.markdown(f"<h2 style='color: #4B0082;'>A paz do Senhor, {user_name}! ({user_role})</h2>", unsafe_allow_html=True)

    # Menu
  # --- Menu de Navegação ---
    # Garante que a variável 'page' existe antes de clicar
    if 'page' not in st.session_state:
        st.session_state['page'] = 'home'

    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🏠 Início"):
            st.session_state['page'] = 'home'
            
    with col2:
        if st.button("📝 Agendar"):
            st.session_state['page'] = 'add'
            
    with col3:
        if st.button("📋 Pendências"):
            st.session_state['page'] = 'list'
            
    with col4:
        if st.button("📊 Relatórios"):
            st.session_state['page'] = 'report'
