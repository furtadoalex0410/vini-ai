import streamlit as st
import pandas as pd
import os
import json
import google.generativeai as genai
from PIL import Image
import fitz  # PyMuPDF
from dotenv import load_dotenv

ARQUIVO_HISTORICO = "data/historico.csv"

# Configuração da API do Gemini
load_dotenv()
CHAVE_API = os.getenv("GEMINI_API_KEY")
if CHAVE_API:
    genai.configure(api_key=CHAVE_API)

def carregar_historico(user_id):
    if os.path.exists(ARQUIVO_HISTORICO):
        df_hist = pd.read_csv(ARQUIVO_HISTORICO)
        return df_hist[df_hist['user_id'] == user_id]
    return pd.DataFrame()

def exibir_modulo(usuario_logado_df):
    st.subheader("🍽️ Concierge Digital (Scanner & Sommelier)")
    st.write("Aponte a câmera para o cardápio ou suba o arquivo PDF. A IA fará a leitura óptica e cruzará com seu DNA.")
    st.divider()

    # Extrai os dados do Master Data do Cliente (usuarios.csv)
    user_id = usuario_logado_df.iloc[0]['user_id']
    tribo_atual = usuario_logado_df.iloc[0]['tribo_dna']
    restricoes = usuario_logado_df.iloc[0].get('restricoes', 'Nenhuma')

    # Carrega o histórico (historico.csv)
    df_historico_pessoal = carregar_historico(user_id)

    if not CHAVE_API:
        st.error("⚠️ Chave da API do Gemini não encontrada. Verifique seu arquivo .env.")
        return

    # 1. O Scanner Visual (Agente Engenheiro de Dados)
    st.info("Faça o upload do cardápio completo (Bebidas e Pratos) para a análise.")
    uploaded_files = st.file_uploader("📸 Arquivos (PDF/Imagens)", type=["png", "jpg", "jpeg", "pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        imagens_processadas = []
        
        # Lógica de conversão de arquivos (O código brilhante que você trouxe)
        for file in uploaded_files:
            if file.name.lower().endswith(".pdf"):
                doc = fitz.open(stream=file.getvalue(), filetype="pdf")
                for page in doc:
                    pix = page.get_pixmap(dpi=100) 
                    imagens_processadas.append(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))
            else:
                imagens_processadas.append(Image.open(file))
        
        st.write(f"📁 **{len(imagens_processadas)} páginas prontas para leitura óptica.**")
        
        if st.button("🚀 Iniciar Motor de Harmonização", type="primary", use_container_width=True):
            with st.spinner("Analisando o cardápio físico e buscando o Match perfeito para sua biologia..."):
                try:
                    # Prepara os dados do CSV para a IA
                    historico_json = "Sem histórico prévio."
                    if not df_historico_pessoal.empty:
                        historico_json = df_historico_pessoal.to_json(orient='records', force_ascii=False)

                    # PROMPT DO AGENTE SOMMELIER
                    PROMPT_CONCIERGE = f"""Você é o Master Sommelier do VINI AI. 
                    1. Leia as imagens do cardápio em anexo (vinhos e pratos).
                    2. O cliente pertence à tribo biológica: {tribo_atual}.
                    3. REGRA ABSOLUTA DE RESTRIÇÃO: O cliente declarou restrição a: '{restricoes}'. PROIBIDO recomendar vinhos que violem isso.
                    
                    4. BANCO DE DADOS DE HISTÓRICO (NOTAS DE 1 A 5): 
                    {historico_json}
                    -> REGRA DO HISTÓRICO: Jamais recomende um vinho do cardápio se ele estiver neste histórico com Nota 1 ou 2.
                    
                    5. TAREFA: Retorne duas listas separadas com base no que está disponível NESTE cardápio das imagens:
                       - Caminho Solo: 5 melhores vinhos apenas para beber, perfeitos para a tribo {tribo_atual}.
                       - Caminho Harmonizacao: 5 combinações perfeitas entre um prato do cardápio e um vinho do cardápio (Regras de Mercadini).
                    
                    Retorne APENAS um JSON estrito neste formato:
                    {{
                      "caminho_solo": [
                        {{"vinho": "Nome do Vinho", "por_que": "Justificativa focada na tribo"}}
                      ],
                      "caminho_harmonizacao": [
                        {{"vinho": "Nome do Vinho", "prato": "Nome do Prato", "por_que": "Justificativa química"}}
                      ]
                    }}"""
                                        
                    # Execução da IA
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    res = model.generate_content(imagens_processadas + [PROMPT_CONCIERGE])
                    
                    # Limpeza e Parser do JSON
                    match_dados = json.loads(res.text.replace("```json", "").replace("```", "").strip())
                    
                    # RENDERIZAÇÃO DA INTERFACE (A Mágica acontece aqui)
                    st.success("✅ Cardápio decodificado com sucesso!")
                    st.divider()
                    
                    col1, col2 = st.columns(2)
                    
                    # Coluna 1: Apenas Beber
                    with col1:
                        st.markdown(f"### 🍷 Caminho Solo")
                        st.caption(f"Top 5 rótulos para o perfil **{tribo_atual}**")
                        for item in match_dados.get('caminho_solo', []):
                            with st.container(border=True):
                                st.markdown(f"**{item.get('vinho')}**")
                                st.write(f"💡 {item.get('por_que')}")

                    # Coluna 2: Harmonização
                    with col2:
                        st.markdown("### 🍽️ Caminho Harmonização")
                        st.caption("Top 5 combinações químicas (Prato + Vinho)")
                        for item in match_dados.get('caminho_harmonizacao', []):
                            with st.container(border=True):
                                st.markdown(f"**🍷 {item.get('vinho')}**")
                                st.markdown(f"**🍴 {item.get('prato')}**")
                                st.info(f"🎯 {item.get('por_que')}")
                                
                except Exception as e:
                    st.error(f"Erro ao processar o cardápio: {e}. Certifique-se de que a imagem está legível e a chave da API é válida.")