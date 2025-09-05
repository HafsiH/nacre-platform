import { useState, useEffect } from 'react'

export default function App() {
  const [file, setFile] = useState(null)
  const [upload, setUpload] = useState(null)
  const [labelColumn, setLabelColumn] = useState('')
  const [columns, setColumns] = useState([])
  const [contextCols, setContextCols] = useState([])
  const [conversion, setConversion] = useState(null)
  const [rows, setRows] = useState([])
  const [processingSpeed, setProcessingSpeed] = useState(1) // 1x = 2 agents, 2x = 4 agents, 4x = 6 agents
  const [conversions, setConversions] = useState([]) // Liste des conversions disponibles
  const [showHistory, setShowHistory] = useState(false) // Afficher l'historique

  // Charger la liste des conversions
  const loadConversions = async () => {
    try {
      const res = await fetch('/conversions')
      if (res.ok) {
        const data = await res.json()
        setConversions(data)
      }
    } catch (error) {
      console.error('Erreur chargement conversions:', error)
    }
  }

  // Effacer l'historique complet
  const clearHistory = async () => {
    if (!confirm('Êtes-vous sûr de vouloir effacer tout l\'historique de la plateforme ? Cette action est irréversible.')) {
      return
    }
    
    try {
      const res = await fetch('/conversions/clear-history', { method: 'DELETE' })
      if (res.ok) {
        const data = await res.json()
        alert(data.message)
        setConversions([])
        setRows([])
        setConversion(null)
        loadConversions() // Recharger pour être sûr
      } else {
        alert('Erreur lors de l\'effacement de l\'historique')
      }
    } catch (error) {
      console.error('Erreur effacement historique:', error)
      alert('Erreur lors de l\'effacement de l\'historique')
    }
  }

  // Charger les conversions au démarrage
  useEffect(() => {
    loadConversions()
  }, [])

  const handleUpload = async (e) => {
    e.preventDefault()
    if (!file) return
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch('/files', { method: 'POST', body: fd })
    if (!res.ok) { alert('Upload échoué'); return }
    const data = await res.json()
    setUpload(data)
    setColumns(data.columns || [])
  }

  const toggleContext = (name) => {
    setContextCols((prev) => prev.includes(name) ? prev.filter(c => c !== name) : [...prev, name])
  }

  const startConversion = async () => {
    if (!upload || !labelColumn) { alert('Sélectionnez la colonne libellé'); return }
    const batchSize = processingSpeed === 1 ? 8 : processingSpeed === 2 ? 15 : 25  // Optimized batch sizes
    console.log('[DEBUG] Processing speed:', processingSpeed, 'Batch size:', batchSize)
    const payload = { 
      upload_id: upload.upload_id, 
      label_column: labelColumn, 
      context_columns: contextCols, 
      max_rows: 200,
      batch_size: batchSize
    }
    const res = await fetch('/conversions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
    if (!res.ok) { alert('Conversion échouée'); return }
    const status = await res.json()
    setConversion(status)
    // Poll progress until completed
    const id = status.conversion_id
    const poll = async () => {
      const sres = await fetch(`/conversions/${id}`)
      const sdata = await sres.json()
      setConversion(sdata)
      if (sdata.status === 'completed') {
        clearInterval(timer)
        const rowsRes = await fetch(`/conversions/${id}/rows?limit=1000`)
        const rowsData = await rowsRes.json()
        setRows(rowsData.rows || [])
        // Update columns from conversion results if available
        if (rowsData.rows && rowsData.rows.length > 0) {
          const firstRow = rowsData.rows[0]
          const conversionColumns = Object.keys(firstRow).filter(key => key !== 'id')
          setColumns(conversionColumns)
        }
      }
    }
    // Progressive polling: start fast, then slow down
    let pollInterval = 500 // Start at 0.5 seconds for faster updates
    const maxInterval = 2000 // Max 2 seconds
    let pollCount = 0
    
    const progressivePoll = async () => {
      try {
        pollCount++
        
        // Increase interval after first few polls
        if (pollCount > 3 && pollInterval < maxInterval) {
          pollInterval = Math.min(pollInterval * 1.2, maxInterval)
        }
        
        // Fetch conversion status
        const sres = await fetch(`/conversions/${id}`)
        const sdata = await sres.json()
        
        console.log(`Poll ${pollCount}: Status=${sdata.status}, Progress=${sdata.processed_rows}/${sdata.total_rows}`)
        setConversion(sdata)
        
        if (sdata.status !== 'completed' && sdata.status !== 'error') {
          setTimeout(progressivePoll, pollInterval)
        } else {
          // Fetch final results
          const rowsRes = await fetch(`/conversions/${id}/rows?limit=1000`)
          const rowsData = await rowsRes.json()
          setRows(rowsData.rows || [])
          // Update columns from conversion results if available
          if (rowsData.rows && rowsData.rows.length > 0) {
            const firstRow = rowsData.rows[0]
            const conversionColumns = Object.keys(firstRow).filter(key => key !== 'id')
            setColumns(conversionColumns)
          }
          // Recharger la liste des conversions
          loadConversions()
        }
      } catch (error) {
        console.error('Polling error:', error)
        setTimeout(progressivePoll, pollInterval)
      }
    }
    
    // Start progressive polling
    setTimeout(progressivePoll, pollInterval)
  }

  return (
    <>
      <div className="topbar">
        <div className="brand">NACRE Conversion</div>
        <div style={{ display:'flex', alignItems:'center', gap:12 }}>
        <HealthBar />
        </div>
      </div>
      <div className="container">
      <SophieIntro />
      <SophieLookup />
      <SophieChat />
      <section className="card">
        <div className="section-header">
          <div>
            <h3 className="section-title">Import de fichier</h3>
            <p className="section-subtitle">Uploadez votre fichier CSV ou Excel pour commencer l'analyse</p>
          </div>
        </div>
        
        <form onSubmit={handleUpload} className="form-row">
          <div className="form-group" style={{ flex: 2 }}>
          <input type="file" accept=".csv,.xlsx" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          </div>
          <button type="submit" className="btn" disabled={!file}>
            {!file ? 'Choisir un fichier' : 'Uploader le fichier'}
          </button>
        </form>
        
        {columns.length > 0 && (
          <div className="animate-fade-in" style={{ marginTop: 24 }}>
            <div className="form-group">
              <label>Colonne libellé</label>
              <select value={labelColumn} onChange={(e) => setLabelColumn(e.target.value)} className="select">
                <option value="">-- Sélectionnez la colonne principale --</option>
              {columns.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
            </div>
            
            <div className="form-group">
              <label>Colonnes contexte (optionnel)</label>
              <p className="text-sm" style={{ color: 'var(--muted)', marginBottom: '12px' }}>Sélectionnez les colonnes qui aideront à améliorer la précision de la classification</p>
              <div className="checkbox-group">
                {columns.filter(c => c !== labelColumn).map(c => (
                  <div key={c} className={`checkbox-item ${contextCols.includes(c) ? 'checked' : ''}`} onClick={() => toggleContext(c)}>
                    <input type="checkbox" checked={contextCols.includes(c)} onChange={() => toggleContext(c)} />
                    <span>{c}</span>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="processing-speed-controls" style={{ marginTop: 16, marginBottom: 16 }}>
              <label style={{ display: 'block', marginBottom: 8, fontWeight: 'bold' }}>
                Traitement parallèle (agents multiples)
              </label>
              <div className="speed-buttons" style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <button 
                  type="button"
                  className={`btn ${processingSpeed === 1 ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setProcessingSpeed(1)}
                  title="2 agents parallèles - 5 éléments/tâche"
                >
                  1× (2 agents)
                </button>
                <button 
                  type="button"
                  className={`btn ${processingSpeed === 2 ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setProcessingSpeed(2)}
                  title="4 agents parallèles - 8 éléments/tâche"
                >
                  2× (4 agents)
                </button>
                <button 
                  type="button"
                  className={`btn ${processingSpeed === 4 ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setProcessingSpeed(4)}
                  title="6 agents parallèles - 12 éléments/tâche"
                >
                  4× (6 agents)
                </button>
                <span style={{ marginLeft: 12, fontSize: '13px', color: 'var(--text-muted)' }}>
                  {processingSpeed === 1 && '• Traitement avec 2 agents parallèles'}
                  {processingSpeed === 2 && '• Traitement avec 4 agents parallèles'}
                  {processingSpeed === 4 && '• Traitement avec 6 agents parallèles'}
                </span>
              </div>
            </div>
            
            <button onClick={startConversion} className="btn" disabled={!labelColumn}>
              {!labelColumn ? 'Sélectionnez une colonne libellé' : 'Lancer la conversion'}
            </button>
          </div>
        )}
      </section>

      {conversion && (
        <section className="card animate-fade-in">
          <div className="section-header">
            <div>
              <h2 className="section-title">Résultats de l'analyse</h2>
              <p className="section-subtitle">{rows.length} entrées traitées</p>
            </div>
            <div className="flex gap-3">
              {conversion.status === 'completed' && (
                <span className="badge success">Terminé</span>
              )}
              {conversion.status !== 'completed' && (
                <span className="badge warning">En cours</span>
              )}
            </div>
          </div>
          
          <Progress status={conversion} />
          <ExportBox upload={upload} conversion={conversion} columns={columns} />
          
          <div className="table-container">
            <table>
            <thead>
              <tr>
                  <th>#</th>
                  <th>Libellé</th>
                  <th>Code</th>
                  <th>Catégorie</th>
                  <th>Confiance</th>
                  <th>Explication</th>
                  <th>Évolution</th>
                  <th>Alternatives</th>
                  <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <ResultRow key={r.row_index} convId={conversion.conversion_id} row={r} onUpdated={async()=>{
                  const rowsRes = await fetch(`/conversions/${conversion.conversion_id}/rows?limit=1000`)
                  const rowsData = await rowsRes.json()
                  setRows(rowsData.rows || [])
                }} />
              ))}
            </tbody>
          </table>
          </div>
        </section>
      )}
      
      {/* Bouton pour afficher l'historique */}
      {conversions.length > 0 && !showHistory && (
        <div style={{ textAlign: 'center', margin: '20px 0' }}>
          <button 
            className="btn btn-secondary" 
            onClick={() => setShowHistory(true)}
            style={{ fontSize: '12px', padding: '6px 12px' }}
          >
            Voir l'historique ({conversions.length} conversions)
          </button>
        </div>
      )}

      {/* Section des conversions disponibles */}
      {showHistory && conversions.length > 0 && (
        <section className="conversions-list-section">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h2>Historique des conversions</h2>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button 
                className="btn btn-danger btn-sm" 
                onClick={clearHistory}
                title="Effacer tout l'historique de la plateforme"
              >
                🗑️ Effacer tout
              </button>
              <button 
                className="btn btn-secondary btn-sm" 
                onClick={() => setShowHistory(false)}
              >
                Masquer
              </button>
            </div>
          </div>
          <div className="conversions-grid">
            {conversions.map((conv) => (
              <div key={conv.conversion_id} className="conversion-card">
                <div className="conversion-header">
                  <span className={`status-badge status-${conv.status}`}>
                    {conv.status === 'completed' ? '✅ Terminé' : 
                     conv.status === 'processing' ? '⏳ En cours' : 
                     conv.status === 'error' ? '❌ Erreur' : '⚪ ' + conv.status}
                  </span>
                  <span className="conversion-id">#{conv.conversion_id.slice(0, 8)}</span>
                </div>
                
                <div className="conversion-stats">
                  <div className="stat">
                    <span className="stat-label">Lignes:</span>
                    <span className="stat-value">{conv.total_rows}</span>
                  </div>
                  {conv.stats?.processing_time && (
                    <div className="stat">
                      <span className="stat-label">Temps:</span>
                      <span className="stat-value">{conv.stats.processing_time}</span>
                    </div>
                  )}
                  {conv.stats?.average_rate && (
                    <div className="stat">
                      <span className="stat-label">Vitesse:</span>
                      <span className="stat-value">{conv.stats.average_rate}</span>
                    </div>
                  )}
                  {conv.stats?.agents_used && (
                    <div className="stat">
                      <span className="stat-label">Agents:</span>
                      <span className="stat-value">{conv.stats.agents_used}</span>
                    </div>
                  )}
                </div>
                
                {conv.status === 'completed' && (
                  <div className="conversion-actions">
                    <button 
                      className="btn btn-sm"
                      onClick={async () => {
                        const rowsRes = await fetch(`/conversions/${conv.conversion_id}/rows?limit=1000`)
                        const rowsData = await rowsRes.json()
                        setRows(rowsData.rows || [])
                        setConversion(conv)
                        // Scroll to results
                        document.querySelector('.conversion-results')?.scrollIntoView({ behavior: 'smooth' })
                      }}
                    >
                      Voir les résultats
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}
      </div>
    </>
  )
}

function ExportBox({ upload, conversion, columns }) {
  const [keepCols, setKeepCols] = useState(columns)
  const [includeCls, setIncludeCls] = useState(true)
  const [isExporting, setIsExporting] = useState(false)
  const [showCarbonCalc, setShowCarbonCalc] = useState(false)
  const [showCarbonViz, setShowCarbonViz] = useState(false)
  const [carbonVizData, setCarbonVizData] = useState(null)
  const [loadingViz, setLoadingViz] = useState(false)

  const toggleKeep = (c) => {
    setKeepCols(prev => prev.includes(c) ? prev.filter(x => x !== c) : [...prev, c])
  }

  const generateCarbonVisualizations = async () => {
    if (!conversion) return

    setLoadingViz(true)
    try {
      // Demander à l'utilisateur de sélectionner la colonne montant
      const montantColumn = prompt("Veuillez entrer le nom de la colonne contenant les montants:", "montant")
      if (!montantColumn) {
        setLoadingViz(false)
        return
      }

      // Générer l'analyse complète avec visualisations
      const response = await fetch(`/api/carbon-viz/analyze-conversion`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversion_id: conversion.conversion_id,
          montant_column: montantColumn
        })
      })

      if (!response.ok) {
        throw new Error(`Erreur ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      setCarbonVizData(data)
      setShowCarbonViz(true)
    } catch (error) {
      console.error('Erreur lors de la génération des visualisations:', error)
      alert(`Erreur: ${error.message}`)
    } finally {
      setLoadingViz(false)
    }
  }

  const doExport = async () => {
    if (!conversion) return
    setIsExporting(true)
    try {
    const payload = {
      conversion_id: conversion.conversion_id,
      columns_to_keep: keepCols,
      include_classification: includeCls,
      classification_prefix: 'nacre_'
    }
    const res = await fetch('/exports', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
    if (!res.ok) { alert('Export échoué'); return }
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
      a.download = `nacre_export_${conversion.conversion_id}.csv`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <div className="export-section">
      <div className="export-title">
        Exporter les résultats
      </div>
      
      <div className="form-group">
        <label>Colonnes à inclure</label>
        <div className="column-selector">
        {columns.map(c => (
            <div key={c} className={`checkbox-item ${keepCols.includes(c) ? 'checked' : ''}`} onClick={() => toggleKeep(c)}>
            <input type="checkbox" checked={keepCols.includes(c)} onChange={() => toggleKeep(c)} />
            <span>{c}</span>
            </div>
        ))}
      </div>
      </div>
      
      <div className="form-group">
        <div className={`checkbox-item ${includeCls ? 'checked' : ''}`} onClick={() => setIncludeCls(!includeCls)}>
        <input type="checkbox" checked={includeCls} onChange={() => setIncludeCls(!includeCls)} />
          <span>Inclure les colonnes de classification (nacre_code, nacre_category, nacre_confidence)</span>
        </div>
      </div>
      
      <div className="export-actions">
        <button onClick={doExport} className="btn" disabled={isExporting || keepCols.length === 0}>
          {isExporting ? (
            <><span className="spinner" style={{ width: 16, height: 16 }}></span> Export en cours...</>
          ) : (
            'Télécharger le fichier CSV'
          )}
        </button>
        
        {conversion?.status === 'completed' && (
          <>
            <button 
              className="btn btn-success carbon-btn" 
              onClick={() => setShowCarbonCalc(true)}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M7,13H17V11H7"/>
              </svg>
              Calculer le bilan carbone
            </button>
            
            <button 
              className="btn btn-primary viz-btn" 
              disabled={loadingViz}
              onClick={generateCarbonVisualizations}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M3,3V21H21V19H5V3H3M9,17H7V10H9V17M13,17H11V7H13V17M17,17H15V13H17V17M19,17H21V4H19V17Z"/>
              </svg>
              {loadingViz ? 'Génération...' : 'Visualiser les émissions'}
            </button>
          </>
        )}
      </div>
      
      {showCarbonCalc && (
        <CarbonCalculator 
          conversion={conversion} 
          columns={columns}
          onClose={() => setShowCarbonCalc(false)} 
        />
      )}
      
      {showCarbonViz && carbonVizData && (
        <CarbonVisualizationModal 
          data={carbonVizData}
          onClose={() => setShowCarbonViz(false)} 
        />
      )}
    </div>
  )
}

function CarbonCalculator({ conversion, columns, onClose }) {
  const [montantColumn, setMontantColumn] = useState('')
  const [isCalculating, setIsCalculating] = useState(false)
  const [carbonResult, setCarbonResult] = useState(null)
  const [error, setError] = useState('')

  // Debug logs removed

  const possibleMontantColumns = columns?.filter(col => 
    col.toLowerCase().includes('montant') || 
    col.toLowerCase().includes('amount') || 
    col.toLowerCase().includes('valeur') || 
    col.toLowerCase().includes('prix') ||
    col.toLowerCase().includes('total')
  ) || []

  const calculateCarbon = async () => {
    if (!montantColumn) {
      setError('Veuillez sélectionner une colonne montant')
      return
    }

    setIsCalculating(true)
    setError('')
    
    try {
      // Récupérer les données de conversion
      const rowsRes = await fetch(`/conversions/${conversion.conversion_id}/rows?limit=10000`)
      const rowsData = await rowsRes.json()
      
      // Préparer les données pour le calcul CO2
      const data = rowsData.rows.map(row => ({
        code_nacre: row.nacre_code,
        libelle: row.original_label,
        [montantColumn]: row.original_data?.[montantColumn] || row[montantColumn] || 0
      }))

      // Appel à l'IA CO2
      const response = await fetch('/co2/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          data: data,
          montant_column: montantColumn
        })
      })

      if (!response.ok) {
        throw new Error('Erreur lors du calcul du bilan carbone')
      }

      const result = await response.json()
      setCarbonResult(result)
      
    } catch (err) {
      setError(err.message || 'Erreur lors du calcul')
    } finally {
      setIsCalculating(false)
    }
  }

  return (
    <div className="carbon-calculator-modal">
      <div className="modal-overlay" onClick={onClose}></div>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>IA - Analyse CO2</h3>
          <p>Calcul du bilan carbone basé sur les codes NACRE et les montants</p>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        {!carbonResult ? (
          <div className="carbon-setup">
            <div className="form-group">
              <label>Sélectionner la colonne montant</label>
              <select 
                value={montantColumn} 
                onChange={(e) => setMontantColumn(e.target.value)}
                className="select"
              >
                <option value="">-- Choisir la colonne contenant les montants --</option>
                {possibleMontantColumns.map(col => (
                  <option key={col} value={col}>{col}</option>
                ))}
                {possibleMontantColumns.length === 0 && columns?.map(col => (
                  <option key={col} value={col}>{col}</option>
                ))}
                {(!columns || columns.length === 0) && (
                  <option disabled>Aucune colonne disponible</option>
                )}
              </select>
            </div>

            {error && (
              <div className="error-message">
                {error}
              </div>
            )}

            <div className="carbon-actions">
              <button 
                className="btn btn-primary" 
                onClick={calculateCarbon}
                disabled={isCalculating || !montantColumn}
              >
                {isCalculating ? (
                  <>
                    <span className="spinner" style={{ width: 16, height: 16 }}></span>
                    Calcul en cours...
                  </>
                ) : (
                  <>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M19,3H5C3.89,3 3,3.89 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5C21,3.89 20.1,3 19,3M19,5V19H5V5H19Z"/>
                    </svg>
                    Lancer le calcul CO2
                  </>
                )}
              </button>
              <button className="btn btn-secondary" onClick={onClose}>
                Annuler
              </button>
            </div>
          </div>
        ) : (
          <CarbonResults result={carbonResult} onClose={onClose} />
        )}
      </div>
    </div>
  )
}

function CarbonResults({ result, onClose }) {
  return (
    <div className="carbon-results">
      <div className="results-header">
        <h4>Résultats du Bilan Carbone</h4>
        <div className="results-summary">
          <div className="summary-card total">
            <div className="summary-value">{result.total_co2_tonnes?.toFixed(2) || 0} t</div>
            <div className="summary-label">CO2 Total</div>
          </div>
          <div className="summary-card">
            <div className="summary-value">{result.total_montant?.toLocaleString() || 0} €</div>
            <div className="summary-label">Montant Analysé</div>
          </div>
          <div className="summary-card">
            <div className="summary-value">{result.processed_lines || 0}</div>
            <div className="summary-label">Lignes Traitées</div>
          </div>
          <div className="summary-card">
            <div className="summary-value">{result.success_rate?.toFixed(1) || 0}%</div>
            <div className="summary-label">Taux de Succès</div>
          </div>
        </div>
      </div>

      {result.performance_metrics && (
        <div className="performance-metrics">
          <h5>Métriques de Performance</h5>
          <div className="metrics-grid">
            <div className="metric-item">
              <span className="metric-label">Temps de traitement</span>
              <span className="metric-value">{result.performance_metrics.total_processing_time_seconds}s</span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Vitesse</span>
              <span className="metric-value">{result.performance_metrics.lines_per_second} lignes/s</span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Estimation 1K lignes</span>
              <span className="metric-value">{result.performance_metrics.estimated_time_for_1000_lines_seconds}s</span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Estimation 10K lignes</span>
              <span className="metric-value">{result.performance_metrics.estimated_time_for_10000_lines_minutes}min</span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Efficacité mémoire</span>
              <span className={`metric-value score-${result.performance_metrics.memory_efficiency_score?.toLowerCase()}`}>
                {result.performance_metrics.memory_efficiency_score}
              </span>
            </div>
          </div>
        </div>
      )}

      {result.emission_sources && Object.keys(result.emission_sources).length > 0 && (
        <div className="emission-sources">
          <h5>Sources des Facteurs d'Émission</h5>
          <div className="sources-list">
            {Object.entries(result.emission_sources).map(([source, data]) => (
              <div key={source} className="source-item">
                <div className="source-info">
                  <span className="source-name">
                    {source === 'emission' ? 'Colonne emission (spécifique)' : 'Colonne emission_factor (sectoriel)'}
                  </span>
                  <span className="source-stats">
                    {data.count} codes • {(data.total_co2_kg / 1000).toFixed(2)} t CO2
                  </span>
                </div>
                <div className="source-bar">
                  <div 
                    className={`source-fill ${source}`}
                    style={{ width: `${(data.count / result.processed_lines) * 100}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {result.ai_analysis && (
        <div className="ai-analysis">
          <h5>Analyse IA</h5>
          <div className="analysis-content">
            {result.ai_analysis}
          </div>
        </div>
      )}

      {result.summary_by_code && Object.keys(result.summary_by_code).length > 0 && (
        <div className="top-emitters">
          <h5>Principaux Émetteurs</h5>
          <div className="emitters-list">
            {Object.entries(result.summary_by_code)
              .sort(([,a], [,b]) => b.total_co2_kg - a.total_co2_kg)
              .slice(0, 5)
              .map(([code, data]) => (
                <div key={code} className="emitter-item">
                  <div className="emitter-code">{code}</div>
                  <div className="emitter-details">
                    <span className="co2-amount">{(data.total_co2_kg / 1000).toFixed(2)} t CO2</span>
                    <span className="montant-amount">{data.total_montant?.toLocaleString()} €</span>
                    <span className="occurrences">{data.occurrences} ligne{data.occurrences > 1 ? 's' : ''}</span>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {result.recommendations && result.recommendations.length > 0 && (
        <div className="recommendations">
          <h5>Recommandations</h5>
          <ul>
            {result.recommendations.map((rec, idx) => (
              <li key={idx}>{rec}</li>
            ))}
          </ul>
        </div>
      )}

      {result.errors && result.errors.length > 0 && (
        <div className="calculation-errors">
          <h5>Erreurs de Calcul ({result.errors.length})</h5>
          <div className="errors-list">
            {result.errors.slice(0, 10).map((error, idx) => (
              <div key={idx} className="error-item">{error}</div>
            ))}
            {result.errors.length > 10 && (
              <div className="error-item">... et {result.errors.length - 10} autres erreurs</div>
            )}
          </div>
        </div>
      )}

      <div className="results-actions">
        <button className="btn btn-primary" onClick={() => {
          const dataStr = JSON.stringify(result, null, 2)
          const blob = new Blob([dataStr], { type: 'application/json' })
          const url = URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = `bilan_carbone_${new Date().toISOString().split('T')[0]}.json`
          a.click()
          URL.revokeObjectURL(url)
        }}>
          Télécharger le rapport
        </button>
        <button className="btn btn-secondary" onClick={onClose}>
          Fermer
        </button>
      </div>
    </div>
  )
}

function Progress({ status }) {
  const [startTime, setStartTime] = useState(null)
  const [currentTime, setCurrentTime] = useState(Date.now())
  
  const total = status?.total_rows || 0
  const done = status?.processed_rows || 0
  const percent = total > 0 ? Math.floor((done / total) * 100) : (status?.status === 'completed' ? 100 : 0)
  const running = status?.status !== 'completed'
  
  useEffect(() => {
    if (running && !startTime) {
      setStartTime(Date.now())
    }
    
    const timer = setInterval(() => setCurrentTime(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [running, startTime])
  
  const elapsed = startTime ? (currentTime - startTime) / 1000 : 0
  const rate = elapsed > 0 ? (done / elapsed) : 0
  const eta = rate > 0 ? ((total - done) / rate) : 0
  
  return (
    <div style={{ marginBottom: 20 }}>
      <div className="progress-info">
        <span className="progress-text">
          Progression de l'analyse
          {running && <span className="spinner" style={{ marginLeft: 8, width: 16, height: 16 }}></span>}
        </span>
        <span className="progress-percentage">{percent}%</span>
      </div>
      <div className="progress-info" style={{ fontSize: '0.75rem', marginBottom: 8 }}>
        <span>{done}/{total} entrées</span>
        <span>{running ? 'En cours...' : 'Terminé'}</span>
      </div>
      {running && elapsed > 0 && (
        <div className="progress-info" style={{ fontSize: '0.7rem', marginBottom: 8, color: 'var(--text-muted)' }}>
          <span>⚡ {rate.toFixed(1)} entrées/sec</span>
          {eta > 0 && <span style={{ marginLeft: 12 }}>⏱️ ETA: {Math.ceil(eta)}s</span>}
          <span style={{ marginLeft: 12 }}>🕐 {elapsed.toFixed(0)}s</span>
        </div>
      )}
      <div className="progress-container">
        <div className="progress-bar" style={{ width: `${percent}%` }} />
      </div>
    </div>
  )
}

function ResultRow({ convId, row, onUpdated }) {
  const [sel, setSel] = useState(row.chosen_code)
  const [conf, setConf] = useState(row.confidence)
  const [isUpdating, setIsUpdating] = useState(false)
  const [copied, setCopied] = useState(false)
  
  const alts = [{ code: row.chosen_code, category: row.chosen_category, confidence: row.confidence }, ...(row.alternatives||[])]
  
  const copy = async (text) => { 
    try { 
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {} 
  }
  
  const apply = async () => {
    setIsUpdating(true)
    try {
    const chosen = alts.find(a => a.code === sel)
    const payload = {
      chosen_code: sel,
      chosen_category: chosen?.category,
      confidence: conf
    }
    const res = await fetch(`/conversions/${convId}/rows/${row.row_index}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      if (!res.ok) { alert('❌ Échec de la mise à jour'); return }
    await onUpdated?.()
    } finally {
      setIsUpdating(false)
    }
  }
  
  const getConfidenceColor = (confidence) => {
    if (confidence >= 80) return 'var(--ok)'
    if (confidence >= 60) return 'var(--warning)'
    return 'var(--bad)'
  }
  
  return (
    <tr>
      <td><span className="badge">{row.row_index}</span></td>
      <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }} title={row.label_raw}>
        {row.label_raw}
      </td>
      <td>
        <div className="flex items-center gap-2">
          <code className="lookup-code">{row.chosen_code}</code>
          <button 
            className="copy-button" 
            onClick={() => copy(row.chosen_code)} 
            data-tooltip={copied ? "Copié !" : "Copier le code"}
          >
            {copied ? 'Copié' : 'Copier'}
          </button>
        </div>
      </td>
      <td style={{ maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis' }} title={row.chosen_category}>
        {row.chosen_category}
      </td>
      <td>
        <div className="flex items-center gap-2">
          <input 
            type="number" 
            min={0} 
            max={100} 
            value={conf} 
            onChange={e => setConf(parseInt(e.target.value||'0',10))} 
            className="confidence-input"
          />
          <div 
            style={{ 
              width: '8px', 
              height: '8px', 
              borderRadius: '50%', 
              backgroundColor: getConfidenceColor(conf) 
            }}
          />
        </div>
      </td>
      <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }} title={row.explanation}>
        {row.explanation || '—'}
      </td>
      <td style={{ maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis' }} title={row.evolution_summary}>
        {row.evolution_summary || '—'}
      </td>
      <td>
        <select value={sel} onChange={e => setSel(e.target.value)} className="select" style={{ minWidth: '150px' }}>
          {alts.map((a, index) => (
            <option key={`${a.code}-${index}`} value={a.code}>{a.code} : {a.category}</option>
          ))}
        </select>
      </td>
      <td>
        <button 
          className="btn btn-sm" 
          onClick={apply} 
          disabled={isUpdating || (sel === row.chosen_code && conf === row.confidence)}
        >
          {isUpdating ? (
            <><span className="spinner" style={{ width: 12, height: 12 }}></span> Mise à jour...</>
          ) : (
            'Appliquer'
          )}
        </button>
      </td>
    </tr>
  )
}

function HealthBar() {
  const [ok, setOk] = useState(false)
  const [oa, setOa] = useState('unknown') // 'ok' | 'bad' | 'unknown'
  const [dict, setDict] = useState(false)
  const [learning, setLearning] = useState({ ready: false, in_progress: false, done: 0, total: 0 })
  const [co2, setCo2] = useState('unknown') // 'ok' | 'bad' | 'unknown'
  const [rebuilding, setRebuilding] = useState(false)
  const [resetting, setResetting] = useState(false)

  const fetchHealth = async () => {
    try {
      const res = await fetch('/health')
      if (!res.ok) throw new Error('health not ok')
      const data = await res.json()
      setOk(Boolean(data.api && data.storage_ok && data.dict_loaded))
      setDict(Boolean(data.dict_loaded))
      if (data.openai_connectivity === true) setOa('ok')
      else if (data.openai_connectivity === false) setOa('bad')
      else setOa('unknown')
      if (data.learning) setLearning(data.learning)
      
      // CO2 analyzer status
      if (data.co2_analyzer) {
        if (data.co2_analyzer.status === 'active' && data.co2_analyzer.nacre_dict_loaded) {
          setCo2('ok')
        } else if (data.co2_analyzer.status === 'error') {
          setCo2('bad')
        } else {
          setCo2('unknown')
        }
      } else {
        setCo2('bad')
      }
    } catch (e) {
      setOk(false); setOa('bad'); setCo2('bad')
    }
  }

  const resetConnections = async () => {
    setResetting(true)
    try {
      // Call the dedicated reset endpoint
      const response = await fetch('/health/reset-connections', { method: 'POST' })
      const result = await response.json()
      
      if (result.ok) {
        console.log('Connexions réinitialisées:', result.message)
      } else {
        console.error('Erreur reset connexions:', result.message)
      }
      
      // Force refresh health status
      await fetchHealth()
      
      // If still failing, wait a bit and try again
      if (!ok || oa !== 'ok') {
        await new Promise(resolve => setTimeout(resolve, 2000))
        await fetchHealth()
      }
    } catch (error) {
      console.error('Erreur lors du reset des connexions:', error)
    } finally {
      setResetting(false)
    }
  }

  useEffect(() => {
    fetchHealth()
    // Reduced frequency: health check every 30 seconds instead of 10
    const t = setInterval(fetchHealth, 30000)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="status">
      <span className="pill"><span className={`dot ${ok ? 'ok' : 'bad'}`}></span>API</span>
      <span className="pill"><span className={`dot ${oa==='ok' ? 'ok' : (oa==='bad' ? 'bad' : '')}`}></span>OpenAI</span>
      <span className="pill"><span className={`dot ${dict ? 'ok' : 'bad'}`}></span>Dictionnaire</span>
      <span className="pill" title="Analyseur CO2 pour calcul bilan carbone">
        <span className={`dot ${co2==='ok' ? 'ok' : (co2==='bad' ? 'bad' : '')}`}></span>CO2
      </span>
      <span className="pill" title="Index d'apprentissage du dictionnaire">
        <span className={`dot ${learning.ready ? 'ok' : (learning.in_progress ? '' : 'bad')}`}></span>
        Apprentissage {learning.in_progress ? `${learning.done}/${learning.total}` : (learning.ready ? 'prêt' : 'en attente')}
      </span>
      <button 
        className="btn" 
        disabled={resetting} 
        onClick={resetConnections}
        title="Réinitialiser les connexions API et OpenAI"
      >
        {resetting ? 'Reset…' : 'Reset Connection'}
      </button>
      <button className="btn" disabled={rebuilding} onClick={async ()=>{
        try {
          setRebuilding(true)
          await fetch('/health/rebuild', { method: 'POST' })
          await fetchHealth()
        } finally {
          setRebuilding(false)
        }
      }}>
        {rebuilding ? 'Reconstruction…' : 'Reconstruire'}
      </button>
    </div>
  )
}

function SophieIntro() {
  const [intro, setIntro] = useState("")
  const [children, setChildren] = useState([])
  const [dict, setDict] = useState({ total_entries: 0, categories_count: 0 })
  const [isLoading, setIsLoading] = useState(true)
  
  const load = async () => {
    setIsLoading(true)
    try {
      // Fetch dynamic introduction from Sophie
      const introRes = await fetch('/sophie/introduction')
      if (introRes.ok) {
        const introData = await introRes.json()
        setIntro(introData?.introduction || "Bonjour, je suis Sophie, votre assistante spécialisée en classification NACRE.")
      }
      
      // Fetch children status from health
      const res = await fetch('/health')
      if (res.ok) {
        const h = await res.json()
        setChildren(h?.sophie?.children || [])
      }
      
      // Fetch dictionary summary from /sophie/context
      const ctx = await fetch('/sophie/context')
      if (ctx.ok) {
        const c = await ctx.json()
        const nd = c?.nacre_dictionary || {}
        setDict({ total_entries: nd.total_entries || 0, categories_count: nd.categories_count || 0 })
      }
    } catch {}
    finally {
      setIsLoading(false)
  }
  }
  
  useEffect(() => { load() }, [])
  
  if (isLoading) {
    return (
      <div className="card loading">
        <div className="flex items-center gap-3">
          <span className="spinner"></span>
          <span>Initialisation de Sophie...</span>
        </div>
      </div>
    )
  }
  
  if (!intro) return null
  
  return (
    <div className="card animate-fade-in">
      <div className="section-header">
        <div>
          <h3 className="section-title">Sophie - Assistant IA</h3>
          <p className="section-subtitle">{intro}</p>
        </div>
      </div>
      
      <div className="status">
        <div className="pill" data-tooltip="État du dictionnaire NACRE">
          <span className="dot ok"></span>
          Dictionnaire: {dict.total_entries.toLocaleString()} entrées, {dict.categories_count} catégories
        </div>
        {children.map((c,i) => {
          return (
            <div key={i} className="pill" data-tooltip={`Service ${c.name}: ${c.status}`}>
              <span className={`dot ${c.status==='ready' ? 'ok' : (c.status==='building' ? 'warning' : 'bad')}`}></span>
              {c.name}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function SophieLookup() {
  const [q, setQ] = useState("")
  const [lookup, setLookup] = useState(null)
  const [results, setResults] = useState([])
  const [limit, setLimit] = useState(5)
  const [offset, setOffset] = useState(0)
  const [busy, setBusy] = useState(false)
  const [showScores, setShowScores] = useState(true)

  const doLookup = async () => {
    if (!q.trim()) return
    setBusy(true)
    try {
      const r = await fetch(`/sophie/lookup?query=${encodeURIComponent(q)}`)
      if (r.ok) setLookup(await r.json())
    } finally { setBusy(false) }
  }
  
  const doSearch = async (newOffset = 0) => {
    if (!q.trim()) return
    setBusy(true)
    try {
      const r = await fetch(`/sophie/search?query=${encodeURIComponent(q)}&limit=${limit}&offset=${newOffset}`)
      if (r.ok) {
        const d = await r.json()
        setResults(d.results || [])
        setOffset(d.offset || 0)
      }
    } finally { setBusy(false) }
  }

  return (
    <section className="card">
      <div className="section-header">
        <div>
          <h3 className="section-title">Recherche dans le dictionnaire NACRE</h3>
          <p className="section-subtitle">Trouvez rapidement un code ou explorez les catégories disponibles</p>
        </div>
      </div>
      
      <div className="form-row">
        <div className="search-input form-group" style={{ flex: 2 }}>
          <input 
            placeholder="Rechercher un code NACRE (ex: papeterie, fournitures bureau...)" 
            value={q} 
            onChange={e=>setQ(e.target.value)}
            onKeyPress={e => e.key === 'Enter' && doLookup()}
          />
        </div>
        <button className="btn" onClick={doLookup} disabled={busy || !q.trim()}>
          {busy ? (
            <><span className="spinner" style={{ width: 16, height: 16 }}></span> Recherche...</>
          ) : (
            'Trouver le code'
          )}
        </button>
        <button className="btn btn-secondary" onClick={()=>doSearch(0)} disabled={busy || !q.trim()}>
          {busy ? 'Chargement...' : 'Parcourir'}
        </button>
        {results.length > 0 && (
          <button className="btn btn-tertiary" onClick={()=>setResults([])}>
            Fermer liste
          </button>
        )}
      </div>
      
      {lookup && (
        <div className="animate-fade-in" style={{ marginBottom: 16, padding: 16, background: 'var(--card-hover)', borderRadius: 12, border: '1px solid var(--border)' }}>
          <div style={{ fontWeight: 600, marginBottom: 8, color: 'var(--accent)' }}>Meilleure correspondance</div>
          <div>
            {lookup.code ? (
              <div className="flex items-center gap-3">
                <code className="lookup-code" style={{ fontSize: '1rem' }}>{lookup.code}</code>
                <span>—</span>
                <span style={{ color: 'var(--text-secondary)' }}>{lookup.category}</span>
              </div>
            ) : (
              <span style={{ color: 'var(--muted)' }}>Aucune correspondance trouvée</span>
            )}
          </div>
          {!!(lookup.candidates||[]).length && (
            <div style={{ marginTop: 8, padding: 8, background: 'var(--card)', borderRadius: 8 }}>
              <div style={{ fontSize: '0.875rem', color: 'var(--muted)', marginBottom: 4 }}>Suggestions alternatives :</div>
              <div className="flex gap-2 flex-wrap">
                {(lookup.candidates||[]).slice(0,5).map(c=>(
                  <span key={c.code} className="badge">{c.code}</span>
        ))}
      </div>
    </div>
          )}
        </div>
      )}
      
      {!!results.length && (
        <div className="animate-fade-in search-results-section">
          <div style={{ fontWeight: 600, marginBottom: 12, color: 'var(--accent)' }}>Résultats de recherche</div>
          <div className="lookup-results">
            {results.map((r,i)=>(
              <div key={i} className="lookup-item">
                <div className="flex justify-between items-center">
                  <div>
                    <code className="lookup-code">{r.code}</code>
                    <div className="lookup-category">{r.category}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="flex gap-3 items-center mt-4">
            <button 
              className="btn btn-secondary" 
              onClick={()=>{ const no = Math.max(0, offset - limit); doSearch(no) }} 
              disabled={busy || offset===0}
            >
              Précédent
            </button>
            <button 
              className="btn btn-secondary" 
              onClick={()=>{ const no = offset + limit; doSearch(no) }} 
              disabled={busy}
            >
              Suivant
            </button>
            <span className="text-sm opacity-75">Position {offset + 1}</span>
          </div>
        </div>
      )}
    </section>
  )
}

function SophieChat() {
  const [history, setHistory] = useState([])
  const [input, setInput] = useState("")
  const [busy, setBusy] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [debug, setDebug] = useState({ received:false, interpreted:false, used_fallback:false })
  const [showDbg, setShowDbg] = useState(false)
  const [snapshot, setSnapshot] = useState("")
  const [thinkingMode, setThinkingMode] = useState(true)
  const [currentThinking, setCurrentThinking] = useState(null)
  const [autonomyLevel, setAutonomyLevel] = useState('high')
  
  const getAutonomyDescription = (level) => {
    const descriptions = {
      low: "Sophie suit vos instructions précises et demande confirmation pour les actions importantes",
      medium: "Sophie équilibre autonomie et guidance, propose des options avant d'agir",
      high: "Sophie prend des initiatives et execute des tâches complexes de manière indépendante",
      maximum: "Sophie agit avec une liberté totale, gérant tous les aspects de manière autonome"
    }
    return descriptions[level] || ""
  }
  
  const load = async () => {
    try {
      const res = await fetch('/sophie/chat/history?limit=50')
      if (!res.ok) return
      const d = await res.json()
      setHistory(d?.history || [])
    } catch {}
  }
  
  useEffect(() => { load() }, [])
  
  const sendWithThinking = async () => {
    if (!input.trim()) return
    const userMsg = { ts: Date.now()/1000, role: 'user', content: input }
    setHistory(h => [...h, userMsg])
    setInput("")
    
    try {
      setBusy(true)
      setCurrentThinking({ steps: [], status: 'processing' })
      
      const res = await fetch('/sophie/chat-with-thinking', { 
        method:'POST', 
        headers:{'Content-Type':'application/json'}, 
        body: JSON.stringify({ message: userMsg.content }) 
      })
      
      if (!res.ok) return
      
      const data = await res.json()
      const botMsg = { 
        ts: Date.now()/1000, 
        role: 'assistant', 
        content: data?.reply || '',
        thinking_process: data?.thinking_process || [],
        tasks_created: data?.tasks_created || [],
        tasks_completed: data?.tasks_completed || [],
        autonomy_level: data?.autonomy_level || 'medium',
        execution_time: data?.execution_time || 0
      }
      
      setHistory(h => [...h, botMsg])
      setCurrentThinking(null)
      
    } catch (error) {
      console.error('Error in thinking chat:', error)
      setCurrentThinking({ error: error.message })
    } finally { 
      setBusy(false) 
    }
  }

  const sendRegular = async () => {
    if (!input.trim()) return
    const userMsg = { ts: Date.now()/1000, role: 'user', content: input }
    setHistory(h => [...h, userMsg])
    setInput("")
    try {
      setBusy(true)
      setDebug(d => ({ ...d, received: true, interpreted: false }))
      
      // Utiliser la communication humanisée par défaut
      const conversationHistory = history.slice(-6).map(msg => ({
        role: msg.role,
        content: msg.content
      }))
      
      const res = await fetch('/sophie/chat-humanized', { 
        method:'POST', 
        headers:{'Content-Type':'application/json'}, 
        body: JSON.stringify({ 
          message: userMsg.content,
          conversation_history: conversationHistory
        }) 
      })
      
      setDebug(d => ({ ...d, interpreted: true }))
      if (!res.ok) { return }
      const d = await res.json()
      
      const botMsg = { 
        ts: Date.now()/1000, 
        role: 'assistant', 
        content: d?.reply || '',
        communication_metadata: d?.communication_metadata || {}
      }
      
      setHistory(h => [...h, botMsg])
      
      try {
        const dbg = await fetch('/sophie/debug')
        if (dbg.ok) {
          const obj = await dbg.json()
          setDebug(prev => ({
            ...prev, 
            received:true, 
            interpreted:true, 
            used_fallback: !d?.communication_metadata?.humanization_success
          }))
          setSnapshot(obj?.snapshot || '')
        }
      } catch {}
    } catch {} finally { setBusy(false) }
    setTimeout(()=>{
      setDebug({ received:false, interpreted:false, used_fallback:false })
    }, 1200)
  }

  const send = sendWithThinking // Toujours utiliser le mode thinking

  return (
    <div className="sophie-container">
      <div className="sophie-header">
        <div className="sophie-title">
          <div className="sophie-avatar">S</div>
          <div className="sophie-info">
            <h2>Sophie</h2>
            <span className="sophie-subtitle">Assistant IA Agentique</span>
          </div>
        </div>
        
        <div className="sophie-controls">
          <div className="control-group">
            <label className="control-label">Niveau d'autonomie</label>
            <div className="autonomy-selector">
              <select 
                value={autonomyLevel} 
                onChange={(e) => setAutonomyLevel(e.target.value)}
                className="control-select autonomy-select"
                title={getAutonomyDescription(autonomyLevel)}
              >
                <option value="low" title="Sophie suit vos instructions précises et demande confirmation pour les actions importantes">
                  Guidé
                </option>
                <option value="medium" title="Sophie équilibre autonomie et guidance, propose des options avant d'agir">
                  Équilibré
                </option>
                <option value="high" title="Sophie prend des initiatives et execute des tâches complexes de manière indépendante">
                  Autonome
                </option>
                <option value="maximum" title="Sophie agit avec une liberté totale, gérant tous les aspects de manière autonome">
                  Libre
                </option>
              </select>
            </div>
          </div>
          
          <div className="control-actions">
            <button 
              className="control-btn secondary" 
              onClick={()=>setShowDbg(s=>!s)}
              title="Afficher les informations de débogage"
            >
              Debug
            </button>
            <button 
              className="control-btn danger" 
              disabled={resetting} 
              onClick={async()=>{
          try {
            setResetting(true)
            await fetch('/sophie/reset', { method:'POST' })
            setHistory([])
            setDebug({ received:false, interpreted:false, used_fallback:false })
            setSnapshot('')
                  setCurrentThinking(null)
          } finally { setResetting(false) }
              }}
              title="Réinitialiser la conversation"
            >
              {resetting ? 'Reset...' : 'Reset'}
            </button>
      </div>
      </div>
      </div>
      
      
      {showDbg && (
        <div className="sophie-debug">
          <div className="debug-header">
            <h4>Informations de débogage</h4>
          </div>
          <div className="debug-content">
            <pre>{snapshot || 'Aucune donnée disponible'}</pre>
          </div>
        </div>
      )}
      
      {currentThinking && (
        <ThinkingProcess thinking={currentThinking} />
      )}
      
      <div className="sophie-conversation">
        <div className="conversation-content">
          {history.length === 0 ? (
            <div className="conversation-empty">
              <div className="empty-state">
                <div className="empty-icon">S</div>
                <h3>Commencez une conversation</h3>
                <p>Sophie est prête à vous aider avec l'analyse et la classification de vos données NACRE.</p>
      </div>
            </div>
          ) : (
            history.map((msg, idx) => (
              <ChatMessage key={idx} message={msg} showThinking={thinkingMode} />
            ))
          )}
        </div>
      </div>
      
      <div className="sophie-input">
        <div className="input-container">
          <textarea 
            placeholder="Décrivez votre demande ou posez une question à Sophie..."
            value={input} 
            onChange={e=>setInput(e.target.value)} 
            onKeyDown={e=>{ 
              if(e.key==='Enter' && !e.shiftKey && !busy) {
                e.preventDefault()
                send()
              }
            }}
            className="message-input"
            rows="1"
            disabled={busy}
          />
          <button 
            onClick={send} 
            disabled={busy || !input.trim()} 
            className="send-button"
            title="Envoyer le message (Entrée)"
          >
            {busy ? (
              <div className="send-loading">
                <div className="loading-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            ) : (
              <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
              </svg>
            )}
          </button>
        </div>
        
        <div className="input-hint">
          <div className="hint-content">
            <span className="hint-icon">◦</span>
            Sophie détaillera automatiquement son processus de réflexion
          </div>
        </div>
      </div>
      
      <TrainCard />
    </div>
  )
}

function ChatMessage({ message, showThinking }) {
  const [showDetails, setShowDetails] = useState(false)
  
  const formatMessage = (text) => {
    if (!text) return text
    
    // Convertir les ** en gras HTML
    let formatted = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    
    // Gérer les sauts de ligne
    formatted = formatted.replace(/\n\n/g, '</p><p>')
    formatted = formatted.replace(/\n/g, '<br/>')
    
    // Envelopper dans des paragraphes si nécessaire
    if (formatted.includes('<br/>') || formatted.includes('<strong>')) {
      formatted = '<p>' + formatted + '</p>'
    }
    
    return formatted
  }
  
  return (
    <div className={`message-wrapper ${message.role}`}>
      <div className="message-avatar">
        {message.role === 'user' ? 'U' : 'S'}
      </div>
      
      <div className="message-bubble">
        <div 
          className="message-text"
          dangerouslySetInnerHTML={{ __html: formatMessage(message.content) }}
        />
        
        {message.role === 'assistant' && message.communication_metadata && (
          <div className="communication-indicator">
            <div className="communication-meta">
              <span className={`communication-status ${message.communication_metadata.humanization_success ? 'humanized' : 'technical'}`}>
                {message.communication_metadata.humanization_success ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2C13.1 2 14 2.9 14 4C14 5.1 13.1 6 12 6C10.9 6 10 5.1 10 4C10 2.9 10.9 2 12 2ZM21 9V7L15 1H5C3.89 1 3 1.89 3 3V21C3 22.11 3.89 23 5 23H11V21H5V3H13V9H21Z"/>
                  </svg>
                ) : (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M9,5V9H21V7L15,1H5A2,2 0 0,0 3,3V19A2,2 0 0,0 5,21H11V19H5V5H9M12,19L17,16.5V15C17,14.45 16.55,14 16,14H12.5C12.22,14 12,13.78 12,13.5V13C12,12.45 12.45,12 13,12H16C17.1,12 18,12.9 18,14V16.5L22,19L18,21.5V23C18,24.1 17.1,25 16,25H13C12.45,25 12,24.55 12,24V19Z"/>
                  </svg>
                )}
                <span className="communication-label">
                  {message.communication_metadata.humanization_success ? 'Communication naturelle' : 'Mode technique'}
                </span>
              </span>
              {message.communication_metadata.tone && (
                <span className={`tone-indicator ${message.communication_metadata.tone}`}>
                  {message.communication_metadata.tone}
                </span>
              )}
            </div>
          </div>
        )}

        {message.role === 'assistant' && message.thinking_process && (
          <div className="reasoning-panel">
            <button 
              className="reasoning-toggle" 
              onClick={() => setShowDetails(!showDetails)}
            >
              <span className="toggle-indicator">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                </svg>
              </span>
              <div className="toggle-content">
                <span className="toggle-text">
                  {showDetails ? 'Masquer le processus' : 'Voir le processus de raisonnement'}
                </span>
                <div className="reasoning-meta">
                  {message.thinking_process.length} étapes
                  {message.execution_time && (
                    <span className="execution-time">{message.execution_time.toFixed(1)}s</span>
                  )}
                </div>
              </div>
            </button>
            
            {showDetails && (
              <div className="reasoning-details">
                <div className="reasoning-overview">
                  <div className="overview-stats">
                    <div className="stat-item">
                      <span className="stat-label">Niveau d'autonomie</span>
                      <span className="stat-value">{message.autonomy_level}</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">Tâches exécutées</span>
                      <span className="stat-value">
                        {message.tasks_completed?.length || 0} / {message.tasks_created?.length || 0}
                      </span>
                    </div>
                  </div>
                </div>
                
                <div className="reasoning-steps">
                  {message.thinking_process.map((step, idx) => (
                    <div key={idx} className={`reasoning-step ${step.status}`}>
                      <div className="step-indicator">
                        <div className={`step-number ${step.status}`}>
                          {step.status === 'completed' ? (
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                              <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                            </svg>
                          ) : step.status === 'processing' ? (
                            <div className="processing-spinner"></div>
                          ) : step.status === 'failed' ? (
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                            </svg>
                          ) : (
                            <div className="step-dot"></div>
                          )}
                        </div>
                      </div>
                      <div className="step-content">
                        <div className="step-title">{step.step}</div>
                        <div className="step-description">{step.content}</div>
                      </div>
                    </div>
                  ))}
                </div>
                
                {message.tasks_created && message.tasks_created.length > 0 && (
                  <div className="tasks-overview">
                    <h4 className="tasks-header">Tâches autonomes</h4>
                    <div className="tasks-grid">
                      {message.tasks_created.map((task, idx) => (
                        <div key={idx} className={`task-card ${message.tasks_completed?.includes(task.id) ? 'completed' : 'pending'}`}>
                          <div className="task-status-indicator">
                            {message.tasks_completed?.includes(task.id) ? (
                              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                              </svg>
                            ) : (
                              <div className="pending-indicator"></div>
                            )}
                          </div>
                          <div className="task-info">
                            <div className="task-title">{task.name}</div>
                            <div className="task-description">{task.description}</div>
                            <div className="task-meta">
                              <span className={`task-priority ${task.priority}`}>
                                {task.priority}
                              </span>
                              {task.estimated_duration && (
                                <span className="task-duration">{task.estimated_duration}s</span>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function ThinkingProcess({ thinking }) {
  if (!thinking) return null
  
  if (thinking.error) {
    return (
      <div className="thinking-status error">
        <div className="status-header">
          <div className="status-icon error">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
          </div>
          <div className="status-content">
            <h4>Erreur de traitement</h4>
            <p>Une erreur s'est produite lors de l'analyse</p>
          </div>
        </div>
        <div className="error-details">
          <pre>{thinking.error}</pre>
        </div>
      </div>
    )
  }
  
  return (
    <div className="thinking-status active">
      <div className="status-header">
        <div className="status-icon processing">
          <div className="thinking-pulse"></div>
        </div>
        <div className="status-content">
          <h4>Analyse en cours</h4>
          <p>Sophie traite votre demande étape par étape</p>
        </div>
      </div>
      <div className="processing-indicator">
        <div className="progress-track">
          <div className="progress-fill"></div>
        </div>
        <div className="processing-steps">
          <span className="step-dot active"></span>
          <span className="step-dot active"></span>
          <span className="step-dot"></span>
          <span className="step-dot"></span>
          <span className="step-dot"></span>
        </div>
      </div>
    </div>
  )
}

function TrainCard() {
  const [file, setFile] = useState(null)
  const [summary, setSummary] = useState(null)
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState({ in_progress:false, processed:0, total:0, errors:0 })
  const [poll, setPoll] = useState(null)
  const [headers, setHeaders] = useState([])
  const [showMap, setShowMap] = useState(false)
  const [mapping, setMapping] = useState({ label:'', code:'', fournisseur:'', compte:'', montant:'', confidence:'' })

  const guessMap = (hs) => {
    const low = hs.map(h=>({raw:h, key:h.toLowerCase().trim()}))
    
    const find = (cands) => {
      // Recherche exacte
      for (const c of cands) { 
        const f = low.find(x=>x.key === c); 
        if (f) return f.raw 
      }
      // Recherche par inclusion
      for (const c of cands) { 
        const f = low.find(x=>x.key.includes(c)); 
        if (f) return f.raw 
      }
      // Recherche par début
      for (const c of cands) { 
        const f = low.find(x=>x.key.startsWith(c)); 
        if (f) return f.raw 
      }
      return ''
    }
    
    return {
      label: find([
        'libellé', 'libelle', 'label', 'description', 'designation', 
        'intitulé', 'intitule', 'nom', 'name', 'titre', 'title',
        'desc', 'lib', 'libellé_activité', 'activité', 'activite'
      ]),
      code: find([
        'code_nacre', 'code', 'nacre', 'code_activité', 'code_activite',
        'cd_nacre', 'cd', 'classification', 'classe'
      ]),
      fournisseur: find([
        'fournisseur', 'supplier', 'vendor', 'vendeur', 'prestataire',
        'partenaire', 'entreprise', 'société', 'societe'
      ]),
      compte: find([
        'compte_comptable', 'compte', 'account', 'comptable',
        'cpt', 'num_compte', 'numero_compte'
      ]),
      montant: find([
        'montant', 'amount', 'valeur', 'prix', 'price', 'cout', 'coût',
        'total', 'somme', 'value', 'val'
      ]),
      confidence: find([
        'confiance', 'confidence', 'score', 'probabilité', 'probabilite',
        'certitude', 'fiabilité', 'fiabilite'
      ])
    }
  }

  const onSelectFile = async (f) => {
    setFile(f)
    if (!f) return
    // Read first line to get headers (adaptive to many columns)
    const txt = await f.text()
    const firstLine = txt.split(/\r?\n/)[0] || ''
    // detect delimiter ; or , or tab
    const candidates = [';','\t',',']
    let best = ','
    let bestCount = 0
    for (const d of candidates) {
      const c = firstLine.split(d).length
      if (c > bestCount) { bestCount = c; best = d }
    }
    const hs = firstLine.split(best).map(h=>h.trim())
    setHeaders(hs)
    const m = guessMap(hs)
    setMapping(m)
    setShowMap(true) // Toujours afficher le mapping pour permettre à l'utilisateur de vérifier/modifier
  }
  const onTrain = async () => {
    if (!file) return
    setBusy(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      if (Object.values(mapping).some(Boolean)) {
        fd.append('mapping_json', JSON.stringify(mapping))
      }
      let data = null
      try {
        const res = await fetch('/sophie/train/start', { method:'POST', body: fd })
        if (res.ok) {
          data = await res.json()
          setSummary(data)
          const timer = setInterval(async ()=>{
            try {
              const st = await fetch('/sophie/train/status')
              if (st.ok) {
                const s = await st.json()
                setStatus(s)
                if (!s.in_progress) { clearInterval(timer); setPoll(null) }
              }
            } catch {}
          }, 800)
          setPoll(timer)
          return
        }
      } catch (e) {
        // network/abort errors -> fallback
      }
      // Fallback legacy sync API
      try {
        const res2 = await fetch('/sophie/train', { method:'POST', body: fd })
        if (!res2.ok) { alert('Démarrage apprentissage échoué'); return }
        const data2 = await res2.json()
        setSummary(data2)
        setStatus({ in_progress:false, processed:data2.rows_processed||0, total:data2.rows_processed||0, errors:data2.errors||0 })
      } catch(e) {
        alert('Démarrage apprentissage échoué');
      }
    } finally { setBusy(false) }
  }
  const onCancel = async () => {
    await fetch('/sophie/train/cancel', { method:'POST' })
  }
  return (
    <div className="learning-section">
      <div className="learning-header">
        <h3>Apprentissage depuis un CSV annoté</h3>
        <p>Améliorez les performances de Sophie en important vos données de classification</p>
      </div>
      
      <div className="learning-content">
        <div className="file-upload-area">
          <input 
            type="file" 
            accept=".csv" 
            onChange={e => onSelectFile(e.target.files?.[0] || null)} 
            style={{display:'none'}} 
            id="learning-file-input" 
          />
          <label htmlFor="learning-file-input" className="file-upload-btn">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
              <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
            </svg>
            <div className="upload-content">
              <div className="upload-title">
                {file ? file.name : 'Sélectionner un fichier CSV'}
              </div>
              <div className="upload-subtitle">
                {file ? 'Fichier prêt pour l\'apprentissage' : 'Format CSV avec colonnes: libellé, code_nacre'}
              </div>
            </div>
          </label>
        </div>
        
        {file && (
          <div className="learning-actions">
            <button 
              className="btn btn-primary learning-start-btn" 
              onClick={onTrain} 
              disabled={busy || status.in_progress}
            >
              {busy ? (
                <>
                  <div className="loading-spinner"></div>
                  Analyse en cours...
                </>
              ) : (
                <>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M8,5.14V19.14L19,12.14L8,5.14Z"/>
                  </svg>
                  Lancer l'apprentissage
                </>
              )}
            </button>
            
            {status.in_progress && (
              <button className="btn btn-danger" onClick={onCancel}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z"/>
                </svg>
                Arrêter
              </button>
            )}
          </div>
        )}
        
        {file && showMap && (
          <div className="column-mapping-section">
            <div className="mapping-header">
              <h4>Configuration des colonnes</h4>
              <p>Vérifiez et ajustez le mapping des colonnes détectées</p>
            </div>
            <div className="mapping-grid">
              {Object.entries({
                label: 'Libellé/Description',
                code: 'Code NACRE',
                fournisseur: 'Fournisseur',
                compte: 'Compte comptable',
                montant: 'Montant',
                confidence: 'Score de confiance'
              }).map(([key, label]) => (
                <div key={key} className="mapping-item">
                  <label className="mapping-label">{label}</label>
                  <select 
                    value={mapping[key]} 
                    onChange={e => setMapping({...mapping, [key]: e.target.value})}
                    className="mapping-select"
                  >
                    <option value="">-- Non mappé --</option>
                    {headers.map(h => (
                      <option key={h} value={h}>{h}</option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
      
      {summary && (
        <div className="training-status animate-fade-in">
          <div className="flex justify-between text-sm">
            <span>Lignes traitées: <strong>{summary.rows_processed}</strong></span>
            <span>Erreurs: <strong>{summary.errors}</strong></span>
          </div>
          <div className="text-xs mt-2" style={{ color: 'var(--muted)' }}>
            Colonnes détectées: 
            {Object.entries({
              label: summary.detected_columns?.label,
              code: summary.detected_columns?.code,
              fournisseur: summary.detected_columns?.fournisseur,
              compte: summary.detected_columns?.compte,
              montant: summary.detected_columns?.montant
            }).map(([key, value]) => (
              <span key={key} className="badge" style={{ margin: '0 4px' }}>
                {key}: {value || '—'}
              </span>
            ))}
          </div>
        </div>
      )}
      
      <div className="training-status">
        <div className="training-progress">
          <span>
            {status.in_progress ? 'En cours' : (status.canceled ? 'Annulé' : 'Terminé')}
          </span>
          <span className="text-sm">
            {status.processed}/{status.total} (erreurs: {status.errors})
          </span>
        </div>
        <div className="training-progress-bar">
          <div 
            className="training-progress-fill" 
            style={{ width: `${status.total ? Math.floor((status.processed/status.total)*100) : 0}%` }}
          />
        </div>
      </div>
    </div>
  )
}

function MappingModal({ headers, mapping, setMapping, onClose }) {
  if (!headers?.length) return null
  const Row = ({label, keyName}) => (
    <div className="row">
      <label>{label}</label>
      <select className="select" value={mapping[keyName]||''} onChange={e=>setMapping(m=>({...m, [keyName]: e.target.value}))}>
        <option value="">— non défini —</option>
        {headers.map(h=> <option key={h} value={h}>{h}</option>)}
      </select>
    </div>
  )
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e=>e.stopPropagation()}>
        <h3>Mapper les colonnes du CSV annoté</h3>
        <div className="grid2">
          <Row label="Libellé (Description)" keyName="label" />
          <Row label="Code NACRE" keyName="code" />
          <Row label="Fournisseur" keyName="fournisseur" />
          <Row label="Compte comptable" keyName="compte" />
          <Row label="Montant" keyName="montant" />
          <Row label="Confiance (%)" keyName="confidence" />
        </div>
        <div className="actions">
          <button className="btn" onClick={onClose}>Fermer</button>
        </div>
      </div>
    </div>
  )
}

function CarbonVisualizationModal({ data, onClose }) {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [screenshotting, setScreenshotting] = useState(false)

  // Fonction pour prendre une capture d'écran
  const takeScreenshot = async (vizType) => {
    setScreenshotting(true)
    try {
      // Utiliser l'API native de Plotly pour l'export
      if (window.Plotly) {
        const plotElement = document.getElementById(`plotly-${vizType}`)
        if (!plotElement) {
          alert('Graphique non trouvé')
          return
        }

        // Export en image avec Plotly
        const imgData = await window.Plotly.toImage(plotElement, {
          format: 'jpeg',
          width: 1200,
          height: 800,
          scale: 2
        })

        // Créer un lien de téléchargement
        const link = document.createElement('a')
        link.download = `carbon_analysis_${vizType}_${new Date().getTime()}.jpg`
        link.href = imgData
        link.click()
      } else {
        alert('Plotly n\'est pas chargé')
      }
    } catch (error) {
      console.error('Erreur lors de la capture:', error)
      alert('Erreur lors de la capture d\'écran: ' + error.message)
    } finally {
      setScreenshotting(false)
    }
  }

  const renderVisualization = (vizType, vizData) => {
    if (!vizData || vizData.error) {
      return (
        <div className="viz-error">
          <p>Erreur: {vizData?.error || 'Données non disponibles'}</p>
        </div>
      )
    }

    return (
      <div id={`viz-${vizType}`} className="visualization-container">
        <div className="viz-header">
          <h3>{getVizTitle(vizType)}</h3>
          <button 
            className="btn btn-secondary screenshot-btn"
            onClick={() => takeScreenshot(vizType)}
            disabled={screenshotting}
          >
            {screenshotting ? 'Capture...' : '📷 Capturer'}
          </button>
        </div>
        <div className="plotly-div" id={`plotly-${vizType}`}>
          {/* Plotly sera injecté ici via JavaScript */}
        </div>
      </div>
    )
  }

  const getVizTitle = (type) => {
    const titles = {
      dashboard: 'Dashboard Complet',
      heatmap: 'Heatmap des Émissions',
      '3d_visualization': 'Visualisation 3D',
      neural_network: 'Analyse par Réseau de Neurones',
      clustering: 'Clustering Hiérarchique'
    }
    return titles[type] || type
  }

  // Effet pour charger Plotly et afficher les graphiques
  useEffect(() => {
    if (!data?.visualizations) return

    // Charger Plotly.js dynamiquement
    const loadPlotly = async () => {
      if (!window.Plotly) {
        const script = document.createElement('script')
        script.src = 'https://cdn.plot.ly/plotly-latest.min.js'
        document.head.appendChild(script)
        
        await new Promise((resolve) => {
          script.onload = resolve
        })
      }

      // Afficher le graphique actif
      const vizData = data.visualizations[activeTab]
      if (vizData && vizData.figure && window.Plotly) {
        const plotElement = document.getElementById(`plotly-${activeTab}`)
        if (plotElement) {
          window.Plotly.newPlot(
            `plotly-${activeTab}`,
            vizData.figure.data,
            vizData.figure.layout,
            vizData.config
          )
        }
      }
    }

    loadPlotly()
  }, [data, activeTab])

  return (
    <div className="carbon-viz-modal">
      <div className="modal-overlay" onClick={onClose}></div>
      <div className="modal-content viz-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Visualisations d'Analyse Carbone</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        
        <div className="modal-body">
          {/* Résumé des résultats */}
          <div className="analysis-summary">
            <div className="summary-card">
              <h4>Émissions Totales</h4>
              <p className="metric-value">
                {data.carbon_analysis?.total_co2_emission?.toFixed(2) || 0} kg CO₂
              </p>
            </div>
            <div className="summary-card">
              <h4>Montant Total</h4>
              <p className="metric-value">
                {data.carbon_analysis?.total_amount?.toLocaleString() || 0} €
              </p>
            </div>
            <div className="summary-card">
              <h4>Catégories</h4>
              <p className="metric-value">
                {Object.keys(data.category_stats || {}).length}
              </p>
            </div>
          </div>

          {/* Onglets de visualisation */}
          <div className="viz-tabs">
            {Object.entries(data.visualizations || {}).map(([type, vizData]) => (
              <button
                key={type}
                className={`tab-btn ${activeTab === type ? 'active' : ''}`}
                onClick={() => setActiveTab(type)}
              >
                {getVizTitle(type)}
              </button>
            ))}
          </div>

          {/* Contenu de visualisation */}
          <div className="viz-content">
            {data.visualizations && data.visualizations[activeTab] && 
              renderVisualization(activeTab, data.visualizations[activeTab])
            }
          </div>
        </div>
      </div>
    </div>
  )
}
