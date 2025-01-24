![zoomaker_social_keyvisual](https://github.com/hfg-gmuend/zoomaker/assets/480224/75d3d492-fe54-4711-afbf-02768bbb4033)

Zoomaker - Friendly house keeping for your AI model zoo and related resources.
========

Zoomaker is a command-line tool that helps install AI models, git repositories and run scripts.

- **single source of truth**: all resources are neatly defined in the `zoo.yaml` file
- **freeze versions**: know exactly which revision of a resources is installed at any time
- **only download once**: optimize bandwidth and cache your models locally
- **optimize disk usage**: downloaded models are cached

## 😻 TL;DR

1. Install Zoomaker `pip install zoomaker`
2. Define your resources in the `zoo.yaml` file
3. Run `zoomaker install` to install them


## 📦 Installation

```bash
pip install zoomaker
```

## 🦁 zoo.yaml Examples

Example of the `zoo.yaml` of a Stable Diffusion project with the [Automatic1111](https://github.com/AUTOMATIC1111/stable-diffusion-webui) image generator:

```yaml
name: my-automatic1111-model-zoo
version: 1.0
description: Lorem ipsum
author: your name

resources:
  image_generator:
    - name: automatic1111
      src: https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
      type: git
      revision: 22bcc7be428c94e9408f589966c2040187245d81
      install_to: ./

  models:
    - name: v2-1_768-ema-pruned
      src: stabilityai/stable-diffusion-2-1/v2-1_768-ema-pruned.safetensors
      type: huggingface
      install_to: ./stable-diffusion-webui/models/Stable-diffusion/
```

<details>
<summary>`zoo.yaml` example long</summary>

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
```
</details>

<details>
<summary>`zoo.yaml` with script snippets</summary>

Here are a few examples of how to run scripts snippets from the `zoo.yaml` file. For example for starting the Automatic1111's webui, you could setup snippets like these and then run them with `zoomaker run start_webui`. All scripts are run from the root of the project, please adjust the paths accordingly.

```yaml
scripts:
  start_webui: |
    cd .\stable-diffusion-webui && call webui.bat
```

```yaml
scripts:
  start_webui: |
    conda activate automatic1111
    cd /home/$(whoami)/stable-diffusion-webui/
    ./webui.sh --xformers --no-half
```
</details>

<details>
<summary>`zoo.yaml` with web download</summary>

```yaml
resources:
  models:
    - name: analog-diffusion-v1
      src: https://civitai.com/api/download/models/1344
      type: download
      install_to: ./stable-diffusion-webui/models/Stable-diffusion/
      rename_to: analog-diffusion-v1.safetensors
```
Please note:
The resource `type: download` can be seen as the last resort. Existing web downloads are skipped, but no other caching. It is recommended to avoid web downloads :)
</details>

## 🧮 zoo.yaml Structure

<details>
<summary>Top level:</summary>

- `name` (mandatory)
- `version`, `description`, `author`, `aliases` (optional)
- `resources` (mandatory) : `<group-name>` : `[]` (array of resources)
- `scripts` (optional) : `<script-name>`
</details>

<details>
<summary>Resource:</summary>

- `name`, `src`, `type`, `install_to` (mandatory)
- `rename_to` (optional)
- `revision` (optional), if none is defined the latest version from the main branch is downloaded
- `type` can either be `git`, `huggingface` or `download`
- `api_key` (optional) for civitai
</details>

## 🧞 Zoomaker Commands

All commands are run from the root of the project, where also your `zoo.yaml` file is located.

| Command                | Action                                           |
| :--------------------- | :----------------------------------------------- |
| `zoomaker install`          | Installs resources as defined in `zoo.yaml` |
| `zoomaker run <script_name>`    | Run CLI scripts as defined in `zoo.yaml` |
| `zoomaker --help` | Get help using the Zoomaker CLI                     |
| `zoomaker --version` | Show current Zoomaker version                     |
| `zoomaker install -f <file>` | Installs resources as defined in the specified YAML file |
| `zoomaker run -f <file> <script_name>` | Run CLI scripts as defined in the specified YAML file |

## 🤗 Hugging Face Access Token and Custom Cache Location

You might be asked for a [Hugging Face Access Token](https://huggingface.co/docs/hub/security-tokens) during `zoomaker install`. Some resources on Hugging Face require accepting the terms of use of the model. You can set your access token by running this command in a terminal. The command `huggingface-cli` is automatically shipped alongside zoomaker.

```bash
huggingface-cli login
```

You can specify a custom cache location by setting the HF_HOME environment variable. The default cache location is `~/.cache/huggingface/`.

```bash
export HF_HOME=/path/to/your/cache
zoomaker install
```

## 🙏 Acknowledgements
- Most of the internal heavy lifting is done be the [huggingface_hub library](https://huggingface.co/docs/huggingface_hub/guides/download) by Hugging Face. Thanks!
- "Zoomaker Safari Hacker Cat" cover image by Alia Tasler, based on this [OpenMoji](https://openmoji.org/library/emoji-1F431-200D-1F4BB/). Thanks!
