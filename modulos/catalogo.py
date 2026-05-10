import streamlit as st
import pandas as pd
import os
import json
import time
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
import fitz  # PyMuPDF
from datetime import datetime
import math

ARQUIVO_VINHOS = "data/vinhos.csv"
ARQUIVO_HISTORICO = "data/historico.csv"
ARQUIVO_INVENTARIO = "data/inventario.csv"


# ==========================================
# MOTOR MATEMÁTICO (MACHINE LEARNING)
# ==========================================
def calcular_distancia_euclidiana(vetor_usuario, vetor_vinho):
    """Calcula a distância entre o DNA do usuário e a química do vinho"""
    return math.sqrt(sum((u - v) ** 2 for u, v in zip(vetor_usuario, vetor_vinho)))

# ==========================================
# CONFIGURAÇÕES E CONSTANTES
# ==========================================
ARQUIVO_VINHOS = "data/vinhos.csv"
ARQUIVO_HISTORICO = "data/historico.csv"
ARQUIVO_INVENTARIO = "data/inventario.csv"

# Configuração da API do Gemini
load_dotenv()
CHAVE_API = os.getenv("GEMINI_API_KEY")
if CHAVE_API:
    genai.configure(api_key=CHAVE_API)

# ... (aqui continua o resto do seu código com as funções de inicializar_memoria, carregar_vinhos, etc) ...


# Configuração da API do Gemini
load_dotenv()
CHAVE_API = os.getenv("GEMINI_API_KEY")
if CHAVE_API:
    genai.configure(api_key=CHAVE_API)

# --- INICIALIZAÇÃO DE MEMÓRIA ---
def inicializar_memoria():
    if 'resultado_scan' not in st.session_state:
        st.session_state.resultado_scan = None
    if 'vinho_em_foco' not in st.session_state:
        st.session_state.vinho_em_foco = None
    if 'rascunho_ia' not in st.session_state:
        st.session_state.rascunho_ia = None

def carregar_vinhos():
    if os.path.exists(ARQUIVO_VINHOS):
        return pd.read_csv(ARQUIVO_VINHOS)
    return pd.DataFrame()

def carregar_historico_pessoal(user_id):
    if os.path.exists(ARQUIVO_HISTORICO):
        df_hist = pd.read_csv(ARQUIVO_HISTORICO)
        return df_hist[df_hist['user_id'] == user_id]
    return pd.DataFrame()

def carregar_inventario(user_id):
    if os.path.exists(ARQUIVO_INVENTARIO):
        df_inv = pd.read_csv(ARQUIVO_INVENTARIO)
        return df_inv[df_inv['user_id'] == user_id]
    return pd.DataFrame(columns=["log_id", "user_id", "vinho_id", "quantidade", "status"])

def salvar_vinho_novo(novo_vinho_dict):
    df_vinhos = carregar_vinhos()
    
    # 1. Verifica se já existe para evitar duplicação
    if not df_vinhos.empty:
        existente = df_vinhos[(df_vinhos['nome_base'].str.contains(novo_vinho_dict.get('nome_base', ''), case=False, na=False)) & 
                              (df_vinhos['safra'].astype(str) == str(novo_vinho_dict.get('safra', '')))]
        if not existente.empty:
            return existente.iloc[0]['vinho_id'], existente.iloc[0]

    # 2. Gera o novo ID seguindo o seu padrão
    novo_id = f"vin_{len(df_vinhos) + 1:04d}" if not df_vinhos.empty else "vin_0001"
    novo_vinho_dict['vinho_id'] = novo_id
    
    # 3. Transforma o dicionário num DataFrame de 1 linha
    df_novo = pd.DataFrame([novo_vinho_dict])

    # 4. BLINDAGEM DO BANCO DE DADOS (Anti vírgulas vazias)
    # Garante que a nova linha tenha EXATAMENTE as mesmas colunas que o arquivo CSV original
    if not df_vinhos.empty:
        for col in df_vinhos.columns:
            if col not in df_novo.columns:
                if "nota" in col.lower():
                    df_novo[col] = 3.0  # Se for uma coluna de nota de tribo faltando, põe a média
                else:
                    df_novo[col] = "N/D" # Qualquer outra coluna faltando, preenche com N/D
                    
    # 5. Adiciona e salva
    df_vinhos = pd.concat([df_vinhos, df_novo], ignore_index=True)
    
    # Previne qualquer erro residual de NaN (que causa as vírgulas ,,, no CSV)
    df_vinhos.fillna("N/D", inplace=True)
    df_vinhos.to_csv(ARQUIVO_VINHOS, index=False)
    
    return novo_id, df_novo.iloc[0]

