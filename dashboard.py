import pandas as pd
import glob
import os
import streamlit as st  # Importamos streamlit

# --- 1. Constantes Globales del Proyecto ---
RUTA_DATOS = "datos_excel/"
CALIF_MINIMA = 60
COLUMNAS_FIJAS = ['grupo', 'matricula', 'nombre']
NOMBRE_HOJA = "Hoja1"

# --- 2. Funciones de Procesamiento de Datos ---

@st.cache_data  # ¡Mantenemos la caché de Streamlit!
def cargar_y_procesar_todo():
    """
    Función única que carga, transforma, limpia y analiza todos los datos.
    """
    
    # --- 2.1. Cargar Datos ---
    print("EJECUTANDO: cargar_datos()")
    patron_busqueda = os.path.join(RUTA_DATOS, "*.xlsx")
    archivos_excel = glob.glob(patron_busqueda)
    
    if not archivos_excel:
        st.error(f"No se encontraron archivos .xlsx en la carpeta '{RUTA_DATOS}'.")
        return None, None, None, None

    lista_de_dfs = []
    for archivo in archivos_excel:
        try:
            df = pd.read_excel(archivo, sheet_name=NOMBRE_HOJA, header=0)
            columnas_actuales = df.columns.tolist()
            mapa_renombre = {
                columnas_actuales[0]: 'grupo',
                columnas_actuales[1]: 'matricula',
                columnas_actuales[2]: 'nombre'
            }
            df.rename(columns=mapa_renombre, inplace=True)
            lista_de_dfs.append(df)
        except Exception as e:
            print(f"Error al leer {archivo}: {e}")

    if not lista_de_dfs:
        st.error("No se pudo leer ningún archivo de Excel correctamente.")
        return None, None, None, None

    df_maestro = pd.concat(lista_de_dfs, ignore_index=True)

    # --- 2.2. Transformar Datos ---
    print("EJECUTANDO: transformar_datos()")
    columnas_modulos = [col for col in df_maestro.columns if col not in COLUMNAS_FIJAS]
    if not columnas_modulos:
        st.error("No se encontraron columnas de módulos para analizar.")
        return None, None, None, None
        
    df_largo = df_maestro.melt(
        id_vars=COLUMNAS_FIJAS, 
        value_vars=columnas_modulos, 
        var_name="Modulo",
        value_name="Calificacion"
    )

    # --- 2.3. Limpiar Datos ---
    print("EJECUTANDO: limpiar_datos()")
    df_limpio = df_largo.dropna(subset=['Calificacion']).copy()
    df_limpio['Calificacion'] = pd.to_numeric(df_limpio['Calificacion'], errors='coerce')
    df_limpio = df_limpio.dropna(subset=['Calificacion'])

    if df_limpio.empty:
        st.warning("No se encontraron calificaciones válidas después de la limpieza.")
        return None, None, None, None

    # --- 2.4. Analizar Datos ---
    print("EJECUTANDO: analizar_datos()")
    df_analisis = df_limpio.copy()
    df_analisis['es_reprobado'] = df_analisis['Calificacion'] < CALIF_MINIMA
    
    # Cálculo 1: Por Alumno
    df_reprobados_alumno = df_analisis.groupby(['matricula', 'nombre', 'grupo'])['es_reprobado'].sum().reset_index()
    df_reprobados_alumno = df_reprobados_alumno.rename(columns={'es_reprobado': 'Total_Reprobadas'})
    df_reprobados_alumno = df_reprobados_alumno.sort_values(by='Total_Reprobadas', ascending=False)
    
    # Cálculo 2: Por Grupo
    df_reprobados_grupo = df_analisis.groupby('grupo')['es_reprobado'].sum().reset_index()
    df_reprobados_grupo = df_reprobados_grupo.rename(columns={'es_reprobado': 'Total_Reprobadas'})
    df_reprobados_grupo = df_reprobados_grupo.sort_values(by='Total_Reprobadas', ascending=False)
    
    # Cálculo 3: Por Módulo
    df_reprobados_modulo = df_analisis.groupby('Modulo')['es_reprobado'].sum().reset_index()
    df_reprobados_modulo = df_reprobados_modulo.rename(columns={'es_reprobado': 'Total_Reprobadas'})
    df_reprobados_modulo = df_reprobados_modulo.sort_values(by='Total_Reprobadas', ascending=False)

    # Cálculo 4: Desglose Grupo-Módulo
    df_desglose_grupo_modulo = df_analisis.groupby(['grupo', 'Modulo'])['es_reprobado'].sum().reset_index()
    df_desglose_grupo_modulo = df_desglose_grupo_modulo.rename(columns={'es_reprobado': 'Total_Reprobadas'})
    df_desglose_grupo_modulo = df_desglose_grupo_modulo.sort_values(by=['grupo', 'Total_Reprobadas'], ascending=[True, False])
    df_desglose_grupo_modulo = df_desglose_grupo_modulo[df_desglose_grupo_modulo['Total_Reprobadas'] > 0]
    
    return df_reprobados_alumno, df_reprobados_grupo, df_reprobados_modulo, df_desglose_grupo_modulo

