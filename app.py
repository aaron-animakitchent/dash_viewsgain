import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import logging
from utils import build_payload_search, build_payload_video_details, fetch_data_post, trends_response_to_dataframe, video_details_response_to_dataframe, set_date_range, categorize_video

# Configuración del logger
logging.basicConfig(level=logging.INFO, format='%(asctime=s - %(levelname=s - %(message=s')
logger = logging.getLogger(__name__)

st.set_page_config(layout="wide")

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
if 'comparison_searches' not in st.session_state:
    st.session_state.comparison_searches = []
    
# Selección de granularidad
st.write("### Seleccione la granularidad de los datos:")
granularity_option = st.selectbox(
    "",
    ('Día', 'Semana', 'Mes', 'Año'),
    index=0
)
# Entrada de búsqueda
st.write("### Búsqueda")
search = st.text_input('Buscar')

# Botón para añadir a la búsqueda
if st.button('Añadir a la búsqueda'):
    if search:
        st.session_state.search_terms.append(search)
        st.experimental_rerun()

# Botón para añadir a la comparación
if st.button('Añadir a la comparación'):
    if st.session_state.search_terms:
        st.session_state.comparison_searches.append(' OR '.join(st.session_state.search_terms))
        st.session_state.search_terms = []
        st.experimental_rerun()

# Mostrar términos de búsqueda actuales
if st.session_state.search_terms:
    st.write(f"Términos de búsqueda actuales: {' , '.join(st.session_state.search_terms)}")

# Mostrar términos de comparación actuales
if st.session_state.comparison_searches:
    st.write(f"Búsquedas para comparar: {', '.join(st.session_state.comparison_searches)}")

st.divider()



def process_data_for_plotting(df_combined, granularity_option, selected_video_types):
    # Filtrar por tipo de video
    df_filtered = df_combined[df_combined['tipo_video'].isin(selected_video_types)]
    logger.info(f'DataFrame filtrado por tipo de video: {df_filtered.head()}')

    # Agrupar datos según la granularidad seleccionada
    if granularity_option == 'Día':
        df_filtered['granularity'] = df_filtered['date'].dt.to_period('D').dt.start_time
    elif granularity_option == 'Semana':
        df_filtered['granularity'] = df_filtered['date'].dt.to_period('W').apply(lambda r: f"W{r.week} {r.start_time.year}")
    elif granularity_option == 'Mes':
        df_filtered['granularity'] = df_filtered['date'].dt.to_period('M').dt.start_time
    elif granularity_option == 'Año':
        df_filtered['granularity'] = df_filtered['date'].dt.to_period('Y').dt.start_time

    # Agrupar y graficar las visualizaciones frente a la fecha por tipo de video
    df_grouped = df_filtered.groupby(['granularity', 'tipo_video'])['views'].sum().reset_index()
    if granularity_option == 'Semana':
        df_grouped['granularity'] = pd.Categorical(df_grouped['granularity'], ordered=True, categories=sorted(df_grouped['granularity'].unique(), key=lambda x: (int(x.split()[1]), int(x.split()[0][1:]))))
    df_pivot = df_grouped.pivot(index='granularity', columns='tipo_video', values='views').fillna(0)
    df_pivot = df_pivot.sort_index()

    return df_pivot

# Botón de búsqueda principal
if st.button('Buscar', key='buscar'):
    with st.spinner('Obteniendo datos de la API...'):
        try:
            combined_search = ' OR '.join(st.session_state.search_terms)
            df_combined = fetch_combined_data(combined_search, min_date, max_date)

            # Almacenar el DataFrame combinado en el estado de la sesión
            st.session_state.df_combined = df_combined

            # Procesar datos para la gráfica
            df_pivot = process_data_for_plotting(df_combined, granularity_option, selected_video_types)

            # Ajustar los límites del eje x para que solo se muestren datos disponibles
            min_date = df_pivot.index[0]
            max_date = df_pivot.index[-1]

            plt.figure(figsize=(10, 6))
            plt.stackplot(df_pivot.index, df_pivot.T, labels=df_pivot.columns)
            plt.legend(loc='upper left')
            plt.xlabel('Fecha')
            plt.ylabel('Ganancias de Visualizaciones')
            plt.title(f'Ganancias de Visualizaciones a lo Largo del Tiempo por Tipo de Video (Apilado) - Granularidad: {granularity_option}')
            plt.xlim(min_date, max_date)
            if granularity_option == 'Semana':
                plt.xticks(rotation=45, ha='right')
                plt.gca().set_xticks(range(len(df_pivot.index)))
                plt.gca().set_xticklabels(df_pivot.index, rotation=45, ha='right')
            else:
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

