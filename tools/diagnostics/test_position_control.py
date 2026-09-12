#!/usr/bin/env python3
"""
Test position control for a single joint
"""

import mujoco
import numpy as np
import time

# Load model
model = mujoco.MjModel.from_xml_path('models/robot.xml')
data = mujoco.MjData(model)

# Get joint index
joint_name = 'lf_j1'
for i in range(model.njnt):
    name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, i)
    if name == joint_name:
        joint_id = i
        break

print(f"Testing joint: {joint_name} (id={joint_id})")
qpos_address = model.jnt_qposadr[joint_id]
print(f"Initial position: {data.qpos[qpos_address]}")

# Setup controller
actuator_id = None
for i in range(model.nu):
    name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, i)
    if name == joint_name:
        actuator_id = i
        break

print(f"Actuator id: {actuator_id}")

# Create viewer
try:
    from mujoco import viewer
    
    with viewer.launch_passive(model, data) as vid:
        # Move joint to different positions
        test_positions = [0.0, 1.0, -1.0, 0.0]
        
        for pos in test_positions:
            print(f"\nMoving to {pos:.2f} rad...")
            
            # Velocity actuators are limited to [-1, 1] rad/s.  A proportional
            # outer loop converts this test's position target to velocity.
            for _ in range(300):
                if actuator_id is not None:
                    error = pos - data.qpos[qpos_address]
                    data.ctrl[actuator_id] = np.clip(4.0 * error, -1.0, 1.0)
                mujoco.mj_step(model, data)
                vid.sync()
                time.sleep(0.002)
            
            print(f"  Current position: {data.qpos[qpos_address]:.3f} rad")
            
except ImportError:
    print("MuJoCo viewer not available.")

print("\nTest complete")

