# app.py
import streamlit as st
import pandas as pd
import os
from io import BytesIO

# -----------------------------
# CONFIGURACIÓN DE LA PÁGINA
# -----------------------------
st.set_page_config(
    page_title="DSICCO – Resúmenes 2025",
    layout="wide",
    page_icon="🛡️"
)

st.markdown(
    """
    <div style='text-align:center; background-color:#003366; padding:15px; border-radius:10px;'>
        <h1 style='color:white;'>🛡️ DSICCO – Carga y Resúmenes 2025</h1>
        <p style='color:white;'>Subí tu archivo DSICCO.xlsx con las hojas ALLANAMIENTOS y ARMAS</p>
    </div>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# CARPETA DE UPLOADS
# -----------------------------
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

uploaded_file = st.file_uploader(
    "📂 Seleccioná el archivo Excel",
    type=["xlsx"],
    help="Debe contener hojas ALLANAMIENTOS y ARMAS"
)

# -----------------------------
# FUNCIONES AUXILIARES
# -----------------------------
def nombre_mes(num):
    meses = [
        "SIN MES","ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO",
        "JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"
    ]
    try:
        n = int(num)
        return meses[n] if 1 <= n <= 12 else "SIN MES"
    except:
        return "SIN MES"

def build_blocks(df, mes_col, mes_name_col, unidad_col="UNIDAD", interv_col="INTERVENCION", cant_col="CANTIDAD"):
    blocks = []
    total_general = 0
    for mes in sorted(df[mes_col].unique()):
        df_mes = df[df[mes_col]==mes]
        if df_mes.empty:
            continue
        mes_label = df_mes[mes_name_col].iloc[0] if mes_name_col in df_mes.columns else nombre_mes(mes)
        blocks.append([mes_label,"","", ""])
        for _, r in df_mes.iterrows():
            blocks.append([
                "",
                r.get(unidad_col,""),
                r.get(interv_col,"ALLANAMIENTO") if interv_col in df_mes.columns else "ALLANAMIENTO",
                int(r.get(cant_col,0))
            ])
        subtotal = int(df_mes[cant_col].sum())
        blocks.append(["Subtotal","", "", subtotal])
        total_general += subtotal
    blocks.append(["TOTAL GENERAL","","", total_general])
    return blocks

def export_excel(blocks_allan, blocks_armas):
    output = BytesIO()
    df_allan = pd.DataFrame(blocks_allan, columns=["Mes","Unidad","Intervención","Cantidad"])
    df_armas = pd.DataFrame(blocks_armas, columns=["Mes","Unidad","Intervención","Cantidad"])
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_allan.to_excel(writer, sheet_name="ALLANAMIENTOS", index=False)
        df_armas.to_excel(writer, sheet_name="ARMAS", index=False)
    return output.getvalue()

# =============================================================
# PROCESAMIENTO DEL EXCEL
# =============================================================
if uploaded_file is not None:
    try:
        excel = pd.read_excel(uploaded_file, sheet_name=None)

        if "ALLANAMIENTOS" not in excel or "ARMAS" not in excel:
            st.error("❌ El archivo debe contener las hojas ALLANAMIENTOS y ARMAS.")
            st.stop()

        # --- HOJAS ---
        allan = excel["ALLANAMIENTOS"].copy()
        allan.columns = allan.columns.str.upper().str.strip()

        armas = excel["ARMAS"].copy()
        armas.columns = armas.columns.str.upper().str.strip()

        st.success("✔ Archivo cargado correctamente.")

        # --- Guardar localmente ---
        save_path = os.path.join(UPLOAD_FOLDER, "DSICCO.xlsx")
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        st.info(f"📂 Archivo guardado en: {save_path}")

        # -----------------------------
        # ALLANAMIENTOS
        # -----------------------------
        st.markdown("## 🔵 ALLANAMIENTOS")
        allan["FECHA"] = pd.to_datetime(allan["FECHA"], errors="coerce")
        allan["MES"] = allan["FECHA"].dt.month.fillna(0).astype(int)
        allan["MES_NOMBRE"] = allan["MES"].apply(nombre_mes)
        allan["POSITIVO_FLAG"] = allan["RESULTADO"].astype(str).str.upper().str.contains("POS", na=False)
        allan["NEGATIVO_FLAG"] = allan["RESULTADO"].astype(str).str.upper().str.contains("NEG", na=False)
        allan["CANTIDAD"] = 1

        resumen_allan = (
            allan.groupby(["MES","MES_NOMBRE","UNIDAD"], as_index=False)
            .agg({"POSITIVO_FLAG":"sum","NEGATIVO_FLAG":"sum","CANTIDAD":"sum"})
        )

        blocks_allan = build_blocks(resumen_allan, "MES", "MES_NOMBRE", unidad_col="UNIDAD", interv_col=None, cant_col="CANTIDAD")

        # Mostrar en columnas profesionales
        for mes in sorted(resumen_allan["MES"].unique()):
            df_mes = resumen_allan[resumen_allan["MES"]==mes]
            with st.expander(f"📅 {df_mes['MES_NOMBRE'].iloc[0]}"):
                st.table(df_mes.rename(columns={
                    "UNIDAD":"Unidad",
                    "POSITIVO_FLAG":"Positivos",
                    "NEGATIVO_FLAG":"Negativos",
                    "CANTIDAD":"Total"
                }))
                st.markdown(f"**Subtotal:** {df_mes['CANTIDAD'].sum()}")

        st.markdown("---")
        st.metric("Total Positivos", resumen_allan['POSITIVO_FLAG'].sum())
        st.metric("Total Negativos", resumen_allan['NEGATIVO_FLAG'].sum())
        st.metric("TOTAL Allanamientos", resumen_allan['CANTIDAD'].sum())

        # -----------------------------
        # ARMAS
        # -----------------------------
        st.markdown("## 🔴 ARMAS (Solo fuego/tumberas)")
        armas["FECHA"] = pd.to_datetime(armas["FECHA"], errors="coerce")
        armas["MES"] = armas["FECHA"].dt.month.fillna(0).astype(int)
        armas["MES_NOMBRE"] = armas["MES"].apply(nombre_mes)
        armas_validas = armas[armas["TIPO"].astype(str).str.upper().str.contains("ARMA DE FUEGO|ARMA\\b|TUMBERA", regex=True, na=False)].copy()
        armas_validas["CANTIDAD"] = pd.to_numeric(armas_validas["CANTIDAD"], errors="coerce").fillna(1).astype(int)

        resumen_armas = (
            armas_validas.groupby(["MES","MES_NOMBRE","UNIDAD","INTERVENCION"], as_index=False)
            .agg({"CANTIDAD":"sum"})
        )

        blocks_armas = build_blocks(resumen_armas, "MES", "MES_NOMBRE", unidad_col="UNIDAD", interv_col="INTERVENCION", cant_col="CANTIDAD")

        # Mostrar por mes
        for mes in sorted(resumen_armas["MES"].unique()):
            df_mes = resumen_armas[resumen_armas["MES"]==mes]
            with st.expander(f"📅 {df_mes['MES_NOMBRE'].iloc[0]}"):
                st.table(df_mes.rename(columns={
                    "UNIDAD":"Unidad",
                    "INTERVENCION":"Intervención",
                    "CANTIDAD":"Cantidad"
                }))
                st.markdown(f"**Subtotal:** {df_mes['CANTIDAD'].sum()}")

        st.markdown("---")
        st.metric("Total armas (solo fuego/tumberas)", resumen_armas['CANTIDAD'].sum())

        # -----------------------------
        # RESUMEN ARMAS POR MES Y PROCEDIMIENTO
        # -----------------------------
        st.markdown("## 📊 Resumen rápido de ARMAS")
        col1, col2 = st.columns(2)

        with col1:
            total_armas_mes = resumen_armas.groupby("MES_NOMBRE")["CANTIDAD"].sum().reset_index().rename(columns={"CANTIDAD":"Cantidad Total"})
            st.markdown("**Cantidad total de armas por mes:**")
            st.table(total_armas_mes)

        with col2:
            total_armas_proc = resumen_armas.groupby("INTERVENCION")["CANTIDAD"].sum().reset_index().rename(columns={"CANTIDAD":"Cantidad Total"})
            st.markdown("**Cantidad total de armas por procedimiento/intervención:**")
            st.table(total_armas_proc)

        # -----------------------------
        # DESCARGA EXCEL
        # -----------------------------
        excel_bytes = export_excel(blocks_allan, blocks_armas)
        st.download_button(
            label="📥 Descargar Resúmenes en EXCEL",
            data=excel_bytes,
            file_name="Resumenes_DSICCO.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"❌ Error al procesar archivo: {e}")
