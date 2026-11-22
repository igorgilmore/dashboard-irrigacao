from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Horta Automatizada", page_icon="🌱", layout="wide")

# ---------- Configuração ----------
AUTOR = "Igor"
REPO = "igorgilmore/dashboard-irrigacao"
CSV_URL = f"https://raw.githubusercontent.com/{REPO}/main/base_irriga%C3%A7%C3%A3o.csv"
CSV_LOCAL = Path("base_irrigação.csv")
IMG_DIR = Path("imagens")
DADOS_SIMULADOS = True  # troque para False quando usar medições reais do sensor

# Mesmos parâmetros do sketch do Arduino e do analise_horta.py
ADC_SECO, ADC_MOLHADO = 620, 260
LIMIAR, TEMPO_BOMBA, INTERVALO_MIN = 40, 2, 20
SALTO_P_P, LACUNA_MIN = 25, 40
VERDE, AZUL, LARANJA, VERMELHO = "#2E7D32", "#1565C0", "#EF6C00", "#C62828"


# ---------- Dados ----------
@st.cache_data(ttl=300)  # se o CSV mudar no GitHub, o painel atualiza em até 5 min
def carregar_dados() -> tuple[pd.DataFrame, str]:
    try:
        df, origem = pd.read_csv(CSV_URL), "GitHub"
    except Exception:
        if not CSV_LOCAL.exists():
            raise
        df, origem = pd.read_csv(CSV_LOCAL), "arquivo local"
    df["data_hora"] = pd.to_datetime(df["data_hora"])
    df = df.sort_values("data_hora").reset_index(drop=True)
    df["ligada"] = df["estado_bomba"].eq("Ligada")
    df["dia"] = df["data_hora"].dt.normalize()
    df["hora"] = df["data_hora"].dt.hour
    df["gap_min"] = df["data_hora"].diff().dt.total_seconds() / 60
    df["salto"] = df["umidade_percentual"].diff().abs()
    return df, origem


try:
    df, origem = carregar_dados()
except Exception as e:
    st.error(f"Não foi possível carregar o CSV: {e}")
    st.stop()

periodo = f"{df['data_hora'].min():%d/%m/%Y} a {df['data_hora'].max():%d/%m/%Y}"


def aviso_simulado():
    if DADOS_SIMULADOS:
        st.warning(
            "**Dados de teste (simulados).** A base foi gerada pelo script `gerar_base_teste.py`, "
            "no mesmo formato que o Arduino UNO envia. Não são medições de um solo real."
        )


# ---------- Navegação ----------
secao = st.sidebar.radio(
    "Navegação", ["Projeto", "Coleta dos dados", "Armazenamento", "Análise dos resultados"]
)
st.sidebar.markdown("---")
if DADOS_SIMULADOS:
    st.sidebar.warning("Dados simulados")
st.sidebar.caption(f"Dados lidos de: {origem}")
st.sidebar.caption(f"Autor: {AUTOR}")
st.sidebar.caption(f"github.com/{REPO}")

# ---------- 1. Projeto ----------
if secao == "Projeto":
    st.title("🌱 Horta Automatizada")
    st.subheader("Irrigação automática com Arduino, banco de dados e painel de análise")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Problema")
        st.write("Regar a horta na hora certa, sem depender de alguém lembrar e sem desperdiçar água.")
        st.markdown("### Solução")
        st.write(
            f"Um sensor mede a umidade do solo. Quando ela fica **abaixo de {LIMIAR}%**, o Arduino "
            f"liga a válvula solenoide por **{TEMPO_BOMBA} s**. Cada leitura é enviada ao computador, "
            "guardada em um banco PostgreSQL e analisada em Python."
        )
    with c2:
        st.markdown("### Componentes")
        st.write(
            "- Arduino UNO\n"
            "- Sensor de umidade do solo capacitivo\n"
            "- Módulo relé de 5 V\n"
            "- Válvula solenoide de 12 V\n"
            "- Display LCD 16x2 com potenciômetro de contraste\n"
            "- Protoboard e jumpers"
        )
        st.markdown("### Tecnologias")
        st.write("Arduino (C++) · Python · PostgreSQL · Pandas · Plotly · Streamlit")

    st.markdown("### Fluxo do sistema")
    st.code(
        "Sensor de solo → Arduino UNO → serial/USB → coletor.py → PostgreSQL → análise → painel\n"
        "                      ↓\n"
        "          relé → válvula solenoide (liga por 2 s se umidade < 40%)",
        language="text",
    )

    fotos = [IMG_DIR / "montagem_1.jpg", IMG_DIR / "montagem_2.jpg"]
    if all(f.exists() for f in fotos):
        st.markdown("### Montagem")
        f1, f2 = st.columns(2)
        f1.image(str(fotos[0]), caption="Circuito montado: Arduino, relé, válvula e display")
        f2.image(str(fotos[1]), caption="Sensor de solo no copo e leitura no LCD")

