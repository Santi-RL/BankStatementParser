import streamlit as st
import pandas as pd
from contextlib import nullcontext
from typing import List, Dict, Any, Optional
import argparse
import logging
import hashlib
import importlib
from pathlib import Path
import re
import toml

from format_engine import FormatRegistry, FormatSpec
from format_training import build_initial_spec, extract_text_from_pdf, publish_spec, save_draft
from pdf_processor import PDFProcessor
from reconciliation import aggregate_reconciliation_status
import utils as _utils

# Streamlit Cloud may rerun app.py after pulling code without clearing cached helper modules.
if not hasattr(_utils, "user_facing_product_type"):
    _utils = importlib.reload(_utils)

import excel_generator as _excel_generator

if not hasattr(_excel_generator.ExcelGenerator, "_prepare_transaction_export_dataframe"):
    _excel_generator = importlib.reload(_excel_generator)

ExcelGenerator = _excel_generator.ExcelGenerator
from utils import (
    escape_spreadsheet_formula_value,
    format_currency,
    get_supported_banks,
    get_transaction_currencies,
    resolve_single_currency,
    set_logging_level,
    setup_logging,
    temporary_pdf_copy,
    user_facing_product_type,
    user_facing_transaction_records,
    validate_pdf_files,
)

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
        "es": """\n        **Columnas en Excel:**\n        - Fecha\n        - Descripci\u00F3n\n        - Monto\n        - Saldo\n        - Banco\n        - Cuenta\n        - Tipo de movimiento\n        """,
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
    "analysis_error_safe": {
        "en": "\u274c Could not analyze the uploaded files. Check logs/app.log.",
        "es": "\u274c No se pudieron analizar los archivos cargados. Revis\u00E1 logs/app.log.",
    },
    "processing_error_safe": {
        "en": "\u274c Could not complete processing. Check logs/app.log.",
        "es": "\u274c No se pudo completar el procesamiento. Revis\u00E1 logs/app.log.",
    },
    "error_processing_file_safe": {
        "en": "\u274c Error processing {name}. Check logs/app.log.",
        "es": "\u274c Error procesando {name}. Revis\u00E1 logs/app.log.",
    },
    "summary_header": {"en": "\U0001f4ca Processing Summary", "es": "\U0001f4ca Resumen del Proceso"},
    "metric_files": {"en": "Files Processed", "es": "Archivos Procesados"},
    "metric_transactions": {"en": "Total Transactions", "es": "Transacciones Totales"},
    "metric_banks": {"en": "Banks Detected", "es": "Bancos Detectados"},
    "metric_amount": {"en": "Total Amount", "es": "Monto Total"},
    "metric_amount_multiple_currencies": {"en": "N/A (multiple currencies)", "es": "No aplica (m\u00FAltiples monedas)"},
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
    "argparse_mode": {"en": "Execution mode", "es": "Modo de ejecuci\u00F3n"},
}

