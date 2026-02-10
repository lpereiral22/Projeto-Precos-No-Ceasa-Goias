import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import requests
import os
import emoji

# --- CONFIGURAÇÕES DE BASTIDORES ---
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=GOOGLE_API_KEY)

# st.sidebar.write("API carregada:", bool(GOOGLE_API_KEY))


st.set_page_config(page_title="Painel do Produtor - Ceasa 2026", layout="wide")

# Estilo para cards brancos e fundo suave
st.markdown("""
      <style>
    /* 1. Fundo Gradiente Suave */
    .stApp {
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
    }

    /* 2. Cartões com Efeito de Vidro (Glassmorphism) */
    [data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        backdrop-filter: blur(4px);
        transition: transform 0.3s ease;
    }

    /* 3. Efeito de Hover (passar o mouse) nos cartões */
    [data-testid="stMetric"]:hover {
        transform: translateY(-5px);
        border-color: #00ff7f; /* Verde neon suave ao passar o mouse */
    }

    /* 4. Customização de Títulos */
    h1, h2, h3 {
        color: #ffffff !important;
        font-family: 'Inter', sans-serif;
    }
        /* Estilo para st.caption (Legendas) */
    [data-testid="stCaptionContainer"] {
        color: #cbd5e1 !important; /* Um cinza azulado claro e bem legível */
        font-size: 0.9rem;
        font-weight: 500;
        margin-top: 10px;
    }

    /* Estilo para links dentro da legenda */
    [data-testid="stCaptionContainer"] a {
        color: #00ff7f !important; /* Cor verde para destacar o link */
        text-decoration: none;
        font-weight: bold;
    }
           /* 1. Rótulos (Selecione Sua Cultivar / Classe) em Verde Neon */
    [data-testid="stWidgetLabel"] p {
        color: #00ff7f !important;
        font-weight: bold;
        font-size: 1.1rem;
    }

    /* 2. O Fundo da Caixa de Seleção */
    div[data-baseweb="select"] > div {
        background-color: rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }

    div[data-baseweb="select"] * {
        color: white !important;
        -webkit-text-fill-color: white !important; /* Força em navegadores como Chrome/Safari */
    }

    /* 4. Ícone da setinha em Branco */
    div[data-baseweb="select"] svg {
        fill: white !important;
    }

    /* 5. Garante que a lista que ABRE (Dropdown) tenha fundo legível */
    /* Se o texto é branco, o fundo da lista precisa ser escuro para contrastar */
    ul[data-baseweb="menu"] {
        background-color: #1e293b !important;
    }
    
    ul[data-baseweb="menu"] li {
        color: white !important;
    }



    /* Estiliza os botões de rádio (Horizontal) */
    [data-testid="stMarkdownContainer"] p {
        color: white;
    }

    /* Melhora o contraste dos textos dentro do selectbox */
    div[data-baseweb="select"] * {
        color: white !important;
    }

    </style>
    """, unsafe_allow_html=True)

