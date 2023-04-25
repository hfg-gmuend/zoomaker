import os
import subprocess
import yaml
import argparse
from huggingface_hub import hf_hub_download
import git
import requests
from tqdm import tqdm

class Zoomaker:
    def __init__(self, yaml_file: str):
        self.yaml_file = yaml_file
        with open(yaml_file, "r") as f:
            self.data = yaml.safe_load(f)

    def install(self):
        print(f"👋 -- {self.yaml_file} --")
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
                    if rename_to:
                        os.rename(downloaded, os.path.join(install_to, rename_to))
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
                        repo = git.Repo.clone_from(src, repo_path, no_checkout=True, allow_unsafe_protocols=True, allow_unsafe_options=True)
                        if revision:
                            repo.git.checkout(revision)
                            print(f"\tgit checkout revision: {repo.head.object.hexsha}")
                        else:
                            repo.remotes.origin.pull()
                            print(f"\tgit pull latest: {repo.head.object.hexsha}")
                # Download
                elif type == "donwload":
                    downloaded = self._download_file(src, os.path.join(install_to, os.path.basename(src)))
                    if rename_to:
                        os.rename(downloaded, os.path.join(install_to, rename_to))
                    if revision:
                        print(f"\trevision is not supported for download. Ignoring revision: {revision}")
                # Unknown
                else:
                    print(f"\tUnknown resource type: {type}")

        print(f"\n✅ Installation of {counter} resources completed.")

    def run(self, script_name: str):
        if script_name not in self.data["scripts"]:
            print(f"No script found with name: {script_name}")
            return
        script_string = self.data["scripts"][script_name]
        subprocess.check_call(script_string, shell=True)

    def _get_repo_name(self, src: str):
        if src.endswith(".git"):
            return os.path.basename(src).replace(".git", "")
        else:
            return os.path.basename(src)

    def _download_file(self, url, filename):
        response = requests.get(url, stream=True)
        total_size_in_bytes = int(response.headers.get('content-length', 0))
        block_size = 1024
        progress_bar = tqdm(desc="\tdownloading", total=total_size_in_bytes, unit='iB', unit_scale=True, ncols=100)
        with open(filename, 'wb') as file:
            for data in response.iter_content(block_size):
                progress_bar.update(len(data))
                file.write(data)
        progress_bar.close()
        if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
            print("Error: Failed to download the complete file.")
            return None
        return filename


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Install models, git repos and run scripts defined in the zoo.yaml file")
    parser.add_argument("command", choices=["install", "run"], help="The command to execute.")
    parser.add_argument("script", nargs="?", help="The script name to execute.")
    parser.add_argument("-v", "--version", action='version', help="The current version of the zoomaker.", version="0.1.0")
    args = parser.parse_args()

    zoomaker = Zoomaker("zoo.yaml")
    if args.command == "install":
        zoomaker.install()
    elif args.command == "run":
        zoomaker.run(args.script)
