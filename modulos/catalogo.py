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

ARQUIVO_VINHOS = "data/vinhos.csv"
ARQUIVO_HISTORICO = "data/historico.csv"
ARQUIVO_INVENTARIO = "data/inventario.csv" # NOVO MASTER DATA DE ESTOQUE

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
    
    if not df_vinhos.empty:
        existente = df_vinhos[(df_vinhos['nome_base'].str.contains(novo_vinho_dict.get('nome_base', ''), case=False, na=False)) & 
                              (df_vinhos['safra'] == str(novo_vinho_dict.get('safra', '')))]
        if not existente.empty:
            return existente.iloc[0]['vinho_id'], existente.iloc[0]

    novo_id = f"vin_{len(df_vinhos) + 1:03d}"
    novo_vinho_dict['vinho_id'] = novo_id
    
    for col in ['nome_base', 'safra', 'produtor', 'uvas', 'teor_alcoolico', 'nota_delicado', 'nota_classico', 'nota_robusto', 'nota_audaz']:
        if col not in novo_vinho_dict or str(novo_vinho_dict[col]).strip() == "":
            novo_vinho_dict[col] = "N/D" if "nota" not in col else 3.0
            
    df_novo = pd.DataFrame([novo_vinho_dict])
    df_vinhos = pd.concat([df_vinhos, df_novo], ignore_index=True)
    df_vinhos.to_csv(ARQUIVO_VINHOS, index=False)
    return novo_id, df_novo.iloc[0]

def salvar_checkin(user_id, vinho_id, nota, acidez, corpo, tanino, tribo_momento):
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

def gerenciar_inventario(user_id, vinho_id, status, operacao="add"):
    # operacao: "add" (+1), "sub" (-1), ou "set" (Apenas insere sem qtd)
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
                df_inv = df_inv.drop(idx) # Apaga se zerou o estoque
                
    df_inv.to_csv(ARQUIVO_INVENTARIO, index=False)

