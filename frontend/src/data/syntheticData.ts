/**
 * Calibrated Baseline Demonstration Dataset
 * Conforming strictly to LMIS Master R&D and AI Handoff Specifications.
 *
 * DATA PROVENANCE & METHODOLOGY NOTICE:
 * All figures, records, time series, and alerts below represent calibrated baseline data
 * for the Maharashtra pilot corridor (Pune & Nashik). They are provided for analytical
 * demonstration and planning workflow validation. They do not constitute official published
 * government census counts or live administrative portal feeds.
 */

import type {
  OccupationSummary,
  MonthlyTrendData,
  EarlyWarningSignal,
  DataSourceProvenance,
  IngestionSchemaField,
  IngestionBatchRecord,
} from '../types/lmis';
import { calculateAbsoluteGap, calculateGapRate, determineRiskLevel } from '../utils/calculations';

// Detailed occupation records for Maharashtra pilot (Pune & Nashik)
export const SYNTHETIC_OCCUPATIONS: OccupationSummary[] = [
  {
    id: 'occ-solar-pune',
    ncoCode: '7421.0301',
    ncoDivision: '7 - Craft and Related Trades Workers (Electrical & Electronics)',
    canonicalTitle: 'Solar PV Installation & Maintenance Technician',
    sector: 'Clean Tech & Renewable Energy',
    district: 'Pune',
    nsqfLevel: 4,
    documentedDemand: 680,
    qualifiedSupply: 420,
    trainingCapacity: 450,
    enrolledStudents: 410,
    lastYearCompletions: 360,
    certifiedWorkers: 345,
    reportedPlacementRate: 72.5,
    absoluteGap: calculateAbsoluteGap(680, 420),
    gapRate: calculateGapRate(680, 420),
    riskLevel: determineRiskLevel(680, 420),
    sourceStatus: 'SYNTHETIC DEMO',
    lastUpdated: '2026-10-15',
    mappingConfidence: 96,
    aliases: [
      'Solar Rooftop Technician',
      'Solar PV Installer',
      'Solar Panel Maintenance Executive',
      'Solar Electrician Level 4',
    ],
    taskDescription:
      'Installs, configures, tests, and maintains distributed rooftop and ground-mounted solar photovoltaic electrical systems, inverters, and battery banks in accordance with safety standards.',
    caveat:
      'Commercial rooftop installations in Chakan & Bhosari industrial parks driving high hiring velocity. Training capacity lags demand due to limited accredited laboratory setups.',
    monthlyHistory: [
      { period: 'Nov 2025', demand: 510, supply: 380 },
      { period: 'Dec 2025', demand: 530, supply: 385 },
      { period: 'Jan 2026', demand: 550, supply: 390 },
      { period: 'Feb 2026', demand: 580, supply: 395 },
      { period: 'Mar 2026', demand: 610, supply: 400 },
      { period: 'Apr 2026', demand: 590, supply: 405 },
      { period: 'May 2026', demand: 620, supply: 410 },
      { period: 'Jun 2026', demand: 635, supply: 412 },
      { period: 'Jul 2026', demand: 645, supply: 415 },
      { period: 'Aug 2026', demand: 660, supply: 418 },
      { period: 'Sep 2026', demand: 670, supply: 419 },
      { period: 'Oct 2026', demand: 680, supply: 420 },
    ],
  },
  {
    id: 'occ-solar-nashik',
    ncoCode: '7421.0301',
    ncoDivision: '7 - Craft and Related Trades Workers (Electrical & Electronics)',
    canonicalTitle: 'Solar PV Installation & Maintenance Technician',
    sector: 'Clean Tech & Renewable Energy',
    district: 'Nashik',
    nsqfLevel: 4,
    documentedDemand: 290,
    qualifiedSupply: 275,
    trainingCapacity: 300,
    enrolledStudents: 280,
    lastYearCompletions: 245,
    certifiedWorkers: 238,
    reportedPlacementRate: 68.0,
    absoluteGap: calculateAbsoluteGap(290, 275),
    gapRate: calculateGapRate(290, 275),
    riskLevel: determineRiskLevel(290, 275),
    sourceStatus: 'SYNTHETIC DEMO',
    lastUpdated: '2026-10-15',
    mappingConfidence: 94,
    aliases: [
      'Agri-Solar Pump Technician',
      'Solar PV System Installer',
      'Solar Technician Rural Electrification',
    ],
    taskDescription:
      'Performs field installations of decentralized solar water pumping systems and farm microgrids across agricultural clusters.',
    caveat:
      'Demand and local trained capacity closely aligned; seasonal farm pump solar installations create periodic demand spikes during post-monsoon quarters.',
    monthlyHistory: [
      { period: 'Nov 2025', demand: 240, supply: 250 },
      { period: 'Dec 2025', demand: 250, supply: 255 },
      { period: 'Jan 2026', demand: 260, supply: 260 },
      { period: 'Feb 2026', demand: 265, supply: 262 },
      { period: 'Mar 2026', demand: 270, supply: 265 },
      { period: 'Apr 2026', demand: 275, supply: 268 },
      { period: 'May 2026', demand: 280, supply: 270 },
      { period: 'Jun 2026', demand: 282, supply: 271 },
      { period: 'Jul 2026', demand: 285, supply: 272 },
      { period: 'Aug 2026', demand: 288, supply: 273 },
      { period: 'Sep 2026', demand: 289, supply: 274 },
      { period: 'Oct 2026', demand: 290, supply: 275 },
    ],
  },
  {
    id: 'occ-mach-pune',
    ncoCode: '7233.0100',
    ncoDivision: '7 - Craft and Related Trades Workers (Metal & Machinery)',
    canonicalTitle: 'Industrial Machinery Maintenance Mechanic',
    sector: 'Advanced Manufacturing',
    district: 'Pune',
    nsqfLevel: 5,
    documentedDemand: 1240,
    qualifiedSupply: 910,
    trainingCapacity: 950,
    enrolledStudents: 905,
    lastYearCompletions: 780,
    certifiedWorkers: 750,
    reportedPlacementRate: 81.2,
    absoluteGap: calculateAbsoluteGap(1240, 910),
    gapRate: calculateGapRate(1240, 910),
    riskLevel: determineRiskLevel(1240, 910),
    sourceStatus: 'SYNTHETIC DEMO',
    lastUpdated: '2026-10-15',
    mappingConfidence: 98,
    aliases: [
      'Industrial Plant Maintenance Technician',
      'Mechanical Maintenance Executive',
      'CNC Machine Maintenance Mechanic',
      'Electro-Mechanical Service Engineer',
    ],
    taskDescription:
      'Installs, overhauls, inspects, and repairs heavy mechanical equipment, hydraulic systems, pneumatic pumps, and automated assembly line gear in manufacturing plants.',
    caveat:
      'Automotive and EV manufacturing corridors in Talegaon & Chakan demand specialized mechatronics expertise not fully provided in traditional general ITI fitter curricula.',
    monthlyHistory: [
      { period: 'Nov 2025', demand: 980, supply: 840 },
      { period: 'Dec 2025', demand: 1010, supply: 850 },
      { period: 'Jan 2026', demand: 1040, supply: 860 },
      { period: 'Feb 2026', demand: 1070, supply: 870 },
      { period: 'Mar 2026', demand: 1100, supply: 880 },
      { period: 'Apr 2026', demand: 1110, supply: 885 },
      { period: 'May 2026', demand: 1140, supply: 890 },
      { period: 'Jun 2026', demand: 1170, supply: 895 },
      { period: 'Jul 2026', demand: 1190, supply: 900 },
      { period: 'Aug 2026', demand: 1210, supply: 903 },
      { period: 'Sep 2026', demand: 1225, supply: 907 },
      { period: 'Oct 2026', demand: 1240, supply: 910 },
    ],
  },
  {
    id: 'occ-mach-nashik',
    ncoCode: '7233.0100',
    ncoDivision: '7 - Craft and Related Trades Workers (Metal & Machinery)',
    canonicalTitle: 'Industrial Machinery Maintenance Mechanic',
    sector: 'Advanced Manufacturing',
    district: 'Nashik',
    nsqfLevel: 5,
    documentedDemand: 380,
    qualifiedSupply: 310,
    trainingCapacity: 360,
    enrolledStudents: 330,
    lastYearCompletions: 290,
    certifiedWorkers: 280,
    reportedPlacementRate: 70.4,
    absoluteGap: calculateAbsoluteGap(380, 310),
    gapRate: calculateGapRate(380, 310),
    riskLevel: determineRiskLevel(380, 310),
    sourceStatus: 'SYNTHETIC DEMO',
    lastUpdated: '2026-10-15',
    mappingConfidence: 89,
    aliases: [
      'Machine Maintenance Technician',
      'Factory Plant Maintenance Craftsman',
      'Fabrication Unit Maintenance Fitter',
    ],
    taskDescription:
      'Performs preventive and breakdown maintenance on industrial presses, conveyors, packaging machinery, and electrical motors in local industrial estates.',
    caveat:
      'Moderate shortage signal; postings exhibit high variance between small fabrication units and larger engineering plants. Portal sample density is low.',
    monthlyHistory: [
      { period: 'Nov 2025', demand: 320, supply: 290 },
      { period: 'Dec 2025', demand: 330, supply: 295 },
      { period: 'Jan 2026', demand: 335, supply: 298 },
      { period: 'Feb 2026', demand: 345, supply: 300 },
      { period: 'Mar 2026', demand: 350, supply: 302 },
      { period: 'Apr 2026', demand: 355, supply: 304 },
      { period: 'May 2026', demand: 360, supply: 305 },
      { period: 'Jun 2026', demand: 365, supply: 307 },
      { period: 'Jul 2026', demand: 370, supply: 308 },
      { period: 'Aug 2026', demand: 374, supply: 309 },
      { period: 'Sep 2026', demand: 378, supply: 309 },
      { period: 'Oct 2026', demand: 380, supply: 310 },
    ],
  },
  {
    id: 'occ-comp-pune',
    ncoCode: '3511.0101',
    ncoDivision: '3 - Technicians and Associate Professionals (Information & Communications)',
    canonicalTitle: 'Computer Operations & Data Processing Specialist',
    sector: 'IT & IT-Enabled Services',
    district: 'Pune',
    nsqfLevel: 4,
    documentedDemand: 1650,
    qualifiedSupply: 1540,
    trainingCapacity: 1800,
    enrolledStudents: 1720,
    lastYearCompletions: 1510,
    certifiedWorkers: 1480,
    reportedPlacementRate: 76.5,
    absoluteGap: calculateAbsoluteGap(1650, 1540),
    gapRate: calculateGapRate(1650, 1540),
    riskLevel: determineRiskLevel(1650, 1540),
    sourceStatus: 'SYNTHETIC DEMO',
    lastUpdated: '2026-10-15',
    mappingConfidence: 97,
    aliases: [
      'Data Entry Operator Level 4',
      'Computer Systems Assistant',
      'MIS Executive',
      'Office IT Support Associate',
    ],
    taskDescription:
      'Operates computer systems, spreadsheets, cloud business interfaces, database query tools, and data curation pipelines for enterprise operations.',
    caveat:
      'High overall volume with steady absorption; shift observed toward data curation and cloud workflows away from basic manual data entry.',
    monthlyHistory: [
      { period: 'Nov 2025', demand: 1450, supply: 1410 },
      { period: 'Dec 2025', demand: 1480, supply: 1430 },
      { period: 'Jan 2026', demand: 1510, supply: 1450 },
      { period: 'Feb 2026', demand: 1530, supply: 1470 },
      { period: 'Mar 2026', demand: 1550, supply: 1490 },
      { period: 'Apr 2026', demand: 1560, supply: 1500 },
      { period: 'May 2026', demand: 1580, supply: 1510 },
      { period: 'Jun 2026', demand: 1600, supply: 1520 },
      { period: 'Jul 2026', demand: 1620, supply: 1525 },
      { period: 'Aug 2026', demand: 1630, supply: 1530 },
      { period: 'Sep 2026', demand: 1640, supply: 1535 },
      { period: 'Oct 2026', demand: 1650, supply: 1540 },
    ],
  },
  {
    id: 'occ-comp-nashik',
    ncoCode: '3511.0101',
    ncoDivision: '3 - Technicians and Associate Professionals (Information & Communications)',
    canonicalTitle: 'Computer Operations & Data Processing Specialist',
    sector: 'IT & IT-Enabled Services',
    district: 'Nashik',
    nsqfLevel: 4,
    documentedDemand: 580,
    qualifiedSupply: 790,
    trainingCapacity: 850,
    enrolledStudents: 820,
    lastYearCompletions: 740,
    certifiedWorkers: 720,
    reportedPlacementRate: 51.0,
    absoluteGap: calculateAbsoluteGap(580, 790),
    gapRate: calculateGapRate(580, 790),
    riskLevel: determineRiskLevel(580, 790),
    sourceStatus: 'SYNTHETIC DEMO',
    lastUpdated: '2026-10-15',
    mappingConfidence: 92,
    aliases: [
      'Data Entry Operator',
      'Computer Operator ITI',
      'Clerical Computer Associate',
    ],
    taskDescription:
      'Performs entry-level computer operations, word processing, document preparation, and customer record management.',
    caveat:
      'Institutional training seat output significantly exceeds verified local district demand signals. High risk of underemployment or forced outward migration.',
    monthlyHistory: [
      { period: 'Nov 2025', demand: 540, supply: 720 },
      { period: 'Dec 2025', demand: 550, supply: 730 },
      { period: 'Jan 2026', demand: 555, supply: 740 },
      { period: 'Feb 2026', demand: 560, supply: 750 },
      { period: 'Mar 2026', demand: 565, supply: 760 },
      { period: 'Apr 2026', demand: 568, supply: 770 },
      { period: 'May 2026', demand: 570, supply: 775 },
      { period: 'Jun 2026', demand: 572, supply: 780 },
      { period: 'Jul 2026', demand: 575, supply: 785 },
      { period: 'Aug 2026', demand: 577, supply: 788 },
      { period: 'Sep 2026', demand: 579, supply: 789 },
      { period: 'Oct 2026', demand: 580, supply: 790 },
    ],
  },
];

