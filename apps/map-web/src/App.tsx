import { useEffect, useRef, useState } from 'react'
import * as maplibregl from 'maplibre-gl'
import type { Map as MapLibreMap, MapLayerMouseEvent } from 'maplibre-gl'
import { Protocol } from 'pmtiles'
import {
  contributionFeatures,
  loadContributionCells,
  PRIOR_LAYERS,
  priorSource,
  type PriorLayerId,
} from './mapData'
import 'maplibre-gl/dist/maplibre-gl.css'

let protocolRegistered = false

function registerPmtiles() {
  if (protocolRegistered) return
  const protocol = new Protocol()
  maplibregl.addProtocol('pmtiles', protocol.tile)
  protocolRegistered = true
}

export function App() {
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const [activeLayer, setActiveLayer] = useState<PriorLayerId>('soc')
  const [mapStatus, setMapStatus] = useState('Loading public soil layers…')

  useEffect(() => {
    if (!container.current) return
    registerPmtiles()
    const map = new maplibregl.Map({
      attributionControl: false,
      center: [8, 12],
      container: container.current,
      maxZoom: 12,
      minZoom: 1,
      style: {
        layers: [
          {
            id: 'background',
            paint: { 'background-color': '#132822' },
            type: 'background',
          },
        ],
        sources: {},
        version: 8,
      },
      zoom: 1.7,
    })
    mapRef.current = map
    map.addControl(
      new maplibregl.NavigationControl({ showCompass: false }),
      'bottom-right',
    )
    map.addControl(
      new maplibregl.AttributionControl({
        compact: true,
        customAttribution:
          'SoilGrids © ISRIC, CC BY 4.0 · Contributions are H3-fuzzed',
      }),
      'bottom-right',
    )
    map.on('load', () => {
      for (const layer of PRIOR_LAYERS) {
        map.addSource(`prior-${layer.id}`, priorSource(layer))
        map.addLayer({
          id: `prior-${layer.id}`,
          layout: { visibility: layer.id === 'soc' ? 'visible' : 'none' },
          maxzoom: 13,
          paint: { 'raster-opacity': 0.78, 'raster-resampling': 'linear' },
          source: `prior-${layer.id}`,
          type: 'raster',
        })
      }
      map.addSource('contributions', {
        data: contributionFeatures([]),
        type: 'geojson',
      })
      map.addLayer({
        id: 'contribution-density',
        paint: {
          'fill-color': [
            'interpolate',
            ['linear'],
            ['get', 'count'],
            1,
            '#f7d873',
            5,
            '#ed8b42',
            20,
            '#cf4d3f',
          ],
          'fill-opacity': 0.78,
          'fill-outline-color': '#fff4c2',
        },
        source: 'contributions',
        type: 'fill',
      })
      map.on('click', 'contribution-density', (event: MapLayerMouseEvent) => {
        const feature = event.features?.[0]
        if (!feature) return
        const count = Number(feature.properties?.count ?? 0)
        const latest = String(feature.properties?.latest ?? 'Unknown')
        new maplibregl.Popup({ closeButton: false })
          .setLngLat(event.lngLat)
          .setHTML(
            `<strong>${count} contribution${count === 1 ? '' : 's'}</strong><br>Latest: ${latest}`,
          )
          .addTo(map)
      })
      map.on('mouseenter', 'contribution-density', () => {
        map.getCanvas().style.cursor = 'pointer'
      })
      map.on('mouseleave', 'contribution-density', () => {
        map.getCanvas().style.cursor = ''
      })
      void loadContributionCells()
        .then((cells) => {
          const source = map.getSource(
            'contributions',
          ) as maplibregl.GeoJSONSource
          source.setData(contributionFeatures(cells))
          setMapStatus(
            cells.length
              ? `${cells.length} public H3 cells loaded. No precise points are shown.`
              : 'No QA-passed public contributions yet.',
          )
        })
        .catch(() => {
          setMapStatus(
            'Contribution layer unavailable. No placeholder data is shown.',
          )
        })
    })
    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [])

  function chooseLayer(id: PriorLayerId) {
    setActiveLayer(id)
    const map = mapRef.current
    if (!map?.isStyleLoaded()) return
    for (const layer of PRIOR_LAYERS)
      map.setLayoutProperty(
        `prior-${layer.id}`,
        'visibility',
        layer.id === id ? 'visible' : 'none',
      )
  }

  const selected = PRIOR_LAYERS.find((layer) => layer.id === activeLayer)!
  return (
    <main className="map-shell">
      <div
        ref={container}
        className="map-canvas"
        aria-label="Interactive global soil map"
      />
      <header className="map-header">
        <a
          className="brand"
          href="../"
          aria-label="Global Soil Intelligence home"
        >
          <span className="brand-mark">G</span>
          <span>Global Soil Intelligence</span>
        </a>
        <a className="contribute" href="../capture/">
          Contribute an observation
        </a>
      </header>

      <section className="map-intro" aria-labelledby="map-title">
        <p className="eyebrow">Open soil context</p>
        <h1 id="map-title">Read the ground globally.</h1>
        <p>
          Explore SoilGrids priors alongside privacy-preserving community
          coverage. Zooming past level 8 overzooms the same native soil tiles—no
          false precision is introduced.
        </p>
      </section>

      <section className="layer-panel" aria-label="Map layers">
        <p className="panel-label">Soil property</p>
        <div className="layer-buttons">
          {PRIOR_LAYERS.map((layer) => (
            <button
              aria-pressed={activeLayer === layer.id}
              key={layer.id}
              onClick={() => chooseLayer(layer.id)}
              type="button"
            >
              <span>{layer.label}</span>
              <small>{layer.unit}</small>
            </button>
          ))}
        </div>
        <div
          className={`legend legend-${activeLayer}`}
          aria-label={`${selected.label} legend`}
        >
          <span>{selected.low}</span>
          <i />
          <span>{selected.high}</span>
        </div>
        <p className="map-status" aria-live="polite">
          {mapStatus}
        </p>
      </section>
    </main>
  )
}
