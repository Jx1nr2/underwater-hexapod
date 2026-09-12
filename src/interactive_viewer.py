#!/usr/bin/env python3
"""Keyboard-driven visual test using the same action interface as Gymnasium."""

import argparse
import time

import glfw
import numpy as np

try:
    from .envs.hexapod_env import (
        ADHESION_ACTIONS,
        JOINT_ACTIONS,
        UnderwaterHexapodEnv,
    )
except ImportError:  # Support direct execution: python src/interactive_viewer.py
    from envs.hexapod_env import (
        ADHESION_ACTIONS,
        JOINT_ACTIONS,
        UnderwaterHexapodEnv,
    )


LEGS = ("lf", "lm", "lr", "rf", "rm", "rr")


class KeyboardController:
    def __init__(self, speed: float) -> None:
        self.action = np.zeros(len(JOINT_ACTIONS) + len(ADHESION_ACTIONS), dtype=np.float32)
        self.speed = float(np.clip(speed, 0.0, 1.0))
        self.selected_leg = 0
        self.reset_requested = False
        self.quit_requested = False

    def print_help(self) -> None:
        print(
            """
Keyboard controls
-----------------
1..6       select LF, LM, LR, RF, RM, RR
W / S      selected leg joint 1: +speed / -speed
E / D      selected leg joint 2: +speed / -speed
X          stop both joints of selected leg
Up / Down  fold rear plate up / down
F          toggle adhesion on selected foot
A          toggle adhesion on all feet
Space      stop all mechanical joints
R          reset simulation and commands
H          show this help
Esc        quit

Commands persist until changed or stopped.
"""
        )
        self.print_status()

    def print_status(self) -> None:
        leg = LEGS[self.selected_leg]
        joint_offset = 1 + 2 * self.selected_leg
        adhesion_offset = len(JOINT_ACTIONS) + self.selected_leg
        print(
            f"Selected={leg.upper()}  "
            f"j1={self.action[joint_offset]:+.1f}  "
            f"j2={self.action[joint_offset + 1]:+.1f}  "
            f"adhesion={'ON' if self.action[adhesion_offset] else 'OFF'}  "
            f"fold={self.action[0]:+.1f}"
        )

    def on_key(self, key: int) -> None:
        number_keys = (
            glfw.KEY_1, glfw.KEY_2, glfw.KEY_3,
            glfw.KEY_4, glfw.KEY_5, glfw.KEY_6,
        )
        if key in number_keys:
            self.selected_leg = number_keys.index(key)
        elif key in (glfw.KEY_W, glfw.KEY_S):
            self.action[1 + 2 * self.selected_leg] = self.speed if key == glfw.KEY_W else -self.speed
        elif key in (glfw.KEY_E, glfw.KEY_D):
            self.action[2 + 2 * self.selected_leg] = self.speed if key == glfw.KEY_E else -self.speed
        elif key == glfw.KEY_X:
            start = 1 + 2 * self.selected_leg
            self.action[start:start + 2] = 0.0
        elif key == glfw.KEY_UP:
            self.action[0] = self.speed
        elif key == glfw.KEY_DOWN:
            self.action[0] = -self.speed
        elif key == glfw.KEY_F:
            index = len(JOINT_ACTIONS) + self.selected_leg
            self.action[index] = 1.0 - self.action[index]
        elif key == glfw.KEY_A:
            values = self.action[len(JOINT_ACTIONS):]
            values[:] = 0.0 if np.all(values > 0.5) else 1.0
        elif key == glfw.KEY_SPACE:
            self.action[:len(JOINT_ACTIONS)] = 0.0
        elif key == glfw.KEY_R:
            self.action[:] = 0.0
            self.reset_requested = True
        elif key == glfw.KEY_H:
            self.print_help()
            return
        elif key == glfw.KEY_ESCAPE:
            self.quit_requested = True
            return
        else:
            return
        self.print_status()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive underwater hexapod test")
    parser.add_argument("--model", default=None, help="Optional MJCF model path")
    parser.add_argument(
        "--speed", type=float, default=1.0,
        help="Keyboard joint speed magnitude in rad/s (0 to 1)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    kwargs = {"render_mode": "human"}
    if args.model is not None:
        kwargs["model_path"] = args.model
    env = UnderwaterHexapodEnv(**kwargs)
    keyboard = KeyboardController(args.speed)
    env.reset()
    viewer = env.launch_viewer(keyboard.on_key)
    keyboard.print_help()

    try:
        while viewer.is_running() and not keyboard.quit_requested:
            if keyboard.reset_requested:
                env.reset()
                keyboard.reset_requested = False
            _, _, terminated, _, _ = env.step(keyboard.action)
            env.render()
            if terminated:
                print("Simulation became non-finite; resetting.")
                keyboard.action[:] = 0.0
                env.reset()
            time.sleep(env.dt)
    finally:
        env.close()


if __name__ == "__main__":
    main()

