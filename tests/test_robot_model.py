import unittest
from pathlib import Path

import mujoco
import numpy as np

from src.envs.hexapod_env import UnderwaterHexapodEnv


MODEL_PATH = Path(__file__).parents[1] / "models" / "robot.xml"
LEGS = ("lf", "lm", "lr", "rf", "rm", "rr")


class RobotModelTest(unittest.TestCase):
    def setUp(self):
        self.model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))

    def test_expected_interfaces_exist(self):
        for leg in LEGS:
            for suffix in ("j1", "j2"):
                name = f"{leg}_{suffix}"
                self.assertGreaterEqual(
                    mujoco.mj_name2id(
                        self.model, mujoco.mjtObj.mjOBJ_JOINT, name
                    ),
                    0,
                )
            for suffix in ("foot_site", "adhesion"):
                object_type = (
                    mujoco.mjtObj.mjOBJ_SITE
                    if suffix == "foot_site"
                    else mujoco.mjtObj.mjOBJ_ACTUATOR
                )
                self.assertGreaterEqual(
                    mujoco.mj_name2id(
                        self.model, object_type, f"{leg}_{suffix}"
                    ),
                    0,
                )

    def test_velocity_commands_are_limited(self):
        for name in ("base_fold",) + tuple(
            f"{leg}_j{joint}" for leg in LEGS for joint in (1, 2)
        ):
            actuator_id = mujoco.mj_name2id(
                self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, name
            )
            np.testing.assert_allclose(
                self.model.actuator_ctrlrange[actuator_id], [-1.0, 1.0]
            )

    def test_unit_mass_policy(self):
        moving_masses = self.model.body_mass[1:]
        np.testing.assert_allclose(moving_masses, np.ones(20))
        self.assertAlmostEqual(float(moving_masses.sum()), 20.0)

    def test_settles_without_numerical_failure(self):
        data = mujoco.MjData(self.model)
        warning_count_before = sum(item.number for item in data.warning)
        for _ in range(2500):
            mujoco.mj_step(self.model, data)
            self.assertTrue(np.isfinite(data.qpos).all())
            self.assertTrue(np.isfinite(data.qvel).all())
        warning_count_after = sum(item.number for item in data.warning)
        self.assertEqual(warning_count_after, warning_count_before)
        self.assertTrue((data.sensordata > 0).all())

    def test_positive_fold_direction_is_up(self):
        data = mujoco.MjData(self.model)
        joint_id = mujoco.mj_name2id(
            self.model, mujoco.mjtObj.mjOBJ_JOINT, "base_fold"
        )
        rear_geom_id = mujoco.mj_name2id(
            self.model, mujoco.mjtObj.mjOBJ_GEOM, "rear_plate"
        )
        mujoco.mj_forward(self.model, data)
        flat_z = data.geom_xpos[rear_geom_id, 2]
        data.qpos[self.model.jnt_qposadr[joint_id]] = np.pi / 2
        mujoco.mj_forward(self.model, data)
        self.assertGreater(data.geom_xpos[rear_geom_id, 2], flat_z)


class GymInterfaceTest(unittest.TestCase):
    def test_reset_and_step_follow_gymnasium_api(self):
        env = UnderwaterHexapodEnv()
        try:
            observation, info = env.reset(seed=1)
            self.assertTrue(env.observation_space.contains(observation))
            self.assertIn("foot_contacts", info)

            action = np.zeros(env.action_space.shape, dtype=np.float32)
            next_observation, reward, terminated, truncated, info = env.step(action)
            self.assertTrue(env.observation_space.contains(next_observation))
            self.assertEqual(reward, 0.0)
            self.assertFalse(terminated)
            self.assertFalse(truncated)
            self.assertIn("base_position", info)
        finally:
            env.close()


if __name__ == "__main__":
    unittest.main()
