import streamlit as st
import pandas as pd
import plotly.express as px
import os

ARQUIVO_HISTORICO = "data/historico.csv"

def carregar_historico(user_id):
    if os.path.exists(ARQUIVO_HISTORICO):
        df = pd.read_csv(ARQUIVO_HISTORICO)
        # Filtra apenas as degustações do usuário atual
        return df[df['user_id'] == user_id]
    return pd.DataFrame()

def exibir_modulo(usuario_logado_df):
    st.subheader("📈 Sua Jornada Sensorial")
    st.write("Acompanhe como a sua biologia interage com diferentes rótulos e safras ao longo do tempo.")
    st.divider()

    user_id = usuario_logado_df.iloc[0]['user_id']
    df_hist = carregar_historico(user_id)

    if df_hist.empty:
        st.info("Você ainda não tem check-ins registrados. Vá até a aba 'Catálogo', avalie um vinho e volte aqui para ver seu DNA em movimento!")
        return

    # Preparação dos dados (ETL no front)
    mapa_tribos = {
        "Paladar Delicado": 1,
        "Paladar Clássico": 2,
        "Paladar Robusto": 3,
        "Paladar Audaz": 4
    }
    
    # Mapeia as tribos para valores numéricos para o eixo Y
    df_hist['score_tribo'] = df_hist['tribo_momento'].map(mapa_tribos)
    df_hist = df_hist.sort_values(by='data')

    # Criação do gráfico interativo
    fig = px.line(
        df_hist, 
        x="data", 
        y="score_tribo", 
        markers=True,
        line_shape="spline",
        title="Evolução do seu DNA Sensorial",
        labels={"score_tribo": "Perfil Biológico", "data": "Data do Check-in"}
    )

    # Customiza o eixo Y para exibir os nomes em vez dos números
    fig.update_layout(
        yaxis=dict(
            tickmode='array',
            tickvals=[1, 2, 3, 4],
            ticktext=['Delicado', 'Clássico', 'Robusto', 'Audaz']
        ),
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)

    # Insight Preditivo do Agente Growth Hacker
    if len(df_hist) >= 2:
        tribo_inicial = df_hist.iloc[0]['tribo_momento']
        tribo_atual = df_hist.iloc[-1]['tribo_momento']
        
        st.divider()
        if tribo_inicial != tribo_atual:
            st.success(f"💡 **Insight Preditivo:** Detectamos uma migração! Você começou no perfil **{tribo_inicial}** e suas últimas avaliações puxam para o **{tribo_atual}**.")
        else:
            st.info(f"💡 **Insight Preditivo:** Seu paladar está firmemente ancorado na tribo **{tribo_atual}**. Que tal testar uma safra diferente para explorar novas texturas?")