import React, { useState } from 'react';
import {
  Search,
  Filter,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  TrendingDown,
  ArrowUpDown,
  ChevronRight,
} from 'lucide-react';
import type { OccupationSummary, PilotDistrict, RiskLevel } from '../../types/lmis';
import {
  formatNumber,
  formatSignedNumber,
  formatGapRate,
} from '../../utils/calculations';
import { OccupationFactsheetDrawer } from '../occupations/OccupationFactsheetDrawer';

interface OccupationBreakdownTableProps {
  occupations: OccupationSummary[];
  selectedDistrict: PilotDistrict;
  selectedSector?: string;
  title?: string;
  subtitle?: string;
}

type SortField = 'canonicalTitle' | 'documentedDemand' | 'qualifiedSupply' | 'absoluteGap' | 'gapRate';

export const OccupationBreakdownTable: React.FC<OccupationBreakdownTableProps> = ({
  occupations,
  selectedDistrict,
  selectedSector = 'ALL',
  title = 'Occupation & Sector Demand-Supply Breakdown',
  subtitle = 'Standardized mapping to NCO-2015 taxonomy with separation of demand signals, qualified supply estimates, and training capacity.',
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [tableSector, setTableSector] = useState<string>(selectedSector);
  const [selectedRisk, setSelectedRisk] = useState<string>('ALL');
  const [sortField, setSortField] = useState<SortField>('absoluteGap');
  const [sortAsc, setSortAsc] = useState<boolean>(false);
  const [inspectedOccupation, setInspectedOccupation] = useState<OccupationSummary | null>(null);

  const activeSector = tableSector !== 'ALL' ? tableSector : selectedSector;

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  const filteredRows = occupations
    .filter((item) => {
      if (selectedDistrict !== 'All Districts' && item.district !== selectedDistrict) {
        return false;
      }
      if (activeSector !== 'ALL' && item.sector !== activeSector) {
        return false;
      }
      if (selectedRisk !== 'ALL' && item.riskLevel !== selectedRisk) {
        return false;
      }
      if (searchTerm.trim() !== '') {
        const q = searchTerm.toLowerCase();
        const matchTitle = item.canonicalTitle.toLowerCase().includes(q);
        const matchCode = item.ncoCode.toLowerCase().includes(q);
        const matchSector = item.sector.toLowerCase().includes(q);
        const matchAlias = item.aliases.some((a) => a.toLowerCase().includes(q));
        if (!matchTitle && !matchCode && !matchSector && !matchAlias) return false;
      }
      return true;
    })
    .sort((a, b) => {
      let comparison: number;
      if (sortField === 'canonicalTitle') {
        comparison = a.canonicalTitle.localeCompare(b.canonicalTitle);
      } else if (sortField === 'gapRate') {
        const aRate = a.gapRate ?? -9999;
        const bRate = b.gapRate ?? -9999;
        comparison = aRate - bRate;
      } else {
        comparison = a[sortField] - b[sortField];
      }
      return sortAsc ? comparison : -comparison;
    });

  const renderRiskBadge = (level: RiskLevel) => {
    switch (level) {
      case 'CRITICAL_SHORTAGE':
        return (
          <span className="ledger-badge shortage" title="Shortage gap rate > 25%">
            <AlertCircle size={11} style={{ display: 'inline', marginRight: 4 }} />
            Critical Shortage
          </span>
        );
      case 'MODERATE_SHORTAGE':
        return (
          <span className="ledger-badge shortage" style={{ backgroundColor: '#fff7ed', color: '#c2410c' }}>
            <AlertCircle size={11} style={{ display: 'inline', marginRight: 4 }} />
            Moderate Shortage
          </span>
        );
      case 'POTENTIAL_OVERSUPPLY':
        return (
          <span className="ledger-badge surplus" title="Qualified supply exceeds demand signals by >15%">
            <TrendingDown size={11} style={{ display: 'inline', marginRight: 4 }} />
            Oversupply Risk
          </span>
        );
      case 'BALANCED':
        return (
          <span className="ledger-badge balanced">
            <CheckCircle2 size={11} style={{ display: 'inline', marginRight: 4 }} />
            Balanced
          </span>
        );
      case 'INSUFFICIENT_DATA':
        return (
          <span className="ledger-badge neutral">
            <HelpCircle size={11} style={{ display: 'inline', marginRight: 4 }} />
            Sparse Data
          </span>
        );
    }
  };

  return (
    <>
      <section className="editorial-card" aria-label="Occupation and Sector Breakdown Table">
        <div className="editorial-card-header">
          <div className="editorial-heading-group" style={{ marginBottom: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h3>{title}</h3>
              <span className="data-status-tag" style={{ fontSize: '9.5px', padding: '2px 6px' }}>SYNTHETIC</span>
            </div>
            <div className="heading-accent-bar" style={{ width: '28px', marginTop: '4px' }}></div>
            <p style={{ fontSize: '12.5px', marginTop: '4px' }}>{subtitle}</p>
          </div>

          {/* Filter & Search Bar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <div className="ribbon-filter" style={{ minWidth: '220px' }}>
              <Search size={13} className="text-stone-400" aria-hidden="true" />
              <input
                type="text"
                placeholder="Search title, alias, NCO code..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{
                  border: 'none',
                  background: 'transparent',
                  outline: 'none',
                  fontSize: '12px',
                  width: '100%',
                  fontFamily: 'inherit',
                }}
                aria-label="Search occupations by title or code"
              />
            </div>

            <div className="ribbon-filter">
              <Filter size={13} className="text-stone-400" aria-hidden="true" />
              <select
                value={tableSector}
                onChange={(e) => setTableSector(e.target.value)}
                aria-label="Filter by Sector"
              >
                <option value="ALL">All Sectors</option>
                <option value="Clean Tech & Renewable Energy">Clean Tech</option>
                <option value="Advanced Manufacturing">Adv. Manufacturing</option>
                <option value="IT & IT-Enabled Services">IT-ITeS</option>
              </select>
            </div>

            <div className="ribbon-filter">
              <select
                value={selectedRisk}
                onChange={(e) => setSelectedRisk(e.target.value)}
                aria-label="Filter by Risk Classification"
              >
                <option value="ALL">All Statuses</option>
                <option value="CRITICAL_SHORTAGE">Critical Shortage</option>
                <option value="MODERATE_SHORTAGE">Moderate Shortage</option>
                <option value="POTENTIAL_OVERSUPPLY">Oversupply Risk</option>
                <option value="BALANCED">Balanced</option>
              </select>
            </div>
          </div>
        </div>

        {/* Table view */}
        <div className="table-wrapper-refined">
          <table className="editorial-table">
            <thead>
              <tr>
                <th
                  className="sortable"
                  onClick={() => handleSort('canonicalTitle')}
                  title="Sort by Canonical Title"
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span>Canonical Occupation (NCO-2015)</span>
                    <ArrowUpDown size={11} />
                  </div>
                </th>
                <th>Sector</th>
                <th>District</th>
                <th
                  className="num-val sortable"
                  onClick={() => handleSort('documentedDemand')}
                  title="Sort by Documented Demand"
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '4px' }}>
                    <span>Demand Signals</span>
                    <ArrowUpDown size={11} />
                  </div>
                </th>
                <th
                  className="num-val sortable"
                  onClick={() => handleSort('qualifiedSupply')}
                  title="Sort by Qualified Supply"
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '4px' }}>
                    <span>Qualified Supply</span>
                    <ArrowUpDown size={11} />
                  </div>
                </th>
                <th className="num-val" title="Sanctioned institutional capacity. Guardrail: NOT active supply!">
                  Training Seats*
                </th>
                <th
                  className="num-val sortable"
                  onClick={() => handleSort('absoluteGap')}
                  title="Sort by Net Gap"
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '4px' }}>
                    <span>Net Gap</span>
                    <ArrowUpDown size={11} />
                  </div>
                </th>
                <th
                  className="num-val sortable"
                  onClick={() => handleSort('gapRate')}
                  title="Sort by Gap Rate"
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '4px' }}>
                    <span>Gap Rate %</span>
                    <ArrowUpDown size={11} />
                  </div>
                </th>
                <th>Market Risk Signal</th>
                <th style={{ textAlign: 'center' }}>Inspect</th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.length === 0 ? (
                <tr>
                  <td colSpan={10} style={{ textAlign: 'center', padding: '32px', color: '#78716c' }}>
                    No occupations matched your filter criteria.
                  </td>
                </tr>
              ) : (
                filteredRows.map((row) => {
                  const isShortage = row.absoluteGap > 0;
                  const isSurplus = row.absoluteGap < 0;

                  return (
                    <tr
                      key={row.id}
                      className="clickable-row"
                      onClick={() => setInspectedOccupation(row)}
                      title="Click to view detailed Occupation Factsheet"
                    >
                      <td>
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                          <span style={{ fontWeight: 600, color: '#1c1917' }}>{row.canonicalTitle}</span>
                          <span style={{ fontFamily: 'monospace', fontSize: '11px', color: '#78716c' }}>
                            NCO: {row.ncoCode} · NSQF L{row.nsqfLevel}
                          </span>
                        </div>
                      </td>
                      <td>
                        <span style={{ fontSize: '12px', color: '#44403c' }}>{row.sector}</span>
                      </td>
                      <td>
                        <span style={{ fontSize: '11.5px', fontFamily: 'monospace', color: '#57534e', background: '#f5f5f4', padding: '1px 5px', borderRadius: '2px' }}>
                          {row.district}
                        </span>
                      </td>
                      <td className="num-val bold" style={{ color: '#1e3a8a' }}>
                        {formatNumber(row.documentedDemand)}
                      </td>
                      <td className="num-val bold" style={{ color: '#0f766e' }}>
                        {formatNumber(row.qualifiedSupply)}
                      </td>
                      <td className="num-val" style={{ color: '#78716c' }}>
                        <span title="Sanctioned capacity; not immediate qualified workers">
                          {formatNumber(row.trainingCapacity)}
                        </span>
                      </td>
                      <td
                        className="num-val bold"
                        style={{ color: isShortage ? '#c2410c' : isSurplus ? '#4338ca' : '#15803d' }}
                      >
                        {formatSignedNumber(row.absoluteGap)}
                      </td>
                      <td
                        className="num-val bold"
                        style={{ color: isShortage ? '#c2410c' : isSurplus ? '#4338ca' : '#15803d' }}
                      >
                        {formatGapRate(row.gapRate)}
                      </td>
                      <td>{renderRiskBadge(row.riskLevel)}</td>
                      <td style={{ textAlign: 'center' }}>
                        <button
                          type="button"
                          className="gov-btn gov-btn-outline"
                          style={{ padding: '2px 6px', fontSize: '11px' }}
                          onClick={(e) => {
                            e.stopPropagation();
                            setInspectedOccupation(row);
                          }}
                          aria-label={`Inspect ${row.canonicalTitle}`}
                        >
                          <span>Factsheet</span>
                          <ChevronRight size={11} />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11.5px', color: '#78716c', flexWrap: 'wrap', gap: '8px' }}>
          <span>
            Showing {filteredRows.length} of {occupations.length} monitored occupations · District:{' '}
            <strong>{selectedDistrict}</strong>
          </span>
          <span style={{ fontStyle: 'italic' }}>
            * Training Seats represent capacity; not qualified workers ready for employment.
          </span>
        </div>
      </section>

      {/* Factsheet Inspector Drawer */}
      <OccupationFactsheetDrawer
        occupation={inspectedOccupation}
        onClose={() => setInspectedOccupation(null)}
      />
    </>
  );
};
