import streamlit as st
import pandas as pd
import json
import os
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
import fitz  # PyMuPDF

# Configuração da API
load_dotenv()
CHAVE_API = os.getenv("GEMINI_API_KEY")
if CHAVE_API:
    genai.configure(api_key=CHAVE_API)

def exibir_modulo():
    st.subheader("🏢 Painel Executivo VINI (B2B)")
    st.write("Auditoria Sensorial de Cardápio e Inteligência de Compras para o Restaurante.")
    st.divider()

    if not CHAVE_API:
        st.error("⚠️ Chave da API do Gemini não encontrada no arquivo .env.")
        return

    # O Prompt do Agente 5 - Inteligência de Negócio B2B
    INSTRUCAO_SISTEMA = """
    Você é o Agente de Business Intelligence do VINI AI. Sua função é auditar cardápios de restaurantes físicos.

    Regras de Negócio:
    1. Tribos de Paladar (Mapeamento Biológico): 
       - Paladar Delicado: Prefere espumantes brut, brancos leves, tintos de baixo tanino.
       - Paladar Clássico: Vinhos de corpo médio, brancos com madeira, Merlot.
       - Paladar Robusto: Tintos estruturados, Cabernet Sauvignon, Malbec.
       - Paladar Audaz: Vinhos potentes, alta extração, Tannat, vinhos de sobremesa.
    2. Regras de Harmonização Mercadini: Acidez corta Gordura/Fritura. Umami (cogumelo/shoyu) rejeita Tanino. Prato Doce exige Vinho Doce/Ácido.

    Tarefa: Identifique gaps críticos de harmonização entre os pratos e os vinhos do cardápio e CONTE os rótulos disponíveis que atendem cada Tribo.

    Saída Obrigatória (JSON Estrito):
    {
      "auditoria_info": { "estabelecimento": "Nome (se achar no topo)", "status_estoque": "Resumo executivo do cardápio", "total_vinhos_detectados": 0 },
      "cobertura_paladar": { "Delicado": 0, "Clássico": 0, "Robusto": 0, "Audaz": 0 },
      "gaps_criticos": [ { "prato_ou_categoria": "...", "classe_afetada": "...", "causa_quimica": "..." } ],
      "plano_acao_compras": [ { "acao": "COMPRAR/MANTER/REDUZIR", "prioridade": "ALTA/MÉDIA/BAIXA", "estilo_sugerido": "...", "justificativa": "..." } ]
    }
    """

    col_input, col_dash = st.columns([1, 2.5])

    with col_input:
        st.info("Upload do cardápio completo (Bebidas e Pratos).")
        uploaded_files = st.file_uploader("Arquivos (PDF/Imagens)", type=["png", "jpg", "jpeg", "pdf"], accept_multiple_files=True, key="b2b_upload")
        imagens_processadas = []
        
        if uploaded_files:
            for file in uploaded_files:
                if file.name.lower().endswith(".pdf"):
                    doc = fitz.open(stream=file.getvalue(), filetype="pdf")
                    for page in doc:
                        pix = page.get_pixmap(dpi=100) 
                        imagens_processadas.append(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))
                else:
                    imagens_processadas.append(Image.open(file))
            
            st.write(f"📁 **{len(imagens_processadas)} páginas prontas para auditoria.**")
            executar = st.button("🚀 Iniciar Auditoria B2B", type="primary", use_container_width=True)
        else:
            executar = False

    with col_dash:
        if uploaded_files and executar:
            with st.spinner("Analisando DNA químico do cardápio e mapeando gaps de estoque..."):
                try:
                    model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=INSTRUCAO_SISTEMA)
                    response = model.generate_content(imagens_processadas + ["Execute a auditoria completa e retorne apenas o JSON."])
                    
                    # Limpeza robusta do JSON
                    dados = json.loads(response.text.replace('```json', '').replace('```', '').strip())
                    
                    # Renderização do Dashboard
                    st.subheader(f"📊 Relatório: {dados.get('auditoria_info', {}).get('estabelecimento', 'Auditoria Geral')}")
                    st.info(dados.get('auditoria_info', {}).get('status_estoque', ''))
                    
                    k1, k2, k3 = st.columns(3)
                    k1.metric("Rótulos Encontrados", dados.get('auditoria_info', {}).get('total_vinhos_detectados', 0))
                    k2.metric("Alertas de Risco", len(dados.get('gaps_criticos', [])))
                    k3.metric("Ações Recomendadas", len(dados.get('plano_acao_compras', [])))
                    st.divider()

                    col_g1, col_g2 = st.columns(2)
                    with col_g1:
                        st.write("👥 **Cobertura de Público (Tribos VINI)**")
                        cob = dados.get("cobertura_paladar", {})
                        if cob:
                            df_p = pd.DataFrame({
                                "Tribo": ["Delicado", "Clássico", "Robusto", "Audaz"], 
                                "Qtd": [cob.get("Delicado", 0), cob.get("Clássico", 0), cob.get("Robusto", 0), cob.get("Audaz", 0)]
                            })
                            st.bar_chart(df_p.set_index("Tribo"), color="#4b0082") 
                    
                    with col_g2:
                        st.write("🛒 **Esforço de Compras por Prioridade**")
                        acoes = dados.get("plano_acao_compras", [])
                        if acoes:
                            df_acoes = pd.DataFrame(acoes)
                            grafico_prioridade = df_acoes['prioridade'].value_counts()
                            st.bar_chart(grafico_prioridade, color="#8b0000") 
                    
                    st.divider()
                    
                    col_op1, col_op2 = st.columns([1, 1.2])
                    with col_op1:
                        st.subheader("🚨 Descritivo de Rupturas")
                        for gap in dados.get("gaps_criticos", []):
                            with st.expander(f"{gap.get('prato_ou_categoria')} ({gap.get('classe_afetada')})"): 
                                st.write(gap.get('causa_quimica'))
                    
                    with col_op2:
                        st.subheader("📋 Plano de Compras")
                        if acoes: 
                            df_c = pd.DataFrame(acoes)
                            st.dataframe(df_c[["acao", "prioridade", "estilo_sugerido"]], use_container_width=True, hide_index=True)

                except Exception as e:
                    st.error(f"Erro na esteira de dados: {e}")