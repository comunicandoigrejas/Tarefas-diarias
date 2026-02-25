import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import cloudinary
import cloudinary.uploader
from datetime import datetime, date, time, timedelta
import time as t_time
import uuid
import pytz

# --- CONFIGURAÇÃO TESTE (DIRETO NO CÓDIGO) ---
cloudinary.config(
  cloud_name = "dzs4gxmfc",
  api_key = "627471382294285",
  api_secret = "D4yDdj6Zq5m47G9qUBeGx0KbK20"
)

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

def fazer_upload_cloudinary(arquivo):
    try:
        # 1. Upload simples e direto
        resultado = cloudinary.uploader.upload(
            arquivo, 
            resource_type="auto"
        )
        
        # 2. Pegamos a URL segura
        link = resultado.get('secure_url')
        
        # 3. Pequeno ajuste manual para garantir que o navegador abra na tela
        # Removemos qualquer instrução de 'download' forçado
        if ".pdf" in arquivo.name.lower():
            link = link.replace("/raw/upload/", "/image/upload/")
            if not link.endswith(".pdf"):
                link = link + ".pdf"
            
        return link
    except Exception as e:
        st.error(f"Erro no Cloudinary: {e}")
        return ""

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
        
        user_atual = str(st.session_state.get('user')).strip().lower()
        if st.session_state.get('role') != 'Administrador':
            df = df[df['responsavel'].str.lower() == user_atual].copy()
        return df
    except: return pd.DataFrame()

def salvar_missao(titulo, desc, resp, dt, hr, criador, rec, link_anexo=""):
    try:
        aba = conectar_google("Página1")
        # Coluna 12 (L) deve existir na sua planilha como 'link_anexo'
        aba.append_row([str(uuid.uuid4())[:8], titulo, desc, resp, str(dt), str(hr), 'Iniciado', '', '', criador, rec, link_anexo])
        return True
    except: return False

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

