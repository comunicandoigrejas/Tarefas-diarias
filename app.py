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

# --- ESTILO VISUAL ---
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
    .chat-msg { padding: 10px; border-radius: 10px; margin-bottom: 5px; color: white; border-left: 5px solid; }
    .msg-eu { background-color: #006400; border-color: #FFFF00; }
    .msg-outro { background-color: #4B0082; border-color: #FFA500; }
    .hist-box { background-color: #2D004B; padding: 10px; border-radius: 5px; border: 1px solid #5D008B; margin-bottom: 10px; font-size: 0.9em; white-space: pre-wrap; }
    </style>
""", unsafe_allow_html=True)

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

# --- FUNÇÕES DE DADOS ---
def carregar_tarefas():
    try:
        aba = conectar_google("Página1")
        df = pd.DataFrame(aba.get_all_records())
        if df.empty: return df
        df.columns = [c.strip().lower() for c in df.columns]
        df['data_prazo_dt'] = pd.to_datetime(df['data_prazo'], errors='coerce')
        df = df.sort_values(by=['data_prazo_dt', 'hora_prazo'], ascending=[True, True])
        df['responsavel_limpo'] = df['responsavel'].astype(str).str.strip().str.lower()
        if st.session_state.get('role') != 'Administrador':
            df = df[df['responsavel_limpo'] == str(st.session_state.get('user')).lower()].copy()
        return df
    except: return pd.DataFrame()

def atualizar_tarefa_planilha(id_t, status_final=None, responsavel=None, nova_data=None, novo_comentario=None):
    try:
        aba = conectar_google("Página1")
        celula = aba.find(str(id_t))
        row_idx = celula.row
        agora = obter_agora_br()
        if novo_comentario:
            s_p = aba.cell(row_idx, 7).value or ""
            aba.update_cell(row_idx, 7, f"[{agora.strftime('%d/%m %H:%M')}]: {novo_comentario}\n{s_p}")
        if status_final:
            s_p = aba.cell(row_idx, 7).value or ""
            aba.update_cell(row_idx, 7, f"--- {status_final.upper()} em {agora.strftime('%d/%m')} ---\n{s_p}")
        if responsavel: aba.update_cell(row_idx, 4, responsavel)
        if nova_data: aba.update_cell(row_idx, 5, str(nova_data))
        return True
    except: return False

def salvar_missao(titulo, desc, resp, dt, hr, criador, rec):
    try:
        aba = conectar_google("Página1")
        aba.append_row([str(uuid.uuid4())[:8], titulo, desc, resp, str(dt), str(hr), 'Iniciado', '', '', criador, rec])
        return True
    except: return False

# --- LÓGICA DE LOGIN ---
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
    # --- MENU ---
    menu = st.columns(6)
    labels = ["🏠 Início", "📝 Agendar", "📋 Missões", "📊 Relatório", "💬 Chat", "👤 Sair"]
    pages = ['home', 'add', 'list', 'report', 'chat', 'exit']
    for i, nome in enumerate(labels):
        if menu[i].button(nome):
            if pages[i] == 'exit': st.session_state.clear(); st.rerun()
            st.session_state['page'] = pages[i]

    df_geral = carregar_tarefas()

    # --- PÁGINA: HOME ---
    if st.session_state['page'] == 'home':
        st.title(f"☀️ Olá, {st.session_state['user']}!")
        hoje_str = obter_agora_br().strftime('%Y-%m-%d')
        st.subheader("📅 Para Hoje:")
        if not df_geral.empty:
            df_hoje = df_geral[(df_geral['data_prazo'].astype(str) == hoje_str) & (~df_geral['status'].str.contains('CONCLUÍDO', case=False, na=False))]
            if not df_hoje.empty:
                for _, r in df_hoje.iterrows():
                    st.markdown(f"<div style='background-color:#4B0082; padding:15px; border-radius:10px; border-left:5px solid #0000FF; margin-bottom:10px;'><h4>🕒 {r['hora_prazo']} - {r['titulo']}</h4></div>", unsafe_allow_html=True)
            else: st.success("Nada pendente para hoje!")

    # --- PÁGINA: AGENDAR ---
    elif st.session_state['page'] == 'add':
        st.title("📝 Agendar Missão")
        with st.form("f_add"):
            t = st.text_input("Título")
            d = st.text_area("Descrição")
            r = st.selectbox("Responsável", ["Willian", "Aprendiz"])
            dt = st.date_input("Data", date.today())
            hr = st.time_input("Hora", time(9,0))
            rec = st.selectbox("Recorrência", ["Única", "Diário", "Semanal", "Mensal"])
            if st.form_submit_button("Agendar"):
                if salvar_missao(t, d, r, dt, hr, st.session_state['user'], rec):
                    st.success("Salvo!"); t_time.sleep(1); st.rerun()

    # --- PÁGINA: MISSÕES (COM CAMPO DE OBSERVAÇÃO RESTAURADO) ---
    elif st.session_state['page'] == 'list':
        st.title("📋 Painel de Missões")
        if not df_geral.empty:
            df_vivas = df_geral[~df_geral['status'].str.contains('CONCLUÍDO', case=False, na=False)]
            for _, row in df_vivas.iterrows():
                resp_tag = f"[{row['responsavel'].upper()}]"
                with st.expander(f"📌 {resp_tag} {row['titulo']} (Prazo: {row['data_prazo']})"):
                    st.write(f"**Descrição:** {row['descricao']}")
                    st.markdown(f"<div class='hist-box'>{row['status']}</div>", unsafe_allow_html=True)
                    
                    # --- RESTAURAÇÃO DO CAMPO DE OBSERVAÇÃO ---
                    obs_txt = st.text_input("Registrar observação/andamento:", key=f"obs_{row['id']}")
                    if st.button("💾 Salvar Observação", key=f"btn_obs_{row['id']}"):
                        if obs_txt:
                            atualizar_tarefa_planilha(row['id'], novo_comentario=obs_txt)
                            st.success("Observação salva!"); t_time.sleep(1); st.rerun()
                    
                    st.divider()
                    
                    # Botão Concluir com Recorrência
                    if st.button("✅ CONCLUIR MISSÃO", key=f"c_{row['id']}"):
                        atualizar_tarefa_planilha(row['id'], status_final='Concluído')
                        if str(row.get('recorrencia', '')).strip().capitalize() == "Diário":
                            amanha = (pd.to_datetime(row['data_prazo']) + timedelta(days=1)).date()
                            salvar_missao(row['titulo'], row['descricao'], row['responsavel'], amanha, row['hora_prazo'], "Sistema", "Diário")
                        st.rerun()
                    
                    # Transferir e Adiar
                    c1, c2 = st.columns(2)
                    with c1:
                        dest = "Aprendiz" if st.session_state['role'] == 'Administrador' else "Willian"
                        if st.button(f"➡️ Para {dest}", key=f"t_{row['id']}"):
                            atualizar_tarefa_planilha(row['id'], responsavel=dest, novo_comentario=f"Transferido para {dest}"); st.rerun()
                    with c2:
                        n_dt = st.date_input("Adiar para:", value=date.today()+timedelta(days=1), key=f"d_{row['id']}")
                        if st.button("⏳ Confirmar Adiar", key=f"btn_a_{row['id']}"):
                            atualizar_tarefa_planilha(row['id'], status_final='Adiado', nova_data=n_dt); st.rerun()

    # --- PÁGINA: CHAT ---
    elif st.session_state['page'] == 'chat':
        st.title("💬 Mural de Chat")
        aba_c = conectar_google("Chat")
        df_c = pd.DataFrame(aba_c.get_all_records())
        df_ativos = df_c[df_c['status'] != 'Baixado'] if not df_c.empty else pd.DataFrame()
        
        if not df_ativos.empty:
            for idx, msg in df_ativos.iterrows():
                classe = "msg-eu" if msg['remetente'] == st.session_state['user'] else "msg-outro"
                st.markdown(f"<div class='chat-msg {classe}'><small>{msg['remetente']} - {msg['data_hora']}</small><br>{msg['mensagem']}</div>", unsafe_allow_html=True)
                if st.button("📥 Baixar", key=f"bx_{idx}"):
                    aba_c.update_cell(idx + 2, 5, "Baixado"); st.rerun()
        
        with st.form("f_chat", clear_on_submit=True):
            lista_res = ["Nenhuma"] + list(reversed(df_ativos['mensagem'].tail(50).tolist())) if not df_ativos.empty else ["Nenhuma"]
            resp_a = st.selectbox("Responder a:", lista_res)
            txt = st.text_area("Sua mensagem:")
            if st.form_submit_button("Enviar"):
                final = f"↪️ Resp: {resp_a}\n---\n{txt}" if resp_a != "Nenhuma" else txt
                aba_c.append_row([obter_agora_br().strftime('%d/%m %H:%M'), st.session_state['user'], "Todos", final, "Ativo"])
                st.rerun()

    # --- PÁGINA: RELATÓRIO ---
    elif st.session_state['page'] == 'report':
        st.title("📊 Relatório")
        if not df_geral.empty:
            st.dataframe(df_geral[df_geral['status'].str.contains('CONCLUÍDO', case=False, na=False)])