def salvar_checkin(user_id, vinho_id, nota, acidez, corpo, tanino, tribo_momento):
    # 1. SALVA NO DIÁRIO DO USUÁRIO
    if os.path.exists(ARQUIVO_HISTORICO):
        df_hist = pd.read_csv(ARQUIVO_HISTORICO)
    else:
        df_hist = pd.DataFrame(columns=["log_id", "user_id", "vinho_id", "data", "nota_geral", "acidez", "corpo", "tanino", "tribo_momento"])
    
    novo_log_id = f"log_{len(df_hist) + 1:04d}"
    novo_registro = pd.DataFrame([{
        "log_id": novo_log_id, "user_id": user_id, "vinho_id": vinho_id,
        "data": datetime.now().strftime("%Y-%m-%d"), "nota_geral": nota,
        "acidez": acidez, "corpo": corpo, "tanino": tanino, "tribo_momento": tribo_momento
    }])
    
    df_hist = pd.concat([df_hist, novo_registro], ignore_index=True)
    df_hist.to_csv(ARQUIVO_HISTORICO, index=False)

    # 2. ALGORITMO DE MÉDIA MÓVEL (Atualiza o Global Master Data)
    df_vinhos = carregar_vinhos()
    
    # Pega TODAS as notas que a Tribo do usuário já deu para este Vinho específico
    notas_da_tribo = df_hist[(df_hist['vinho_id'] == vinho_id) & (df_hist['tribo_momento'] == tribo_momento)]['nota_geral']
    
    if not notas_da_tribo.empty:
        nova_media_global = round(notas_da_tribo.mean(), 1) # Calcula a média matemática
        coluna_nota_tribo = f"nota_{tribo_momento.split()[1].lower().replace('á', 'a')}"
        
        # Substitui o "chute da IA" pela média real dos humanos
        df_vinhos.loc[df_vinhos['vinho_id'] == vinho_id, coluna_nota_tribo] = nova_media_global
        df_vinhos.to_csv(ARQUIVO_VINHOS, index=False)

def gerenciar_inventario(user_id, vinho_id, status, operacao="add"):
    if os.path.exists(ARQUIVO_INVENTARIO):
        df_inv = pd.read_csv(ARQUIVO_INVENTARIO)
    else:
        df_inv = pd.DataFrame(columns=["log_id", "user_id", "vinho_id", "quantidade", "status"])

    mask = (df_inv['user_id'] == user_id) & (df_inv['vinho_id'] == vinho_id) & (df_inv['status'] == status)
    
    if df_inv[mask].empty:
        if operacao in ["add", "set"]:
            novo_log_id = f"inv_{len(df_inv) + 1:04d}"
            novo_registro = pd.DataFrame([{
                "log_id": novo_log_id, "user_id": user_id, "vinho_id": vinho_id,
                "quantidade": 1 if status == "adega" else 0, "status": status
            }])
            df_inv = pd.concat([df_inv, novo_registro], ignore_index=True)
    else:
        idx = df_inv[mask].index[0]
        if operacao == "add":
            df_inv.at[idx, 'quantidade'] += 1
        elif operacao == "sub":
            df_inv.at[idx, 'quantidade'] -= 1
            if df_inv.at[idx, 'quantidade'] <= 0:
                df_inv = df_inv.drop(idx)
                
    df_inv.to_csv(ARQUIVO_INVENTARIO, index=False)


