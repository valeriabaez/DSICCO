
import streamlit as st
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Eliminado: conexión MySQL. No se usará base de datos.
engine = None  # Compatibilidad

# Utilities
MES_MAP = {
    1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL", 5: "MAYO", 6: "JUNIO",
    7: "JULIO", 8: "AGOSTO", 9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE"
}


def nombre_mes(n):
    try:
        return MES_MAP.get(int(n), 'SIN FECHA')
    except Exception:
        return 'SIN FECHA'


def basic_clean(df):
    # Strip whitespace for object columns, uppercase strings, convert dates if possible
    for c in df.select_dtypes(include=['object']).columns:
        df[c] = df[c].astype(str).str.strip()
        # preserve NA values
        df.loc[df[c].isin(['nan', 'None', 'NoneType']), c] = np.nan
        try:
            df[c] = df[c].str.upper()
        except Exception:
            pass

    # Try to parse any column with 'fecha' in its name
    for c in df.columns:
        if 'fecha' in c.lower() or 'fecha' in c:
            try:
                df[c] = pd.to_datetime(df[c], dayfirst=True, errors='coerce')
            except Exception:
                pass

    # Add month number if not present
    if 'MesNum' not in df.columns:
        # guess: look for any date column
        date_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
        if len(date_cols) > 0:
            df['MesNum'] = df[date_cols[0]].dt.month
        else:
            df['MesNum'] = np.nan
    return df


# Create or ensure tables exist (simple CREATE TABLE if not exists)
# (Bloque de BD eliminado)

def df_to_sql_json_rows_placeholder():
    return 0

# Continuación del código(df, table_name, engine, mescol='MesNum'):
    # Insert each row as JSON in 'fila_original' and set MesNum separately
    records = []
    for _, row in df.iterrows():
        # Convert row to dict but coerce NaN to None
        d = {k: (None if (pd.isna(v)) else (v if not isinstance(v, (pd.Timestamp, pd.DatetimeTZDtype)) else v.isoformat())) for k, v in row.items()}
        mes = d.get(mescol)
        records.append({'fila_original': pd.io.json.dumps(d, default=str), 'MesNum': int(mes) if mes not in (None, '', np.nan) else None})

    # Bulk insert using VALUES
    if len(records) == 0:
        return 0

    with engine.begin() as conn:
        # Prepare insert statement
        insert_sql = text(f"INSERT INTO {table_name} (fila_original, MesNum) VALUES (:fila_original, :MesNum)")
        conn.execute(insert_sql, records)
    return len(records)


# UI - File upload
uploaded_file = st.file_uploader("Subí la planilla Excel (.xlsx) con las hojas Allanamientos y/o Armas", type=['xlsx', 'xls'])

