# nlp
It is ***heavily*** recommended to run the project on Linux (tested on Ubuntu 25.10) for easier dependencies management.
The project has been tested to function on a NVIDIA GeForce RTX 3080 GPU. If for some reason the project seems to be failing at the DiffSinger stage of the pipeline (e.g., a CUDA related-error) it is probably linked to the GPU being used that requires specific CUDA version.
To reproduce:
- Clone/download the repo.
- This project uses the Cerebras Inference API for fast LLM inference. Please create a free account at https://www.cerebras.ai/ and then generate an API key on https://cloud.cerebras.ai/
Our project will access it via the CEREBRAS_API_KEY environment variable, please set this variable's value to your generated API key.
- Inside the project folder, sync the dependencies using 'uv sync', this will also automatically create your project environment.
- The DiffSinger pipeline works as a "subprocess" in our project. It requires a specific Python version (3.8) and dependencies. You can install those and create the related project environment by running './external/DiffSinger/venvdiff/bin/pip install -r external/DiffSinger/requirements.txt' in the terminal (still in the project folder).
- The project requires manually setting the DiffSinger project path and python venv for backward compatibility reasons. For example, if all guidelines were followed until now, you could run something like this in your terminal:
  export DS_PROJECT_ROOT="/home/USERNAME/PycharmProjects/nlp/external/DiffSinger"
  export DS_PYTHON_PATH="/home/USERNAME/PycharmProjects/nlp/external/DiffSinger/venvdiff/bin/python3.8"
  (while changing the "/home/USERNAME/PycharmProjects" depending on where you have the project located on your computer)
- The DiffSinger pipeline requires some pretrained models in order to work. Please download them here:
https://github.com/MoonInTheRiver/DiffSinger/releases/download/pretrain-model/0109_hifigan_bigpopcs_hop128.zip (pre-trained model of HifiGAN-Singing which is specially designed for SVS with NSF mechanism)
https://github.com/MoonInTheRiver/DiffSinger/releases/download/pretrain-model/0102_xiaoma_pe.zip (pre-trained vocoder)
https://github.com/MoonInTheRiver/DiffSinger/releases/download/pretrain-model/0228_opencpop_ds100_rel.zip (pre-trained model of DiffSinger)
Once you have downloaded all three zip files, place them inside the folder 'external/checkpoints' and extract them in there. Then delete the now useless .zip files.
- Once this has been done you should be able to run the project. For instance, running 'python main.py --lyrics 小酒窝长睫毛是你最美的记号' in your terminal while in the root folder of the project generates an entire song based on the given lyrics. Please look inside main.py in order to see all available arguments you can use.
