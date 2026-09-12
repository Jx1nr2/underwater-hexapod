#!/usr/bin/env python3
"""
Debug script to check model structure and DOF
"""

import mujoco
import numpy as np

# Load model
model = mujoco.MjModel.from_xml_path('models/robot.xml')
data = mujoco.MjData(model)

print(f"Model: {model.name_.decode() if hasattr(model, 'name_') else 'unnamed'}")
print(f"nq (generalized coordinates): {model.nq}")
print(f"nv (degrees of freedom): {model.nv}")
print(f"njnt (joints): {model.njnt}")
print(f"nbody (bodies): {model.nbody}")

print(f"\nqpos (position): {data.qpos}")
print(f"qvel (velocity): {data.qvel}")

print(f"\nqpos0 (initial position): {model.qpos0}")
print(f"qpos_spring (spring positions): {model.qpos_spring}")

# Check joint information
print("\nJoint information:")
for i in range(model.njnt):
    joint_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, i)
    joint_type = model.jnt_type[i]
    joint_limited = model.jnt_limited[i]
    joint_range = model.jnt_range[i] if joint_limited else None
    print(f"  {i}: {joint_name} (type={joint_type}, limited={joint_limited}, range={joint_range})")

# Check body information
print("\nBody information:")
for i in range(model.nbody):
    body_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, i)
    parent_id = model.body_parentid[i]
    jnt_num = model.body_jntnum[i]
    print(f"  {i}: {body_name} (parent={parent_id}, jnt_num={jnt_num})")

