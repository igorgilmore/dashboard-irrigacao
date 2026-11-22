from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Painel de Irrigação", page_icon="💧", layout="wide")

REPO = "igorgilmore/dashboard-irrigacao"
CSV_URL = f"https://raw.githubusercontent.com/{REPO}/main/base_irriga%C3%A7%C3%A3o.csv"
CSV_LOCAL = Path("base_irrigação.csv")


# ---------- Dados ----------
@st.cache_data(ttl=300)  # atualiza a cada 5 min se o CSV mudar no GitHub
def carregar_dados() -> tuple[pd.DataFrame, str]:
    try:
        df, origem = pd.read_csv(CSV_URL), "GitHub"
    except Exception:
        if not CSV_LOCAL.exists():
            raise
        df, origem = pd.read_csv(CSV_LOCAL), "arquivo local"
    df["data_hora"] = pd.to_datetime(df["data_hora"])
    df["bomba_ligada"] = df["estado_bomba"].eq("Ligada")
    df["data"] = df["data_hora"].dt.date
    df["hora"] = df["data_hora"].dt.hour
    return df.sort_values("data_hora"), origem


try:
    df, origem = carregar_dados()
except Exception as e:
    st.error(f"Não foi possível carregar o CSV: {e}")
    st.stop()

# ---------- Navegação ----------
secao = st.sidebar.radio(
    "Navegação", ["Projeto", "Coleta dos dados", "Armazenamento", "Análise dos resultados"]
)
st.sidebar.markdown("---")
st.sidebar.caption(f"Dados lidos de: {origem}")
st.sidebar.caption(f"Autor: SEU NOME · github.com/{REPO}")

# ---------- 1. Projeto ----------
if secao == "Projeto":
    st.title("💧 Painel de Irrigação")
    st.subheader("Monitoramento da umidade do solo e do acionamento da bomba")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Problema")
        st.write("Descreva o problema (ex.: irrigar no momento certo, sem desperdício de água).")
        st.markdown("### Objetivo")
        st.write("Descreva o que o projeto busca entregar.")
    with c2:
        st.markdown("### Tecnologias")
        st.write("Sensor de umidade · Python · Streamlit · Pandas · Plotly · PostgreSQL")
        st.markdown("### Resultado")
        st.write("Dashboard com o histórico de umidade e dos acionamentos da bomba.")

# ---------- 2. Coleta ----------
elif secao == "Coleta dos dados":
    st.title("🔎 Coleta dos dados")
    intervalo = df["data_hora"].diff().mode().iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Leituras", len(df))
    c2.metric("Início", f"{df['data_hora'].min():%d/%m %H:%M}")
    c3.metric("Fim", f"{df['data_hora'].max():%d/%m %H:%M}")
    c4.metric("Intervalo entre leituras", f"{int(intervalo.total_seconds() // 60)} min")

    st.markdown("#### O que cada coluna representa")
    st.table(
        pd.DataFrame(
            {
                "coluna": ["data_hora", "umidade_percentual", "valor_adc",
                           "tempo_bomba_segundos", "estado_bomba"],
                "descrição": [
                    "Momento da leitura",
                    "Umidade do solo em %",
                    "Valor bruto lido pelo conversor analógico-digital do sensor",
                    "Tempo em que a bomba ficou acionada na leitura",
                    "Ligada ou Desligada",
                ],
            }
        )
    )
    st.markdown("#### Amostra dos dados")
    st.dataframe(df.drop(columns=["bomba_ligada", "data", "hora"]).head(30),
                 width="stretch")

# ---------- 3. Armazenamento ----------
elif secao == "Armazenamento":
    st.title("🗄️ Armazenamento no banco de dados")
    st.write("Cada leitura do sensor vira uma linha na tabela, em ordem cronológica.")
    st.code(
        "CREATE TABLE leituras_irrigacao (\n"
        "    data_hora            TIMESTAMP PRIMARY KEY,\n"
        "    umidade_percentual   REAL,\n"
        "    valor_adc            INTEGER,\n"
        "    tempo_bomba_segundos REAL,\n"
        "    estado_bomba         TEXT\n"
        ");",
        language="sql",
    )
    st.markdown("#### Exemplo de consulta")
    st.code(
        "SELECT DATE(data_hora) AS dia, COUNT(*) AS acionamentos\n"
        "FROM leituras_irrigacao\n"
        "WHERE estado_bomba = 'Ligada'\n"
        "GROUP BY dia ORDER BY dia;",
        language="sql",
    )
    st.markdown("#### Resultado equivalente nos dados")
    st.dataframe(
        df[df["bomba_ligada"]].groupby("data").size().rename("acionamentos").reset_index(),
        width="stretch",
    )

# ---------- 4. Análise ----------
elif secao == "Análise dos resultados":
    st.title("📈 Análise dos resultados")

    dias = sorted(df["data"].unique())
    ini, fim = st.select_slider("Período", options=dias, value=(dias[0], dias[-1]))
    d = df[(df["data"] >= ini) & (df["data"] <= fim)]
    lig = d[d["bomba_ligada"]]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Umidade média", f"{d['umidade_percentual'].mean():.1f}%")
    c2.metric("Umidade mínima", f"{d['umidade_percentual'].min():.1f}%")
    c3.metric("Acionamentos da bomba", len(lig))
    c4.metric("Tempo total de bomba", f"{d['tempo_bomba_segundos'].sum():.0f} s")

    # Umidade ao longo do tempo com marcação dos acionamentos
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["data_hora"], y=d["umidade_percentual"],
                             mode="lines", name="Umidade (%)"))
    fig.add_trace(go.Scatter(x=lig["data_hora"], y=lig["umidade_percentual"],
                             mode="markers", name="Bomba ligada",
                             marker=dict(size=9, color="red", symbol="triangle-up")))
    fig.update_layout(title="Umidade do solo ao longo do tempo",
                      yaxis_title="Umidade (%)", xaxis_title="Data e hora")
    st.plotly_chart(fig, width="stretch")

    col_a, col_b = st.columns(2)
    with col_a:
        por_dia = d.groupby("data")["bomba_ligada"].sum().reset_index(name="acionamentos")
        st.plotly_chart(px.bar(por_dia, x="data", y="acionamentos",
                               title="Acionamentos da bomba por dia"),
                        width="stretch")
    with col_b:
        por_hora = d.groupby("hora")["umidade_percentual"].mean().reset_index()
        st.plotly_chart(px.line(por_hora, x="hora", y="umidade_percentual", markers=True,
                                title="Umidade média por hora do dia"),
                        width="stretch")

    st.plotly_chart(px.scatter(d, x="valor_adc", y="umidade_percentual",
                               color="estado_bomba",
                               title="Relação entre valor ADC e umidade"),
                    width="stretch")

    st.markdown("### Principais conclusões")
    if len(lig):
        st.write(
            f"- A bomba foi acionada **{len(lig)} vezes**, sempre com umidade entre "
            f"**{lig['umidade_percentual'].min():.1f}%** e **{lig['umidade_percentual'].max():.1f}%**."
        )
    corr = d["valor_adc"].corr(d["umidade_percentual"])
    st.write(f"- Correlação entre valor ADC e umidade: **{corr:.3f}** "
             "(quanto maior o ADC, mais seco o solo)." if corr < 0 else
             f"- Correlação entre valor ADC e umidade: **{corr:.3f}**.")
    st.write("- Adicione aqui as suas próprias conclusões.")
    st.markdown("### Próximos passos")
    st.write("O que dá para melhorar ou expandir?")
