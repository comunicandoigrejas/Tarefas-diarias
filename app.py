import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, time
import time as t_time

# --- Configuração da Página ---
st.set_page_config(page_title="Gestão Comunicando Igrejas", layout="wide", page_icon="🙏")

# --- Cores e Estilo (CSS Personalizado) ---
# Aqui aplicamos as cores: Azul, Roxo, Verde, Laranja, Amarelo
st.markdown("""
    <style>
    .main-header {color: #4B0082; text-align: center; font-weight: bold;} /* Roxo */
    .stButton>button {
        background-color: #0000FF; /* Azul */
        color: white;
        border-radius: 10px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #FFA500; /* Laranja no hover */
        color: black;
    }
    .success-box {background-color: #32CD32; padding: 10px; border-radius: 5px; color: white;} /* Verde */
    .warning-box {background-color: #FFA500; padding: 10px; border-radius: 5px; color: black;} /* Laranja */
    .danger-box {background-color: #FF4500; padding: 10px; border-radius: 5px; color: white;} /* Vermelho/Laranja escuro */
    .info-box {background-color: #FFFF00; padding: 10px; border-radius: 5px; color: black;} /* Amarelo */
    </style>
""", unsafe_allow_html=True)

# --- Banco de Dados (SQLite) ---
def init_db():
    conn = sqlite3.connect('tarefas_ci.db')
    c = conn.cursor()
    # Tabela de Tarefas
    c.execute('''CREATE TABLE IF NOT EXISTS tarefas
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  titulo TEXT,
                  descricao TEXT,
                  responsavel TEXT,
                  data_prazo DATE,
                  hora_prazo TIME,
                  status TEXT,
                  observacoes TEXT,
                  motivo_adiamento TEXT,
                  criado_por TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- Funções Auxiliares ---
def get_connection():
    return sqlite3.connect('tarefas_ci.db')

def login():
    st.sidebar.title("🔐 Acesso Restrito")
    usuario = st.sidebar.text_input("Usuário")
    senha = st.sidebar.text_input("Senha", type="password")
    
    if st.sidebar.button("Entrar no Mistério"):
        # Senhas simples para teste (Varão, mude isso depois se quiser algo mais robusto)
        if usuario == "willian" and senha == "admin123":
            st.session_state['logged_in'] = True
            st.session_state['user'] = "Willian (Admin)"
            st.session_state['role'] = "admin"
            st.rerun()
        elif usuario == "aprendiz" and senha == "ap123":
            st.session_state['logged_in'] = True
            st.session_state['user'] = "Aprendiz"
            st.session_state['role'] = "aprendiz"
            st.rerun()
        else:
            st.sidebar.error("Vigiai! Usuário ou senha incorretos.")

def logout():
    if st.sidebar.button("Sair"):
        st.session_state['logged_in'] = False
        st.rerun()

# --- Lógica Principal ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h1 class='main-header'>Comunicando Igrejas - Gestão de Tarefas</h1>", unsafe_allow_html=True)
    st.info("Faça login na barra lateral para acessar o sistema, varão.")
    login()
else:
    logout()
    user_name = st.session_state['user']
    user_role = st.session_state['role']
    
    st.markdown(f"<h2 style='color: #4B0082;'>A paz do Senhor, {user_name}!</h2>", unsafe_allow_html=True)

    # Menu de Navegação (Botões como pedido)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🏠 Início / Avisos"):
            st.session_state['page'] = 'home'
    with col2:
        if st.button("📝 Agendar Tarefa"):
            st.session_state['page'] = 'add'
    with col3:
        if st.button("📋 Minhas Pendências"):
            st.session_state['page'] = 'list'
    with col4:
        if st.button("📊 Relatórios / Concluídos"):
            st.session_state['page'] = 'report'

    if 'page' not in st.session_state:
        st.session_state['page'] = 'home'

    # --- PÁGINA: INÍCIO (AVISOS) ---
    if st.session_state['page'] == 'home':
        st.markdown("---")
        st.subheader("⚠️ Avisos e Urgências")
        
        conn = get_connection()
        # Busca tarefas pendentes que já passaram do prazo
        query = "SELECT * FROM tarefas WHERE status = 'Pendente'"
        df = pd.read_sql(query, conn)
        conn.close()

        if not df.empty:
            df['prazo_completo'] = pd.to_datetime(df['data_prazo'].astype(str) + ' ' + df['hora_prazo'].astype(str))
            agora = datetime.now()
            
            # Filtra tarefas atrasadas
            atrasadas = df[df['prazo_completo'] < agora]
            
            # Filtra tarefas para 'agora' (próxima hora)
            hoje = df[(df['prazo_completo'] >= agora) & (df['prazo_completo'] <= agora + pd.Timedelta(hours=1))]

            if not atrasadas.empty:
                st.error(f"🔥 VIGIAI VARÃO! Existem {len(atrasadas)} tarefas ATRASADAS!")
                for index, row in atrasadas.iterrows():
                    st.markdown(f"""
                    <div class='danger-box'>
                        <strong>ATRASADO:</strong> {row['titulo']} ({row['responsavel']}) - Era para: {row['prazo_completo']}
                    </div>
                    <br>
                    """, unsafe_allow_html=True)
            else:
                st.success("Glória a Deus, nenhuma tarefa atrasada no momento.")

            if not hoje.empty:
                st.warning(f"⏳ Atenção: {len(hoje)} tarefas para a próxima hora.")
                for index, row in hoje.iterrows():
                    st.markdown(f"**{row['titulo']}** - Responsável: {row['responsavel']}")
        else:
            st.info("Nenhuma tarefa pendente registrada. A obra está em dia!")

    # --- PÁGINA: AGENDAR TAREFA ---
    elif st.session_state['page'] == 'add':
        st.markdown("---")
        st.subheader("📝 Nova Missão")
        
        with st.form("nova_tarefa"):
            titulo = st.text_input("Título da Tarefa")
            desc = st.text_area("Descrição do Serviço")
            
            # Se for Admin, pode escolher quem faz. Se for aprendiz, só para ela mesma (ou define regra aqui)
            opcoes_resp = ["Willian (Admin)", "Aprendiz"]
            responsavel = st.selectbox("Quem vai realizar essa obra?", opcoes_resp, index=0 if user_role == 'admin' else 1)
            
            col_d, col_h = st.columns(2)
            d_prazo = col_d.date_input("Data do Prazo", date.today())
            h_prazo = col_h.time_input("Hora do Prazo", time(9, 0)) # Começa as 9h
            
            submit = st.form_submit_button("Agendar na Graça")
            
            if submit:
                conn = get_connection()
                c = conn.cursor()
                c.execute("""INSERT INTO tarefas (titulo, descricao, responsavel, data_prazo, hora_prazo, status, criado_por)
                             VALUES (?, ?, ?, ?, ?, ?, ?)""",
                          (titulo, desc, responsavel, d_prazo, str(h_prazo), 'Pendente', user_name))
                conn.commit()
                conn.close()
                st.success(f"Bênção! A tarefa '{titulo}' foi agendada para {responsavel}.")

    # --- PÁGINA: LISTAR E GERENCIAR ---
    elif st.session_state['page'] == 'list':
        st.markdown("---")
        st.subheader("🔨 Mãos à Obra (Pendentes)")
        
        conn = get_connection()
        # Se for admin vê tudo, se for aprendiz vê só o dela
        if user_role == 'admin':
            df = pd.read_sql("SELECT * FROM tarefas WHERE status = 'Pendente' OR status = 'Adiado'", conn)
        else:
            df = pd.read_sql(f"SELECT * FROM tarefas WHERE (status = 'Pendente' OR status = 'Adiado') AND responsavel = 'Aprendiz'", conn)
        conn.close()

        if df.empty:
            st.info("Nenhuma pendência, varão.")
        else:
            for index, row in df.iterrows():
                with st.expander(f"📌 {row['titulo']} - Prazo: {row['data_prazo']} às {row['hora_prazo']} ({row['status']})"):
                    st.write(f"**Descrição:** {row['descricao']}")
                    st.write(f"**Responsável:** {row['responsavel']}")
                    if row['status'] == 'Adiado':
                        st.warning(f"⚠️ Motivo do último adiamento: {row['motivo_adiamento']}")

                    col_a, col_b = st.columns(2)
                    
                    # Concluir Tarefa
                    with col_a:
                        with st.form(key=f"concluir_{row['id']}"):
                            obs = st.text_area("Observações da Conclusão")
                            btn_concluir = st.form_submit_button("✅ Concluir Obra")
                            if btn_concluir:
                                conn = get_connection()
                                c = conn.cursor()
                                c.execute("UPDATE tarefas SET status='Concluído', observacoes=? WHERE id=?", (obs, row['id']))
                                conn.commit()
                                conn.close()
                                st.success("Glória! Tarefa finalizada.")
                                t_time.sleep(1)
                                st.rerun()

                    # Adiar Tarefa
                    with col_b:
                        with st.form(key=f"adiar_{row['id']}"):
                            nova_data = st.date_input("Nova Data", date.today())
                            nova_hora = st.time_input("Nova Hora", time(12,0))
                            motivo = st.text_input("Motivo do Adiamento (Justifique, varão)")
                            btn_adiar = st.form_submit_button("📅 Adiar Serviço")
                            if btn_adiar:
                                if motivo:
                                    conn = get_connection()
                                    c = conn.cursor()
                                    c.execute("""UPDATE tarefas 
                                                 SET status='Adiado', motivo_adiamento=?, data_prazo=?, hora_prazo=? 
                                                 WHERE id=?""", 
                                              (motivo, nova_data, str(nova_hora), row['id']))
                                    conn.commit()
                                    conn.close()
                                    st.warning("Serviço adiado. Não deixe para amanhã o que pode fazer hoje, mas se precisar, mudamos a data!")
                                    t_time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("Precisa explicar o motivo do adiamento, irmão.")

    # --- PÁGINA: RELATÓRIOS ---
    elif st.session_state['page'] == 'report':
        st.markdown("---")
        st.subheader("📚 Livro das Obras (Concluídas)")
        
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM tarefas WHERE status = 'Concluído'", conn)
        conn.close()
        
        if df.empty:
            st.info("Ainda não há tarefas concluídas para testemunhar.")
        else:
            # Mostra tabela
            st.dataframe(df)
            
            # Botão de Exportar
            csv = df.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="📥 Baixar Relatório (CSV)",
                data=csv,
                file_name='relatorio_obras_concluidas.csv',
                mime='text/csv',
            )
            
            st.markdown("### 📊 Estatísticas Rápidas")
            st.metric(label="Total de Bênçãos Concluídas", value=len(df))
