import React, { useState, useEffect } from 'react';
import {
  Download,
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  FileText,
  Clock,
  Layers,
  FileCheck,
  RefreshCw,
  Upload,
  Link2,
  Shield,
} from 'lucide-react';
import {
  DATA_SOURCES_PROVENANCE,
  INGESTION_SCHEMA_FIELDS,
  INGESTION_BATCH_HISTORY,
  SYNTHETIC_OCCUPATIONS,
  FALLBACK_CONNECTORS,
} from '../../data/syntheticData';
import type { DataStatusLabel } from '../../types/lmis';
import { apiClient } from '../../services/apiClient';
import type {
  BackendValidationResult,
  BackendImportResult,
  BackendConnectorMetadata,
} from '../../services/apiClient';

interface SampleValidationRow {
  rowNum: number;
  postingId: string;
  rawTitle: string;
  districtCode: string;
  date: string;
  status: 'VALID' | 'REJECTED';
  rejectionReason?: string;
}

const SAMPLE_CSV_ROWS: SampleValidationRow[] = [
  {
    rowNum: 1,
    postingId: 'PST-2026-9041',
    rawTitle: 'Solar PV Rooftop Electrician',
    districtCode: 'MH_PUN',
    date: '2026-10-10',
    status: 'VALID',
  },
  {
    rowNum: 2,
    postingId: 'PST-2026-9042',
    rawTitle: 'CNC Turning Machine Operator',
    districtCode: 'MH_NSK',
    date: '2026-10-11',
    status: 'VALID',
  },
  {
    rowNum: 3,
    postingId: 'PST-2026-9043',
    rawTitle: '',
    districtCode: 'MH_PUN',
    date: '2026-10-11',
    status: 'REJECTED',
    rejectionReason: 'Mandatory field `raw_title` is empty or null.',
  },
  {
    rowNum: 4,
    postingId: 'PST-2026-9044',
    rawTitle: 'Data Entry Associate',
    districtCode: 'XX_UNKNOWN',
    date: '2026-10-12',
    status: 'REJECTED',
    rejectionReason: 'Invalid district code `XX_UNKNOWN` not found in census standard.',
  },
  {
    rowNum: 5,
    postingId: 'PST-2026-9045',
    rawTitle: 'Assembly Line Fitter Trainee',
    districtCode: 'MH_PUN',
    date: '2027-05-01',
    status: 'REJECTED',
    rejectionReason: 'Observation date `2027-05-01` is in the future.',
  },
];

export const DataReportsView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'provenance' | 'validator' | 'connectors' | 'exports'>('provenance');
  const [downloadNotice, setDownloadNotice] = useState<string | null>(null);
  const [connectors, setConnectors] = useState<BackendConnectorMetadata[]>([]);