# --- 3. Construcción de la Interfaz de Usuario (UI) ---

# Configuración de la página (para que use todo el ancho)
st.set_page_config(layout="wide")

# Título principal del Dashboard
st.title("📊 Dashboard de Análisis de Reprobación")
st.write("Este dashboard analiza los archivos de Excel en la carpeta `datos_excel/` para identificar grupos y módulos con problemas.")

# Cargar los datos (usará la caché si es posible)
df_al, df_gr, df_mod, df_gr_mod = cargar_y_procesar_todo()

# Si los datos no se cargaron, detener la ejecución de la UI
if df_al is None:
    st.stop()

# --- 3.1. Resumen General ---
st.header("Resumen General")

# Organizar en columnas
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total de Reprobaciones", f"{df_gr['Total_Reprobadas'].sum():,}")
col2.metric("Grupos Analizados", f"{len(df_gr)}")
col3.metric("Alumnos Analizados", f"{len(df_al)}")
col4.metric("Módulo con Más Reprobados", f"{df_mod.iloc[0]['Modulo']}")

# --- MODIFICADO: Gráfico de Módulos (Top 10) movido aquí ---
st.subheader("Top 10 Módulos con Más Reprobados (Global)")
df_mod_chart = df_mod.head(10).set_index('Modulo')
# Usar el gráfico de barras nativo de Streamlit
st.bar_chart(df_mod_chart['Total_Reprobadas'], use_container_width=True)

st.divider()

# --- 3.2. Análisis Interactivo (Filtro y Desglose) ---
st.header("Análisis Interactivo por Grupo")

# Crear 2 columnas: una para filtros y otra para el desglose
col_filtro, col_tabla_desglose = st.columns([1, 2])

with col_filtro:
    # --- MODIFICADO: Filtro Interactivo con grupos ordenados ---
    
    # Obtener lista de grupos únicos y ordenarla
    grupos_sorted = sorted(df_gr['grupo'].unique().tolist())
    lista_grupos = ["Todos"] + grupos_sorted # Añadir "Todos" al inicio
    
    grupo_seleccionado = st.selectbox(
        "Selecciona un grupo para filtrar:",
        options=lista_grupos
    )
    
    st.info("""
    - Selecciona un grupo para ver el detalle.
    - Selecciona 'Todos' para ver el ranking global.
    """)

with col_tabla_desglose:
    # --- MODIFICADO: Tabla de Desglose movida aquí ---
    st.subheader(f"Desglose de Módulos Reprobados para: {grupo_seleccionado}")
    
    if grupo_seleccionado == "Todos":
        # Mostrar el ranking global si 'Todos' está seleccionado
        st.dataframe(df_gr_mod, use_container_width=True, height=400)
    else:
        # Filtrar el DataFrame por el grupo seleccionado
        df_filtrado_desglose = df_gr_mod[df_gr_mod['grupo'] == grupo_seleccionado]
        st.dataframe(df_filtrado_desglose, use_container_width=True, height=400)

st.divider()

# --- 3.3. NUEVO: Top 10 Alumnos del Grupo Seleccionado ---
st.header(f"Top 10 Alumnos con más Reprobadas (Grupo: {grupo_seleccionado})")

if grupo_seleccionado == "Todos":
    # Mostrar Top 10 Global
    st.dataframe(df_al.head(10), use_container_width=True)
else:
    # Filtrar por grupo y luego tomar el Top 10 de ese grupo
    df_filtrado_alumnos = df_al[df_al['grupo'] == grupo_seleccionado]
    st.dataframe(df_filtrado_alumnos.head(10), use_container_width=True)


# --- 4. Expanders para ver datos completos (Sin cambios) ---
st.divider()
st.header("Datos Maestros (Completos)")

with st.expander("Ver Ranking Completo de Grupos"):
    st.dataframe(df_gr, use_container_width=True)

with st.expander("Ver Ranking Completo de Módulos"):
    st.dataframe(df_mod, use_container_width=True)

with st.expander("Ver Ranking Completo de Alumnos"):
    st.dataframe(df_al, use_container_width=True)