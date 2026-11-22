
import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import plotly.graph_objects as go

from datetime import datetime

# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================

st.set_page_config(
    page_title="Horta Inteligente | Monitoramento",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# IDENTIDADE VISUAL
# =========================================================

st.markdown("""
<style>
    .stApp {
        background-color: #f5f7f2;
    }

    h1, h2, h3 {
        color: #18392b;
    }

    [data-testid="stMetric"] {
        background-color: white;
        border: 1px solid #e1e8df;
        padding: 18px;
        border-radius: 12px;
    }

    div[data-testid="stSidebar"] {
        background-color: #18392b;
    }

    div[data-testid="stSidebar"] * {
        color: white;
    }

    .intro-box {
        background-color: #e6f1e7;
        padding: 24px;
        border-radius: 15px;
        border-left: 5px solid #39834c;
    }

    .small-text {
        color: #65776b;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# CONEXÃO COM O POSTGRESQL
# =========================================================

@st.cache_data(ttl=60)
def carregar_dados():

    conn = psycopg2.connect(
        host=st.secrets["postgres"]["host"],
        port=st.secrets["postgres"]["port"],
        database=st.secrets["postgres"]["database"],
        user=st.secrets["postgres"]["user"],
        password=st.secrets["postgres"]["password"]
    )

    query = """
        SELECT
            id,
            data_hora,
            umidade_percentual,
            valor_adc,
            tempo_bomba_segundos,
            estado_bomba
        FROM leituras
        ORDER BY data_hora ASC;
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    df["data_hora"] = pd.to_datetime(df["data_hora"])
    df["umidade_percentual"] = pd.to_numeric(
        df["umidade_percentual"], errors="coerce"
    )
    df["valor_adc"] = pd.to_numeric(
        df["valor_adc"], errors="coerce"
    )
    df["tempo_bomba_segundos"] = pd.to_numeric(
        df["tempo_bomba_segundos"], errors="coerce"
    )

    df["estado_bomba"] = (
        df["estado_bomba"].astype(str).str.strip().str.capitalize()
    )

    return df


# =========================================================
# CARREGAMENTO DOS DADOS
# =========================================================

try:
    df = carregar_dados()

except Exception as e:
    st.error("Não foi possível conectar ao banco de dados.")
    st.error(f"Erro: {e}")

    st.info(
        "Verifique as credenciais, a conexão PostgreSQL "
        "e a disponibilidade do servidor."
    )

    st.stop()


# =========================================================
# MENU LATERAL
# =========================================================

st.sidebar.title("🌱 Horta Inteligente")

st.sidebar.markdown("""
Projeto de monitoramento de umidade do solo
e automação de irrigação.
""")

pagina = st.sidebar.radio(
    "Navegação",
    [
        "Apresentação",
        "Coleta de dados",
        "Armazenamento",
        "Análise dos dados",
        "Validação"
    ]
)

st.sidebar.divider()

st.sidebar.caption("Projeto acadêmico • Ciência de Dados")

# =========================================================
# INDICADORES GERAIS
# =========================================================

total_registros = len(df)

umidade_media = df["umidade_percentual"].mean()

umidade_minima = df["umidade_percentual"].min()

umidade_maxima = df["umidade_percentual"].max()

total_bomba_ligada = (
    df["estado_bomba"].str.lower() == "ligada"
).sum()

total_bomba_desligada = (
    df["estado_bomba"].str.lower() == "desligada"
).sum()

tempo_total_bomba = df["tempo_bomba_segundos"].sum()

# =========================================================
# PÁGINA 1 - APRESENTAÇÃO
# =========================================================

if pagina == "Apresentação":

    st.title("🌱 Horta Inteligente")

    st.markdown("""
    <div class="intro-box">
        <h2>Monitoramento da umidade do solo e automação da irrigação</h2>

        <p>
        Este projeto apresenta uma proposta de monitoramento da umidade
        do solo por meio de dados, armazenamento em banco de dados
        e análise das informações utilizando Python.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    st.markdown("### Objetivo do projeto")

    st.write("""
    Utilizar tecnologia e análise de dados para acompanhar os níveis
    de umidade do solo e compreender o funcionamento de um sistema
    de irrigação automatizado, contribuindo para um uso mais eficiente
    dos recursos hídricos.
    """)

    st.markdown("### Etapas do projeto")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Etapa 01", "Coleta")
    c2.metric("Etapa 02", "Python")
    c3.metric("Etapa 03", "PostgreSQL")
    c4.metric("Etapa 04", "Análise")

    st.markdown("---")

    st.subheader("Visão geral dos dados")

    c1, c2, c3 = st.columns(3)

    c1.metric("Registros armazenados", f"{total_registros:,}".replace(",", "."))

    c2.metric(
        "Umidade média",
        f"{umidade_media:.2f}%" if pd.notna(umidade_media) else "N/A"
    )

    c3.metric(
        "Acionamentos registrados",
        int(total_bomba_ligada)
    )

    st.markdown("""
    ### O que será apresentado?

    - Como os dados foram coletados;
    - Como os dados foram conectados e armazenados;
    - Como as informações foram analisadas;
    - Quais resultados foram identificados;
    - Como foi realizada a verificação da base.
    """)

# =========================================================
# PÁGINA 2 - COLETA
# =========================================================

elif pagina == "Coleta de dados":

    st.title("📡 Coleta de dados")

    st.write("""
    A coleta de dados é a etapa responsável por obter as informações
    relacionadas à umidade do solo e ao funcionamento do sistema de irrigação.
    Essas informações são posteriormente utilizadas no processamento,
    armazenamento e análise.
    """)

    st.subheader("Fluxo de coleta")

    st.markdown("""
    **Sensor de umidade → Arduino UNO → Python → PostgreSQL**

    - O sensor fornece valores relacionados à umidade do solo.
    - O Arduino realiza a leitura do sinal analógico.
    - Os dados são transmitidos para o Python.
    - O Python organiza as informações para armazenamento.
    """)

    st.info(
        "Neste projeto, os dados utilizados foram simulados para representar "
        "as leituras do sistema durante o período de monitoramento. "
        "Não devem ser interpretados como medições físicas reais."
    )

    st.subheader("Variáveis coletadas")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **Umidade percentual**

        Representa o percentual de umidade utilizado
        para acompanhamento das condições do solo.
        """)

        st.markdown("""
        **Valor ADC**

        Representa o valor numérico obtido a partir
        da leitura analógica do sensor.
        """)

    with col2:
        st.markdown("""
        **Data e hora**

        Permite identificar o momento em que
        cada leitura foi registrada.
        """)

        st.markdown("""
        **Estado da bomba**

        Identifica se o sistema registrou
        a bomba ligada ou desligada.
        """)

    st.subheader("Visualização das leituras")

    st.dataframe(
        df[[
            "data_hora",
            "umidade_percentual",
            "valor_adc",
            "tempo_bomba_segundos",
            "estado_bomba"
        ]],
        use_container_width=True,
        hide_index=True
    )

# =========================================================
# PÁGINA 3 - ARMAZENAMENTO
# =========================================================

elif pagina == "Armazenamento":

    st.title("🗄️ Armazenamento dos dados")

    st.write("""
    Após o processamento em Python, os dados foram armazenados
    em um banco de dados relacional PostgreSQL, permitindo sua
    organização, consulta e utilização nas análises.
    """)

    st.subheader("Tecnologias utilizadas")

    c1, c2 = st.columns(2)

    c1.markdown("""
    ### Python

    Utilizado na conexão com o banco de dados,
    manipulação e análise das informações.
    """)

    c2.markdown("""
    ### PostgreSQL

    Sistema gerenciador de banco de dados relacional
    utilizado para armazenar as leituras.
    """)

    st.subheader("Estrutura da tabela `leituras`")

    estrutura = pd.DataFrame({
        "Coluna": [
            "id",
            "data_hora",
            "umidade_percentual",
            "valor_adc",
            "tempo_bomba_segundos",
            "estado_bomba"
        ],
        "Tipo": [
            "SERIAL / INTEGER",
            "TIMESTAMP",
            "NUMERIC",
            "INTEGER",
            "FLOAT",
            "VARCHAR"
        ],
        "Descrição": [
            "Identificador do registro",
            "Data e hora da leitura",
            "Umidade registrada",
            "Valor analógico do sensor",
            "Tempo de funcionamento da bomba",
            "Estado da bomba"
        ]
    })

    st.dataframe(estrutura, use_container_width=True, hide_index=True)

    st.subheader("Consulta SQL utilizada")

    st.code("""
SELECT
    id,
    data_hora,
    umidade_percentual,
    valor_adc,
    tempo_bomba_segundos,
    estado_bomba
FROM leituras
ORDER BY data_hora ASC;
    """, language="sql")

    st.subheader("Dados armazenados")

    st.metric("Total de registros no PostgreSQL", total_registros)

    st.dataframe(df, use_container_width=True, hide_index=True)

# =========================================================
# PÁGINA 4 - ANÁLISE
# =========================================================

elif pagina == "Análise dos dados":

    st.title("📊 Análise dos dados")

    st.write("""
    Nesta etapa, os registros armazenados foram utilizados para
    gerar indicadores e visualizações, permitindo compreender
    o comportamento da umidade e os registros do sistema de irrigação.
    """)

    st.subheader("Filtros")

    data_min = df["data_hora"].min().date()
    data_max = df["data_hora"].max().date()

    intervalo = st.date_input(
        "Selecione o intervalo de análise",
        value=(data_min, data_max),
        min_value=data_min,
        max_value=data_max
    )

    if isinstance(intervalo, tuple) and len(intervalo) == 2:

        data_inicio, data_fim = intervalo

        df_filtrado = df[
            (df["data_hora"].dt.date >= data_inicio) &
            (df["data_hora"].dt.date <= data_fim)
        ]

    else:
        df_filtrado = df.copy()

    if df_filtrado.empty:

        st.warning("Não há dados para o período selecionado.")

    else:

        media = df_filtrado["umidade_percentual"].mean()
        minimo = df_filtrado["umidade_percentual"].min()
        maximo = df_filtrado["umidade_percentual"].max()

        ligado = (
            df_filtrado["estado_bomba"].str.lower() == "ligada"
        ).sum()

        k1, k2, k3, k4 = st.columns(4)

        k1.metric("Umidade média", f"{media:.2f}%")
        k2.metric("Umidade mínima", f"{minimo:.2f}%")
        k3.metric("Umidade máxima", f"{maximo:.2f}%")
        k4.metric("Registros", len(df_filtrado))

        st.markdown("---")

        # GRÁFICO DE UMIDADE

        st.subheader("Comportamento da umidade ao longo do tempo")

        fig_umidade = px.line(
            df_filtrado,
            x="data_hora",
            y="umidade_percentual",
            markers=True,
            title="Variação da umidade do solo",
            labels={
                "data_hora": "Data e hora",
                "umidade_percentual": "Umidade (%)"
            }
        )

        fig_umidade.update_layout(
            template="plotly_white",
            hovermode="x unified"
        )

        st.plotly_chart(fig_umidade, use_container_width=True)

        # HISTOGRAMA

        st.subheader("Distribuição dos níveis de umidade")

        fig_hist = px.histogram(
            df_filtrado,
            x="umidade_percentual",
            nbins=20,
            title="Distribuição das leituras de umidade",
            labels={
                "umidade_percentual": "Umidade (%)",
                "count": "Frequência"
            }
        )

        fig_hist.update_layout(template="plotly_white")

        st.plotly_chart(fig_hist, use_container_width=True)

        # ADC

        st.subheader("Valores analógicos do sensor")

        fig_adc = px.line(
            df_filtrado,
            x="data_hora",
            y="valor_adc",
            title="Variação do valor ADC",
            labels={
                "data_hora": "Data e hora",
                "valor_adc": "Valor ADC"
            }
        )

        fig_adc.update_layout(template="plotly_white")

        st.plotly_chart(fig_adc, use_container_width=True)

        # BOMBA

        st.subheader("Estado da bomba")

        estados = (
            df_filtrado["estado_bomba"]
            .value_counts()
            .reset_index()
        )

        estados.columns = ["Estado", "Quantidade"]

        fig_bomba = px.pie(
            estados,
            names="Estado",
            values="Quantidade",
            title="Distribuição dos estados da bomba",
            hole=0.45
        )

        st.plotly_chart(fig_bomba, use_container_width=True)

        st.metric("Registros com bomba ligada", int(ligado))

        # TEMPO DE BOMBA

        st.subheader("Tempo de funcionamento da bomba")

        fig_tempo = px.bar(
            df_filtrado,
            x="data_hora",
            y="tempo_bomba_segundos",
            title="Tempo de acionamento por registro",
            labels={
                "data_hora": "Data e hora",
                "tempo_bomba_segundos": "Tempo (segundos)"
            }
        )

        fig_tempo.update_layout(template="plotly_white")

        st.plotly_chart(fig_tempo, use_container_width=True)

        # TABELA ANALÍTICA

        st.subheader("Resumo estatístico")

        resumo = df_filtrado[
            [
                "umidade_percentual",
                "valor_adc",
                "tempo_bomba_segundos"
            ]
        ].describe().round(2)

        st.dataframe(resumo, use_container_width=True)

# =========================================================
# PÁGINA 5 - VALIDAÇÃO
# =========================================================

elif pagina == "Validação":

    st.title("✅ Verificação e validação dos dados")

    st.write("""
    Após o armazenamento e a análise, foi realizada uma etapa de
    verificação para avaliar a integridade dos registros, identificar
    possíveis inconsistências e conferir se os dados estavam adequados
    para utilização.
    """)

    # VERIFICAÇÕES

    duplicados = df["id"].duplicated().sum()

    nulos = df.isnull().sum().sum()

    umidade_fora = (
        (df["umidade_percentual"] < 0) |
        (df["umidade_percentual"] > 100)
    ).sum()

    estados_invalidos = (
        ~df["estado_bomba"].str.lower().isin(["ligada", "desligada"])
    ).sum()

    ids_unicos = df["id"].nunique()

    # RESULTADOS

    st.subheader("Indicadores de qualidade")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("IDs duplicados", int(duplicados))
    c2.metric("Valores nulos", int(nulos))
    c3.metric("Umidade inválida", int(umidade_fora))
    c4.metric("Estados inválidos", int(estados_invalidos))

    st.markdown("---")

    verificacoes = pd.DataFrame({
        "Verificação": [
            "Quantidade de registros",
            "Identificadores únicos",
            "IDs duplicados",
            "Valores nulos",
            "Umidade entre 0% e 100%",
            "Estado da bomba válido"
        ],
        "Resultado": [
            total_registros,
            ids_unicos,
            int(duplicados),
            int(nulos),
            int(umidade_fora),
            int(estados_invalidos)
        ],
        "Status": [
            "Verificado",
            "Verificado",
            "OK" if duplicados == 0 else "Atenção",
            "OK" if nulos == 0 else "Atenção",
            "OK" if umidade_fora == 0 else "Atenção",
            "OK" if estados_invalidos == 0 else "Atenção"
        ]
    })

    st.subheader("Checklist de integridade")

    st.dataframe(
        verificacoes,
        use_container_width=True,
        hide_index=True
    )

    # VERIFICAÇÃO DE DATA E ORGANIZAÇÃO

    datas_ordenadas = df["data_hora"].is_monotonic_increasing

    st.subheader("Organização temporal")

    if datas_ordenadas:
        st.success("Os registros estão ordenados cronologicamente.")
    else:
        st.warning("Os registros não estão totalmente ordenados por data.")

    # RESULTADO GERAL

    validacao_ok = (
        duplicados == 0 and
        nulos == 0 and
        umidade_fora == 0 and
        estados_invalidos == 0 and
        datas_ordenadas
    )

    st.markdown("---")

    if validacao_ok:
        st.success(
            "As verificações realizadas não identificaram inconsistências "
            "nos critérios avaliados."
        )
    else:
        st.warning(
            "Foram encontradas situações que precisam ser avaliadas "
            "nos critérios de integridade."
        )

    st.caption(
        "As verificações são executadas automaticamente sobre os dados "
        "carregados do PostgreSQL. Elas não substituem a validação física "
        "do sensor ou do sistema de irrigação."
    )

# =========================================================
# RODAPÉ
# =========================================================

st.markdown("---")

st.markdown("""
<div style="text-align:center; color:#65776b;">
    🌱 Projeto Horta Inteligente |
    Monitoramento • Banco de Dados • Ciência de Dados
</div>
""", unsafe_allow_html=True)
