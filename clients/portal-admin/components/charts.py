"""
Componentes de gráficos usando tkinter.Canvas nativo.
No requiere matplotlib ni ninguna dependencia de terceros.
Funciona en cualquier versión de Python 3.8+.
"""

import tkinter as tk
import customtkinter as ctk

import theme as t


# ── Helper: header estándar para tarjetas de gráfico ────────────────────────
def _build_chart_header(parent, title: str, subtitle: str, legend=None):
    """
    legend: lista de tuplas (color_hex, label) para mostrar en la cabecera.
    """
    header = ctk.CTkFrame(parent, fg_color="transparent")
    header.pack(fill="x", padx=24, pady=(20, 4))

    left = ctk.CTkFrame(header, fg_color="transparent")
    left.pack(side="left", anchor="w")

    ctk.CTkLabel(
        left, text=title,
        font=(t.FONT_DISPLAY, t.SIZE_TITLE, "bold"),
        text_color=t.INK, anchor="w",
    ).pack(anchor="w")

    ctk.CTkLabel(
        left, text=subtitle,
        font=(t.FONT_FAMILY, t.SIZE_SMALL),
        text_color=t.MUTED, anchor="w",
    ).pack(anchor="w", pady=(2, 0))

    if legend:
        leg_wrap = ctk.CTkFrame(header, fg_color="transparent")
        leg_wrap.pack(side="right", anchor="e")
        for color, label in legend:
            item = ctk.CTkFrame(leg_wrap, fg_color="transparent")
            item.pack(side="left", padx=(12, 0))
            swatch = ctk.CTkFrame(item, width=10, height=10,
                                  fg_color=color, corner_radius=2)
            swatch.pack(side="left", padx=(0, 6))
            swatch.pack_propagate(False)
            ctk.CTkLabel(
                item, text=label,
                font=(t.FONT_FAMILY, t.SIZE_SMALL),
                text_color=t.MUTED,
            ).pack(side="left")

    ctk.CTkFrame(parent, height=1, fg_color=t.BORDER_SOFT).pack(fill="x")


