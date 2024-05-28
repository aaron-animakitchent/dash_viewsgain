import streamlit as st
import requests
import pickle
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Load configuration from pickle file
config = pickle.load(open(r'.\pkls\config.pkl', 'rb'))
api_key_tub = config['api_key_tub']
proxies = config['proxies']

# Initialize session_state for view_count if not exists
if 'view_count' not in st.session_state:
    st.session_state['view_count'] = None

# Function to get videos based on the query
def get_videos_by_query_tubular(proxies, query, date_range):
    headers = {
        'Api-Key': api_key_tub,
    }

    data = {
        "query": {
            "include_filter": {
                "search": query
            }
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
    print(response_json)
    if 'videos' in response_json and len(response_json['videos']) > 0:
        return response_json['videos']
    else:
        raise Exception("No videos found for the given query")

# Define date ranges
today = datetime.today()
date_ranges = {
    '7 days': {'min': (today - timedelta(days=7)).strftime('%Y-%m-%d'), 'max': today.strftime('%Y-%m-%d')},
    '14 days': {'min': (today - timedelta(days=14)).strftime('%Y-%m-%d'), 'max': today.strftime('%Y-%m-%d')},
    '1 month': {'min': (today - timedelta(days=30)).strftime('%Y-%m-%d'), 'max': today.strftime('%Y-%m-%d')},
    'YTD': {'min': f'{today.year}-01-01', 'max': today.strftime('%Y-%m-%d')},
}

# Streamlit app
st.title('Video Query App')

# Date range selection
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
    date_range = date_ranges['7 days']  # Default selection

# Query input
query = st.text_input('Search Query', 'navalha')

# Video type selection
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
        video_types = []  # Reset to empty to include all types if 'All' is selected

# Fetch and display videos
st.subheader('Videos')
try:
    videos = get_videos_by_query_tubular(proxies, query, date_range)
except Exception as e:
    st.error(f"Error: {str(e)}")
    videos = []

# Filter videos based on selected types
if videos:
    filtered_videos = []
    for video in videos:
        is_short = video['duration'] < 62
        is_live = video['video_was_live']
        if 'short' in video_types and is_short:
            filtered_videos.append(video)
        elif 'livestream' in video_types and is_live:
            filtered_videos.append(video)
        elif 'video' in video_types and not (is_short or is_live):
            filtered_videos.append(video)
        elif not video_types:
            filtered_videos.append(video)
    videos = filtered_videos

# Plotting the stacked line chart for views over time
if videos:
    st.subheader('Views Over Time')
    views_data = pd.DataFrame(videos)
    views_data['publish_date'] = pd.to_datetime(views_data['publish_date'])
    views_data = views_data.sort_values('publish_date')

    views_data['video_type'] = views_data.apply(
        lambda x: 'short' if x['duration'] < 62 else ('livestream' if x['video_was_live'] else 'video'), axis=1)

    pivot_table = views_data.pivot_table(index='publish_date', columns='video_type', values='views_gain', aggfunc='sum').fillna(0)

    fig, ax = plt.subplots()
    pivot_table.plot(kind='area', stacked=True, ax=ax)
    ax.set_xlabel('Publish Date')
    ax.set_ylabel('Views gain')
    ax.set_title('Stacked Line Chart of Views Over Time')
    plt.xticks(rotation=45)
    st.pyplot(fig)

    # Display videos in a table format
    st.subheader('Videos')
    for _, video in views_data.iterrows():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            st.image(video['thumbnail_url'], width=100)
        with col2:
            st.write(f"**{video['video_id']}** - {video['title']}")
        with col3:
            st.write(f"[Watch Video]({video['video_url']})")