# Botón de comparación
if st.button('Comparar'):
    if st.session_state.comparison_searches:
        with st.spinner('Obteniendo datos de la API...'):
            comparison_data = []
            try:
                for search in st.session_state.comparison_searches:
                    df_combined = fetch_combined_data(search, min_date, max_date)
                    comparison_data.append((search, df_combined))

                st.session_state.comparison_data = comparison_data
                st.session_state.comparison_searches = []
                st.experimental_rerun()

            except Exception as e:
                logger.error(f"Error obteniendo datos: {e}")
                st.error(f"Error obteniendo datos: {e}")

# Mostrar comparación de resultados
if 'comparison_data' in st.session_state and st.session_state.comparison_data:
    st.write("### Comparación de Resultados:")
    comparison_data = st.session_state.comparison_data

    # Crear columnas para cada comparación
    cols = st.columns(len(comparison_data))
    for col, (search, df_combined) in zip(cols, comparison_data):
        with col:
            st.write(f"{search}")

            # Procesar datos para la gráfica
            df_pivot = process_data_for_plotting(df_combined, granularity_option, selected_video_types)

            # Ajustar los límites del eje x para que solo se muestren datos disponibles
            min_date = df_pivot.index[0]
            max_date = df_pivot.index[-1]

            plt.figure(figsize=(10, 6))
            plt.stackplot(df_pivot.index, df_pivot.T, labels=df_pivot.columns)
            plt.legend(loc='upper left')
            plt.xlabel('Fecha')
            plt.ylabel('Ganancias de Visualizaciones')
            plt.title(f'Ganancias de Visualizaciones a lo Largo del Tiempo por Tipo de Video (Apilado) - Granularidad: {granularity_option}')
            plt.xlim(min_date, max_date)
            if granularity_option == 'Semana':
                plt.xticks(rotation=45, ha='right')
                plt.gca().set_xticks(range(len(df_pivot.index)))
                plt.gca().set_xticklabels(df_pivot.index, rotation=45, ha='right')
            else:
                plt.xticks(rotation=45)
            st.pyplot(plt)

            st.divider()

            # Crear DataFrame intermedio para mostrar detalles de los videos
            df_unique_videos = df_combined[['video_id', 'title', 'thumbnail_url', 'video_url']].drop_duplicates(subset=['video_id'])

            # Mostrar detalles de videos
            st.write("### Detalles de Videos:")
            for idx, row in df_unique_videos.iterrows():
                cols_videos = st.columns(3)
                with cols_videos[0]:
                    st.image(row['thumbnail_url'], width=120)
                with cols_videos[1]:
                    st.write(f"{row['video_id']} - {row['title']}")
                with cols_videos[2]:
                    st.write(f"[Ver Video]({row['video_url']})")

            st.divider()

# Mostrar DataFrame combinado, oculto por defecto
if 'df_combined' in st.session_state:
    if st.checkbox('Mostrar DataFrame combinado'):
        st.write("### DataFrame combinado:")
        st.dataframe(st.session_state.df_combined)

    st.divider()

    # Botón para descargar CSV
    csv = st.session_state.df_combined.to_csv(index=False).encode('utf-8')
    st.download_button(label="Descargar CSV", data=csv, file_name='video_trends.csv', mime='text/csv')