# --- CARREGAMENTO DOS DADOS (API + SEUS DADOS DE 2026) ---
@st.cache_data(ttl=600)
def carregar_dados_unificados():

    # 1. Busca histórico da API (Dados Governamentais)
    RESOURCE_ID = "af62cd58-5e71-4719-9df2-32f12d4eead8"
    API_URL = "https://dadosabertos.go.gov.br/sv/api/3/action/datastore_search_sql"
    
    # Busca um volume maior (500) para garantir histórico
    sql = f'''
    SELECT "DT.DIGIT." as data, "NOME_PROD." as produto, "PRC.COMUM" as preco 
    FROM "{RESOURCE_ID}" 
    WHERE "NOME_PROD." ILIKE '%%PIMENTA%%' OR "NOME_PROD." ILIKE '%%PIMENTAO%%'
    ORDER BY "DT.DIGIT." DESC LIMIT 20000
    '''
    
    df_api = pd.DataFrame()
    try:
        res = requests.get(API_URL, params={'sql': sql}, timeout=10).json()
        if 'result' in res and 'records' in res['result']:
            df_api = pd.DataFrame(res['result']['records'])
            
            # Limpeza dos dados da API
            df_api['preco'] = df_api['preco'].astype(str).str.replace(',', '.').astype(float)
            df_api['data'] = pd.to_datetime(df_api['data'], dayfirst=True)
            
            # Padronização de nomes: Remove números e termos entre parênteses
            df_api['produto'] = df_api['produto'].str.upper()
            df_api['produto'] = df_api['produto'].str.replace(r'^\d+\s*', '', regex=True)
            df_api['produto'] = df_api['produto'].str.split('(').str[0].str.strip()
            
            df_api['classe'] = "1" # Padrão API costuma ser Classe 1
            # st.sidebar.success("✅ API Ceasa Conectada")
    except Exception as e:
        st.sidebar.warning(f"⚠️ API Ceasa indisponível (usando apenas local)")

    # 2. Seus dados de 2026 (Busca em múltiplos caminhos)
    df_2026 = pd.DataFrame()
    caminhos_para_tentar = [
        "seus_dados_2026.csv",
        "dados_ceasa/seus_dados_2026.csv",
        r"C:\Users\Lucas Pereira Lima\Desktop\programação\Precos_Ceasa_\dados_ceasa\seus_dados_2026.csv"
    ]

    for caminho in caminhos_para_tentar:
        if os.path.exists(caminho):
            try:
                df_2026 = pd.read_csv(caminho)
                df_2026['data'] = pd.to_datetime(df_2026['data'])
                df_2026['classe'] = df_2026['classe'].astype(str)
                df_2026['produto'] = df_2026['produto'].str.strip().upper()
                st.sidebar.info("📂 Banco 2026 carregado")
                break
            except:
                continue

    # Combinação Final
    df_total = pd.concat([df_api, df_2026], ignore_index=True)
    if not df_total.empty:
        # Remove duplicatas se houver sobreposição de datas/produtos
        df_total = df_total.drop_duplicates(subset=['data', 'produto', 'classe'])
        
    return df_total

# --- INTERFACE ---
st.title("Quanto Custa as Pimentas no _:green[Ceasa Goiás]_? 🌶️")
# st.header("Preço Justo e Decisão Rápida")
st.subheader("Monitore preços e tendências das pimentas comercializadas no Ceasa Goiás.")
st.caption("Dados disponíveis em: goias.gov.br (https://goias.gov.br/ceasa/cotacoes-diarias-2026)")
st.markdown (":green[___________________________________________]")
df = carregar_dados_unificados()

