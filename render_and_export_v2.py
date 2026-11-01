import bpy
import os
import math
from mathutils import Vector

# ================= SETTINGS =================
output_folder = r"E:\blender files\blender cheated one"   # raw string: keeps the backslashes
resolution = 1024            # output image size (square)
distance_margin = 1.15       # bigger = cameras further away from the model
# ============================================

os.makedirs(output_folder, exist_ok=True)
scene = bpy.context.scene

# Camera names (same as the video): Camera, Camera1 ... Camera10
camera_names = ["Camera"] + [f"Camera{i}" for i in range(1, 11)]

# (azimuth angle, height angle) in degrees for each of the 11 cameras
# 6 low cameras all around, 4 higher cameras, 1 from the top
camera_angles = [
    (0, 15), (60, 15), (120, 15), (180, 15), (240, 15), (300, 15),
    (30, 45), (120, 45), (210, 45), (300, 45),
    (0, 80),
]

# ---------- Find the model(s) and work out their size ----------
meshes = [o for o in scene.objects if o.type == 'MESH']
if not meshes:
    raise RuntimeError("No mesh object found in the scene. Import or add your 3D model first.")

corners = []
for obj in meshes:
    for c in obj.bound_box:
        corners.append(obj.matrix_world @ Vector(c))

min_v = Vector((min(v.x for v in corners), min(v.y for v in corners), min(v.z for v in corners)))
max_v = Vector((max(v.x for v in corners), max(v.y for v in corners), max(v.z for v in corners)))
center = (min_v + max_v) / 2
radius = (max_v - min_v).length / 2          # bounding sphere radius

# ---------- Create (or reuse) the cameras and aim them at the model ----------
for name, (azimuth, elevation) in zip(camera_names, camera_angles):
    cam_obj = bpy.data.objects.get(name)
    if cam_obj is None or cam_obj.type != 'CAMERA':
        cam_data = bpy.data.cameras.new(name)
        cam_obj = bpy.data.objects.new(name, cam_data)
        scene.collection.objects.link(cam_obj)

    cam_data = cam_obj.data
    cam_data.lens = 50
    fov = 2 * math.atan((cam_data.sensor_width / 2) / cam_data.lens)
    dist = radius / math.sin(fov / 2) * distance_margin
    cam_data.clip_start = 0.01
    cam_data.clip_end = max(1000.0, dist * 10)

    az = math.radians(azimuth)
    el = math.radians(elevation)
    offset = Vector((
        dist * math.cos(el) * math.cos(az),
        dist * math.cos(el) * math.sin(az),
        dist * math.sin(el),
    ))
    cam_obj.location = center + offset

    # Point the camera at the model
    direction = center - cam_obj.location
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

print(f"Created/updated {len(camera_names)} cameras around the model.")

# ---------- Make sure there is some light ----------
if not any(o.type == 'LIGHT' for o in scene.objects):
    sun_data = bpy.data.lights.new("Sun", 'SUN')
    sun_data.energy = 3.0
    sun_obj = bpy.data.objects.new("Sun", sun_data)
    sun_obj.rotation_euler = (math.radians(50), 0, math.radians(30))
    scene.collection.objects.link(sun_obj)
    print("No light found - added a Sun light.")

if scene.world is None:
    scene.world = bpy.data.worlds.new("World")
    scene.world.use_nodes = True

# ---------- Render settings ----------
scene.render.resolution_x = resolution
scene.render.resolution_y = resolution
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'

# ---------- Render from each camera ----------
for camera_name in camera_names:
    camera = bpy.data.objects.get(camera_name)
    if camera:
        scene.camera = camera
        output_path = os.path.join(output_folder, f"{camera_name}.png")
        scene.render.filepath = output_path
        bpy.ops.render.render(write_still=True)
        print(f"Rendered from {camera_name}: {output_path}")
    else:
        print(f"Camera '{camera_name}' was not found!")

# ---------- Save a copy of the scene as .blend ----------
blend_file_path = os.path.join(output_folder, "scene.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_file_path, copy=True)
print(f"Scene saved as .blend: {blend_file_path}")

# ---------- Export in multiple formats (Blender 4.x operators) ----------
exporters = {
    "OBJ": (".obj", lambda p: bpy.ops.wm.obj_export(filepath=p)),
    "STL": (".stl", lambda p: bpy.ops.wm.stl_export(filepath=p)),
    "FBX": (".fbx", lambda p: bpy.ops.export_scene.fbx(filepath=p, object_types={'MESH'})),
}

for format_name, (extension, export_func) in exporters.items():
    export_path = os.path.join(output_folder, f"scene{extension}")
    try:
        export_func(export_path)
        print(f"Scene exported as {format_name}: {export_path}")
    except Exception as e:
        print(f"Error exporting {format_name}: {e}")
