import unittest
from MobotixScan import calculate_pt

class TestCalculatePt(unittest.TestCase):
    def test_case_1(self):
        sdir = 28
        pdir = "SES,NEG"
        expected = '21, 16'
        self.assertEqual(calculate_pt(sdir, pdir), expected)

    def test_case_2(self):
        sdir = 18
        pdir = "wh,SEG,ES,neb,NG,NES,eg"
        expected = '26, 16, 9, 7, 4, 29, 28'
        self.assertEqual(calculate_pt(sdir, pdir), expected)

    def test_invalid_direction(self):
        with self.assertRaises(ValueError) as context:
            calculate_pt('GFH', '1')

if __name__ == '__main__':
    unittest.main()
