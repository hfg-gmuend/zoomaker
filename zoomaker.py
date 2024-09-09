import os
import subprocess
import yaml
import argparse
from huggingface_hub import hf_hub_download
import git
import requests
from tqdm import tqdm
import unicodedata
import re

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
        print(f"👋 ===> {self.yaml_file} <===")
        print(f"name: {self.data.get('name', 'N/A')}")
        print(f"version: {self.data.get('version', 'N/A')}\n")
        print(f"👇 installing resources ...")
        counter = 0;
        for group, resources in self.data["resources"].items():
            print(f"\n{group}:")

            for resource in resources:
                name = resource["name"]
                src = resource["src"]
                type = resource["type"]
                api_key = resource.get("api_key", None)
                revision = resource.get("revision", None)
                rename_to = resource.get("rename_to", None)
                install_to = os.path.abspath(resource["install_to"])
                counter += 1
                print(f"\t{counter}. {name} to {install_to}")
                os.makedirs(install_to, exist_ok=True)

                # Hugging Face Hub
                if type == "huggingface":
                    repo_id = "/".join(src.split("/")[0:2])
                    repo_filepath = "/".join(src.split("/")[2:])
                    downloaded = hf_hub_download(repo_id=repo_id, filename=repo_filepath, local_dir=install_to, revision=revision)
                    print(f"\t   size: {self._get_file_size(downloaded)}")
                    if rename_to:
                        self._rename_file(downloaded, os.path.join(install_to, rename_to))
                # Git
                elif type == "git":
                    repo_path = os.path.join(install_to, self._get_repo_name(src))
                    if rename_to:
                        print(f"\trename_to is not supported for git repos. Ignoring rename_to: {rename_to}")
                    # existing repo
                    if os.path.exists(repo_path):
                        repo = git.Repo(repo_path)
                        if revision:
                            repo.git.checkout(revision)
                            print(f"\tgit checkout revision: {repo.head.object.hexsha}")
                        else:
                            repo.remotes.origin.pull()
                            print(f"\tgit pull: {repo.head.object.hexsha}")
                    # new repo
                    else:
                        repo = git.Repo.clone_from(src, repo_path, allow_unsafe_protocols=True, allow_unsafe_options=True)
                        if revision:
                            repo.git.checkout(revision)
                            print(f"\tgit checkout revision: {repo.head.object.hexsha}")
                        else:
                            repo.remotes.origin.pull()
                            print(f"\tgit pull latest: {repo.head.object.hexsha}")

                # Download
                else:
                    filename = self._slugify(os.path.basename(src))
                    destination = os.path.join(install_to, filename)
                    destinationRenamed = os.path.join(install_to, rename_to)
                    if os.path.exists(destination) or os.path.exists(destinationRenamed):
                        print(f"\t   ℹ️ Skipping download: '{filename}' already exists")
                    else:
                        downloaded = self._download_file(src, install_to, filename, api_key)
                        print(f"\t   size: {self._get_file_size(downloaded)}")
                        if rename_to:
                            self._rename_file(downloaded, destinationRenamed)
                        if revision:
                            print(f"\trevision is not supported for download. Ignoring revision: {revision}")

        print(f"\n✅ {counter} resources installed.")

    def run(self, script_name: str):
        if script_name not in self.data["scripts"]:
            print(f"No script found with name: '{script_name}'")
            if self.data["scripts"]:
                print(f"\nAvailable scripts:")
                for script_name in self.data["scripts"]:
                    print(f"zoomaker run {script_name}")
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
        if os.path.exists(dest):
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
            # Send a GET request to the download URL
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            if bearer_token:
                headers['Authorization'] = f'Bearer {bearer_token}'
            response = requests.get(src, stream=True, allow_redirects=True, headers=headers)
            response.raise_for_status()

            # Get the filename from the Content-Disposition header
            content_disposition = response.headers.get('Content-Disposition')
            if content_disposition:
                filename = re.findall("filename=(.+)", content_disposition)[0].strip('"')
            else:
                filename = name

            # Sanitize the filename
            filename = self._slugify(filename)

            # Construct the full path for the file
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

            print(f"\t   Downloaded: {file_path}")
            print(f"\t   Size: {self._get_file_size(file_path)}")

            return file_path
        except requests.exceptions.RequestException as e:
            print(f"\t   ❌ Error downloading file: {e}")
            return None
        except IOError as e:
            print(f"\t   ❌ Error writing file: {e}")
            return None
        except Exception as e:
            print(f"\t   ❌ Unexpected error: {e}")
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
    parser.add_argument("-v", "--version", action="version", help="The current version of the zoomaker.", version="0.9.0")
    args = parser.parse_args()

    if args.command == "install":
        Zoomaker("zoo.yaml").install()
    elif args.command == "run":
        Zoomaker("zoo.yaml").run(args.script)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
