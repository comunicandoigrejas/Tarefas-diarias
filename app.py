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

# --- CONEXÃO GOOGLE SHEETS ---
def conectar_google(aba_nome):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds).open("Tarefas Diarias DB").worksheet(aba_nome)
    except:
        st.error("Erro de conexão. Verifique os Secrets.")
        st.stop()

# --- FUNÇÃO PARA SALVAR TAREFA (REUTILIZÁVEL) ---
def salvar_tarefa_db(titulo, desc, resp, d_prazo, h_prazo, criador, recorrencia):
    try:
        aba = conectar_google("Página1")
        aba.append_row([str(uuid.uuid4())[:8], titulo, desc, resp, str(d_prazo), str(h_prazo), 'Iniciado', '', '', criador, recorrencia])
        return True
    except: return False

# --- FUNÇÃO DE CONCLUSÃO COM LÓGICA DE RECORRÊNCIA ---
def concluir_missao(row):
    try:
        aba = conectar_google("Página1")
        # 1. Marcar a atual como concluída
        celula = aba.find(str(row['id']))
        agora = obter_agora_br()
        status_p = aba.cell(celula.row, 7).value or ""
        aba.update_cell(celula.row, 7, f"--- CONCLUÍDO em {agora.strftime('%d/%m')} ---\n{status_p}")
        
        # 2. SE FOR DIÁRIO, GERAR A PRÓXIMA PARA AMANHÃ
        # Verificamos a coluna 'recorrencia' (índice 11 na planilha)
        recorrencia_tipo = str(row.get('recorrencia', 'Única')).strip().capitalize()
        
        if recorrencia_tipo == "Diário":
            amanha = (datetime.strptime(str(row['data_prazo']), '%Y-%m-%d') + timedelta(days=1)).date()
            salvar_tarefa_db(
                row['titulo'], 
                row['descricao'], 
                row['responsavel'], 
                amanha, 
                row['hora_prazo'], 
                "Sistema (Recorrência)", 
                "Diário"
            )
            st.success(f"Missão concluída e reagendada para {amanha.strftime('%d/%m')}!")
        else:
            st.success("Missão concluída com sucesso!")
            
        t_time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao concluir: {e}")

# --- (O RESTANTE DO CÓDIGO - ESTILO, LOGIN, HOME E CHAT - SEGUE IGUAL) ---
# ... (Manter as mesmas configurações de estilo da v17.0) ...

# --- NA PÁGINA DE MISSÕES, ALTERAR O BOTÃO CONCLUIR PARA CHAMAR A NOVA FUNÇÃO ---
# (Substitua a parte do botão na aba 'list')

# --- PÁGINA: MISSÕES ---
if 'page' in st.session_state and st.session_state['page'] == 'list':
    # ... (carregamento do df_geral e filtros) ...
    df_vivas = carregar_tarefas() # Supondo que a função carregar_tarefas() já existe conforme v17
    if not df_vivas.empty:
        df_vivas = df_vivas[~df_vivas['status'].str.contains('CONCLUÍDO', case=False, na=False)]
        for _, row in df_vivas.iterrows():
            with st.expander(f"📌 [{row['responsavel'].upper()}] {row['titulo']} (Prazo: {row['data_prazo']})"):
                # ... (Exibição de descrição e comentário igual v17) ...
                
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    # CHAMADA DA NOVA FUNÇÃO QUE GERA A PRÓXIMA TAREFA
                    if st.button("✅ CONCLUIR", key=f"c_{row['id']}"):
                        concluir_missao(row)
                # ... (Restante dos botões de Transferir e Adiar conforme v17) ...
