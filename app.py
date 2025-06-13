import streamlit as st
import pandas as pd
import io
import zipfile
from typing import List, Dict, Any
import tempfile
import os
import argparse
import logging

from pdf_processor import PDFProcessor
from excel_generator import ExcelGenerator
from utils import validate_pdf_files, format_currency, setup_logging, get_supported_banks

# Internacionalización sencilla
LANG = "es"
TRANSLATIONS = {
    "page_title": {
        "en": "Bank Statement Processor",
        "es": "Procesador de Extractos Bancarios",
    },
    "main_title": {
        "en": "🏦 Bank Statement PDF to Excel Converter",
        "es": "🏦 Convertidor de PDF de Extractos Bancarios a Excel",
    },
    "intro_text": {
        "en": "Upload multiple bank statement PDFs and get a structured Excel file with all transactions.",
        "es": "Sube varios PDFs de extractos bancarios y obt\u00E9n un archivo Excel con todas las transacciones.",
    },
    "debug_mode": {"en": "\U0001f41e Debug Mode", "es": "\U0001f41e Modo Depuraci\u00F3n"},
    "instructions_header": {"en": "\U0001f4cb Instructions", "es": "\U0001f4cb Instrucciones"},
    "instructions_text": {
        "en": """\n        **File Requirements:**\n        - PDF format only\n        - Text-based PDFs (not scanned images)\n        - Maximum 10 files per upload\n        - Maximum 50MB per file\n\n        **Output:**\n        - Structured Excel file\n        - Standardized transaction format\n        - Summary statistics\n        """,
        "es": """\n        **Requisitos de Archivo:**\n        - Solo formato PDF\n        - PDFs basados en texto (no im\u00E1genes escaneadas)\n        - M\u00E1ximo 10 archivos por carga\n        - M\u00E1ximo 50MB por archivo\n\n        **Salida:**\n        - Archivo Excel estructurado\n        - Formato de transacciones estandarizado\n        - Estad\u00EDsticas resumidas\n        """,
    },
    "supported_banks_header": {"en": "\U0001f3e6 Supported Banks", "es": "\U0001f3e6 Bancos Soportados"},
    "sample_header": {"en": "\U0001f4ca Sample Output Structure", "es": "\U0001f4ca Ejemplo de Estructura de Salida"},
    "sample_text": {
        "en": """\n        **Columns in Excel:**\n        - Date\n        - Description\n        - Amount\n        - Balance\n        - Bank\n        - Account\n        - Transaction Type\n        """,
        "es": """\n        **Columnas en Excel:**\n        - Fecha\n        - Descripci\u00F3n\n        - Monto\n        - Balance\n        - Banco\n        - Cuenta\n        - Tipo de Transacci\u00F3n\n        """,
    },
    "upload_header": {"en": "\U0001f4c1 Upload Bank Statements", "es": "\U0001f4c1 Sube Extractos Bancarios"},
    "file_uploader_label": {"en": "Choose PDF files", "es": "Elige archivos PDF"},
    "file_uploader_help": {
        "en": "Upload multiple bank statement PDF files. Maximum 10 files, 50MB each.",
        "es": "Sube varios archivos PDF de extractos bancarios. M\u00E1ximo 10 archivos, 50MB cada uno.",
    },
    "valid_files": {
        "en": "\u2705 {n} valid PDF files uploaded",
        "es": "\u2705 {n} archivos PDF v\u00E1lidos cargados",
    },
    "file_details": {"en": "\U0001f4c4 File Details", "es": "\U0001f4c4 Detalles de los Archivos"},
    "process_button": {"en": "\U0001f504 Process Statements", "es": "\U0001f504 Procesar Extractos"},
    "validation_failed": {"en": "\u274c File validation failed:", "es": "\u274c La validaci\u00F3n de archivos fall\u00F3:"},
    "processing_status_header": {"en": "\U0001f4c8 Processing Status", "es": "\U0001f4c8 Estado del Proceso"},
    "upload_and_click": {
        "en": "Upload PDF files and click 'Process Statements' to begin.",
        "es": "Sube archivos PDF y haz clic en 'Procesar Extractos' para comenzar.",
    },
    "processing_file": {
        "en": "Processing {name}... ({i}/{total})",
        "es": "Procesando {name}... ({i}/{total})",
    },
    "transactions_extracted": {
        "en": "\u2705 {name}: {count} transactions extracted",
        "es": "\u2705 {name}: {count} transacciones extra\u00EDdas",
    },
    "file_error": {
        "en": "\u274c {name}: {error}",
        "es": "\u274c {name}: {error}",
    },
    "error_processing_file": {
        "en": "\u274c Error processing {name}: {error}",
        "es": "\u274c Error procesando {name}: {error}",
    },
    "processing_complete_status": {"en": "Processing complete!", "es": "\u00A1Procesamiento completado!"},
    "final_success": {
        "en": "\U0001f389 Processing complete! {transactions} transactions from {files} files.",
        "es": "\U0001f389 \u00A1Procesamiento completado! {transactions} transacciones de {files} archivos.",
    },
    "no_transactions": {
        "en": "No transactions could be extracted from the uploaded files.",
        "es": "No se pudieron extraer transacciones de los archivos cargados.",
    },
    "processing_error": {
        "en": "\u274c An error occurred during processing: {error}",
        "es": "\u274c Ocurri\u00F3 un error durante el procesamiento: {error}",
    },
    "summary_header": {"en": "\U0001f4ca Processing Summary", "es": "\U0001f4ca Resumen del Proceso"},
    "metric_files": {"en": "Files Processed", "es": "Archivos Procesados"},
    "metric_transactions": {"en": "Total Transactions", "es": "Transacciones Totales"},
    "metric_banks": {"en": "Banks Detected", "es": "Bancos Detectados"},
    "metric_amount": {"en": "Total Amount", "es": "Monto Total"},
    "banks_detected_header": {"en": "\U0001f3db\ufe0f Banks Detected", "es": "\U0001f3db\ufe0f Bancos Detectados"},
    "processing_errors": {"en": "\u26a0\ufe0f Processing Errors", "es": "\u26a0\ufe0f Errores de Proceso"},
    "preview_header": {"en": "\U0001f4cb Transaction Preview", "es": "\U0001f4cb Vista Previa de Transacciones"},
    "showing_transactions": {
        "en": "Showing first 10 of {total} transactions. Download Excel file for complete data.",
        "es": "Mostrando las primeras 10 de {total} transacciones. Descarga el archivo Excel para ver todos los datos.",
    },
    "download_header": {"en": "\U0001f4be Download Results", "es": "\U0001f4be Descargar Resultados"},
    "download_excel": {"en": "\U0001f4e5 Download Excel File", "es": "\U0001f4e5 Descargar Archivo Excel"},
    "download_csv": {"en": "\U0001f4c4 Download CSV File", "es": "\U0001f4c4 Descargar Archivo CSV"},
    "process_new": {"en": "\U0001f504 Process New Files", "es": "\U0001f504 Procesar Nuevos Archivos"},
    "argparse_desc": {
        "en": "Bank Statement Processor",
        "es": "Procesador de Extractos Bancarios",
    },
    "argparse_debug": {"en": "Enable debug logging", "es": "Activar registro de depuraci\u00F3n"},
}

