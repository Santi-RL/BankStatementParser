import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.utils import get_column_letter
from openpyxl.cell.cell import MergedCell
from openpyxl.chart import BarChart, Reference, LineChart
import io
from typing import List, Dict, Any
from datetime import datetime

from utils import format_currency

class ExcelGenerator:
    """Generates structured Excel files from transaction data."""
    
    def __init__(self):
        self.workbook = None
        self.transactions_df = None
    
    def create_excel_file(self, transactions: List[Dict[str, Any]], summary: Dict[str, Any]) -> bytes:
        """
        Create a comprehensive Excel file with transaction data and analysis.
        
        Args:
            transactions: List of transaction dictionaries
            summary: Processing summary information
            
        Returns:
            Excel file as bytes
        """
        # Create DataFrame
        self.transactions_df = pd.DataFrame(transactions)
        
        # Create workbook
        self.workbook = Workbook()
        
        # Remove default sheet
        if 'Sheet' in self.workbook.sheetnames:
            self.workbook.remove(self.workbook['Sheet'])
        
        # Create sheets
        self._create_summary_sheet(summary)
        self._create_transactions_sheet()
        self._create_analysis_sheet()
        self._create_monthly_summary_sheet()
        
        # Save to bytes
        excel_buffer = io.BytesIO()
        self.workbook.save(excel_buffer)
        excel_buffer.seek(0)
        
        return excel_buffer.getvalue()
    
    def _create_summary_sheet(self, summary: Dict[str, Any]):
        """Create summary sheet with processing information."""
        ws = self.workbook.create_sheet("Summary", 0)
        
        # Title
        ws['A1'] = "Bank Statement Processing Summary"
        ws['A1'].font = Font(size=16, bold=True)
        ws['A1'].alignment = Alignment(horizontal='center')
        ws.merge_cells('A1:D1')
        
        # Processing date
        ws['A3'] = "Processing Date:"
        ws['B3'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # File statistics
        ws['A5'] = "File Statistics"
        ws['A5'].font = Font(bold=True, size=12)
        
        ws['A6'] = "Total Files Uploaded:"
        ws['B6'] = summary['total_files']
        
        ws['A7'] = "Successfully Processed:"
        ws['B7'] = summary['successful_files']
        
        ws['A8'] = "Failed Files:"
        ws['B8'] = summary['failed_files']
        
        # Transaction statistics
        ws['A10'] = "Transaction Statistics"
        ws['A10'].font = Font(bold=True, size=12)
        
        ws['A11'] = "Total Transactions:"
        ws['B11'] = summary['total_transactions']
        
        ws['A12'] = "Banks Detected:"
        ws['B12'] = len(summary['banks_detected'])
        
        ws['A13'] = "Bank Names:"
        ws['B13'] = ", ".join(sorted(summary['banks_detected']))
        
        # Transaction totals
        if not self.transactions_df.empty:
            total_credits = self.transactions_df[self.transactions_df['amount'] > 0]['amount'].sum()
            total_debits = abs(self.transactions_df[self.transactions_df['amount'] < 0]['amount'].sum())
            net_amount = total_credits - total_debits
            
            ws['A15'] = "Financial Summary"
            ws['A15'].font = Font(bold=True, size=12)
            
            ws['A16'] = "Total Credits:"
            ws['B16'] = total_credits
            ws['B16'].number_format = '#,##0.00'
            
            ws['A17'] = "Total Debits:"
            ws['B17'] = total_debits
            ws['B17'].number_format = '#,##0.00'
            
            ws['A18'] = "Net Amount:"
            ws['B18'] = net_amount
            ws['B18'].number_format = '#,##0.00'
            if net_amount < 0:
                ws['B18'].font = Font(color="FF0000")  # Red for negative
            else:
                ws['B18'].font = Font(color="008000")  # Green for positive
        
        # Errors section
        if summary['errors']:
            ws['A20'] = "Processing Errors"
            ws['A20'].font = Font(bold=True, size=12, color="FF0000")
            
            row = 21
            for error in summary['errors']:
                ws[f'A{row}'] = error
                ws[f'A{row}'].font = Font(color="FF0000")
                row += 1
        
        # Auto-adjust column widths
        for column in ws.columns:
            first = next((c for c in column if not isinstance(c, MergedCell)), column[0])
            col_letter = get_column_letter(first.column)
            max_length = max(len(str(c.value)) for c in column if c.value)
            ws.column_dimensions[col_letter].width = min(max_length + 2, 50)
    
    def _create_transactions_sheet(self):
        """Create main transactions sheet."""
        ws = self.workbook.create_sheet("All Transactions")
        
        if self.transactions_df.empty:
            ws['A1'] = "No transactions found"
            return
        
        # Prepare data for Excel
        df_excel = self.transactions_df.copy()
        
        # Format date column
        if 'date' in df_excel.columns:
            df_excel['date'] = pd.to_datetime(df_excel['date'], errors='coerce')
        
        # Reorder columns for better presentation
        column_order = ['date', 'description', 'amount', 'balance', 'transaction_type', 'bank', 'account', 'currency']
        existing_columns = [col for col in column_order if col in df_excel.columns]
        df_excel = df_excel[existing_columns]
        
        # Rename columns for better readability
        column_names = {
            'date': 'Date',
            'description': 'Description',
            'amount': 'Amount',
            'balance': 'Balance',
            'transaction_type': 'Type',
            'bank': 'Bank',
            'account': 'Account',
            'currency': 'Currency'
        }
        df_excel = df_excel.rename(columns=column_names)
        
        # Add data to worksheet
        for r in dataframe_to_rows(df_excel, index=False, header=True):
            ws.append(r)
        
        # Format header row
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
        
        # Format data rows
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                # Add borders
                thin_border = Border(
                    left=Side(style='thin'),
                    right=Side(style='thin'),
                    top=Side(style='thin'),
                    bottom=Side(style='thin')
                )
                cell.border = thin_border
                
                # Format amount columns
                if cell.column_letter in ['C', 'D']:  # Amount and Balance columns
                    cell.number_format = '#,##0.00'
                    if cell.value and cell.value < 0:
                        cell.font = Font(color="FF0000")  # Red for negative amounts
                
                # Format date column
                if cell.column_letter == 'A' and cell.value:
                    cell.number_format = 'DD/MM/YYYY'
        
        # Auto-adjust column widths
        for column in ws.columns:
            first = next((c for c in column if not isinstance(c, MergedCell)), column[0])
            col_letter = get_column_letter(first.column)
            max_length = max(len(str(c.value)) for c in column if c.value)
            ws.column_dimensions[col_letter].width = min(max_length + 2, 50)
        
        # Freeze header row
        ws.freeze_panes = 'A2'
    
    def _create_analysis_sheet(self):
        """Create analysis sheet with charts and insights."""
        ws = self.workbook.create_sheet("Analysis")
        
        if self.transactions_df.empty:
            ws['A1'] = "No data available for analysis"
            return
        
        # Transaction type analysis
        ws['A1'] = "Transaction Analysis"
        ws['A1'].font = Font(size=14, bold=True)
        
        # Count by transaction type
        type_counts = self.transactions_df['transaction_type'].value_counts()
        
        ws['A3'] = "Transaction Type Summary"
        ws['A3'].font = Font(bold=True)
        
        row = 4
        for trans_type, count in type_counts.items():
            ws[f'A{row}'] = trans_type
            ws[f'B{row}'] = count
            row += 1
        
        # Bank analysis
        if 'bank' in self.transactions_df.columns:
            bank_counts = self.transactions_df['bank'].value_counts()
            
            ws['D3'] = "Transactions by Bank"
            ws['D3'].font = Font(bold=True)
            
            row = 4
            for bank, count in bank_counts.items():
                ws[f'D{row}'] = bank
                ws[f'E{row}'] = count
                row += 1
        
        # Monthly spending analysis
        if 'date' in self.transactions_df.columns:
            df_copy = self.transactions_df.copy()
            df_copy['date'] = pd.to_datetime(df_copy['date'], errors='coerce')
            df_copy['month'] = df_copy['date'].dt.to_period('M')
            
            monthly_spending = df_copy[df_copy['amount'] < 0].groupby('month')['amount'].sum().abs()
            monthly_income = df_copy[df_copy['amount'] > 0].groupby('month')['amount'].sum()
            
            ws['G3'] = "Monthly Summary"
            ws['G3'].font = Font(bold=True)
            
            ws['G4'] = "Month"
            ws['H4'] = "Income"
            ws['I4'] = "Spending"
            ws['J4'] = "Net"
            
            # Header formatting
            for cell in [ws['G4'], ws['H4'], ws['I4'], ws['J4']]:
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
            
            row = 5
            for month in monthly_spending.index.union(monthly_income.index):
                income = monthly_income.get(month, 0)
                spending = monthly_spending.get(month, 0)
                net = income - spending
                
                ws[f'G{row}'] = str(month)
                ws[f'H{row}'] = income
                ws[f'I{row}'] = spending
                ws[f'J{row}'] = net
                
                # Format numbers
                for col in ['H', 'I', 'J']:
                    ws[f'{col}{row}'].number_format = '#,##0.00'
                    if col == 'J' and net < 0:
                        ws[f'{col}{row}'].font = Font(color="FF0000")
                
                row += 1
    
    def _create_monthly_summary_sheet(self):
        """Create monthly summary sheet."""
        ws = self.workbook.create_sheet("Monthly Summary")
        
        if self.transactions_df.empty:
            ws['A1'] = "No data available for monthly summary"
            return
        
        # Process data
        df_copy = self.transactions_df.copy()
        df_copy['date'] = pd.to_datetime(df_copy['date'], errors='coerce')
        df_copy = df_copy.dropna(subset=['date'])
        
        if df_copy.empty:
            ws['A1'] = "No valid dates found for monthly summary"
            return
        
        df_copy['year_month'] = df_copy['date'].dt.to_period('M')
        
        # Group by month and calculate summaries
        monthly_data = []
        for month, group in df_copy.groupby('year_month'):
            credits = group[group['amount'] > 0]['amount'].sum()
            debits = abs(group[group['amount'] < 0]['amount'].sum())
            net = credits - debits
            transaction_count = len(group)
            
            monthly_data.append({
                'Month': str(month),
                'Total Credits': credits,
                'Total Debits': debits,
                'Net Amount': net,
                'Transaction Count': transaction_count,
                'Average Transaction': group['amount'].mean()
            })
        
        # Create DataFrame and add to sheet
        monthly_df = pd.DataFrame(monthly_data)
        
        # Add title
        ws['A1'] = "Monthly Financial Summary"
        ws['A1'].font = Font(size=14, bold=True)
        ws.merge_cells('A1:F1')
        
        # Add data
        for r in dataframe_to_rows(monthly_df, index=False, header=True):
            ws.append(r)
        
        # Format header (row 3 since we added a title)
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        
        for cell in ws[3]:  # Header is now in row 3
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
        
        # Format data rows
        for row in ws.iter_rows(min_row=4):
            for cell in row:
                # Format monetary columns
                if cell.column_letter in ['B', 'C', 'D', 'F']:
                    cell.number_format = '#,##0.00'
                    if cell.value and cell.value < 0:
                        cell.font = Font(color="FF0000")
                
                # Format count column
                elif cell.column_letter == 'E':
                    cell.number_format = '#,##0'
        
        # Auto-adjust column widths
        for column in ws.columns:
            first = next((c for c in column if not isinstance(c, MergedCell)), column[0])
            col_letter = get_column_letter(first.column)
            max_length = max(len(str(c.value)) for c in column if c.value)
            ws.column_dimensions[col_letter].width = min(max_length + 2, 20)
