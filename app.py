from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Apresentação do Projeto", page_icon="📊", layout="wide")

CSV_PADRAO = Path("dados.csv")  # coloque o CSV na mesma pasta do app.py

# ---------- Navegação ----------
SECOES = ["Projeto", "Coleta dos dados", "Armazenamento", "Análise dos resultados"]
secao = st.sidebar.radio("Navegação", SECOES)
st.sidebar.markdown("---")
arquivo = st.sidebar.file_uploader("Trocar o CSV (opcional)", type="csv")
st.sidebar.caption("Autor: SEU NOME · GitHub: https://github.com/igorgilmore/dashboard-irrigacao")


# ---------- Dados ----------
@st.cache_data
def ler_csv(origem) -> pd.DataFrame:
    for enc in ("utf-8", "latin-1"):
        try:
            if hasattr(origem, "seek"):
                origem.seek(0)
            return pd.read_csv(origem, sep=None, engine="python", encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("Não foi possível ler o CSV.")


def carregar_dados() -> pd.DataFrame | None:
    if arquivo is not None:
        df = ler_csv(arquivo)
    elif CSV_PADRAO.exists():
        df = ler_csv(CSV_PADRAO)
    else:
        return None
    # tenta converter colunas de data automaticamente
    for col in df.select_dtypes(include="object").columns:
        if any(k in col.lower() for k in ("data", "date", "hora", "time")):
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


df = carregar_dados()

if df is None:
    st.title("📊 Apresentação do Projeto")
    st.warning("Coloque um arquivo `dados.csv` na pasta do app ou envie um CSV pela barra lateral.")
    st.stop()

num_cols = df.select_dtypes(include="number").columns.tolist()
data_cols = df.select_dtypes(include="datetime").columns.tolist()
cat_cols = [c for c in df.columns if c not in num_cols + data_cols]

# ---------- 1. Projeto ----------
if secao == "Projeto":
    st.title("💧 Nome do Projeto")
    st.subheader("Uma frase que resume o que o projeto faz")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Problema")
        st.write("Qual dor ou pergunta o projeto resolve?")
        st.markdown("### Objetivo")
        st.write("O que você queria alcançar?")
    with c2:
        st.markdown("### Tecnologias")
        st.write("Python · Streamlit · Pandas · Plotly · PostgreSQL · ...")
        st.markdown("### Resultado esperado")
        st.write("Qual é o valor entregue?")

# ---------- 2. Coleta ----------
elif secao == "Coleta dos dados":
    st.title("🔎 Coleta dos dados")
    st.write("De onde vêm os dados? (sensores, API, planilha, formulário...)")
    c1, c2, c3 = st.columns(3)
    c1.metric("Registros", f"{len(df):,}".replace(",", "."))
    c2.metric("Colunas", df.shape[1])
    if data_cols:
        c3.metric("Período", f"{df[data_cols[0]].min():%d/%m/%Y} a {df[data_cols[0]].max():%d/%m/%Y}")
    st.markdown("#### Amostra dos dados")
    st.dataframe(df.head(50), use_container_width=True)
    st.markdown("#### Colunas e tipos")
    st.dataframe(
        pd.DataFrame({"coluna": df.columns, "tipo": df.dtypes.astype(str).values,
                      "nulos": df.isna().sum().values}),
        use_container_width=True,
    )

# ---------- 3. Armazenamento ----------
elif secao == "Armazenamento":
    st.title("🗄️ Armazenamento dos dados")
    st.write("Como os dados são guardados e organizados.")
    st.markdown("#### Estrutura (exemplo de tabela no PostgreSQL)")
    tipos = {"int64": "INTEGER", "float64": "REAL", "datetime64[ns]": "TIMESTAMP"}
    linhas = [f"    {c} {tipos.get(str(t), 'TEXT')}" for c, t in df.dtypes.items()]
    st.code("CREATE TABLE minha_tabela (\n" + ",\n".join(linhas) + "\n);", language="sql")
    st.info("Nesta apresentação os dados são lidos de um arquivo CSV exportado do banco.")
    st.download_button("Baixar CSV", df.to_csv(index=False).encode("utf-8"), "dados.csv", "text/csv")

# ---------- 4. Análise ----------
elif secao == "Análise dos resultados":
    st.title("📈 Análise dos resultados")

    if not num_cols:
        st.warning("O CSV não tem colunas numéricas para analisar.")
        st.stop()

    if cat_cols:
        filtro = st.selectbox("Filtrar por", ["(sem filtro)"] + cat_cols)
        if filtro != "(sem filtro)":
            valores = st.multiselect("Valores", sorted(df[filtro].dropna().unique()),
                                     default=sorted(df[filtro].dropna().unique()))
            df = df[df[filtro].isin(valores)]

    metrica = st.selectbox("Variável", num_cols)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Média", f"{df[metrica].mean():.2f}")
    c2.metric("Mínimo", f"{df[metrica].min():.2f}")
    c3.metric("Máximo", f"{df[metrica].max():.2f}")
    c4.metric("Desvio padrão", f"{df[metrica].std():.2f}")

    if data_cols:
        fig = px.line(df.sort_values(data_cols[0]), x=data_cols[0], y=metrica,
                      title=f"{metrica} ao longo do tempo")
        st.plotly_chart(fig, use_container_width=True)
    st.plotly_chart(px.histogram(df, x=metrica, title=f"Distribuição de {metrica}"),
                    use_container_width=True)

    if len(num_cols) > 1:
        st.plotly_chart(px.imshow(df[num_cols].corr(), text_auto=".2f",
                                  title="Correlação entre variáveis"),
                        use_container_width=True)

    st.markdown("### Principais conclusões")
    st.write("- Insight 1\n- Insight 2\n- Insight 3")
    st.markdown("### Próximos passos")
    st.write("O que dá para melhorar ou expandir?")
