# Available tests:
# - test_empty_zoo_yaml
# - text_missing_zoo_yaml
# - test_invalid_zoo_yaml
# - test_valid_zoo_yaml
# - test_install_civitai
# - test_install_huggingface
# - test_install_huggingface_cached
# - test_install_git
# - test_install_download
# - test_install_download_no_valid_filename_from_src_url_derived

import unittest
import subprocess
from textwrap import dedent
import git
import time
import os
import io
import shutil
import sys
import logging
from huggingface_hub import try_to_load_from_cache, _CACHED_NO_EXIST

# Ensure we use the local version
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from zoomaker import Zoomaker, logger
from unittest.runner import TextTestRunner
from unittest.runner import TextTestResult

class RealTimeTestResult(TextTestResult):
    def startTest(self, test):
        self._started_at = time.time()
        super().startTest(test)

    def addSuccess(self, test):
        super().addSuccess(test)
        self.stream.write('\n')
        self.stream.flush()

def create_zoo(zoo_yaml):
    with open("zoo.yaml", "w") as f:
        f.write(dedent(zoo_yaml))

def delete_zoo():
    if os.path.exists("zoo.yaml"):
        os.remove("zoo.yaml")

def delete_tmp():
    dir_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "tmp")
    logger.info(dir_path)
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path, ignore_errors=True)

class ZoomakerTestCase(unittest.TestCase):
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
       

    @unittest.skip("Large file")
    def test_install_huggingface_large(self):
        create_zoo(
            """
            name: test
            resources:
                embeddings:
                    - name: deep1
                      src: mcmonkey/cosmos-1.0/Cosmos-1_0-Diffusion-7B-Text2World.safetensors
                      type: huggingface
                      install_to: ./tmp/test/
            """
        )
        zoomaker = Zoomaker("zoo.yaml")
        zoomaker.install()
        self.assertTrue(os.path.exists("./tmp/test/Cosmos-1_0-Diffusion-7B-Text2World.safetensors"))
    
    def test_install_huggingface(self):
        create_zoo(
            """
            name: test
            resources:
                embeddings:
                    - name: deep1
                      src: deepseek-ai/DeepSeek-R1/figures/benchmark.jpg
                      type: huggingface
                      install_to: ./tmp/test/
            """
        )
        zoomaker = Zoomaker("zoo.yaml")
        zoomaker.install()
        self.assertTrue(os.path.exists("./tmp/test/benchmark.jpg"))

    #@unittest.skip("skip")
    def test_install_huggingface_rename(self):
        create_zoo(
            """
            name: test
            resources:
                embeddings:
                    - name: deep2
                      src: deepseek-ai/DeepSeek-R1/figures/benchmark.jpg
                      type: huggingface
                      install_to: ./tmp/test/
                      rename_to: benchmark2.jpg
            """
        )
        zoomaker = Zoomaker("zoo.yaml")
        zoomaker.install()
        self.assertTrue(os.path.exists("./tmp/test/benchmark2.jpg"))

    @unittest.skipIf(sys.platform.startswith("win"), "Skipping on Windows")
    def test_install_huggingface_cached(self):
        filepath = try_to_load_from_cache(
            repo_id="sd-concepts-library/moebius", filename="learned_embeds.bin")

        if filepath is None:
            self.skipTest("File not found in cache")

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
                      src: https://raw.githubusercontent.com/thundercat71/Automatic1111-Fooocus-Styles/main/styles.csv
                      type: download
                      install_to: ./tmp/
                      rename_to: styles.csv
            """
        )
        zoomaker = Zoomaker("zoo.yaml")
        zoomaker.install()
        self.assertTrue(os.path.exists("./tmp/styles.csv"))

    # skip this test as it requires an API key
    @unittest.skip("Requires API key")
    def test_install_civitai_derived_filename_from_api(self):
        custom_yaml_file = "custom_zoo.yaml"
        with open(custom_yaml_file, "w") as f:
            f.write(dedent(
                """
                name: test
                resources:
                    models:
                        - name: test_model
                          src: https://civitai.com/api/download/models/369718?type=Model&format=PickleTensor
                          type: download
                          api_key: 65f5bdb2332ef1bab3b5c156dd85b6fa
                          install_to: ./tmp/models/
                """
            ))
        zoomaker = Zoomaker(custom_yaml_file)
        zoomaker.install()
        self.assertTrue(os.path.exists("./tmp/models/CS-MNC.pt"))
        os.remove(custom_yaml_file)

    @unittest.skip("Large file")
    def test_install_civitai_derived_filename(self):
        custom_yaml_file = "custom_zoo.yaml"
        with open(custom_yaml_file, "w") as f:
            f.write(dedent(
                """
                name: test
                resources:
                    models:
                        - name: test_model
                          src: https://civitai.com/api/download/models/712448?type=Model&format=SafeTensor&size=pruned&fp=fp16
                          type: download
                          install_to: ./tmp/models/
                """
            ))
        zoomaker = Zoomaker(custom_yaml_file)
        zoomaker.install()
        self.assertTrue(os.path.exists("./tmp/models/realDream_15SD15.safetensors"))
        os.remove(custom_yaml_file)
    
    @unittest.skip("Large file")
    def test_install_civitai_rename(self):
        custom_yaml_file = "custom_zoo.yaml"
        with open(custom_yaml_file, "w") as f:
            f.write(dedent(
                """
                name: test
                resources:
                    models:
                        - name: test_model
                          src: https://civitai.com/api/download/models/712448?type=Model&format=SafeTensor&size=pruned&fp=fp16
                          type: download
                          #api_key: 65f5bdb2332ef1bab3b5c156dd85b6f
                          install_to: ./tmp/models/
                          rename_to: test.zip
                """
            ))
        zoomaker = Zoomaker(custom_yaml_file)
        zoomaker.install()
        self.assertTrue(os.path.exists("./tmp/models/test.zip"))
        os.remove(custom_yaml_file)

if __name__ == "__main__":
    # Create a test suite
    suite = unittest.TestSuite()

    # If command-line arguments are provided, run only those tests
    if len(sys.argv) > 1:
        for test_name in sys.argv[1:]:
            suite.addTest(ZoomakerTestCase(test_name))
    else:
        # If no arguments, run all tests
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(ZoomakerTestCase)

    # Run the tests with real-time output
    runner = TextTestRunner(verbosity=2, resultclass=RealTimeTestResult)
    runner.run(suite)