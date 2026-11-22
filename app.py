import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

st.set_page_config(page_title="Apresentação do Projeto", page_icon="📊", layout="wide")

# ---------- Navegação ----------
SECOES = ["Projeto", "Coleta dos dados", "Banco de dados", "Análise dos resultados"]
secao = st.sidebar.radio("Navegação", SECOES)
st.sidebar.markdown("---")
st.sidebar.caption("Autor: SEU NOME · Link do GitHub: https://github.com/SEU_USUARIO/SEU_REPO")


# ---------- Conexão com o PostgreSQL ----------
@st.cache_resource
def get_engine():
    """Lê as credenciais de .streamlit/secrets.toml (seção [postgres])."""
    c = st.secrets["postgres"]
    url = URL.create(
        "postgresql+psycopg2",
        username=c["user"],
        password=c["password"],
        host=c["host"],
        port=int(c.get("port", 5432)),
        database=c["dbname"],
    )
    return create_engine(url, pool_pre_ping=True)


@st.cache_data(ttl=600)
def consultar(sql: str) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(sql, conn)


def carregar_dados() -> pd.DataFrame:
    try:
        return consultar("SELECT * FROM minha_tabela")  # troque pela sua tabela
    except Exception as e:
        st.sidebar.error(f"Sem conexão com o banco: {e}")
        # Dados de exemplo para a apresentação não quebrar
        return pd.DataFrame({"categoria": ["A", "B", "C", "D"], "valor": [120, 80, 150, 60]})


df = carregar_dados()

# ---------- 1. Projeto ----------
if secao == "Projeto":
    st.title("📊 Nome do Projeto")
    st.subheader("Uma frase que resume o que o projeto faz")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Problema")
        st.write("Qual dor ou pergunta o projeto resolve?")
        st.markdown("### Objetivo")
        st.write("O que você queria alcançar?")
    with col2:
        st.markdown("### Tecnologias")
        st.write("Python · Streamlit · Pandas · SQL · ...")
        st.markdown("### Resultado esperado")
        st.write("Qual é o valor entregue?")

# ---------- 2. Coleta ----------
elif secao == "Coleta dos dados":
    st.title("🔎 Coleta dos dados")
    st.write("De onde vêm os dados? (API, web scraping, formulário, planilha...)")

    c1, c2, c3 = st.columns(3)
    c1.metric("Fonte", "NOME DA FONTE")
    c2.metric("Registros coletados", f"{len(df)}")
    c3.metric("Frequência", "Diária / Pontual")

    st.markdown("#### Como foi feita a coleta")
    st.code(
        "import requests\n\n"
        "resposta = requests.get('URL_DA_FONTE')\n"
        "dados = resposta.json()",
        language="python",
    )
    st.markdown("#### Amostra dos dados brutos")
    st.dataframe(df, use_container_width=True)

# ---------- 3. Banco de dados ----------
elif secao == "Banco de dados":
    st.title("🗄️ Armazenamento no banco de dados")
    st.write("Qual banco foi usado e por quê? Como os dados ficam organizados?")

    st.markdown("#### Estrutura da tabela")
    st.code(
        "CREATE TABLE minha_tabela (\n"
        "    id INTEGER PRIMARY KEY,\n"
        "    categoria TEXT,\n"
        "    valor REAL\n"
        ");",
        language="sql",
    )

    st.markdown("#### Consulta ao vivo")
    consulta = st.text_area("SQL (somente SELECT)", "SELECT * FROM minha_tabela LIMIT 20")
    if st.button("Executar"):
        if not consulta.strip().lower().startswith("select"):
            st.warning("Por segurança, só consultas SELECT são permitidas.")
        else:
            try:
                st.dataframe(consultar(consulta), use_container_width=True)
            except Exception as e:
                st.error(f"Erro na consulta: {e}")

# ---------- 4. Análise ----------
elif secao == "Análise dos resultados":
    st.title("📈 Análise dos resultados")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total", int(df["valor"].sum()))
    c2.metric("Média", round(df["valor"].mean(), 1))
    c3.metric("Maior valor", int(df["valor"].max()))

    fig = px.bar(df, x="categoria", y="valor", title="Valor por categoria")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Principais conclusões")
    st.write("- Insight 1\n- Insight 2\n- Insight 3")

    st.markdown("### Próximos passos")
    st.write("O que dá para melhorar ou expandir?")
