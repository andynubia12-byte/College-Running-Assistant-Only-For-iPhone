"""GeoPilot theme system — light and dark mode stylesheets."""

from dataclasses import dataclass


@dataclass
class Theme:
    bg_page: str
    bg_card: str
    bg_card_hover: str
    bg_input: str
    bg_input_focus: str

    border: str
    border_light: str
    border_focus: str

    text_primary: str
    text_secondary: str
    text_tertiary: str
    text_inverse: str

    accent: str
    accent_hover: str
    accent_pressed: str
    accent_light: str

    success: str
    success_light: str
    warning: str
    warning_light: str
    error: str
    error_light: str


LIGHT = Theme(
    bg_page="#F8FAFC",
    bg_card="#FFFFFF",
    bg_card_hover="#F1F5F9",
    bg_input="#F8FAFC",
    bg_input_focus="#FFFFFF",

    border="#E2E8F0",
    border_light="#F1F5F9",
    border_focus="#2563EB",

    text_primary="#0F172A",
    text_secondary="#475569",
    text_tertiary="#94A3B8",
    text_inverse="#FFFFFF",

    accent="#2563EB",
    accent_hover="#1D4ED8",
    accent_pressed="#1E40AF",
    accent_light="#EFF6FF",

    success="#22C55E",
    success_light="#F0FDF4",
    warning="#F59E0B",
    warning_light="#FFFBEB",
    error="#EF4444",
    error_light="#FEF2F2",
)

DARK = Theme(
    bg_page="#0B1121",
    bg_card="#111C30",
    bg_card_hover="#162244",
    bg_input="#111C30",
    bg_input_focus="#162244",

    border="#1E3050",
    border_light="#162244",
    border_focus="#3B82F6",

    text_primary="#F1F5F9",
    text_secondary="#94A3B8",
    text_tertiary="#64748B",
    text_inverse="#0B1121",

    accent="#3B82F6",
    accent_hover="#2563EB",
    accent_pressed="#1D4ED8",
    accent_light="#1E293B",

    success="#22C55E",
    success_light="#0F1F14",
    warning="#F59E0B",
    warning_light="#1F1A0F",
    error="#EF4444",
    error_light="#1F1315",
)


