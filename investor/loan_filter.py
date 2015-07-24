#!/usr/bin/env python3

import logging
import operator


class loan_filter():
	'A simple class to represent a LendingClub loan filter.'

	def __init__(self, key, op, comp, exclusion=True):
		operators = { '>' : operator.gt, '>=' : operator.ge, '<' : operator.lt, '<=' : operator.le, '==' : operator.eq, '!=' : operator.ne }
		self.logger = logging.getLogger(__name__)
		self.key  = key
		self.op   = operators[op]
		self.comp = comp
		if comp == 'None':
			self.comp = None

		self.exclusion = exclusion
		self.pass_count = 0
		self.fail_count = 0

	def __eval(self, loan):
		# Catch the case where the key value should be None but it isn't
		if loan[self.key] != None and self.comp == None:
			return False

		# Fail loans that do not define the key required by the filter
		if loan[self.key] == None and self.comp != None:
			return False

		# Handle normal comparisons
		return not self.op(loan[self.key], self.comp)


	def apply(self, loan):
		if self.__eval(loan):
			self.pass_count += 1
			return True
		else:
			self.fail_count += 1
			return False

if __name__ == '__main__':
	import sys

	# Test 'loans'
	loans = []
	loans.append( [ 'loan_a', { 'param_a' : 50,     'param_b' : 50,   'param_c' : 'TestA' } ] )
	loans.append( [ 'loan_b', { 'param_a' : 100,    'param_b' : None, 'param_c' : 1 } ] )
	loans.append( [ 'loan_c', { 'param_a' : 'Test', 'param_b' : -1  , 'param_c' : 'CSCI' } ] )

	# Test filters
	filters = []
	filters.append( [ 'loan_a', True,  loan_filter('param_a', '>',  100)  ] )
	filters.append( [ 'loan_a', False, loan_filter('param_b', '!=', None) ] )
	filters.append( [ 'loan_b', True,  loan_filter('param_c', '<',  0) ] )
	filters.append( [ 'loan_b', False, loan_filter('param_a', '<=', 100) ] )
	filters.append( [ 'loan_c', False, loan_filter('param_b', '==', -1) ] )
	filters.append( [ 'loan_c', True,  loan_filter('param_c', '!=', 'CSCI') ] )

	# Execute tests
	fail_count = 0
	for loan in loans:
		for filter in filters:
			# Check if this filter applies to this test loan
			if loan[0] == filter[0]:
				if filter[2].apply(loan[1]) != filter[1]:
					fail_count += 1
				#print('filter.apply(%s): %s' % (loan[0], 'Pass' if filter[2].apply(loan[1]) == filter[1] else 'Fail'))

	if fail_count == 0:
		print('All filter tests passed')
	else:
		print('Error: %d test(s) failed' % (fail_count))

	sys.exit(fail_count)
