"""Vista de gestión de documentos institucionales."""

import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

import theme as t
from components.scroll_fix import TrackpadScrollMixin
from data import db
from data.bus_client import IngestionError


# Mapa de colores por tipo de documento
TYPE_COLORS = {
    "reglamento":  (t.UDP_RED_SOFT, t.UDP_RED),
    "malla":       ("#EAF0E4", "#4A6730"),
    "calendario":  ("#F5EDE3", "#8B5A14"),
    "faq":         ("#E8F0EE", "#2A6B5E"),
    "tramite":     ("#F4ECE1", "#8B5A14"),
    "otro":        (t.SURFACE_2, t.MUTED),
}


class DocumentosView(TrackpadScrollMixin, ctk.CTkScrollableFrame):
    """Vista de gestión de documentos: cargar, listar, activar, eliminar."""

    def __init__(self, parent):
        self._scroll_accum = 0.0
        super().__init__(
            parent,
            fg_color=t.BG,
            corner_radius=1,   # 0 causa bug de renderizado en macOS
            scrollbar_button_color=t.BORDER,
            scrollbar_button_hover_color=t.MUTED,
        )

        # Estado interno
        self.archivo_seleccionado: Path = None
        self.filtro_estado = ctk.StringVar(value="todos")
        self.filtro_tipo = ctk.StringVar(value="todos")
        self.tipo_seleccionado = ctk.StringVar(value="reglamento")

        self._build_header()
        self._build_upload_card()
        self._build_filters_and_table()

    # ── Page header ─────────────────────────────────────────────────────
    def _build_header(self):
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", pady=(28, 24))

        ctk.CTkLabel(
            head, text="BASE DE CONOCIMIENTO",
            font=(t.FONT_FAMILY, 10, "bold"),
            text_color=t.UDP_RED, anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            head, text="Documentos institucionales",
            font=(t.FONT_DISPLAY, t.SIZE_DISPLAY, "bold"),
            text_color=t.INK, anchor="w",
        ).pack(anchor="w", pady=(4, 4))
        ctk.CTkLabel(
            head,
            text="Reglamentos, mallas, calendarios y demás documentos que SAGA utiliza para generar respuestas automáticas.",
            font=(t.FONT_FAMILY, t.SIZE_BODY),
            text_color=t.MUTED, anchor="w",
            wraplength=900, justify="left",
        ).pack(anchor="w")

        ctk.CTkFrame(self, height=1, fg_color=t.BORDER).pack(fill="x", pady=(0, 24))

    # ── Upload card ─────────────────────────────────────────────────────
    def _build_upload_card(self):
        card = ctk.CTkFrame(
            self, fg_color=t.SURFACE, corner_radius=t.CORNER_RADIUS,
            border_width=1, border_color=t.BORDER,
        )
        card.pack(fill="x", pady=(0, 24))

        # Header del card
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=24, pady=(20, 4))
        ctk.CTkLabel(
            head, text="Cargar nuevo documento",
            font=(t.FONT_DISPLAY, t.SIZE_TITLE, "bold"),
            text_color=t.INK, anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            head, text="Formato aceptado: .pdf. El sistema extrae el texto, genera chunks vectoriales en ChromaDB y tripletas RDF en el Knowledge Graph.",
            font=(t.FONT_FAMILY, t.SIZE_SMALL),
            text_color=t.MUTED, anchor="w",
            wraplength=900, justify="left",
        ).pack(anchor="w", pady=(2, 0))

        ctk.CTkFrame(card, height=1, fg_color=t.BORDER_SOFT).pack(
            fill="x", pady=(14, 0)
        )

        # ── Zona de selección ──────────────────────────────────────────
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=24, pady=20)

        # Dropzone clickable
        self.dropzone = ctk.CTkFrame(
            body, fg_color=t.SURFACE_2, corner_radius=8,
            border_width=2, border_color=t.BORDER, height=130,
        )
        self.dropzone.pack(fill="x")
        self.dropzone.pack_propagate(False)

        self.dz_icon = ctk.CTkLabel(
            self.dropzone, text="⬆",
            font=(t.FONT_FAMILY, 28),
            text_color=t.MUTED,
        )
        self.dz_icon.pack(pady=(22, 4))

        self.dz_text = ctk.CTkLabel(
            self.dropzone, text="Haz clic para seleccionar un archivo",
            font=(t.FONT_FAMILY, t.SIZE_BODY, "bold"),
            text_color=t.INK,
        )
        self.dz_text.pack()

        self.dz_hint = ctk.CTkLabel(
            self.dropzone, text="Máximo 25 MB · sólo PDF",
            font=(t.FONT_FAMILY, t.SIZE_SMALL),
            text_color=t.MUTED,
        )
        self.dz_hint.pack(pady=(2, 16))

        # Hacer toda la dropzone clickable
        for w in [self.dropzone, self.dz_icon, self.dz_text, self.dz_hint]:
            w.bind("<Button-1>", lambda e: self._seleccionar_archivo())
            w.bind("<Enter>", lambda e: self._dz_hover(True))
            w.bind("<Leave>", lambda e: self._dz_hover(False))
            w.configure(cursor="hand2")

        # ── Fila de tipo + botón ────────────────────────────────────────
        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.pack(fill="x", pady=(16, 0))

        # Selector de tipo
        type_wrap = ctk.CTkFrame(actions, fg_color="transparent")
        type_wrap.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            type_wrap, text="TIPO DE DOCUMENTO",
            font=(t.FONT_FAMILY, 10, "bold"),
            text_color=t.INK_2, anchor="w",
        ).pack(anchor="w", pady=(0, 4))

        self.tipo_combo = ctk.CTkOptionMenu(
            type_wrap,
            variable=self.tipo_seleccionado,
            values=list(db.TIPOS_DOCUMENTO.keys()),
            width=260,
            height=36,
            corner_radius=6,
            fg_color=t.SURFACE,
            button_color=t.SURFACE,
            button_hover_color=t.SURFACE_2,
            text_color=t.INK,
            dropdown_fg_color=t.SURFACE,
            dropdown_hover_color=t.SURFACE_2,
            dropdown_text_color=t.INK,
            font=(t.FONT_FAMILY, t.SIZE_BODY),
        )
        self.tipo_combo.pack(anchor="w")
        # Borde manual (CTkOptionMenu no expone border)
        self.tipo_combo.configure(button_color=t.BORDER)

        # Botón principal
        self.btn_upload = ctk.CTkButton(
            actions,
            text="  Cargar documento",
            font=(t.FONT_FAMILY, t.SIZE_BODY, "bold"),
            fg_color=t.UDP_RED,
            hover_color=t.UDP_RED_DARK,
            text_color="white",
            corner_radius=6,
            height=42,
            width=180,
            command=self._cargar_documento,
        )
        self.btn_upload.pack(side="right", anchor="se")

    def _dz_hover(self, enter: bool):
        if enter:
            self.dropzone.configure(border_color=t.UDP_RED, fg_color=t.UDP_RED_TINT)
        else:
            self.dropzone.configure(border_color=t.BORDER, fg_color=t.SURFACE_2)

    def _seleccionar_archivo(self):
        path = filedialog.askopenfilename(
            title="Seleccionar documento institucional",
            filetypes=[("PDF", "*.pdf")],
        )
        if not path:
            return
        self.archivo_seleccionado = Path(path)
        tamano_kb = max(1, self.archivo_seleccionado.stat().st_size // 1024)
        self.dz_icon.configure(text="✓", text_color=t.UDP_RED)
        self.dz_text.configure(
            text=self.archivo_seleccionado.name,
            text_color=t.INK,
        )
        self.dz_hint.configure(
            text=f"{tamano_kb} KB · Listo para cargar",
            text_color=t.SUCCESS,
        )

    def _cargar_documento(self):
        if not self.archivo_seleccionado:
            messagebox.showwarning(
                "Selecciona un archivo",
                "Debes seleccionar un archivo antes de cargar el documento.",
            )
            return

        ext = self.archivo_seleccionado.suffix.lower()
        if ext != ".pdf":
            messagebox.showerror(
                "Formato no soportado",
                "El motor RAG sólo indexa archivos PDF. "
                f"Recibido: {ext or '(sin extensión)'}.",
            )
            return

        # Bloquear UI y disparar ingestión en background. El servicio docum
        # extrae texto, embebe chunks en ChromaDB y, si GRAPH_EXTRACT_ON_INGEST
        # está activo, escribe tripletas en el Knowledge Graph (Fuseki/RDFLib).
        self.btn_upload.configure(
            state="disabled",
            text="  Procesando…",
        )
        self.dz_icon.configure(text="⏳", text_color=t.MUTED)
        self.dz_hint.configure(
            text="Enviando al servicio de ingestión…",
            text_color=t.MUTED,
        )

        archivo = self.archivo_seleccionado
        tipo = self.tipo_seleccionado.get()

        def _worker():
            try:
                doc = db.ingest_documento(archivo, tipo)
                self.after(0, lambda: self._on_ingest_ok(doc))
            except IngestionError as e:
                self.after(0, lambda err=e: self._on_ingest_fail(str(err)))
            except Exception as e:  # noqa: BLE001
                self.after(0, lambda err=e: self._on_ingest_fail(f"Error inesperado: {err}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_ingest_ok(self, doc: dict):
        chunks = doc.get("chunks_indexados", 0)
        messagebox.showinfo(
            "Documento indexado",
            f"'{doc['nombre']}' fue ingresado al motor RAG.\n\n"
            f"• Chunks vectoriales generados: {chunks}\n"
            f"• Tripletas KG: extraídas si el servicio docum tiene "
            f"GRAPH_EXTRACT_ON_INGEST=true.\n"
            f"• Ya disponible para responder consultas vía ragsv.",
        )
        self._reset_dropzone()
        self._refresh_table()

    def _on_ingest_fail(self, message: str):
        messagebox.showerror(
            "No se pudo indexar el documento",
            f"{message}\n\n"
            "Verifica que docker-compose esté arriba (BUS + ChromaDB + servicio docum):\n"
            "    docker-compose up -d",
        )
        self._reset_dropzone()

    def _reset_dropzone(self):
        self.archivo_seleccionado = None
        self.dz_icon.configure(text="⬆", text_color=t.MUTED)
        self.dz_text.configure(text="Haz clic para seleccionar un archivo")
        self.dz_hint.configure(
            text="Máximo 25 MB · sólo PDF",
            text_color=t.MUTED,
        )
        self.btn_upload.configure(state="normal", text="  Cargar documento")

    # ── Filtros + tabla ─────────────────────────────────────────────────
    def _build_filters_and_table(self):
        self.table_card = ctk.CTkFrame(
            self, fg_color=t.SURFACE, corner_radius=t.CORNER_RADIUS,
            border_width=1, border_color=t.BORDER,
        )
        self.table_card.pack(fill="x", pady=(0, 28))

        # Header con filtros
        head = ctk.CTkFrame(self.table_card, fg_color="transparent")
        head.pack(fill="x", padx=24, pady=(20, 12))

        # Lado izquierdo: títulos
        left = ctk.CTkFrame(head, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            left, text="Repositorio actual",
            font=(t.FONT_DISPLAY, t.SIZE_TITLE, "bold"),
            text_color=t.INK, anchor="w",
        ).pack(anchor="w")
        self.lbl_count = ctk.CTkLabel(
            left, text="",
            font=(t.FONT_FAMILY, t.SIZE_SMALL),
            text_color=t.MUTED, anchor="w",
        )
        self.lbl_count.pack(anchor="w", pady=(2, 0))

        # Lado derecho: filtros
        right = ctk.CTkFrame(head, fg_color="transparent")
        right.pack(side="right", anchor="ne")

        # Filtro estado
        f1 = ctk.CTkFrame(right, fg_color="transparent")
        f1.pack(side="left", padx=(0, 12))
        ctk.CTkLabel(
            f1, text="ESTADO",
            font=(t.FONT_FAMILY, 9, "bold"),
            text_color=t.INK_2, anchor="w",
        ).pack(anchor="w", pady=(0, 2))
        cb1 = ctk.CTkOptionMenu(
            f1,
            variable=self.filtro_estado,
            values=["todos", "activo", "inactivo"],
            width=130, height=30,
            corner_radius=6,
            fg_color=t.SURFACE,
            button_color=t.BORDER,
            button_hover_color=t.SURFACE_2,
            text_color=t.INK,
            dropdown_fg_color=t.SURFACE,
            dropdown_hover_color=t.SURFACE_2,
            dropdown_text_color=t.INK,
            font=(t.FONT_FAMILY, t.SIZE_SMALL),
            command=lambda _: self._refresh_table(),
        )
        cb1.pack()

        # Filtro tipo
        f2 = ctk.CTkFrame(right, fg_color="transparent")
        f2.pack(side="left")
        ctk.CTkLabel(
            f2, text="TIPO",
            font=(t.FONT_FAMILY, 9, "bold"),
            text_color=t.INK_2, anchor="w",
        ).pack(anchor="w", pady=(0, 2))
        cb2 = ctk.CTkOptionMenu(
            f2,
            variable=self.filtro_tipo,
            values=["todos"] + list(db.TIPOS_DOCUMENTO.keys()),
            width=180, height=30,
            corner_radius=6,
            fg_color=t.SURFACE,
            button_color=t.BORDER,
            button_hover_color=t.SURFACE_2,
            text_color=t.INK,
            dropdown_fg_color=t.SURFACE,
            dropdown_hover_color=t.SURFACE_2,
            dropdown_text_color=t.INK,
            font=(t.FONT_FAMILY, t.SIZE_SMALL),
            command=lambda _: self._refresh_table(),
        )
        cb2.pack()

        # Frame que contendrá la tabla
        self.table_body = ctk.CTkFrame(self.table_card, fg_color="transparent")
        self.table_body.pack(fill="x")

        self._refresh_table()

    def _refresh_table(self):
        # Limpiar tabla
        for w in self.table_body.winfo_children():
            w.destroy()

        docs = db.get_documentos(
            filtro_estado=self.filtro_estado.get(),
            filtro_tipo=self.filtro_tipo.get(),
        )
        self.lbl_count.configure(
            text=f"{len(docs)} documento(s) coincidente(s) con los filtros aplicados."
        )

        # Cabecera
        head_row = ctk.CTkFrame(self.table_body, fg_color=t.SURFACE_2, height=34)
        head_row.pack(fill="x")
        head_row.pack_propagate(False)

        ctk.CTkLabel(head_row, text="DOCUMENTO",
                     font=(t.FONT_FAMILY, 10, "bold"),
                     text_color=t.MUTED).place(relx=0.02, rely=0.5, anchor="w")
        ctk.CTkLabel(head_row, text="TIPO",
                     font=(t.FONT_FAMILY, 10, "bold"),
                     text_color=t.MUTED).place(relx=0.42, rely=0.5, anchor="w")
        ctk.CTkLabel(head_row, text="CARGADO",
                     font=(t.FONT_FAMILY, 10, "bold"),
                     text_color=t.MUTED).place(relx=0.58, rely=0.5, anchor="w")
        ctk.CTkLabel(head_row, text="TAMAÑO",
                     font=(t.FONT_FAMILY, 10, "bold"),
                     text_color=t.MUTED).place(relx=0.72, rely=0.5, anchor="w")
        ctk.CTkLabel(head_row, text="ESTADO",
                     font=(t.FONT_FAMILY, 10, "bold"),
                     text_color=t.MUTED).place(relx=0.81, rely=0.5, anchor="w")
        ctk.CTkLabel(head_row, text="ACCIONES",
                     font=(t.FONT_FAMILY, 10, "bold"),
                     text_color=t.MUTED, anchor="e").place(relx=0.98, rely=0.5, anchor="e")

        ctk.CTkFrame(self.table_body, height=1, fg_color=t.BORDER).pack(fill="x")

        if not docs:
            empty = ctk.CTkFrame(self.table_body, fg_color="transparent", height=120)
            empty.pack(fill="x")
            empty.pack_propagate(False)
            ctk.CTkLabel(
                empty, text="No hay documentos que coincidan con los filtros aplicados.",
                font=(t.FONT_FAMILY, t.SIZE_BODY),
                text_color=t.MUTED,
            ).pack(expand=True)
            ctk.CTkFrame(self.table_body, height=14, fg_color="transparent").pack(fill="x")
            return

        for i, doc in enumerate(docs):
            self._build_doc_row(doc, alt=(i % 2 == 1))

        ctk.CTkFrame(self.table_body, height=14, fg_color="transparent").pack(fill="x")

    def _build_doc_row(self, doc, alt=False):
        bg = t.SURFACE_2 if alt else t.SURFACE

        row = ctk.CTkFrame(self.table_body, fg_color=bg, height=68)
        row.pack(fill="x")
        row.pack_propagate(False)

        # ── Documento (icono + nombre + metadata) ──────────────────────
        # Icon
        icon = ctk.CTkFrame(row, width=38, height=38,
                            fg_color=t.UDP_RED_SOFT, corner_radius=6)
        icon.place(relx=0.02, rely=0.5, anchor="w")
        icon.pack_propagate(False)
        ctk.CTkLabel(
            icon, text="📄",
            font=(t.FONT_FAMILY, 14),
            text_color=t.UDP_RED,
        ).place(relx=0.5, rely=0.5, anchor="center")

        # Nombre + metadata
        info = ctk.CTkFrame(row, fg_color="transparent")
        info.place(relx=0.07, rely=0.5, anchor="w")
        ctk.CTkLabel(
            info, text=self._truncate(doc["nombre"], 45),
            font=(t.FONT_FAMILY, t.SIZE_BODY, "bold"),
            text_color=t.INK, anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            info, text=f"{doc['paginas']} págs · {doc['cargado_por']}",
            font=(t.FONT_FAMILY, t.SIZE_TINY),
            text_color=t.MUTED, anchor="w",
        ).pack(anchor="w", pady=(1, 0))

        # ── Tipo (tag) ─────────────────────────────────────────────────
        bg_tag, fg_tag = TYPE_COLORS.get(doc["tipo"], (t.SURFACE_2, t.MUTED))
        tag = ctk.CTkFrame(row, fg_color=bg_tag, corner_radius=4, height=22)
        tag.place(relx=0.42, rely=0.5, anchor="w")
        ctk.CTkLabel(
            tag, text=db.TIPOS_DOCUMENTO.get(doc["tipo"], doc["tipo"]).upper(),
            font=(t.FONT_FAMILY, 9, "bold"),
            text_color=fg_tag,
        ).pack(padx=8, pady=2)

        # ── Cargado ────────────────────────────────────────────────────
        ctk.CTkLabel(
            row, text=doc["fecha_carga"].strftime("%d %b %Y · %H:%M"),
            font=(t.FONT_FAMILY, t.SIZE_SMALL),
            text_color=t.MUTED, anchor="w",
        ).place(relx=0.58, rely=0.5, anchor="w")

        # ── Tamaño ─────────────────────────────────────────────────────
        ctk.CTkLabel(
            row, text=f"{doc['tamano_kb']} KB",
            font=(t.FONT_FAMILY, t.SIZE_SMALL),
            text_color=t.MUTED, anchor="w",
        ).place(relx=0.72, rely=0.5, anchor="w")

        # ── Estado ─────────────────────────────────────────────────────
        if doc["estado"] == "activo":
            est_bg, est_fg, est_txt = t.SUCCESS_BG, t.SUCCESS, "Activo"
        else:
            est_bg, est_fg, est_txt = t.SURFACE_2, t.MUTED, "Inactivo"

        est_wrap = ctk.CTkFrame(row, fg_color=est_bg, corner_radius=12, height=24)
        est_wrap.place(relx=0.81, rely=0.5, anchor="w")
        dot = ctk.CTkFrame(est_wrap, width=6, height=6,
                           fg_color=est_fg, corner_radius=3)
        dot.pack(side="left", padx=(10, 5), pady=9)
        dot.pack_propagate(False)
        ctk.CTkLabel(
            est_wrap, text=est_txt,
            font=(t.FONT_FAMILY, t.SIZE_TINY, "bold"),
            text_color=est_fg,
        ).pack(side="left", padx=(0, 12))

        # ── Acciones ───────────────────────────────────────────────────
        acciones = ctk.CTkFrame(row, fg_color="transparent")
        acciones.place(relx=0.98, rely=0.5, anchor="e")

        toggle_lbl = "Desactivar" if doc["estado"] == "activo" else "Activar"
        ctk.CTkButton(
            acciones, text=toggle_lbl,
            font=(t.FONT_FAMILY, 11),
            fg_color="transparent",
            hover_color=t.SURFACE_2,
            text_color=t.INK_2,
            border_width=1,
            border_color=t.BORDER,
            corner_radius=4,
            height=28, width=88,
            command=lambda d=doc: self._toggle(d["id"]),
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            acciones, text="✕",
            font=(t.FONT_FAMILY, 12, "bold"),
            fg_color="transparent",
            hover_color=t.UDP_RED_SOFT,
            text_color=t.UDP_RED,
            corner_radius=4,
            height=28, width=32,
            command=lambda d=doc: self._delete(d["id"], d["nombre"]),
        ).pack(side="left")

        # Separador
        ctk.CTkFrame(self.table_body, height=1, fg_color=t.BORDER_SOFT).pack(fill="x")

    @staticmethod
    def _truncate(text: str, n: int) -> str:
        return text if len(text) <= n else text[:n - 1] + "…"

    def _toggle(self, doc_id: int):
        db.toggle_documento(doc_id)
        self._refresh_table()

    def _delete(self, doc_id: int, nombre: str):
        if messagebox.askyesno(
            "Eliminar documento",
            f"¿Eliminar definitivamente '{nombre}'?\n\nEsta acción no se puede deshacer.",
        ):
            db.delete_documento(doc_id)
            self._refresh_table()
