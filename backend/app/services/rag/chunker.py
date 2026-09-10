"""
SIH26117 — Hierarchical Document Chunker
Implements structure-preserving document chunking over Phase 4 NormalizedDocument.
Preserves headings, section hierarchy, page provenance, and table row boundaries.
Enforces ~500 token target with ~50 token overlap using portable deterministic token estimation.
"""

import hashlib
import re
from typing import List, Optional

try:
    from app.services.ingestion.models import NormalizedDocument, ParsedTable
    from app.services.rag.base import DocumentChunk
except ImportError:
    from backend.app.services.ingestion.models import NormalizedDocument, ParsedTable
    from backend.app.services.rag.base import DocumentChunk


def estimate_token_count(text: str) -> int:
    """
    Portable, deterministic token estimator.
    Uses regex word and punctuation splitting (~1.3 tokens per whitespace-delimited word).
    Avoids hard dependency on heavyweight model tokenizers while maintaining precision.
    """
    if not text:
        return 0
    words = re.findall(r"\w+|[^\w\s]", text, re.UNICODE)
    return max(1, int(len(words) * 1.15))


def format_table_as_markdown(table: ParsedTable) -> str:
    """
    Render a ParsedTable as a structured Markdown table to preserve tabular semantics.
    """
    lines: List[str] = []
    if table.headers:
        header_row = "| " + " | ".join(str(h).strip() for h in table.headers) + " |"
        separator = "| " + " | ".join("---" for _ in table.headers) + " |"
        lines.append(header_row)
        lines.append(separator)

    for row in table.rows:
        row_str = "| " + " | ".join(str(c).strip() if c is not None else "" for c in row) + " |"
        lines.append(row_str)

    return "\n".join(lines)


