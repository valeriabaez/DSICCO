import streamlit as st
import pandas as pd
import os

# -------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# -------------------------------------------------
st.set_page_config(
    page_title="DSICCO – Tablero de Control",
    page_icon="🛡️ DSICCO",
    layout="wide"
)

# -------------------------------------------------
# SIDEBAR – MENÚ LATERAL
# -------------------------------------------------
st.sidebar.title("🛡️ DSICCO")

# Usamos session_state para navegación
if "pagina" not in st.session_state:
    st.session_state["pagina"] = "tablero"

opcion = st.sidebar.radio(
    "Menú",
    [
        "🏠 Tablero Principal",
        "📊 Allanamientos y Armas",
        "🚓 Móviles DSICCO",
        "🛠️ Taller Mecánico",
        "⚙️ Configuración"
    ]
)


# Actualizamos página según selección
if opcion == "🏠 Tablero Principal":
    st.session_state["pagina"] = "tablero"
elif opcion == "📊 Allanamientos y Armas":
    st.session_state["pagina"] = "allanamientos"
elif opcion == "🚓 Móviles DSICCO":
    st.session_state["pagina"] = "moviles"
elif opcion == "🛠️ Taller Mecánico":
    st.session_state["pagina"] = "taller"
elif opcion == "⚙️ Configuración":
    st.session_state["pagina"] = "configuracion"


# -------------------------------------------------
# TABLERO PRINCIPAL
# -------------------------------------------------
if st.session_state["pagina"] == "tablero":
    st.title("🛡️ DSICCO – Tablero de Control")
    st.caption("Dirección de Seguridad Interior Cutral Co")
    st.divider()

    # ----------------- ARCHIVOS EXISTENTES -----------------
    UPLOAD_FOLDER = "uploads"
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    EXCEL_FILE = os.path.join(UPLOAD_FOLDER, "DSICCO.xlsx")
    MOVILES_FILE = os.path.join(UPLOAD_FOLDER, "MOVILES.xlsx")

    if not os.path.exists(EXCEL_FILE):
        st.warning("📁 DSICCO.xlsx no encontrado en 'uploads'.")
    if not os.path.exists(MOVILES_FILE):
        st.warning("📁 MOVILES.xlsx no encontrado en 'uploads'.")

    # ----------------- CARGAR DATOS -----------------
    allan = pd.DataFrame()
    armas = pd.DataFrame()
    flota = pd.DataFrame()
    motos = pd.DataFrame()

    if os.path.exists(EXCEL_FILE):
        try:
            excel_data = pd.read_excel(EXCEL_FILE, sheet_name=None)
            if "ALLANAMIENTOS" in excel_data:
                allan = excel_data["ALLANAMIENTOS"].copy()
                allan.columns = allan.columns.str.upper().str.strip()
            if "ARMAS" in excel_data:
                armas = excel_data["ARMAS"].copy()
                armas.columns = armas.columns.str.upper().str.strip()
        except:
            st.warning("No se pudo leer DSICCO.xlsx")

    if os.path.exists(MOVILES_FILE):
        try:
            excel_m = pd.read_excel(MOVILES_FILE, sheet_name=None)
            for h in excel_m.keys():
                key_upper = h.upper()
                df = excel_m[h].copy()
                df.columns = df.columns.str.upper().str.strip()
                for col in df.columns:
                    df[col] = df[col].astype(str).str.upper().str.strip()
                if "FLOTA" in key_upper:
                    flota = df
                    if "UNIDAD" not in flota.columns:
                        flota["UNIDAD"] = "SIN UNIDAD"
                elif "MOTO" in key_upper:
                    motos = df
                    if "UNIDAD" not in motos.columns:
                        if "DESTINO" in motos.columns:
                            motos["UNIDAD"] = motos["DESTINO"].replace({"": "SIN UNIDAD"}).fillna("SIN UNIDAD")
                        else:
                            motos["UNIDAD"] = "SIN UNIDAD"
        except:
            st.warning("No se pudo leer MOVILES.xlsx")

    # ----------------- CALCULO KPIs -----------------
    if not allan.empty:
        allan["RESULTADO"] = allan["RESULTADO"].astype(str).str.upper()
        allan_positivos = int(allan["RESULTADO"].str.contains("POS").sum())
        allan_negativos = int(allan["RESULTADO"].str.contains("NEG").sum())
    else:
        allan_positivos = 0
        allan_negativos = 0

    if not armas.empty:
        armas_fuego = armas[armas["TIPO"].astype(str).str.upper().str.contains("ARMA|TUMBERA", regex=True, na=False)]
        cartucheria = armas[armas["TIPO"].astype(str).str.upper().str.contains("CARTUCHERIA", regex=True, na=False)]
        armas_secuestradas = int(armas_fuego["CANTIDAD"].sum())
        cartucheria_secuestrada = int(cartucheria["CANTIDAD"].sum())
    else:
        armas_secuestradas = 0
        cartucheria_secuestrada = 0

    # ----------------- MOSTRAR KPIs -----------------
    st.subheader("📊 Resumen Principal")
    c1, c2, c3, c4 = st.columns(4)

    if c1.button(f"✅ Allanamientos Positivos: {allan_positivos}"):
        st.session_state["pagina"] = "allanamientos"
        st.experimental_rerun()

    if c2.button(f"❌ Allanamientos Negativos: {allan_negativos}"):
        st.session_state["pagina"] = "allanamientos"
        st.experimental_rerun()

    if c3.button(f"🔫 Armas Secuestradas: {armas_secuestradas}"):
        st.session_state["pagina"] = "allanamientos"
        st.experimental_rerun()

    if c4.button(f"🧰 Cartuchería Secuestrada: {cartucheria_secuestrada}"):
        st.session_state["pagina"] = "allanamientos"
        st.experimental_rerun()

    st.divider()
    st.subheader("🚓 Estado de Móviles y Motocicletas")

    def resumen_estado(df):
        if "SITUACION ACTUAL" in df.columns:
            df["SITUACION ACTUAL"] = df["SITUACION ACTUAL"].str.upper().str.strip()
            en_servicio = df[df["SITUACION ACTUAL"]=="EN SERVICIO"].shape[0]
            fuera_servicio = df[df["SITUACION ACTUAL"]=="FUERA DE SERVICIO"].shape[0]
            return en_servicio, fuera_servicio
        return 0,0

    moviles_en, moviles_fuera = resumen_estado(flota)
    motos_en, motos_fuera = resumen_estado(motos)

    c1, c2, c3, c4 = st.columns(4)
    if c1.button(f"🚓 Móviles En Servicio: {moviles_en}"):
        st.session_state["pagina"] = "moviles"
        st.experimental_rerun()
    if c2.button(f"🚓 Móviles Fuera de Servicio: {moviles_fuera}"):
        st.session_state["pagina"] = "moviles"
        st.experimental_rerun()
    if c3.button(f"🏍️ Motocicletas En Servicio: {motos_en}"):
        st.session_state["pagina"] = "moviles"
        st.experimental_rerun()
    if c4.button(f"🏍️ Motocicletas Fuera de Servicio: {motos_fuera}"):
        st.session_state["pagina"] = "moviles"
        st.experimental_rerun()