def tr(key: str, **kwargs) -> str:
    """Return the translated text for the current language."""
    text = TRANSLATIONS.get(key, {}).get(LANG, key)
    if kwargs:
        return text.format(**kwargs)
    return text

def main(debug: bool = False, lang: str = LANG):
    """Launch the Streamlit application."""
    global LANG
    LANG = lang

    setup_logging()
    logger = logging.getLogger()

    st.set_page_config(
        page_title=tr("page_title"),
        page_icon="🏦",
        layout="wide"
    )
    
    st.title(tr("main_title"))
    st.markdown(tr("intro_text"))
    
    # Initialize session state
    if 'processed_data' not in st.session_state:
        st.session_state.processed_data = None
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False
    
    # Sidebar with instructions and debug toggle
    with st.sidebar:
        debug_enabled = st.checkbox(tr("debug_mode"), value=debug, key="debug_logging")
        st.header(tr("instructions_header"))
        st.markdown(tr("instructions_text"))

        st.header(tr("supported_banks_header"))
        for bank in get_supported_banks():
            st.markdown(f"- {bank}")

        st.header(tr("sample_header"))
        st.markdown(tr("sample_text"))

        # Ajustar nivel de logging según el estado del checkbox
        if debug_enabled:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header(tr("upload_header"))
        
        uploaded_files = st.file_uploader(
            tr("file_uploader_label"),
            type=['pdf'],
            accept_multiple_files=True,
            help="Upload multiple bank statement PDF files. Maximum 10 files, 50MB each."
        )
        
        if uploaded_files:
            # Validate files
            validation_results = validate_pdf_files(uploaded_files)
            
            if validation_results['valid']:
                st.success(tr("valid_files", n=len(uploaded_files)))
                
                # Display file information
                with st.expander(tr("file_details"), expanded=True):
                    for i, file in enumerate(uploaded_files):
                        file_size = len(file.getvalue()) / (1024 * 1024)  # MB
                        st.write(f"**{i+1}.** {file.name} - {file_size:.2f} MB")
                
                # Process button
                if st.button(tr("process_button"), type="primary", use_container_width=True):
                    process_files(uploaded_files, debug=debug_enabled)
                    
            else:
                st.error(tr("validation_failed"))
                for error in validation_results['errors']:
                    st.error(f"• {error}")
    
    with col2:
        st.header(tr("processing_status_header"))
        
        if st.session_state.processing_complete and st.session_state.processed_data:
            display_results()
        else:
            st.info(tr("upload_and_click"))

