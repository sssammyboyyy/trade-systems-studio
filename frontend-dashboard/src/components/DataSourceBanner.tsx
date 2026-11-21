"use client";

import React from "react";
import { AlertTriangle, Database, Info, X } from "lucide-react";
import { useDataSource } from "@/lib/dataSource";
import { SNAPSHOT_AS_OF } from "@/data/mockData";

interface DataSourceBannerProps {
  uploadError?: string | null;
  onDismissUploadError?: () => void;
}

/**
 * Says plainly where the numbers on screen came from. A backend failure is never hidden
 * behind a fallback: it is shown here in red.
 */
export const DataSourceBanner: React.FC<DataSourceBannerProps> = ({ uploadError, onDismissUploadError }) => {
  const { source, error } = useDataSource();

  if (uploadError) {
    return (
      <div role="alert" className="mb-3 flex items-start gap-2.5 rounded-lg border border-status-crimson/40 bg-status-crimson/10 px-3 py-2 text-body-dense text-ink-primary">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-ink-crimson" aria-hidden />
        <div className="flex-1">
          <span className="font-medium">Upload not audited.</span> {uploadError}
        </div>
        {onDismissUploadError && (
          <button onClick={onDismissUploadError} aria-label="Dismiss" className="text-ink-muted hover:text-ink-primary">
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    );
  }

  if (error) {
    return (
      <div role="alert" className="mb-3 flex items-start gap-2.5 rounded-lg border border-status-crimson/40 bg-status-crimson/10 px-3 py-2 text-body-dense text-ink-primary">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-ink-crimson" aria-hidden />
        <div>
          <span className="font-medium">{error}.</span>{" "}
          {source === "snapshot"
            ? `Showing the build-time results (as of ${SNAPSHOT_AS_OF}) instead of a live audit.`
            : source === "client"
              ? "The document was scanned in the browser only: keyword checks, no amounts, never released."
              : "Nothing was substituted."}
        </div>
      </div>
    );
  }

  if (source === "live") return null;

  return (
    <div className="mb-3 flex items-start gap-2.5 rounded-lg border border-terminal-subtle bg-terminal-slate px-3 py-2 text-body-dense text-ink-secondary">
      {source === "client" ? (
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-ink-amber" aria-hidden />
      ) : (
        <Database className="mt-0.5 h-4 w-4 shrink-0 text-ink-cobalt" aria-hidden />
      )}
      <div>
        {source === "client" ? (
          <>
            <span className="font-medium text-ink-primary">Browser scan.</span> No backend is connected, so this upload
            was checked for keywords only. No amounts are computed and the document stays quarantined.
          </>
        ) : (
          <>
            <span className="font-medium text-ink-primary">Static demo.</span> These results were computed by the
            Python backend on the bundled sample documents (as of {SNAPSHOT_AS_OF}) and shipped with the page. Run the
            backend locally for live audits and uploads.
          </>
        )}
      </div>
    </div>
  );
};