# -------------------------------------------------
# ALLANAMIENTOS Y ARMAS
# -------------------------------------------------
elif st.session_state["pagina"] == "allanamientos":
    st.title("📊 Allanamientos y Armas")
    allan_path = os.path.join(os.getcwd(), "allanas_armas.py")
    if os.path.exists(allan_path):
        with open(allan_path, "r", encoding="utf-8") as f:
            code = f.read()
        exec_namespace = {}
        try:
            exec(code, exec_namespace)
        except Exception as e:
            st.error(f"Error ejecutando allanas_armas.py: {e}")
    else:
        st.error("No se encontró allanas_armas.py en la carpeta de la app.")

# -------------------------------------------------
# MÓVILES DSICCO
# -------------------------------------------------
elif st.session_state["pagina"] == "moviles":
    st.title("🚓 Móviles DSICCO")
    moviles_path = os.path.join(os.getcwd(), "moviles.py")
    if os.path.exists(moviles_path):
        with open(moviles_path, "r", encoding="utf-8") as f:
            code = f.read()
        exec_namespace = {}
        try:
            exec(code, exec_namespace)
        except Exception as e:
            st.error(f"Error ejecutando moviles.py: {e}")
    else:
        st.error("No se encontró moviles.py en la carpeta de la app.")


# -------------------------------------------------
# TALLER MECÁNICO
# -------------------------------------------------
elif st.session_state["pagina"] == "taller":
    st.title("🛠️ Taller Mecánico – Gestión de Móviles")
    taller_path = os.path.join(os.getcwd(), "TALLER_MOVILES.PY")

    if os.path.exists(taller_path):
        with open(taller_path, "r", encoding="utf-8") as f:
            code = f.read()
        exec_namespace = {}
        try:
            exec(code, exec_namespace)
        except Exception as e:
            st.error(f"Error ejecutando taller_moviles.py: {e}")
    else:
        st.warning("No se encontró el archivo taller_moviles.py")

# -------------------------------------------------
# CONFIGURACIÓN
# -------------------------------------------------
elif st.session_state["pagina"] == "configuracion":
    st.title("⚙️ Configuración")
    st.info("Parámetros del sistema (sin subida de archivos).")
