import streamlit as st
import pandas as pd
import io
import zipfile
from typing import List, Dict, Any
import tempfile
import os

from pdf_processor import PDFProcessor
from excel_generator import ExcelGenerator
from utils import validate_pdf_files, format_currency

def main():
    st.set_page_config(
        page_title="Bank Statement Processor",
        page_icon="🏦",
        layout="wide"
    )
    
    st.title("🏦 Bank Statement PDF to Excel Converter")
    st.markdown("Upload multiple bank statement PDFs and get a structured Excel file with all transactions.")
    
    # Initialize session state
    if 'processed_data' not in st.session_state:
        st.session_state.processed_data = None
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False
    
    # Sidebar with instructions
    with st.sidebar:
        st.header("📋 Instructions")
        st.markdown("""
        **Supported Banks:**
        - Most common banks (PDF text format)
        - Spanish banks (Santander, BBVA, CaixaBank, etc.)
        - International banks with standard formats
        
        **File Requirements:**
        - PDF format only
        - Text-based PDFs (not scanned images)
        - Maximum 10 files per upload
        - Maximum 50MB per file
        
        **Output:**
        - Structured Excel file
        - Standardized transaction format
        - Summary statistics
        """)
        
        st.header("📊 Sample Output Structure")
        st.markdown("""
        **Columns in Excel:**
        - Date
        - Description
        - Amount
        - Balance
        - Bank
        - Account
        - Transaction Type
        """)
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📁 Upload Bank Statements")
        
        uploaded_files = st.file_uploader(
            "Choose PDF files",
            type=['pdf'],
            accept_multiple_files=True,
            help="Upload multiple bank statement PDF files. Maximum 10 files, 50MB each."
        )
        
        if uploaded_files:
            # Validate files
            validation_results = validate_pdf_files(uploaded_files)
            
            if validation_results['valid']:
                st.success(f"✅ {len(uploaded_files)} valid PDF files uploaded")
                
                # Display file information
                with st.expander("📄 File Details", expanded=True):
                    for i, file in enumerate(uploaded_files):
                        file_size = len(file.getvalue()) / (1024 * 1024)  # MB
                        st.write(f"**{i+1}.** {file.name} - {file_size:.2f} MB")
                
                # Process button
                if st.button("🔄 Process Statements", type="primary", use_container_width=True):
                    process_files(uploaded_files)
                    
            else:
                st.error("❌ File validation failed:")
                for error in validation_results['errors']:
                    st.error(f"• {error}")
    
    with col2:
        st.header("📈 Processing Status")
        
        if st.session_state.processing_complete and st.session_state.processed_data:
            display_results()
        else:
            st.info("Upload PDF files and click 'Process Statements' to begin.")

def process_files(uploaded_files: List[Any]):
    """Process uploaded PDF files and extract transaction data."""
    
    # Initialize progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Initialize processor
        pdf_processor = PDFProcessor()
        all_transactions = []
        processing_summary = {
            'total_files': len(uploaded_files),
            'successful_files': 0,
            'failed_files': 0,
            'total_transactions': 0,
            'banks_detected': set(),
            'errors': []
        }
        
        # Process each file
        for i, uploaded_file in enumerate(uploaded_files):
            progress = (i + 1) / len(uploaded_files)
            progress_bar.progress(progress)
            status_text.text(f"Processing {uploaded_file.name}... ({i+1}/{len(uploaded_files)})")
            
            try:
                # Save uploaded file temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                
                # Process PDF
                result = pdf_processor.process_pdf(tmp_file_path, uploaded_file.name)
                
                if result['success']:
                    transactions = result['transactions']
                    all_transactions.extend(transactions)
                    processing_summary['successful_files'] += 1
                    processing_summary['total_transactions'] += len(transactions)
                    processing_summary['banks_detected'].add(result['bank_detected'])
                    
                    st.success(f"✅ {uploaded_file.name}: {len(transactions)} transactions extracted")
                else:
                    processing_summary['failed_files'] += 1
                    processing_summary['errors'].append(f"{uploaded_file.name}: {result['error']}")
                    st.error(f"❌ {uploaded_file.name}: {result['error']}")
                
                # Cleanup temporary file
                os.unlink(tmp_file_path)
                
            except Exception as e:
                processing_summary['failed_files'] += 1
                processing_summary['errors'].append(f"{uploaded_file.name}: {str(e)}")
                st.error(f"❌ Error processing {uploaded_file.name}: {str(e)}")
        
        # Complete processing
        progress_bar.progress(1.0)
        status_text.text("Processing complete!")
        
        if all_transactions:
            # Generate Excel file
            excel_generator = ExcelGenerator()
            excel_data = excel_generator.create_excel_file(all_transactions, processing_summary)
            
            # Store results in session state
            st.session_state.processed_data = {
                'excel_data': excel_data,
                'transactions': all_transactions,
                'summary': processing_summary
            }
            st.session_state.processing_complete = True
            
            st.success(f"🎉 Processing complete! {processing_summary['total_transactions']} transactions from {processing_summary['successful_files']} files.")
            st.rerun()
        else:
            st.error("No transactions could be extracted from the uploaded files.")
            
    except Exception as e:
        st.error(f"❌ An error occurred during processing: {str(e)}")
        progress_bar.empty()
        status_text.empty()

def display_results():
    """Display processing results and download options."""
    
    data = st.session_state.processed_data
    summary = data['summary']
    transactions = data['transactions']
    
    # Summary metrics
    st.header("📊 Processing Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Files Processed", f"{summary['successful_files']}/{summary['total_files']}")
    with col2:
        st.metric("Total Transactions", summary['total_transactions'])
    with col3:
        st.metric("Banks Detected", len(summary['banks_detected']))
    with col4:
        total_amount = sum(float(t.get('amount', 0)) for t in transactions if t.get('amount'))
        st.metric("Total Amount", format_currency(total_amount))
    
    # Banks detected
    if summary['banks_detected']:
        st.subheader("🏛️ Banks Detected")
        banks_text = ", ".join(sorted(summary['banks_detected']))
        st.write(banks_text)
    
    # Errors if any
    if summary['errors']:
        with st.expander("⚠️ Processing Errors", expanded=False):
            for error in summary['errors']:
                st.error(error)
    
    # Transaction preview
    if transactions:
        st.subheader("📋 Transaction Preview")
        
        # Convert to DataFrame for display
        df = pd.DataFrame(transactions)
        
        # Display first 10 transactions
        st.dataframe(
            df.head(10),
            use_container_width=True,
            hide_index=True
        )
        
        if len(transactions) > 10:
            st.info(f"Showing first 10 of {len(transactions)} transactions. Download Excel file for complete data.")
    
    # Download section
    st.header("💾 Download Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if data['excel_data']:
            st.download_button(
                label="📥 Download Excel File",
                data=data['excel_data'],
                file_name=f"bank_statements_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )
    
    with col2:
        # CSV download as backup
        if transactions:
            df = pd.DataFrame(transactions)
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="📄 Download CSV File",
                data=csv_data,
                file_name=f"bank_statements_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    # Reset button
    if st.button("🔄 Process New Files", use_container_width=True):
        st.session_state.processed_data = None
        st.session_state.processing_complete = False
        st.rerun()

if __name__ == "__main__":
    main()