# --- NOVA FUNÇÃO: CHEF DA ADEGA (Criada para consultar o inventário) ---
def exibir_chef_estoque_fisico(user_id):
    st.divider()
    st.subheader("👨‍🍳 Chef da Minha Adega")
    st.markdown("Sugestões de harmonização baseadas **exclusivamente** no que você tem em casa.")

    try:
        df_vinhos = carregar_vinhos()
        df_inventario = carregar_inventario(user_id)
        
        # Filtra apenas o que está marcado como 'adega' física
        meu_estoque = df_inventario[df_inventario['status'] == 'adega']
        
        if meu_estoque.empty:
            st.warning("Adicione vinhos à sua adega física no Catálogo para o Chef poder ajudar.")
            return

        # Cruza os dados de inventário com o catálogo para obter uvas, safra e nome
        df_cruzado = pd.merge(meu_estoque, df_vinhos, on='vinho_id', how='inner')

        # Keys únicas para não dar conflito com o Streamlit
        prato = st.text_input("O que você vai comer hoje?", placeholder="Ex: Picanha, Pizza de Calabresa, Sushi...", key="input_chef_adega")

        if st.button("Consultar o Chef", type="primary", key="btn_chef_adega"):
            if prato:
                with st.spinner("Analisando suas garrafas..."):
                    # Prepara a lista do estoque real para enviar à IA
                    lista_vinhos = df_cruzado.apply(
                        lambda x: f"- {x['nome_base']} ({x['uvas']}) | Safra: {x['safra']} | Qtd: {x['quantidade']}", axis=1
                    ).tolist()
                    
                    prompt = f"""
                    Aja como Master Sommelier do VINI AI. O usuário vai comer: {prato}.
                    Ele tem APENAS estes vinhos em casa:
                    {chr(10).join(lista_vinhos)}
                    
                    Selecione as ATÉ 5 MELHORES opções em ordem de preferência.
                    Se não houver 5 opções boas, mostre apenas as que harmonizam.
                    Explique brevemente (uma frase) por que a química daquele vinho (acidez, tanino, corpo) combina com o prato.
                    """
                    
                    try:
                        model = genai.GenerativeModel("gemini-2.5-flash")
                        res = model.generate_content(prompt)
                        st.success("🍷 **As melhores escolhas do seu estoque:**")
                        st.write(res.text)
                    except Exception as e:
                        st.error(f"Erro na comunicação com a IA: {e}")
            else:
                st.warning("Por favor, informe o prato para o Chef.")
    except Exception as e:
        st.error(f"Erro ao carregar os dados do Chef: {e}")
# ------------------------------------------------------------------------


