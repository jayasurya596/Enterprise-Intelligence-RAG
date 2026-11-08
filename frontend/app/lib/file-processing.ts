export type ExtractedPage = { pageNumber: number | null; text: string };

const MAX_UPLOAD_BYTES = 5 * 1024 * 1024;
const MAX_TEXT_CHARS = 40_000;
const CHUNK_CHARS = 2_000;
const OVERLAP_CHARS = 0;
const MAX_CHUNKS_PER_DOCUMENT = 20;

export async function extractDocumentText(file: File): Promise<ExtractedPage[]> {
  if (file.size > MAX_UPLOAD_BYTES) {
    throw new Error("Free-tier prototype uploads are limited to 5 MB per file.");
  }

  const extension = file.name.split(".").pop()?.toLowerCase();
  let pages: ExtractedPage[];

  if (extension === "pdf") {
    const pdfjs = await import("pdfjs-dist");
    pdfjs.GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).toString();
    const pdf = await pdfjs.getDocument({ data: new Uint8Array(await file.arrayBuffer()) }).promise;
    pages = [];
    for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
      const page = await pdf.getPage(pageNumber);
      const content = await page.getTextContent();
      const text = content.items.map((item) => "str" in item ? item.str : "").join(" ").replace(/\s+/g, " ").trim();
      if (text) pages.push({ pageNumber, text });
    }
  } else if (extension === "docx") {
    const mammoth = await import("mammoth");
    const result = await mammoth.extractRawText({ arrayBuffer: await file.arrayBuffer() });
    pages = [{ pageNumber: null, text: result.value.trim() }];
  } else if (extension === "txt" || extension === "csv") {
    pages = [{ pageNumber: null, text: (await file.text()).trim() }];
  } else {
    throw new Error("Supported file types are PDF, DOCX, TXT, and CSV.");
  }

  const totalChars = pages.reduce((count, page) => count + page.text.length, 0);
  if (totalChars === 0) {
    throw new Error("No searchable text was found. Scanned PDFs need OCR, which this free prototype does not include.");
  }
  if (totalChars > MAX_TEXT_CHARS) {
    throw new Error("This file contains too much extracted text for the free prototype. Limit is 40,000 characters per file.");
  }
  return pages;
}

export function chunkPages(pages: ExtractedPage[]): Array<{ pageNumber: number | null; text: string }> {
  const chunks: Array<{ pageNumber: number | null; text: string }> = [];
  for (const page of pages) {
    let start = 0;
    while (start < page.text.length) {
      let end = Math.min(start + CHUNK_CHARS, page.text.length);
      if (end < page.text.length) {
        const boundary = page.text.lastIndexOf(" ", end);
        if (boundary > start + Math.floor(CHUNK_CHARS * 0.6)) end = boundary;
      }
      const text = page.text.slice(start, end).trim();
      if (text) chunks.push({ pageNumber: page.pageNumber, text });
      if (end >= page.text.length) break;
      start = Math.max(end - OVERLAP_CHARS, start + 1);
    }
  }
  if (chunks.length > MAX_CHUNKS_PER_DOCUMENT) {
    throw new Error("This document needs more than 20 search chunks. Reduce its size to stay within the free prototype limit.");
  }
  return chunks;
}
