import streamlit as st
import pandas as pd
import os

# ---------------------------------------------------------
# CABECERA (solo visual)
# ---------------------------------------------------------
st.markdown("""
<div style='text-align:center; background-color:#003366; padding:15px; border-radius:10px;'>
    <h1 style='color:white;'>🚓 DSICCO – Móviles 2025</h1>
    <p style='color:white;'>Flota automotriz y motocicletas</p>
</div>
""", unsafe_allow_html=True)

st.divider()

# ---------------------------------------------------------
# CARPETA UPLOADS
# ---------------------------------------------------------
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
SAVED_FILE = os.path.join(UPLOAD_FOLDER, "MOVILES.xlsx")

# ---------------------------------------------------------
# SUBIR ARCHIVO NUEVO
# ---------------------------------------------------------
uploaded = st.file_uploader("📂 Seleccioná archivo Excel de móviles", type=["xlsx"])

if uploaded:
 with open(SAVED_FILE, "wb") as f:
  f.write(uploaded.getvalue())
  st.success("✔ Archivo cargado y reemplazado correctamente.")

# ---------------------------------------------------------
# CARGAR ARCHIVO EXISTENTE
# ---------------------------------------------------------
if not os.path.exists(SAVED_FILE):
    st.warning("📁 Todavía no hay archivo cargado.")
    excel = {}
else:
    try:
        excel = pd.read_excel(SAVED_FILE, sheet_name=None)
    except Exception as e:
        st.error(f"❌ Error al abrir el archivo guardado: {e}")
        excel = {}

if excel:
    # ---------------------------------------------------------
    # DETECTAR HOJAS
    # ---------------------------------------------------------
    hojas = {h.upper().strip(): h for h in excel.keys()}
    flota_key = next((k for k in hojas if "FLOTA" in k), None)
    motos_key = next((k for k in hojas if "MOTO" in k), None)

    if flota_key and motos_key:
        flota = excel[hojas[flota_key]].copy()
        motos = excel[hojas[motos_key]].copy()

        # ---------------------------------------------------------
        # NORMALIZAR COLUMNAS
        # ---------------------------------------------------------
        for df in (flota, motos):
            df.columns = df.columns.str.upper().str.strip()
            for col in df.columns:
                df[col] = df[col].astype(str).str.upper().str.strip()

        # ---------------------------------------------------------
        # AJUSTE COLUMNA UNIDAD
        # ---------------------------------------------------------
        if "UNIDAD" in flota.columns:
            flota["UNIDAD"] = flota["UNIDAD"].replace({"": "SIN UNIDAD"}).fillna("SIN UNIDAD")
        else:
            flota["UNIDAD"] = "SIN UNIDAD"

        if "UNIDAD" in motos.columns:
            motos["UNIDAD"] = motos["UNIDAD"].replace({"": "SIN UNIDAD"}).fillna("SIN UNIDAD")
        elif "DESTINO" in motos.columns:
            motos["UNIDAD"] = motos["DESTINO"].replace({"": "SIN UNIDAD"}).fillna("SIN UNIDAD")
        else:
            motos["UNIDAD"] = "SIN UNIDAD"

        # ---------------------------------------------------------
        # FILTROS
        # ---------------------------------------------------------
        st.subheader("🔍 Filtros")

        def valores_filtro(df, col_name):
            if col_name in df.columns:
                return sorted(df[col_name].dropna().unique())
            return []

        destinos = sorted(set(
            valores_filtro(flota, "DESTINO") + valores_filtro(motos, "DESTINO") +
            valores_filtro(flota, "UNIDAD") + valores_filtro(motos, "UNIDAD")
        ))
        direcciones = sorted(set(valores_filtro(flota, "DIRECCION") + valores_filtro(motos, "DIRECCION")))

        c1, c2 = st.columns(2)
        with c1:
            destino = st.selectbox("DESTINO", ["TODOS"] + destinos)
        with c2:
            direccion = st.selectbox("DIRECCIÓN", ["TODAS"] + direcciones)

        # ---------------------------------------------------------
        # APLICAR FILTROS
        # ---------------------------------------------------------
        def aplicar_filtros(df):
            df_filtered = df.copy()
            if destino != "TODOS":
                if "DESTINO" in df_filtered.columns:
                    df_filtered = df_filtered[df_filtered["DESTINO"] == destino]
                elif "UNIDAD" in df_filtered.columns:
                    df_filtered = df_filtered[df_filtered["UNIDAD"] == destino]
            if direccion != "TODAS" and "DIRECCION" in df_filtered.columns:
                df_filtered = df_filtered[df_filtered["DIRECCION"] == direccion]
            return df_filtered

        flota_filtrada = aplicar_filtros(flota)
        motos_filtrada = aplicar_filtros(motos)

        # ---------------------------------------------------------
        # RESUMEN MOVILES
        # ---------------------------------------------------------
        def resumen_movil(df):
            if "SITUACION ACTUAL" not in df.columns:
                return pd.DataFrame(columns=["UNIDAD","JP","ESTADO"])
            df["SITUACION ACTUAL"] = df["SITUACION ACTUAL"].astype(str).str.upper().str.strip()
            df["ESTADO"] = df["SITUACION ACTUAL"].apply(lambda x: "🟢" if x=="EN SERVICIO" else "🔴" if x=="FUERA DE SERVICIO" else "🟡")
            return df[["UNIDAD","JP","ESTADO"]]

        resumen_flota = resumen_movil(flota_filtrada)
        resumen_motos = resumen_movil(motos_filtrada)

        # ---------------------------------------------------------
        # MOSTRAR TABLAS
        # ---------------------------------------------------------
        st.subheader("🚓 Flota Automotriz")
        if not resumen_flota.empty:
            for unidad in resumen_flota["UNIDAD"].unique():
                df_u = resumen_flota[resumen_flota["UNIDAD"] == unidad]
                with st.expander(f"Unidad: {unidad}"):
                    st.table(df_u[["JP","ESTADO"]])
        else:
            st.info("No hay datos de flota para mostrar")

        st.subheader("🏍️ Motocicletas")
        if not resumen_motos.empty:
            for unidad in resumen_motos["UNIDAD"].unique():
                df_u = resumen_motos[resumen_motos["UNIDAD"] == unidad]
                with st.expander(f"Unidad: {unidad}"):
                    st.table(df_u[["JP","ESTADO"]])
        else:
            st.info("No hay datos de motos para mostrar")
    else:
        st.error("❌ El archivo debe contener hojas de FLOTA y MOTOCICLETAS.")
