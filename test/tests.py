import unittest
import subprocess
from textwrap import dedent
import git
import os
import io
import shutil
import sys
from huggingface_hub import try_to_load_from_cache, _CACHED_NO_EXIST
sys.path.append('..')
from zoomaker import Zoomaker


def create_zoo(zoo_yaml):
    with open("zoo.yaml", "w") as f:
        f.write(dedent(zoo_yaml))

def delete_zoo():
    if os.path.exists("zoo.yaml"):
        os.remove("zoo.yaml")

def delete_tmp():
    dir_path = os.path.join(os.path.abspath(os.path.dirname( __file__)), "tmp")
    print(dir_path)
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path, ignore_errors=True)


class ZoomakerTestCase(unittest.TestCase):
    def setUpClass():
        suppress_text = io.StringIO()
        sys.stdout = suppress_text

    def tearDownClass():
        sys.stdout = sys.__stdout__

    def tearDown(self):
        delete_zoo()
        delete_tmp()

    def test_empty_zoo_yaml(self):
        create_zoo("")
        with self.assertRaises(Exception):
            zoomaker = Zoomaker("zoo.yaml")

    def text_missing_zoo_yaml(self):
        with self.assertRaises(Exception):
            zoomaker = Zoomaker("zoo.yaml")

    def test_invalid_zoo_yaml(self):
        create_zoo("invalid")
        with self.assertRaises(Exception):
            zoomaker = Zoomaker("zoo.yaml")

    def test_valid_zoo_yaml(self):
        create_zoo(
            """
            name: test
            resources: {}
            """
        )
        zoomaker = Zoomaker("zoo.yaml")
        self.assertEqual(zoomaker.data["name"], "test")
        self.assertEqual(zoomaker.data["resources"], {})

    def test_install_huggingface(self):
        create_zoo(
            """
            name: test
            resources:
                embeddings:
                    - name: moebius
                      src: sd-concepts-library/moebius/learned_embeds.bin
                      type: huggingface
                      install_to: ./tmp/embeddings/
                      rename_to: moebius.bin
            """
        )
        zoomaker = Zoomaker("zoo.yaml")
        zoomaker.install()
        self.assertTrue(os.path.exists("./tmp/embeddings/moebius.bin"))

    @unittest.skipIf(sys.platform.startswith("win"), "Skipping on Windows")
    def test_install_huggingface_cached(self):
        filepath = try_to_load_from_cache(
            repo_id="sd-concepts-library/moebius", filename="learned_embeds.bin")

        self.assertTrue(isinstance(filepath, str))
        self.assertTrue(os.path.exists(filepath))
        self.assertFalse(filepath == _CACHED_NO_EXIST)

    def test_install_git(self):
        create_zoo(
            """
            name: test
            resources:
                extensions:
                    - name: stable-diffusion-webui-images-browser
                      src: https://github.com/AlUlkesh/stable-diffusion-webui-images-browser.git
                      type: git
                      revision: a42c7a30181636a05815e62426d5eff4d3340529
                      install_to: ./tmp/extensions/
            """
        )
        zoomaker = Zoomaker("zoo.yaml")
        zoomaker.install()
        install_to = "./tmp/extensions/stable-diffusion-webui-images-browser"
        self.assertTrue(os.path.exists(install_to))
        repo = git.Repo(install_to)
        self.assertEqual(repo.head.commit.hexsha, "a42c7a30181636a05815e62426d5eff4d3340529")

    def test_install_download(self):
        create_zoo(
            """
            name: test
            resources:
                downloads:
                    - name: test-download
                      src: https://benedikt-gross.de/images/skull.svg
                      type: download
                      install_to: ./tmp/
                      rename_to: test-download.svg
            """
        )
        zoomaker = Zoomaker("zoo.yaml")
        zoomaker.install()
        self.assertTrue(os.path.exists("./tmp/test-download.svg"))

    def test_install_download_no_valid_filename_from_src_url_derived(self):
        create_zoo(
            """
            name: test
            resources:
                downloads:
                    - name: test-download
                      src: https://www.patreon.com/file?h=79649068&i=14281983
                      type: download
                      install_to: ./tmp/
                      rename_to: styles.csv
            """
        )
        zoomaker = Zoomaker("zoo.yaml")
        zoomaker.install()
        self.assertTrue(os.path.exists("./tmp/styles.csv"))

if __name__ == "__main__":
    unittest.main()
