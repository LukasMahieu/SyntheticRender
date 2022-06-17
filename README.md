# Synthetic Rendering

This module allows you to create your own synthetic datasets as long as you have 3D models available of the objects you want to render.
Its main purpose is to use these synthetically generated datasets as input for object detection models. 
On top of rendering the images, the annotations (in COCO format) will be rendered as well, so you don't have to go through the trouble of manually annotating your dataset.

## How it works
Using the BlenderProc package (https://github.com/DLR-RM/BlenderProc, which uses the Blender API), we will generate a room and randomly drop a sample of target objects and distractor objects in this room using realistic physics rendering. 

Next, we take N different camera positions from this single scene, render N final images, and output the associated annotations to the /output folder. This process is repeated for the specified amount of scenes you'd like to render. 

## Requirements

To be able to run this module, you only need to have *docker* installed.

Additionally, you need to create your own 3D models in *.obj* format (with *.mtl* textures if you have them) and download distractor object models from BOP: Benchmark for 6D object Pose Estimation (https://bop.felk.cvut.cz/datasets/).  
You only need the 'Base archive' and 'Object models' from the LM (linemod) and T-LESS datasets.

Clone this repository and place these files under the /resources folder, which should be structured as follows:
```
- /resources
  - config.yml
  - camera_positions
  - /my_models
    - model1.obj
    - model1.mtl
    - model2.obj
    - model2.mtl
    - ...  
  - /bop_data
    - /lm
      - /models
        - models_info.json
        - obj_000001.ply
        - ...
      - camera.json
      - dataset_info.md
      - test_targets_bop19.json 
    - /tless
      - /models_cad
        - models_info.json
        - obj_000001.ply
        - ...
      -  camera_primesense.json
      -  dataset_info.md
      -  test_targets_bop19.json
```
Additionaly, change the config.yml under /resources to point towards the correctly named paths, and change other properties as pleased.

## How to run

**1. Build the docker image**
```
docker build -t synthetic_render .
```
This might take a while, since blender and other packages will be installed, while also downloading a sample of background textures which will be randomly used to create the texture of the room itself.

The dockerfile uses the python script which starts the rendering as the ENTRYPOINT, which makes it easier to run the container in *detached (-d)* mode.

If you want more control and run the container interactively, just change the entrypoint of the Dockerfile to */bin/bash*

**2. Run the container**

To run the container, you need to specify three things:
1. Point a volume from the location of the _config.yml_ file on your machine towards the correct location inside the container which is */synthetic_data/resources/config.yml* (you need to use absolute paths)
2. Create an empty /output folder and point a volume towards the correct path inside the container which is */synthetic_data/output/*. This is where the rendered images/annotations will be saved.
3. If you want to use your GPUs for rendering, don't forget to add the *--gpus all* flag. You can also render on the CPU alone, but that will be much slower

Example:
```
docker run -d -v "/home/user/.../synthetic_rendering/resources/config.yml:/synthetic_data/resources/config.yml" -v "/home/user/.../synthetic_rendering/output:/synthetic_data/output/" --gpus all synthetic_gen
```
