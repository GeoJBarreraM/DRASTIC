import streamlit as st
import numpy as np
import rasterio
import os
from io import BytesIO
import pandas as pd 

# --- 1. CONFIGURACIÓN DE ESCENARIOS Y RANGOS CALIBRADOS ---

# Pesos Estándar (Intrínsecos) para referencia
PESOS_ESTANDAR = {
    "D": 5, "R": 4, "A": 3, "S": 2, "T": 1, "I": 5, "C": 3,
}

# Diccionario de Pesos para cada Escenario
ESCENARIOS_PESOS = {
    "Estándar (Intrínseco)": PESOS_ESTANDAR,
    "Acuífero Confinado": {"D": 5, "R": 1, "A": 3, "S": 2, "T": 1, "I": 5, "C": 2}, 
    "Acuífero Semiconfinado": {"D": 5, "R": 5, "A": 4, "S": 2, "T": 1, "I": 5, "C": 3}, 
    "Acuífero Libre": {"D": 5, "R": 4, "A": 3, "S": 3, "T": 1, "I": 5, "C": 4}, 
    "Acuífero Kárstico": {"D": 4, "R": 5, "A": 5, "S": 1, "T": 2, "I": 5, "C": 5}, 
}

# 💡 RANGOS TEÓRICOS CALIBRADOS (Intervalos Fijos Min/Max de cada escenario)
# Los valores son los 4 cortes que separan las 5 clases (C1, C2, C3, C4)
RANGOS_CALIBRADOS_FIJOS = {
    "Estándar (Intrínseco)": [64, 106, 147, 189],
    "Acuífero Confinado": [53, 88, 122, 157],
    "Acuífero Semiconfinado": [70, 115, 160, 205], 
    "Acuífero Libre": [70, 115, 160, 205],
    "Acuífero Kárstico": [76, 125, 174, 223],
}

# Diccionario de Variables con Acrónimos y Nombres Completos (se mantiene igual)
VARIABLES_DRASTIC = {
    "D": ("Profundidad del Agua", 5), "R": ("Recarga Neta", 4), "A": ("Material del Acuífero", 3),
    "S": ("Material del Suelo", 2), "T": ("Topografía", 1), "I": ("Zona No Saturada", 5),
    "C": ("Conductividad Hidráulica", 3),
}


# --- 2. CONFIGURACIÓN INICIAL DE LA APP ---
st.set_page_config(
    page_title="DRASTIC Map Algebra Tool",
    layout="wide"
)

# ➡️ LÍNEA PARA AGREGAR LA IMAGEN EN LA PORTADA PRINCIPAL
st.image("Logo.png", caption="DRASTIC - Análisis de Vulnerabilidad", width=1500)

st.title("🗺️ Calculadora de Vulnerabilidad DRASTIC Ponderada")
st.markdown("Herramienta flexible para el **Álgebra de Mapas** y el cálculo de vulnerabilidad mediante la fórmula: $Vulnerabilidad = \sum_{i=1}^{7}(R_i \cdot W_i)$")

# --- 3. WIDGETS DE ENTRADA EN LA BARRA LATERAL (Sidebar) ---
st.sidebar.header("⚙️ Configuración del Escenario")

# ➡️ LÍNEA PARA AGREGAR LA IMAGEN EN LA BARRA LATERAL
st.sidebar.image("Logo_2.png", use_column_width=True)

# Selección del Acuífero (ESCENARIO CRÍTICO)
tipo_acuifero = st.sidebar.selectbox(
    "Selecciona el Tipo de Acuífero (Escenario de Pesos):",
    list(ESCENARIOS_PESOS.keys())
)

# Cargar los pesos del escenario seleccionado
pesos_seleccionados = ESCENARIOS_PESOS[tipo_acuifero]

st.sidebar.markdown("---")

# Diccionario para almacenar los rásters subidos
rasters_subidos = {}
st.sidebar.subheader("📤 Carga de Rásters de Variables")
st.sidebar.caption("Sube los rásters de **Calificación ($R_i$)** para cada factor.")

