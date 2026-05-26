import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------

st.set_page_config(
    page_title="DSS Vitícola",
    layout="wide"
)

# ---------------------------------------------------
# ESTILO
# ---------------------------------------------------

st.markdown("""
<style>

.main {
    background-color: #f4f6f9;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

div[data-testid="stMetric"] {
    background-color: white;
    border-radius: 12px;
    padding: 15px;
    border: 1px solid #dddddd;
}

</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# FUNCION GRAFICOS
# ---------------------------------------------------

def estilo_figura(fig):

    fig.update_layout(
        template="plotly_white",
        height=320,
        margin=dict(
            l=20,
            r=20,
            t=40,
            b=20
        ),
        hovermode="x unified",
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(size=13)
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor="#eeeeee"
    )

    fig.update_yaxes(
        showgrid=True,
        gridcolor="#eeeeee"
    )

    return fig

# ---------------------------------------------------
# TITULO
# ---------------------------------------------------

st.title("🍇 DSS Vitícola")
st.markdown(
    "### Dashboard epidemiológico estilo FieldClimate"
)

# ---------------------------------------------------
# UPLOAD
# ---------------------------------------------------

uploaded_file = st.file_uploader(
    "Sube archivo climático XLS",
    type=["xls"]
)

# ---------------------------------------------------
# APP
# ---------------------------------------------------

if uploaded_file:

    try:

        # ---------------------------------------------------
        # LEER XLS
        # ---------------------------------------------------

        df = pd.read_excel(
            uploaded_file,
            engine="xlrd"
        )

        st.success("Archivo cargado correctamente")

        # ---------------------------------------------------
        # COLUMNAS
        # ---------------------------------------------------

        fecha_col = df.columns[0]

        temp_col = "Temp. Aire"
        hr_col = "Humedad"
        lluvia_col = "Precip."
        viento_col = "Vel. Media"

        # ---------------------------------------------------
        # FECHAS
        # ---------------------------------------------------

        df[fecha_col] = pd.to_datetime(
            df[fecha_col],
            dayfirst=True,
            errors="coerce"
        )

        df = df.dropna(
            subset=[fecha_col]
        )

        # ---------------------------------------------------
        # NUMERICOS
        # ---------------------------------------------------

        for c in [
            temp_col,
            hr_col,
            lluvia_col,
            viento_col
        ]:

            df[c] = pd.to_numeric(
                df[c],
                errors="coerce"
            )

        # ---------------------------------------------------
        # DIA
        # ---------------------------------------------------

        df["DIA"] = (
            df[fecha_col].dt.date
        )

        # ---------------------------------------------------
        # ET0
        # ---------------------------------------------------

        df["ET0"] = (
            0.0023 *
            (df[temp_col] + 17.8) *
            np.sqrt(
                df[temp_col].clip(lower=0)
            )
        )

        df["ET0_ACUM"] = (
            df["ET0"].cumsum()
        )

        # ---------------------------------------------------
        # LLUVIA
        # ---------------------------------------------------

        df["LLUVIA_ACUM"] = (
            df[lluvia_col].cumsum()
        )

        # ---------------------------------------------------
        # GDD BASE 10
        # ---------------------------------------------------

        df["GDD10"] = (
            (df[temp_col] - 10)
            .clip(lower=0)
        )

        df["GDD10_ACUM"] = (
            df["GDD10"].cumsum()
        )

        # ---------------------------------------------------
        # BALANCE HIDRICO
        # ---------------------------------------------------

        CRAD = 120

        df["BALANCE"] = (
            CRAD +
            df["LLUVIA_ACUM"] -
            df["ET0_ACUM"]
        )

        # ---------------------------------------------------
        # RESUMEN DIARIO
        # ---------------------------------------------------

        diario = df.groupby("DIA").agg({

            temp_col: ["mean", "max"],

            hr_col: "mean",

            lluvia_col: "sum"

        })

        diario.columns = [
            "TEMP_MEDIA",
            "TEMP_MAX",
            "HR_MEDIA",
            "LLUVIA"
        ]

        diario = diario.reset_index()

        # ---------------------------------------------------
        # OIDIO GUBLER THOMAS
        # ---------------------------------------------------

        indice = 0

        oidio = []

        for i in range(len(diario)):

            t = diario["TEMP_MEDIA"].iloc[i]
            tmax = diario["TEMP_MAX"].iloc[i]

            if 21 <= t <= 30:

                indice += 20

            if tmax > 35:

                indice -= 20

            indice = max(0, min(100, indice))

            oidio.append(indice)

        diario["OIDIO"] = oidio

        # ---------------------------------------------------
        # BOTRITIS
        # ---------------------------------------------------

        diario["BOTRITIS"] = np.where(

            (
                (diario["HR_MEDIA"] > 85) &
                (diario["TEMP_MEDIA"] > 15)
            ),

            30,

            0
        )

        # ---------------------------------------------------
        # MILDIU PRIMARIO
        # ---------------------------------------------------

        mildiu_prim = []
        severidad_prim = []

        desarrollo = 0
        evento = False

        for i in range(len(diario)):

            lluvia = diario["LLUVIA"].iloc[i]
            hr = diario["HR_MEDIA"].iloc[i]
            temp = diario["TEMP_MEDIA"].iloc[i]

            condiciones = (

                lluvia > 2 and
                hr > 85 and
                11 <= temp <= 25

            )

            if condiciones and not evento:

                evento = True
                desarrollo = 20

            elif evento:

                if condiciones:

                    desarrollo += 20

                else:

                    desarrollo += 10

            if desarrollo >= 100:

                desarrollo = 0
                evento = False

            mildiu_prim.append(desarrollo)

            if desarrollo == 0:

                severidad = "Sin infección"

            elif desarrollo < 30:

                severidad = "Leve"

            elif desarrollo < 70:

                severidad = "Media"

            else:

                severidad = "Severa"

            severidad_prim.append(severidad)

        diario["MILDIU_PRIM"] = mildiu_prim
        diario["SEVERIDAD_PRIM"] = severidad_prim

        # ---------------------------------------------------
        # MILDIU SECUNDARIO
        # ---------------------------------------------------

        mildiu_sec = []
        severidad_sec = []

        desarrollo = 0
        evento = False

        for i in range(len(diario)):

            hr = diario["HR_MEDIA"].iloc[i]
            temp = diario["TEMP_MEDIA"].iloc[i]

            condiciones = (

                hr > 90 and
                12 <= temp <= 28

            )

            if condiciones and not evento:

                evento = True
                desarrollo = 15

            elif evento:

                if condiciones:

                    desarrollo += 15

                else:

                    desarrollo += 5

            if desarrollo >= 100:

                desarrollo = 0
                evento = False

            mildiu_sec.append(desarrollo)

            if desarrollo == 0:

                severidad = "Sin infección"

            elif desarrollo < 30:

                severidad = "Leve"

            elif desarrollo < 70:

                severidad = "Media"

            else:

                severidad = "Severa"

            severidad_sec.append(severidad)

        diario["MILDIU_SEC"] = mildiu_sec
        diario["SEVERIDAD_SEC"] = severidad_sec

        # ---------------------------------------------------
        # KPIS
        # ---------------------------------------------------

        st.header("📊 Resumen campaña")

        c1, c2, c3 = st.columns(3)

        with c1:

            st.metric(
                "☔ Lluvia acumulada",
                f"{df['LLUVIA_ACUM'].iloc[-1]:.1f} mm"
            )

        with c2:

            st.metric(
                "💧 ET0 acumulada",
                f"{df['ET0_ACUM'].iloc[-1]:.1f} mm"
            )

        with c3:

            st.metric(
                "🌡️ Integral térmica",
                f"{df['GDD10_ACUM'].iloc[-1]:.1f}"
            )

        # ---------------------------------------------------
        # CLIMA
        # ---------------------------------------------------

        st.header("🌦️ Clima")

        fig_clima = go.Figure()

        fig_clima.add_trace(

            go.Scatter(

                x=df[fecha_col],
                y=df[temp_col],

                mode="lines",

                line_shape="spline",

                line=dict(
                    color="#d62728",
                    width=3
                ),

                name="Temperatura"
            )
        )

        fig_clima.add_trace(

            go.Bar(

                x=df[fecha_col],
                y=df[lluvia_col],

                opacity=0.35,

                name="Lluvia"
            )
        )

        fig_clima = estilo_figura(fig_clima)

        st.plotly_chart(
            fig_clima,
            use_container_width=True
        )

        # ---------------------------------------------------
        # BOTRITIS
        # ---------------------------------------------------

        st.subheader("🟠 Botritis")

        fig_bot = go.Figure()

        fig_bot.add_trace(

            go.Scatter(

                x=diario["DIA"],
                y=diario["BOTRITIS"],

                fill="tozeroy",

                mode="lines",

                line_shape="spline",

                line=dict(
                    color="#ff7f0e",
                    width=3
                )
            )
        )

        fig_bot.update_yaxes(range=[0,100])

        fig_bot = estilo_figura(fig_bot)

        st.plotly_chart(
            fig_bot,
            use_container_width=True
        )

        # ---------------------------------------------------
        # MILDIU PRIMARIO
        # ---------------------------------------------------

        st.subheader("🟢 Mildiu primario")

        fig_mp = go.Figure()

        fig_mp.add_trace(

            go.Scatter(

                x=diario["DIA"],
                y=diario["MILDIU_PRIM"],

                fill="tozeroy",

                mode="lines",

                line_shape="spline",

                line=dict(
                    color="#2ca02c",
                    width=3
                )
            )
        )

        fig_mp.update_yaxes(range=[0,100])

        fig_mp = estilo_figura(fig_mp)

        st.plotly_chart(
            fig_mp,
            use_container_width=True
        )

        st.write(
            "Estado:",
            diario["SEVERIDAD_PRIM"].iloc[-1]
        )

        # ---------------------------------------------------
        # MILDIU SECUNDARIO
        # ---------------------------------------------------

        st.subheader("🟢 Mildiu secundario")

        fig_ms = go.Figure()

        fig_ms.add_trace(

            go.Scatter(

                x=diario["DIA"],
                y=diario["MILDIU_SEC"],

                fill="tozeroy",

                mode="lines",

                line_shape="spline",

                line=dict(
                    color="#006400",
                    width=3
                )
            )
        )

        fig_ms.update_yaxes(range=[0,100])

        fig_ms = estilo_figura(fig_ms)

        st.plotly_chart(
            fig_ms,
            use_container_width=True
        )

        st.write(
            "Estado:",
            diario["SEVERIDAD_SEC"].iloc[-1]
        )

        # ---------------------------------------------------
        # OIDIO
        # ---------------------------------------------------

        st.subheader("🔴 Oídio riesgo")

        fig_or = go.Figure()

        fig_or.add_trace(

            go.Scatter(

                x=diario["DIA"],
                y=diario["OIDIO"],

                fill="tozeroy",

                mode="lines",

                line_shape="spline",

                line=dict(
                    color="#d62728",
                    width=4
                )
            )
        )

        fig_or.update_yaxes(range=[0,100])

        fig_or = estilo_figura(fig_or)

        st.plotly_chart(
            fig_or,
            use_container_width=True
        )

        # ---------------------------------------------------
        # BALANCE
        # ---------------------------------------------------

        st.header("💧 Balance hídrico")

        fig_balance = go.Figure()

        fig_balance.add_trace(

            go.Scatter(

                x=df[fecha_col],
                y=df["BALANCE"],

                fill="tozeroy",

                mode="lines",

                line_shape="spline",

                line=dict(
                    color="#2ca02c",
                    width=3
                )
            )
        )

        fig_balance = estilo_figura(fig_balance)

        st.plotly_chart(
            fig_balance,
            use_container_width=True
        )

        # ---------------------------------------------------
        # GDD
        # ---------------------------------------------------

        st.header("🌡️ Integral térmica Base 10")

        fig_gdd = go.Figure()

        fig_gdd.add_trace(

            go.Scatter(

                x=df[fecha_col],
                y=df["GDD10_ACUM"],

                fill="tozeroy",

                mode="lines",

                line_shape="spline",

                line=dict(
                    color="#ff9900",
                    width=3
                )
            )
        )

        fig_gdd = estilo_figura(fig_gdd)

        st.plotly_chart(
            fig_gdd,
            use_container_width=True
        )

    except Exception as e:

        st.error(f"Error leyendo archivo: {e}")

else:

    st.info("Sube un archivo XLS climático")
