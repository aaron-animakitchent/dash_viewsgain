import streamlit as st
import requests
import pickle
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta


st. set_page_config(layout="wide")
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
        raise Exception(f"API request failed with status code {response.status_code}: {response.text}")

    response_json = response.json()
    if 'videos' in response_json and len(response_json['videos']) > 0:
        return response_json['videos']
    else:
        raise Exception("No videos found for the given query")

# Definir rangos de fechas
today = datetime.today()
date_ranges = {
    '7 days': {'min': (today - timedelta(days=7)).strftime('%Y-%m-%d'), 'max': today.strftime('%Y-%m-%d')},
    '14 days': {'min': (today - timedelta(days=14)).strftime('%Y-%m-%d'), 'max': today.strftime('%Y-%m-%d')},
    '1 month': {'min': (today - timedelta(days=30)).strftime('%Y-%m-%d'), 'max': today.strftime('%Y-%m-%d')},
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

st.title('Video Query App')
st.divider()

# Selección de rango de fechas
st.subheader('Select Date Range')
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    range_7_days = st.checkbox('7 days')
with col2:
    range_14_days = st.checkbox('14 days')
with col3:
    range_1_month = st.checkbox('1 month')
with col4:
    range_ytd = st.checkbox('YTD')
with col5:
    range_custom = st.checkbox('Custom')

if range_custom:
    min_date = st.date_input('Start Date')
    max_date = st.date_input('End Date')
    date_range = {'min': min_date.strftime('%Y-%m-%d'), 'max': max_date.strftime('%Y-%m-%d')}
elif range_7_days:
    date_range = date_ranges['7 days']
elif range_14_days:
    date_range = date_ranges['14 days']
elif range_1_month:
    date_range = date_ranges['1 month']
elif range_ytd:
    date_range = date_ranges['YTD']
else:
    date_range = date_ranges['7 days']  # Selección predeterminada
st.divider()

# Entrada de consulta
query = st.text_input('Search Query', '')

# Añadir consulta a la lista
if st.button('Add Query'):
    if query:
        st.session_state['queries'].append(query)


# Selección de tipos de video
st.subheader('Select Video Types')
col1, col2, col3, col4 = st.columns(4)
video_types = []
with col1:
    if st.checkbox('Video'):
        video_types.append('video')
with col2:
    if st.checkbox('Short'):
        video_types.append('short')
with col3:
    if st.checkbox('Livestream'):
        video_types.append('livestream')
with col4:
    if st.checkbox('All'):
        video_types = []  # Restablecer a vacío para incluir todos los tipos si se selecciona 'All'
st.divider()

# Botón para iniciar la búsqueda
if st.button('Search Videos'):
    st.session_state['results'] = {}
    for q in st.session_state['queries']:
        try:
            videos = get_videos_by_query_tubular(api_key_tub, proxies, q, date_range, video_types)
            st.session_state['results'][q] = videos
        except Exception as e:
            st.error(f"Error for query '{q}': {str(e)}")

# Mostrar las consultas añadidas
st.subheader('Added Queries')
st.write(', '.join(st.session_state['queries']))

# Comparar y mostrar los resultados
if st.session_state['results']:
    st.subheader('Comparison Results')

    queries = list(st.session_state['results'].keys())
    columns = st.columns(len(queries))

    for idx, query in enumerate(queries):
        with columns[idx]:
            st.subheader(f'Results for "{query}"')
            videos = st.session_state['results'][query]
            views_data = pd.DataFrame(videos)
            views_data['publish_date'] = pd.to_datetime(views_data['publish_date'])
            views_data = views_data.sort_values('publish_date')

            # Filtrar datos de vistas según el rango de fechas seleccionado
            views_data = views_data[(views_data['publish_date'] >= date_range['min']) & (views_data['publish_date'] <= date_range['max'])]

            views_data['video_type'] = views_data.apply(
                lambda x: 'short' if x['duration'] < 62 else ('livestream' if x['video_was_live'] else 'video'), axis=1)

            pivot_table = views_data.pivot_table(index='publish_date', columns='video_type', values='views_gain', aggfunc='sum').fillna(0)

            fig, ax = plt.subplots()
            pivot_table.plot(kind='area', stacked=True, ax=ax)
            ax.set_xlabel('Date')
            ax.set_ylabel('Views Gain')
            ax.set_title(f'Views Over Time for "{query}"')
            plt.xticks(rotation=45)
            st.pyplot(fig)

            st.subheader(f'Videos for "{query}"')
            for _, video in views_data.iterrows():
                st.image(video['thumbnail_url'], width=100)
                st.write(f"{video['video_id']['id']} - {video['title']}")
                st.write(f"[Watch Video]({video['video_url']})")