/**
 * Combined 15-Month Time Series for the Pilot
 */
export const SYNTHETIC_MONTHLY_TREND: MonthlyTrendData[] = [
  { period: 'Nov 2025', documentedDemand: 4040, qualifiedSupply: 3670, trainingCapacity: 4410, isForecast: false },
  { period: 'Dec 2025', documentedDemand: 4150, qualifiedSupply: 3715, trainingCapacity: 4410, isForecast: false },
  { period: 'Jan 2026', documentedDemand: 4250, qualifiedSupply: 3760, trainingCapacity: 4410, isForecast: false },
  { period: 'Feb 2026', documentedDemand: 4350, qualifiedSupply: 3802, trainingCapacity: 4410, isForecast: false },
  { period: 'Mar 2026', documentedDemand: 4445, qualifiedSupply: 3839, trainingCapacity: 4410, isForecast: false },
  { period: 'Apr 2026', documentedDemand: 4458, qualifiedSupply: 3871, trainingCapacity: 4410, isForecast: false },
  { period: 'May 2026', documentedDemand: 4552, qualifiedSupply: 3895, trainingCapacity: 4410, isForecast: false },
  { period: 'Jun 2026', documentedDemand: 4624, qualifiedSupply: 3915, trainingCapacity: 4410, isForecast: false },
  { period: 'Jul 2026', documentedDemand: 4685, qualifiedSupply: 3930, trainingCapacity: 4410, isForecast: false },
  { period: 'Aug 2026', documentedDemand: 4749, qualifiedSupply: 3943, trainingCapacity: 4410, isForecast: false },
  { period: 'Sep 2026', documentedDemand: 4801, qualifiedSupply: 3953, trainingCapacity: 4410, isForecast: false },
  { period: 'Oct 2026 (Current)', documentedDemand: 4820, qualifiedSupply: 3945, trainingCapacity: 4410, isForecast: false },
  // Baseline projections
  {
    period: 'Nov 2026 (P)',
    documentedDemand: 4890,
    qualifiedSupply: 3980,
    trainingCapacity: 4410,
    projectedDemandBaseline: 4890,
    projectedSupplyBaseline: 3980,
    isForecast: true,
    uncertaintyLower: 4680,
    uncertaintyUpper: 5100,
  },
  {
    period: 'Dec 2026 (P)',
    documentedDemand: 4960,
    qualifiedSupply: 4010,
    trainingCapacity: 4410,
    projectedDemandBaseline: 4960,
    projectedSupplyBaseline: 4010,
    isForecast: true,
    uncertaintyLower: 4710,
    uncertaintyUpper: 5210,
  },
  {
    period: 'Jan 2027 (P)',
    documentedDemand: 5040,
    qualifiedSupply: 4040,
    trainingCapacity: 4410,
    projectedDemandBaseline: 5040,
    projectedSupplyBaseline: 4040,
    isForecast: true,
    uncertaintyLower: 4750,
    uncertaintyUpper: 5330,
  },
];

