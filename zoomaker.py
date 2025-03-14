import os
import subprocess
import sys
import yaml
import argparse
from huggingface_hub import hf_hub_download
import git
import requests
from tqdm import tqdm
import unicodedata
import re
import logging

__all__ = ['Zoomaker', 'logger']

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Only add handler if none exists to avoid duplicates
if not logger.handlers:
    formatter = logging.Formatter('%(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class Zoomaker:
    def __init__(self, yaml_file: str):
        self.yaml_file = yaml_file
        with open(yaml_file, "r") as f:
            self.data = yaml.safe_load(f)
        self._check_yaml()

    def _check_yaml(self):
        if "name" not in self.data:
            raise Exception("❌ 'name' is missing in zoo.yaml")
        if "resources" not in self.data:
            raise Exception("❌ 'resources' is missing in zoo.yaml")
        for group, resources in self.data["resources"].items():
            for resource in resources:
                if "name" not in resource:
                    raise Exception("❌ Resource must have 'name' attribute")
                if "src" not in resource:
                    raise Exception("❌ Resource must have 'src' attribute")
                if "type" not in resource:
                    raise Exception("❌ Resource must have 'type' attribute")
                if "install_to" not in resource:
                    raise Exception("❌ Resource must have 'install_to' attribute")
                type = resource["type"]
                if type not in ["huggingface", "git", "download"]:
                    raise Exception(f"❌ Unknown resource type: {type}")

    def install(self):
        logger.info(f"👋 ===> {self.yaml_file} <===")
        logger.info(f"name: {self.data.get('name', 'N/A')}")
        logger.info(f"version: {self.data.get('version', 'N/A')}\n")
        logger.info(f"👇 installing resources ...")
        counter = 0
        for group, resources in self.data["resources"].items():
            logger.info(f"\n{group}:")

            for resource in resources:
                src = resource["src"]
                name = resource["name"] if "name" in resource else os.path.basename(src)
                type = resource["type"]
                api_key = resource.get("api_key", None)
                revision = resource.get("revision", None)
                rename_to = resource.get("rename_to", None)
                install_to = os.path.abspath(resource["install_to"])
                counter += 1
                logger.info(f"\t{counter}. {name} to {install_to}")
                os.makedirs(install_to, exist_ok=True)

                # Hugging Face Hub
                if type == "huggingface":
                    repo_id = "/".join(src.split("/")[0:2])
                    repo_filepath = "/".join(src.split("/")[2:])
                    repo_filename = os.path.basename(repo_filepath)
                    destination = os.path.join(install_to, repo_filename)
                    destinationRenamed = rename_to and os.path.join(install_to, rename_to)
                    # logger.info(f"\t   repo_id: {repo_id}")
                    # logger.info(f"\t   repo_filepath: {repo_filepath}")
                    # logger.info(f"\t   repo_filename: {repo_filename}")
                    # logger.info(f"\t   destination: {destination}")
                    # logger.info(f"\t   destinationRenamed: {destinationRenamed}")
                    if destinationRenamed and os.path.exists(destinationRenamed):
                        logger.info(f"\t   ℹ️  Skipping download: '{repo_filename}' already exists")
                    else:
                        downloaded = hf_hub_download(repo_id=repo_id, filename=repo_filepath, local_dir=install_to, revision=revision)
                        logger.info(f"\t   size: {self._get_file_size(downloaded)}")
                        if rename_to:
                            self._rename_file(downloaded, destinationRenamed)
                            logger.info(f"\t   Downloaded and Renamed to: {destinationRenamed}")
                        else:
                            self._rename_file(downloaded, destination)
                            logger.info(f"\t   Downloaded to: {destination}")

                # Git
                elif type == "git":
                    repo_path = os.path.join(install_to, self._get_repo_name(src))
                    if rename_to:
                        logger.warning(f"\trename_to is not supported for git repos. Ignoring rename_to: {rename_to}")
                    # existing repo
                    if os.path.exists(repo_path):
                        repo = git.Repo(repo_path)
                        if revision:
                            repo.git.checkout(revision)
                            logger.info(f"\tgit checkout revision: {repo.head.object.hexsha}")
                        else:
                            repo.remotes.origin.pull()
                            # Update submodules recursively
                            repo.git.submodule('update', '--init', '--recursive')
                            logger.info(f"\tgit pull: {repo.head.object.hexsha}")
                            logger.info(f"\tsubmodules updated recursively")
                    # new repo
                    else:
                        repo = git.Repo.clone_from(src, repo_path, allow_unsafe_protocols=True, allow_unsafe_options=True, recursive=True)
                        if revision:
                            repo.git.checkout(revision)
                            # Update submodules recursively after checkout
                            repo.git.submodule('update', '--init', '--recursive')
                            logger.info(f"\tgit checkout revision: {repo.head.object.hexsha}")
                            logger.info(f"\tsubmodules updated recursively")
                        else:
                            # Already cloned recursively, but still need to update submodules after pull
                            repo.remotes.origin.pull()
                            repo.git.submodule('update', '--init', '--recursive')
                            logger.info(f"\tgit pull latest: {repo.head.object.hexsha}")
                            logger.info(f"\tsubmodules updated recursively")

                # Download
                else:
                    filename = self._slugify(os.path.basename(src))
                    logger.info(f"\t   src: {src}")
                    logger.info(f"\t   filename: {filename}")
                    destination = os.path.join(install_to, filename)
                    destinationRenamed = rename_to and os.path.join(install_to, rename_to)
                    if os.path.exists(destination) or destinationRenamed and os.path.exists(destinationRenamed):
                        logger.info(f"\t   ℹ️ Skipping download: '{filename}' already exists")
                    else:
                        downloaded = self._download_file(src, install_to, filename, api_key)
                        if downloaded:
                            logger.info(f"\t   Size: {self._get_file_size(downloaded)}")
                            logger.info(f"\t   Downloaded to: {downloaded}")
                            if rename_to:
                                self._rename_file(downloaded, destinationRenamed)
                                logger.info(f"\t   Renamed to: {destinationRenamed}")
                        else:
                            logger.warning(f"\t   ❌ Download failed.")
                            return
                        if revision:
                            logger.warning(f"\trevision is not supported for download. Ignoring revision: {revision}")

        logger.info(f"\n✅ {counter} resources installed.")

    def run(self, script_name: str):
        if script_name not in self.data["scripts"]:
            logger.info(f"No script found with name: '{script_name}'")
            if self.data["scripts"]:
                logger.info(f"\nAvailable scripts:")
                for script_name in self.data["scripts"]:
                    logger.info(f"zoomaker run {script_name}")
            return
        script_string = self.data["scripts"][script_name]
        subprocess.check_call(script_string, shell=True)

    def _get_repo_name(self, src: str):
        if src.endswith(".git"):
            return os.path.basename(src).replace(".git", "")
        else:
            return os.path.basename(src)

    def _rename_file(self, src, dest):
        # remove dest if exists due to os.rename limitation in Windows
        if sys.platform.startswith("win") and os.path.exists(dest):
            os.remove(dest)
            os.rename(src, dest)
        else:
            os.rename(src, dest)

    def _get_file_size(self, path):
        size = os.stat(path).st_size
        if size < 1024:
            return f"{size} bytes"
        elif size < pow(1024, 2):
            return f"{round(size/1024, 2)} KB"
        elif size < pow(1024, 3):
            return f"{round(size/(pow(1024,2)), 2)} MB"
        elif size < pow(1024, 4):
            return f"{round(size/(pow(1024,3)), 2)} GB"

    def _download_file(self, src, install_to, name, bearer_token = None):
        try:
            # Send HEAD request first to check headers without downloading
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.134 Safari/538.36'
            }
            if bearer_token:
                headers['Authorization'] = f'Bearer {bearer_token}'

            # Now do the actual download
            response = requests.get(src, stream=True, allow_redirects=True, headers=headers)
            response.raise_for_status()

            # Check if response is HTML
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/html' in content_type or 'application/xhtml+xml' in content_type:
                logger.error(f"\t   ❌ Received HTML response instead of file. If you are downloading from civitai you will need to add api_key: YOUR_CIVITAI_API_KEY to the resource.")
                return None

            # Rest of the method...
            content_disposition = response.headers.get('Content-Disposition')
            logger.info(f"\t   Content-Disposition: {content_disposition}")
            if content_disposition:
                filename = re.findall("filename=(.+)", content_disposition)[0].strip('"')
            else:
                filename = name
                filename = self._slugify(filename)

            # Rest of the download code...
            file_path = os.path.join(install_to, filename)

            # Download the file with progress bar
            total_size = int(response.headers.get('content-length', 0))
            with open(file_path, 'wb') as file, tqdm(
                desc=filename,
                total=total_size,
                unit='iB',
                unit_scale=True,
                unit_divisor=1024,
            ) as progress_bar:
                for data in response.iter_content(chunk_size=1024):
                    size = file.write(data)
                    progress_bar.update(size)

            logger.info(f"\t   Downloaded: {file_path}")

            return file_path
        except requests.exceptions.RequestException as e:
            logger.error(f"\t   ❌ Error downloading file: {e}")
            return None
        except IOError as e:
            logger.error(f"\t   ❌ Error writing file: {e}")
            return None
        except Exception as e:
            logger.error(f"\t   ❌ Unexpected error: {e}")
            return None

    def _slugify(self, value, allow_unicode=False):
        """
        Makes a filename safe for usage on all filesystems.

        Taken from https://github.com/django/django/blob/master/django/utils/text.py
        Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
        dashes to single dashes. Remove characters that aren't alphanumerics,
        underscores, or hyphens. Convert to lowercase. Also strip leading and
        trailing whitespace, dashes, and underscores.
        """
        value = str(value)
        if allow_unicode:
            value = unicodedata.normalize('NFKC', value)
        else:
            value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
        value = re.sub(r'[^\w\s-]', '', value.lower())
        return re.sub(r'[-\s]+', '-', value).strip('-_')

def main():
    parser = argparse.ArgumentParser(description="Install models, git repos and run scripts defined in the zoo.yaml file.")
    parser.add_argument("command", nargs="?", choices=["install", "run"], help="The command to execute.")
    parser.add_argument("script", nargs="?", help="The script name to execute.")
    parser.add_argument("-f", "--file", default="zoo.yaml", help="The YAML file to use.")
    parser.add_argument("-v", "--version", action="version", help="The current version of the zoomaker.", version="0.10.2")
    args = parser.parse_args()

    if args.command == "install":
        Zoomaker(args.file).install()
    elif args.command == "run":
        Zoomaker(args.file).run(args.script)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