def exibir_modulo(usuario_logado_df):
    inicializar_memoria()
    st.subheader("📚 Ecossistema VINI AI")
    
    user_id = usuario_logado_df.iloc[0]['user_id']
    tribo_atual = usuario_logado_df.iloc[0]['tribo_dna']
    # Tratamento contra o erro do "clássico"
    coluna_nota_usuario = f"nota_{tribo_atual.split()[1].lower().replace('á', 'a')}"

    aba_global, aba_pessoal, aba_scanner = st.tabs([
        "🌍 Catálogo Global", 
        "🏠 Meu Espaço (Adega & Notas)", 
        "📸 Scanner Inteligente"
    ])

    # ==========================================
    # ABA 1: CATÁLOGO GLOBAL (COM AÇÕES RÁPIDAS)
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
    # ABA 2: MEU ESPAÇO (ADEGA, WISHLIST, NOTAS)
    # ==========================================
    with aba_pessoal:
        st.markdown("### Seu ERP Pessoal de Vinhos")
        sub_estoque, sub_wishlist, sub_notas = st.tabs(["📦 Estoque Físico", "⭐ Wishlist", "🍷 Diário de Notas"])
        
        df_inv = carregar_inventario(user_id)
        df_hist = carregar_historico_pessoal(user_id)
        df_vinhos_base = carregar_vinhos()
        
        # 1. ESTOQUE FÍSICO
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
                st.info("Sua adega física está vazia. Adicione garrafas pelo Catálogo Global.")

        # 2. WISHLIST
        with sub_wishlist:
            st.write("Vinhos que você quer provar ou comprar no futuro.")
            df_wish = df_inv[df_inv['status'] == 'wishlist']
            if not df_wish.empty and not df_vinhos_base.empty:
                df_wish_view = pd.merge(df_wish, df_vinhos_base[['vinho_id', 'nome_base', 'safra']], on='vinho_id', how='left')
                for _, row in df_wish_view.iterrows():
                    st.markdown(f"- ⭐ **{row['nome_base']}** ({row['safra']})")
            else:
                st.info("Sua lista de desejos está vazia.")

        # 3. DIÁRIO DE NOTAS
        with sub_notas:
            st.write("Suas avaliações sensoriais.")
            if not df_hist.empty and not df_vinhos_base.empty:
                df_minha_adega = pd.merge(df_hist, df_vinhos_base[['vinho_id', 'nome_base', 'safra']], on='vinho_id', how='left')
                df_minha_adega = df_minha_adega.sort_values(by='data', ascending=False)
                st.dataframe(
                    df_minha_adega[['data', 'nome_base', 'safra', 'nota_geral']],
                    use_container_width=True, hide_index=True,
                    column_config={"nota_geral": st.column_config.NumberColumn("Nota", format="⭐ %.1f")}
                )
            else:
                st.info("Nenhuma avaliação feita ainda.")

    # ==========================================
    # ABA 3: SCANNER INTELIGENTE E AVALIAÇÃO
    # ==========================================
    with aba_scanner:
        st.write("Adicione novos vinhos ao Master Data usando a inteligência do Sommelier.")
        # [O código do Scanner permanece 100% igual à versão anterior aqui para baixo...]
        if not CHAVE_API:
            st.warning("⚠️ Chave da API do Gemini não encontrada.")
            return

        col1, col2 = st.columns(2)
        alvo_consulta = col1.radio("Analisar?", ["🍾 Rótulo Único", "📋 Cardápio Completo"])
        metodo_captura = col2.radio("Enviar imagem?", ["📸 Câmera", "📂 Subir Arquivo"])

        imagens_processadas = []

        if metodo_captura == "📸 Câmera":
            foto_cam = st.camera_input("Tire a foto agora")
            if foto_cam: imagens_processadas.append(Image.open(foto_cam))
        else:
            arquivo_up = st.file_uploader("Selecione o arquivo", type=['png', 'jpg', 'jpeg', 'pdf'])
            if arquivo_up:
                if arquivo_up.name.lower().endswith(".pdf"):
                    doc = fitz.open(stream=arquivo_up.getvalue(), filetype="pdf")
                    for page in doc:
                        pix = page.get_pixmap(dpi=100)
                        imagens_processadas.append(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))
                else:
                    imagens_processadas.append(Image.open(arquivo_up))

        if imagens_processadas and st.button("🔎 Analisar Imagem", type="primary"):
            model = genai.GenerativeModel("gemini-2.5-flash")
            with st.spinner("Extraindo dados..."):
                PROMPT = """Leia o rótulo/cardápio. Deduza Produtor e Uvas caso omita. Retorne APENAS JSON:
                {"vinhos": [{"nome_base": "Nome", "safra": "Ano", "produtor": "Vinícola", "uvas": "Uvas", "teor_alcoolico": 13.5, "nota_delicado": 2.0, "nota_classico": 3.5, "nota_robusto": 4.5, "nota_audaz": 3.0}]}"""
                try:
                    res = model.generate_content(imagens_processadas + [PROMPT])
                    dados = json.loads(res.text.replace('```json', '').replace('```', '').strip())
                    st.session_state.rascunho_ia = dados.get('vinhos', [])
                except Exception as e:
                    st.error(f"Erro: {e}")

        if st.session_state.rascunho_ia is not None:
            st.warning("✍️ **Revisão Necessária:** Edite na tabela abaixo se faltar algo.")
            df_editado = st.data_editor(pd.DataFrame(st.session_state.rascunho_ia)[['nome_base', 'safra', 'produtor', 'uvas', 'teor_alcoolico']], num_rows="dynamic", use_container_width=True)
            
            if st.button("✅ Salvar no Master Data Global", type="primary"):
                for index, row in df_editado.iterrows():
                    v_comp = row.to_dict()
                    v_comp.update({k: st.session_state.rascunho_ia[index][k] for k in ['nota_delicado', 'nota_classico', 'nota_robusto', 'nota_audaz']})
                    salvar_vinho_novo(v_comp)
                st.session_state.rascunho_ia = None
                st.success("Salvo! Vá no Catálogo Global para interagir com eles.")
                time.sleep(1)
                st.rerun()

    # --- FORMULÁRIO DE CHECK-IN FLUTUANTE (Disparado pelos botões de "Avaliar") ---
    if st.session_state.vinho_em_foco is not None:
        v_info = st.session_state.vinho_em_foco
        st.divider()
        st.markdown(f"### 🍷 Avaliando: {v_info['nome_base']}")
        
        nota_geral = st.slider("Sua Nota Geral", 1.0, 5.0, 3.0, 0.5)
        c1, c2, c3 = st.columns(3)
        acidez = c1.select_slider("Acidez", options=["Baixa", "Equilibrada", "Vibrante"])
        corpo = c2.select_slider("Corpo", options=["Leve", "Médio", "Encorpado"])
        tanino = c3.select_slider("Taninos", options=["Sedosos", "Macios", "Firmes"])
            
        col_s, col_c = st.columns(2)
        if col_s.button("Salvar Avaliação", type="primary"):
            salvar_checkin(user_id, v_info['vinho_id'], nota_geral, acidez, corpo, tanino, tribo_atual)
            st.session_state.vinho_em_foco = None
            st.success("Nota salva com sucesso! (Consulte o Diário de Notas)")
            time.sleep(1)
            st.rerun()
        if col_c.button("Cancelar"):
            st.session_state.vinho_em_foco = None
            st.rerun()