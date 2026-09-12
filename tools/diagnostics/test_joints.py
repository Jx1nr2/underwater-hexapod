#!/usr/bin/env python3
"""
Joint Test Controller for Underwater Hexapod
Tests each joint individually by moving it through its full range of motion
"""

import mujoco
import numpy as np
import time
import argparse
import sys


def parse_args():
    parser = argparse.ArgumentParser(description='Test individual joints of Hexapod')
    parser.add_argument('--model', type=str, default='models/robot.xml',
                        help='Path to MuJoCo model file')
    parser.add_argument('--duration', type=float, default=2.0,
                        help='Duration to hold each joint position (seconds)')
    parser.add_argument('--speed', type=float, default=0.5,
                        help='Speed of joint movement (0.1 to 2.0)')
    parser.add_argument('--joint', type=str, default=None,
                        help='Test specific joint by name (e.g., lf_j1)')
    parser.add_argument('--list', action='store_true',
                        help='List all available joints and exit')
    return parser.parse_args()


def get_joint_ranges(model):
    """Get the range (min, max) for each joint"""
    joint_ranges = {}
    for i in range(model.njnt):
        joint_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, i)
        if joint_name and model.jnt_limited[i]:
            joint_ranges[joint_name] = (model.jnt_range[i, 0], model.jnt_range[i, 1])
    return joint_ranges


def get_default_posture():
    """Return default joint angles for standing posture"""
    return {
        'base_fold': 0.0,
        'lf_j1': 0.0, 'lf_j2': 0.0,
        'lm_j1': 0.0, 'lm_j2': 0.0,
        'lr_j1': 0.0, 'lr_j2': 0.0,
        'rf_j1': 0.0, 'rf_j2': 0.0,
        'rm_j1': 0.0, 'rm_j2': 0.0,
        'rr_j1': 0.0, 'rr_j2': 0.0,
    }