/**
 * Early Warning Signals for Planners
 */
export const SYNTHETIC_ALERTS: EarlyWarningSignal[] = [
  {
    id: 'alt-001',
    alertType: 'SHORTAGE_RISK',
    severity: 'HIGH',
    triageStatus: 'NEW',
    occupation: 'Solar PV Installation & Maintenance Technician',
    ncoCode: '7421.0301',
    district: 'Pune',
    projectedGap: 260,
    gapRate: 38.2,
    evidenceSummary:
      'Documented hiring demand (680) exceeds estimated available qualified pool (420). 4-month sustained acceleration in solar rooftop installations across industrial zones.',
    uncertaintyNote:
      'Excludes informal unregistered rooftop work. Supply estimate assumes 72.5% local retention of previous year graduates.',
    recommendedAction:
      'Review whether additional apprenticeship quotas or employer-linked skilling batches can be sanctioned before Q1 2027.',
    sourceStatus: 'SYNTHETIC DEMO',
    detectedAt: '2026-10-12',
  },
  {
    id: 'alt-002',
    alertType: 'OVERSUPPLY_RISK',
    severity: 'MEDIUM',
    triageStatus: 'NEW',
    occupation: 'Computer Operations & Data Processing Specialist',
    ncoCode: '3511.0101',
    district: 'Nashik',
    projectedGap: -210,
    gapRate: -36.2,
    evidenceSummary:
      'Estimated qualified workforce pool (790) surpasses verified hiring demand signals (580). 850 institutional seats operating at high capacity with flat local hiring.',
    uncertaintyNote:
      'May not capture remote freelance contract workers residing in Nashik but working for Pune/Mumbai employers.',
    recommendedAction:
      'Review annual seat quotas with vocational institutes and introduce modular upgrade tracks (e.g. cloud operations, business analytics).',
    sourceStatus: 'SYNTHETIC DEMO',
    detectedAt: '2026-10-14',
  },
  {
    id: 'alt-003',
    alertType: 'EMERGING_DEMAND',
    severity: 'MEDIUM',
    triageStatus: 'NEW',
    occupation: 'Industrial Machinery Maintenance Mechanic',
    ncoCode: '7233.0100',
    district: 'Pune',
    projectedGap: 330,
    gapRate: 26.6,
    evidenceSummary:
      'Hiring signal velocity rose +21% over the past 90 days across automotive supply chains and EV manufacturing clusters in Talegaon & Chakan.',
    uncertaintyNote:
      'Job titles vary across portals; 14% of vacancy listings currently pending human verification in occupation mapping queue.',
    recommendedAction:
      'Engage district skill committee and industrial clusters to evaluate curriculum readiness for predictive maintenance tools.',
    sourceStatus: 'SYNTHETIC DEMO',
    detectedAt: '2026-10-16',
  },
  {
    id: 'alt-004',
    alertType: 'DATA_WARNING',
    severity: 'WARNING',
    triageStatus: 'NEW',
    occupation: 'Industrial Machinery Maintenance Mechanic',
    ncoCode: '7233.0100',
    district: 'Nashik',
    projectedGap: 70,
    gapRate: 18.4,
    evidenceSummary:
      'Low sample density in monthly employer postings (last 45 days). High reliance on single-portal signal feeds.',
    uncertaintyNote:
      'Statistical forecast confidence below 70% threshold. Naïve baseline applied; complex time-series model withheld.',
    recommendedAction:
      'Validate district industry employer listings before taking training seat adjustment decisions. Avoid strong policy actions.',
    sourceStatus: 'SYNTHETIC DEMO',
    detectedAt: '2026-10-17',
  },
];

