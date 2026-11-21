"use client";

import { BENCHMARK } from "@/lib/metrics";
import React, { useState } from "react";
import { Terminal, Copy, Check, Zap, Play, Loader2 } from "lucide-react";
import { motion } from "framer-motion";

const isBrowser = typeof window !== "undefined";
const isPublicHost =
  isBrowser &&
  window.location.hostname !== "localhost" &&
  window.location.hostname !== "127.0.0.1";
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || (isPublicHost ? "" : "http://localhost:8000");

type EndpointKey = "cargowise" | "hts_classify" | "hts_fail_closed" | "valuation";

interface EndpointConfig {
  label: string;
  path: string;
  method: "POST" | "GET";
  benchmarkLabel: string;
  payload: Record<string, any>;
  offlinePreview: string;
}

const ENDPOINT_CONFIGS: Record<EndpointKey, EndpointConfig> = {
  cargowise: {
    label: "/export/cargowise-xml",
    path: "/api/v1/export/cargowise-xml",
    method: "POST",
    benchmarkLabel: `Tier 2 p99: ${BENCHMARK.tier2_p99_ms} ms`,
    payload: {
      shipment_id: "S00001000",
      declaration_id: "B00001000",
      port_origin_code: "CNSZX",
      port_origin_name: "Shenzhen",
      port_dest_code: "USLAX",
      port_dest_name: "Los Angeles",
      incoterm: "CIF",
      invoice_amount: "148500.00",
      insurance_amount: "1450.00",
    },
    offlinePreview: `HTTP/1.1 200 OK
Content-Type: application/xml
X-Engine-Mode: Static Example Response (Run Local Backend to Execute Live)
X-Deterministic-Engine: python-decimal-std

<UniversalInterchange xmlns="http://www.cargowise.com/Schemas/Universal/2011/11" version="1.1">
  <Header>
    <SenderID>TRADESYSTEMS_PREAUDIT</SenderID>
    <RecipientID>CW1_EADAPTOR_PRD</RecipientID>
    <CorrelationID>CW-C9F321B08E14A702</CorrelationID>
  </Header>
  <Body>
    <UniversalShipment xmlns="http://www.cargowise.com/Schemas/Universal/2011/11" version="1.1">
      <Shipment>
        <DataContext>
          <DataTargetCollection>
            <DataTarget><Type>ForwardingShipment</Type><Key>S00001000</Key></DataTarget>
            <DataTarget><Type>CustomsDeclaration</Type><Key>B00001000</Key></DataTarget>
          </DataTargetCollection>
          <Company><Code>CPH</Code></Company>
          <EnterpriseID>TRN</EnterpriseID>
          <ServerID>A04</ServerID>
        </DataContext>
        <PortOfOrigin><Code>CNSZX</Code><Name>Shenzhen</Name></PortOfOrigin>
        <PortOfDestination><Code>USLAX</Code><Name>Los Angeles</Name></PortOfDestination>
        <CommercialInvoiceCollection>
          <CommercialInvoice>
            <InvoiceNumber>CI-2026-01</InvoiceNumber>
            <Incoterm><Code>CIF</Code></Incoterm>
            <InvoiceAmount Currency="USD">148500.00</InvoiceAmount>
            <InsuranceAmount Currency="USD">1450.00</InsuranceAmount>
          </CommercialInvoice>
        </CommercialInvoiceCollection>
      </Shipment>
    </UniversalShipment>
  </Body>
</UniversalInterchange>`,
  },
  hts_classify: {
    label: "/hts/classify (Match)",
    path: "/api/v1/hts/classify",
    method: "POST",
    benchmarkLabel: "HTS p99: 0.242 ms",
    payload: {
      product_title: "Industrial Brushless DC Drone Motor with Integrated ESC",
      product_description: "480W brushless DC UAV propulsion motor with electronic speed controller",
      country_of_origin: "TW",
      entered_value: "45000.00",
      is_ocean_freight: true,
      freight_and_insurance: "1500.00",
    },
    offlinePreview: `HTTP/1.1 200 OK
Content-Type: application/json
X-Engine-Mode: Static Example Response (Run Local Backend to Execute Live)
X-GRI-Rule: WCO GRI 3(b) Essential Character

{
  "item_id": "hts-drone_motor",
  "product_title": "Industrial Brushless DC Drone Motor with Integrated ESC",
  "country_of_origin": "TW",
  "classified_hts_code": "8501.31.8000",
  "confidence": 0.94,
  "requires_human_review": false,
  "landed_cost": {
    "entered_value": "45000.00",
    "duty_rate_ad_valorem": "0.024",
    "customs_duty": "1080.00",
    "section_301_rate": "0.00",
    "section_301_duty": "0.00",
    "mpf_rate": "0.003464",
    "mpf_min_cap": "34.58",
    "mpf_max_cap": "670.86",
    "mpf_fee": "155.88",
    "hmf_rate": "0.00125",
    "hmf_fee": "56.25",
    "freight_and_insurance": "1500.00",
    "total_customs_cost": "1292.13",
    "total_landed_cost": "47792.13",
    "fiscal_year": "FY2027"
  }
}`,
  },
  hts_fail_closed: {
    label: "/hts/classify (Fail-Closed)",
    path: "/api/v1/hts/classify",
    method: "POST",
    benchmarkLabel: "HTS p99: 0.242 ms",
    payload: {
      product_title: "Cotton T-Shirt",
      product_description: "100% ring-spun cotton crewneck tee",
      country_of_origin: "VN",
      entered_value: "12000.00",
      is_ocean_freight: true,
      freight_and_insurance: "500.00",
    },
    offlinePreview: `HTTP/1.1 200 OK
Content-Type: application/json
X-Engine-Mode: Static Example Response (Run Local Backend to Execute Live)
X-Fail-Closed-Gate: Conf(e) < 0.85 -> Broker Escalation

{
  "item_id": "hts-unclassified",
  "product_title": "Cotton T-Shirt",
  "country_of_origin": "VN",
  "classified_hts_code": "REQUIRES_BROKER_REVIEW",
  "confidence": 0.0,
  "requires_human_review": true,
  "gri_path": [],
  "chapter_notes_cited": [
    "Unclassified merchandise: product description does not match pre-computed GRI patterns.",
    "Mandatory review by licensed customs broker required under 19 CFR Part 111 before CBP entry filing."
  ],
  "landed_cost": {
    "entered_value": "12000.00",
    "duty_rate_ad_valorem": "0.00",
    "customs_duty": "0.00",
    "mpf_fee": "41.57",
    "hmf_fee": "15.00",
    "total_customs_cost": "56.57",
    "total_landed_cost": "12556.57",
    "fiscal_year": "FY2027"
  }
}`,
  },
  valuation: {
    label: "/valuation/audit-entry",
    path: "/api/v1/valuation/audit-entry",
    method: "POST",
    benchmarkLabel: `Tier 2 p99: ${BENCHMARK.tier2_p99_ms} ms`,
    payload: {
      entry_number: "CBP-7501-84920184",
      importer_of_record: "Pacific Tech Imports LLC",
      declared_transaction_value: "450000.00",
      duty_rate_ad_valorem: "0.054",
      current_entry_units: 15000,
      invoice_incoterm: "CIF Los Angeles",
      international_freight_in_invoice: "24500.00",
      marine_insurance_in_invoice: "3200.00",
      months_elapsed: 9,
    },
    offlinePreview: `HTTP/1.1 200 OK
Content-Type: application/json
X-Engine-Mode: Static Example Response (Run Local Backend to Execute Live)
X-Valuation-Rule: 19 U.S.C. § 1401a / 19 CFR § 152.103

{
  "entry_number": "CBP-7501-84920184",
  "importer_of_record": "Pacific Tech Imports LLC",
  "declared_transaction_value": "450000.00",
  "duty_rate_ad_valorem": "0.054",
  "improper_cif_overvaluation": "27700.00",
  "assists_omitted_cost": "57750.00",
  "adjusted_lawful_dutiable_value": "480050.00",
  "lawful_duty_due": "25922.70",
  "declared_duty_paid": "24300.00",
  "duty_underpayment": "1622.70",
  "statutory_interest_19usc1505": "87.21",
  "negligence_penalty_exposure": "3245.40",
  "gross_negligence_penalty_exposure": "6490.80",
  "prior_disclosure_tender_amount": "1709.91",
  "total_liability_avoided": "4780.89"
}`,
  },
};

