#!/usr/bin/env python3
"""
Single Joint Test Controller for Underwater Hexapod
Interactive script to test one joint at a time with full control

Usage:
    python test_single_joint.py --joint lf_j1
"""

import argparse
import sys
import time

import glfw
import mujoco
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(description='Test a single joint interactively')
    parser.add_argument('--model', type=str, default='models/robot.xml',
                        help='Path to MuJoCo model file')
    parser.add_argument('--joint', type=str, required=True,
                        help='Joint name to test (e.g., lf_j1)')
    parser.add_argument('--range', type=float, default=1.57,
                        help='Test range (default: 1.57 rad)')
    return parser.parse_args()


def main():
    args = parse_args()

    # Load model
    try:
        model = mujoco.MjModel.from_xml_path(args.model)
        data = mujoco.MjData(model)
    except Exception as e:
        print(f"Error loading model: {e}")
        sys.exit(1)

    # Get joint indices
    joint_indices = {}
    for i in range(model.njnt):
        joint_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, i)
        if joint_name:
            joint_indices[joint_name] = i

    # Validate joint
    if args.joint not in joint_indices:
        print(f"Error: Joint '{args.joint}' not found.")
        print(f"Available joints: {list(joint_indices.keys())}")
        sys.exit(1)

    joint_id = joint_indices[args.joint]
    qpos_address = model.jnt_qposadr[joint_id]
    actuator_id = mujoco.mj_name2id(
        model, mujoco.mjtObj.mjOBJ_ACTUATOR, args.joint
    )
    if actuator_id < 0:
        print(f"Error: Velocity actuator for '{args.joint}' not found.")
        sys.exit(1)
    
    # Get joint range if limited
    if model.jnt_limited[joint_id]:
        joint_range = model.jnt_range[joint_id]
        print(f"Joint '{args.joint}' range: [{joint_range[0]:.2f}, {joint_range[1]:.2f}] rad")
    else:
        joint_range = [-args.range, args.range]
        print(f"Joint '{args.joint}' (unlimited, using test range: ±{args.range:.2f})")

    print(f"\nControls:")
    print(f"  [1] Move to minimum: {joint_range[0]:.2f} rad")
    print(f"  [2] Move to center: 0.00 rad")
    print(f"  [3] Move to maximum: {joint_range[1]:.2f} rad")
    print(f"  [q] Quit\n")

    try:
        from mujoco import viewer

        state = {"target": 0.0, "quit": False}

        def on_key(key):
            if key == glfw.KEY_1:
                state["target"] = float(joint_range[0])
            elif key == glfw.KEY_2:
                state["target"] = 0.0
            elif key == glfw.KEY_3:
                state["target"] = float(joint_range[1])
            elif key in (glfw.KEY_Q, glfw.KEY_ESCAPE):
                state["quit"] = True
            else:
                return
            print(f"\nNew target: {state['target']:.2f} rad")

        with viewer.launch_passive(model, data, key_callback=on_key) as vid:
            print(f"Viewer started. Testing joint: {args.joint}")
            print(f"Current target: {state['target']:.2f} rad")
            
            while vid.is_running() and not state["quit"]:
                # Apply current target
                error = state["target"] - data.qpos[qpos_address]
                data.ctrl[actuator_id] = np.clip(4.0 * error, -1.0, 1.0)

                mujoco.mj_step(model, data)
                vid.sync()

                # Print joint position periodically
                if int(data.time * 10) % 10 == 0:
                    joint_pos = data.qpos[qpos_address]
                    print(
                        f"\rJoint position: {joint_pos:6.3f} rad "
                        f"(target: {state['target']:6.3f} rad)",
                        end='',
                        flush=True,
                    )

                time.sleep(0.02)

    except ImportError:
        print("MuJoCo viewer not available.")
        sys.exit(1)

    print("\nTest complete")


if __name__ == '__main__':
    main()
