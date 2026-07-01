import React, { useState } from "react";
import { api, ApiError } from "../lib/api";
import Card from "./Card";
import { Upload, FileSpreadsheet } from "lucide-react";

interface BulkImportCardProps {
  portfolioId: string;
  onImportSuccess: () => Promise<void>;
}

export const BulkImportCard: React.FC<BulkImportCardProps> = ({ portfolioId, onImportSuccess }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
      setUploadError(null);
      setUploadSuccess(null);
    }
  };

  const handleImportPortfolio = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!portfolioId || !selectedFile) return;

    setUploadError(null);
    setUploadSuccess(null);
    setUploadLoading(true);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const result = await api.post(`/portfolios/${portfolioId}/import`, formData);

      setUploadSuccess(result.message || `Successfully imported holdings.`);
      setSelectedFile(null);

      const fileInput = document.getElementById("portfolio-file-input") as HTMLInputElement;
      if (fileInput) fileInput.value = "";

      await onImportSuccess();
    } catch (err) {
      setUploadError(
        err instanceof ApiError
          ? err.message
          : "Failed to import portfolio holdings.",
      );
    } finally {
      setUploadLoading(false);
    }
  };

  return (
    <Card title="Bulk Import Holdings">
      <form onSubmit={handleImportPortfolio}>
        {uploadError && (
          <div className="upload-alert-message error">
            {uploadError}
          </div>
        )}
        {uploadSuccess && (
          <div className="upload-alert-message success">
            {uploadSuccess}
          </div>
        )}

        <div
          className="file-drop-zone"
          onDragOver={(e) => {
            e.preventDefault();
            e.currentTarget.style.borderColor = "var(--primary-color)";
          }}
          onDragLeave={(e) => {
            e.preventDefault();
            e.currentTarget.style.borderColor = "var(--surface-border)";
          }}
          onDrop={(e) => {
            e.preventDefault();
            e.currentTarget.style.borderColor = "var(--surface-border)";
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
              setSelectedFile(e.dataTransfer.files[0]);
              setUploadError(null);
              setUploadSuccess(null);
            }
          }}
          onClick={() => document.getElementById("portfolio-file-input")?.click()}
        >
          <input
            id="portfolio-file-input"
            type="file"
            accept=".csv,.xlsx"
            onChange={handleFileChange}
            style={{ display: "none" }}
          />
          <Upload
            size={32}
            color="var(--primary-color)"
            className="upload-icon"
          />
          {selectedFile ? (
            <div>
              <div className="file-name-meta">
                {selectedFile.name}
              </div>
              <div className="file-size-meta">
                {(selectedFile.size / 1024).toFixed(1)} KB
              </div>
            </div>
          ) : (
            <div>
              <p className="dropzone-prompt">
                Drag & drop your file here, or click to browse
              </p>
              <p className="dropzone-subprompt">
                Supports CSV or Excel (.xlsx) files
              </p>
            </div>
          )}
        </div>

        <div className="import-instructions">
          <div className="instructions-title">
            <FileSpreadsheet size={13} color="var(--secondary-color)" />
            Required Columns (Headers)
          </div>
          • Ticker/Symbol (e.g. RELIANCE, TCS)
          <br />
          • Quantity/Shares (e.g. 50)
          <br />• Avg Price/Cost (e.g. 2400)
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          disabled={uploadLoading || !selectedFile}
          style={{ width: "100%", gap: "6px" }}
        >
          <Upload size={16} />
          {uploadLoading ? "Uploading & Processing..." : "Upload & Import"}
        </button>
      </form>
    </Card>
  );
};
export default BulkImportCard;