# ═══════════════════════════════════════════════════════════════════════════
#  Gráfico de líneas
# ═══════════════════════════════════════════════════════════════════════════
class LineChartCard(ctk.CTkFrame):
    """
    Tarjeta con gráfico de líneas temporales.
    Dibujado con tkinter.Canvas: no requiere matplotlib.
    Se redibuja automáticamente al cambiar el tamaño.
    """

    # Márgenes internos del canvas (px)
    _PL, _PR, _PT, _PB = 50, 20, 20, 44

    def __init__(self, parent, title: str, subtitle: str, datos):
        super().__init__(
            parent,
            fg_color=t.SURFACE,
            corner_radius=t.CORNER_RADIUS,
            border_width=1,
            border_color=t.BORDER,
        )
        self._datos = datos

        _build_chart_header(
            self, title, subtitle,
            legend=[(t.UDP_RED, "Automático"), (t.DERIV_TONE, "Derivado")],
        )

        wrap = ctk.CTkFrame(self, fg_color=t.SURFACE)
        wrap.pack(fill="both", expand=True, padx=20, pady=(8, 16))

        # Asignar datos ANTES de crear el canvas y hacer el bind
        self._canvas = tk.Canvas(
            wrap,
            bg=t.SURFACE,
            bd=0,
            highlightthickness=0,
            height=280,
        )
        self._canvas.bind("<Configure>", self._on_resize)
        self._canvas.pack(fill="both", expand=True)

    def _on_resize(self, event):
        if event.width < 60 or event.height < 60:
            return
        self._canvas.delete("all")
        self._draw_chart(event.width, event.height)

    def _draw_chart(self, W: int, H: int):
        datos = self._datos
        n = len(datos)
        if n < 2:
            return

        PL, PR, PT, PB = self._PL, self._PR, self._PT, self._PB
        cw = W - PL - PR
        ch = H - PT - PB

        auto_v  = [d["respondidos_auto"] for d in datos]
        deriv_v = [d["derivados"]        for d in datos]
        fechas  = [d["fecha"]            for d in datos]

        max_v = max(max(auto_v), max(deriv_v)) * 1.12 or 1

        def xp(i): return PL + (i / (n - 1)) * cw
        def yp(v): return PT + ch * (1.0 - v / max_v)

        # ── Líneas de grilla horizontales ──────────────────────────────
        steps = 4
        for k in range(steps + 1):
            v  = max_v * k / steps
            cy = yp(v)
            self._canvas.create_line(
                PL, cy, W - PR, cy,
                fill=t.BORDER, width=1,
            )
            self._canvas.create_text(
                PL - 6, cy,
                text=str(int(v)),
                anchor="e",
                fill=t.MUTED,
                font=("Helvetica", 9),
            )

        # ── Eje X ──────────────────────────────────────────────────────
        self._canvas.create_line(
            PL, yp(0), W - PR, yp(0),
            fill=t.BORDER, width=1,
        )

        # ── Área rellena: automático ───────────────────────────────────
        poly_a = []
        for i in range(n):
            poly_a += [xp(i), yp(auto_v[i])]
        poly_a += [xp(n - 1), yp(0), xp(0), yp(0)]
        self._canvas.create_polygon(*poly_a, fill="#FAE9EA", outline="")

        # ── Área rellena: derivados ────────────────────────────────────
        poly_d = []
        for i in range(n):
            poly_d += [xp(i), yp(deriv_v[i])]
        poly_d += [xp(n - 1), yp(0), xp(0), yp(0)]
        self._canvas.create_polygon(*poly_d, fill="#FBF5ED", outline="")

        # ── Línea: automático ──────────────────────────────────────────
        pts_a = []
        for i in range(n):
            pts_a += [xp(i), yp(auto_v[i])]
        self._canvas.create_line(
            *pts_a,
            fill=t.UDP_RED, width=2, smooth=True,
        )

        # ── Línea: derivados (punteada) ────────────────────────────────
        pts_d = []
        for i in range(n):
            pts_d += [xp(i), yp(deriv_v[i])]
        self._canvas.create_line(
            *pts_d,
            fill=t.DERIV_TONE, width=2,
            smooth=True, dash=(5, 3),
        )

        # ── Etiquetas eje X ────────────────────────────────────────────
        step = max(1, n // 6)
        for i in range(0, n, step):
            f   = fechas[i]
            lbl = f.strftime("%d %b") if hasattr(f, "strftime") else str(f)[-5:]
            self._canvas.create_text(
                xp(i), H - PB + 12,
                text=lbl, anchor="n",
                fill=t.MUTED, font=("Helvetica", 9),
            )


# ═══════════════════════════════════════════════════════════════════════════
#  Gráfico de dona
# ═══════════════════════════════════════════════════════════════════════════
class DonutChartCard(ctk.CTkFrame):
    """
    Tarjeta con gráfico de dona por categoría.
    Dibujado con tkinter.Canvas: no requiere matplotlib.
    """

    _COLORS = [
        t.UDP_RED,
        "#1F5C8F",
        "#8B5A14",
        "#4A6730",
        "#6B3A5A",
        "#757070",
    ]

    def __init__(self, parent, title: str, subtitle: str, datos: dict):
        super().__init__(
            parent,
            fg_color=t.SURFACE,
            corner_radius=t.CORNER_RADIUS,
            border_width=1,
            border_color=t.BORDER,
        )
        self._datos = datos

        _build_chart_header(self, title, subtitle)

        wrap = ctk.CTkFrame(self, fg_color=t.SURFACE)
        wrap.pack(fill="both", expand=True, padx=20, pady=(8, 16))

        self._canvas = tk.Canvas(
            wrap,
            bg=t.SURFACE,
            bd=0,
            highlightthickness=0,
            height=260,
        )
        self._canvas.bind("<Configure>", self._on_resize)
        self._canvas.pack(fill="both", expand=True)

    def _on_resize(self, event):
        if event.width < 60 or event.height < 60:
            return
        self._canvas.delete("all")
        self._draw_chart(event.width, event.height)

    def _draw_chart(self, W: int, H: int):
        items = list(self._datos.items())
        total = sum(v for _, v in items)
        if not total:
            return

        # ── Geometría de la dona ───────────────────────────────────────
        r       = min(W * 0.26, H * 0.38)
        inner_r = r * 0.60
        cx      = W * 0.30
        cy      = H * 0.50

        # ── Arcos (sectores) ───────────────────────────────────────────
        angle = -90.0
        for i, (cat, val) in enumerate(items):
            extent = (val / total) * 360.0
            color  = self._COLORS[i % len(self._COLORS)]
            self._canvas.create_arc(
                cx - r, cy - r,
                cx + r, cy + r,
                start=angle, extent=extent,
                fill=color,
                outline=t.SURFACE, width=2,
                style="pieslice",
            )
            angle += extent

        # ── Círculo interior (agujero de dona) ─────────────────────────
        self._canvas.create_oval(
            cx - inner_r, cy - inner_r,
            cx + inner_r, cy + inner_r,
            fill=t.SURFACE, outline="",
        )

        # ── Texto central ──────────────────────────────────────────────
        font_size = max(16, int(r * 0.30))
        self._canvas.create_text(
            cx, cy - r * 0.06,
            text=str(total),
            fill=t.INK,
            font=("Georgia", font_size, "bold"),
            anchor="center",
        )
        self._canvas.create_text(
            cx, cy + r * 0.22,
            text="TOTAL",
            fill=t.MUTED,
            font=("Helvetica", 9),
            anchor="center",
        )

        # ── Leyenda (a la derecha de la dona) ──────────────────────────
        lx      = cx + r + 22
        n_items = len(items)
        ly_start = max(20.0, (H - n_items * 28) / 2)

        for i, (cat, val) in enumerate(items):
            color = self._COLORS[i % len(self._COLORS)]
            ly    = ly_start + i * 28

            # Swatch
            self._canvas.create_rectangle(
                lx,      ly,
                lx + 12, ly + 12,
                fill=color, outline="",
            )

            # Etiqueta
            label = f"{cat}  ·  {val}"
            self._canvas.create_text(
                lx + 18, ly + 6,
                text=label,
                anchor="w",
                fill=t.INK_2,
                font=("Helvetica", 10),
            )
