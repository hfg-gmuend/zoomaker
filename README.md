# Work in progress. Please ignore.

zoomaker
========

Zoomaker is a command-line tool that helps install models, git repositories and run scripts. The information about the resources and scripts to be installed is specified in the `zoo.yaml` file.

## zoo.yaml example

```yaml
name: my-automatic1111-model-zoo
version: 1.0
description: Lorem ipsum
author: your name

aliases:
  image_generator: &image_generator ./
  models: &models ./stable-diffusion-webui/models/Stable-diffusion/
  controlnet: &controlnet ./stable-diffusion-webui/models/ControlNet/
  embeddings: &embeddings ./stable-diffusion-webui/embeddings/
  extensions: &extensions ./stable-diffusion-webui/extensions/

resources:
  image_generator:
    - name: automatic1111
      src: https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
      type: git
      revision: 22bcc7be428c94e9408f589966c2040187245d81
      install_to: *image_generator

  models:
    - name: v1-5-pruned-emaonly
      src: runwayml/stable-diffusion-v1-5/v1-5-pruned-emaonly.safetensors
      type: huggingface
      install_to: *models
    - name: analog-diffusion-v1
      src: https://civitai.com/api/download/models/1344
      type: donwload
      install_to: *models
      rename_to: analog-diffusion-v1.safetensors

  controlnet:
    - name: control_sd15_canny
      src: lllyasviel/ControlNet/models/control_sd15_canny.pth
      type: huggingface
      install_to: *controlnet

  embeddings:
    - name: midjourney-style
      src: sd-concepts-library/midjourney-style/learned_embeds.bin
      type: huggingface
      install_to: *embeddings
      rename_to: midjourney-style.bin
    - name: moebius
      src: sd-concepts-library/moebius/learned_embeds.bin
      type: huggingface
      install_to: *embeddings
      rename_to: moebius.bin

  extensions:
    - name: sd-webui-tunnels
      src: https://github.com/Bing-su/sd-webui-tunnels.git
      type: git
      install_to: *extensions

scripts:
  start: |
    conda init bash
    source ~/.bashrc
    conda activate automatic1111
    cd /home/$(whoami)/stable-diffusion-webui/
    ./webui.sh --no-half --listen

```

## Installation

```
pip install zoomaker
```

## Usage

```
zoomaker <command> <script>
```

where `<command>` is one of `install` or `run`, and `<script>` is the name of the script to execute.

- To install the resources defined in the `zoo.yaml` file, run:

  ```
  zoomaker install
  ```

- To run a script defined in the `zoo.yaml` file, run:

  ```
  zoomaker run <script_name>
  ```