/**
 * Data Sources Inventory & Lineage
 */
export const DATA_SOURCES_PROVENANCE: DataSourceProvenance[] = [
  {
    id: 'src-demand',
    dataFamily: 'Job Demand Signals',
    referenceSource: 'National Career Service (NCS) / Job Portals',
    currentStatus: 'SYNTHETIC DEMO',
    geographyScope: 'Maharashtra Pilot: Pune & Nashik',
    updateFrequency: 'Monthly simulated batch',
    lastObserved: '2026-10-15',
    recordCount: '4,820 postings (simulated)',
    limitationNotice:
      'Listings are indicators, not a complete census of total vacancies. Informal and non-digital hiring is underrepresented.',
  },
  {
    id: 'src-training',
    dataFamily: 'Training Capacity & Outcomes',
    referenceSource: 'Vocational Training & Scheme Records (PMKVY / ITI / DGET)',
    currentStatus: 'SYNTHETIC DEMO',
    geographyScope: 'Maharashtra Pilot: Pune & Nashik',
    updateFrequency: 'Annual / Quarterly intake cycles',
    lastObserved: '2026-09-30',
    recordCount: '4,710 sanctioned seats (simulated)',
    limitationNotice:
      'Training seats represent sanctioned capacity, not workers currently available. Completions and placements must be evaluated with transition rates.',
  },
  {
    id: 'src-unorganised',
    dataFamily: 'Worker Registration & Context',
    referenceSource: 'e-Shram Portal Reference Architecture',
    currentStatus: 'PLANNED',
    geographyScope: 'State / District Level',
    updateFrequency: 'Administrative periodic extract',
    lastObserved: 'Future Planned Connector',
    recordCount: 'Planned Integration',
    limitationNotice:
      'e-Shram registration confirms occupational identity, not active real-time job availability or verified credential equivalence.',
  },
  {
    id: 'src-nco',
    dataFamily: 'Occupational Reference Taxonomy',
    referenceSource: 'National Classification of Occupations (NCO-2015)',
    currentStatus: 'REAL PUBLIC DATA',
    geographyScope: 'National Standard (DGE / MoLE)',
    updateFrequency: 'Static reference standard',
    lastObserved: '2015 Classification',
    recordCount: '3 Canonical Codes mapped',
    limitationNotice:
      'Standard taxonomy; modern job titles require alias dictionaries and human-in-the-loop review for ambiguous titles.',
  },
  {
    id: 'src-plfs',
    dataFamily: 'Macro Labour Force Benchmarks',
    referenceSource: 'Periodic Labour Force Survey (PLFS) 2023–24',
    currentStatus: 'REAL PUBLIC DATA',
    geographyScope: 'State-level baseline benchmarks',
    updateFrequency: 'Annual official report',
    lastObserved: 'PLFS Annual Report 2023–24',
    recordCount: 'Published aggregate tables',
    limitationNotice:
      'Survey sample sizes provide macro context but cannot provide monthly district-level occupational hiring volumes.',
  },
];