if not df.empty:
    
    # Filtros de Cultivar e Classe
    st.markdown("### 🔍 Filtros de Busca")
    c1, c2 = st.columns(2)
    with c1:
        pimenta = st.selectbox("Selecione Sua Cultivar:", sorted(df['produto'].unique()))
    with c2:
        classes_disponiveis = sorted(df[df['produto'] == pimenta]['classe'].unique())
        classe_sel = st.radio("Classe:", classes_disponiveis, horizontal=True)
    
    # Linha divisória
    st.markdown('<hr style="border: 1px solid green;">', unsafe_allow_html=True)

    # Filtragem por Produto e Classe
    df_f = df[(df['produto'] == pimenta) & (df['classe'] == classe_sel)].sort_values('data')

    if not df_f.empty:
        # --- LÓGICA DE SELEÇÃO DE ANO ---
        df_f['data'] = pd.to_datetime(df_f['data'])
        anos_disponiveis = sorted(df_f['data'].dt.year.unique(), reverse=True)
        ano_sel = st.sidebar.selectbox("📅 Selecione o Ano:", anos_disponiveis)
        
        df_exibicao = df_f[df_f['data'].dt.year == ano_sel]

        if not df_exibicao.empty:
            # --- MÉTRICAS ---# --- CALCULOS ---
            ultimo_preco = df_exibicao.iloc[-1]['preco']
            variacao = 0.0
            if len(df_exibicao) > 1:
                preco_anterior = df_exibicao.iloc[-2]['preco']
                variacao = ((ultimo_preco - preco_anterior) / preco_anterior) * 100

            # --- METRICAS ---
            col1, col2, col3 = st.columns(3)
            col1.metric(f"Preço Atual (C{classe_sel})", f"R$ {ultimo_preco:.2f}", f"{variacao:.1f}%")
            col2.metric("Tendência", "Alta" if variacao > 0 else ("Baixa" if variacao < 0 else "Estável"))
            col3.metric("Status", "Favorável" if variacao >= 0 else "Atenção")

            # --- SIDEBAR SIMULADOR ---
            with st.sidebar:
                st.markdown("---")
                st.markdown("### 💰 Simulador de Lucro")
                qtd = st.number_input("Quantidade de Caixas/Sacos:", min_value=1, value=1, step=1)
                lucro_estimado = qtd * ultimo_preco
                st.success(f"Receita Bruta: **R$ {lucro_estimado:,.2f}**")
                st.info(f"Preço Base: R$ {ultimo_preco:.2f} /un")
                st.markdown("---")

            # --- RECORDES ---
            st.markdown(f"### 🏆 Recordes de {ano_sel}")
            l_max = df_exibicao.loc[df_exibicao['preco'].idxmax()]
            l_min = df_exibicao.loc[df_exibicao['preco'].idxmin()]
            rec1, rec2 = st.columns(2)

            with rec1:
                st.markdown(f"""
                <div style="background-color: rgba(0, 255, 127, 0.1); border: 1px solid #00ff7f; padding: 15px; border-radius: 10px;">
                    <h4 style="color: #00ff7f; margin: 0;">🚀 Preço Máximo</h4>
                    <p style="font-size: 24px; font-weight: bold; margin: 10px 0;">R$ {l_max['preco']:.2f}</p>
                    <p style="font-size: 14px; color: #cbd5e1;">Data: {l_max['data'].strftime('%d/%m/%Y')}</p>
                </div>
                """, unsafe_allow_html=True)

            with rec2:
                st.markdown(f"""
                <div style="background-color: rgba(255, 69, 58, 0.1); border: 1px solid #ff453a; padding: 15px; border-radius: 10px;">
                    <h4 style="color: #ff453a; margin: 0;">📉 Preço Mínimo</h4>
                    <p style="font-size: 24px; font-weight: bold; margin: 10px 0;">R$ {l_min['preco']:.2f}</p>
                    <p style="font-size: 14px; color: #cbd5e1;">Data: {l_min['data'].strftime('%d/%m/%Y')}</p>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # --- GRÁFICO (Único e Estilizado) ---
            cor = '#00ff7f' if classe_sel == "1" else '#ffcc00'
            fig = px.area(df_exibicao, x='data', y='preco',
                          title=f"📈 Evolução de Preço: {pimenta} ({ano_sel})",
                          line_shape="spline",
                          color_discrete_sequence=[cor])
            
            fig.update_traces(
                line=dict(width=3),
                fillcolor='rgba(0, 255, 127, 0.15)' if classe_sel == "1" else 'rgba(255, 204, 0, 0.15)',
                mode='lines+markers',
                marker=dict(size=6, opacity=0.8, line=dict(width=1, color='white'))
            )

            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color="white",
                title_font=dict(size=20, family="Inter, sans-serif"),
                hovermode="x unified",
                margin=dict(l=0, r=10, t=50, b=0),
                xaxis=dict(showgrid=False, tickfont=dict(color='rgba(255,255,255,0.7)'), fixedrange=True),
                yaxis=dict(gridcolor='rgba(255,255,255,0.05)', tickfont=dict(color='rgba(255,255,255,0.7)'), zeroline=False, fixedrange=True)
            )

            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.warning(f"Não há dados disponíveis para o ano de {ano_sel}.")

st.markdown("### 🤖 Consultoria da Inteligência Artificial")

botao_ia = st.button("Analisar Viabilidade de Colheita")

if botao_ia:
    if df_exibicao.empty:
        st.warning("Dados insuficientes para análise neste período.")
    else:
        with st.spinner("IA analisando tendências da Ceasa..."):
            try:
                model = genai.GenerativeModel('gemini-2.0-flash')

                dados_resumo = df_exibicao.tail(10)[["data", "preco"]].to_string(index=False)

                prompt = f"""
Como consultor técnico da Ceasa Goiás, analise a pimenta {pimenta} (Classe {classe_sel}).
Dados recentes:
{dados_resumo}
Preço atual: R$ {ultimo_preco:.2f}.
Dê um conselho curto (2 frases) sobre vender agora ou esperar.
Use sotaque goiano e seja direto.
"""

                response = model.generate_content(prompt)
                st.success(response.text)

            except Exception as e:
                st.error("Falha na IA. Verifique a chave ou o modelo.")
                st.code(str(e))


    

    

















