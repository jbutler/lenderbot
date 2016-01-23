#!/usr/bin/env python3

from abc import ABCMeta, abstractmethod
from lenderbot import FilterParser

import logging
import re
from multiprocessing import Pool, cpu_count


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
    def _eval(self, loan, block):
        pass

    def apply(self, loan, block=True):
        return self._eval(loan, block)


class BasicFilter(LoanFilter):
    'A simple class to represent a LendingClub loan filter. Loans failing this filter will be discarded.'

    def __init__(self, filterStr):
        self.filterStr = filterStr
        super(BasicFilter, self).__init__()

        self.ppool = Pool(processes=cpu_count())

    def __str__(self):
        return self.filterStr

    def _eval(self, loan, block):
        # Replace lookups with the actual loan value
        # Lookups are the loan key inside braces, i.e. the key 'loanTerm' would be encoded as {loanTerm}
        replacedFilterStr = re.sub('{[A-Za-z0-9]+}', lambda match: str(loan[match.group(0)[1:-1]]), self.filterStr)
        # self.logger.debug('Transformed filter: %s -> %s' % (self.filterStr, replacedFilterStr))
        res = self.ppool.apply_async(LoanFilter.LoanFilterParser.eval, [replacedFilterStr])
        if block:
            return res.get()
        else:
            return res


if __name__ == '__main__':
    import sys

    # Test 'loans'
    loans = []
    loans.append(['loan_a', {'paramA': 50, 'paramB': 50, 'paramC': 'TestA'}])
    loans.append(['loan_b', {'paramA': 100, 'paramB': None, 'paramC': 1}])
    loans.append(['loan_c', {'paramA': 'Test', 'paramB': -1, 'paramC': 'CSCI'}])
    loans.append(['loan_d', {'paramA': 'C', 'paramB': None, 'paramC': None}])

    # Test filters
    filters = []
    filters.append(['loan_a', False, BasicFilter('50 < 10')])
    filters.append(['loan_a', False, BasicFilter('{paramA} > 100')])
    filters.append(['loan_a', True, BasicFilter('{paramB} != None')])
    filters.append(['loan_b', False, BasicFilter('{paramC} < 0')])
    filters.append(['loan_b', True, BasicFilter('{paramA} <= 100')])
    filters.append(['loan_c', True, BasicFilter('{paramB} == -1')])
    filters.append(['loan_c', False, BasicFilter('{paramC} != CSCI')])

    # Execute tests
    fail_count = 0
    for loan in loans:
        for filter in filters:
            # Check if this filter applies to this test loan
            if loan[0] == filter[0]:
                if filter[2].apply(loan[1]) != filter[1]:
                    fail_count += 1
                # print('filter.apply(%s): %s' % (loan[0], 'Pass' if filter[2].apply(loan[1]) == filter[1] else 'Fail'))

    if fail_count == 0:
        print('All filter tests passed')
    else:
        print('Error: %d test(s) failed' % (fail_count))

    sys.exit(fail_count)