/**
 * Standard CSV/XLSX Ingestion Schema Definition
 */
export const INGESTION_SCHEMA_FIELDS: IngestionSchemaField[] = [
  {
    fieldName: 'posting_id',
    dataType: 'String (UUID / Alphanumeric)',
    required: true,
    validationRule: 'Unique non-empty identifier',
    description: 'Unique identifier from source portal to prevent duplicate counting.',
  },
  {
    fieldName: 'raw_title',
    dataType: 'String',
    required: true,
    validationRule: 'Length 3-150 chars',
    description: 'Raw job title as posted by employer prior to normalization.',
  },
  {
    fieldName: 'district_code',
    dataType: 'String',
    required: true,
    validationRule: 'Matches ISO/Census district code (e.g. MH_PUN, MH_NSK)',
    description: 'Standard district identifier for geographic aggregation.',
  },
  {
    fieldName: 'observation_date',
    dataType: 'Date (YYYY-MM-DD)',
    required: true,
    validationRule: 'Valid calendar date <= current date',
    description: 'Date the posting or training intake was recorded.',
  },
  {
    fieldName: 'source_system',
    dataType: 'Enum',
    required: true,
    validationRule: 'One of: NCS_FEED, PORTAL_SCRAPE, SCHEME_MIS, ENTERPRISE_SURVEY',
    description: 'Ingestion channel origin for lineage tracking.',
  },
  {
    fieldName: 'vacancy_count',
    dataType: 'Integer',
    required: false,
    validationRule: 'Integer >= 1 (defaults to 1)',
    description: 'Number of openings indicated in posting.',
  },
];

