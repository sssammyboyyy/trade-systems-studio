import type { AuditResult, Discrepancy } from "./types";

/**
 * In-browser keyword scanner, used only when no backend is reachable. It never computes
 * dollar amounts and never releases a document: every result is QUARANTINED for review.
 */

export interface ClientAuditOptions {
  file: File;
  onProgress?: (status: string) => void;
}

interface ExtractedToken {
  text: string;
  x: number;
  y: number;
  width: number;
  height: number;
  pageNumber: number;
}

export async function auditUploadedPdf(file: File): Promise<AuditResult> {
  // Dynamically import react-pdf on client to avoid Node.js SSR evaluation
  const { pdfjs } = await import("react-pdf");

  const blobUrl = URL.createObjectURL(file);
  const arrayBuffer = await file.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", arrayBuffer.slice(0));
  const documentSha256 = Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");

  const loadingTask = pdfjs.getDocument({ data: arrayBuffer });
  const pdfDoc = await loadingTask.promise;
  const numPages = pdfDoc.numPages;

  const items: ExtractedToken[] = [];

  for (let pageNum = 1; pageNum <= numPages; pageNum++) {
    const page = await pdfDoc.getPage(pageNum);
    const textContent = await page.getTextContent();
    // The viewport transform applies /Rotate and the MediaBox origin, so positions match
    // what the viewer renders (text-item transforms are in unrotated user space).
    const viewport = page.getViewport({ scale: 1.0 });
    const pageWidth = viewport.width;
    const pageHeight = viewport.height;

    for (const rawItem of textContent.items) {
      if (!("str" in rawItem) || !rawItem.str.trim()) continue;
      const item = rawItem as { str: string; transform: number[]; width: number; height: number };
      const m = pdfjs.Util.transform(viewport.transform, item.transform);
      const fontHeight = Math.hypot(m[2], m[3]) || item.height || 12;
      const rotated = Math.abs(m[1]) > Math.abs(m[0]);
      const runLength = (item.width || 40) * (viewport.scale || 1);
      // m[4], m[5] is the text baseline origin in top-left viewport space
      const left = rotated ? m[4] - fontHeight : m[4];
      const top = rotated ? m[5] : m[5] - fontHeight;
      const w = rotated ? fontHeight : runLength;
      const h = rotated ? runLength : fontHeight;

      const normX = Math.max(0, Math.min(995.0, (left / pageWidth) * 1000));
      const normY = Math.max(0, Math.min(995.0, (top / pageHeight) * 1000));
      const normW = Math.max(5.0, Math.min(1000.0 - normX - 0.1, (w / pageWidth) * 1000));
      const normH = Math.max(5.0, Math.min(1000.0 - normY - 0.1, (h / pageHeight) * 1000));

      items.push({
        text: item.str,
        x: Math.round(normX * 10) / 10,
        y: Math.round(normY * 10) / 10,
        width: Math.round(normW * 10) / 10,
        height: Math.round(normH * 10) / 10,
        pageNumber: pageNum,
      });
    }
  }

  const fullText = items.map((i) => i.text).join(" ");
  const upperText = fullText.toUpperCase();

  const discrepancies: Discrepancy[] = [];
  let detectedIncoterm = "UNSPECIFIED";
  let hasInsuranceMention = false;

  // 1. Incoterms
  if (upperText.includes("CIF") || upperText.includes("C.I.F.")) {
    detectedIncoterm = "CIF";
    if (upperText.includes("INSURANCE") || upperText.includes("MARINE")) {
      hasInsuranceMention = true;
    } else {
      const cifItem = items.find((i) => i.text.toUpperCase().includes("CIF")) || {
        x: 50.0,
        y: 120.0,
        width: 300.0,
        height: 25.0,
        pageNumber: 1,
      };

      discrepancies.push({
        id: "client-disc-cif-01",
        concept_id: "concept_1_customs",
        title: "CIF Invoice Without Itemised Insurance (keyword scan)",
        description:
          "The invoice mentions CIF terms but no insurance line. International freight and insurance are excluded from transaction value (19 U.S.C. § 1401a(b)(4)(A)) only when itemised. No amount is computed by the browser scanner.",
        statutory_code: "19 CFR § 152.103 / 19 U.S.C. § 1401a",
        severity: "warning",
        exposure_amount: "0.00",
        confidence: 0.75, // Cap heuristic confidence <= 0.75 (triggers visual dashed amber border)
        bounding_box: {
          x: cifItem.x,
          y: cifItem.y,
          width: Math.min(1000 - cifItem.x - 0.1, Math.max(180, cifItem.width * 2)),
          height: Math.min(1000 - cifItem.y - 0.1, Math.max(24, cifItem.height * 1.5)),
          page_number: cifItem.pageNumber,
          confidence: 0.75,
        },
        metadata: {
          incoterm: "CIF",
          remedy: "Submit Post-Summary Correction (PSC) to deduct actual insurance and recover duty overpayment.",
          verification_status: "Client-Side Offline Extraction: Requires Backend Audit Verification",
        },
      });
    }
  } else if (upperText.includes("FOB") || upperText.includes("F.O.B.")) {
    detectedIncoterm = "FOB";
  } else if (upperText.includes("DDP") || upperText.includes("D.D.P.")) {
    detectedIncoterm = "DDP";
  }

  // 2. Scan for freight overbilling indicators
  if (upperText.includes("CHASSIS SPLIT") || upperText.includes("DETENTION")) {
    const splitItem = items.find((i) =>
      i.text.toUpperCase().includes("CHASSIS") || i.text.toUpperCase().includes("DETENTION")
    ) || { x: 50.0, y: 350.0, width: 350.0, height: 25.0, pageNumber: 1 };

    discrepancies.push({
      id: "client-disc-freight-01",
      concept_id: "concept_2_freight",
      title: "Potential Accessorial Surcharge Keyword Detected",
      description:
        "A chassis split or detention charge is mentioned. Check it against the service contract and, for detention, the 46 CFR Part 541 billing requirements. No amount is computed by the browser scanner.",
      statutory_code: "Service contract / 46 CFR Part 541",
      severity: "warning",
      exposure_amount: "0.00",
      confidence: 0.75,
      bounding_box: {
        x: splitItem.x,
        y: splitItem.y,
        width: Math.min(1000 - splitItem.x - 0.1, Math.max(220, splitItem.width * 2)),
        height: Math.min(1000 - splitItem.y - 0.1, Math.max(24, splitItem.height * 1.5)),
        page_number: splitItem.pageNumber,
        confidence: 0.75,
      },
      metadata: {
        remedy: "Verify carrier service contract and terminal gate free time record before payment authorization.",
        verification_status: "Client-Side Offline Extraction: Requires Backend Audit Verification",
      },
    });
  }

  return {
    concept_id: "client_upload_audit",
    title: `Local Offline Scan: ${file.name}`,
    subtitle:
      discrepancies.length === 0
        ? "Zero keyword pattern anomalies detected in offline mode. Requires backend verification."
        : `${discrepancies.length} pattern anomalies flagged for review (client offline scan)`,
    document_filename: file.name,
    document_url: blobUrl,
    metrics: {
      penalty_exposure_avoided: "0.00",
      carrier_overbilling_caught: "0.00",
      drawback_unclaimed_unlocked: "0.00",
    },
    discrepancies,
    extracted_data: {
      filename: file.name,
      file_size_bytes: file.size,
      pages_scanned: numPages,
      incoterms_detected: detectedIncoterm,
      insurance_mention: hasInsuranceMention,
      audit_environment: "Client Browser Offline Scanner (Demonstration Only - Non-Statutory)",
      inspection_type: "Client-Side Offline Extraction: Requires Backend Audit Verification",
    },
    offline_fallback_active: true,
    audit_run_id: `LOCAL-${documentSha256.slice(0, 16).toUpperCase()}`,
    document_sha256: documentSha256,
    calc_version: "browser-keyword-scan",
    executed_at: new Date().toISOString(),
    source: "client",
    missing_fields: [],
    quarantine_reasons: ["BROWSER_SCAN_ONLY"],
    quarantine_status: "QUARANTINED",
  };
}
