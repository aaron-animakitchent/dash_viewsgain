import pystray
from PIL import Image
import threading
import requests
import time

headers = {
    'Api-Key': '62668-e737eed94e4d0e074a891f484c1c7710',
}

def api_available():
    
    limits = requests.post('https://tubularlabs.com/api/v3/rate_limit.details', headers=headers)
    limit1 = limits.json()['rate_limits']['Concurrency']['remaining']
    
    time.sleep(10)
    
    limits = requests.post('https://tubularlabs.com/api/v3/rate_limit.details', headers=headers)
    limit2 = limits.json()['rate_limits']['Concurrency']['remaining']
    
    return (limit1 and limit2)

def create_image(color):
    image = Image.new('RGB', (30, 30), color=color)
    return image

def update_icon():
    while True:
        if api_available():
            icon.icon = create_image('green')
        else:
            icon.icon = create_image('red')

        threading.Event().wait(60*3)

icon = pystray.Icon("test_icon", create_image('red'))
t = threading.Thread(target=update_icon)
t.start()
icon.run()