def build_stylesheet(t: Theme) -> str:
    return f"""
/* ═══════════════════════════════════════════════════════════
   GeoPilot — Device-Centric Dashboard Theme
   ═══════════════════════════════════════════════════════════ */

/* ── Window & Base ──────────────────────────────────────── */
QMainWindow {{
    background-color: {t.bg_page};
}}
QWidget#centralWidget {{
    background-color: {t.bg_page};
}}

/* ── Dialogs — match main window design ─────────────────── */
QDialog {{
    background-color: {t.bg_card};
}}
QMessageBox {{
    background-color: {t.bg_card};
}}
QMessageBox QLabel {{
    color: {t.text_primary};
    font-size: 13px;
}}
QInputDialog {{
    background-color: {t.bg_card};
}}

/* ── Typography ──────────────────────────────────────────── */
QLabel#pageTitle {{
    font-size: 16px;
    font-weight: 600;
    color: {t.text_primary};
    background: transparent;
}}
QLabel#sectionTitle {{
    font-size: 11px;
    font-weight: 700;
    color: {t.text_tertiary};
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 0 2px;
}}
QLabel#bodyLabel {{
    font-size: 13px;
    color: {t.text_secondary};
    background: transparent;
}}
QLabel#captionLabel {{
    font-size: 11px;
    color: {t.text_tertiary};
    background: transparent;
}}
QLabel#deviceName {{
    font-size: 13px;
    font-weight: 600;
    color: {t.text_primary};
    background: transparent;
}}
QLabel#deviceSub {{
    font-size: 11px;
    color: {t.text_tertiary};
    background: transparent;
}}
QLabel#statusDot {{
    font-size: 13px;
    font-weight: 600;
}}
QLabel#statusText {{
    font-size: 12px;
    color: {t.text_secondary};
}}

/* ── QPushButton — Default ───────────────────────────────── */
QPushButton {{
    border: 1px solid {t.border};
    padding: 7px 14px;
    min-height: 32px;
    max-height: 32px;
    color: {t.text_secondary};
    border-radius: 7px;
    background-color: {t.bg_card};
    font-size: 13px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {t.bg_card_hover};
    border: 1px solid {t.text_tertiary};
    color: {t.text_primary};
}}
QPushButton:pressed {{
    background-color: {t.border_light};
}}
QPushButton:disabled {{
    background-color: {t.bg_page};
    border: 1px solid {t.border_light};
    color: {t.text_tertiary};
}}

/* ── QPushButton#primaryBtn ──────────────────────────────── */
QPushButton#primaryBtn {{
    color: {t.text_inverse};
    background-color: {t.accent};
    border: 1px solid {t.accent};
    font-weight: 600;
    min-height: 36px;
    max-height: 36px;
    padding: 8px 18px;
}}
QPushButton#primaryBtn:hover {{
    background-color: {t.accent_hover};
    border: 1px solid {t.accent_hover};
}}
QPushButton#primaryBtn:pressed {{
    background-color: {t.accent_pressed};
    border: 1px solid {t.accent_pressed};
}}
QPushButton#primaryBtn:disabled {{
    background-color: {t.text_tertiary};
    border: 1px solid {t.text_tertiary};
    color: {t.text_inverse};
}}

/* ── QPushButton#ghostBtn — icon buttons ─────────────────── */
QPushButton#ghostBtn {{
    border: none;
    background: transparent;
    color: {t.text_secondary};
    min-height: 32px;
    max-height: 32px;
    min-width: 32px;
    max-width: 32px;
    padding: 0;
    font-size: 14px;
    border-radius: 6px;
}}
QPushButton#ghostBtn:hover {{
    background-color: {t.bg_card_hover};
    color: {t.text_primary};
}}

/* ── QPushButton#modeBtn — compact toolbar buttons ────────── */
QPushButton#modeBtn {{
    font-size: 13px;
    font-weight: 600;
    color: {t.text_primary};
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: 8px;
    padding: 10px 16px;
    min-height: 52px;
    max-height: 52px;
}}
QPushButton#modeBtn:hover {{
    border: 1px solid {t.accent};
    background-color: {t.accent_light};
    color: {t.accent};
}}
QPushButton#modeBtn:disabled {{
    background-color: {t.bg_page};
    border: 1px solid {t.border_light};
    color: {t.text_tertiary};
}}

/* ── QPushButton#dangerBtn ───────────────────────────────── */
QPushButton#dangerBtn {{
    color: {t.error};
    background-color: {t.bg_card};
    border: 1px solid {t.border};
}}
QPushButton#dangerBtn:hover {{
    color: {t.text_inverse};
    background-color: {t.error};
    border: 1px solid {t.error};
}}

/* ── QPushButton#backBtn ──────────────────────────────────── */
QPushButton#backBtn {{
    border: none;
    background: transparent;
    color: {t.text_secondary};
    padding: 4px 8px;
    min-height: 30px;
    max-height: 30px;
    font-size: 13px;
}}
QPushButton#backBtn:hover {{
    color: {t.text_primary};
    background-color: {t.bg_card_hover};
}}

/* ── Status Card (QFrame) ─────────────────────────────────── */
QFrame#statusCard {{
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: 10px;
    padding: 0px;
}}

/* ── Content Card (QFrame) ────────────────────────────────── */
QFrame#contentCard {{
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: 10px;
    padding: 0px;
}}

/* ── Device List Card (QFrame) ────────────────────────────── */
QFrame#deviceListCard {{
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: 10px;
    padding: 0px;
}}

/* ── QCheckBox ────────────────────────────────────────────── */
QCheckBox {{
    color: {t.text_primary};
    font-size: 13px;
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid {t.text_tertiary};
    background-color: {t.bg_card};
}}
QCheckBox::indicator:hover {{
    border: 2px solid {t.accent};
}}
QCheckBox::indicator:checked {{
    background-color: {t.accent};
    border: 2px solid {t.accent};
}}

/* ── QGroupBox ───────────────────────────────────────────── */
QGroupBox {{
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: 10px;
    margin-top: 14px;
    padding: 16px 14px 12px 14px;
    font-weight: 600;
    font-size: 12px;
    color: {t.text_primary};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: {t.text_secondary};
}}

/* ── QListWidget ──────────────────────────────────────────── */
QListWidget {{
    background-color: transparent;
    border: none;
    color: {t.text_primary};
    outline: none;
    font-size: 13px;
}}
QListWidget::item {{
    background: transparent;
    border: none;
    padding: 0px;
    margin: 0px;
}}
QListWidget::item:hover {{
    background-color: {t.bg_card_hover};
    border-radius: 6px;
}}
QListWidget::item:selected {{
    background-color: {t.border};
    color: {t.text_primary};
    border-radius: 6px;
}}
QListWidget:focus {{
    border: none;
    outline: none;
}}

/* ── QSpinBox / QDoubleSpinBox ────────────────────────────── */
QSpinBox, QDoubleSpinBox {{
    background-color: {t.bg_input};
    border-radius: 6px;
    border: 1px solid {t.border};
    padding: 4px 10px;
    min-height: 32px;
    max-height: 32px;
    color: {t.text_primary};
    min-width: 80px;
    font-size: 13px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {t.border_focus};
    background-color: {t.bg_input_focus};
}}
QSpinBox:hover, QDoubleSpinBox:hover {{
    border: 1px solid {t.text_tertiary};
}}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    border: none;
    background-color: transparent;
    border-radius: 4px;
    margin: 2px;
    width: 16px;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {t.bg_card_hover};
}}

/* ── QComboBox ────────────────────────────────────────────── */
QComboBox {{
    background-color: {t.bg_input};
    border-radius: 6px;
    border: 1px solid {t.border};
    padding: 4px 10px;
    min-height: 32px;
    max-height: 32px;
    color: {t.text_primary};
    font-size: 13px;
}}
QComboBox:hover {{
    border: 1px solid {t.text_tertiary};
}}
QComboBox:focus {{
    border: 1px solid {t.border_focus};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: 6px;
    selection-background-color: {t.accent_light};
    selection-color: {t.accent};
    color: {t.text_secondary};
    outline: none;
    padding: 4px;
}}

/* ── QScrollArea ──────────────────────────────────────────── */
QScrollArea {{
    border: none;
    background: transparent;
}}

/* ── QScrollBar — Vertical ────────────────────────────────── */
QScrollBar:vertical {{
    background-color: transparent;
    width: 6px;
    border-radius: 3px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background-color: {t.text_tertiary};
    border-radius: 3px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {t.text_secondary};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

/* ── QScrollBar — Horizontal ──────────────────────────────── */
QScrollBar:horizontal {{
    background-color: transparent;
    height: 6px;
    border-radius: 3px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background-color: {t.text_tertiary};
    border-radius: 3px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {t.text_secondary};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}

/* ── QTextEdit ────────────────────────────────────────────── */
QTextEdit {{
    background-color: {t.bg_input};
    border-radius: 8px;
    border: 1px solid {t.border};
    padding: 10px 12px;
    color: {t.text_primary};
    font-size: 12px;
}}

/* ── QProgressBar ─────────────────────────────────────────── */
QProgressBar {{
    border-radius: 4px;
    background-color: {t.border_light};
    height: 6px;
    border: none;
    text-align: center;
    color: transparent;
    font-size: 1px;
}}
QProgressBar::chunk {{
    border-radius: 4px;
    background-color: {t.accent};
}}

/* ── QLabel ───────────────────────────────────────────────── */
QLabel {{
    color: {t.text_secondary};
    background: transparent;
}}

/* ── QFormLayout ──────────────────────────────────────────── */
QFormLayout QLabel {{
    color: {t.text_secondary};
    font-size: 13px;
    font-weight: 500;
}}

/* ── QToolTip ─────────────────────────────────────────────── */
QToolTip {{
    background-color: {t.bg_card};
    color: {t.text_primary};
    border: 1px solid {t.border};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}
"""


LIGHT_STYLESHEET = build_stylesheet(LIGHT)
DARK_STYLESHEET = build_stylesheet(DARK)

STYLESHEET = LIGHT_STYLESHEET
