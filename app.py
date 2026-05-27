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
        margin=dict(l=20, r=20, t=40, b=20),
        hovermode="x unified",
        paper_bgcolor="white",
        plot_bgcolor="white"
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
st.markdown("### Dashboard epidemiológico calibrado")

# ---------------------------------------------------
# UPLOAD
# ---------------------------------------------------

uploaded_file = st.file_uploader(
    "Sube archivo XLS",
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

        temp_col = "Temperatura media"
        tmax_col = "Temperatura maxima"
        tmin_col = "Temperatura minima"

        hr_col = "Humedad media"
        lluvia_col = "Precipitacion total"
        viento_col = "Viento"

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
            tmax_col,
            tmin_col,
            hr_col,
            lluvia_col,
            viento_col
        ]:

            df[c] = (
                df[c]
                .astype(str)
                .str.replace(",", ".")
            )

            df[c] = pd.to_numeric(
                df[c],
                errors="coerce"
            )

        # ---------------------------------------------------
        # ET0 HARGREAVES
        # ---------------------------------------------------

        ra = 20

        df["ET0"] = (

            0.0023 *
            (df[temp_col] + 17.8) *
            np.sqrt(df[tmax_col] - df[tmin_col]) *
            ra

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
        # GDD
        # ---------------------------------------------------

        df["GDD10"] = (
            (df[temp_col] - 10)
            .clip(lower=0)
        )

        df["GDD10_ACUM"] = (
            df["GDD10"].cumsum()
        )

        # ---------------------------------------------------
        # BALANCE
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

        diario = pd.DataFrame()

        diario["DIA"] = df[fecha_col]

        diario["TEMP_MEDIA"] = df[temp_col]
        diario["TEMP_MAX"] = df[tmax_col]
        diario["TEMP_MIN"] = df[tmin_col]

        diario["HR_MEDIA"] = df[hr_col]
        diario["LLUVIA"] = df[lluvia_col]

        # ---------------------------------------------------
        # OIDIO CALIBRADO
        # ---------------------------------------------------

        indice = 0
        dias_favorables = 0

        oidio = []

        for i in range(len(diario)):

            t = diario["TEMP_MEDIA"].iloc[i]
            tmax = diario["TEMP_MAX"].iloc[i]
            lluvia = diario["LLUVIA"].iloc[i]

            favorable = (
                21 <= t <= 30
            )

            if favorable:

                dias_favorables += 1

                if dias_favorables >= 2:

                    indice += 20

            else:

                dias_favorables = 0

            # CALOR EXTREMO

            if tmax > 35:

                indice -= 10

            # LLUVIA FUERTE

            if lluvia > 15:

                indice -= 10

            indice = max(0, min(100, indice))

            oidio.append(indice)

        diario["OIDIO"] = oidio

        # ---------------------------------------------------
        # BOTRITIS
        # ---------------------------------------------------

        diario["BOTRITIS"] = np.where(

            (
                (diario["HR_MEDIA"] > 85) &
                (diario["TEMP_MEDIA"] > 12)
            ),

            40,

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

            disparo = (

                lluvia >= 2 and
                hr >= 80 and
                10 <= temp <= 26

            )

            incubacion = (

                hr >= 75 and
                11 <= temp <= 27

            )

            # NUEVO EVENTO

            if disparo and not evento:

                evento = True
                desarrollo = 25

            # DESARROLLO

            elif evento:

                if incubacion:

                    if lluvia > 0:

                        desarrollo += 20

                    else:

                        desarrollo += 12

                else:

                    desarrollo -= 8

            desarrollo = max(
                0,
                min(100, desarrollo)
            )

            # RESET

            if desarrollo >= 100:

                desarrollo = 0
                evento = False

            mildiu_prim.append(desarrollo)

            # SEVERIDAD

            if desarrollo == 0:

                severidad = "Sin infección"
                color = "#2ecc71"

            elif desarrollo < 35:

                severidad = "Leve"
                color = "#ffe08a"

            elif desarrollo < 70:

                severidad = "Media"
                color = "#ff9f43"

            else:

                severidad = "Severa"
                color = "#ee5253"

            severidad_prim.append(severidad)

        diario["MILDIU_PRIM"] = mildiu_prim
        diario["SEVERIDAD_PRIM"] = severidad_prim

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

        fig = go.Figure()

        fig.add_trace(

            go.Scatter(

                x=df[fecha_col],
                y=df[temp_col],

                mode="lines",

                line_shape="spline",

                line=dict(
                    color="red",
                    width=3
                ),

                name="Temperatura"
            )
        )

        fig.add_trace(

            go.Bar(

                x=df[fecha_col],
                y=df[lluvia_col],

                opacity=0.35,

                name="Lluvia"
            )
        )

        fig = estilo_figura(fig)

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        # ---------------------------------------------------
        # MILDIU
        # ---------------------------------------------------

        st.header("🟢 Mildiu primario")

        fig = go.Figure()

        fig.add_trace(

            go.Scatter(

                x=diario["DIA"],
                y=diario["MILDIU_PRIM"],

                fill="tozeroy",

                mode="lines",

                line_shape="spline",

                line=dict(
                    color="green",
                    width=4
                )
            )
        )

        fig.update_yaxes(range=[0,100])

        fig = estilo_figura(fig)

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        # SEVERIDAD

        estado = diario["SEVERIDAD_PRIM"].iloc[-1]
        valor = diario["MILDIU_PRIM"].iloc[-1]

        if estado == "Leve":
            color = "#ffe08a"

        elif estado == "Media":
            color = "#ff9f43"

        elif estado == "Severa":
            color = "#ee5253"

        else:
            color = "#2ecc71"

        st.markdown(f"""

        <div style="
        padding:15px;
        border-radius:12px;
        background:{color};
        color:white;
        font-size:22px;
        font-weight:bold;
        text-align:center;
        margin-bottom:20px;
        ">

        Infección {estado} — Desarrollo {valor:.0f}%

        </div>

        """, unsafe_allow_html=True)

        # ---------------------------------------------------
        # OIDIO
        # ---------------------------------------------------

        st.header("🔴 Oídio")

        fig = go.Figure()

        fig.add_trace(

            go.Scatter(

                x=diario["DIA"],
                y=diario["OIDIO"],

                fill="tozeroy",

                mode="lines",

                line_shape="spline",

                line=dict(
                    color="red",
                    width=4
                )
            )
        )

        fig.update_yaxes(range=[0,100])

        fig = estilo_figura(fig)

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        # ---------------------------------------------------
        # BOTRITIS
        # ---------------------------------------------------

        st.header("🟠 Botritis")

        fig = go.Figure()

        fig.add_trace(

            go.Scatter(

                x=diario["DIA"],
                y=diario["BOTRITIS"],

                fill="tozeroy",

                mode="lines",

                line_shape="spline",

                line=dict(
                    color="orange",
                    width=4
                )
            )
        )

        fig.update_yaxes(range=[0,100])

        fig = estilo_figura(fig)

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        # ---------------------------------------------------
        # BALANCE HIDRICO
        # ---------------------------------------------------

        st.header("💧 Balance hídrico")

        fig = go.Figure()

        fig.add_trace(

            go.Scatter(

                x=df[fecha_col],
                y=df["BALANCE"],

                fill="tozeroy",

                mode="lines",

                line_shape="spline",

                line=dict(
                    color="green",
                    width=3
                )
            )
        )

        fig = estilo_figura(fig)

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        # ---------------------------------------------------
        # GDD
        # ---------------------------------------------------

        st.header("🌡️ Integral térmica Base 10")

        fig = go.Figure()

        fig.add_trace(

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

        fig = estilo_figura(fig)

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    except Exception as e:

        st.error(f"Error: {e}")

else:

    st.info("Sube un archivo XLS")