# --- LOGIN ---
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
        st.subheader("📅 Missões para Hoje:")
        
        if not df_geral.empty:
            # Filtra o que é para hoje e não está concluído
            df_hoje = df_geral[(df_geral['data_prazo'].astype(str) == hoje_str) & 
                               (~df_geral['status'].str.contains('CONCLUÍDO', case=False, na=False))]
            
            if df_hoje.empty:
                st.success("Glória a Deus! Tudo em dia por aqui.")
            else:
                for _, r in df_hoje.iterrows():
                    # O container deve estar alinhado com o 'for'
                    with st.container():
                        col_txt, col_btn = st.columns([3, 1])
                        with col_txt:
                            st.markdown(f"""
                                <div style='background-color:#4B0082; padding:15px; border-radius:10px; border-left:5px solid #FFFF00;'>
                                    <h4 style='margin:0;'>🕒 {r['hora_prazo']} - {r['titulo']}</h4>
                                </div>
                            """, unsafe_allow_html=True)
                        with col_btn:
                            # ESTA LINHA ABAIXO PRECISA ESTAR EXATAMENTE ABAIXO DO 'with col_btn'
                            if st.button(f"🚀 Executar", key=f"exec_{r['id']}"):
                                st.session_state['page'] = 'list'
                                st.session_state['tarefa_foco'] = str(r['id'])
                                st.rerun()
        else:
            st.info("Nenhuma missão registrada.")

    # --- PÁGINA: AGENDAR ---
    elif st.session_state['page'] == 'add':
        st.title("📝 Agendar Missão")
        with st.form("f_add"):
            t = st.text_input("Título")
            d = st.text_area("Descrição")
            r = st.selectbox("Responsável", ["Willian", "Bia"])
            dt = st.date_input("Data", date.today())
            hr = st.time_input("Hora", time(9,0))
            rec = st.selectbox("Recorrência", ["Única", "Diário", "Semanal", "Mensal"])
            
            # --- NOVO CAMPO DE ANEXO ---
            arquivo_upload = st.file_uploader("📎 Anexar PDF ou Imagem (via Cloudinary)", type=['pdf','png','jpg','docx'])
            
            if st.form_submit_button("Agendar"):
                link_final = ""
                if arquivo_upload:
                    with st.spinner("Fazendo upload do anexo..."):
                        link_final = fazer_upload_cloudinary(arquivo_upload)
                
                if salvar_missao(t, d, r, dt, hr, st.session_state['user'], rec, link_final):
                    st.success("Salvo!"); t_time.sleep(1); st.rerun()

    # --- PÁGINA: MISSÕES ---
    elif st.session_state['page'] == 'list':
        st.title("📋 Missões")
        
        # Recuperamos o ID que veio da Home (se existir)
        foco_id = st.session_state.get('tarefa_foco', None)
        
        if not df_geral.empty:
            df_vivas = df_geral[~df_geral['status'].str.contains('CONCLUÍDO', case=False, na=False)]
            for _, row in df_vivas.iterrows():
                # A MÁGICA ESTÁ AQUI: 
                # Se o ID da tarefa for o mesmo que clicamos na Home, 'expanded' será True
                abrir_caixa = (str(row['id']) == foco_id)
                
                with st.expander(f"📌 [{row['responsavel'].upper()}] {row['titulo']} - {row['data_prazo']}", expanded=abrir_caixa):
                    st.write(f"**Descrição:** {row['descricao']}")
                    
                    # Limpa o foco após abrir para não ficar abrindo sempre a mesma
                    if abrir_caixa:
                        st.session_state['tarefa_foco'] = None
                    
                    # ... (resto do seu código de botões, anexos e conclusões)
                    
                    # EXIBE BOTÃO SE HOUVER ANEXO
                    if row.get('link_anexo'):
                        st.markdown(f'<a href="{row["link_anexo"]}" target="_blank"><button style="background-color:#ff00ff; color:black; border:none; padding:10px; border-radius:5px; width:100%; font-weight:bold;">📂 ABRIR ANEXO</button></a>', unsafe_allow_html=True)
                    
                    st.markdown(f"<div class='hist-box'>{row['status']}</div>", unsafe_allow_html=True)
                    obs = st.text_input("Obs:", key=f"obs_{row['id']}")
                    if st.button("Salvar Obs", key=f"bo_{row['id']}"):
                        atualizar_tarefa_planilha(row['id'], novo_comentario=obs); st.rerun()
                    
                    st.divider()
                    if st.button("✅ CONCLUIR", key=f"c_{row['id']}"):
                        atualizar_tarefa_planilha(row['id'], status_final='Concluído')
                        st.rerun()
                    
                    # Botões de Transferir e Adiar (Omitidos aqui por brevidade, mas devem ser mantidos conforme v24)
                    c1, c2 = st.columns(2)
                    with c1:
                        dest = "Bia" if st.session_state['role'] == 'Administrador' else "Willian"
                        if st.button(f"➡️ Para {dest}", key=f"t_{row['id']}"):
                            atualizar_tarefa_planilha(row['id'], responsavel=dest); st.rerun()
                    with c2:
                        n_dt = st.date_input("Adiar:", value=date.today()+timedelta(days=1), key=f"d_{row['id']}")
                        if st.button("⏳ Confirmar", key=f"ba_{row['id']}"):
                            atualizar_tarefa_planilha(row['id'], status_final='Adiado', nova_data=n_dt); st.rerun()

# --- PÁGINA: RELATÓRIO PENTE FINO (v49) ---
    elif st.session_state['page'] == 'report':
        st.title("📊 Relatório Geral de Atividades")
        st.markdown(f"**Comunicando Igrejas** - Histórico Completo de Missões Concluídas")
        
        try:
            # 1. CONEXÃO COM A PÁGINA1 (Fonte principal)
            aba_p1 = conectar_google("Página1")
            dados_p1 = aba_p1.get_all_records()
            df_p1 = pd.DataFrame(dados_p1)

            if not df_p1.empty:
                # 2. LÓGICA PENTE FINO: 
                # Transformamos tudo em texto e buscamos 'CONCLUÍDO' em qualquer lugar da linha.
                # O 'case=False' garante que pegue 'Concluído', 'CONCLUÍDO' ou 'concluido'.
                mask = df_p1.astype(str).apply(lambda x: x.str.contains('CONCLUÍDO', case=False, na=False)).any(axis=1)
                df_finalizados = df_p1[mask].copy()

                if not df_finalizados.empty:
                    # Ordenar pela data de prazo (se existir a coluna) para ver as mais recentes primeiro
                    if 'data_prazo' in df_finalizados.columns:
                        df_finalizados = df_finalizados.sort_values(by='data_prazo', ascending=False)

                    st.success(f"🙌 Glória a Deus! Localizamos {len(df_finalizados)} tarefas finalizadas no histórico.")
                    
                    # 3. EXIBIÇÃO EM TABELA INTERATIVA
                    st.subheader("📜 Detalhamento das Vitórias")
                    st.dataframe(
                        df_finalizados, 
                        use_container_width=True, 
                        hide_index=True
                    )

                    # 4. MÉTRICAS POR RESPONSÁVEL (Cores: Verde e Azul)
                    if 'responsavel' in df_finalizados.columns:
                        st.divider()
                        st.subheader("📈 Resumo de Produtividade")
                        col_graf, col_met = st.columns([2, 1])
                        
                        with col_graf:
                            contagem = df_finalizados['responsavel'].value_counts()
                            st.bar_chart(contagem, color="#2E8B57") # Verde Pentecostal
                        
                        with col_met:
                            for nome, qtd in contagem.items():
                                st.metric(label=f"Servo(a): {nome}", value=f"{qtd} Feitas")

                else:
                    st.warning("Varão, o sistema leu a Página1 mas não encontrou o termo 'CONCLUÍDO' em nenhuma linha.")
                    st.info("Dica: Verifique se na planilha o status foi escrito corretamente pelo App.")
            else:
                st.error("A aba 'Página1' parece não ter registros para gerar o relatório.")

        except Exception as e:
            st.error(f"Erro ao gerar relatório: {e}")
  
