import unittest

from src.pose_tracking import joint_angle


class JointAngleTests(unittest.TestCase):
    def test_right_angle(self):
        self.assertAlmostEqual(joint_angle((2, 1), (2, 3), (6, 3)), 90)

    def test_straight_joint(self):
        self.assertAlmostEqual(joint_angle((1, 2), (3, 2), (6, 2)), 180)

    def test_coincident_points(self):
        self.assertIsNone(joint_angle((1, 1), (1, 1), (2, 2)))
        self.assertIsNone(joint_angle((2, 2), (1, 1), (1, 1)))
