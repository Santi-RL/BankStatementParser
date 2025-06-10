#!/usr/bin/env python3
"""
Test script to debug Chase PDF parsing
"""

import pytest
pytest.skip("Debug script not intended as a test", allow_module_level=True)

from pdf_processor import PDFProcessor
import tempfile
import os

# Sample content from the Chase PDF
test_content = """
December 30, 2023 through January 31, 2024
JPMorgan Chase Bank, N.A.

*start*deposits and additions

DEPOSITS AND ADDITIONS

     DATE                      DESCRIPTION                                                                                                          AMOUNT
01/02                          Deposit    2063844249                                                                                               $300.00
01/02                          Zelle Payment From Dave Adden Pinnock 19468032866                                                                   1,800.00
01/18                          Deposit    2096126287                                                                                               2,000.00
01/26                          Zelle Payment From Osvaldo Mario Mastino 19679532458                                                                 110.00

Total Deposits and Additions                                                                                                                  $4,210.00
*end*deposits and additions

*start*electronic withdrawal

ELECTRONIC WITHDRAWALS

     DATE                          DESCRIPTION                                                                                                                       AMOUNT
01/03                              Zelle Payment To Ugarte Martin Jpm99A7Fueo0                                                                                       $500.00
01/04                              Zelle Payment To Herby 1 Jpm99A7Hl7Mx                                                                                              400.00
01/08                              Zelle Payment To Laura Coll 19516915865                                                                                            700.00

Total Electronic Withdrawals                                                                                                                                    $3,227.83
*end*electronic withdrawal

*start*fees section

FEES

     DATE                          DESCRIPTION                                                                                                                       AMOUNT
01/31                              Monthly Service Fee                                                                                                                $15.00

Total Fees                                                                                                                                                            $15.00
*end*fees section
"""

if __name__ == "__main__":
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_content)
        temp_path = f.name
    
    try:
        processor = PDFProcessor()
        # Simulate the parsing by calling the Chase format parser directly
        from parsers.generic import GenericEnglishParser
        
        parser = GenericEnglishParser()
        account_info = {'account_number': '000000771927196', 'currency': 'USD'}
        
        # Test the Chase format parsing
        transactions = parser._parse_chase_format(test_content, "test.pdf", account_info)
        
        print(f"Found {len(transactions)} transactions:")
        for i, trans in enumerate(transactions):
            print(f"{i+1}. {trans['date']} - {trans['description']} - ${trans['amount']}")
        
    finally:
        # Clean up
        os.unlink(temp_path)