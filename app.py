import streamlit as st
import requests
import pickle
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

st.set_page_config(layout="wide")

# Cargar configuración desde un archivo pickle
config = pickle.load(open(r'.\pkls\config.pkl', 'rb'))
api_key_tub = config['api_key_tub']
proxies = config['proxies']

# Inicializar session_state para manejar múltiples consultas
if 'queries' not in st.session_state:
    st.session_state['queries'] = []
if 'results' not in st.session_state:
    st.session_state['results'] = {}

# Función para obtener videos basados en la consulta
@st.cache
def get_videos_by_query_tubular(api_key, proxies, query, date_range, video_types):
    headers = {
        'Api-Key': api_key,
    }

    include_filter = {
        "search": query
    }

    if 'short' in video_types:
        include_filter["video_duration"] = {"max": 61}
    elif 'video' in video_types:
        include_filter["video_duration"] = {"min": 62}

    if 'livestream' in video_types:
        include_filter["video_was_live"] = True

    data = {
        "query": {
            "include_filter": include_filter
        },
        "fields": [
            "views",
            "views_gain",
            "video_id",
            "title",
            "thumbnail_url",
            "video_url",
            "publish_date",
            "video_was_live",
            "duration"
        ],
        "sort": {
            "sort": "views_gain",
            "sort_reverse": True,
            "sort_date_range": {
                "min": date_range['min'],
                "max": date_range['max']
            }
        }
    }

    response = requests.post('https://tubularlabs.com/api/v3/video.search', headers=headers, json=data, proxies=proxies)

    if response.status_code != 200:
        raise Exception(f"La solicitud a la API falló con el código de estado {response.status_code}: {response.text}")

    response_json = response.json()
    if 'videos' in response_json and len(response_json['videos']) > 0:
        return response_json['videos']
    else:
        raise Exception("No se encontraron videos para la consulta dada")

# Definir rangos de fechas
today = datetime.today()
date_ranges = {
    '7 días': {'min': (today - timedelta(days=7)).strftime('%Y-%m-%d'), 'max': today.strftime('%Y-%m-%d')},
    '14 días': {'min': (today - timedelta(days=14)).strftime('%Y-%m-%d'), 'max': today.strftime('%Y-%m-%d')},
    '1 mes': {'min': (today - timedelta(days=30)).strftime('%Y-%m-%d'), 'max': today.strftime('%Y-%m-%d')},
    'YTD': {'min': f'{today.year}-01-01', 'max': today.strftime('%Y-%m-%d')},
}

# Aplicación de Streamlit
st.markdown(
    """
    <style>
        .reportview-container .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
        .reportview-container .main {
            max-width: 200%;
            padding: 0;
        }
    </style>
    """,
    unsafe_allow_html=True
)

st.title('Aplicación de Consulta de Videos')
st.divider()

# Selección de rango de fechas
st.subheader('Seleccione el Rango de Fechas')
date_range_option = st.radio(
    "Seleccione una opción:",
    ('7 días', '14 días', '1 mes', 'YTD', 'Personalizado')
)

if date_range_option == 'Personalizado':
    min_date = st.date_input('Fecha de Inicio')
    max_date = st.date_input('Fecha de Fin')
    date_range = {'min': min_date.strftime('%Y-%m-%d'), 'max': max_date.strftime('%Y-%m-%d')}
else:
    # Mapeo de la selección del radio button al rango de fechas
    date_range = date_ranges[date_range_option]

st.divider()

# Entrada de consulta
query = st.text_input('Consulta de Búsqueda', '')

# Añadir consulta a la lista
if st.button('Agregar Consulta'):
    if query:
        st.session_state['queries'].append(query)

# Selección de tipos de video
st.subheader('Seleccione los Tipos de Video')
col1, col2, col3, col4 = st.columns(4)
video_types = []
with col1:
    if st.checkbox('Video'):
        video_types.append('video')
with col2:
    if st.checkbox('Corto'):
        video_types.append('short')
with col3:
    if st.checkbox('Transmisión en Vivo'):
        video_types.append('livestream')
with col4:
    if st.checkbox('Todos'):
        video_types = []  # Restablecer a vacío para incluir todos los tipos si se selecciona 'Todos'
st.divider()

# Botón para iniciar la búsqueda
if st.button('Buscar Videos'):
    st.session_state['results'] = {}
    for q in st.session_state['queries']:
        try:
            videos = get_videos_by_query_tubular(api_key_tub, proxies, q, date_range, video_types)
            st.session_state['results'][q] = videos
        except Exception as e:
            st.error(f"Error para la consulta '{q}': {str(e)}")

# Mostrar las consultas añadidas
st.subheader('Consultas Agregadas')
st.write(', '.join(st.session_state['queries']))

# Comparar y mostrar los resultados
if st.session_state['results']:
    st.subheader('Resultados de la Comparación')

    queries = list(st.session_state['results'].keys())
    columns = st.columns(len(queries))

    for idx, query in enumerate(queries):
        with columns[idx]:
            st.subheader(f'Resultados para "{query}"')
            videos = st.session_state['results'][query]
            views_data = pd.DataFrame(videos)
            views_data['publish_date'] = pd.to_datetime(views_data['publish_date'])
            views_data = views_data.sort_values('publish_date')

            # Filtrar datos de vistas según el rango de fechas seleccionado
            views_data = views_data[(views_data['publish_date'] >= date_range['min']) & (views_data['publish_date'] <= date_range['max'])]

            views_data['video_type'] = views_data.apply(
                lambda x: 'corto' if x['duration'] < 62 else ('transmisión en vivo' if x['video_was_live'] else 'video'), axis=1)

            # Agregar columnas de vistas y vistas ganadas
            views_data['Vistas'] = views_data['views']
            views_data['Vistas Ganadas'] = views_data['views_gain']

            pivot_table = views_data.pivot_table(index='publish_date', columns='video_type', values='views_gain', aggfunc='sum').fillna(0)

            fig, ax = plt.subplots()
            pivot_table.plot(kind='area', stacked=True, ax=ax)
            ax.set_xlabel('Fecha')
            ax.set_ylabel('Visualizaciones')
            ax.set_title(f'Visualizaciones a lo largo del tiempo para "{query}"')
            plt.xticks(rotation=45)
            st.pyplot(fig)

            st.subheader(f'Videos para "{query}"')

            # Mostrar tabla con las vistas y vistas ganadas
            st.write(views_data[['thumbnail_url', 'video_id', 'title', 'Vistas', 'Vistas Ganadas']].set_index('title'))

            # Añadir botón para descargar en CSV
            csv_file = views_data[['thumbnail_url', 'video_id', 'title', 'Vistas', 'Vistas Ganadas']]
            csv_export_button = st.download_button(
                label="Exportar CSV",
                data=csv_file.to_csv().encode('utf-8'),
                file_name=f'resultados_{query}.csv',
                mime='text/csv',
                key=f"csv_button_{query}"  # Utilizar el nombre de la consulta como parte de la clave para hacerla única
            )
            st.write(csv_export_button)