def process_files(uploaded_files: List[Any], debug: bool = False):
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
            status_text.text(tr("processing_file", name=uploaded_file.name, i=i+1, total=len(uploaded_files)))
            
            try:
                # Save uploaded file temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                
                # Process PDF
                result = pdf_processor.process_pdf(tmp_file_path, uploaded_file.name, debug=debug)
                
                if result['success']:
                    transactions = result['transactions']
                    all_transactions.extend(transactions)
                    processing_summary['successful_files'] += 1
                    processing_summary['total_transactions'] += len(transactions)
                    processing_summary['banks_detected'].add(result.get('bank_name', result['bank_detected']))

                    st.success(tr("transactions_extracted", name=uploaded_file.name, count=len(transactions)))
                else:
                    processing_summary['failed_files'] += 1
                    processing_summary['errors'].append(f"{uploaded_file.name}: {result['error']}")
                    st.error(tr("file_error", name=uploaded_file.name, error=result['error']))

                if debug and result.get('debug_log'):
                    with st.expander(f"Debug Log for {uploaded_file.name}"):
                        for step in result['debug_log']:
                            st.write(step)
                
                # Cleanup temporary file
                os.unlink(tmp_file_path)
                
            except Exception as e:
                processing_summary['failed_files'] += 1
                processing_summary['errors'].append(f"{uploaded_file.name}: {str(e)}")
                st.error(tr("error_processing_file", name=uploaded_file.name, error=str(e)))
        
        # Complete processing
        progress_bar.progress(1.0)
        status_text.text(tr("processing_complete_status"))
        
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
            
            st.success(tr("final_success", transactions=processing_summary['total_transactions'], files=processing_summary['successful_files']))
            st.rerun()
        else:
            st.error(tr("no_transactions"))
            
    except Exception as e:
        st.error(tr("processing_error", error=str(e)))
        progress_bar.empty()
        status_text.empty()

def display_results():
    """Display processing results and download options."""
    
    data = st.session_state.processed_data
    summary = data['summary']
    transactions = data['transactions']
    
    # Summary metrics
    st.header(tr("summary_header"))
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(tr("metric_files"), f"{summary['successful_files']}/{summary['total_files']}")
    with col2:
        st.metric(tr("metric_transactions"), summary['total_transactions'])
    with col3:
        st.metric(tr("metric_banks"), len(summary['banks_detected']))
    with col4:
        total_amount = sum(float(t.get('amount', 0)) for t in transactions if t.get('amount'))
        st.metric(tr("metric_amount"), format_currency(total_amount))
    
    # Banks detected
    if summary['banks_detected']:
        st.subheader(tr("banks_detected_header"))
        banks_text = ", ".join(sorted(summary['banks_detected']))
        st.write(banks_text)
    
    # Errors if any
    if summary['errors']:
        with st.expander(tr("processing_errors"), expanded=False):
            for error in summary['errors']:
                st.error(error)
    
    # Transaction preview
    if transactions:
        st.subheader(tr("preview_header"))
        
        # Convert to DataFrame for display
        df = pd.DataFrame(transactions)
        
        # Display first 10 transactions
        st.dataframe(
            df.head(10),
            use_container_width=True,
            hide_index=True
        )
        
        if len(transactions) > 10:
            st.info(tr("showing_transactions", total=len(transactions)))
    
    # Download section
    st.header(tr("download_header"))
    
    col1, col2 = st.columns(2)
    
    with col1:
        if data['excel_data']:
            st.download_button(
                label=tr("download_excel"),
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
                label=tr("download_csv"),
                data=csv_data,
                file_name=f"bank_statements_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    # Reset button
    if st.button(tr("process_new"), use_container_width=True):
        st.session_state.processed_data = None
        st.session_state.processing_complete = False
        st.rerun()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=tr("argparse_desc"))
    parser.add_argument("--debug", action="store_true", help=tr("argparse_debug"))
    parser.add_argument("--lang", choices=["en", "es"], default=LANG, help="UI language")
    args, _ = parser.parse_known_args()
    main(debug=args.debug, lang=args.lang)
