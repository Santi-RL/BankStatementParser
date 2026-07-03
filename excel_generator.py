import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.utils import get_column_letter
from openpyxl.cell.cell import MergedCell
import io
import re
from numbers import Real
from typing import List, Dict, Any
from datetime import datetime

from utils import format_currency, get_transaction_currencies, resolve_single_currency


FORMULA_TRIGGER_CHARACTERS = ("=", "+", "-", "@", "\t", "\r", "\n")


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
        self._create_scope_transaction_sheets()
        self._create_analysis_sheet()
        self._create_monthly_summary_sheet()
        
        # Save to bytes
        excel_buffer = io.BytesIO()
        self.workbook.save(excel_buffer)
        excel_buffer.seek(0)
        
        return excel_buffer.getvalue()

    def _transaction_currency_list(self) -> List[str]:
        if self.transactions_df is None or self.transactions_df.empty:
            return []
        return get_transaction_currencies(self.transactions_df.to_dict("records"))

    def _single_transaction_currency(self) -> str | None:
        if self.transactions_df is None or self.transactions_df.empty:
            return None
        return resolve_single_currency(self.transactions_df.to_dict("records"))

    def _display_financial_amount(self, amount: float, multiple_currency_label: str) -> str:
        currencies = self._transaction_currency_list()
        if len(currencies) > 1:
            return multiple_currency_label
        return format_currency(amount, self._single_transaction_currency())

    def _safe_excel_value(self, value: Any) -> Any:
        if isinstance(value, str) and value.startswith(FORMULA_TRIGGER_CHARACTERS):
            return f"'{value}"
        return value

    def _set_cell_value(self, worksheet, coordinate: str, value: Any):
        worksheet[coordinate] = self._safe_excel_value(value)

    def _append_dataframe_rows(self, worksheet, dataframe: pd.DataFrame):
        for row in dataframe_to_rows(dataframe, index=False, header=True):
            worksheet.append([self._safe_excel_value(value) for value in row])

    def _currency_bucket_series(self, dataframe: pd.DataFrame) -> pd.Series:
        if 'currency' not in dataframe.columns:
            return pd.Series(["N/A"] * len(dataframe), index=dataframe.index)
        return (
            dataframe['currency']
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
            .replace("", "N/A")
        )

    def _monthly_summary_rows(self, dataframe: pd.DataFrame) -> tuple[List[Dict[str, Any]], bool]:
        df_copy = dataframe.copy()
        df_copy['date'] = pd.to_datetime(df_copy['date'], errors='coerce')
        df_copy = df_copy.dropna(subset=['date'])

        if df_copy.empty:
            return [], False

        df_copy['year_month'] = df_copy['date'].dt.to_period('M')
        df_copy['currency_bucket'] = self._currency_bucket_series(df_copy)
        split_by_currency = df_copy['currency_bucket'].nunique(dropna=False) > 1
        group_columns = ['year_month', 'currency_bucket'] if split_by_currency else ['year_month']

        monthly_data = []
        for group_key, group in df_copy.groupby(group_columns, sort=True):
            if split_by_currency:
                month, currency = group_key
            else:
                month = group_key
                currency = None

            credits = group[group['amount'] > 0]['amount'].sum()
            debits = abs(group[group['amount'] < 0]['amount'].sum())
            net = credits - debits
            row = {
                'Month': str(month),
                'Total Credits': credits,
                'Total Debits': debits,
                'Net Amount': net,
                'Transaction Count': len(group),
                'Average Transaction': group['amount'].mean(),
            }
            if split_by_currency:
                row = {
                    'Month': str(month),
                    'Currency': currency,
                    **{key: value for key, value in row.items() if key != 'Month'},
                }
            monthly_data.append(row)

        return monthly_data, split_by_currency
    
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
        self._set_cell_value(ws, 'B13', ", ".join(sorted(summary['banks_detected'])))

        currencies = self._transaction_currency_list()
        ws['A14'] = "Currencies Detected:"
        self._set_cell_value(ws, 'B14', ", ".join(currencies) if currencies else "N/A")

        selected_scopes = summary.get('selected_scopes', [])
        if selected_scopes:
            ws['A16'] = "Selected Scopes"
            ws['A16'].font = Font(bold=True, size=12)
            ws['A17'] = "Label"
            ws['B17'] = "Type"
            ws['C17'] = "Currency"
            for cell in [ws['A17'], ws['B17'], ws['C17']]:
                cell.font = Font(bold=True)

            row = 18
            for scope in selected_scopes:
                self._set_cell_value(ws, f'A{row}', scope.get('label', ''))
                self._set_cell_value(ws, f'B{row}', scope.get('product_type', ''))
                self._set_cell_value(ws, f'C{row}', scope.get('currency', ''))
                row += 1
        else:
            row = 16
        
        # Transaction totals
        if not self.transactions_df.empty:
            total_credits = self.transactions_df[self.transactions_df['amount'] > 0]['amount'].sum()
            total_debits = abs(self.transactions_df[self.transactions_df['amount'] < 0]['amount'].sum())
            net_amount = total_credits - total_debits
            
            summary_row = row if selected_scopes else 16
            ws[f'A{summary_row}'] = "Financial Summary"
            ws[f'A{summary_row}'].font = Font(bold=True, size=12)
            
            ws[f'A{summary_row + 1}'] = "Total Credits:"
            self._set_cell_value(
                ws,
                f'B{summary_row + 1}',
                self._display_financial_amount(total_credits, "N/A (multiple currencies)"),
            )
            
            ws[f'A{summary_row + 2}'] = "Total Debits:"
            self._set_cell_value(
                ws,
                f'B{summary_row + 2}',
                self._display_financial_amount(total_debits, "N/A (multiple currencies)"),
            )
            
            ws[f'A{summary_row + 3}'] = "Net Amount:"
            net_display = self._display_financial_amount(net_amount, "N/A (multiple currencies)")
            self._set_cell_value(ws, f'B{summary_row + 3}', net_display)
            if isinstance(net_display, str) and net_display.startswith("N/A"):
                pass
            elif net_amount < 0:
                ws[f'B{summary_row + 3}'].font = Font(color="FF0000")
            else:
                ws[f'B{summary_row + 3}'].font = Font(color="008000")
        
        # Errors section
        if summary['errors']:
            error_row = max(20, row + 6)
            ws[f'A{error_row}'] = "Processing Errors"
            ws[f'A{error_row}'].font = Font(bold=True, size=12, color="FF0000")
            
            row = error_row + 1
            for error in summary['errors']:
                self._set_cell_value(ws, f'A{row}', error)
                ws[f'A{row}'].font = Font(color="FF0000")
                row += 1
        
        # Auto-adjust column widths
        for column in ws.columns:
            first = next((c for c in column if not isinstance(c, MergedCell)), column[0])
            col_letter = get_column_letter(first.column)
            lengths = [len(str(c.value)) for c in column if c.value]
            max_length = max(lengths) if lengths else 0
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
        column_order.extend(['scope_label', 'product_type', 'linked_account', 'source_file'])
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
            'currency': 'Currency',
            'scope_label': 'Scope',
            'product_type': 'Product Type',
            'linked_account': 'Linked Account',
            'source_file': 'Source File',
        }
        df_excel = df_excel.rename(columns=column_names)
        
        # Add data to worksheet
        self._append_dataframe_rows(ws, df_excel)
        
        # Format header row
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
        
        # Format data rows
        header_columns = {cell.value: cell.column for cell in ws[1]}
        amount_columns = {
            column
            for column in [
                header_columns.get('Amount'),
                header_columns.get('Balance'),
            ]
            if column is not None
        }
        date_column = header_columns.get('Date')

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
                if cell.column in amount_columns:
                    cell.number_format = '#,##0.00'
                    if isinstance(cell.value, Real) and not isinstance(cell.value, bool) and cell.value < 0:
                        cell.font = Font(color="FF0000")  # Red for negative amounts
                
                # Format date column
                if cell.column == date_column and cell.value:
                    cell.number_format = 'DD/MM/YYYY'
        
        # Auto-adjust column widths
        for column in ws.columns:
            first = next((c for c in column if not isinstance(c, MergedCell)), column[0])
            col_letter = get_column_letter(first.column)
            lengths = [len(str(c.value)) for c in column if c.value]
            max_length = max(lengths) if lengths else 0
            ws.column_dimensions[col_letter].width = min(max_length + 2, 50)
        
        # Freeze header row
        ws.freeze_panes = 'A2'

    def _create_scope_transaction_sheets(self):
        if self.transactions_df is None or self.transactions_df.empty:
            return

        if 'scope_label' not in self.transactions_df.columns:
            return

        grouped = self.transactions_df.dropna(subset=['scope_label']).groupby(['bank', 'scope_label'], sort=True)
        used_titles: set[str] = set(self.workbook.sheetnames)
        for (bank, scope_label), group in grouped:
            title = self._unique_sheet_title(f"{bank[:8]} {scope_label}", used_titles)
            used_titles.add(title)
            ws = self.workbook.create_sheet(title)
            df_scope = group.copy()
            if 'date' in df_scope.columns:
                df_scope['date'] = pd.to_datetime(df_scope['date'], errors='coerce')

            column_order = ['date', 'description', 'amount', 'balance', 'transaction_type', 'bank', 'account', 'currency', 'scope_label', 'product_type', 'linked_account', 'source_file']
            existing_columns = [col for col in column_order if col in df_scope.columns]
            df_scope = df_scope[existing_columns]
            self._append_dataframe_rows(ws, df_scope)

            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_font = Font(color="FFFFFF", bold=True)
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center')

            for column in ws.columns:
                first = next((c for c in column if not isinstance(c, MergedCell)), column[0])
                col_letter = get_column_letter(first.column)
                lengths = [len(str(c.value)) for c in column if c.value]
                max_length = max(lengths) if lengths else 0
                ws.column_dimensions[col_letter].width = min(max_length + 2, 50)
            ws.freeze_panes = 'A2'

    def _unique_sheet_title(self, base_title: str, used_titles: set[str]) -> str:
        cleaned = "".join(" " if character in '[]:*?/\\\\' else character for character in base_title)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip() or "Scope"
        cleaned = cleaned[:31].rstrip() or "Scope"
        candidate = cleaned
        index = 2
        normalized_used_titles = {title.lower() for title in used_titles}
        while candidate.lower() in normalized_used_titles:
            suffix = f" {index}"
            candidate = f"{cleaned[:31 - len(suffix)]}{suffix}"
            index += 1
        return candidate
    
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
            self._set_cell_value(ws, f'A{row}', trans_type)
            ws[f'B{row}'] = count
            row += 1
        
        # Bank analysis
        if 'bank' in self.transactions_df.columns:
            bank_counts = self.transactions_df['bank'].value_counts()
            
            ws['D3'] = "Transactions by Bank"
            ws['D3'].font = Font(bold=True)
            
            row = 4
            for bank, count in bank_counts.items():
                self._set_cell_value(ws, f'D{row}', bank)
                ws[f'E{row}'] = count
                row += 1
        
        # Monthly spending analysis
        if 'date' in self.transactions_df.columns:
            monthly_data, split_by_currency = self._monthly_summary_rows(self.transactions_df)
            
            ws['G3'] = "Monthly Summary"
            ws['G3'].font = Font(bold=True)

            headers = ["Month"]
            if split_by_currency:
                headers.append("Currency")
            headers.extend(["Income", "Spending", "Net"])
            start_column = 7
            for offset, header in enumerate(headers):
                cell = ws.cell(row=4, column=start_column + offset, value=header)
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
            
            row = 5
            for monthly_row in monthly_data:
                values = [monthly_row["Month"]]
                if split_by_currency:
                    values.append(monthly_row["Currency"])
                values.extend([
                    monthly_row["Total Credits"],
                    monthly_row["Total Debits"],
                    monthly_row["Net Amount"],
                ])
                for offset, value in enumerate(values):
                    cell = ws.cell(row=row, column=start_column + offset, value=self._safe_excel_value(value))
                    if headers[offset] in {"Income", "Spending", "Net"}:
                        cell.number_format = '#,##0.00'
                    if headers[offset] == "Net" and isinstance(value, Real) and not isinstance(value, bool) and value < 0:
                        cell.font = Font(color="FF0000")
                
                row += 1
    
    def _create_monthly_summary_sheet(self):
        """Create monthly summary sheet."""
        ws = self.workbook.create_sheet("Monthly Summary")
        
        if self.transactions_df.empty:
            ws['A1'] = "No data available for monthly summary"
            return
        
        # Process data
        monthly_data, split_by_currency = self._monthly_summary_rows(self.transactions_df)

        if not monthly_data:
            ws['A1'] = "No valid dates found for monthly summary"
            return
        
        # Create DataFrame and add to sheet
        monthly_df = pd.DataFrame(monthly_data)
        
        # Add title
        ws['A1'] = "Monthly Financial Summary"
        ws['A1'].font = Font(size=14, bold=True)
        title_end_column = 'G' if split_by_currency else 'F'
        ws.merge_cells(f'A1:{title_end_column}1')
        
        # Add data
        self._append_dataframe_rows(ws, monthly_df)
        
        # Format header (row 2 since we only added a title row)
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        
        for cell in ws[2]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
        
        # Format data rows
        header_columns = {cell.value: cell.column for cell in ws[2]}
        monetary_columns = {
            column
            for column in [
                header_columns.get('Total Credits'),
                header_columns.get('Total Debits'),
                header_columns.get('Net Amount'),
                header_columns.get('Average Transaction'),
            ]
            if column is not None
        }
        count_column = header_columns.get('Transaction Count')

        for row in ws.iter_rows(min_row=3):
            for cell in row:
                # Format monetary columns
                if cell.column in monetary_columns:
                    cell.number_format = '#,##0.00'
                    if isinstance(cell.value, Real) and not isinstance(cell.value, bool) and cell.value < 0:
                        cell.font = Font(color="FF0000")
                
                # Format count column
                elif cell.column == count_column:
                    cell.number_format = '#,##0'
        
        # Auto-adjust column widths
        for column in ws.columns:
            first = next((c for c in column if not isinstance(c, MergedCell)), column[0])
            col_letter = get_column_letter(first.column)
            lengths = [len(str(c.value)) for c in column if c.value]
            max_length = max(lengths) if lengths else 0
            ws.column_dimensions[col_letter].width = min(max_length + 2, 20)
