/**
 * Document Ingestion and Metadata types.
 */

export interface DocumentIngestionResult {
  sha256: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  page_count: number;
  table_count: number;
  storage_path: string;
  extraction_summary: string;
  created_at?: string;
}

export interface ExtractedTable {
  page_number: number;
  table_index: number;
  headers: string[];
  rows: string[][];
  confidence?: number;
}

export interface NormalizedDocument {
  sha256: string;
  filename: string;
  file_type: string;
  size_bytes: number;
  pages_count: number;
  tables_count: number;
  extracted_text?: string;
  tables?: ExtractedTable[];
}
