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
st.markdown("### Dashboard epidemiológico")

# ---------------------------------------------------
# SUBIR ARCHIVO
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
        # LEER ARCHIVO
        # ---------------------------------------------------

        df = pd.read_excel(
            uploaded_file,
            engine="xlrd"
        )

        st.success("Archivo cargado")

        # ---------------------------------------------------
        # COLUMNAS
        # ---------------------------------------------------

        fecha_col = df.columns[0]

        temp_col = "Temp. Aire"
        hr_col = "Humedad"
        lluvia_col = "Precip."

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
            lluvia_col
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
            np.sqrt(df[temp_col].clip(lower=0))
        )

        df["ET0_ACUM"] = (
            df["ET0"].cumsum()
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
        # LLUVIA
        # ---------------------------------------------------

        df["LLUVIA_ACUM"] = (
            df[lluvia_col].cumsum()
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
        # OIDIO
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

            # SEVERIDAD

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
        # KPIS
        # ---------------------------------------------------

        st.header("📊 Resumen")

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric(
                "☔ Lluvia",
                f"{df['LLUVIA_ACUM'].iloc[-1]:.1f} mm"
            )

        with c2:
            st.metric(
                "💧 ET0",
                f"{df['ET0_ACUM'].iloc[-1]:.1f} mm"
            )

        with c3:
            st.metric(
                "🌡️ GDD",
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

        # ---------------------------------------------------
        # SEVERIDAD VISUAL
        # ---------------------------------------------------

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
        # BALANCE
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

    except Exception as e:

        st.error(f"Error: {e}")

else:

    st.info("Sube un archivo XLS")
             

             

        
        
               

       


       
       
            
