# Work in progess. Please ignore.

zoomaker
========

Zoomaker is a command-line tool that helps install models, git repositories and run scripts. The information about the resources and scripts to be installed is specified in the `zoo.yaml` file.

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