class HierarchicalChunker:
    """
    Chunker that preserves document hierarchies, table boundaries, and page provenance.
    Target chunk size: ~500 tokens. Overlap: ~50 tokens.
    """

    def __init__(
        self,
        target_chunk_tokens: int = 500,
        chunk_overlap_tokens: int = 50,
        min_chunk_tokens: int = 40,
    ) -> None:
        self.target_chunk_tokens = target_chunk_tokens
        self.chunk_overlap_tokens = chunk_overlap_tokens
        self.min_chunk_tokens = min_chunk_tokens

    def chunk_document(self, doc: NormalizedDocument) -> List[DocumentChunk]:
        """
        Chunk a NormalizedDocument into a list of structure-preserving DocumentChunk objects.
        """
        chunks: List[DocumentChunk] = []
        chunk_idx = 0

        # Case A: Document has flowing sections (DOCX)
        if doc.sections:
            current_header = doc.original_filename
            for sec in doc.sections:
                if sec.heading:
                    current_header = f"{sec.heading} (Level {sec.heading_level or 1})"

                # 1. Chunk section narrative text
                if sec.text and sec.text.strip():
                    sec_chunks = self._chunk_text_block(
                        text=sec.text,
                        doc=doc,
                        page_number=sec.provenance.page_number if sec.provenance else None,
                        section_index=sec.section_index,
                        section_header=current_header,
                        start_idx=chunk_idx,
                    )
                    chunks.extend(sec_chunks)
                    chunk_idx += len(sec_chunks)

                # 2. Chunk section tables (preserving row boundaries)
                for table in sec.tables:
                    table_chunks = self._chunk_table(
                        table=table,
                        doc=doc,
                        page_number=table.provenance.page_number if table.provenance else None,
                        section_index=sec.section_index,
                        section_header=current_header,
                        start_idx=chunk_idx,
                    )
                    chunks.extend(table_chunks)
                    chunk_idx += len(table_chunks)

        # Case B: Document has paginated pages (PDF, Scanned Docs)
        elif doc.pages:
            for page in doc.pages:
                page_num = page.page_number

                # 1. Chunk page text
                if page.text and page.text.strip():
                    page_chunks = self._chunk_text_block(
                        text=page.text,
                        doc=doc,
                        page_number=page_num,
                        section_index=None,
                        section_header=f"Page {page_num}",
                        start_idx=chunk_idx,
                    )
                    chunks.extend(page_chunks)
                    chunk_idx += len(page_chunks)

                # 2. Chunk page tables
                for table in page.tables:
                    table_chunks = self._chunk_table(
                        table=table,
                        doc=doc,
                        page_number=page_num,
                        section_index=None,
                        section_header=f"Page {page_num} Table",
                        start_idx=chunk_idx,
                    )
                    chunks.extend(table_chunks)
                    chunk_idx += len(table_chunks)

        # Case C: Document has spreadsheets (XLSX, CSV)
        elif doc.sheets:
            for sheet in doc.sheets:
                for table in sheet.tables:
                    table_chunks = self._chunk_table(
                        table=table,
                        doc=doc,
                        page_number=None,
                        section_index=sheet.sheet_index,
                        section_header=f"Sheet: {sheet.sheet_name}",
                        start_idx=chunk_idx,
                    )
                    chunks.extend(table_chunks)
                    chunk_idx += len(table_chunks)

        # Case D: Fallback for unstructured single text payload
        if not chunks:
            # Create a single chunk if any raw text exists
            fallback_text = f"Document: {doc.original_filename}\nFormat: {doc.media_type}"
            c_hash = hashlib.sha256(fallback_text.encode("utf-8")).hexdigest()
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{doc.sha256[:12]}_c0000",
                    document_id=doc.document_id,
                    source_sha256=doc.sha256,
                    source_document=doc.original_filename,
                    page_number=1,
                    section_index=0,
                    section_header=doc.original_filename,
                    text=fallback_text,
                    content_sha256=c_hash,
                    token_count=estimate_token_count(fallback_text),
                    chunk_type="text",
                )
            )

        return chunks

    def _chunk_text_block(
        self,
        text: str,
        doc: NormalizedDocument,
        page_number: Optional[int],
        section_index: Optional[int],
        section_header: Optional[str],
        start_idx: int,
    ) -> List[DocumentChunk]:
        """
        Split narrative text block into sliding chunks respecting paragraph boundaries.
        """
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if not paragraphs:
            paragraphs = [text.strip()]

        chunks: List[DocumentChunk] = []
        current_paragraphs: List[str] = []
        current_tokens = 0
        local_idx = start_idx

        header_prefix = f"[{doc.original_filename}"
        if section_header:
            header_prefix += f" | {section_header}"
        if page_number is not None:
            header_prefix += f" | Page {page_number}"
        header_prefix += "]\n"

        for p in paragraphs:
            p_tokens = estimate_token_count(p)

            # If a single paragraph is enormous, split by sentences
            if p_tokens > self.target_chunk_tokens:
                sentences = re.split(r"(?<=[.!?])\s+", p)
                for s in sentences:
                    s_tokens = estimate_token_count(s)
                    if current_tokens + s_tokens > self.target_chunk_tokens and current_paragraphs:
                        body = "\n\n".join(current_paragraphs)
                        chunk_text = f"{header_prefix}\n{body}"
                        chunks.append(
                            self._create_chunk(
                                text=chunk_text,
                                doc=doc,
                                page_number=page_number,
                                section_index=section_index,
                                section_header=section_header,
                                chunk_idx=local_idx,
                                chunk_type="text",
                            )
                        )
                        local_idx += 1
                        # Maintain overlap: carry over last sentence if small enough
                        if s_tokens < self.chunk_overlap_tokens * 2:
                            current_paragraphs = [s]
                            current_tokens = s_tokens
                        else:
                            current_paragraphs = []
                            current_tokens = 0
                    else:
                        current_paragraphs.append(s)
                        current_tokens += s_tokens
                continue

            # Standard paragraph accumulation
            if current_tokens + p_tokens > self.target_chunk_tokens and current_paragraphs:
                body = "\n\n".join(current_paragraphs)
                chunk_text = f"{header_prefix}\n{body}"
                chunks.append(
                    self._create_chunk(
                        text=chunk_text,
                        doc=doc,
                        page_number=page_number,
                        section_index=section_index,
                        section_header=section_header,
                        chunk_idx=local_idx,
                        chunk_type="text",
                    )
                )
                local_idx += 1

                # Overlap: keep the last paragraph if its token count <= overlap threshold * 1.5
                if current_paragraphs and estimate_token_count(current_paragraphs[-1]) <= self.chunk_overlap_tokens * 1.5:
                    current_paragraphs = [current_paragraphs[-1], p]
                    current_tokens = estimate_token_count(current_paragraphs[0]) + p_tokens
                else:
                    current_paragraphs = [p]
                    current_tokens = p_tokens
            else:
                current_paragraphs.append(p)
                current_tokens += p_tokens

        # Flush final accumulated chunk
        if current_paragraphs:
            body = "\n\n".join(current_paragraphs)
            chunk_text = f"{header_prefix}\n{body}"
            chunks.append(
                self._create_chunk(
                    text=chunk_text,
                    doc=doc,
                    page_number=page_number,
                    section_index=section_index,
                    section_header=section_header,
                    chunk_idx=local_idx,
                    chunk_type="text",
                )
            )

        return chunks

    def _chunk_table(
        self,
        table: ParsedTable,
        doc: NormalizedDocument,
        page_number: Optional[int],
        section_index: Optional[int],
        section_header: Optional[str],
        start_idx: int,
    ) -> List[DocumentChunk]:
        """
        Convert a table into structured chunks while strictly preserving table row boundaries.
        Never splits a single row into separate chunks.
        """
        table_md = format_table_as_markdown(table)
        total_tokens = estimate_token_count(table_md)

        header_prefix = f"[{doc.original_filename}"
        if section_header:
            header_prefix += f" | {section_header}"
        if page_number is not None:
            header_prefix += f" | Page {page_number}"
        header_prefix += " (Structured Table)]\n"

        # If the entire table fits in target_chunk_tokens * 1.5, keep it atomic
        if total_tokens <= int(self.target_chunk_tokens * 1.5):
            chunk_text = f"{header_prefix}\n{table_md}"
            return [
                self._create_chunk(
                    text=chunk_text,
                    doc=doc,
                    page_number=page_number,
                    section_index=section_index,
                    section_header=section_header,
                    chunk_idx=start_idx,
                    chunk_type="table",
                    metadata={"table_id": table.table_id, "row_count": table.row_count},
                )
            ]

        # If table is large, slice rows while re-attaching headers to each slice
        chunks: List[DocumentChunk] = []
        local_idx = start_idx
        header_lines: List[str] = []
        if table.headers:
            header_lines.append("| " + " | ".join(str(h).strip() for h in table.headers) + " |")
            header_lines.append("| " + " | ".join("---" for _ in table.headers) + " |")

        current_rows: List[str] = []
        current_tokens = estimate_token_count("\n".join(header_lines))

        for row in table.rows:
            row_str = "| " + " | ".join(str(c).strip() if c is not None else "" for c in row) + " |"
            row_tokens = estimate_token_count(row_str)

            if current_tokens + row_tokens > self.target_chunk_tokens and current_rows:
                slice_table = "\n".join(header_lines + current_rows)
                chunk_text = f"{header_prefix}\n{slice_table}"
                chunks.append(
                    self._create_chunk(
                        text=chunk_text,
                        doc=doc,
                        page_number=page_number,
                        section_index=section_index,
                        section_header=section_header,
                        chunk_idx=local_idx,
                        chunk_type="table",
                        metadata={"table_id": table.table_id, "row_slice_count": len(current_rows)},
                    )
                )
                local_idx += 1
                current_rows = [row_str]
                current_tokens = estimate_token_count("\n".join(header_lines)) + row_tokens
            else:
                current_rows.append(row_str)
                current_tokens += row_tokens

        if current_rows:
            slice_table = "\n".join(header_lines + current_rows)
            chunk_text = f"{header_prefix}\n{slice_table}"
            chunks.append(
                self._create_chunk(
                    text=chunk_text,
                    doc=doc,
                    page_number=page_number,
                    section_index=section_index,
                    section_header=section_header,
                    chunk_idx=local_idx,
                    chunk_type="table",
                    metadata={"table_id": table.table_id, "row_slice_count": len(current_rows)},
                )
            )

        return chunks

    def _create_chunk(
        self,
        text: str,
        doc: NormalizedDocument,
        page_number: Optional[int],
        section_index: Optional[int],
        section_header: Optional[str],
        chunk_idx: int,
        chunk_type: str,
        metadata: Optional[dict] = None,
    ) -> DocumentChunk:
        """Helper to create a fully validated DocumentChunk."""
        c_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        p_str = f"p{page_number}" if page_number is not None else "p0"
        chunk_id = f"{doc.sha256[:12]}_{p_str}_c{chunk_idx:04d}"

        meta = {
            "source_document": doc.original_filename,
            "source_sha256": doc.sha256,
            "page_number": page_number,
            "section_index": section_index,
            "chunk_type": chunk_type,
        }
        if metadata:
            meta.update(metadata)

        return DocumentChunk(
            chunk_id=chunk_id,
            document_id=doc.document_id,
            source_sha256=doc.sha256,
            source_document=doc.original_filename,
            page_number=page_number,
            section_index=section_index,
            section_header=section_header,
            text=text,
            content_sha256=c_hash,
            token_count=estimate_token_count(text),
            chunk_type=chunk_type,
            metadata=meta,
        )
