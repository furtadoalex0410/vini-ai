import streamlit as st
import pandas as pd
import plotly.express as px
import os

def exibir_modulo(usuario_logado_df):
    st.title("📊 Painel de Evolução")
    
    user_id = usuario_logado_df.iloc[0]['user_id']
    
    # 1. CARREGAMENTO DE DADOS
    try:
        df_vinhos = pd.read_csv("data/vinhos.csv")
        df_hist = pd.read_csv("data/historico.csv")
        df_hist = df_hist[df_hist['user_id'] == user_id]
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return

    # Merge para análise profunda (Histórico + Detalhes Técnicos)
    df_analise = pd.merge(df_hist, df_vinhos, on='vinho_id', how='left')

    # --- MÉTRICAS DE TOPO ---
    c1, c2, c3 = st.columns(3)
    total_provados = len(df_hist)
    nota_media = df_hist['nota_geral'].mean() if not df_hist.empty else 0.0
    
    # Contagem de uvas únicas (tratando listas)
    todas_uvas_set = set()
    for item in df_analise['uvas'].dropna():
        uvas_limpas = str(item).replace("[", "").replace("]", "").replace("'", "").replace('"', "").split(",")
        todas_uvas_set.update([u.strip() for u in uvas_limpas if u.strip()])
    
    c1.metric("Rótulos Provados", total_provados)
    c2.metric("Nota Média", f"{nota_media:.1f} ⭐")
    c3.metric("Diversidade de Uvas", len(todas_uvas_set))

    st.divider()

    # 2. VISUALIZAÇÕES - LINHA 1
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("📈 Evolução do seu Paladar")
        if not df_hist.empty:
            df_hist['data'] = pd.to_datetime(df_hist['data'])
            df_tendencia = df_hist.groupby('data')['nota_geral'].mean().reset_index()
            fig_evol = px.line(df_tendencia, x='data', y='nota_geral', markers=True, title="Média de Notas por Data")
            st.plotly_chart(fig_evol, use_container_width=True)
        else:
            st.info("Ainda não há histórico de avaliações.")

    with col_b:
        # --- LÓGICA CORRIGIDA DO GRÁFICO DE UVAS ---
        st.subheader("🍇 Variedades Favoritas")
        if not df_analise.empty:
            lista_todas_uvas = []
            for item in df_analise['uvas'].dropna():
                limpo = str(item).replace("[", "").replace("]", "").replace("'", "").replace('"', "")
                unidades = [u.strip() for u in limpo.split(",") if u.strip()]
                lista_todas_uvas.extend(unidades)
            
            df_contagem = pd.Series(lista_todas_uvas).value_counts().reset_index()
            df_contagem.columns = ['Uva', 'Quantidade']
            
            fig_uvas = px.pie(
                df_contagem.head(10), 
                values='Quantidade', 
                names='Uva', 
                hole=.3,
                color_discrete_sequence=px.colors.sequential.RdBu
            )
            st.plotly_chart(fig_uvas, use_container_width=True)
        else:
            st.info("Dados de uvas insuficientes.")

    st.divider()

    # 3. VISUALIZAÇÕES - LINHA 2
    col_c, col_d = st.columns(2)

    with col_c:
        st.subheader("🔝 Seus Top 5 Vinhos")
        if not df_analise.empty:
            top_5 = df_analise.sort_values(by='nota_geral', ascending=False).head(5)
            st.dataframe(top_5[['nome_base', 'safra', 'nota_geral']], use_container_width=True, hide_index=True)
        else:
            st.info("Avalie vinhos para ver o seu ranking.")

    with col_d:
        st.subheader("🌍 Origem das Descobertas")
        # Se tiveres a coluna 'regiao' no vinhos.csv, podemos mapear aqui
        if 'regiao' in df_analise.columns:
            df_regiao = df_analise['regiao'].value_counts().reset_index()
            fig_mapa = px.bar(df_regiao.head(5), x='count', y='regiao', orientation='h', title="Top Regiões")
            st.plotly_chart(fig_mapa, use_container_width=True)