# Widgets para subir archivos ráster
for acronimo, (nombre_var, peso_std) in VARIABLES_DRASTIC.items():
    archivo_subido = st.sidebar.file_uploader(
        f"Cargar Ráster **{acronimo}** - {nombre_var}",
        type=["tif"],
        key=f"uploader_{acronimo}"
    )
    if archivo_subido:
        rasters_subidos[acronimo] = archivo_subido
        st.sidebar.success(f"✔️ Ráster '{acronimo}' cargado.")

st.sidebar.markdown("---")

# --- 4. VISUALIZACIÓN Y AJUSTE DE PESOS ($W_i$) ---

st.header(f"⚖️ Pesos ($W_i$) Asignados: **{tipo_acuifero}**")
st.markdown("Ajusta los *sliders* para modificar los pesos. Los valores iniciales corresponden al escenario seleccionado.")

# Crear una fila SÓLO para los encabezados
col_acronimo_h, col_var_h, col_peso_h, col_std_h = st.columns([1, 4, 2, 1])

# Centrar los encabezados usando HTML/CSS
with col_acronimo_h: st.markdown("<h3 style='text-align: center;'>Fact.</h3>", unsafe_allow_html=True)
with col_var_h: st.markdown("<h3 style='text-align: center;'>Variable</h3>", unsafe_allow_html=True)
with col_peso_h: st.markdown("<h3 style='text-align: center;'>Peso ($W$)</h3>", unsafe_allow_html=True)
with col_std_h: st.markdown("<h3 style='text-align: center;'>$W_{std}$</h3>", unsafe_allow_html=True)

pesos_ajustados = {}

# Se crea la interfaz de ajuste de pesos
for acronimo, (nombre_var, peso_std) in VARIABLES_DRASTIC.items():
    
    peso_inicial = pesos_seleccionados.get(acronimo, peso_std)

    # Definir las columnas DENTRO del bucle para cada fila
    col_acronimo, col_var, col_peso, col_std = st.columns([1, 4, 2, 1])

    # Centrar el contenido de cada celda usando HTML/CSS
    with col_acronimo:
        # Centra y mantiene el texto en negrita
        st.markdown(f"<p style='text-align: center; font-weight: bold;'>{acronimo}</p>", unsafe_allow_html=True)

    with col_var:
        # Centra el nombre de la variable. OJO: Si este texto es muy largo, podría ser mejor dejarlo alineado a la izquierda.
        st.markdown(f"<p style='text-align: center;'>{nombre_var}</p>", unsafe_allow_html=True)

    with col_peso:
        # Widget para modificar el peso. El slider no puede ser centrado por este método, pero el texto sí.
        # El slider se alinea dentro del ancho de su columna.
        peso = st.slider(
            f"Peso {acronimo}",
            min_value=1,
            max_value=10,
            value=peso_inicial,
            key=f"peso_{acronimo}",
            label_visibility="collapsed"
        )
        pesos_ajustados[acronimo] = peso

    with col_std:
        # Centra el peso estándar
        st.markdown(f"<p style='text-align: center;'>*{peso_std}*</p>", unsafe_allow_html=True)

# --- 5. LÓGICA DEL CÁLCULO, DOBLE RÁSTER Y RECLASIFICACIÓN EN TIEMPO REAL (VERSIÓN FINAL) ---

st.markdown("---")
st.header("📈 Resultados del Análisis de Vulnerabilidad")