/**
 * Audit Log of Ingestion Batches
 */
export const INGESTION_BATCH_HISTORY: IngestionBatchRecord[] = [
  {
    batchId: 'BATCH-2026-10-A',
    sourceName: 'Simulated NCS Maharashtra Feed',
    uploadedAt: '2026-10-15 08:30:00',
    totalRows: 4850,
    validRows: 4820,
    rejectedRows: 30,
    status: 'COMPLETED',
    errorSummary: '30 rows rejected: 18 invalid district codes, 12 missing job titles.',
  },
  {
    batchId: 'BATCH-2026-09-V',
    sourceName: 'Vocational Training Sanctioned Seats MIS',
    uploadedAt: '2026-09-30 14:15:22',
    totalRows: 4725,
    validRows: 4710,
    rejectedRows: 15,
    status: 'COMPLETED',
    errorSummary: '15 rows rejected: duplicate trade codes within identical ITI institute ID.',
  },
  {
    batchId: 'BATCH-2026-09-E',
    sourceName: 'Experimental Sector Web Crawl (Clean Tech)',
    uploadedAt: '2026-09-20 19:45:10',
    totalRows: 620,
    validRows: 510,
    rejectedRows: 110,
    status: 'WARNING',
    errorSummary: '110 rows flagged: ambiguous job titles lacking NCO alias match routed to review queue.',
  },
];

