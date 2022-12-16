import base64
import time
from pathlib import Path
import requests

for i in range(100):
    start = time.time()
    response = requests.post('https://fgqkv-01gmbp5pydq2c217qt2qyaxcrv.litng-ai-03.litng.ai/predict', json={
        "text": "A portrait of a person looking away from the camera"
    })

    img = response.json()["image"]
    img = base64.b64decode(img.encode("utf-8"))
    Path(f"response_{i}.png").write_bytes(img)
    print(i, time.time() - start)