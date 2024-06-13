import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import logging
from utils import build_payload_search, build_payload_video_details, fetch_data_post, trends_response_to_dataframe, video_details_response_to_dataframe, set_date_range, categorize_video

# Configuración del logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message=s')
logger = logging.getLogger(__name__)

@st.cache_data
def fetch_combined_data(search, min_date, max_date):
    # Realizar la primera consulta
    base_url = 'https://tubularlabs.com/api/'
    url_trends = base_url + 'v3.1/video.trends'
    payload_trends = build_payload_search(search, min_date, max_date)
    logger.info(f'Realizando consulta a la API de tendencias con payload: {payload_trends}')
    data_trends = fetch_data_post(url_trends, payload_trends)
    df_trends = trends_response_to_dataframe(data_trends)

    # Realizar la segunda consulta para cada video_id en los resultados de la primera consulta
    url_video_details = base_url + 'v3/video.search'
    video_details_records = []

    for video_id in df_trends['video_id'].unique():
        payload_video_details = build_payload_video_details(video_id)
        logger.info(f'Realizando consulta a la API de detalles del video para video_id {video_id}')
        data_video_details = fetch_data_post(url_video_details, payload_video_details)
        df_video_details = video_details_response_to_dataframe(data_video_details)
        video_details_records.append(df_video_details)

    # Concatenar todos los DataFrames de detalles de video
    df_all_video_details = pd.concat(video_details_records, ignore_index=True)

    # Combinar los DataFrames de tendencias y detalles de videos
    df_combined = pd.merge(df_trends, df_all_video_details, on='video_id', how='left')
    df_combined['date'] = pd.to_datetime(df_combined['date'])
    logger.info(f'DataFrame combinado construido: {df_combined.head()}')

    # Añadir columna de tipo de video
    df_combined['tipo_video'] = df_combined.apply(categorize_video, axis=1)

    return df_combined

# Configuración del Dashboard
st.title('YouTube Video Trends Dashboard')
st.write('Este dashboard muestra las tendencias de visualizaciones de videos de YouTube y sus detalles.')

st.divider()

# Selección de rango de fechas en horizontal usando st.radio
st.write("### Seleccione el rango de fechas:")
date_option = st.radio(
    "",
    ('Últimos 7 días', 'Últimos 14 días', 'Último mes', 'YTD', 'Personalizado'),
    index=0,
    horizontal=True
)

# Configuración del rango de fechas basado en la opción seleccionada
min_date, max_date = set_date_range(date_option)

if date_option == 'Personalizado':
    col1, col2 = st.columns(2)
    with col1:
        min_date = st.date_input('Fecha mínima', pd.to_datetime('2023-01-01'))
    with col2:
        max_date = st.date_input('Fecha máxima', pd.to_datetime('2023-06-30'))

st.divider()

# Checkboxes para seleccionar el tipo de video en horizontal
st.write("### Seleccione el tipo de video:")
col6, col7, col8, col9 = st.columns(4)

# Variables de estado para los checkboxes
if 'todos' not in st.session_state:
    st.session_state.todos = False
if 'shorts' not in st.session_state:
    st.session_state.shorts = True
if 'videos' not in st.session_state:
    st.session_state.videos = True
if 'directos' not in st.session_state:
    st.session_state.directos = True

def update_checkboxes(key):
    if key == 'todos':
        if st.session_state.todos:
            st.session_state.shorts = False
            st.session_state.videos = False
            st.session_state.directos = False
    else:
        if st.session_state.shorts or st.session_state.videos or st.session_state.directos:
            st.session_state.todos = False

# Checkbox logic
with col6:
    short_checkbox = st.checkbox('Shorts', value=st.session_state.shorts, key='shorts', on_change=update_checkboxes, args=('shorts',))
with col7:
    video_checkbox = st.checkbox('Videos', value=st.session_state.videos, key='videos', on_change=update_checkboxes, args=('videos',))
with col8:
    directo_checkbox = st.checkbox('Directos', value=st.session_state.directos, key='directos', on_change=update_checkboxes, args=('directos',))
