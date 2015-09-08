#!/usr/bin/env python3

import sys
import getopt
import os
import logging
import csv
import re

from Loan import PastLoan
from LoanFilter import BasicFilter

class LoanHistory(object):
   def __init__(self, loanFilt, files=[]):
      self.Filt = loanFilt
      # Group loans to reduce search space at the expense of storage when groupings are not exclusive
      self.Loans = {'default' : {},
                    'good'    : {}}

      self.Files = files
      for f in self.Files:
         if os.path.isfile(f):
            logging.info("Gathering Stats on {}".format(f))
            with open(f, 'r') as csvfile:
               if not self._parseFile(csvfile):
                  logging.info("Could not parse the CSV file. Scrubbing it before continuing")

                  csvfile.seek(0)
                  csvfile = self._scrubFile(csvfile)

                  csvfile.seek(0)
                  self._parseFile(csvfile)


   def _parseFile(self, fn):
      csvRestKey = 'xkey'
      csvRestVal = 'xval'

      # Assume line 1 holds the keys
      for line,row in enumerate(csv.DictReader(fn, restkey=csvRestKey, restval=csvRestVal)):
         row.update({'csv_line' : line})
         loan = PastLoan(csvRestKey, csvRestVal, row)

         if not loan.isValid():
            return False
         elif self.Filt.apply(loan):
            self._gatherDefaultStats(loan)
            self._gatherStereotypeStats(loan)

      return True


   # Clean up LendingClub CSV files
   def _scrubFile(self, f):
      logging.debug("Scrubbing " + f.name)

      scrubbed = False
      newlines = []
      for line in [l.rstrip('\n') for l in f]:
         # Drop everything after and including first non-CSV line
         #  (Declined loans and/or footer text)
         if re.match('^[^"]', line):
            scrubbed = True

            logging.debug("\n'{}'\n is not valid CSV".format(line))
            break

         newlines.append(line)

      if scrubbed:
         # Reopen to overwrite
         new = f.name
         f.close()

         logging.info("CSV File has been scrubbed")
         new = input("Save scrubbed CSV as [{}]: ".format(new)) or new

         f = open(new, 'w+')
         for line in newlines:
            f.write(line + '\n')

      return f


   # Determine % of filtered loans that will default in specified ranges of time
   def _gatherDefaultStats(self, loan):
      logging.debug("Collecting loan {}".format(loan['id']))
      if loan['loan_status'] == "Charged Off":
         loans = self.Loans['default']
      else:
         loans = self.Loans['good']

      # Put the loan into its age bucket
      age = loan.getAge()
      if age not in loans:
         loans[age] = []
      loans[age].append(loan)


   def _gatherStereotypeStats(self, loan):
      # Count frequency of other properties on loans that pass the filter
      pass


   def _countByAge(self, loans, months):
      # Loans that lived longer than our last bucket
      count = {-1 : 0}
      count[-1] += sum( [len(loans) for iAge,loans in loans.items() if iAge >= months[-1]] )

      prev_m = 0
      for m in months:
         count[m] = 0

         # Count the loans that lived between (prev_m -> m) months
         count[m] += sum( [len(loans) for iAge,loans in loans.items() if iAge < m and iAge >= prev_m] )
         prev_m = m

      return count


   # Determine the default rate of loans that passed the filter, and when they defaulted
   def defaultRate(self, months=[1,3,6,12,18]):
      logging.debug("Calculating default rate at " + ", ".join( [str(month) for month in months] ) + " months" )

      # TODO: Loan age using loan.getAge()
      defaultCnt = self._countByAge(self.Loans['default'], months)
      goodCnt = self._countByAge(self.Loans['good'], months)


      total = sum( defaultCnt.values() )
      total += sum( goodCnt.values() )

      print ("{:d} loans passed the filter...".format(total))
      if total == 0:
         return

      print ( "{:d} did not default".format( sum(goodCnt.values()) ) )

      prev_m = 0
      for m in months:
         mDefaults = defaultCnt[m]
         print ( "{:.2%} ({:d}) defaulted between {:d} and {:d} months".format( mDefaults/total, mDefaults, prev_m, m) )

         prev_m = m

      mDefaults = defaultCnt[-1]
      print ( "{:.2%} ({:d}) defaulted after {:d} months".format( mDefaults/total, mDefaults, prev_m) )

   def stereoType(self):
      pass


def historyTest(files, periods):
   nh = LoanHistory( BasicFilter('{id} > 0'), files)
   nh.defaultRate( periods )


def printUsage():
   print ("\nUsage: {} <options>".format(sys.argv[0]) )
   print ("\t-h|--help\n\t\tPrint this message and exit")
   print ("\t-f|--file <filename>\n\t\tSpecify the csv file to analyze")
   print ("\t-p|--period <n>\n\t\tSpecify points in time (in months) that you want to know the loan default rate of")
   print ("\t-l|--log <level>\n\t\tSpecify the log level")
   print ("\t\tExample: '-p 6 -p 12 -p 18 -p 36' will tell you how many loans defaulted before 6 months, between 6 and 12, etc.")

if (__name__) == "__main__":
   if (len(sys.argv) < 2):
      printUsage()
      sys.exit(1)

   log_level = "WARNING"
   files = []
   periods = []

   # Get the command line arguments
   try:
      opts, args = getopt.getopt(sys.argv[1:], "hf:p:l:", ["help", "file=", "period=", "log="])
   except getopt.GetoptError:
      printUsage()
      sys.exit(1)

   for opt, arg in opts:
      if opt in ("-h", "--help"):
         printUsage()
         sys.exit(1)
      elif opt in ("-f", "--file"):
         files.append(arg)
      elif opt in ("-p", "--period"):
         periods.append(int(arg))
      elif opt in ("-l", "--log"):
         log_level = arg
      else:
         printUsage()
         sys.exit(1)
   logging.basicConfig(level=log_level)

   # Allow user to pass file without -f option
   if len(files) == 0:
      if len(args) != 0:
         files = args
      else:
         printUsage()
         logging.critical("Must specify a Loan CSV file")
         sys.exit(1)


   # Default periods
   if len(periods) == 0:
      periods = [6, 12, 24, 36, 48]

   historyTest(files, periods)