def main():
    args = parse_args()

    # Load model
    try:
        model = mujoco.MjModel.from_xml_path(args.model)
        data = mujoco.MjData(model)
    except Exception as e:
        print(f"Error loading model: {e}")
        sys.exit(1)

    # Get joint information
    joint_names = []
    joint_indices = {}
    qpos_addresses = {}
    actuator_indices = {}
    joint_ranges = get_joint_ranges(model)
    
    for i in range(model.njnt):
        joint_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, i)
        if joint_name and joint_name in joint_ranges:
            joint_names.append(joint_name)
            joint_indices[joint_name] = i
            qpos_addresses[joint_name] = model.jnt_qposadr[i]
            actuator_indices[joint_name] = mujoco.mj_name2id(
                model, mujoco.mjtObj.mjOBJ_ACTUATOR, joint_name
            )

    # List joints
    if args.list:
        print(f"Available joints ({len(joint_names)} total):")
        for name in joint_names:
            min_val, max_val = joint_ranges[name]
            print(f"  {name}: [{min_val:.2f}, {max_val:.2f}] rad")
        sys.exit(0)

    # Check if testing specific joint
    if args.joint:
        if args.joint not in joint_indices:
            print(f"Error: Joint '{args.joint}' not found.")
            print(f"Available joints: {joint_names}")
            sys.exit(1)
        test_joints = [args.joint]
    else:
        test_joints = joint_names

    print(f"\n{'='*60}")
    print(f"Starting joint test for {len(test_joints)} joint(s)")
    print(f"Duration per joint: {args.duration}s")
    print(f"{'='*60}\n")

    # Default posture for non-tested joints
    default_posture = get_default_posture()

    try:
        from mujoco import viewer
        
        with viewer.launch_passive(model, data) as vid:
            current_joint_idx = 0
            state = "MOVING_TO_START"  # States: MOVING_TO_START, HOLDING_START, MOVING_TO_END, HOLDING_END
            start_time = time.time()
            target_position = 0.0
            
            # Initialize targets with default posture
            joint_targets = default_posture.copy()

            while vid.is_running() and current_joint_idx < len(test_joints):
                # Step simulation
                mujoco.mj_step(model, data)

                # Sync viewer
                vid.sync()

                # Get current joint value
                current_joint_name = test_joints[current_joint_idx]
                current_joint_id = joint_indices[current_joint_name]
                current_value = data.qpos[qpos_addresses[current_joint_name]]

                # Get range for this joint
                min_val, max_val = joint_ranges[current_joint_name]
                
                # State machine for joint testing
                if state == "MOVING_TO_START":
                    # Move to minimum position
                    target_position = min_val
                    # Move other joints to default
                    for name in test_joints:
                        if name != current_joint_name and name in default_posture:
                            joint_targets[name] = default_posture[name]
                    
                    # Move target joint
                    if abs(current_value - min_val) < 0.05:
                        state = "HOLDING_START"
                        start_time = time.time()
                        print(f"  [{current_joint_name}] Reached start position: {min_val:.2f} rad")
                    else:
                        # Move towards start with some speed
                        speed = args.speed * 0.05
                        if current_value < min_val:
                            joint_targets[current_joint_name] = min(current_value + speed, min_val)
                        else:
                            joint_targets[current_joint_name] = max(current_value - speed, min_val)

                elif state == "HOLDING_START":
                    # Hold at minimum for duration
                    if time.time() - start_time >= args.duration:
                        state = "MOVING_TO_END"
                        start_time = time.time()
                        print(f"  [{current_joint_name}] Starting end position test...")
                    else:
                        # Keep at start position
                        joint_targets[current_joint_name] = min_val

                elif state == "MOVING_TO_END":
                    # Move to maximum position
                    # Move other joints to default
                    for name in test_joints:
                        if name != current_joint_name and name in default_posture:
                            joint_targets[name] = default_posture[name]
                    
                    # Move target joint
                    if abs(current_value - max_val) < 0.05:
                        state = "HOLDING_END"
                        start_time = time.time()
                        print(f"  [{current_joint_name}] Reached end position: {max_val:.2f} rad")
                    else:
                        # Move towards end with some speed
                        speed = args.speed * 0.05
                        if current_value < max_val:
                            joint_targets[current_joint_name] = min(current_value + speed, max_val)
                        else:
                            joint_targets[current_joint_name] = max(current_value - speed, max_val)

                elif state == "HOLDING_END":
                    # Hold at maximum for duration
                    if time.time() - start_time >= args.duration:
                        current_joint_idx += 1
                        if current_joint_idx < len(test_joints):
                            print(f"\n  Moving to next joint...")
                            state = "MOVING_TO_START"
                            start_time = time.time()
                        else:
                            print(f"\n  All joints tested!")
                            # Return to default posture
                            state = "RETURNING_HOME"
                            start_time = time.time()
                    else:
                        # Keep at end position
                        joint_targets[current_joint_name] = max_val

                elif state == "RETURNING_HOME":
                    # Return to default posture
                    all_at_default = True
                    for name in joint_names:
                        if name in default_posture:
                            current = data.qpos[qpos_addresses[name]]
                            if abs(current - default_posture[name]) > 0.1:
                                all_at_default = False
                                # Move towards default
                                speed = 0.05
                                if current < default_posture[name]:
                                    joint_targets[name] = min(current + speed, default_posture[name])
                                else:
                                    joint_targets[name] = max(current - speed, default_posture[name])
                            else:
                                joint_targets[name] = default_posture[name]

                    if all_at_default:
                        break

                # Apply targets
                for name, target in joint_targets.items():
                    if name in actuator_indices:
                        current = data.qpos[qpos_addresses[name]]
                        data.ctrl[actuator_indices[name]] = np.clip(
                            4.0 * (target - current), -1.0, 1.0
                        )

                # Add small delay for visualization
                time.sleep(0.02)

            print("\n" + "="*60)
            print("Joint testing complete!")
            print("="*60)

    except ImportError:
        print("MuJoCo viewer not available. Running headless...")
        print("This test requires visual feedback, please install mujoco viewer.")
        
        # Headless mode - just simulate
        joint_targets = default_posture.copy()
        for _ in range(int(10 * 500)):  # 10 seconds
            for name, target in joint_targets.items():
                if name in actuator_indices:
                    current = data.qpos[qpos_addresses[name]]
                    data.ctrl[actuator_indices[name]] = np.clip(
                        4.0 * (target - current), -1.0, 1.0
                    )
            mujoco.mj_step(model, data)
            time.sleep(0.002)

    print("\nSimulation complete")


if __name__ == '__main__':
    main()

