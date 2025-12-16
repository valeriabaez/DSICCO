import streamlit as st
import pandas as pd
import os
from datetime import datetime

UPLOADS = "uploads"
MOVILES_FILE = os.path.join(UPLOADS, "MOVILES.xlsx")
TALLER_FILE = os.path.join(UPLOADS, "TALLER_MOVILES.xlsx")

st.set_page_config(page_title="Taller de Móviles", layout="wide")

# -------------------------------------------------
# HEADER
# -------------------------------------------------
st.markdown("""
<div style='text-align:center; background-color:#2c3e50; padding:15px; border-radius:10px;'>
    <h2 style='color:white;'>🛠️ Taller Mecánico – Parque Automotor</h2>
    <p style='color:white;'>Gestión operativa y mantenimiento</p>
</div>
""", unsafe_allow_html=True)

st.divider()

# -------------------------------------------------
# VALIDACIONES
# -------------------------------------------------
if not os.path.exists(MOVILES_FILE):
    st.error("❌ No existe MOVILES.xlsx")
    st.stop()

# -------------------------------------------------
# CARGA MOVILES
# -------------------------------------------------
excel = pd.read_excel(MOVILES_FILE, sheet_name=None)
moviles = pd.DataFrame()

for _, df in excel.items():
    df.columns = df.columns.str.upper().str.strip()
    if {"UNIDAD", "JP"}.issubset(df.columns):
        moviles = pd.concat([moviles, df[["UNIDAD", "JP"]]])

moviles["JP"] = pd.to_numeric(moviles["JP"], errors="coerce").dropna().astype(int).astype(str)
moviles["UNIDAD"] = moviles["UNIDAD"].astype(str).str.upper()

# -------------------------------------------------
# CARGA TALLER
# -------------------------------------------------
if os.path.exists(TALLER_FILE):
    df_taller = pd.read_excel(TALLER_FILE)
else:
    df_taller = pd.DataFrame(columns=[
        "FECHA_INGRESO","FECHA_EGRESO","UNIDAD","MOVIL",
        "TIPO_TRABAJO","DESCRIPCION","TALLER","RESPONSABLE","ESTADO"
    ])

df_taller["FECHA_INGRESO"] = pd.to_datetime(df_taller["FECHA_INGRESO"], errors="coerce")
df_taller["FECHA_EGRESO"] = pd.to_datetime(df_taller["FECHA_EGRESO"], errors="coerce")
df_taller["MOVIL"] = df_taller["MOVIL"].astype(str)
df_taller["UNIDAD"] = df_taller["UNIDAD"].astype(str)

# -------------------------------------------------
# INGRESO MOVIL
# -------------------------------------------------
st.subheader("➕ Ingreso de móvil al taller")

c1, c2 = st.columns(2)
unidad = c1.selectbox("Unidad", sorted(moviles["UNIDAD"].unique()))
movil = c2.selectbox("Móvil (JP)", moviles[moviles["UNIDAD"] == unidad]["JP"])

activo = df_taller[
    (df_taller["UNIDAD"] == unidad) &
    (df_taller["MOVIL"] == movil) &
    (df_taller["ESTADO"] != "FINALIZADO")
]

if not activo.empty:
    st.warning("⚠️ Este móvil ya tiene un trabajo activo.")
else:
    with st.form("ingreso"):
        tipo = st.selectbox("Tipo trabajo", ["MANTENIMIENTO","REPARACIÓN","SINIESTRO","SERVICIO GENERAL"])
        taller = st.selectbox("Taller", [
            "TALLER POLICIAL","SERVICIO OFICIAL","GOMERIA",
            "ELECTRICISTA","CHAPISTA","OTRO"
        ])
        desc = st.text_area("Descripción")
        ok = st.form_submit_button("Ingresar")

        if ok:
            df_taller = pd.concat([df_taller, pd.DataFrame([{
                "FECHA_INGRESO": datetime.now(),
                "FECHA_EGRESO": pd.NaT,
                "UNIDAD": unidad,
                "MOVIL": movil,
                "TIPO_TRABAJO": tipo,
                "DESCRIPCION": desc.upper(),
                "TALLER": taller,
                "RESPONSABLE": "",
                "ESTADO": "INGRESADO"
            }])])
            df_taller.to_excel(TALLER_FILE, index=False)
            st.success("✔ Móvil ingresado")
            st.rerun()

st.divider()

# -------------------------------------------------
# TABLAS EDITABLES (ÚNICO CAMBIO)
# -------------------------------------------------
def tabla_estado(titulo, estado):
    st.subheader(titulo)

    df = df_taller[df_taller["ESTADO"] == estado].copy()

    if df.empty:
        st.info("Sin registros")
        return

    edit = st.data_editor(
        df,
        key=f"editor_{estado}",
        use_container_width=True,
        column_config={
            "ESTADO": st.column_config.SelectboxColumn(
                "Estado",
                options=["INGRESADO","EN REPARACIÓN","FINALIZADO"]
            ),
            "RESPONSABLE": st.column_config.TextColumn("Responsable")
        },
        disabled=[
            "FECHA_INGRESO","FECHA_EGRESO","UNIDAD","MOVIL",
            "TIPO_TRABAJO","DESCRIPCION","TALLER"
        ]
    )

    if st.button(f"Guardar cambios – {titulo}", key=f"btn_{estado}"):
        for _, row in edit.iterrows():

            idx = df_taller.index[
                (df_taller["UNIDAD"] == row["UNIDAD"]) &
                (df_taller["MOVIL"] == row["MOVIL"]) &
                (df_taller["FECHA_INGRESO"] == row["FECHA_INGRESO"])
            ]

            if idx.empty:
                continue

            idx = idx[0]

            if row["ESTADO"] == "FINALIZADO" and pd.isna(df_taller.loc[idx, "FECHA_EGRESO"]):
                df_taller.loc[idx, "FECHA_EGRESO"] = datetime.now()

            df_taller.loc[idx, "ESTADO"] = row["ESTADO"]
            df_taller.loc[idx, "RESPONSABLE"] = row["RESPONSABLE"]

        df_taller.to_excel(TALLER_FILE, index=False)
        st.success("✔ Actualizado")
        st.rerun()

tabla_estado("🔴 Fuera de servicio", "INGRESADO")
tabla_estado("🟡 En reparación", "EN REPARACIÓN")

# -------------------------------------------------
# OPERATIVOS (SOLO LECTURA)
# -------------------------------------------------
st.subheader("🟢 Operativos (finalizados)")
st.dataframe(
    df_taller[df_taller["ESTADO"] == "FINALIZADO"],
    use_container_width=True
)

# -------------------------------------------------
# DASHBOARD Y RANKING
# -------------------------------------------------
st.divider()
st.subheader("📊 Indicadores del Taller")

c1, c2, c3 = st.columns(3)
c1.metric("🔴 Fuera de servicio", (df_taller["ESTADO"]=="INGRESADO").sum())
c2.metric("🟡 En reparación", (df_taller["ESTADO"]=="EN REPARACIÓN").sum())
c3.metric("🟢 Operativos", (df_taller["ESTADO"]=="FINALIZADO").sum())

st.divider()
st.subheader("🏆 Ranking de móviles reincidentes")

ranking = (
    df_taller.groupby(["UNIDAD","MOVIL"])
    .size()
    .reset_index(name="INGRESOS")
    .sort_values("INGRESOS", ascending=False)
)

st.dataframe(ranking, use_container_width=True)
