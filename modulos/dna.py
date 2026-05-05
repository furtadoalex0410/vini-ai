import streamlit as st
import pandas as pd
import os

ARQUIVO_USUARIOS = "data/usuarios.csv"

def classificar_tribo(score):
    # Regra 1.2: Classificação Sensorial
    if score > 70:
        return "Paladar Delicado"
    elif score >= 46:
        return "Paladar Clássico"
    elif score >= 26:
        return "Paladar Robusto"
    else:
        return "Paladar Audaz"

def laudo_empatico(tribo):
    if tribo == "Paladar Delicado":
        return "Sua genética permite que você sinta nuances sutis que outros ignoram. Você brilha com frescor, espumantes e tintos leves."
    elif tribo == "Paladar Clássico":
        return "Sua sensibilidade é muito equilibrada. Seu corpo busca a elegância do meio-termo, vinhos redondos e harmônicos."
    elif tribo == "Paladar Robusto":
        return "Você tem uma tolerância fantástica. Seu paladar gosta de presença, texturas firmes e sabores bem definidos."
    else:
        return "Sua tolerância é máxima! Você exige o máximo de potência, impacto e extração na taça."

def exibir_teste(nome_usuario):
    st.subheader("🧬 Mapeamento Psicofísico do Paladar")
    st.write(f"Bem-vindo, **{nome_usuario}**. Para garantir recomendações perfeitas, não vamos perguntar se você 'entende' de vinho, mas sim como a sua biologia percebe o mundo ao seu redor.")
    st.divider()

    st.markdown("### 1. Responda com base no seu dia a dia:")
    
    # Sliders de 0 a 25. Quanto maior a sensibilidade, maior a nota.
    cafe = st.slider("Como você percebe o amargor do café preto sem açúcar?", 
                     0, 25, 12, help="0 = Adoro o gosto / 25 = Intolerável, muito amargo")
    
    pimenta = st.slider("Qual é a sua tolerância à pimenta na comida?", 
                        0, 25, 12, help="0 = Como muita pimenta, não sinto nada / 25 = Queima absurdamente, não tolero")
    
    doce = st.slider("Qual é a sua preferência por doces e sobremesas?", 
                      0, 25, 12, help="0 = Adoro coisas extremamente doces / 25 = Prefiro o amargo, não gosto de muito açúcar")
    
    alcool = st.slider("Ao beber um destilado puro, como você percebe o álcool?", 
                       0, 25, 12, help="0 = Sinto um calor agradável / 25 = É uma queimação muito agressiva")
    
    st.divider()
    
    st.markdown("### 2. 🚫 Restrições Absolutas (Hard Blocks)")
    st.write("Marque se você possui alguma restrição. O sistema bloqueará recomendações que não respeitem isso.")
    restricoes = st.multiselect("Minhas Restrições:", 
                                ["Nenhuma", "Alergia a Sulfitos", "Odeio Vinho Branco", "Odeio Vinho Tinto", "Vegano"])

    # Botão de Ação
    if st.button("Gerar meu DNA Sensorial", type="primary"):
        # Processamento (Engenharia de Dados)
        score_total = cafe + pimenta + doce + alcool
        tribo = classificar_tribo(score_total)
        
        restricoes_str = "Nenhuma" if not restricoes or "Nenhuma" in restricoes else " | ".join(restricoes)
            
        # Salva no Banco de Dados (CSV)
        if os.path.exists(ARQUIVO_USUARIOS):
            df = pd.read_csv(ARQUIVO_USUARIOS)
        else:
            # Se o arquivo não existir, cria a base vazia
            df = pd.DataFrame(columns=["user_id", "nome", "tribo_dna", "restricoes"])
            
        novo_id = f"usr_{len(df) + 1:03d}"
        
        novo_registro = pd.DataFrame([{
            "user_id": novo_id,
            "nome": nome_usuario,
            "tribo_dna": tribo,
            "restricoes": restricoes_str
        }])
        
        df = pd.concat([df, novo_registro], ignore_index=True)
        df.to_csv(ARQUIVO_USUARIOS, index=False)
        
        # Feedback de Sucesso e Laudo
        st.success(f"🎉 Análise Concluída! Você é da tribo: **{tribo}**")
        st.info(laudo_empatico(tribo))
        
        # Botão para atualizar o app.py e entrar no sistema
        st.button("Acessar o Ecossistema VINI AI", on_click=st.rerun)