def exibir_modulo(usuario_logado_df):
    inicializar_memoria()
    st.subheader("📚 Ecossistema VINI AI")
    
    user_id = usuario_logado_df.iloc[0]['user_id']
    tribo_atual = usuario_logado_df.iloc[0]['tribo_dna']
    coluna_nota_usuario = f"nota_{tribo_atual.split()[1].lower().replace('á', 'a')}"

    aba_global, aba_pessoal, aba_scanner = st.tabs([
        "🌍 Catálogo Global", 
        "🏠 Meu Espaço (Adega & Notas)", 
        "📸 Scanner Inteligente"
    ])

    # ==========================================
    # ABA 1: CATÁLOGO GLOBAL 
    # ==========================================
    with aba_global:
        st.markdown("### Explore e gerencie suas descobertas")
        df_vinhos = carregar_vinhos()
        
        if not df_vinhos.empty:
            with st.expander("🔎 Filtros de Busca"):
                col_f1, col_f2 = st.columns(2)
                busca_nome = col_f1.text_input("Buscar por Nome/Produtor:")
                busca_uva = col_f2.text_input("Buscar por Uva:")
            
            df_filtrado = df_vinhos.copy()
            if busca_nome:
                df_filtrado = df_filtrado[df_filtrado['nome_base'].str.contains(busca_nome, case=False, na=False) | 
                                          df_filtrado['produtor'].str.contains(busca_nome, case=False, na=False)]
            if busca_uva:
                df_filtrado = df_filtrado[df_filtrado['uvas'].str.contains(busca_uva, case=False, na=False)]
            
            st.dataframe(
                df_filtrado[['nome_base', 'safra', 'produtor', 'uvas', coluna_nota_usuario]], 
                use_container_width=True,
                column_config={coluna_nota_usuario: st.column_config.NumberColumn(f"Nota {tribo_atual}", format="⭐ %.1f")},
                hide_index=True
            )
            
            st.divider()
            st.markdown("#### ⚙️ Interagir com um Vinho")
            opcoes_vinhos = df_filtrado.apply(lambda x: f"{x['nome_base']} ({x['safra']}) - ID: {x['vinho_id']}", axis=1).tolist()
            vinho_selecionado = st.selectbox("Selecione um vinho da lista acima:", [""] + opcoes_vinhos)
            
            if vinho_selecionado:
                v_id_selecionado = vinho_selecionado.split("ID: ")[-1]
                
                col_b1, col_b2, col_b3 = st.columns(3)
                if col_b1.button("📝 Avaliar (Já bebi)", use_container_width=True):
                    st.session_state.vinho_em_foco = df_vinhos[df_vinhos['vinho_id'] == v_id_selecionado].iloc[0].to_dict()
                    st.rerun()
                if col_b2.button("🛒 Tenho na Adega (+1)", use_container_width=True):
                    gerenciar_inventario(user_id, v_id_selecionado, "adega", "add")
                    st.success("Garrafa adicionada ao seu estoque físico!")
                if col_b3.button("⭐ Por na Wishlist", use_container_width=True):
                    gerenciar_inventario(user_id, v_id_selecionado, "wishlist", "set")
                    st.success("Vinho adicionado à sua Lista de Desejos!")

        else:
            st.info("Catálogo vazio. Use o Scanner!")

    # ==========================================
    # ABA 2: MEU ESPAÇO 
    # ==========================================
    with aba_pessoal:
        st.markdown("### Seu ERP Pessoal de Vinhos")
        sub_estoque, sub_wishlist, sub_notas = st.tabs(["📦 Estoque Físico", "⭐ Wishlist", "🍷 Diário de Notas"])
        
        df_inv = carregar_inventario(user_id)
        df_hist = carregar_historico_pessoal(user_id)
        df_vinhos_base = carregar_vinhos()
        
        with sub_estoque:
            st.write("Controle das garrafas que você tem em casa.")
            df_adega = df_inv[df_inv['status'] == 'adega']
            if not df_adega.empty and not df_vinhos_base.empty:
                df_adega_view = pd.merge(df_adega, df_vinhos_base[['vinho_id', 'nome_base', 'safra']], on='vinho_id', how='left')
                for _, row in df_adega_view.iterrows():
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([3, 1, 1])
                        c1.markdown(f"**{row['nome_base']}** ({row['safra']})")
                        c2.markdown(f"📦 Qtd: **{row['quantidade']}**")
                        if c3.button("Abrir Garrafa (-1)", key=f"sub_{row['vinho_id']}"):
                            gerenciar_inventario(user_id, row['vinho_id'], "adega", "sub")
                            st.rerun()
            else:
                st.info("Sua adega física está vazia.")
            
            # --- CHAMADA DO CHEF DA ADEGA INSERIDA AQUI ---
            exibir_chef_estoque_fisico(user_id)
            # ----------------------------------------------

        with sub_wishlist:
            df_wish = df_inv[df_inv['status'] == 'wishlist']
            if not df_wish.empty and not df_vinhos_base.empty:
                df_wish_view = pd.merge(df_wish, df_vinhos_base[['vinho_id', 'nome_base', 'safra']], on='vinho_id', how='left')
                for _, row in df_wish_view.iterrows():
                    st.markdown(f"- ⭐ **{row['nome_base']}** ({row['safra']})")
            else:
                st.info("Sua lista de desejos está vazia.")

        with sub_notas:
            if not df_hist.empty and not df_vinhos_base.empty:
                df_minha_adega = pd.merge(df_hist, df_vinhos_base[['vinho_id', 'nome_base', 'safra']], on='vinho_id', how='left')
                df_minha_adega = df_minha_adega.sort_values(by='data', ascending=False)
                st.dataframe(df_minha_adega[['data', 'nome_base', 'safra', 'nota_geral']], use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma avaliação feita ainda.")

   # ==========================================
    # ABA 3: SCANNER INTELIGENTE E AVALIAÇÃO
    # ==========================================
    with aba_scanner:
        st.markdown("### 📸 Descubra tudo sobre uma garrafa")
        st.write("Fotografe o rótulo. A IA extrairá os dados, preencherá as lacunas técnicas e cruzará com o Master Data.")
        
        if not CHAVE_API:
            st.warning("⚠️ Chave da API do Gemini não encontrada.")
            return

        # Vetor do usuário logado para o cálculo KNN
        vetor_usuario = [
            float(usuario_logado_df.iloc[0].get('nota_delicado', 3.0)),
            float(usuario_logado_df.iloc[0].get('nota_classico', 3.0)),
            float(usuario_logado_df.iloc[0].get('nota_robusto', 3.0)),
            float(usuario_logado_df.iloc[0].get('nota_audaz', 3.0))
        ]

        metodo_captura = st.radio("Como enviar a imagem do rótulo?", ["📸 Câmera", "📂 Subir Arquivo"], horizontal=True)
        imagens_processadas = []

        if metodo_captura == "📸 Câmera":
            foto_cam = st.camera_input("Fotografe o rótulo frontal")
            if foto_cam: imagens_processadas.append(Image.open(foto_cam))
        else:
            arquivo_up = st.file_uploader("Selecione a foto do rótulo", type=['png', 'jpg', 'jpeg'])
            if arquivo_up: imagens_processadas.append(Image.open(arquivo_up))

        if imagens_processadas and st.button("🔎 Analisar Rótulo", type="primary", use_container_width=True):
            model = genai.GenerativeModel("gemini-2.5-flash")
            
            with st.spinner("Extraindo dados, pesquisando o vinho na internet e cruzando com o Master Data..."):
                prompt = """
                Você é um Master Sommelier Investigador de elite. 
                A imagem anexada é um rótulo de vinho. 
                
                Sua missão NÃO É apenas ler o texto da imagem. Sua missão é IDENTIFICAR qual é este vinho e pesquisar na sua base de conhecimento global na internet TUDO sobre ele para trazer os DADOS REAIS E EXATOS de mercado.
                
                OBRIGAÇÕES:
                1. PRODUTOR: Descubra o nome real e oficial da vinícola que produz.
                2. TEOR ALCOÓLICO: Qual é o volume alcoólico (ABV) exato de mercado desta garrafa? (Pesquise!)
                3. UVAS: Quais as uvas reais que compõem este vinho?
                4. REGIÃO: Traga a região e o país corretos.
                5. NENHUM CAMPO VAZIO: Nunca retorne 'N/D'. Se for preciso, estime com base em vinhos idênticos da mesma região.
                
                Retorne APENAS um JSON estrito:
                {
                  "nome_base": "Nome do Vinho",
                  "safra": "Ano ou NV",
                  "produtor": "Nome da Vinícola real",
                  "regiao": "Região - País",
                  "uvas": "Lista de uvas corretas",
                  "teor_alcoolico": 13.5,
                  "estimativa_ia": [nota_delicado, nota_classico, nota_robusto, nota_audaz]
                }
                """
                
                try:
                    res = model.generate_content(imagens_processadas + [prompt])
                    dados_extraidos = json.loads(res.text.replace('```json', '').replace('```', '').strip())
                    
                    df_vinhos = carregar_vinhos()
                    
                    # Tenta achar no banco batendo Nome E Safra
                    if not df_vinhos.empty:
                        match_db = df_vinhos[
                            (df_vinhos['nome_base'].str.contains(dados_extraidos['nome_base'], case=False, na=False)) & 
                            (df_vinhos['safra'].astype(str) == str(dados_extraidos['safra']))
                        ]
                    else:
                        match_db = pd.DataFrame()
                    
                    st.divider()
                    
                    if not match_db.empty:
                        st.success("✅ Este vinho já está no Catálogo Global!")
                        vinho_real = match_db.iloc[0]
                        nota_da_tribo = vinho_real.get(coluna_nota_usuario, "Sem avaliações")
                        
                        vetor_real = [vinho_real['nota_delicado'], vinho_real['nota_classico'], vinho_real['nota_robusto'], vinho_real['nota_audaz']]
                        distancia = calcular_distancia_euclidiana(vetor_usuario, vetor_real)
                        afinidade = max(0, min(100, 100 - (distancia * 15)))
                        
                        c1, c2 = st.columns([2, 1])
                        with c1:
                            st.markdown(f"### {vinho_real['nome_base']} ({vinho_real['safra']})")
                            st.write(f"🍇 **Uvas:** {vinho_real['uvas']} | 🏭 **Produtor:** {vinho_real['produtor']}")
                            if isinstance(nota_da_tribo, (int, float)):
                                st.write(f"⭐ **Nota da Tribo ({tribo_atual}):** {nota_da_tribo:.1f}/5.0")
                            else:
                                st.write(f"⭐ **Nota da Tribo ({tribo_atual}):** {nota_da_tribo}")
                        
                        with c2:
                            with st.container(border=True):
                                st.metric("Seu Match (KNN)", f"{afinidade:.1f}%")
                                if afinidade > 80: st.success("Altamente Recomendado!")
                                elif afinidade > 60: st.warning("Boa escolha.")
                                else: st.error("Fora do seu perfil.")
                                    
                    else:
                        st.info("🆕 Vinho novo! Buscamos os dados de mercado na internet para o Master Data...")
                        
                        vetor_ia = dados_extraidos['estimativa_ia']
                        distancia = calcular_distancia_euclidiana(vetor_usuario, vetor_ia)
                        afinidade = max(0, min(100, 100 - (distancia * 15)))
                        
                        c1, c2 = st.columns([2, 1])
                        with c1:
                            st.markdown(f"### {dados_extraidos['nome_base']} ({dados_extraidos['safra']})")
                            st.write(f"🍇 **Uvas:** {dados_extraidos['uvas']} | 📍 **Região:** {dados_extraidos['regiao']}")
                            st.write(f"🏭 **Produtor:** {dados_extraidos['produtor']} | 🍷 **Álcool:** {dados_extraidos['teor_alcoolico']}%")
                            st.caption("✔️ Dados oficiais validados pela pesquisa do Agente IA.")
                        
                        with c2:
                            with st.container(border=True):
                                st.metric("Match Estimado", f"{afinidade:.1f}%")
                        
                        st.session_state.rascunho_ia = [dados_extraidos]
                        
                except Exception as e:
                    st.error(f"Erro na leitura ou processamento do rótulo: {e}")

        # FLUXO DE APROVAÇÃO (Agora perfeitamente alinhado)
        if st.session_state.rascunho_ia is not None:
            st.markdown("#### ➕ Validar e Adicionar à Lista Mestra")
            df_editado = st.data_editor(
                pd.DataFrame(st.session_state.rascunho_ia)[['nome_base', 'safra', 'produtor', 'uvas', 'regiao', 'teor_alcoolico']], 
                num_rows="dynamic", 
                use_container_width=True
            )
            
            if st.button("✅ Confirmar e Salvar no Master Data", type="primary"):
                for index, row in df_editado.iterrows():
                    v_comp = row.to_dict()
                    
                    if index < len(st.session_state.rascunho_ia):
                        estimativa = st.session_state.rascunho_ia[index].get('estimativa_ia', [3.0, 3.0, 3.0, 3.0])
                    else:
                        estimativa = [3.0, 3.0, 3.0, 3.0]
                    
                    v_comp.update({
                        'nota_delicado': estimativa[0], 
                        'nota_classico': estimativa[1], 
                        'nota_robusto': estimativa[2], 
                        'nota_audaz': estimativa[3]
                    })
                    
                    salvar_vinho_novo(v_comp)
                
                st.session_state.rascunho_ia = None
                st.success("Operação Concluída! Banco de dados atualizado com perfeição estrutural.")
                time.sleep(1.5)
                st.rerun()

    # --- FORMULÁRIO DE CHECK-IN ---
    if st.session_state.vinho_em_foco is not None:
        v_info = st.session_state.vinho_em_foco
        st.divider()
        st.markdown(f"### 🍷 Avaliando: {v_info['nome_base']}")
        
        nota_geral = st.slider("Sua Nota Geral (Isso afetará a média global da sua Tribo!)", 1.0, 5.0, 3.0, 0.5)
        c1, c2, c3 = st.columns(3)
        acidez = c1.select_slider("Acidez", options=["Baixa", "Equilibrada", "Vibrante"])
        corpo = c2.select_slider("Corpo", options=["Leve", "Médio", "Encorpado"])
        tanino = c3.select_slider("Taninos", options=["Sedosos", "Macios", "Firmes"])
            
        col_s, col_c = st.columns(2)
        if col_s.button("Salvar Avaliação", type="primary"):
            salvar_checkin(user_id, v_info['vinho_id'], nota_geral, acidez, corpo, tanino, tribo_atual)
            st.session_state.vinho_em_foco = None
            st.success("Nota salva! A média da sua tribo foi atualizada no Master Data.")
            time.sleep(1.5)
            st.rerun()
        if col_c.button("Cancelar"):
            st.session_state.vinho_em_foco = None
            st.rerun()