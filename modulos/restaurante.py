import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import json
import math
from dotenv import load_dotenv
from PIL import Image
import fitz  # PyMuPDF

# --- MOTOR DE MACHINE LEARNING (KNN) ---
def calcular_distancia_euclidiana(vetor_usuario, vetor_vinho):
    return math.sqrt(sum((u - v) ** 2 for u, v in zip(vetor_usuario, vetor_vinho)))

def exibir_modulo(usuario_logado_df):
    st.title("🍽️ Modo Restaurante")
    
    # 1. Dados do Usuário e Configurações
    user_id = usuario_logado_df.iloc[0]['user_id']
    tribo_atual = usuario_logado_df.iloc[0]['tribo_dna']
    vetor_usuario = [
        float(usuario_logado_df.iloc[0].get('nota_delicado', 3.0)),
        float(usuario_logado_df.iloc[0].get('nota_classico', 3.0)),
        float(usuario_logado_df.iloc[0].get('nota_robusto', 3.0)),
        float(usuario_logado_df.iloc[0].get('nota_audaz', 3.0))
    ]

    try:
        df_global = pd.read_csv("data/vinhos.csv")
    except FileNotFoundError:
        st.error("Erro: Arquivo data/vinhos.csv não encontrado.")
        return

    load_dotenv()
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

    st.info(f"🧬 DNA Sensorial: **{tribo_atual}**")

    # 2. Inputs do Usuário
    st.divider()
    st.markdown("### 1️⃣ O que vamos comer? (Opcional)")
    prato = st.text_input("Se já souber o prato, digite aqui. Se não, deixe em branco para sugestões do Chef.", placeholder="Ex: Picanha, Risoto...")
    
    st.markdown("### 2️⃣ A Carta de Vinhos")
    metodo_captura = st.radio("Como enviar o cardápio?", ["📸 Câmera", "📂 Arquivo (Múltiplos)"], horizontal=True)
    
    imagens = []
    
    if metodo_captura == "📸 Câmera":
        # Nota: Camera_input geralmente é unitário por vez, mas pode ser usado repetidamente
        foto = st.camera_input("Fotografe uma página do cardápio")
        if foto: 
            imagens.append(Image.open(foto))
    else:
        # ATUALIZAÇÃO: Agora aceita múltiplos arquivos simultaneamente
        arquivos = st.file_uploader("Selecione Fotos ou PDFs (Pode escolher vários)", type=['png', 'jpg', 'jpeg', 'pdf'], accept_multiple_files=True)
        if arquivos:
            for arq in arquivos:
                if arq.name.lower().endswith(".pdf"):
                    doc = fitz.open(stream=arq.getvalue(), filetype="pdf")
                    for page in doc:
                        pix = page.get_pixmap(dpi=150)
                        imagens.append(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))
                else:
                    imagens.append(Image.open(arq))

    # 3. Execução do Fluxo
    if st.button("🍷 Analisar Cardápio com VINI AI", type="primary", use_container_width=True):
        if not imagens:
            st.warning("⚠️ Envie pelo menos uma foto do cardápio.")
            return

        with st.spinner("O Motor KNN está processando as imagens..."):
            
            # Ajuste do Prompt baseado na presença ou não do prato
            if prato:
                contexto_missao = f"Harmonize vinhos para o prato '{prato}'."
            else:
                contexto_missao = "O usuário não escolheu o prato. Sugira 5 vinhos para beber solo e 5 vinhos sugerindo o prato ideal do cardápio para eles."

            prompt = f"""
            Aja como um Engenheiro de Dados e Master Sommelier. 
            Missão: {contexto_missao}
            Perfil do Cliente: DNA {tribo_atual}.
            
            Extraia os vinhos da imagem e retorne um JSON puro (sem markdown) com esta estrutura:
            [
              {{
                "nome": "Nome do Vinho",
                "preco": "Preço",
                "prato_sugerido": "Caso prato esteja em branco, sugira um prato ideal deste cardápio para este vinho",
                "estimativa_ia": [nota_delicado, nota_classico, nota_robusto, nota_audaz]
              }}
            ]
            """

            try:
                # Usando o modelo estável que corrigimos
                model = genai.GenerativeModel("gemini-2.5-flash")
                res = model.generate_content(imagens + [prompt])
                vinhos_cardapio = json.loads(res.text.replace("```json", "").replace("```", "").strip())

                # Processamento KNN
                resultados_finais = []
                for v in vinhos_cardapio:
                    # Busca no Global
                    match_global = df_global[df_global['nome_base'].str.contains(v['nome'], case=False, na=False)]
                    if not match_global.empty:
                        dados = match_global.iloc[0]
                        vetor_final = [dados['nota_delicado'], dados['nota_classico'], dados['nota_robusto'], dados['nota_audaz']]
                        fonte = "Catálogo Global"
                    else:
                        vetor_final = v['estimativa_ia']
                        fonte = "IA (Cold Start)"

                    distancia = calcular_distancia_euclidiana(vetor_usuario, vetor_final)
                    v.update({
                        "distancia": distancia,
                        "afinidade": max(0, min(100, 100 - (distancia * 15))),
                        "origem": fonte
                    })
                    resultados_finais.append(v)

                # Ordenação por Match
                resultados_finais = sorted(resultados_finais, key=lambda x: x['distancia'])

                # 4. EXIBIÇÃO DOS RESULTADOS
                if prato:
                    st.markdown(f"### 🏆 Top Matches para {prato}")
                    for r in resultados_finais[:5]:
                        with st.container(border=True):
                            col1, col2 = st.columns([3, 1])
                            col1.markdown(f"**{r['nome']}**")
                            col1.caption(f"Fonte: {r['origem']}")
                            col2.metric("Match", f"{r['afinidade']:.1f}%")
                            st.write(f"🏷️ {r['preco']}")
                else:
                    # Lógica de 5 Solo e 5 Harmonizados
                    st.markdown("### 🍷 5 Opções para Beber Solo")
                    for r in resultados_finais[:5]:
                        st.write(f"✅ **{r['nome']}** ({r['preco']}) - Match: {r['afinidade']:.1f}%")
                    
                    st.divider()
                    st.markdown("### 🍽️ 5 Opções com Harmonização Sugerida")
                    for r in resultados_finais[5:10]:
                        with st.expander(f"🍷 {r['nome']} + 🍴 {r['prato_sugerido']}"):
                            st.write(f"**Preço:** {r['preco']}")
                            st.write(f"**Por que este prato?** A IA identificou que este prato do restaurante combina perfeitamente com este rótulo para o seu DNA {tribo_atual}.")

            except Exception as e:
                st.error(f"Erro no processamento: {e}")