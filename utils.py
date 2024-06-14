import requests
import pandas as pd
from datetime import datetime, timedelta
import logging

# Configuración del logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Función para construir el payload para la consulta de tendencias de videos
def build_payload_search(search, min_date, max_date):
    payload = {
        "query": {
            "include_filter": {
                "search": search,
                "video_platforms": ["youtube"]
            }
        },
        "date_range": {
            "min": min_date.strftime('%Y-%m-%d'),
            "max": max_date.strftime('%Y-%m-%d')
        },
        "scroll": {
            "scroll_size": 10
        }
        }
    logger.info(f'Payload de búsqueda construido: {payload}')
    return payload

# Función para construir el payload para la consulta de detalles del video
def build_payload_video_details(video_id):
    payload = {
        "query": {
            "include_filter": {
                "video_gids": [
                    "ytv_" + video_id
                ]
            }
        },
        "fields": [
            "video_id",
            "title",
            "duration",
            "publish_date",
            "thumbnail_url",
            "video_url",
            "video_was_live"
        ]
    }
    logger.info(f'Payload de detalles del video construido: {payload}')
    return payload

# Función para hacer la solicitud a la API (POST)
def fetch_data_post(url, payload):
    headers = {'Api-Key': ''}
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    logger.info(f'Datos obtenidos de la API: {response.json()}')
    return response.json()

# Función para convertir la respuesta en un DataFrame de pandas para la primera consulta
def trends_response_to_dataframe(response):
    trends = response['trends']
    records = []
    for trend in trends:
        video_id = trend['id']
        platform = trend['platform']
        for point in trend['points']:
            date = point['date']
            views = point['views']
            engagements = point['engagements']
            records.append([video_id, platform, date, views, engagements])
    df = pd.DataFrame(records, columns=['video_id', 'platform', 'date', 'views', 'engagements'])
    logger.info(f'DataFrame de tendencias construido: {df.head()}')
    return df

# Función para convertir la respuesta en un DataFrame de pandas para la segunda consulta
def video_details_response_to_dataframe(response):
    videos = response['videos']
    records = []
    for video in videos:
        video_id = video['video_id']['id']
        title = video['title']
        duration = video['duration']
        publish_date = video['publish_date']
        thumbnail_url = video['thumbnail_url']
        video_url = video['video_url']
        video_was_live = video.get('video_was_live', False)
        records.append([video_id, title, duration, publish_date, thumbnail_url, video_url, video_was_live])
    df = pd.DataFrame(records, columns=['video_id', 'title', 'duration', 'publish_date', 'thumbnail_url', 'video_url', 'video_was_live'])
    logger.info(f'DataFrame de detalles del video construido: {df.head()}')
    return df

# Función para establecer el rango de fechas
def set_date_range(option):
    today = datetime.now()
    if option == 'Últimos 7 días':
        return today - timedelta(days=7), today
    elif option == 'Últimos 14 días':
        return today - timedelta(days=14), today
    elif option == 'Último mes':
        return today - timedelta(days=30), today
    elif option == 'YTD':
        return datetime(today.year, 1, 1), today
    elif option == 'Personalizado':
        return None, None

# Función para categorizar el tipo de video
def categorize_video(row):
    if row['video_was_live']:
        return 'Directo'
    elif row['duration'] < 62:
        return 'Short'
    else:
        return 'Video'
