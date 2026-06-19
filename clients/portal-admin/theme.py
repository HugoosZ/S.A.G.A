"""
SAGA - Sistema de tema visual
Constantes de diseño basadas en la identidad institucional UDP.
"""

# ── Colores institucionales UDP ─────────────────────────────────────────────
UDP_RED        = "#C0272D"
UDP_RED_DARK   = "#9C1F24"
UDP_RED_HOVER  = "#A82329"
UDP_RED_SOFT   = "#F7E6E7"
UDP_RED_TINT   = "#FBF1F2"

# ── Neutros (tonos cálidos) ─────────────────────────────────────────────────
BG              = "#FAFAF7"   # Fondo general de la app
SURFACE         = "#FFFFFF"   # Tarjetas, paneles
SURFACE_2       = "#F5F4EF"   # Fondos secundarios (filas alternas, etc.)
SIDEBAR_BG      = "#1A1A1A"   # Sidebar oscuro
SIDEBAR_ITEM    = "#2A2A2A"   # Hover en sidebar
SIDEBAR_ACTIVE  = UDP_RED

INK             = "#1A1A1A"   # Texto principal
INK_2           = "#404040"   # Texto secundario
MUTED           = "#757070"   # Texto auxiliar
BORDER          = "#E8E5DC"   # Bordes principales
BORDER_SOFT     = "#F0EDE4"   # Bordes suaves

# ── Semánticos ──────────────────────────────────────────────────────────────
SUCCESS         = "#2D7A47"
SUCCESS_BG      = "#E6F1EA"
WARNING         = "#B86A14"
WARNING_BG      = "#FBEED6"
INFO            = "#1F5C8F"
INFO_BG         = "#E3EEF7"
DERIV_TONE      = "#C4A684"   # Color secundario para derivaciones

# ── Tipografía ──────────────────────────────────────────────────────────────
# CustomTkinter usa fuentes del sistema. Estos son nombres seguros multi-OS.
FONT_FAMILY     = "Helvetica"   # Fallback universal
FONT_FAMILY_ALT = "Segoe UI"    # Windows
FONT_DISPLAY    = "Georgia"     # Serif para títulos institucionales

SIZE_DISPLAY    = 28
SIZE_TITLE      = 20
SIZE_H2         = 16
SIZE_BODY       = 13
SIZE_SMALL      = 12
SIZE_TINY       = 11
SIZE_KPI        = 36

# ── Layout ──────────────────────────────────────────────────────────────────
SIDEBAR_WIDTH   = 230
PADDING_LG      = 32
PADDING_MD      = 20
PADDING_SM      = 12
CORNER_RADIUS   = 10

# (Sin dependencias de terceros para gráficos: se usa tkinter.Canvas nativo)
