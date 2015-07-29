#!/usr/bin/env python3

import sys

sys.path.insert(0, '.')
sys.path.insert(0, '../')
sys.path.insert(0, '../../')

from investor import investor
import unittest

class InvestorTest(unittest.TestCase):
	def test_dummy_test(self):
		self.assertTrue(True)


if __name__ == '__main__':
	unittest.main()

