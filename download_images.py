import json
import os

import requests
from rich.progress import track

with open("result/yellow_notices_2023-04-07--21-10.json") as f:
    data = json.load(f)

img_list = [obj["img"] for obj in data]

if not os.path.exists("result/yellow_notices"):
    os.makedirs("result/yellow_notices")

for img in track(img_list, description=f"Идёт загрузка... "):
    filename = img.split("/")[-1]
    filepath = os.path.join("result/yellow_notices", filename)

    response = requests.get(img)
    with open(filepath, "wb") as f:
        f.write(response.content)