export interface FallbackConnectorMetadata {
  connector_id: string;
  connector_name: string;
  source_family: string;
  connection_status: string;
  auth_mechanism: string;
  is_live_connection: boolean;
  expected_schema: Record<string, string>;
  description: string;
  limitations_notice: string;
  verification_disclaimer: string;
}

export const FALLBACK_CONNECTORS: FallbackConnectorMetadata[] = [
  {
    connector_id: 'POSTINGS_CSV_ADAPTER',
    connector_name: 'Employer Postings Ingestion Adapter',
    source_family: 'JOB_POSTINGS',
    connection_status: 'ACTIVE_LOCAL_ADAPTER',
    auth_mechanism: 'FILE_VALIDATION_SHA256',
    is_live_connection: true,
    expected_schema: {
      posting_id: 'string (unique)',
      raw_title: 'string (3-150 chars)',
      district_code: 'string (e.g. MH_PUN, MH_NSK)',
      observation_date: 'date (YYYY-MM-DD)',
      source_system: 'enum (NCS_FEED, PORTAL_SCRAPE, etc.)',
      vacancy_count: 'integer (optional, default 1)',
    },
    description: 'Deterministic CSV adapter for validating and importing batch job postings into confirmed demand observations.',
    limitations_notice: 'Standard schema validation with SHA-256 duplicate detection. Quarantines invalid records without partial writes.',
    verification_disclaimer: 'Operational local file adapter verified with schema 1.0 specifications.',
  },
  {
    connector_id: 'TRAINING_SUPPLY_CSV_ADAPTER',
    connector_name: 'Institutional Training Supply Adapter',
    source_family: 'TRAINING_CAPACITY',
    connection_status: 'ACTIVE_LOCAL_ADAPTER',
    auth_mechanism: 'FILE_VALIDATION_SHA256',
    is_live_connection: true,
    expected_schema: {
      nco_code: 'string (NCO-2015)',
      district_code: 'string (e.g. MH_PUN, MH_NSK)',
      reporting_period: 'string (YYYY-MM)',
      sanctioned_seats: 'integer',
      enrolled_students: 'integer',
      completed_students: 'integer',
      placed_students: 'integer',
      source_system: 'string',
    },
    description: 'Standardized CSV adapter for ingesting institutional training outcomes, sanctioned seats, completions, and tracked placements.',
    limitations_notice: 'Enforces logical constraints: completed <= enrolled, placed <= completed. Differentiates capacity from active supply.',
    verification_disclaimer: 'Operational local file adapter for vocational and ITI administrative reporting.',
  },
  {
    connector_id: 'NCS_API_CONNECTOR',
    connector_name: 'National Career Service (NCS) REST API Connector',
    source_family: 'JOB_POSTINGS',
    connection_status: 'PLANNED_GOVERNMENT_INTEGRATION',
    auth_mechanism: 'OAUTH2_PLANNED',
    is_live_connection: false,
    expected_schema: {
      job_id: 'string',
      job_title: 'string',
      nco_code: 'string',
      district_id: 'string',
      vacancies: 'integer',
      posted_date: 'date',
      employer_type: 'string',
    },
    description: 'Direct REST API integration specification with the National Career Service portal for employer vacancy streaming.',
    limitations_notice: 'Requires signed Data Sharing Agreement with Directorate General of Employment (DGE) and production API gateway credentials.',
    verification_disclaimer: 'Data Governance Standard: Live government connectivity is strictly claimed only after authorized credential provisioning and network handshake verification.',
  },
  {
    connector_id: 'ESHRAM_API_CONNECTOR',
    connector_name: 'e-Shram Portal Analytics Gateway',
    source_family: 'WORKER_REGISTRATIONS',
    connection_status: 'PLANNED_GOVERNMENT_INTEGRATION',
    auth_mechanism: 'MUTUAL_TLS_PLANNED',
    is_live_connection: false,
    expected_schema: {
      uan_token_hash: 'string (pseudonymized)',
      primary_occupation_nco: 'string',
      current_district: 'string',
      registration_date: 'date',
      education_level: 'string',
    },
    description: 'Planned direct integration specification with e-Shram database for tracking informal and self-employed workforce volumes.',
    limitations_notice: 'In accordance with Master R&D Section 4: e-Shram registrations represent self-declared citizen profiles, NOT verified qualified available job seekers.',
    verification_disclaimer: 'Requires security clearance and Ministry of Labour & Employment authorization. Operates in specification mode.',
  },
  {
    connector_id: 'NCVET_SIP_CONNECTOR',
    connector_name: 'Skill India Digital Hub (SIDH) / NCVET Gateway',
    source_family: 'TRAINING_CAPACITY',
    connection_status: 'PLANNED_GOVERNMENT_INTEGRATION',
    auth_mechanism: 'API_KEY_ENV',
    is_live_connection: false,
    expected_schema: {
      batch_id: 'string',
      iti_code: 'string',
      nsqf_level: 'integer',
      enrolled_count: 'integer',
      certified_count: 'integer',
      assessment_date: 'date',
    },
    description: 'Intake and assessment synchronizer interface with Skill India Digital Hub for tracking certified vocational graduates.',
    limitations_notice: 'Requires API integration authorization from NSDC / MSDE digital infrastructure team.',
    verification_disclaimer: 'System supports local institutional CSV import via TrainingSupplyCsvAdapter. Live API in planned status.',
  },
];

