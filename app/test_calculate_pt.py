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
        expected = '26, 16, 9, 7, 4, 5, 12'
        self.assertEqual(calculate_pt(sdir, pdir), expected)

    def test_case_3(self):
        sdir = 20
        pdir = "SWS, EG, neh, NS, NWG, wb,eH,nEG"
        expected = '21, 12, 6, 1, 32, 27, 10, 8'
        self.assertEqual(calculate_pt(sdir, pdir), expected)
    def test_case_4(self):
        sdir = 22
        pdir = "NEH,NEB,NEG,EH,EB,EG,SEH,SEB,SEG,SH,SB,SG,SWH,SWB,SWG"
        expected = '10, 11, 12, 14, 15, 16, 18, 19, 20, 22, 23, 24, 26, 27, 28'
        self.assertEqual(calculate_pt(sdir, pdir), expected)

    def test_invalid_direction(self):
        with self.assertRaises(ValueError) as context:
            calculate_pt('GFH', '1')

if __name__ == '__main__':
    unittest.main()
