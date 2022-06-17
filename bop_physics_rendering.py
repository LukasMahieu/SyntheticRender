import blenderproc as bproc
import argparse
import os
import numpy as np
import random
import yaml
from contextlib import contextmanager
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--config_path', default='resources/config.yml', help="Path to the config.yml file")
args = parser.parse_args()

bproc.init()

# Load configs
with open(args.config_path, 'r') as file:
    configs = yaml.safe_load(file)
    
print(configs)

# load all objects initially

available_models = [model for model in os.listdir(configs['paths']['lablight_models_path']) if model.endswith('.obj')]
loaded_models = []

assert int(configs['n_objects']) <= len(available_models), 'Not enough .obj models found to sample from using specified n samples'

for obj in available_models:
    if obj.endswith('.obj'):
        loaded_models.extend(bproc.loader.load_obj(os.path.join(configs['paths']['lablight_models_path'], obj)))

# load all distractor bop objects
distractor_bop_objs = bproc.loader.load_bop_objs(bop_dataset_path = os.path.join(configs['paths']['bop_parent_path'], 'lm'),
                                    mm2m = True)

distractor_bop_objs += bproc.loader.load_bop_objs(bop_dataset_path = os.path.join(configs['paths']['bop_parent_path'], 'tless'),
                                    mm2m = True)

# load BOP datset intrinsics
bproc.loader.load_bop_intrinsics(bop_dataset_path = os.path.join(configs['paths']['bop_parent_path'], 'lm'))

# Load all materials
materials = bproc.material.collect_all()

# set shading and physics properties and randomize PBR materials
for obj in (distractor_bop_objs):
    obj.set_shading_mode('auto')
    obj.hide(True)
    obj.set_cp("category_id", 0) # If 0, this gets treated as background

for j, obj in enumerate(loaded_models):
    obj.set_shading_mode('auto')
    obj.hide(True)
    obj.set_cp("category_id", j+1)

# create room
room_planes = [bproc.object.create_primitive('PLANE', scale=[2, 2, 1]),
            bproc.object.create_primitive('PLANE', scale=[2, 2, 1], location=[0, -2, 2], rotation=[-1.570796, 0, 0]),
            bproc.object.create_primitive('PLANE', scale=[2, 2, 1], location=[0, 2, 2], rotation=[1.570796, 0, 0]),
            bproc.object.create_primitive('PLANE', scale=[2, 2, 1], location=[2, 0, 2], rotation=[0, -1.570796, 0]),
            bproc.object.create_primitive('PLANE', scale=[2, 2, 1], location=[-2, 0, 2], rotation=[0, 1.570796, 0])]
for plane in room_planes:
    plane.enable_rigidbody(False, collision_shape='BOX', friction = 100.0, linear_damping = 0.99, angular_damping = 0.99)

# Initialize Light configs
light_plane = bproc.object.create_primitive('PLANE', scale=[3, 3, 1], location=[0, 0, 10])
light_plane.set_name('light_plane')
light_plane_material = bproc.material.create('light_material')

light_point = bproc.types.Light()

# Load CC Texture 
cc_textures = bproc.loader.load_ccmaterials(configs['paths']['cc_textures_path'])

# Define a function that samples 6-DoF poses
def sample_pose_func(obj: bproc.types.MeshObject):
    min = np.random.uniform([-0.3, -0.3, 0.0], [-0.2, -0.2, 0.0])
    max = np.random.uniform([0.2, 0.2, 0.4], [0.3, 0.3, 0.6])
    obj.set_location(np.random.uniform(min, max))
    obj.set_rotation_euler(bproc.sampler.uniformSO3())
    
# activate depth rendering without antialiasing and set amount of samples for color rendering
bproc.renderer.enable_depth_output(activate_antialiasing=False)
bproc.renderer.enable_normals_output()
bproc.renderer.set_max_amount_of_samples(50)
        
