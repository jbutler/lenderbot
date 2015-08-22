#!/usr/bin/env python3

from abc import ABCMeta, abstractmethod
import FilterParser

import logging
import re


class LoanFilter(metaclass=ABCMeta):
	'LendingClub loan filter base class.'

	# Filter parser object
	LoanFilterParser = FilterParser.Arith()

	def __init__(self):
		self.logger = logging.getLogger(__name__)
		self.pass_count = 0
		self.fail_count = 0

	@abstractmethod
	def __str__(self):
		pass

	@abstractmethod
	def _eval(self, loan):
		pass

	def apply(self, loan):
		if self._eval(loan):
			self.pass_count += 1
			return True
		else:
			self.fail_count += 1
			return False


class BasicFilter(LoanFilter):
	'A simple class to represent a LendingClub loan filter. Loans failing this filter will be discarded.'

	def __init__(self, filterStr):
		self.filterStr = filterStr
		super(BasicFilter, self).__init__()

	def __str__(self):
		return self.filterStr

	def _eval(self, loan):
		# Replace lookups with the actual loan value
		# Lookups are the loan key inside braces, i.e. the key 'loanTerm' would be encoded as {loanTerm}
		replacedFilterStr = re.sub('{[A-Za-z0-9]+}', lambda match : str(loan[match.group(0)[1:-1]]), self.filterStr)
		self.logger.debug('Transformed filter: %s -> %s' % (self.filterStr, replacedFilterStr))
		return LoanFilter.LoanFilterParser.eval(replacedFilterStr)

class ExclusionFilter(BasicFilter):
	'A simple class to represent a LendingClub exclusion filter. Loans passing this filter will be discarded.'

	def __str__(self):
		return super(ExclusionFilter, self).__str__()

	def _eval(self, loan):
		return not super(ExclusionFilter, self)._eval(loan)


if __name__ == '__main__':
	import sys

	# Test 'loans'
	loans = []
	loans.append( [ 'loan_a', { 'paramA' : 50,     'paramB' : 50,   'paramC' : 'TestA' } ] )
	loans.append( [ 'loan_b', { 'paramA' : 100,    'paramB' : None, 'paramC' : 1 } ] )
	loans.append( [ 'loan_c', { 'paramA' : 'Test', 'paramB' : -1  , 'paramC' : 'CSCI' } ] )
	loans.append( [ 'loan_d', { 'paramA' : 'C',    'paramB' : None, 'paramC' : None } ] )

	# Test filters
	filters = []
	filters.append( [ 'loan_a', False, BasicFilter('50 < 10')  ] )
	filters.append( [ 'loan_a', False, BasicFilter('{paramA} > 100')  ] )
	filters.append( [ 'loan_a', True,  BasicFilter('{paramB} != None') ] )
	filters.append( [ 'loan_b', False, BasicFilter('{paramC} < 0') ] )
	filters.append( [ 'loan_b', True,  BasicFilter('{paramA} <= 100') ] )
	filters.append( [ 'loan_c', True,  BasicFilter('{paramB} == -1') ] )
	filters.append( [ 'loan_c', False, BasicFilter('{paramC} != CSCI') ] )
	filters.append( [ 'loan_a', False, ExclusionFilter('{paramA} > 25') ] )
	filters.append( [ 'loan_d', False, ExclusionFilter('{paramA} < D') ] )

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
