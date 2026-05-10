import streamlit as st
import pandas as pd
import os

# 1. Configuração Global da Página
st.set_page_config(
    page_title="VINI AI - Ecossistema Sensorial", 
    page_icon="🍷", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Setup Inicial (Garante que as pastas existam para evitar erros)
os.makedirs("data", exist_ok=True)
os.makedirs("modulos", exist_ok=True)

# 3. Função Temporária (Placeholder para os módulos que vamos criar)
def render_em_construcao(nome_modulo, agente_responsavel):
    st.info(f"🚧 **{nome_modulo}** está em construção.")
    st.caption(f"Agente responsável: {agente_responsavel}")

# 4. Cabeçalho do App
st.title("🍷 VINI AI")
st.markdown("*A ciência do seu paladar.*")
st.divider()

# 5. Banco de Dados Simulado (CSVs)
ARQUIVO_USUARIOS = "data/usuarios.csv"

def carregar_usuarios():
    try:
        # Tenta ler o arquivo se ele existir
        if os.path.exists(ARQUIVO_USUARIOS):
            return pd.read_csv(ARQUIVO_USUARIOS)
        else:
            # Se não existir, cria o arquivo físico na hora e devolve vazio
            df_vazio = pd.DataFrame(columns=["user_id", "nome", "tribo_dna", "restricoes"])
            df_vazio.to_csv(ARQUIVO_USUARIOS, index=False)
            return df_vazio
    except Exception:
        # Em caso de qualquer outro erro de leitura, segura o app e não deixa travar
        return pd.DataFrame(columns=["user_id", "nome", "tribo_dna", "restricoes"])

df_usuarios = carregar_usuarios()

# 6. Sidebar (Menu Lateral) - Seletor de Realidade
with st.sidebar:
    st.header("Entrar no Ecossistema")
    modo_app = st.radio("Selecione a Visão:", ["👤 Área do Cliente (B2C)", "🏢 Painel do Restaurante (B2B)"])
    st.divider()

    if modo_app == "👤 Área do Cliente (B2C)":
        nome_input = st.text_input("Digite seu nome:", placeholder="Ex: Alex")

# 7. Roteamento Principal (A Lógica de Navegação)
if modo_app == "🏢 Painel do Restaurante (B2B)":
    from modulos import b2b
    b2b.exibir_modulo()

elif modo_app == "👤 Área do Cliente (B2C)" and nome_input:
    # Busca o usuário ignorando maiúsculas/minúsculas
    usuario_logado = df_usuarios[df_usuarios['nome'].str.lower() == nome_input.lower()]
    
    # CENÁRIO A: Usuário Novo (Precisa fazer o Onboarding)
    if usuario_logado.empty:
        st.warning(f"Olá, {nome_input}! Vimos que você ainda não tem um DNA Sensorial mapeado.")
        
        from modulos import dna
        dna.exibir_teste(nome_input)
        
    # CENÁRIO B: Usuário Existente (Acessa o ecossistema)
    else:
        tribo_atual = usuario_logado.iloc[0]['tribo_dna']
        st.success(f"Bem-vindo de volta, {nome_input}! Sua tribo atual é: **{tribo_atual}**")
        
        # ---> ADICIONAMOS A ABA DO RESTAURANTE AQUI <---
        aba_concierge, aba_catalogo, aba_restaurante, aba_evolucao = st.tabs([
            "🍽️ Concierge Digital", 
            "📖 Catálogo & Check-in",
            "🍷 Modo Restaurante", 
            "📈 Minha Evolução"
        ])
        
        with aba_concierge:
            from modulos import concierge
            concierge.exibir_modulo(usuario_logado)
            
        with aba_catalogo:
            from modulos import catalogo
            catalogo.exibir_modulo(usuario_logado)
            
        # ---> CHAMADA DO NOVO MÓDULO <---
        with aba_restaurante:
            from modulos import restaurante
            restaurante.exibir_modulo(usuario_logado)
            
        with aba_evolucao:
            from modulos import dashboard
            dashboard.exibir_modulo(usuario_logado)

elif modo_app == "👤 Área do Cliente (B2C)" and not nome_input:
    st.info("👈 Por favor, insira seu nome no menu lateral para acessar a sua jornada sensorial.")