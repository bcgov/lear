# Test Data tosupport the LEAR project

## Setup
Note: This is targeted at VSCode, although it'll work in other IDEs that support **Remote Development**

1. Install [VSCode](https://code.visualstudio.com/)
1. Install [Docker](https://www.docker.com/)
1. Install [Remote Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

Note: Docker will need to be setup in your Linux partition, so default for Mac, WSL for Windows and No Worries for Linux users.

## Starting the devcontainer
1. Open the ```lear/tests/data``` in VSCode
1. When prompted to _Re-Open_ theproject as a _devcontainer_, click on **Yes**

## Starting the server
Once the devcontainer has built, open a _New_ _Terminal_ in VSCode
Start the service by running in the terminal
```bash
./run.sh
```
The output will look something like this:
```
[I 22:49:49.784 NotebookApp] Use Control-C to stop this server and shut down all kernels (twice to skip confirmation).
[C 22:49:49.793 NotebookApp] 
    
    To access the notebook, open this file in a browser:
        file:///home/jovyan/.local/share/jupyter/runtime/nbserver-380-open.html
    Or copy and paste one of these URLs:
        http://d94578af72d9:8888/?token=7a1e0ca11ffc47d81d5ce0d053292f6aa01c95ed237df4f4
     or http://127.0.0.1:8888/?token=7a1e0ca11ffc47d81d5ce0d053292f6aa01c95ed237df4f4
```
Open a browser by \<cmd> or \<control> clicking on the ``` http://127.0.0.1:8888/?thekeytotheserver``` in the output

## Using
You may need to port-forward or give access to the database, or setup the configuration in ```default-bcr-business-setup-TEST.ipynb``` file depenging on what you are trying to do next.
