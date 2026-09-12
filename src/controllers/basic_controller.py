#!/usr/bin/env python3
"""
Basic MuJoCo Controller for Underwater Hexapod
Controls all joints with position control
"""

import argparse
import time

import mujoco
import numpy as np


MAX_JOINT_SPEED_RAD_S = 1.0
POSITION_GAIN = 4.0


def parse_args():
    parser = argparse.ArgumentParser(description='Basic Hexapod Controller')
    parser.add_argument('--model', type=str, default='models/robot.xml',
                        help='Path to MuJoCo model file')
    parser.add_argument('--duration', type=float, default=10.0,
                        help='Simulation duration in seconds')
    parser.add_argument('--stand', action='store_true',
                        help='Use standing posture')
    parser.add_argument('--adhesion', action='store_true',
                        help='Enable all six electromagnetic feet')
    return parser.parse_args()


def get_default_posture(stand=False):
    """Return a flat posture or an initial crouched standing candidate."""
    posture = {
        'base_fold': 0.0,
        'lf_j1': 0.0, 'lf_j2': 0.0,
        'lm_j1': 0.0, 'lm_j2': 0.0,
        'lr_j1': 0.0, 'lr_j2': 0.0,
        'rf_j1': 0.0, 'rf_j2': 0.0,
        'rm_j1': 0.0, 'rm_j2': 0.0,
        'rr_j1': 0.0, 'rr_j2': 0.0,
    }
    if stand:
        for leg in ('lf', 'lm', 'lr', 'rf', 'rm', 'rr'):
            posture[f'{leg}_j1'] = 0.30
            posture[f'{leg}_j2'] = -0.60
    return posture


def build_control_map(model, joint_targets):
    """Resolve joint position addresses and actuator IDs independently."""
    control_map = {}
    for name in joint_targets:
        joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
        actuator_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, name)
        if joint_id < 0 or actuator_id < 0:
            raise ValueError(f"Missing joint or velocity actuator: {name}")
        control_map[name] = (model.jnt_qposadr[joint_id], actuator_id)
    return control_map


def apply_position_targets(model, data, joint_targets, control_map):
    """Outer position loop driving the model's speed-limited velocity actuators."""
    for name, target in joint_targets.items():
        qpos_address, actuator_id = control_map[name]
        error = target - data.qpos[qpos_address]
        command = np.clip(
            POSITION_GAIN * error,
            -MAX_JOINT_SPEED_RAD_S,
            MAX_JOINT_SPEED_RAD_S,
        )
        data.ctrl[actuator_id] = command


def main():
    args = parse_args()

    # Load model
    model = mujoco.MjModel.from_xml_path(args.model)
    data = mujoco.MjData(model)

    joint_targets = get_default_posture(stand=args.stand)
    control_map = build_control_map(model, joint_targets)
    adhesion_ids = [
        mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, f'{leg}_adhesion')
        for leg in ('lf', 'lm', 'lr', 'rf', 'rm', 'rr')
    ]

    posture_name = "standing candidate" if args.stand else "flat posture"
    print(
        f"Loaded floating-base model with {len(joint_targets)} controlled "
        f"joints using {posture_name}"
    )

    # Create viewer
    try:
        from mujoco import viewer
        with viewer.launch_passive(model, data) as vid:
            while vid.is_running() and data.time < args.duration:
                apply_position_targets(model, data, joint_targets, control_map)
                for actuator_id in adhesion_ids:
                    data.ctrl[actuator_id] = float(args.adhesion)

                # Step simulation
                mujoco.mj_step(model, data)

                # Sync viewer
                vid.sync()

                time.sleep(1.0 / 60.0)
    except ImportError:
        print("MuJoCo viewer not available. Running headless...")
        # Headless mode - just simulate
        for _ in range(int(args.duration * 500)):
            apply_position_targets(model, data, joint_targets, control_map)
            for actuator_id in adhesion_ids:
                data.ctrl[actuator_id] = float(args.adhesion)
            mujoco.mj_step(model, data)

    print("Simulation complete")


if __name__ == '__main__':
    main()