interface IngestionBatchItem {
  batch_id?: string;
  batchId?: string;
  source_system?: string;
  sourceName?: string;
  created_at?: string;
  uploadedAt?: string;
  total_rows?: number;
  totalRows?: number;
  accepted_rows?: number;
  validRows?: number;
  rejected_rows?: number;
  rejectedRows?: number;
  status?: string;
  error_summary?: string;
  errorSummary?: string;
  [key: string]: unknown;
}

  // Live file upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isValidating, setIsValidating] = useState<boolean>(false);
  const [isImporting, setIsImporting] = useState<boolean>(false);
  const [validationResult, setValidationResult] = useState<BackendValidationResult | null>(null);
  const [importResult, setImportResult] = useState<BackendImportResult | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [liveBatches, setLiveBatches] = useState<IngestionBatchItem[]>([]);
  const [showBriefModal, setShowBriefModal] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;
    apiClient.getImportBatches()
      .then((batches) => {
        if (isMounted && batches && batches.length > 0) {
          setLiveBatches(batches as unknown as IngestionBatchItem[]);
        }
      })
      .catch(() => {
        // Keep static fallback
      });
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;
    apiClient
      .getConnectors()
      .then((conns) => {
        if (isMounted && conns && conns.length > 0) {
          setConnectors(conns);
        }
      })
      .catch(() => {
        // Keep empty
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const fetchBatches = async () => {
    try {
      const batches = await apiClient.getImportBatches();
      if (batches && batches.length > 0) {
        setLiveBatches(batches as unknown as IngestionBatchItem[]);
      }
    } catch {
      // Keep static history
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setValidationResult(null);
      setImportResult(null);
      setUploadError(null);
    }
  };

  const handleValidateUploadedFile = async () => {
    if (!selectedFile) return;
    setIsValidating(true);
    setUploadError(null);
    try {
      const res = await apiClient.validateCsv(selectedFile);
      setValidationResult(res);
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : 'Validation request failed');
    } finally {
      setIsValidating(false);
    }
  };

  const handleImportUploadedFile = async () => {
    if (!selectedFile) return;
    setIsImporting(true);
    setUploadError(null);
    try {
      const res = await apiClient.importCsv(selectedFile, 'NCS_FEED');
      let proposalsCount = 0;
      let proposalMsg = '';
      try {
        const normRes = await apiClient.processBatch(res.batch_id);
        proposalsCount = normRes.proposals_created;
        proposalMsg = ` Automatically routed ${normRes.proposals_created} job postings to the Occupation Human Review Queue.`;
      } catch (normErr: unknown) {
        console.warn('Batch normalization notice:', normErr);
      }

      setImportResult({
        ...res,
        proposals_created: proposalsCount,
        message: `${res.message}${proposalMsg}`,
      });
      fetchBatches();
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : 'Import request failed');
    } finally {
      setIsImporting(false);
    }
  };

  const renderStatusBadge = (status: DataStatusLabel) => {
    switch (status) {
      case 'SYNTHETIC DEMO':
        return <span className="data-status-tag" style={{ fontSize: '9.5px', padding: '2px 5px' }}>SYNTHETIC BASELINE</span>;
      case 'REAL PUBLIC DATA':
        return <span className="ledger-badge balanced" style={{ fontSize: '9.5px' }}>PUBLIC BENCHMARK</span>;
      case 'PLANNED':
        return <span className="ledger-badge neutral" style={{ fontSize: '9.5px' }}>PLANNED CONNECTOR</span>;
      case 'IMPORTED':
        return <span className="ledger-badge balanced" style={{ fontSize: '9.5px' }}>VERIFIED IMPORT</span>;
    }
  };

  const handleDownloadCsv = async () => {
    try {
      const liveGaps = await apiClient.getGaps();
      if (liveGaps && liveGaps.length > 0) {
        const hasImported = liveGaps.some((g) => g.data_status === 'IMPORTED');
        const headers = [
          '# KARYADRISHTI PLATFORM - MAHARASHTRA LABOUR MARKET GAP REPORT',
          `# DATA STATUS: ${hasImported ? 'HYBRID (CONTAINS VERIFIED IMPORTED DEMAND OBSERVATIONS)' : 'CALIBRATED SYNTHETIC BASELINE DATA'}`,
          '# GENERATION TIMESTAMP: ' + new Date().toISOString(),
          '# DOMAIN GUARDRAILS: Confirmed demand reflects approved employer postings. Unapproved postings excluded.',
          '# PROVENANCE NOTE: Real public systems remain planned connectors.',
          'nco_code,canonical_title,district_code,reporting_period,demand_value,qualified_supply,absolute_gap,gap_rate_pct,data_status,evidence_status',
        ];

        const rows = liveGaps.map((g) =>
          [
            g.nco_code,
            `"${g.canonical_title || 'Unmapped'}"`,
            g.district_code,
            g.reporting_period,
            g.demand_value,
            g.qualified_supply_value,
            g.absolute_gap,
            g.gap_rate_pct ?? 'N/A',
            g.data_status,
            g.evidence_status,
          ].join(',')
        );

        const csvContent = 'data:text/csv;charset=utf-8,' + encodeURIComponent([...headers, ...rows].join('\n'));
        const link = document.createElement('a');
        link.setAttribute('href', csvContent);
        link.setAttribute('download', `KaryaDrishti_Live_Gap_Dataset_${new Date().toISOString().slice(0, 10)}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        setDownloadNotice(`Exported ${liveGaps.length} live records (${hasImported ? 'including verified imported demand' : 'calibrated baseline'}).`);
        setTimeout(() => setDownloadNotice(null), 5000);
        return;
      }
    } catch {
      // Fallback to baseline synthetic dataset
    }

    const headers = [
      '# KARYADRISHTI PLATFORM - MAHARASHTRA PILOT DATASET',
      '# DATA STATUS: CALIBRATED SYNTHETIC BASELINE DATA',
      '# GENERATION TIMESTAMP: ' + new Date().toISOString(),
      '# NOTICE: Calibrated baseline dataset. Real public systems remain planned connectors.',
      'id,nco_code,canonical_title,sector,district,documented_demand,qualified_supply,training_capacity,absolute_gap,gap_rate_pct,risk_level',
    ];

    const rows = SYNTHETIC_OCCUPATIONS.map((o) =>
      [
        o.id,
        o.ncoCode,
        `"${o.canonicalTitle}"`,
        `"${o.sector}"`,
        o.district,
        o.documentedDemand,
        o.qualifiedSupply,
        o.trainingCapacity,
        o.absoluteGap,
        o.gapRate ?? 'N/A',
        o.riskLevel,
      ].join(',')
    );

    const csvContent = 'data:text/csv;charset=utf-8,' + encodeURIComponent([...headers, ...rows].join('\n'));
    const link = document.createElement('a');
    link.setAttribute('href', csvContent);
    link.setAttribute('download', 'KaryaDrishti_Maharashtra_Pilot_Synthetic_Dataset.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setDownloadNotice('Downloaded KaryaDrishti_Maharashtra_Pilot_Synthetic_Dataset.csv with mandatory synthetic disclaimers.');
    setTimeout(() => setDownloadNotice(null), 5000);
  };

  const handleDownloadAuditJson = async () => {
    try {
      const logs = await apiClient.getAuditLogs();
      const content = 'data:application/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(logs, null, 2));
      const link = document.createElement('a');
      link.setAttribute('href', content);
      link.setAttribute('download', `KaryaDrishti_Cryptographic_Audit_Trail_${new Date().toISOString().slice(0, 10)}.json`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setDownloadNotice(`Exported ${logs.length} live audit log event(s) to JSON.`);
      setTimeout(() => setDownloadNotice(null), 5000);
    } catch {
      setDownloadNotice('Failed to export audit trail from backend.');
      setTimeout(() => setDownloadNotice(null), 5000);
    }
  };

  return (
    <div className="editorial-viewport" role="main" aria-label="Data Provenance and Ingestion Studio">
      {/* Header Card */}
      <div className="editorial-card">
        <div className="editorial-heading-group" style={{ marginBottom: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h2>Data Lineage, Ingestion Sandbox &amp; Evidence Exports</h2>
            <span className="data-status-tag" style={{ fontSize: '10px' }}>AUDIT VERIFIABLE</span>
          </div>
          <div className="heading-accent-bar"></div>
          <p>
            Maintains institutional transparency across all data sources, ingestion runs, validation rules, and planning briefs.
            Every metric displays its origin, collection method, temporal alignment, and policy caveats.
          </p>
        </div>

        {/* Tab Switcher */}
        <div style={{ display: 'flex', gap: '8px', marginTop: '16px', borderBottom: '1px solid #e7e5e4', paddingBottom: '8px' }}>
          <button
            type="button"
            className={`gov-btn ${activeTab === 'provenance' ? 'gov-btn-primary' : 'gov-btn-outline'}`}
            onClick={() => setActiveTab('provenance')}
          >
            <span>Source Lineage Registry</span>
          </button>
          <button
            type="button"
            className={`gov-btn ${activeTab === 'validator' ? 'gov-btn-primary' : 'gov-btn-outline'}`}
            onClick={() => setActiveTab('validator')}
          >
            <UploadCloud size={13} />
            <span>CSV Ingestion &amp; Validator</span>
          </button>
          <button
            type="button"
            className={`gov-btn ${activeTab === 'connectors' ? 'gov-btn-primary' : 'gov-btn-outline'}`}
            onClick={() => setActiveTab('connectors')}
          >
            <Link2 size={13} />
            <span>Connectors &amp; Adapters</span>
          </button>
          <button
            type="button"
            className={`gov-btn ${activeTab === 'exports' ? 'gov-btn-primary' : 'gov-btn-outline'}`}
            onClick={() => setActiveTab('exports')}
          >
            <Download size={13} />
            <span>Evidence Exports</span>
          </button>
        </div>
      </div>

      {downloadNotice && (
        <div style={{ background: '#ecfdf5', border: '1px solid #a7f3d0', color: '#065f46', padding: '10px 14px', borderRadius: '4px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <CheckCircle2 size={16} />
          <span>{downloadNotice}</span>
        </div>
      )}

      {/* Tab 1: Source Lineage Registry */}
      {activeTab === 'provenance' && (
        <section className="editorial-card" aria-label="Source Lineage Registry">
          <div className="editorial-card-header">
            <div className="editorial-heading-group" style={{ marginBottom: 0 }}>
              <h3>Primary Data Sources &amp; Operational Integration Registry</h3>
              <div className="heading-accent-bar" style={{ width: '28px', marginTop: '4px' }}></div>
              <p style={{ fontSize: '12px', marginTop: '4px' }}>
                Inventory of national and state labour market feeds, institutional completion sources, and synthetic demonstration datasets.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {DATA_SOURCES_PROVENANCE.map((src) => (
              <div key={src.id} style={{ border: '1px solid #e7e5e4', borderRadius: '4px', padding: '10px 12px', background: '#ffffff' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '3px' }}>
                  <span style={{ fontSize: '13px', fontWeight: 700, color: '#1c1917' }}>{src.dataFamily}</span>
                  {renderStatusBadge(src.currentStatus)}
                </div>
                <div style={{ fontSize: '11.5px', color: '#57534e', marginBottom: '4px' }}>
                  <span><strong>Reference:</strong> {src.referenceSource}</span> · 
                  <span> <strong>Scope:</strong> {src.geographyScope}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '10.5px', color: '#78716c', marginBottom: '4px' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                    <Clock size={11} /> Refresh: {src.updateFrequency}
                  </span>
                  <span><strong>Volume:</strong> {src.recordCount}</span>
                </div>
                <div style={{ fontSize: '10.5px', color: '#9a3412', background: '#fff7ed', padding: '4px 6px', borderRadius: '3px', border: '1px solid #fed7aa' }}>
                  <strong>Guardrail:</strong> {src.limitationNotice}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Tab 2: Interactive CSV Ingestion Schema Sandbox & Real Upload */}
      {activeTab === 'validator' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {/* Live CSV Upload & FastAPI Validation Card */}
          <section className="editorial-card" aria-label="FastAPI Ingestion Pipeline">
            <div className="editorial-card-header">
              <div className="editorial-heading-group" style={{ marginBottom: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <h3>FastAPI Live CSV Validation &amp; Ingestion Pipeline</h3>
                  <span className="ledger-badge balanced" style={{ fontSize: '10px' }}>FASTAPI BACKEND</span>
                </div>
                <div className="heading-accent-bar" style={{ width: '28px', marginTop: '4px' }}></div>
                <p style={{ fontSize: '12px', marginTop: '4px' }}>
                  Upload a vacancy posting CSV file to execute rigorous schema validation, district verification, and database ingestion.
                </p>
              </div>
            </div>

            <div
              style={{
                border: '2px dashed #d6d3d1',
                borderRadius: '6px',
                padding: '20px',
                textAlign: 'center',
                background: '#fafaf9',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '12px',
              }}
            >
              <UploadCloud size={32} style={{ color: '#0f766e' }} />
              <div>
                <input
                  type="file"
                  id="csv-file-input"
                  accept=".csv"
                  onChange={handleFileChange}
                  style={{ display: 'none' }}
                />
                <label
                  htmlFor="csv-file-input"
                  className="gov-btn gov-btn-outline"
                  style={{ cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                >
                  <Upload size={14} />
                  <span>{selectedFile ? selectedFile.name : 'Select CSV File to Validate'}</span>
                </label>
              </div>
              <div style={{ fontSize: '11px', color: '#78716c' }}>
                Required Columns: <code>posting_id, raw_title, district_code, observation_date, vacancy_count</code> (UTF-8, Max 10MB)
              </div>

              {selectedFile && (
                <div style={{ display: 'flex', gap: '10px', marginTop: '6px' }}>
                  <button
                    type="button"
                    className="gov-btn gov-btn-primary"
                    onClick={handleValidateUploadedFile}
                    disabled={isValidating}
                  >
                    <span>{isValidating ? 'Validating on FastAPI...' : 'Validate CSV Schema'}</span>
                  </button>
                  {validationResult && validationResult.is_valid && (
                    <button
                      type="button"
                      className="gov-btn"
                      style={{ background: '#0f766e', color: '#ffffff', border: 'none' }}
                      onClick={handleImportUploadedFile}
                      disabled={isImporting}
                    >
                      <span>{isImporting ? 'Ingesting...' : 'Import Verified Records to DB'}</span>
                    </button>
                  )}
                </div>
              )}
            </div>

            {uploadError && (
              <div style={{ marginTop: '12px', background: '#fef2f2', border: '1px solid #fecaca', color: '#b91c1c', padding: '10px 14px', borderRadius: '4px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertCircle size={16} />
                <span>Error: {uploadError}</span>
              </div>
            )}

            {validationResult && (
              <div style={{ marginTop: '14px', padding: '14px', background: validationResult.is_valid ? '#f0fdf4' : '#fff7ed', border: `1px solid ${validationResult.is_valid ? '#bbf7d0' : '#fed7aa'}`, borderRadius: '4px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <div style={{ fontWeight: 700, fontSize: '13px', color: validationResult.is_valid ? '#15803d' : '#c2410c' }}>
                    FastAPI Diagnostic: {validationResult.is_valid ? 'All Rows Passed Schema & District Validation' : 'Validation Failed — Schema Constraints Violated'}
                  </div>
                  <span className="ledger-badge neutral" style={{ fontSize: '10px' }}>
                    Total Rows: {validationResult.total_rows} | Valid: {validationResult.valid_rows_count} | Rejected: {validationResult.invalid_rows_count}
                  </span>
                </div>
                {validationResult.errors && validationResult.errors.length > 0 && (
                  <div style={{ fontSize: '11.5px', color: '#991b1b', marginTop: '6px' }}>
                    <strong>Validation Errors Found:</strong>
                    <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                      {validationResult.errors.slice(0, 5).map((e, idx) => (
                        <li key={idx}>Row {e.row_number}: [{e.column_name}] {e.message} (value: "{e.raw_value}")</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {importResult && (
              <div style={{ marginTop: '12px', padding: '12px 14px', background: '#ecfdf5', border: '1px solid #a7f3d0', color: '#065f46', borderRadius: '4px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircle2 size={16} />
                <span>
                  <strong>Success:</strong> Batch <code>{importResult.batch_id}</code> persisted {importResult.imported_rows} valid records. {importResult.message}
                </span>
              </div>
            )}
          </section>

          {/* Schema Rules Card */}
          <section className="editorial-card" aria-label="Schema Specification">
            <div className="editorial-card-header">
              <div className="editorial-heading-group" style={{ marginBottom: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <h3>Standard Ingestion Schema Definition (CSV / XLSX)</h3>
                  <span className="ledger-badge neutral" style={{ fontSize: '10px' }}>SCHEMA 1.0</span>
                </div>
                <div className="heading-accent-bar" style={{ width: '28px', marginTop: '4px' }}></div>
                <p style={{ fontSize: '12px', marginTop: '4px' }}>Required column names, types, and automated validation rules</p>
              </div>
            </div>

            <div className="table-wrapper-refined">
              <table className="editorial-table">
                <thead>
                  <tr>
                    <th>Field Name</th>
                    <th>Data Type</th>
                    <th>Required</th>
                    <th>Validation Rule</th>
                    <th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  {INGESTION_SCHEMA_FIELDS.map((f, i) => (
                    <tr key={i}>
                      <td style={{ fontFamily: 'monospace', fontWeight: 600, color: '#1c1917' }}>{f.fieldName}</td>
                      <td>{f.dataType}</td>
                      <td>
                        {f.required ? (
                          <span className="ledger-badge shortage" style={{ fontSize: '9.5px' }}>REQUIRED</span>
                        ) : (
                          <span className="ledger-badge neutral" style={{ fontSize: '9.5px' }}>OPTIONAL</span>
                        )}
                      </td>
                      <td style={{ fontFamily: 'monospace', fontSize: '11px', color: '#57534e' }}>{f.validationRule}</td>
                      <td style={{ fontSize: '11.5px', color: '#57534e' }}>{f.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* Diagnostic Mock Sandbox */}
          <section className="editorial-card" aria-label="Sample Ingestion Run">
            <div className="editorial-card-header">
              <div className="editorial-heading-group" style={{ marginBottom: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <h3>Sample Schema Validation Diagnostic Reference</h3>
                  <span className="data-status-tag" style={{ fontSize: '9.5px', padding: '2px 5px' }}>REFERENCE</span>
                </div>
                <div className="heading-accent-bar" style={{ width: '28px', marginTop: '4px' }}></div>
                <p style={{ fontSize: '12px', marginTop: '4px' }}>Testing 5 benchmark sample records against schema integrity constraints</p>
              </div>
            </div>

            <div className="table-wrapper-refined">
              <table className="editorial-table">
                <thead>
                  <tr>
                    <th>Row #</th>
                    <th>Posting ID</th>
                    <th>Raw Job Title</th>
                    <th>District Code</th>
                    <th>Observation Date</th>
                    <th>Status</th>
                    <th>Diagnostic Message</th>
                  </tr>
                </thead>
                <tbody>
                  {SAMPLE_CSV_ROWS.map((row) => (
                    <tr key={row.rowNum} style={{ backgroundColor: row.status === 'REJECTED' ? '#fff9f7' : undefined }}>
                      <td className="num-val">{row.rowNum}</td>
                      <td style={{ fontFamily: 'monospace' }}>{row.postingId}</td>
                      <td style={{ fontWeight: 600 }}>{row.rawTitle || <em style={{ color: '#c2410c' }}>[EMPTY]</em>}</td>
                      <td style={{ fontFamily: 'monospace' }}>{row.districtCode}</td>
                      <td>{row.date}</td>
                      <td>
                        {row.status === 'VALID' ? (
                          <span className="ledger-badge balanced" style={{ fontSize: '10px' }}>
                            <CheckCircle2 size={11} style={{ display: 'inline', marginRight: 3 }} /> VALID
                          </span>
                        ) : (
                          <span className="ledger-badge shortage" style={{ fontSize: '10px' }}>
                            <AlertCircle size={11} style={{ display: 'inline', marginRight: 3 }} /> REJECTED
                          </span>
                        )}
                      </td>
                      <td style={{ fontSize: '11px', color: row.status === 'REJECTED' ? '#c2410c' : '#15803d' }}>
                        {row.rejectionReason || 'Passed all schema and district constraints.'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#78716c' }}>
              <span>Outcome: <strong>2 of 5 rows rejected (40% error rate)</strong>. Quarantined in audit log.</span>
              <span>Guardrail: Zero invalid records enter forecast models.</span>
            </div>
          </section>

          {/* Historical Batch Ingestion Audit Log */}
          <section className="editorial-card" aria-label="Ingestion Audit Log">
            <div className="editorial-card-header">
              <div className="editorial-heading-group" style={{ marginBottom: 0 }}>
                <h3>Ingestion Audit Log History</h3>
                <div className="heading-accent-bar" style={{ width: '28px', marginTop: '4px' }}></div>
                <p style={{ fontSize: '12px', marginTop: '4px' }}>Immutable audit trail of recent ingestion jobs, row counts, and rejection summaries</p>
              </div>
              <button
                type="button"
                onClick={fetchBatches}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  background: 'transparent',
                  border: '1px solid #d6d3d1',
                  padding: '4px 8px',
                  borderRadius: '3px',
                  cursor: 'pointer',
                  fontSize: '11px',
                  color: '#57534e',
                }}
              >
                <RefreshCw size={11} />
                <span>Refresh Log</span>
              </button>
            </div>

            <div className="table-wrapper-refined">
              <table className="editorial-table">
                <thead>
                  <tr>
                    <th>Batch ID</th>
                    <th>Source Name</th>
                    <th>Uploaded Timestamp</th>
                    <th className="num-val">Total Rows</th>
                    <th className="num-val">Valid Rows</th>
                    <th className="num-val">Rejected Rows</th>
                    <th>Batch Status</th>
                    <th>Audit Summary</th>
                  </tr>
                </thead>
                <tbody>
                  {(liveBatches.length > 0 ? liveBatches : (INGESTION_BATCH_HISTORY as unknown as IngestionBatchItem[])).map((b: IngestionBatchItem, bIdx: number) => {
                    const rejectedCount = Number(b.rejected_rows ?? b.rejectedRows ?? 0);
                    return (
                      <tr key={b.batch_id || b.batchId || bIdx}>
                        <td style={{ fontFamily: 'monospace', fontWeight: 700 }}>{b.batch_id || b.batchId}</td>
                        <td style={{ fontWeight: 600 }}>{b.source_system || b.sourceName}</td>
                        <td style={{ fontSize: '11px', color: '#78716c' }}>{b.created_at || b.uploadedAt}</td>
                        <td className="num-val">{b.total_rows ?? b.totalRows}</td>
                        <td className="num-val" style={{ color: '#15803d', fontWeight: 600 }}>{b.accepted_rows ?? b.validRows}</td>
                        <td className="num-val" style={{ color: rejectedCount > 0 ? '#c2410c' : '#78716c', fontWeight: 600 }}>
                          {b.rejected_rows ?? b.rejectedRows}
                        </td>
                      <td>
                        {(b.status === 'COMPLETED' || b.status === 'SUCCESS') ? (
                          <span className="ledger-badge balanced" style={{ fontSize: '10px' }}>COMPLETED</span>
                        ) : (
                          <span className="ledger-badge shortage" style={{ fontSize: '10px' }}>
                            {b.status || 'WARNING'}
                          </span>
                        )}
                      </td>
                      <td style={{ fontSize: '11px', color: '#57534e' }}>{b.error_summary || b.errorSummary || 'Verified by schema validator.'}</td>
                    </tr>
                  );
                })}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}

      {/* Tab 3: Data Connectors & Adapters */}
      {activeTab === 'connectors' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="editorial-card" style={{ borderLeft: '4px solid #1e3a8a', padding: '16px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <Shield size={18} style={{ color: '#1e3a8a' }} />
              <h3 style={{ fontSize: '15px', fontWeight: 700, margin: 0, color: '#1e3a8a' }}>
                Data Integration Architecture &amp; Connector Readiness
              </h3>
              <span className="ledger-badge balanced" style={{ fontSize: '10px' }}>STANDARDIZED INTERFACES</span>
            </div>
            <p style={{ fontSize: '12px', color: '#475569', margin: '4px 0 0 0', lineHeight: 1.5 }}>
              Standardized, reusable adapters for local batch ingestion and contract specifications for future national portal APIs.
              In strict compliance with <strong>Public Sector Intelligence &amp; Data Integrity Standards</strong>:
              <em> Live government integrations (NCS, e-Shram, SIDH) are not claimed without active, authorized Data Sharing Agreements and verified credentials.</em>
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '14px' }}>
            {(connectors.length > 0 ? connectors : FALLBACK_CONNECTORS).map((c) => {
              const isLocal = c.connection_status === 'ACTIVE_LOCAL_ADAPTER';
              return (
                <div
                  key={c.connector_id}
                  style={{
                    border: '1px solid #e2e8f0',
                    borderRadius: '4px',
                    padding: '14px 16px',
                    background: '#ffffff',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    gap: '10px',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px', marginBottom: '6px' }}>
                      <span
                        style={{
                          fontSize: '10px',
                          fontWeight: 700,
                          padding: '2px 6px',
                          borderRadius: '3px',
                          background: isLocal ? '#dcfce7' : '#e0e7ff',
                          color: isLocal ? '#15803d' : '#3730a3',
                          border: isLocal ? '1px solid #86efac' : '1px solid #c7d2fe',
                        }}
                      >
                        {isLocal ? 'ACTIVE LOCAL ADAPTER' : 'PLANNED CONNECTOR SPEC'}
                      </span>

                      <span style={{ fontSize: '10px', fontWeight: 600, color: '#64748b' }}>
                        {c.source_family}
                      </span>
                    </div>

                    <div style={{ fontSize: '13.5px', fontWeight: 700, color: '#0f172a', marginBottom: '4px' }}>
                      {c.connector_name}
                    </div>
                    <p style={{ fontSize: '11.5px', color: '#475569', margin: '0 0 8px 0', lineHeight: 1.45 }}>
                      {c.description}
                    </p>

                    {/* Expected Schema */}
                    <div style={{ background: '#f8fafc', padding: '8px 10px', borderRadius: '4px', border: '1px solid #e2e8f0', marginBottom: '8px' }}>
                      <div style={{ fontSize: '10.5px', fontWeight: 700, color: '#334155', marginBottom: '4px' }}>
                        Payload Contract &amp; Schema:
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {Object.entries(c.expected_schema).map(([k, v]) => (
                          <span
                            key={k}
                            style={{
                              fontSize: '9.5px',
                              fontFamily: 'monospace',
                              background: '#ffffff',
                              border: '1px solid #cbd5e1',
                              padding: '1px 5px',
                              borderRadius: '2px',
                              color: '#0f172a',
                            }}
                            title={v}
                          >
                            {k}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Prerequisite & Limitations */}
                    <div style={{ fontSize: '11px', color: '#b45309', background: '#fffbeb', border: '1px solid #fef3c7', padding: '6px 8px', borderRadius: '3px' }}>
                      <strong>Integration Notice:</strong> {c.limitations_notice}
                    </div>
                  </div>

                  <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: '8px', fontSize: '10.5px', color: '#64748b', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>Auth: <code>{c.auth_mechanism}</code></span>
                    <span style={{ color: isLocal ? '#15803d' : '#475569', fontWeight: 600 }}>
                      {isLocal ? '● Operational' : '○ Standby Spec'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab 4: Export Studio */}
      {activeTab === 'exports' && (
        <section className="editorial-card" aria-label="Export Studio">
          <div className="editorial-card-header">
            <div className="editorial-heading-group" style={{ marginBottom: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3>Authenticated Planning Brief &amp; Dataset Exports</h3>
                <span className="ledger-badge neutral" style={{ fontSize: '10px' }}>EXPORT SPEC</span>
              </div>
              <div className="heading-accent-bar" style={{ width: '28px', marginTop: '4px' }}></div>
              <p style={{ fontSize: '12px', marginTop: '4px' }}>All exported files strictly enforce synthetic metadata, pilot scope, and methodological caveats.</p>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '8px' }}>
            {/* Export 1: CSV Tabular Dataset */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 18px', border: '1px solid #e7e5e4', borderRadius: '4px', background: '#ffffff' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <FileCheck size={20} style={{ color: '#0f766e' }} />
                <div>
                  <div style={{ fontWeight: 700, fontSize: '13.5px', color: '#1c1917' }}>
                    Maharashtra Pilot Tabular Analysis (CSV Export)
                  </div>
                  <div style={{ fontSize: '11.5px', color: '#78716c' }}>
                    Includes 6 monitored occupations across Pune &amp; Nashik, demand, qualified supply, training capacity, and gap metrics with synthetic headers.
                  </div>
                </div>
              </div>
              <button
                type="button"
                className="gov-btn gov-btn-primary"
                onClick={handleDownloadCsv}
              >
                <Download size={13} />
                <span>Download Live CSV</span>
              </button>
            </div>

            {/* Export 2: Policy Brief PDF Specification */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 18px', border: '1px solid #e7e5e4', borderRadius: '4px', background: '#ffffff' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <FileText size={20} style={{ color: '#1e3a8a' }} />
                <div>
                  <div style={{ fontWeight: 700, fontSize: '13.5px', color: '#1c1917' }}>
                    District Skill Committee Brief Layout (PDF Specification)
                  </div>
                  <div style={{ fontSize: '11.5px', color: '#78716c' }}>
                    Executive 4-page briefing template for District Collectors and MSDE officials featuring early warning radar and seat scenarios.
                  </div>
                </div>
              </div>
              <button
                type="button"
                className="gov-btn gov-btn-outline"
                onClick={() => setShowBriefModal(true)}
              >
                <FileText size={13} />
                <span>Preview Planning Brief</span>
              </button>
            </div>

            {/* Export 3: Audit Lineage JSON */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 18px', border: '1px solid #e7e5e4', borderRadius: '4px', background: '#ffffff' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <Layers size={20} style={{ color: '#4338ca' }} />
                <div>
                  <div style={{ fontWeight: 700, fontSize: '13.5px', color: '#1c1917' }}>
                    Ingestion &amp; Model Lineage Audit Log (JSON)
                  </div>
                  <div style={{ fontSize: '11.5px', color: '#78716c' }}>
                    Machine-readable checksums, mapping version histories, and baseline model parameters for verifiable audit inspection.
                  </div>
                </div>
              </div>
              <button
                type="button"
                className="gov-btn gov-btn-outline"
                onClick={handleDownloadAuditJson}
              >
                <Download size={13} />
                <span>Export Audit Trail (JSON)</span>
              </button>
            </div>
          </div>
        </section>
      )}

      {/* Executive Briefing Modal */}
      {showBriefModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.75)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '20px',
          }}
          role="dialog"
          aria-modal="true"
          aria-label="District Skill Committee Briefing Document"
        >
          <div
            style={{
              backgroundColor: '#ffffff',
              borderRadius: '6px',
              maxWidth: '820px',
              width: '100%',
              maxHeight: '90vh',
              overflowY: 'auto',
              boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            {/* Modal Header */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '16px 24px',
                borderBottom: '1px solid #e2e8f0',
                background: '#f8fafc',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileText size={20} style={{ color: '#1e3a8a' }} />
                <h3 style={{ fontSize: '16px', fontWeight: 700, margin: 0, color: '#0f172a' }}>
                  District Skill Committee Executive Planning Brief
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowBriefModal(false)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  fontSize: '20px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  color: '#64748b',
                }}
                aria-label="Close modal"
              >
                ✕
              </button>
            </div>

            {/* Document Content */}
            <div style={{ padding: '24px', color: '#1e293b', fontSize: '13px', lineHeight: 1.6 }}>
              {/* Official Header */}
              <div style={{ textAlign: 'center', borderBottom: '2px solid #0f172a', paddingBottom: '14px', marginBottom: '18px' }}>
                <div style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.08em', color: '#64748b', textTransform: 'uppercase' }}>
                  Labour Market Intelligence System • Maharashtra Pilot Region (Pune &amp; Nashik)
                </div>
                <h2 style={{ fontSize: '18px', fontWeight: 800, margin: '6px 0 2px', color: '#0f172a' }}>
                  Labour Market Intelligence &amp; Skill Demand-Supply Brief
                </h2>
                <div style={{ fontSize: '11px', color: '#475569' }}>
                  Reporting Horizon: Q3/Q4 2026 • Target Districts: Pune (MH_PUN) &amp; Nashik (MH_NSK)
                </div>
              </div>

              {/* Status Notice */}
              <div
                style={{
                  backgroundColor: '#fffbeb',
                  border: '1px solid #fde68a',
                  borderRadius: '4px',
                  padding: '10px 14px',
                  marginBottom: '16px',
                  fontSize: '11.5px',
                  color: '#92400e',
                }}
              >
                <strong>METHODOLOGICAL NOTICE:</strong> This brief integrates empirical employer postings reconciled against NCO-2015 standards, ITI/NCVET institutional training capacities, and Holt state-space forecast trajectories. Public national APIs (NCS, e-Shram) remain planned integrations.
              </div>

              {/* Section 1: Executive Summary */}
              <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#1e3a8a', textTransform: 'uppercase', marginBottom: '8px' }}>
                1. Labour Market Shortage Summary
              </h4>
              <p style={{ margin: '0 0 12px 0' }}>
                Based on active evidence reconciliation across 6 pilot trades in Pune and Nashik, significant workforce bottlenecks persist in green energy, precision machining, and electric mobility. In Pune, <strong>Solar PV Installation &amp; Maintenance (NCO 7421.0301)</strong> displays an observed deficit of +260 technicians (38.2% mismatch rate), with Holt 3-month forecast projections expanding to +300 vacancies.
              </p>

              {/* Section 2: Key Policy Interventions */}
              <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#1e3a8a', textTransform: 'uppercase', marginBottom: '8px' }}>
                2. Recommended Policy &amp; Training Interventions
              </h4>
              <ul style={{ paddingLeft: '20px', margin: '0 0 16px 0' }}>
                <li style={{ marginBottom: '6px' }}>
                  <strong>Pune Solar PV Capacity:</strong> Sanction +500 additional intake seats across government and private ITIs. Utilizing standard yield benchmarks (85% enrolment, 80% completion, 75% local entry = 255 net completers), this intervention mitigates 98% of the projected deficit at an estimated annual outlay of ₹90,00,000.
                </li>
                <li style={{ marginBottom: '6px' }}>
                  <strong>Nashik CNC Machine Operation:</strong> Demand velocity is expanding (+15% quarterly growth). Establish rapid dual work-study apprenticeship drives under NAPS with local automotive clusters to bridge immediate hiring bottlenecks.
                </li>
                <li style={{ marginBottom: '6px' }}>
                  <strong>Precautionary Data Audits:</strong> For occupations relying predominantly on synthetic baselines or containing unapproved job postings, defer capital expenditure pending targeted district employer surveys.
                </li>
              </ul>

              {/* Section 3: Governance & Cryptographic Chain */}
              <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#1e3a8a', textTransform: 'uppercase', marginBottom: '8px' }}>
                3. Governance &amp; Audit Trail Verification
              </h4>
              <p style={{ margin: '0 0 8px 0' }}>
                All underlying evidence, human title approvals, and algorithm parameters are recorded in a SHA-256 hash-chained append-only verifiable audit trail. Machine-readable exports can be verified at <code>/api/governance/audit-logs/verify</code>.
              </p>
            </div>

            {/* Modal Footer */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'flex-end',
                gap: '10px',
                padding: '14px 24px',
                borderTop: '1px solid #e2e8f0',
                background: '#f8fafc',
              }}
            >
              <button
                type="button"
                className="gov-btn gov-btn-outline"
                onClick={() => setShowBriefModal(false)}
              >
                Close
              </button>
              <button
                type="button"
                className="gov-btn gov-btn-primary"
                onClick={() => window.print()}
              >
                <Download size={13} />
                <span>Print / Save as PDF</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