# --- PÁGINA: CHAT COM CONFIRMAÇÃO DE LEITURA (v51) ---
    elif st.session_state['page'] == 'chat':
        st.title("💬 Chat Comunicando Igrejas")
        
        try:
            aba_c = conectar_google("Chat")
            dados_chat = aba_c.get_all_records()
            df_full = pd.DataFrame(dados_chat)
            
            # 1. BOTÃO PARA APAGAR SOMENTE AS LIDAS
            if st.button("🗑️ Apagar Mensagens Lidas"):
                with st.spinner("Limpando mensagens confirmadas..."):
                    for i, row in df_full.iterrows():
                        # Se o status for 'Lido', vira 'Baixado' e some da tela
                        if str(row['status']).strip() == 'Lido':
                            aba_c.update_cell(i + 2, 5, "Baixado")
                    st.success("Mensagens lidas foram arquivadas!")
                    st.rerun()

            st.divider()

            # 2. EXIBIÇÃO DAS MENSAGENS (Ativas e Lidas)
            if not df_full.empty:
                # Mostramos o que for 'Ativo' ou 'Lido'
                df_exibir = df_full[df_full['status'].isin(['Ativo', 'Lido'])].copy()
                
                if df_exibir.empty:
                    st.info("🙏 Nenhuma mensagem nova por enquanto.")
                else:
                    for idx, msg in df_exibir.iterrows():
                        user_atual = str(st.session_state['user']).strip().lower()
                        remetente = str(msg['remetente']).strip().lower()
                        destinatario = str(msg['destinatario']).strip().lower()
                        status_msg = str(msg['status']).strip()
                        
                        sou_eu = remetente == user_atual
                        cor = "#2E8B57" if sou_eu else "#4B0082"
                        alinha = "right" if sou_eu else "left"
                        selo_lido = " ✅ (Lida)" if status_msg == "Lido" else " 📩 (Nova)"
                        
                        # Layout da Mensagem
                        with st.container():
                            st.markdown(f"""
                                <div style="background-color:{cor}; padding:10px; border-radius:10px; margin-bottom:5px; text-align:{alinha}; color:white; border-bottom: 2px solid #FFFF00;">
                                    <small>{msg['data_hora']} - {selo_lido}</small><br>
                                    <b>{msg['remetente']} para {msg['destinatario']}:</b><br>{msg['mensagem']}
                                </div>
                            """, unsafe_allow_html=True)
                            
                            # LOGICA DO BOTÃO "LIDO": Só aparece para quem recebeu a mensagem e se ela ainda for 'Ativo'
                            if not sou_eu and status_msg == "Ativo":
                                if st.button(f"✔️ Marcar como lida", key=f"lido_{idx}"):
                                    aba_c.update_cell(idx + 2, 5, "Lido")
                                    st.rerun()

            st.divider()

            # 3. ENVIAR NOVA MENSAGEM
            with st.form("form_envio", clear_on_submit=True):
                st.subheader("📝 Nova Mensagem")
                dest = st.selectbox("Enviar para:", ["Todos", "Willian", "Bia"])
                texto = st.text_area("Sua mensagem:")
                
                if st.form_submit_button("🚀 Enviar"):
                    if texto:
                        agora = obter_agora_br().strftime('%d/%m %H:%M')
                        # Status inicial é sempre 'Ativo'
                        aba_c.append_row([agora, st.session_state['user'], dest, texto, "Ativo"])
                        st.success("Enviada!")
                        st.rerun()

        except Exception as e:
            st.error(f"Erro no Chat: {e}")