if uploaded_file is not None:
    st.sidebar.header('Opciones')
    sheet_s = st.sidebar.text_input('Nombre de la hoja de Allanamientos (dejar en blanco para autodetectar)', value='Allanamientos')
    sheet_a = st.sidebar.text_input('Nombre de la hoja de Armas (dejar en blanco para autodetectar)', value='Armas')
    skip_clean = st.sidebar.checkbox('Skip cleaning (ya subí limpio)', value=False)
    preview_rows = st.sidebar.number_input('Filas a previsualizar', min_value=5, max_value=1000, value=20)

    # Read file
    try:
        xls = pd.ExcelFile(uploaded_file)
    except Exception as e:
        st.error(f"Error al leer Excel: {e}")
        st.stop()

    st.markdown("### Hojas detectadas")
    st.write(xls.sheet_names)

    # Choose sheets
    selected_allan = sheet_s if (sheet_s in xls.sheet_names) else (xls.sheet_names[0] if len(xls.sheet_names)>0 else None)
    selected_armas = sheet_a if (sheet_a in xls.sheet_names) else (xls.sheet_names[1] if len(xls.sheet_names)>1 else None)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader('Allanamientos')
        allan_df = None
        if selected_allan:
            try:
                allan_df = pd.read_excel(xls, sheet_name=selected_allan, engine='openpyxl')
                st.write(f'Leyendo hoja: {selected_allan} — filas: {len(allan_df)}')
            except Exception as e:
                st.warning(f'No se pudo leer hoja {selected_allan}: {e}')
        else:
            st.info('No se detectó hoja para Allanamientos')

        if allan_df is not None:
            st.markdown('Vista previa — Allanamientos')
            st.dataframe(allan_df.head(preview_rows))

    with col2:
        st.subheader('Armas')
        armas_df = None
        if selected_armas:
            try:
                armas_df = pd.read_excel(xls, sheet_name=selected_armas, engine='openpyxl')
                st.write(f'Leyendo hoja: {selected_armas} — filas: {len(armas_df)}')
            except Exception as e:
                st.warning(f'No se pudo leer hoja {selected_armas}: {e}')
        else:
            st.info('No se detectó hoja para Armas')

        if armas_df is not None:
            st.markdown('Vista previa — Armas')
            st.dataframe(armas_df.head(preview_rows))

    # Cleaning step
    if not skip_clean:
        if allan_df is not None:
            st.info('Aplicando limpieza básica a Allanamientos...')
            allan_df = basic_clean(allan_df)
        if armas_df is not None:
            st.info('Aplicando limpieza básica a Armas...')
            armas_df = basic_clean(armas_df)
    else:
        st.info('Omitiendo limpieza, se usarán los datos tal cual subidos')

    # Show transformed columns and allow rename mapping if needed
    st.markdown('### Columnas detectadas y mapeo sugerido')
    def show_mapping(df, title):
        if df is None: return None
        st.write(f'Columnas — {title}:', list(df.columns))
        # Allow user to pick which column is month / date if any
        date_choice = st.selectbox(f"Columna fecha para {title} (opcional)", options=[None]+list(df.columns), key=f'date_{title}')
        mes_choice = st.selectbox(f"Columna MesNum para {title} (opcional)", options=[None]+list(df.columns), key=f'mes_{title}')
        return date_choice, mes_choice

    d_allan, m_allan = show_mapping(allan_df, 'Allanamientos')
    d_armas, m_armas = show_mapping(armas_df, 'Armas')

    # If user selected date columns, parse them and set MesNum
    if allan_df is not None and d_allan:
        try:
            allan_df[d_allan] = pd.to_datetime(allan_df[d_allan], dayfirst=True, errors='coerce')
            allan_df['MesNum'] = allan_df[d_allan].dt.month
        except Exception:
            pass
    elif allan_df is not None and m_allan:
        try:
            allan_df['MesNum'] = pd.to_numeric(allan_df[m_allan], errors='coerce')
        except Exception:
            pass

    if armas_df is not None and d_armas:
        try:
            armas_df[d_armas] = pd.to_datetime(armas_df[d_armas], dayfirst=True, errors='coerce')
            armas_df['MesNum'] = armas_df[d_armas].dt.month
        except Exception:
            pass
    elif armas_df is not None and m_armas:
        try:
            armas_df['MesNum'] = pd.to_numeric(armas_df[m_armas], errors='coerce')
        except Exception:
            pass

    st.markdown('---')
    # Show quick reports that mimic the PHP behavior
    st.header('Resúmenes y tablas (similares al PHP)')

    # Ensure tables exist
    try:
        ensure_tables(engine)
    except Exception as e:
        st.warning(f'No se pudo asegurar tablas en la DB: {e}')

    if allan_df is not None:
        st.subheader('Resumen Allanamientos por Mes')
        if 'MesNum' in allan_df.columns:
            res = allan_df.groupby('MesNum').size().reset_index(name='cantidad')
            res['Mes'] = res['MesNum'].apply(lambda x: nombre_mes(x))
            res = res.sort_values('MesNum')
            st.dataframe(res)
        else:
            st.info('No hay columna MesNum en Allanamientos')

        # Totales por unidad y resultado (si existen las columnas)
        unidad_cols = [c for c in allan_df.columns if 'unidad' in c.lower() or 'unidad' in c]
        resultado_cols = [c for c in allan_df.columns if 'resultado' in c.lower() or 'resultado' in c]
        if len(unidad_cols) > 0:
            col = unidad_cols[0]
            st.write(f'Totales por {col}')
            st.dataframe(allan_df.groupby(col).size().reset_index(name='cantidad').sort_values('cantidad', ascending=False))
        if len(resultado_cols) > 0:
            col = resultado_cols[0]
            st.write(f'Totales por {col}')
            st.dataframe(allan_df.groupby(col).size().reset_index(name='cantidad').sort_values('cantidad', ascending=False))

    if armas_df is not None:
        st.subheader('Resumen Armas por Mes / Unidad / Procedimiento')
        if 'MesNum' in armas_df.columns:
            res = armas_df.groupby('MesNum').size().reset_index(name='cantidad')
            res['Mes'] = res['MesNum'].apply(lambda x: nombre_mes(x))
            res = res.sort_values('MesNum')
            st.dataframe(res)
        unidad_cols = [c for c in armas_df.columns if 'unidad' in c.lower() or 'unidad' in c]
        procedimiento_cols = [c for c in armas_df.columns if 'procedimiento' in c.lower() or 'procedimiento' in c or 'tipo' in c.lower()]
        if len(unidad_cols) > 0:
            col = unidad_cols[0]
            st.write(f'Totales por {col}')
            st.dataframe(armas_df.groupby(col).size().reset_index(name='cantidad').sort_values('cantidad', ascending=False))
        if len(procedimiento_cols) > 0:
            col = procedimiento_cols[0]
            st.write(f'Totales por {col}')
            st.dataframe(armas_df.groupby(col).size().reset_index(name='cantidad').sort_values('cantidad', ascending=False))

    # Allow user to insert into DB
    st.markdown('---')
    st.header('# ---
    st.header('Guardar resultados en un Excel siempre accesible y reportes')
    st.info('El sistema guarda un Excel consolidado y puede generar un Excel solo con resúmenes, un PDF de resúmenes, mantener un histórico por fecha y mostrar una gráfica mensual.')

    import io
    from datetime import datetime
    import os
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_pdf import PdfPages

    HIST_DIR = '/mnt/data/historico_imports'
    os.makedirs(HIST_DIR, exist_ok=True)

    def compute_resumenes(allan_df, armas_df):
        res = {}
        if allan_df is not None:
            if 'MesNum' in allan_df.columns:
                r = allan_df.groupby('MesNum').size().reset_index(name='cantidad')
                r['Mes'] = r['MesNum'].apply(lambda x: nombre_mes(x))
                r = r.sort_values('MesNum')
                res['allan_por_mes'] = r
            # Totales por unidad y resultado
            unidad_cols = [c for c in allan_df.columns if 'unidad' in c.lower() or 'unidad' in c]
            resultado_cols = [c for c in allan_df.columns if 'resultado' in c.lower() or 'resultado' in c]
            if len(unidad_cols) > 0:
                res['allan_por_unidad'] = allan_df.groupby(unidad_cols[0]).size().reset_index(name='cantidad').sort_values('cantidad', ascending=False)
            if len(resultado_cols) > 0:
                res['allan_por_resultado'] = allan_df.groupby(resultado_cols[0]).size().reset_index(name='cantidad').sort_values('cantidad', ascending=False)
        if armas_df is not None:
            if 'MesNum' in armas_df.columns:
                r = armas_df.groupby('MesNum').size().reset_index(name='cantidad')
                r['Mes'] = r['MesNum'].apply(lambda x: nombre_mes(x))
                r = r.sort_values('MesNum')
                res['armas_por_mes'] = r
            unidad_cols = [c for c in armas_df.columns if 'unidad' in c.lower() or 'unidad' in c]
            procedimiento_cols = [c for c in armas_df.columns if 'procedimiento' in c.lower() or 'procedimiento' in c or 'tipo' in c.lower()]
            if len(unidad_cols) > 0:
                res['armas_por_unidad'] = armas_df.groupby(unidad_cols[0]).size().reset_index(name='cantidad').sort_values('cantidad', ascending=False)
            if len(procedimiento_cols) > 0:
                res['armas_por_procedimiento'] = armas_df.groupby(procedimiento_cols[0]).size().reset_index(name='cantidad').sort_values('cantidad', ascending=False)
        return res

    def save_consolidado_excel(allan_df, armas_df, path):
        with pd.ExcelWriter(path, engine='openpyxl') as writer:
            if allan_df is not None:
                allan_df.to_excel(writer, sheet_name='Allanamientos', index=False)
            if armas_df is not None:
                armas_df.to_excel(writer, sheet_name='Armas', index=False)

    def save_resumen_excel(resumen_dict, path):
        with pd.ExcelWriter(path, engine='openpyxl') as writer:
            for name, df in resumen_dict.items():
                # Excel sheet names must be <=31 chars
                sheet = name[:31]
                df.to_excel(writer, sheet_name=sheet, index=False)

    def save_resumen_pdf(resumen_dict, path):
        # Create a simple PDF with each resumen as a table (matplotlib)
        with PdfPages(path) as pdf:
            for name, df in resumen_dict.items():
                fig = Figure(figsize=(8.27, 11.69))  # A4
                ax = fig.subplots()
                ax.axis('off')
                ax.set_title(name.replace('_', ' ').upper(), fontsize=12)
                # render table
                table = ax.table(cellText=df.values, colLabels=df.columns, loc='center', cellLoc='center')
                table.auto_set_font_size(False)
                table.set_fontsize(8)
                table.scale(1, 1.2)
                pdf.savefig(fig)
                fig.clf()

    # Botones y opciones
    colx1, colx2, colx3 = st.columns(3)
    resumenes = compute_resumenes(allan_df, armas_df)

    with colx1:
        if st.button('Generar Excel consolidado (Allanamientos + Armas)'):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            path = f'/mnt/data/Resultados_Allanamientos_Armas.xlsx'
            save_consolidado_excel(allan_df, armas_df, path)
            # Save historic copy
            histpath = os.path.join(HIST_DIR, f'Resultados_{timestamp}.xlsx')
            save_consolidado_excel(allan_df, armas_df, histpath)
            st.success('Consolidado guardado y copia histórica creada.')
            st.download_button('Descargar consolidado', open(path,'rb').read(), file_name=os.path.basename(path))

    with colx2:
        if st.button('Generar Excel SOLO resúmenes'):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            path = f'/mnt/data/Resumenes_Allanamientos_Armas.xlsx'
            save_resumen_excel(resumenes, path)
            histpath = os.path.join(HIST_DIR, f'Resumenes_{timestamp}.xlsx')
            save_resumen_excel(resumenes, histpath)
            st.success('Excel de resúmenes creado y guardado en histórico.')
            st.download_button('Descargar resumenes (.xlsx)', open(path,'rb').read(), file_name=os.path.basename(path))

    with colx3:
        if st.button('Generar PDF de resúmenes'):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            path = f'/mnt/data/Resumenes_Allanamientos_Armas.pdf'
            save_resumen_pdf(resumenes, path)
            histpath = os.path.join(HIST_DIR, f'Resumenes_{timestamp}.pdf')
            # copy pdf to historico
            import shutil
            shutil.copy(path, histpath)
            st.success('PDF de resúmenes generado y copiado al histórico.')
            st.download_button('Descargar PDF de resúmenes', open(path,'rb').read(), file_name=os.path.basename(path))

    st.markdown('---')
    # Gráfica mensual
    st.header('Gráfica mensual (Allanamientos / Armas)')
    fig = None
    if 'allan_por_mes' in resumenes:
        dfm = resumenes['allan_por_mes']
        fig = Figure(figsize=(8,3))
        ax = fig.subplots()
        ax.plot(dfm['MesNum'], dfm['cantidad'], marker='o')
        ax.set_xticks(dfm['MesNum'])
        ax.set_xticklabels(dfm['Mes'])
        ax.set_title('Allanamientos por mes')
        ax.set_xlabel('Mes')
        ax.set_ylabel('Cantidad')
        st.pyplot(fig)
    if 'armas_por_mes' in resumenes:
        dfm = resumenes['armas_por_mes']
        fig2 = Figure(figsize=(8,3))
        ax2 = fig2.subplots()
        ax2.plot(dfm['MesNum'], dfm['cantidad'], marker='o')
        ax2.set_xticks(dfm['MesNum'])
        ax2.set_xticklabels(dfm['Mes'])
        ax2.set_title('Armas por mes')
        ax2.set_xlabel('Mes')
        ax2.set_ylabel('Cantidad')
        st.pyplot(fig2)

    st.markdown('---')
    st.write('Nota: los archivos se guardan en /mnt/data y en la carpeta /mnt/data/historico_imports con marca de fecha. Si querés otra ruta, decímela y la cambio.')

    st.markdown('---')
    st.write('Nota: este importador guarda cada fila como JSON en la DB dentro de la columna `fila_original` y guarda `MesNum` por separado. Si querés un mapeo columna-a-columna tradicional (con columnas SQL individuales), puedo adaptar el script para crear columnas SQL específicas y mapear tipos. Decime si preferís eso.')

else:
    st.info('Subí el archivo Excel para comenzar. Si ya lo subís limpio, podés marcar "Skip cleaning" en la barra lateral.')