export const DeveloperApiSandbox: React.FC = () => {
  const [copied, setCopied] = useState(false);
  const [activeEndpoint, setActiveEndpoint] = useState<EndpointKey>("cargowise");
  const [isRunning, setIsRunning] = useState(false);
  const [responseOutput, setResponseOutput] = useState<string | null>(null);
  const [isLiveResponse, setIsLiveResponse] = useState(false);
  const [latencyText, setLatencyText] = useState<string>(ENDPOINT_CONFIGS.cargowise.benchmarkLabel);

  const displayBaseUrl = API_BASE || "http://localhost:8000";
  const currentConfig = ENDPOINT_CONFIGS[activeEndpoint];

  const curlSnippet = `curl -X ${currentConfig.method} "${displayBaseUrl}${currentConfig.path}" \\
  -H "Content-Type: application/json" \\
  -d '${JSON.stringify(currentConfig.payload, null, 2)}'`;

  const handleSelectEndpoint = (key: EndpointKey) => {
    setActiveEndpoint(key);
    setResponseOutput(null);
    setIsLiveResponse(false);
    setLatencyText(ENDPOINT_CONFIGS[key].benchmarkLabel);
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(curlSnippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRun = async () => {
    setIsRunning(true);
    if (!API_BASE) {
      // Static public host: never trigger blocked loopback fetch to localhost:8000
      setIsLiveResponse(false);
      setLatencyText(`Static Preview (${currentConfig.benchmarkLabel})`);
      setResponseOutput(currentConfig.offlinePreview);
      setIsRunning(false);
      return;
    }

    const startTime = performance.now();
    try {
      const res = await fetch(`${API_BASE}${currentConfig.path}`, {
        method: currentConfig.method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(currentConfig.payload),
      });
      const elapsed = (performance.now() - startTime).toFixed(2);
      setLatencyText(`Live ASGI: ${elapsed} ms`);
      setIsLiveResponse(true);

      if (res.ok) {
        const text = await res.text();
        try {
          const json = JSON.parse(text);
          setResponseOutput(
            `HTTP/1.1 200 OK\nContent-Type: application/json\nX-Latency-Ms: ${elapsed}ms\nX-Engine-State: Live ASGI Engine (${API_BASE})\n\n${JSON.stringify(json, null, 2)}`
          );
        } catch {
          setResponseOutput(
            `HTTP/1.1 200 OK\nContent-Type: application/xml\nX-Latency-Ms: ${elapsed}ms\nX-Engine-State: Live ASGI Engine (${API_BASE})\n\n${text}`
          );
        }
      } else {
        const errText = await res.text();
        setResponseOutput(`HTTP/1.1 ${res.status} ${res.statusText}\nX-Latency-Ms: ${elapsed}ms\n\n${errText}`);
      }
    } catch {
      setIsLiveResponse(false);
      setLatencyText(`Static Preview (${currentConfig.benchmarkLabel})`);
      setResponseOutput(currentConfig.offlinePreview);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="w-full bg-terminal-slate border border-terminal-subtle rounded-xl overflow-hidden p-4 font-mono text-xs shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-terminal-elevated">
        <div className="flex items-center gap-2 flex-wrap">
          <Terminal className="w-4 h-4 text-emerald-400" />
          <span className="font-bold text-slate-200">Developer API &amp; curl Playground</span>
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold">
            <Zap className="w-3 h-3" />
            <span>{latencyText}</span>
          </span>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex bg-terminal-elevated rounded-lg p-0.5 border border-terminal-border/60 flex-wrap">
            {(Object.keys(ENDPOINT_CONFIGS) as EndpointKey[]).map((key) => (
              <button
                key={key}
                onClick={() => handleSelectEndpoint(key)}
                className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                  activeEndpoint === key ? "bg-blue-600 text-canvas-stone" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {ENDPOINT_CONFIGS[key].label}
              </button>
            ))}
          </div>

          <button
            onClick={handleCopy}
            aria-label="Copy curl command"
            className="flex items-center gap-1 px-2.5 py-1 bg-terminal-elevated hover:bg-slate-700 text-slate-300 rounded border border-terminal-border transition-colors"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-slate-400" />}
            <span className="text-[11px]">{copied ? "Copied" : "Copy curl"}</span>
          </button>
        </div>
      </div>

      <div className="mt-3 relative">
        <pre className="p-3 bg-canvas-dark rounded-lg border border-terminal-elevated text-slate-300 overflow-x-auto text-[11px] leading-relaxed">
          <code>{curlSnippet}</code>
        </pre>

        <button
          onClick={handleRun}
          disabled={isRunning}
          aria-label="Execute test request"
          className="mt-2.5 flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-canvas-stone rounded font-bold text-[11px] transition-all shadow-sm cursor-pointer disabled:opacity-50"
        >
          {isRunning ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>Executing...</span>
            </>
          ) : (
            <>
              <Play className="w-3.5 h-3.5" />
              <span>{API_BASE ? "Execute Live Request" : "Preview Static Example Response"}</span>
            </>
          )}
        </button>
      </div>

      {responseOutput && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-3 pt-3 border-t border-terminal-elevated"
        >
          <div className="flex items-center justify-between pb-1.5 text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
            <span>Terminal Response Payload</span>
            <span className={isLiveResponse ? "text-emerald-400" : "text-amber-300"}>
              {isLiveResponse ? "Live ASGI Verified" : "Static Example Response (Run Local Backend to Execute Live)"}
            </span>
          </div>
          <pre className="p-3 bg-canvas-dark rounded-lg border border-emerald-950 text-emerald-300/90 overflow-x-auto text-[10px] leading-relaxed max-h-60">
            <code>{responseOutput}</code>
          </pre>
        </motion.div>
      )}
    </div>
  );
};
