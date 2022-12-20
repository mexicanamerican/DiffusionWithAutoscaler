# !pip install lightning_api_access
# !pip install 'git+https://github.com/Lightning-AI/stablediffusion.git@lit'
# !curl https://raw.githubusercontent.com/Lightning-AI/stablediffusion/main/configs/stable-diffusion/v2-inference-v.yaml -o v2-inference-v.yaml
import time
from typing import List, Any

import aiohttp
import lightning as L
import torch
import os, base64, io, ldm

from pydantic import BaseModel

PROXY_URL = "https://ulhcn-01gd3c9epmk5xj2y9a9jrrvgt8.litng-ai-03.litng.ai/api/predict"


class BatchText(BaseModel):
    inputs: List[L.app.components.Text]


class BatchResponse(BaseModel):
    outputs: List[L.app.components.Image]



class DiffusionServer(L.app.components.PythonServer):
    def __init__(self, *args, **kwargs):
        super().__init__(
            input_type=BatchText,
            output_type=BatchResponse,
            *args,
            **kwargs,
        )

    def setup(self):
        cmd = "curl -C - https://pl-public-data.s3.amazonaws.com/dream_stable_diffusion/768-v-ema.ckpt -o 768-v-ema.ckpt"
        os.system(cmd)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model = ldm.lightning.LightningStableDiffusion(
            config_path="v2-inference-v.yaml",
            checkpoint_path="768-v-ema.ckpt",
            device=device,
        ).to(device)
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def predict(self, requests):
        start = time.time()
        batch_size = len(requests.inputs)
        texts = [request.text for request in requests.inputs]
        images = self._model.predict_step(
            prompts=texts,
            batch_idx=0,  # or whatever
        )
        results = []
        for image in images:
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            image_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
            results.append(image_str)
        print(f"finish predicting with batch size {batch_size} in {time.time() - start} seconds")
        return BatchResponse(outputs=[{"image": image_str} for image_str in results])


component = L.app.components.AutoScaler(
    DiffusionServer,  # The component to scale
    cloud_compute=L.CloudCompute("gpu-rtx", disk_size=80),

    # autoscaler args
    min_replicas=1,
    max_replicas=3,
    endpoint="/predict",
    scale_out_interval=0,
    scale_in_interval=300,  # 30 minutes
    max_batch_size=8,
    timeout_batching=2,
    input_type=L.app.components.Text,
    output_type=L.app.components.Image,
    cold_start_proxy=CustomColdStartProxy(proxy_url=PROXY_URL),
)

app = L.LightningApp(component)