with col9:
    todos_checkbox = st.checkbox('Todos', value=st.session_state.todos, key='todos', on_change=update_checkboxes, args=('todos',))

st.divider()

# Determinar los tipos de video seleccionados
selected_video_types = []
if st.session_state.todos:
    selected_video_types = ['Short', 'Video', 'Directo']
else:
    if st.session_state.shorts:
        selected_video_types.append('Short')
    if st.session_state.videos:
        selected_video_types.append('Video')
    if st.session_state.directos:
        selected_video_types.append('Directo')

# Inicializar la lista de términos de búsqueda en el estado de la sesión
if 'search_terms' not in st.session_state:
    st.session_state.search_terms = []

# Entrada de búsqueda
st.write("### Búsqueda")
search = st.text_input('Buscar')

# Botón para añadir a la búsqueda
if st.button('Añadir a la búsqueda'):
    if search:
        st.session_state.search_terms.append(search)
        st.write(f"Términos de búsqueda actuales: {' OR '.join(st.session_state.search_terms)}")

# Mostrar términos de búsqueda actuales
if st.session_state.search_terms:
    st.write(f"Términos de búsqueda actuales: {' OR '.join(st.session_state.search_terms)}")

st.divider()

# Botón de búsqueda principal
if st.button('Buscar', key='buscar'):
    with st.spinner('Obteniendo datos de la API...'):
        try:
            combined_search = ' OR '.join(st.session_state.search_terms)
            df_combined = fetch_combined_data(combined_search, min_date, max_date)

            # Almacenar el DataFrame combinado en el estado de la sesión
            st.session_state.df_combined = df_combined

            # Filtrar por tipo de video
            df_filtered = df_combined[df_combined['tipo_video'].isin(selected_video_types)]
            logger.info(f'DataFrame filtrado por tipo de video: {df_filtered.head()}')

            # Agrupar y graficar las visualizaciones frente a la fecha por tipo de video
            st.write("### Gráfico de ganancias de visualizaciones frente a la fecha por tipo de video (apilado):")
            df_grouped = df_filtered.groupby(['date', 'tipo_video']).sum().reset_index()
            df_pivot = df_grouped.pivot(index='date', columns='tipo_video', values='views').fillna(0)
            df_pivot = df_pivot.sort_index()

            plt.figure(figsize=(10, 6))
            plt.stackplot(df_pivot.index, df_pivot.T, labels=df_pivot.columns)
            plt.legend(loc='upper left')
            plt.xlabel('Fecha')
            plt.ylabel('Ganancias de Visualizaciones')
            plt.title('Ganancias de Visualizaciones a lo Largo del Tiempo por Tipo de Video (Apilado)')
            plt.xticks(rotation=45)
            st.pyplot(plt)

            st.divider()

            # Crear DataFrame intermedio para mostrar detalles de los videos
            df_unique_videos = df_combined[['video_id', 'title', 'thumbnail_url', 'video_url']].drop_duplicates(subset=['video_id'])

            # Mostrar detalles de videos
            st.write("### Detalles de Videos:")
            for idx, row in df_unique_videos.iterrows():
                cols = st.columns(3)
                with cols[0]:
                    st.image(row['thumbnail_url'], width=120)
                with cols[1]:
                    st.write(f"{row['video_id']} - {row['title']}")
                with cols[2]:
                    st.write(f"[Ver Video]({row['video_url']})")

            st.divider()

        except Exception as e:
            logger.error(f"Error obteniendo datos: {e}")
            st.error(f"Error obteniendo datos: {e}")

# Mostrar DataFrame combinado, oculto por defecto
if 'df_combined' in st.session_state:
    if st.checkbox('Mostrar DataFrame combinado'):
        st.write("### DataFrame combinado:")
        st.dataframe(st.session_state.df_combined)

    st.divider()

    # Botón para descargar CSV
    csv = st.session_state.df_combined.to_csv(index=False).encode('utf-8')
    st.download_button(label="Descargar CSV", data=csv, file_name='video_trends.csv', mime='text/csv')