if len(rasters_subidos) == len(VARIABLES_DRASTIC):
    st.success("¡Todos los rásters de Calificación ($R_i$) cargados! Listo para calcular.")

    # ➡️ Opción para Seleccionar el Método de Reclasificación
    metodo_reclasificacion = st.selectbox(
        "Selecciona el Método de Reclasificación Cualitativa:",
        ["Dinámico (Quintiles/Percentiles)", "Fijo (Intervalos Teóricos Calibrados)"]
    )

    if st.button("🚀 Generar Ambos Mapas de Vulnerabilidad"):
        
        try:
            # 1. CÁLCULO DEL ÍNDICE DRASTIC PONDERADO (Producto 1)
            
            # --- Bloque de Cálculo Ponderado y Máscara (código sin cambios) ---
            
            primer_acronimo = list(VARIABLES_DRASTIC.keys())[0]
            primer_raster_file = rasters_subidos[primer_acronimo]
            primer_bytes_file = BytesIO(primer_raster_file.getvalue())

            with rasterio.open(primer_bytes_file) as src:
                perfil_salida = src.profile
                forma = src.shape
                NODATA_VAL = src.nodata 
                if NODATA_VAL is None: NODATA_VAL = -9999.0

            vulnerabilidad_mapa = np.zeros(forma, dtype=np.float32)
            mascara_comun = np.ones(forma, dtype=bool)

            for acronimo in VARIABLES_DRASTIC.keys():
                raster_file = rasters_subidos[acronimo]
                peso = pesos_ajustados[acronimo]
                bytes_file = BytesIO(raster_file.getvalue())

                with rasterio.open(bytes_file) as src:
                    calificacion_R = src.read(1).astype(np.float32)
                    mascara_actual = (calificacion_R != NODATA_VAL)
                    mascara_comun = mascara_comun & mascara_actual
                    
                    calificacion_R_validos = calificacion_R * mascara_actual
                    contribucion = calificacion_R_validos * peso
                    vulnerabilidad_mapa += contribucion
            
            # Aplicar la máscara al ráster continuo
            vulnerabilidad_mapa_continuo = vulnerabilidad_mapa.copy()
            vulnerabilidad_mapa_continuo[~mascara_comun] = NODATA_VAL
            
            st.success("Cálculo del Índice DRASTIC Ponderado (Continuo) completado.")
            
            
            # 2. PRODUCTO 1: Guardar y Ofrecer el Ráster Continuo (código sin cambios)
            
            st.subheader("1. Índice DRASTIC Ponderado (Continuo)")
            
            perfil_continuo = perfil_salida.copy()
            perfil_continuo.update(dtype=rasterio.float32, count=1, nodata=NODATA_VAL)
            
            output_buffer_cont = BytesIO()
            with rasterio.open(output_buffer_cont, 'w', **perfil_continuo) as dst:
                dst.write(vulnerabilidad_mapa_continuo, 1)

            valores_validos_cont = vulnerabilidad_mapa_continuo[mascara_comun]
            
            if valores_validos_cont.size == 0:
                st.error("No se puede reclasificar sin datos válidos. Asegúrate de que tus rásters se superpongan.")
                st.stop()
            
            st.info(f"Rango de Vulnerabilidad: {valores_validos_cont.min():.2f} a {valores_validos_cont.max():.2f}")
            output_buffer_cont.seek(0)
            st.download_button(
                label="📥 Descargar Ráster CONTINUO (Índice DRASTIC)",
                data=output_buffer_cont.read(),
                file_name=f"DRASTIC_indice_{tipo_acuifero.replace(' ', '_')}.tif",
                mime="application/octet-stream"
            )
            
            st.markdown("---")
            
            
            # 3. RECLASIFICACIÓN DINÁMICA O FIJA (Cualitativa - Producto 2)
            
            st.subheader("2. Reclasificación Cualitativa (5 Clases)")
            
            # 💡 LÓGICA DE SELECCIÓN DE CORTES
            if metodo_reclasificacion == "Dinámico (Quintiles/Percentiles)":
                # Método: Dinámico (Quintiles) - Basado en la distribución real de los datos
                cortes_reales = np.percentile(valores_validos_cont, [20, 40, 60, 80])
                st.info(f"✅ Método: Quintiles. Cortes calculados: {cortes_reales.round(2).tolist()}")
            else:
                # Método: Fijo (Intervalos Teóricos Calibrados) - Basado en el rango teórico del escenario
                cortes_reales = np.array(RANGOS_CALIBRADOS_FIJOS[tipo_acuifero])
                st.info(f"✅ Método: Intervalos Fijos. Cortes usados para **{tipo_acuifero}**: {cortes_reales.tolist()}")
            
            
            # SOLUCIÓN ESTABLE DE df_cortes (Construcción con Concatenación Segura)
            etiquetas_vulnerabilidad = ['Muy Baja', 'Baja', 'Moderada', 'Alta', 'Muy Alta']
            
            # Rango Superior (5 elementos): [C1, C2, C3, C4, Max]
            rango_superior_list = cortes_reales.tolist() + [valores_validos_cont.max()]

            # Rango Inferior (5 elementos): [Min, C1+ε, C2+ε, C3+ε, C4+ε]
            rango_inferior_list = [valores_validos_cont.min()] 
            rango_inferior_list.extend([c + 0.01 for c in cortes_reales[:-1].tolist()]) 
            rango_inferior_list.append(cortes_reales[-1] + 0.01)

            # Ajuste de índice (solo para que la tabla se vea bien)
            rango_inferior_list[-1] = cortes_reales[-1] + 0.01
            
            # Crear y mostrar el DataFrame
            df_cortes = pd.DataFrame({
                'Vulnerabilidad': etiquetas_vulnerabilidad,
                'Rango Inferior': rango_inferior_list,
                'Rango Superior': rango_superior_list
            })

            st.dataframe(df_cortes.set_index('Vulnerabilidad'))


            # 4. Aplicar la Reclasificación
            
            reclasificacion_mapa = np.ones(forma, dtype=np.uint8) # Inicializar en Clase 1 (Muy Baja)

            # Asignación de clases de la más alta a la más baja, usando los cortes
            reclasificacion_mapa[vulnerabilidad_mapa > cortes_reales[3]] = 5 # Muy Alta 
            reclasificacion_mapa[vulnerabilidad_mapa > cortes_reales[2]] = 4 # Alta 
            reclasificacion_mapa[vulnerabilidad_mapa > cortes_reales[1]] = 3 # Moderada 
            reclasificacion_mapa[vulnerabilidad_mapa > cortes_reales[0]] = 2 # Baja 
            # Clase 1 (Muy Baja) ya está asignada por defecto

            # 5. PRODUCTO 2: Aplicar Máscara, Guardar y Ofrecer el Ráster de Clases
            
            NODATA_CLASE = 0 
            reclasificacion_mapa[~mascara_comun] = NODATA_CLASE
            
            st.success(f"Generación del producto final completada. Clases de vulnerabilidad: 1 a 5.")
            
            perfil_clases = perfil_salida.copy()
            perfil_clases.update(dtype=rasterio.uint8, count=1, nodata=NODATA_CLASE)
            
            output_buffer_clases = BytesIO()
            with rasterio.open(output_buffer_clases, 'w', **perfil_clases) as dst:
                dst.write(reclasificacion_mapa, 1)

            clases, conteos = np.unique(reclasificacion_mapa[mascara_comun], return_counts=True)
            
            df_resumen = pd.DataFrame({
                'Clase (Valor)': clases,
                'Vulnerabilidad': ['Muy Baja', 'Baja', 'Moderada', 'Alta', 'Muy Alta'][:len(clases)],
                'Área Píxeles': conteos
            })
            st.dataframe(df_resumen.set_index('Clase (Valor)'))
            
            output_buffer_clases.seek(0)
            st.download_button(
                label="📥 Descargar Ráster CUALITATIVO (Clases 1-5)",
                data=output_buffer_clases.read(),
                file_name=f"DRASTIC_clases_{tipo_acuifero.replace(' ', '_')}_{metodo_reclasificacion.split(' ')[0]}.tif",
                mime="application/octet-stream"
            )

        except Exception as e:
            st.error(f"⚠️ Ocurrió un error. Asegúrate de que todos los rásters tengan la misma extensión, resolución y CRS.")
            st.exception(e)

else:
    st.warning("Por favor, carga los **7 archivos ráster** de las variables de Calificación ($R_i$) en la barra lateral izquierda para iniciar el cálculo.")