# ---------- 2. Coleta ----------
elif secao == "Coleta dos dados":
    st.title("🔎 Coleta dos dados")
    aviso_simulado()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Leituras", len(df))
    c2.metric("Período", periodo)
    c3.metric("Intervalo entre leituras", f"{INTERVALO_MIN} min")
    c4.metric("Comunicação", "Serial 9600 baud")

    a, b = st.columns(2)
    with a:
        st.markdown("#### Do sensor ao percentual")
        st.write(
            "O Arduino lê o sensor numa entrada analógica (valor ADC, de 0 a 1023) e converte "
            "para porcentagem com a calibração do projeto:"
        )
        st.code(
            f"ADC seco    = {ADC_SECO}   →   0 % de umidade\n"
            f"ADC molhado = {ADC_MOLHADO}   → 100 % de umidade\n\n"
            f"umidade = (adc - {ADC_SECO}) * 100 / ({ADC_MOLHADO} - {ADC_SECO})   # limitada de 0 a 100",
            language="text",
        )
    with b:
        st.markdown("#### O que o Arduino envia pela serial")
        st.write("Uma linha por leitura, separada por vírgulas: umidade, ADC, tempo da bomba, estado.")
        p = df.iloc[0]
        st.code(f"{p.umidade_percentual},{p.valor_adc},{p.tempo_bomba_segundos},{p.estado_bomba}",
                language="text")
        st.markdown("#### Script coletor (`coletor.py`)")
        st.code(
            "arduino = serial.Serial(PORTA, 9600)\n"
            "while True:\n"
            "    linha = arduino.readline().decode().strip()\n"
            "    umidade, adc, tempo, estado = linha.split(',')\n"
            "    cur.execute(INSERT_SQL, (datetime.now(), umidade, adc, tempo, estado))\n"
            "    conn.commit()",
            language="python",
        )

    st.markdown("#### Colunas coletadas")
    st.table(pd.DataFrame({
        "coluna": ["data_hora", "umidade_percentual", "valor_adc", "tempo_bomba_segundos", "estado_bomba"],
        "descrição": ["Momento da leitura (data e hora do computador)", "Umidade do solo em %",
                      "Valor bruto do conversor analógico-digital (0 a 1023)",
                      "Segundos em que a bomba ficou acionada", "Ligada ou Desligada"],
    }))
    st.markdown("#### Amostra dos dados")
    st.dataframe(df[["data_hora", "umidade_percentual", "valor_adc", "tempo_bomba_segundos",
                     "estado_bomba"]].head(30), width="stretch")

# ---------- 3. Armazenamento ----------
elif secao == "Armazenamento":
    st.title("🗄️ Armazenamento no banco de dados")
    st.write(
        "Cada linha recebida do Arduino vira um registro na tabela `leituras`, em um banco "
        "PostgreSQL no servidor da instituição."
    )
    st.markdown("#### Estrutura da tabela (tipos ilustrativos)")
    st.code(
        "CREATE TABLE leituras (\n"
        "    data_hora            TIMESTAMP,\n"
        "    umidade_percentual   REAL,\n"
        "    valor_adc            INTEGER,\n"
        "    tempo_bomba_segundos REAL,\n"
        "    estado_bomba         TEXT\n"
        ");",
        language="sql",
    )
    st.markdown("#### Gravação (feita pelo `coletor.py`)")
    st.code(
        "INSERT INTO leituras\n"
        "  (data_hora, umidade_percentual, valor_adc, tempo_bomba_segundos, estado_bomba)\n"
        "VALUES (%s, %s, %s, %s, %s);",
        language="sql",
    )

    a, b = st.columns(2)
    with a:
        st.markdown("#### Consulta: acionamentos por dia")
        st.code(
            "SELECT DATE(data_hora) AS dia, COUNT(*) AS acionamentos\n"
            "FROM leituras\n"
            "WHERE estado_bomba = 'Ligada'\n"
            "GROUP BY dia ORDER BY dia;",
            language="sql",
        )
    with b:
        st.markdown("#### Resultado nos dados do painel")
        por_dia = df.groupby(df["dia"].dt.date)["ligada"].sum().rename("acionamentos").reset_index()
        por_dia = por_dia[por_dia["acionamentos"] > 0]
        st.dataframe(por_dia.rename(columns={"dia": "dia"}), width="stretch", hide_index=True)

    st.info("Para a apresentação, o painel lê um arquivo CSV no mesmo formato da tabela, hospedado no GitHub.")