for i in range(configs['scenes_to_sample']):
    print(f'RENDERING SCENE {i+1} OF {configs["scenes_to_sample"]}')
    # Sample objects for this scene 
    if configs['sample_n_object']:
        n_objects_to_render = random.randint(1,  int(configs['n_objects']))
    else:
        n_objects_to_render = int(configs['n_objects'])

    sampled_target_objs = list(np.random.choice(loaded_models, size=n_objects_to_render, replace=False))
    sampled_distractor_bop_objs = list(np.random.choice(distractor_bop_objs, size=int(configs['n_distractors']), replace=False))
    
    # Randomize materials
    old_colours_dict = {}
    for obj in sampled_target_objs:
        old_colours_dict[obj] = [] # Keep track of og colours
        for mat in obj.get_materials():
            # Sample around loaded object's colours
            old_colour = [*mat.get_principled_shader_value("Base Color")]
            old_colours_dict[obj].append(old_colour)
            changerate = np.random.uniform(0.6,1.4)
            new_colour = list(np.array([*mat.get_principled_shader_value("Base Color")][:3])*changerate)
            mat.set_principled_shader_value("Base Color", new_colour + [1]) 
            mat.set_principled_shader_value("Roughness", np.random.uniform(0.4, 0.6))
            mat.set_principled_shader_value("Specular", np.random.uniform(0.3, 0.7))
            mat.set_principled_shader_value("Metallic", random.uniform(0.4, 0.6))
        obj.enable_rigidbody(True, mass=1.0, friction = 100.0, linear_damping = 0.99, angular_damping = 0.99)
        obj.hide(False)
        
    for obj in (sampled_distractor_bop_objs):
        mat = obj.get_materials()[0]
        mat.set_principled_shader_value("Base Color", [np.random.uniform(0, 1), np.random.uniform(0, 1), np.random.uniform(0, 1), 1]) 
        mat.set_principled_shader_value("Roughness", np.random.uniform(0.1, 0.9))
        mat.set_principled_shader_value("Specular", np.random.uniform(0.1, 0.9))
        mat.set_principled_shader_value("Metallic", random.uniform(0.1, 0.9))
        obj.enable_rigidbody(True, mass=1.0, friction = 100.0, linear_damping = 0.99, angular_damping = 0.99)
        obj.hide(False)
        
    # Randomize light sources
    light_plane_material.make_emissive(emission_strength=np.random.uniform(3,6), 
                                    emission_color=np.random.uniform([0.5, 0.5, 0.5, 1.0], [1.0, 1.0, 1.0, 1.0]))    
    light_plane.replace_materials(light_plane_material)
    light_energy_value = random.uniform(configs['light']['min_energy'], configs['light']['max_energy'])
    light_point.set_energy(light_energy_value)
    light_point.set_color(np.random.uniform([0.5,0.5,0.5],[1,1,1]))
    location = bproc.sampler.shell(center = [0, 0, 0], radius_min = 1, radius_max = 1.5,
                            elevation_min = 5, elevation_max = 89, uniform_volume = False)
    light_point.set_location(location)
    
    # Random CC textures
    random_cc_texture = np.random.choice(cc_textures)
    for plane in room_planes:
        plane.replace_materials(random_cc_texture)
    
    # Sample object poses and check collisions 
    bproc.object.sample_poses(objects_to_sample = sampled_target_objs + sampled_distractor_bop_objs,
                            sample_pose_func = sample_pose_func, 
                            max_tries = 1000)
            
    # Physics Positioning
    bproc.object.simulate_physics_and_fix_final_poses(min_simulation_time=3,
                                                    max_simulation_time=10,
                                                    check_object_interval=1,
                                                    substeps_per_frame = 20,
                                                    solver_iters=25)

    # BVH tree used for camera obstacle checks
    bop_bvh_tree = bproc.object.create_bvh_tree_multi_objects(sampled_target_objs + sampled_distractor_bop_objs)

    poses = 0
    while poses < configs['samples_per_scene']:
        # Sample location
        location = bproc.sampler.shell(center = [0, 0, 0],
                                radius_min = configs['camera']['radius_min'],
                                radius_max = configs['camera']['radius_max'],
                                elevation_min = configs['camera']['elevation_min'],
                                elevation_max = configs['camera']['elevation_max'],
                                uniform_volume = False)
        # Determine point of interest in scene as the object closest to the mean of a subset of objects (focus on one object for now)
        poi = bproc.object.compute_poi(np.random.choice(sampled_target_objs, size=1))
        # Compute rotation based on vector going from location towards poi
        rotation_matrix = bproc.camera.rotation_from_forward_vec(poi - location, inplane_rot=np.random.uniform(-0.7854, 0.7854))
        # Add homog cam pose based on location an rotation
        cam2world_matrix = bproc.math.build_transformation_mat(location, rotation_matrix)
        
        # Check that obstacles are at least 0.1 meter away from the camera and make sure the view interesting enough
        if bproc.camera.perform_obstacle_in_view_check(cam2world_matrix, {"min": 0.1}, bop_bvh_tree):
            # Persist camera pose
            bproc.camera.add_camera_pose(cam2world_matrix, frame=poses)
            poses += 1
            print(f'Rendering pose {poses}')


    
    # define the camera resolution
    bproc.camera.set_resolution(550, 550)

    # render the whole pipeline
    data = bproc.renderer.render()

    # Render segmentation images
    seg_data = bproc.renderer.render_segmap(map_by=["instance", "class"])

    # Write data to coco file
    bproc.writer.write_coco_annotations(os.path.join(configs['paths']['output_dir'], 'coco_data'),
                            instance_segmaps=seg_data["instance_segmaps"],
                            instance_attribute_maps=seg_data["instance_attribute_maps"],
                            colors=data["colors"],
                            append_to_existing_output=True,
                            mask_encoding_format='polygon')

    
    # Hide objects again
    for obj in (sampled_target_objs + sampled_distractor_bop_objs):      
        obj.disable_rigidbody()
        obj.hide(True)

    # Set colour back to original
    for obj in (sampled_target_objs):
        for i,mat in enumerate(obj.get_materials()):
            mat.set_principled_shader_value("Base Color", old_colours_dict[obj][i])

    # Write data in bop format
    # bproc.writer.write_bop(os.path.join(args.output_dir, 'bop_data'),
    #                        dataset = args.lablight_models_path,
    #                        depths = data["depth"],
    #                        colors = data["colors"], 
    #                        color_file_format = "JPEG",
    #                        ignore_dist_thres = 10)
    
# Reformat COCO annotations
