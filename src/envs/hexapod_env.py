"""Gymnasium-compatible environment for the underwater hexapod."""

from pathlib import Path
from typing import Any, Callable

import gymnasium as gym
import mujoco
import numpy as np
from gymnasium import spaces


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "robot.xml"

JOINT_ACTIONS = (
    "base_fold",
    "lf_j1", "lf_j2",
    "lm_j1", "lm_j2",
    "lr_j1", "lr_j2",
    "rf_j1", "rf_j2",
    "rm_j1", "rm_j2",
    "rr_j1", "rr_j2",
)
ADHESION_ACTIONS = (
    "lf_adhesion", "lm_adhesion", "lr_adhesion",
    "rf_adhesion", "rm_adhesion", "rr_adhesion",
)
CONTACT_SENSORS = (
    "lf_contact", "lm_contact", "lr_contact",
    "rf_contact", "rm_contact", "rr_contact",
)


class UnderwaterHexapodEnv(gym.Env):
    """Direct velocity-control interface shared by RL and keyboard control.

    Action layout:
        [13 joint target velocities in rad/s, 6 adhesion switches]

    Observation layout:
        [qpos, qvel, six foot-contact readings, six applied adhesion values]

    The environment intentionally returns a neutral reward.  A task-specific
    training environment can subclass this class and replace ``step``'s reward.
    """

    metadata = {"render_modes": ["human"], "render_fps": 100}

    def __init__(
        self,
        model_path: str | Path = DEFAULT_MODEL_PATH,
        render_mode: str | None = None,
        frame_skip: int = 5,
    ) -> None:
        super().__init__()
        if render_mode not in (None, "human"):
            raise ValueError("render_mode must be None or 'human'")
        if frame_skip < 1:
            raise ValueError("frame_skip must be at least 1")

        self.model_path = Path(model_path).resolve()
        self.model = mujoco.MjModel.from_xml_path(str(self.model_path))
        self.data = mujoco.MjData(self.model)
        self.render_mode = render_mode
        self.frame_skip = frame_skip
        self._viewer = None

        self._joint_actuator_ids = self._resolve_ids(
            mujoco.mjtObj.mjOBJ_ACTUATOR, JOINT_ACTIONS
        )
        self._adhesion_actuator_ids = self._resolve_ids(
            mujoco.mjtObj.mjOBJ_ACTUATOR, ADHESION_ACTIONS
        )
        self._sensor_ids = self._resolve_ids(
            mujoco.mjtObj.mjOBJ_SENSOR, CONTACT_SENSORS
        )

        action_low = np.concatenate((
            -np.ones(len(JOINT_ACTIONS), dtype=np.float32),
            np.zeros(len(ADHESION_ACTIONS), dtype=np.float32),
        ))
        action_high = np.ones(len(JOINT_ACTIONS) + len(ADHESION_ACTIONS), dtype=np.float32)
        self.action_space = spaces.Box(action_low, action_high, dtype=np.float32)

        observation_size = (
            self.model.nq + self.model.nv
            + len(CONTACT_SENSORS) + len(ADHESION_ACTIONS)
        )
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(observation_size,),
            dtype=np.float32,
        )

    @property
    def dt(self) -> float:
        return float(self.model.opt.timestep * self.frame_skip)

    def _resolve_ids(self, object_type: mujoco.mjtObj, names: tuple[str, ...]) -> np.ndarray:
        ids = []
        for name in names:
            object_id = mujoco.mj_name2id(self.model, object_type, name)
            if object_id < 0:
                raise ValueError(f"Model is missing required object: {name}")
            ids.append(object_id)
        return np.asarray(ids, dtype=np.int32)

    def _get_observation(self) -> np.ndarray:
        contact_values = np.asarray(
            [self.data.sensordata[self.model.sensor_adr[i]] for i in self._sensor_ids]
        )
        adhesion_values = self.data.ctrl[self._adhesion_actuator_ids]
        return np.concatenate((
            self.data.qpos,
            self.data.qvel,
            contact_values,
            adhesion_values,
        )).astype(np.float32)

    def _get_info(self) -> dict[str, Any]:
        contacts = {
            name: float(self.data.sensordata[self.model.sensor_adr[sensor_id]])
            for name, sensor_id in zip(CONTACT_SENSORS, self._sensor_ids)
        }
        return {
            "time": float(self.data.time),
            "base_position": self.data.qpos[:3].copy(),
            "foot_contacts": contacts,
        }

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        super().reset(seed=seed)
        mujoco.mj_resetData(self.model, self.data)
        if options and "qpos" in options:
            qpos = np.asarray(options["qpos"], dtype=float)
            if qpos.shape != self.data.qpos.shape:
                raise ValueError(f"qpos must have shape {self.data.qpos.shape}")
            self.data.qpos[:] = qpos
        mujoco.mj_forward(self.model, self.data)
        return self._get_observation(), self._get_info()

    def step(
        self, action: np.ndarray
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        action = np.asarray(action, dtype=np.float32)
        if action.shape != self.action_space.shape:
            raise ValueError(
                f"action must have shape {self.action_space.shape}, got {action.shape}"
            )
        action = np.clip(action, self.action_space.low, self.action_space.high)
        split = len(JOINT_ACTIONS)
        self.data.ctrl[self._joint_actuator_ids] = action[:split]
        self.data.ctrl[self._adhesion_actuator_ids] = action[split:]

        mujoco.mj_step(self.model, self.data, nstep=self.frame_skip)
        observation = self._get_observation()
        terminated = not bool(np.isfinite(observation).all())
        reward = 0.0
        return observation, reward, terminated, False, self._get_info()

    def launch_viewer(
        self, key_callback: Callable[[int], None] | None = None
    ):
        """Open or return the passive viewer used by interactive control."""
        if self._viewer is None or not self._viewer.is_running():
            from mujoco import viewer

            self._viewer = viewer.launch_passive(
                self.model,
                self.data,
                key_callback=key_callback,
                show_left_ui=True,
                show_right_ui=True,
            )
        return self._viewer

    def render(self) -> None:
        if self.render_mode == "human":
            self.launch_viewer().sync()

    def close(self) -> None:
        if self._viewer is not None:
            self._viewer.close()
            self._viewer = None