def tr(key: str, **kwargs) -> str:
    """Return the translated text for the current language."""
    text = TRANSLATIONS.get(key, {}).get(LANG, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def _suggest_format_id(name: str) -> str:
    base = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')
    return base or "draft"


def _multiline_text_to_list(value: str) -> List[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


def _registry_summary(registry: FormatRegistry) -> Dict[str, List[FormatSpec]]:
    return {
        "published": registry.specs_by_status("published"),
        "drafts": registry.list_drafts(),
    }


def _uploaded_file_id(uploaded_file: Any) -> str:
    payload = uploaded_file.getvalue()
    uploaded_file.seek(0)
    return hashlib.sha256(payload).hexdigest()[:12]


def _uploaded_files_signature(uploaded_files: List[Any]) -> tuple[str, ...]:
    return tuple(f"{uploaded_file.name}:{len(uploaded_file.getvalue())}:{_uploaded_file_id(uploaded_file)}" for uploaded_file in uploaded_files)


def _build_user_facing_dataframe(transactions: List[Dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(user_facing_transaction_records(transactions))


def _build_csv_export(transactions: List[Dict[str, Any]]) -> str:
    dataframe = _build_user_facing_dataframe(transactions)
    safe_dataframe = dataframe.map(escape_spreadsheet_formula_value)
    return safe_dataframe.to_csv(index=False)


def _clear_scope_selection_state(file_id: Optional[str] = None):
    prefix = "scope_select_" if file_id is None else f"scope_select_{file_id}_"
    for key in list(st.session_state.keys()):
        if key.startswith(prefix):
            del st.session_state[key]


def _clear_format_selection_state():
    for key in list(st.session_state.keys()):
        if key.startswith("format_select_"):
            del st.session_state[key]


def _format_selector_key(file_id: str) -> str:
    return f"format_select_{file_id}"


def _format_option_key(bank_id: str, format_id: str) -> str:
    return f"{bank_id}/{format_id}"


def _parse_format_option(value: str) -> Optional[Dict[str, str]]:
    if not value or value == "auto":
        return None
    bank_id, separator, format_id = value.partition("/")
    if not separator or not bank_id or not format_id:
        return None
    return {"bank_id": bank_id, "format_id": format_id}


def _analysis_format_option(analysis: Dict[str, Any]) -> Optional[str]:
    bank_detected = str(analysis.get("bank_detected") or "").strip()
    format_id = str(analysis.get("format_id") or "").strip()
    if not bank_detected or not format_id:
        return None
    return _format_option_key(bank_detected, format_id)


def _entry_selected_format_option(entry: Dict[str, Any]) -> str:
    override = entry.get("applied_override")
    if override:
        return _format_option_key(override["bank_id"], override["format_id"])
    return "auto"


def _build_analysis_entry(
    file_id: str,
    file_name: str,
    auto_analysis: Dict[str, Any],
    effective_analysis: Optional[Dict[str, Any]] = None,
    applied_override: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    return {
        "file_id": file_id,
        "file_name": file_name,
        "auto_analysis": auto_analysis,
        "analysis": effective_analysis or auto_analysis,
        "applied_override": applied_override,
    }


def _scope_checkbox_key(file_id: str, scope_id: str) -> str:
    return f"scope_select_{file_id}_{scope_id}"


def _selected_scope_ids(file_id: str, scopes: List[Dict[str, Any]]) -> List[str]:
    selected: List[str] = []
    for scope in scopes:
        if st.session_state.get(_scope_checkbox_key(file_id, scope["id"]), False):
            selected.append(scope["id"])
    return selected


def _apply_scope_preset(file_id: str, scopes: List[Dict[str, Any]], allowed_product_types: set[str] | None = None):
    for scope in scopes:
        selected = allowed_product_types is None or scope.get("product_type") in allowed_product_types
        st.session_state[_scope_checkbox_key(file_id, scope["id"])] = selected


def _sync_scope_selection_state(file_id: str, scopes: List[Dict[str, Any]]):
    expected_keys = {_scope_checkbox_key(file_id, scope["id"]) for scope in scopes}
    for key in list(st.session_state.keys()):
        if key.startswith(f"scope_select_{file_id}_") and key not in expected_keys:
            del st.session_state[key]
    for key in expected_keys:
        st.session_state.setdefault(key, False)


def _seed_training_from_result(file_name: str, result: Dict[str, Any]):
    st.session_state.training_seed = {
        'file_name': file_name,
        'bank_detected': result.get('bank_detected', 'unknown'),
        'bank_name': result.get('bank_name', ''),
        'extracted_text': result.get('extracted_text', ''),
        'diagnostics': result.get('diagnostics', {}),
        'suggested_format_id': _suggest_format_id(file_name),
    }


def _analyze_uploaded_file(
    uploaded_file: Any,
    pdf_processor: PDFProcessor,
    debug: bool = False,
    override: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    with temporary_pdf_copy(uploaded_file.getvalue()) as tmp_file_path:
        return pdf_processor.analyze_pdf(
            tmp_file_path,
            uploaded_file.name,
            debug=debug,
            override_bank_id=override["bank_id"] if override else None,
            override_format_id=override["format_id"] if override else None,
        )


def _build_effective_analysis_entry(
    uploaded_file: Any,
    pdf_processor: PDFProcessor,
    debug: bool = False,
    override: Optional[Dict[str, str]] = None,
    auto_analysis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    file_id = _uploaded_file_id(uploaded_file)
    auto_result = auto_analysis or _analyze_uploaded_file(uploaded_file, pdf_processor, debug=debug)
    effective_analysis = auto_result
    applied_override = None
    if override is not None:
        effective_analysis = _analyze_uploaded_file(uploaded_file, pdf_processor, debug=debug, override=override)
        applied_override = override

    entry = _build_analysis_entry(
        file_id=file_id,
        file_name=uploaded_file.name,
        auto_analysis=auto_result,
        effective_analysis=effective_analysis,
        applied_override=applied_override,
    )
    scopes = effective_analysis.get("available_scopes", []) if effective_analysis.get("success") and effective_analysis.get("multi_scope") else []
    _sync_scope_selection_state(file_id, scopes)
    return entry


def _build_scope_groups(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for transaction in transactions:
        scope_id = str(transaction.get("scope_id", "") or "").strip()
        scope_label = str(transaction.get("scope_label", "") or "").strip()
        if not scope_id or not scope_label:
            continue
        group_key = f"{transaction.get('bank', '')}::{scope_id}"
        if group_key not in grouped:
            grouped[group_key] = {
                "group_key": group_key,
                "scope_id": scope_id,
                "scope_label": scope_label,
                "bank": transaction.get("bank", ""),
                "product_type": transaction.get("product_type", ""),
                "transactions": [],
            }
        grouped[group_key]["transactions"].append(transaction)
    return sorted(grouped.values(), key=lambda item: (item["bank"], item["scope_label"]))


def _analysis_selection_summary(analysis_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    selected_map: Dict[str, Dict[str, Any]] = {}
    for entry in analysis_results:
        analysis = entry["analysis"]
        if not analysis.get("success") or not analysis.get("multi_scope"):
            continue
        for scope in analysis.get("available_scopes", []):
            if scope["id"] not in _selected_scope_ids(entry["file_id"], analysis.get("available_scopes", [])):
                continue
            key = f"{analysis.get('bank_detected', '')}::{scope['id']}"
            if key not in selected_map:
                selected_map[key] = {
                    "group_key": key,
                    "bank_detected": analysis.get("bank_detected", ""),
                    **scope,
                }
    return sorted(selected_map.values(), key=lambda item: (item.get("bank_detected", ""), item.get("label", "")))


def _selection_ready(analysis_results: List[Dict[str, Any]]) -> bool:
    ready = False
    for entry in analysis_results:
        analysis = entry["analysis"]
        if not analysis.get("success"):
            continue
        ready = True
        if analysis.get("multi_scope") and not _selected_scope_ids(entry["file_id"], analysis.get("available_scopes", [])):
            return False
    return ready


def _scope_chip(scope: Dict[str, Any]) -> str:
    product_type = scope.get("product_type", "")
    product_label = {
        "credit_card": "tarjeta de crédito",
        "debit_card": "tarjeta de débito",
        "bank_account": "cuenta bancaria",
    }.get(product_type, user_facing_product_type(product_type) or "entidad")
    linked = f" -> {scope['linked_account']}" if scope.get("linked_account") else ""
    return f"{scope.get('label', scope.get('id', 'entidad'))} ({product_label}){linked}"


def _is_production_test(mode: str) -> bool:
    return mode == "production-test"


def _analysis_bank_label(analysis: Dict[str, Any]) -> str:
    bank_name = str(analysis.get("bank_name") or "").strip()
    if bank_name:
        return bank_name

    bank_detected = str(analysis.get("bank_detected") or "").strip()
    if not bank_detected or bank_detected.lower() == "unknown":
        return ""

    return bank_detected.replace("_", " ").strip().title()


def _analysis_title(file_name: str, analysis: Dict[str, Any]) -> str:
    bank_label = _analysis_bank_label(analysis)
    if bank_label:
        return f"{file_name} · {bank_label}"
    return f"{file_name} · sin detección de banco"


def _render_override_summary(
    entry: Dict[str, Any],
    option_labels: Dict[str, str],
):
    override = entry.get("applied_override")
    if not override:
        return

    analysis = entry["analysis"]
    auto_analysis = entry.get("auto_analysis", analysis)
    override_key = _format_option_key(override["bank_id"], override["format_id"])
    override_label = option_labels.get(override_key, override_key)
    auto_format_key = _analysis_format_option(auto_analysis)

    if auto_analysis.get("success") and auto_format_key and auto_format_key != override_key:
        auto_label = option_labels.get(auto_format_key, auto_format_key)
        st.info(f"Se usará manualmente **{override_label}** en lugar del auto-detectado **{auto_label}**.")
        return

    if auto_analysis.get("success") and auto_format_key == override_key:
        st.info(f"Se fijó manualmente el formato **{override_label}**.")
        return

    auto_bank_label = _analysis_bank_label(auto_analysis)
    if auto_bank_label:
        st.info(
            f"Se intentará manualmente con **{override_label}**. "
            f"La auto-detección original había quedado en revisión para **{auto_bank_label}**."
        )
        return

    st.info(f"Se intentará manualmente con **{override_label}** porque la auto-detección no resolvió el archivo.")


def _render_analysis_technical_details(entry: Dict[str, Any], analysis: Dict[str, Any], debug: bool, mode: str):
    if not debug or _is_production_test(mode):
        return

    with st.expander("Detalles técnicos (depuración)", expanded=False):
        applied_override = entry.get("applied_override")
        if applied_override:
            st.write(f"Override manual: `{applied_override['bank_id']}/{applied_override['format_id']}`")

        bank_detected = analysis.get("bank_detected")
        if bank_detected:
            st.write(f"Banco interno: `{bank_detected}`")

        format_id = analysis.get("format_id")
        if format_id:
            st.write(f"Formato: `{format_id}`")

        format_version = analysis.get("format_version")
        if format_version:
            st.write(f"Versión: `{format_version}`")

        parse_status = analysis.get("parse_status")
        if parse_status:
            st.write(f"Estado de parseo: `{parse_status}`")

        if analysis.get("available_scopes"):
            st.json({"available_scopes": analysis["available_scopes"]})

        if analysis.get("diagnostics"):
            st.json({"diagnostics": analysis["diagnostics"]})

        if analysis.get("debug_log"):
            st.caption(f"Debug log de {entry['file_name']}")
            for step in analysis["debug_log"]:
                st.write(step)


def _report_analysis_exception(exc: Exception, mode: str):
    logging.getLogger(__name__).exception("Unhandled error during PDF analysis")
    if _is_production_test(mode):
        st.error(tr("analysis_error_safe"))
        return
    st.error(f"Error durante el análisis: {exc}")


def _report_processing_exception(exc: Exception, mode: str):
    logging.getLogger(__name__).exception("Unhandled error during statement processing")
    if _is_production_test(mode):
        st.error(tr("processing_error_safe"))
        return
    st.error(tr("processing_error", error=str(exc)))


def _report_file_processing_exception(name: str, exc: Exception, mode: str):
    logging.getLogger(__name__).exception("Unhandled error while processing %s", name)
    if _is_production_test(mode):
        st.error(tr("error_processing_file_safe", name=name))
        return
    st.error(tr("error_processing_file", name=name, error=str(exc)))


def _display_total_amount(transactions: List[Dict[str, Any]]) -> str:
    currencies = get_transaction_currencies(transactions)
    if len(currencies) > 1:
        return tr("metric_amount_multiple_currencies")

    total_amount = sum(float(transaction.get('amount', 0)) for transaction in transactions if transaction.get('amount'))
    return format_currency(total_amount, resolve_single_currency(transactions))

def main(debug: bool = False, lang: str = LANG, mode: str = "local"):
    """Launch the Streamlit application."""
    global LANG
    LANG = lang

    setup_logging(mode=mode, debug=debug if not _is_production_test(mode) else False)

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
    if 'training_seed' not in st.session_state:
        st.session_state.training_seed = None
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None
    if 'upload_signature' not in st.session_state:
        st.session_state.upload_signature = None
    
    # Sidebar with instructions and debug toggle
    with st.sidebar:
        debug_enabled = False
        if not _is_production_test(mode):
            debug_enabled = st.checkbox(tr("debug_mode"), value=debug, key="debug_logging")
            set_logging_level(logging.DEBUG if debug_enabled else logging.INFO)

        st.header(tr("instructions_header"))
        st.markdown(tr("instructions_text"))

        st.header(tr("supported_banks_header"))
        for bank in get_supported_banks():
            st.markdown(f"- {bank}")

        st.header(tr("sample_header"))
        st.markdown(tr("sample_text"))

    if _is_production_test(mode):
        process_tab = st.container()
        backoffice_tab = None
    else:
        process_tab, backoffice_tab = st.tabs(["Procesar Extractos", "Aprender Formatos"])

    with process_tab:
        # Main content area
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.header(tr("upload_header"))
            
            uploaded_files = st.file_uploader(
                tr("file_uploader_label"),
                type=['pdf'],
                accept_multiple_files=True,
                help=tr("file_uploader_help"),
            )
            
            if uploaded_files:
                # Validate files
                validation_results = validate_pdf_files(uploaded_files)
                
                if validation_results['valid']:
                    current_signature = _uploaded_files_signature(uploaded_files)
                    if st.session_state.upload_signature != current_signature:
                        st.session_state.upload_signature = current_signature
                        st.session_state.analysis_results = None
                        st.session_state.processed_data = None
                        st.session_state.processing_complete = False
                        _clear_scope_selection_state()
                        _clear_format_selection_state()

                    st.success(tr("valid_files", n=len(uploaded_files)))
                    
                    # Display file information
                    with st.expander(tr("file_details"), expanded=True):
                        for i, file in enumerate(uploaded_files):
                            file_size = len(file.getvalue()) / (1024 * 1024)  # MB
                            st.write(f"**{i+1}.** {file.name} - {file_size:.2f} MB")

                    if st.button("Analizar Extractos", type="primary", use_container_width=True):
                        analyze_files(uploaded_files, debug=debug_enabled, mode=mode)

                    if st.session_state.analysis_results:
                        render_analysis_results(uploaded_files, st.session_state.analysis_results, debug=debug_enabled, mode=mode)
                        process_disabled = not _selection_ready(st.session_state.analysis_results)
                        if process_disabled:
                            st.info("Selecciona al menos una cuenta o tarjeta en cada PDF consolidado antes de procesar.")
                        if st.button(tr("process_button"), type="primary", use_container_width=True, disabled=process_disabled):
                            process_files(uploaded_files, st.session_state.analysis_results, debug=debug_enabled, mode=mode)
                        
                else:
                    st.error(tr("validation_failed"))
                    for error in validation_results['errors']:
                        st.error(f"• {error}")
        
        with col2:
            st.header(tr("processing_status_header"))
            
            if st.session_state.processing_complete and st.session_state.processed_data:
                display_results(mode=mode)
            else:
                st.info(tr("upload_and_click"))

    if backoffice_tab is not None:
        with backoffice_tab:
            render_format_backoffice(mode=mode)

def analyze_files(uploaded_files: List[Any], debug: bool = False, mode: str = "local"):
    progress_bar = st.progress(0)
    status_text = st.empty()
    pdf_processor = PDFProcessor()
    analysis_results: List[Dict[str, Any]] = []

    try:
        for i, uploaded_file in enumerate(uploaded_files):
            progress = (i + 1) / len(uploaded_files)
            progress_bar.progress(progress)
            status_text.text(f"Analizando {uploaded_file.name}... ({i+1}/{len(uploaded_files)})")

            analysis_entry = _build_effective_analysis_entry(uploaded_file, pdf_processor, debug=debug)
            analysis_results.append(analysis_entry)

            result = analysis_entry["analysis"]
            if not result.get("success") and result.get('parse_status') in {'unknown_format', 'format_changed'}:
                _seed_training_from_result(uploaded_file.name, result)

        st.session_state.analysis_results = analysis_results
        progress_bar.progress(1.0)
        status_text.text("Análisis completado.")
    except Exception as exc:
        _report_analysis_exception(exc, mode)
        progress_bar.empty()
        status_text.empty()


def render_analysis_results(uploaded_files: List[Any], analysis_results: List[Dict[str, Any]], debug: bool = False, mode: str = "local"):
    st.subheader("Análisis previo")
    pdf_processor = PDFProcessor()
    available_formats = pdf_processor.list_available_formats()
    format_keys = ["auto"] + [_format_option_key(fmt["bank_id"], fmt["format_id"]) for fmt in available_formats]
    option_labels = {
        "auto": "Auto-detectado",
        **{
            _format_option_key(fmt["bank_id"], fmt["format_id"]): fmt["label"]
            for fmt in available_formats
        },
    }
    uploaded_file_map = {_uploaded_file_id(uploaded_file): uploaded_file for uploaded_file in uploaded_files}

    for index, entry in enumerate(analysis_results):
        analysis = entry["analysis"]
        title = _analysis_title(entry["file_name"], analysis)
        with st.expander(title, expanded=True):
            selector_key = _format_selector_key(entry["file_id"])
            current_option = _entry_selected_format_option(entry)
            if st.session_state.get(selector_key) not in format_keys:
                st.session_state[selector_key] = current_option if current_option in format_keys else "auto"

            selected_option = st.selectbox(
                "Formato a aplicar",
                options=format_keys,
                format_func=lambda value: option_labels.get(value, value),
                key=selector_key,
                help="Elegí cualquier formato publicado para reanalizar este PDF con esa spec.",
            )
            auto_option = _analysis_format_option(entry.get("auto_analysis", analysis))
            normalized_option = "auto" if selected_option == auto_option else selected_option
            if normalized_option != current_option:
                uploaded_file = uploaded_file_map.get(entry["file_id"])
                if uploaded_file is None:
                    st.error("No se pudo recuperar el archivo cargado para reanalizarlo.")
                else:
                    override = _parse_format_option(normalized_option)
                    analysis_results[index] = _build_effective_analysis_entry(
                        uploaded_file,
                        pdf_processor,
                        debug=debug,
                        override=override,
                        auto_analysis=entry.get("auto_analysis"),
                    )
                    st.session_state.analysis_results = analysis_results
                    st.session_state[selector_key] = normalized_option
                    st.rerun()

            analysis = entry["analysis"]
            _render_override_summary(entry, option_labels)
            bank_label = _analysis_bank_label(analysis)
            if analysis.get("success"):
                if bank_label:
                    st.success(f"Banco detectado: **{bank_label}**")
                else:
                    st.warning("No se pudo identificar el banco automáticamente.")

                if analysis.get("multi_scope"):
                    scopes = analysis.get("available_scopes", [])
                    st.info(f"Se detectaron {len(scopes)} cuentas o tarjetas extraíbles en este PDF. Elegí cuáles querés procesar.")
                    preset_col1, preset_col2, preset_col3, preset_col4 = st.columns(4)
                    with preset_col1:
                        if st.button("Todo", key=f"preset_all_{entry['file_id']}", use_container_width=True):
                            _apply_scope_preset(entry["file_id"], scopes)
                            st.rerun()
                    with preset_col2:
                        if st.button("Solo crédito", key=f"preset_credit_{entry['file_id']}", use_container_width=True):
                            _apply_scope_preset(entry["file_id"], scopes, {"credit_card"})
                            st.rerun()
                    with preset_col3:
                        if st.button("Solo débito", key=f"preset_debit_{entry['file_id']}", use_container_width=True):
                            _apply_scope_preset(entry["file_id"], scopes, {"debit_card"})
                            st.rerun()
                    with preset_col4:
                        if st.button("Solo cuentas", key=f"preset_accounts_{entry['file_id']}", use_container_width=True):
                            _apply_scope_preset(entry["file_id"], scopes, {"bank_account"})
                            st.rerun()

                    for scope in scopes:
                        st.checkbox(
                            _scope_chip(scope),
                            key=_scope_checkbox_key(entry["file_id"], scope["id"]),
                        )
                    selected = _selected_scope_ids(entry["file_id"], scopes)
                    st.caption(f"Seleccionadas: {len(selected)} de {len(scopes)}")
                else:
                    st.success("Documento simple: se procesará completo sin selección adicional.")
            else:
                if bank_label:
                    st.warning(f"Se detectó el banco **{bank_label}**, pero este archivo necesita revisión.")
                else:
                    st.warning("No se pudo detectar el banco o el formato del archivo.")
                st.error(analysis.get("error", "No se pudo analizar el archivo."))
                if not _is_production_test(mode) and analysis.get('parse_status') in {'unknown_format', 'format_changed'}:
                    st.info("Este fallo quedó sembrado en la pestaña 'Aprender Formatos'.")

            _render_analysis_technical_details(entry, analysis, debug=debug, mode=mode)


def process_files(uploaded_files: List[Any], analysis_results: List[Dict[str, Any]], debug: bool = False, mode: str = "local"):
    """Process uploaded PDF files and extract transaction data."""
    
    # Initialize progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Initialize processor
        pdf_processor = PDFProcessor()
        all_transactions = []
        all_reconciliations = []
        analysis_map = {entry["file_id"]: entry for entry in analysis_results}
        selected_scope_map = {
            entry["file_id"]: _selected_scope_ids(entry["file_id"], entry["analysis"].get("available_scopes", []))
            for entry in analysis_results
        }
        processing_summary = {
            'total_files': len(uploaded_files),
            'successful_files': 0,
            'failed_files': 0,
            'total_transactions': 0,
            'banks_detected': set(),
            'errors': [],
            'selected_scopes': _analysis_selection_summary(analysis_results),
        }
        
        # Process each file
        for i, uploaded_file in enumerate(uploaded_files):
            progress = (i + 1) / len(uploaded_files)
            progress_bar.progress(progress)
            status_text.text(tr("processing_file", name=uploaded_file.name, i=i+1, total=len(uploaded_files)))
            
            try:
                file_id = _uploaded_file_id(uploaded_file)
                analysis_entry = analysis_map.get(file_id)
                analysis = analysis_entry["analysis"] if analysis_entry else None
                applied_override = analysis_entry.get("applied_override") if analysis_entry else None
                if analysis and not analysis.get("success"):
                    processing_summary['failed_files'] += 1
                    processing_summary['errors'].append(f"{uploaded_file.name}: {analysis['error']}")
                    st.error(tr("file_error", name=uploaded_file.name, error=analysis['error']))
                    continue

                with temporary_pdf_copy(uploaded_file.getvalue()) as tmp_file_path:
                    result = pdf_processor.process_pdf(
                        tmp_file_path,
                        uploaded_file.name,
                        debug=debug,
                        selected_scope_ids=selected_scope_map.get(file_id) or None,
                        override_bank_id=applied_override["bank_id"] if applied_override else None,
                        override_format_id=applied_override["format_id"] if applied_override else None,
                    )
                
                if result['success']:
                    transactions = result['transactions']
                    all_transactions.extend(transactions)
                    all_reconciliations.extend(result.get('reconciliations', []))
                    processing_summary['successful_files'] += 1
                    processing_summary['total_transactions'] += len(transactions)
                    processing_summary['banks_detected'].add(result.get('bank_name', result['bank_detected']))

                    st.success(tr("transactions_extracted", name=uploaded_file.name, count=len(transactions)))
                else:
                    processing_summary['failed_files'] += 1
                    processing_summary['errors'].append(f"{uploaded_file.name}: {result['error']}")
                    st.error(tr("file_error", name=uploaded_file.name, error=result['error']))
                    if applied_override is None and result.get('parse_status') in {'unknown_format', 'format_changed'}:
                        _seed_training_from_result(uploaded_file.name, result)
                        if not _is_production_test(mode):
                            st.info("Se guardó el último fallo de formato en la pestaña 'Aprender Formatos'.")

                if debug and not _is_production_test(mode) and result.get('debug_log'):
                    with st.expander(f"Debug Log for {uploaded_file.name}"):
                        for step in result['debug_log']:
                            st.write(step)
                
            except Exception as e:
                processing_summary['failed_files'] += 1
                processing_summary['errors'].append(f"{uploaded_file.name}: {str(e)}")
                _report_file_processing_exception(uploaded_file.name, e, mode)
        
        # Complete processing
        progress_bar.progress(1.0)
        status_text.text(tr("processing_complete_status"))
        
        if all_transactions:
            # Generate Excel file
            excel_generator = ExcelGenerator()
            excel_data = excel_generator.create_excel_file(
                all_transactions,
                processing_summary,
                all_reconciliations,
            )
            
            # Store results in session state
            st.session_state.processed_data = {
                'excel_data': excel_data,
                'transactions': all_transactions,
                'summary': processing_summary,
                'reconciliations': all_reconciliations,
            }
            st.session_state.processing_complete = True
            
            st.success(tr("final_success", transactions=processing_summary['total_transactions'], files=processing_summary['successful_files']))
            st.rerun()
        else:
            st.error(tr("no_transactions"))
            
    except Exception as e:
        _report_processing_exception(e, mode)
        progress_bar.empty()
        status_text.empty()

def display_results(mode: str = "local"):
    """Display processing results and download options."""
    
    data = st.session_state.processed_data
    summary = data['summary']
    transactions = data['transactions']
    reconciliations = data.get('reconciliations', [])
    scope_groups = _build_scope_groups(transactions)
    
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
        st.metric(tr("metric_amount"), _display_total_amount(transactions))
    
    # Banks detected
    if summary['banks_detected']:
        st.subheader(tr("banks_detected_header"))
        banks_text = ", ".join(sorted(summary['banks_detected']))
        st.write(banks_text)

    if summary.get("selected_scopes"):
        st.subheader("Entidades seleccionadas")
        for scope in summary["selected_scopes"]:
            st.write(f"- {_scope_chip(scope)}")
    
    reconciliation_status = aggregate_reconciliation_status(reconciliations)
    if reconciliation_status == "passed":
        st.success("Conciliación verificada. Consulta el detalle en la hoja «Conciliación» del Excel.")
    elif reconciliation_status == "failed":
        st.warning("El Excel fue generado con diferencias de conciliación. Revisa la hoja «Conciliación».")
    elif reconciliation_status == "partial":
        st.info("La conciliación está disponible solo para parte de los extractos. Consulta la hoja «Conciliación».")
    else:
        st.info("La conciliación no está disponible para estos formatos. El procesamiento no fue afectado.")
    # Errors if any
    if summary['errors']:
        with st.expander(tr("processing_errors"), expanded=False):
            for error in summary['errors']:
                st.error(error)
    
    # Transaction preview
    if transactions:
        st.subheader(tr("preview_header"))
        df = _build_user_facing_dataframe(transactions)
        if scope_groups:
            tab_labels = ["Todo"] + [f"{group['bank']} · {group['scope_label']}" for group in scope_groups]
            tabs = st.tabs(tab_labels)
            with tabs[0]:
                st.dataframe(df.head(10), use_container_width=True, hide_index=True)
            for index, group in enumerate(scope_groups, start=1):
                with tabs[index]:
                    scope_df = _build_user_facing_dataframe(group["transactions"])
                    st.caption(f"{group['bank']} · {user_facing_product_type(group['product_type']) or 'entidad'}")
                    st.dataframe(scope_df.head(10), use_container_width=True, hide_index=True)
        else:
            st.dataframe(df.head(10), use_container_width=True, hide_index=True)

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
                file_name=f"extractos_bancarios_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )
    
    with col2:
        # CSV download as backup
        if transactions:
            csv_data = _build_csv_export(transactions)
            st.download_button(
                label=tr("download_csv"),
                data=csv_data,
                file_name=f"extractos_bancarios_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    # Reset button
    if st.button(tr("process_new"), use_container_width=True):
        st.session_state.processed_data = None
        st.session_state.processing_complete = False
        st.session_state.analysis_results = None
        st.session_state.upload_signature = None
        _clear_scope_selection_state()
        _clear_format_selection_state()
        st.rerun()


def render_format_backoffice(mode: str = "local"):
    st.header("Backoffice de Formatos")
    st.caption("Entrena, valida y publica parsers declarativos sin tocar el resto del sistema.")

    registry = FormatRegistry()
    summary = _registry_summary(registry)

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Aprender un formato")
        seed = st.session_state.training_seed
        training_file = st.file_uploader(
            "PDF de ejemplo para entrenamiento",
            type=["pdf"],
            key="training_pdf_uploader",
            help="No se guardará el PDF crudo en el repositorio; solo se usa temporalmente para extraer texto.",
        )

        extracted_text = ""
        bank_hint = "unknown_bank"
        display_name = ""
        suggested_format_id = "draft"

        training_context = temporary_pdf_copy(training_file.getvalue()) if training_file is not None else nullcontext(None)
        with training_context as training_tmp_path:
            if training_file is not None and training_tmp_path is not None:
                extracted_text = extract_text_from_pdf(training_tmp_path)
                display_name = training_file.name
                suggested_format_id = _suggest_format_id(training_file.name)
            elif seed:
                extracted_text = seed.get("extracted_text", "")
                bank_hint = seed.get("bank_detected", "unknown_bank") or "unknown_bank"
                display_name = seed.get("bank_name", "") or seed.get("file_name", "Nuevo Formato")
                suggested_format_id = seed.get("suggested_format_id", "draft")
                st.info(f"Seed cargada desde el último fallo de formato: {seed.get('file_name')}")
                if seed.get("diagnostics"):
                    st.json(seed["diagnostics"])

            if extracted_text:
                initial_spec = build_initial_spec(
                    bank_id=bank_hint if bank_hint != "Unknown" else "unknown_bank",
                    format_id=suggested_format_id,
                    display_name=display_name or bank_hint,
                    extracted_text=extracted_text,
                )

                bank_id = st.text_input("bank_id", value=initial_spec["meta"]["bank_id"], key="train_bank_id")
                format_id = st.text_input("format_id", value=initial_spec["meta"]["format_id"], key="train_format_id")
                display_name_input = st.text_input("display_name", value=initial_spec["meta"]["display_name"], key="train_display_name")
                country = st.text_input("country", value=initial_spec["meta"]["country"], key="train_country")
                currency = st.text_input("currency_default", value=initial_spec["meta"]["currency_default"], key="train_currency")

                required_keywords = st.text_area(
                    "required_keywords (uno por línea)",
                    value="\n".join(initial_spec["detect"]["required_keywords"]),
                    height=120,
                    key="train_required_keywords",
                )
                excluded_keywords = st.text_area(
                    "excluded_keywords (uno por línea)",
                    value="\n".join(initial_spec["detect"].get("excluded_keywords", [])),
                    height=80,
                    key="train_excluded_keywords",
                )
                line_pattern = st.text_area(
                    "line_pattern (regex con grupos nombrados)",
                    value=initial_spec["extract"]["line_pattern"],
                    height=120,
                    key="train_line_pattern",
                )
                candidate_pattern = st.text_input(
                    "candidate_pattern",
                    value=initial_spec["extract"]["candidate_pattern"],
                    key="train_candidate_pattern",
                )
                section_start_patterns = st.text_area(
                    "section_start_patterns (una por línea)",
                    value="\n".join(initial_spec["extract"].get("section_start_patterns", [])),
                    height=80,
                    key="train_section_start_patterns",
                )
                ignore_patterns = st.text_area(
                    "ignore_patterns (una por línea)",
                    value="\n".join(initial_spec["extract"].get("ignore_patterns", [])),
                    height=120,
                    key="train_ignore_patterns",
                )
                stop_patterns = st.text_area(
                    "stop_patterns (una por línea)",
                    value="\n".join(initial_spec["extract"].get("stop_patterns", [])),
                    height=120,
                    key="train_stop_patterns",
                )
                account_pattern = st.text_input(
                    "account_pattern",
                    value=initial_spec["fields"].get("account_pattern", ""),
                    key="train_account_pattern",
                )

                preview_spec = {
                    "meta": {
                        "bank_id": bank_id,
                        "format_id": format_id,
                        "version": 1,
                        "status": "draft",
                        "country": country,
                        "currency_default": currency,
                        "display_name": display_name_input,
                    },
                    "detect": {
                        "required_keywords": _multiline_text_to_list(required_keywords),
                        "excluded_keywords": _multiline_text_to_list(excluded_keywords),
                        "min_score": initial_spec["detect"].get("min_score", 0.5),
                    },
                    "extract": {
                        "strategy": "line_regex",
                        "line_pattern": line_pattern,
                        "candidate_pattern": candidate_pattern,
                        "section_start_patterns": _multiline_text_to_list(section_start_patterns),
                        "ignore_patterns": _multiline_text_to_list(ignore_patterns),
                        "stop_patterns": _multiline_text_to_list(stop_patterns),
                        "multiline": True,
                    },
                    "fields": {
                        "date": "date",
                        "description": "description",
                        "amount": "amount",
                        "balance": "balance",
                        "account_pattern": account_pattern,
                    },
                    "normalize": initial_spec["normalize"],
                    "change_detection": initial_spec["change_detection"],
                }
                advanced_spec_text = st.text_area(
                    "Spec TOML avanzada",
                    value=toml.dumps(preview_spec),
                    height=320,
                    key="train_advanced_spec_toml",
                    help="Edita TOML libremente para definir scopes, sections y context_rules avanzadas.",
                )

                preview = None
                effective_spec = preview_spec
                prepared_preview_text = extracted_text
                try:
                    effective_spec = toml.loads(advanced_spec_text)
                    preview_format = FormatSpec(Path("preview/spec.toml"), effective_spec)
                    prepared_preview_text = preview_format.prepare_text(extracted_text, training_tmp_path)
                    preview = preview_format.parse_transactions(prepared_preview_text)
                except Exception as exc:
                    st.error(f"Spec TOML inválida: {exc}")

                st.write("Texto extraído")
                st.text_area("preview_text", prepared_preview_text, height=220, disabled=True, label_visibility="collapsed")

                preview_col, save_col = st.columns(2)
                with preview_col:
                    st.metric("Transacciones detectadas", len(preview.transactions) if preview else 0)
                    if preview:
                        st.json(preview.diagnostics)
                with save_col:
                    if preview and preview.transactions:
                        st.dataframe(pd.DataFrame(preview.transactions).head(10), use_container_width=True, hide_index=True)
                    else:
                        st.warning("La spec actual no detectó transacciones.")

                action_col1, action_col2 = st.columns(2)
                with action_col1:
                    if st.button("Guardar borrador", type="primary", use_container_width=True, key="save_draft_button", disabled=preview is None):
                        spec_path = save_draft(effective_spec, prepared_preview_text, preview.transactions if preview else [])
                        st.success(f"Borrador guardado en {spec_path}")
                        st.session_state.training_seed = None
                        st.rerun()
                with action_col2:
                    if st.button("Descartar seed", use_container_width=True, key="discard_seed_button"):
                        st.session_state.training_seed = None
                        st.rerun()
            else:
                st.info("Carga un PDF o procesa un extracto con error para sembrar este asistente.")

    with col2:
        st.subheader("Estado del registro")
        st.write(f"Publicados: {len(summary['published'])}")
        st.write(f"Borradores: {len(summary['drafts'])}")

        if summary["drafts"]:
            st.markdown("**Borradores**")
            for draft in summary["drafts"]:
                st.write(f"- {draft.bank_id}/{draft.format_id} (v{draft.version})")
                if st.button(
                    f"Publicar {draft.bank_id}/{draft.format_id}",
                    key=f"publish_{draft.bank_id}_{draft.format_id}",
                    use_container_width=True,
                ):
                    publish_spec(draft.source_path)
                    st.success(f"Publicado {draft.bank_id}/{draft.format_id}")
                    st.rerun()

        if summary["published"]:
            st.markdown("**Publicados**")
            for spec in summary["published"]:
                st.write(f"- {spec.bank_id}/{spec.format_id} (v{spec.version})")
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=tr("argparse_desc"))
    parser.add_argument("--debug", action="store_true", help=tr("argparse_debug"))
    parser.add_argument("--lang", choices=["en", "es"], default=LANG, help="UI language")
    parser.add_argument("--mode", choices=["local", "production-test"], default="local", help=tr("argparse_mode"))
    args, _ = parser.parse_known_args()
    main(debug=args.debug, lang=args.lang, mode=args.mode)