# ---------- 4. Análise ----------
elif secao == "Análise dos resultados":
    st.title("📈 Análise dos resultados")
    aviso_simulado()

    lig = df[df["ligada"]]
    por_dia = df.groupby("dia")["ligada"].sum()
    h = df.groupby("hora").agg(umid=("umidade_percentual", "mean"), ac=("ligada", "sum"))
    h = h.reindex(range(24), fill_value=0)

    tab1, tab2, tab3 = st.tabs(["Visão geral", "Padrões", "Alertas e qualidade"])

    # ----- Visão geral -----
    with tab1:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Leituras", len(df))
        c2.metric("Umidade média do solo", f"{df['umidade_percentual'].mean():.1f}%")
        c3.metric("Acionamentos da bomba", f"{len(lig)} ({df['ligada'].mean():.1%})")
        c4.metric("Tempo total de bomba", f"{df['tempo_bomba_segundos'].sum():.0f} s")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["data_hora"], y=df["umidade_percentual"], mode="lines",
                                 name="Umidade do solo (%)", line=dict(color=AZUL, width=1.5)))
        fig.add_trace(go.Scatter(x=lig["data_hora"], y=lig["umidade_percentual"], mode="markers",
                                 name="Bomba ligada", marker=dict(color=LARANJA, size=8)))
        fig.add_hline(y=LIMIAR, line_dash="dash", line_color=VERMELHO,
                      annotation_text=f"Limiar de acionamento ({LIMIAR}%)")
        fig.update_layout(title="Umidade do solo ao longo do tempo", yaxis_title="Umidade (%)",
                          xaxis_title="Data e hora", legend=dict(orientation="h", y=-0.25))
        st.plotly_chart(fig, width="stretch")

        a, b = st.columns(2)
        with a:
            fig = px.bar(x=por_dia.index, y=por_dia.values, title="Acionamentos da bomba por dia",
                         labels={"x": "Dia", "y": "Acionamentos"}, color_discrete_sequence=[LARANJA])
            st.plotly_chart(fig, width="stretch")
        with b:
            fig = px.histogram(df, x="umidade_percentual", nbins=20,
                               title="Distribuição da umidade do solo",
                               labels={"umidade_percentual": "Umidade (%)"},
                               color_discrete_sequence=[VERDE])
            fig.add_vline(x=LIMIAR, line_dash="dash", line_color=VERMELHO)
            st.plotly_chart(fig, width="stretch")

    # ----- Padrões -----
    with tab2:
        a, b = st.columns(2)
        with a:
            fig = px.line(h.reset_index(), x="hora", y="umid", markers=True,
                          title="Umidade média por hora do dia",
                          labels={"hora": "Hora", "umid": "Umidade (%)"},
                          color_discrete_sequence=[AZUL])
            st.plotly_chart(fig, width="stretch")
        with b:
            fig = px.bar(h.reset_index(), x="hora", y="ac", title="Acionamentos por hora do dia",
                         labels={"hora": "Hora", "ac": "Acionamentos"},
                         color_discrete_sequence=[LARANJA])
            st.plotly_chart(fig, width="stretch")

        dia = df.groupby("dia")["umidade_percentual"].agg(["min", "mean", "max"])
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dia.index, y=dia["max"], mode="lines", line=dict(width=0),
                                 showlegend=False))
        fig.add_trace(go.Scatter(x=dia.index, y=dia["min"], mode="lines", line=dict(width=0),
                                 fill="tonexty", fillcolor="rgba(21,101,192,0.2)", name="mín–máx do dia"))
        fig.add_trace(go.Scatter(x=dia.index, y=dia["mean"], mode="lines+markers", name="média do dia",
                                 line=dict(color=AZUL)))
        fig.add_hline(y=LIMIAR, line_dash="dash", line_color=VERMELHO)
        fig.update_layout(title="Umidade diária (mínima, média e máxima)", yaxis_title="Umidade (%)")
        st.plotly_chart(fig, width="stretch")

        corr = df["umidade_percentual"].corr(df["valor_adc"])
        fig = px.scatter(df, x="umidade_percentual", y="valor_adc", color="estado_bomba",
                         color_discrete_map={"Ligada": LARANJA, "Desligada": AZUL},
                         title=f"Sensor: valor ADC × umidade (correlação {corr:.3f})",
                         labels={"umidade_percentual": "Umidade (%)", "valor_adc": "Valor ADC"})
        st.plotly_chart(fig, width="stretch")
        st.caption("A umidade é calculada a partir do ADC por uma conta linear, por isso a relação "
                   "é praticamente perfeita.")

    # ----- Alertas -----
    with tab3:
        fora = df[(df["valor_adc"] > ADC_SECO) | (df["valor_adc"] < ADC_MOLHADO)]
        saltos = df[df["salto"] > SALTO_P_P]
        lacunas = df[df["gap_min"] > LACUNA_MIN]
        seq = (df["ligada"] != df["ligada"].shift()).cumsum()
        tam = df[df["ligada"]].groupby(seq).size()
        seq_longas = tam[tam >= 3]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Leituras fora da faixa do sensor", len(fora))
        c2.metric(f"Saltos bruscos (> {SALTO_P_P} p.p.)", len(saltos))
        c3.metric(f"Lacunas de coleta (> {LACUNA_MIN} min)", len(lacunas))
        c4.metric("Irrigações seguidas (3 ou mais)", len(seq_longas))

        a, b = st.columns(2)
        with a:
            dia_top = por_dia.idxmax()
            d = df[df["dia"] == dia_top]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=d["data_hora"], y=d["umidade_percentual"], mode="lines+markers",
                                     name="Umidade (%)", line=dict(color=AZUL)))
            dl = d[d["ligada"]]
            fig.add_trace(go.Scatter(x=dl["data_hora"], y=dl["umidade_percentual"], mode="markers",
                                     name="Bomba ligada", marker=dict(color=LARANJA, size=10)))
            fig.add_hline(y=LIMIAR, line_dash="dash", line_color=VERMELHO)
            fig.update_layout(title=f"Dia com mais acionamentos: {dia_top:%d/%m}",
                              yaxis_title="Umidade (%)")
            st.plotly_chart(fig, width="stretch")
        with b:
            st.markdown("#### Alertas")
            maior = ""
            if df["salto"].notna().any():
                i = df["salto"].idxmax()
                maior = f" Maior: {df.loc[i, 'salto']:.0f} p.p. em {df.loc[i, 'data_hora']:%d/%m %H:%M}."
            st.write(
                f"1. **Faixa do sensor:** {len(fora)} leituras com ADC fora de {ADC_MOLHADO} a {ADC_SECO} "
                "(sensor solto ou com defeito).\n"
                f"2. **Saltos bruscos:** {len(saltos)} ocorrências.{maior}\n"
                f"3. **Lacunas de coleta:** {len(lacunas)} intervalos acima de {LACUNA_MIN} min sem leitura.\n"
                f"4. **Irrigação sem efeito:** {len(seq_longas)} sequências de 3 ou mais acionamentos seguidos"
                + (f" (maior: {tam.max()})." if len(tam) else ".") + "\n"
                f"5. **Dia crítico:** {dia_top:%d/%m}, com {int(por_dia.max())} acionamentos."
            )

    # ----- Conclusões -----
    st.markdown("---")
    st.markdown("### Principais conclusões")
    hora_pico = int(h["ac"].idxmax())
    st.write(
        f"- A bomba foi acionada **{len(lig)} vezes** em {periodo}, somando "
        f"**{df['tempo_bomba_segundos'].sum():.0f} s**, sempre com umidade entre "
        f"**{lig['umidade_percentual'].min():.1f}%** e **{lig['umidade_percentual'].max():.1f}%**.\n"
        f"- O horário com mais acionamentos foi **{hora_pico}h** ({int(h['ac'].max())} acionamentos).\n"
        f"- O dia com mais irrigações foi **{por_dia.idxmax():%d/%m}** ({int(por_dia.max())})."
    )
    if DADOS_SIMULADOS:
        st.markdown("### Limitação")
        st.write("Os dados são simulados: os resultados demonstram o funcionamento do sistema e da "
                 "análise, mas não o comportamento de um solo real.")
    st.markdown("### Próximos passos")
    st.write("- Coletar leituras reais da horta com o `coletor.py` rodando de forma contínua.\n"
             "- Ler os dados direto do banco no painel.\n"
             "- Ajustar o limiar de acionamento com base nos dados reais.")
