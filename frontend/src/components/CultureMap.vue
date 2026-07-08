<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

import exhibitionMarkerUrl from '../assets/map-markers/exhibition-bubble.png'
import festivalMarkerUrl from '../assets/map-markers/festival-bubble.png'
import performanceMarkerUrl from '../assets/map-markers/performance-bubble.png'
import koreaProvinces from '../assets/korea-provinces.geo.json'
import { loadKakaoMap } from '../utils/loadKakaoMap'


const emit = defineEmits(['select-region', 'select-event', 'select-category', 'browse-more', 'open-event'])

const props = defineProps({
  compact: { type: Boolean, default: false },
  items: { type: Array, default: () => [] },
  regionSummaries: { type: Array, default: () => [] },
})

const REGION_META = [
  { area: '서울', name: '서울특별시', center: [37.5665, 126.9780], label: [37.69, 126.98] },
  { area: '부산', name: '부산광역시', center: [35.1796, 129.0756], label: [35.08, 129.22] },
  { area: '대구', name: '대구광역시', center: [35.8714, 128.6014], label: [35.88, 128.47] },
  { area: '인천', name: '인천광역시', center: [37.4563, 126.7052], label: [37.45, 126.35] },
  { area: '광주', name: '광주광역시', center: [35.1595, 126.8526], label: [35.2, 126.7] },
  { area: '대전', name: '대전광역시', center: [36.3504, 127.3845], label: [36.25, 127.43] },
  { area: '울산', name: '울산광역시', center: [35.5384, 129.3114], label: [35.61, 129.43] },
  { area: '세종', name: '세종특별자치시', center: [36.4800, 127.2890], label: [36.55, 127.08] },
  { area: '경기', name: '경기도', center: [37.4138, 127.5183], label: [37.25, 127.2] },
  { area: '강원', name: '강원특별자치도', center: [37.8228, 128.1555], label: [37.72, 128.5] },
  { area: '충북', name: '충청북도', center: [36.6357, 127.4917], label: [36.82, 127.72] },
  { area: '충남', name: '충청남도', center: [36.6588, 126.6728], label: [36.5, 126.55] },
  { area: '전북', name: '전북특별자치도', center: [35.8203, 127.1088], label: [35.88, 127.03] },
  { area: '전남', name: '전라남도', center: [34.8161, 126.4629], label: [34.85, 126.55] },
  { area: '경북', name: '경상북도', center: [36.4919, 128.8889], label: [36.42, 128.85] },
  { area: '경남', name: '경상남도', center: [35.4606, 128.2132], label: [35.35, 128.08] },
  { area: '제주', name: '제주특별자치도', center: [33.4890, 126.4983], label: [33.43, 126.55] },
]
const REGION_BY_AREA = Object.fromEntries(REGION_META.map((region) => [region.area, region]))
const REGION_NAME_TO_AREA = Object.fromEntries(REGION_META.map((region) => [region.name, region.area]))
Object.assign(REGION_NAME_TO_AREA, {
  강원도: '강원', 전라북도: '전북', 제주도: '제주', 세종시: '세종',
})

const MAP_CATEGORIES = [
  ['', '전체'],
  ['공연', '공연'],
  ['전시', '전시'],
  ['축제·행사', '축제·행사'],
]
const MARKER_URLS = {
  공연: performanceMarkerUrl,
  전시: exhibitionMarkerUrl,
  '축제·행사': festivalMarkerUrl,
}
const PANEL_ITEM_LIMIT = 20
const REGION_FOCUS_SCALE = { 경북: 0.72 }
const SVG_VIEWBOX = { width: 960, height: 600 }
const SVG_BOUNDS = { minLng: 124.5, maxLng: 130.0, minLat: 33.0, maxLat: 38.7 }
const SVG_MAP_BOX = { x: 245, y: 24, width: 470, height: 540 }
const REGION_CALLOUTS = {
  서울: { side: 'left', y: 56 }, 인천: { side: 'left', y: 111 },
  경기: { side: 'left', y: 166 }, 세종: { side: 'left', y: 221 },
  충남: { side: 'left', y: 276 }, 대전: { side: 'left', y: 331 },
  전북: { side: 'left', y: 386 }, 광주: { side: 'left', y: 441 },
  전남: { side: 'left', y: 496 }, 강원: { side: 'right', y: 56 },
  충북: { side: 'right', y: 121 }, 경북: { side: 'right', y: 186 },
  대구: { side: 'right', y: 251 }, 울산: { side: 'right', y: 316 },
  경남: { side: 'right', y: 381 }, 부산: { side: 'right', y: 446 },
  제주: { side: 'right', y: 521 },
}

const mapContainer = ref(null)
const loading = ref(false)
const error = ref('')
const selectedRegion = ref(null)
const selectedEvent = ref(null)
const selectedCategory = ref('')
const transitionRegion = ref(null)
const regionTransitioning = ref(false)
const hoveredMarkerKey = ref('')
let regionTransitionTimer = null
let markerTooltipHideTimer = null
let kakaoApi = null
let map = null
let regionOverlays = []
let regionConnectors = []
let regionPolygons = []
let polygonGroups = new Map()
let markers = []
let markerImages = {}
let markerTooltip = null
let markerTooltipElement = null
let markerRenderId = 0
const geocodeCache = new Map()
const mapPositions = new Map()

const countsByRegion = computed(() => Object.fromEntries(
  props.regionSummaries.map(({ area, count }) => [area, count]),
))
const visibleRegions = computed(() => REGION_META.map((region) => ({
  ...region,
  count: countsByRegion.value[region.area] || 0,
})))
const panelItems = computed(() => {
  if (!selectedEvent.value) return props.items.slice(0, PANEL_ITEM_LIMIT)
  return [
    selectedEvent.value,
    ...props.items.filter((item) => item.seq !== selectedEvent.value.seq),
  ].slice(0, PANEL_ITEM_LIMIT)
})
const hasMoreItems = computed(() => props.items.length > PANEL_ITEM_LIMIT)

function projectSvgPoint(lng, lat) {
  const xRatio = (lng - SVG_BOUNDS.minLng) / (SVG_BOUNDS.maxLng - SVG_BOUNDS.minLng)
  const yRatio = (SVG_BOUNDS.maxLat - lat) / (SVG_BOUNDS.maxLat - SVG_BOUNDS.minLat)
  return {
    x: SVG_MAP_BOX.x + xRatio * SVG_MAP_BOX.width,
    y: SVG_MAP_BOX.y + yRatio * SVG_MAP_BOX.height,
  }
}

function svgGeometryPath(geometry) {
  const polygons = geometryPaths(geometry)
  return svgPolygonsPath(polygons)
}

function svgPolygonsPath(polygons, offset = { x: 0, y: 0 }) {
  return polygons.map((polygon) => polygon.map((ring) => ring.map(([lng, lat], index) => {
    const projected = projectSvgPoint(lng, lat)
    const point = { x: projected.x + offset.x, y: projected.y + offset.y }
    return `${index ? 'L' : 'M'}${point.x.toFixed(1)},${point.y.toFixed(1)}`
  }).join(' ') + ' Z').join(' ')).join(' ')
}

function polygonProjectedBounds(polygon) {
  const points = polygon.flat().map(([lng, lat]) => projectSvgPoint(lng, lat))
  const xs = points.map(({ x }) => x)
  const ys = points.map(({ y }) => y)
  return {
    minX: Math.min(...xs), maxX: Math.max(...xs),
    minY: Math.min(...ys), maxY: Math.max(...ys),
  }
}

function focusedRegionGeometry(geometry, area) {
  if (area !== '경북' || geometry.type !== 'MultiPolygon' || geometry.coordinates.length < 2) {
    return { path: svgGeometryPath(geometry), geometry, islands: null }
  }

  const mainland = geometry.coordinates[0]
  const ulleungdo = geometry.coordinates[1]
  const mainlandBounds = polygonProjectedBounds(mainland)
  const ulleungBounds = polygonProjectedBounds(ulleungdo)
  const mainlandWidth = mainlandBounds.maxX - mainlandBounds.minX
  const mainlandHeight = mainlandBounds.maxY - mainlandBounds.minY
  const ulleungCenter = {
    x: (ulleungBounds.minX + ulleungBounds.maxX) / 2,
    y: (ulleungBounds.minY + ulleungBounds.maxY) / 2,
  }
  const insetCenter = {
    x: mainlandBounds.maxX + mainlandWidth * 0.12,
    y: mainlandBounds.minY + mainlandHeight * 0.28,
  }
  const offset = {
    x: insetCenter.x - ulleungCenter.x,
    y: insetCenter.y - ulleungCenter.y,
  }
  const dokdo = {
    x: insetCenter.x + mainlandWidth * 0.085,
    y: insetCenter.y + mainlandHeight * 0.035,
    radius: Math.max(mainlandWidth * 0.008, 1.2),
  }

  return {
    path: `${svgPolygonsPath([mainland])} ${svgPolygonsPath([ulleungdo], offset)}`,
    geometry: { type: 'Polygon', coordinates: mainland },
    islands: { ulleungdo: insetCenter, dokdo, labelSize: Math.max(mainlandWidth / 30, 3.4) },
  }
}

const svgRegions = computed(() => koreaProvinces.features.map((feature) => {
  const area = REGION_NAME_TO_AREA[feature.properties?.name]
  const region = REGION_BY_AREA[area]
  if (!region) return null
  const center = projectSvgPoint(region.center[1], region.center[0])
  const callout = REGION_CALLOUTS[area]
  const focused = focusedRegionGeometry(feature.geometry, area)
  return {
    ...region,
    count: countsByRegion.value[area] || 0,
    path: svgGeometryPath(feature.geometry),
    geometry: feature.geometry,
    focusPath: focused.path,
    focusGeometry: focused.geometry,
    islands: focused.islands,
    center,
    callout: {
      ...callout,
      x: callout.side === 'left' ? 28 : 764,
      width: 168,
      anchorX: callout.side === 'left' ? 196 : 764,
    },
  }
}).filter(Boolean))

const selectedSvgRegion = computed(() => (
  selectedRegion.value
    ? svgRegions.value.find((region) => region.area === selectedRegion.value.area) || null
    : null
))

const transitionSvgRegion = computed(() => (
  transitionRegion.value
    ? svgRegions.value.find((region) => region.area === transitionRegion.value.area) || null
    : null
))

function geometryProjectedBounds(geometry) {
  const points = geometryPaths(geometry).flat(2).map(([lng, lat]) => projectSvgPoint(lng, lat))
  if (!points.length) return { x: 0, y: 0, width: SVG_VIEWBOX.width, height: SVG_VIEWBOX.height }
  const xs = points.map(({ x }) => x)
  const ys = points.map(({ y }) => y)
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  const width = Math.max(maxX - minX, 28)
  const height = Math.max(maxY - minY, 28)
  const padding = Math.max(width, height) * 0.18
  return {
    x: minX - padding,
    y: minY - padding,
    width: width + padding * 2,
    height: height + padding * 2,
  }
}

const selectedSvgBounds = computed(() => (
  selectedSvgRegion.value
    ? geometryProjectedBounds(selectedSvgRegion.value.geometry)
    : { x: 0, y: 0, width: SVG_VIEWBOX.width, height: SVG_VIEWBOX.height }
))

const selectedSvgViewBox = computed(() => {
  const bounds = selectedSvgBounds.value
  return `${bounds.x} ${bounds.y} ${bounds.width} ${bounds.height}`
})

const selectedRegionDecorations = computed(() => {
  const bounds = selectedSvgBounds.value
  const x = bounds.x
  const y = bounds.y
  const w = bounds.width
  const h = bounds.height

  return {
    roads: [
      [
        { x: x + w * 0.16, y: y + h * 0.36 },
        { x: x + w * 0.33, y: y + h * 0.31 },
        { x: x + w * 0.54, y: y + h * 0.43 },
        { x: x + w * 0.76, y: y + h * 0.33 },
      ],
      [
        { x: x + w * 0.27, y: y + h * 0.73 },
        { x: x + w * 0.43, y: y + h * 0.58 },
        { x: x + w * 0.61, y: y + h * 0.67 },
        { x: x + w * 0.83, y: y + h * 0.56 },
      ],
      [
        { x: x + w * 0.47, y: y + h * 0.22 },
        { x: x + w * 0.49, y: y + h * 0.46 },
        { x: x + w * 0.39, y: y + h * 0.77 },
      ],
    ],
    icons: [
      { type: 'house', x: x + w * 0.29, y: y + h * 0.45, size: Math.max(w, h) * 0.045 },
      { type: 'tree', x: x + w * 0.66, y: y + h * 0.31, size: Math.max(w, h) * 0.042 },
      { type: 'pond', x: x + w * 0.37, y: y + h * 0.66, size: Math.max(w, h) * 0.052 },
      { type: 'tower', x: x + w * 0.56, y: y + h * 0.55, size: Math.max(w, h) * 0.046 },
      { type: 'tree', x: x + w * 0.73, y: y + h * 0.68, size: Math.max(w, h) * 0.04 },
      { type: 'house', x: x + w * 0.48, y: y + h * 0.28, size: Math.max(w, h) * 0.038 },
    ],
  }
})

function regionFocusTransform(region) {
  if (!region) return { matrix: '1 0 0 1 0 0', scale: 1, translateX: 0, translateY: 0 }
  const bounds = geometryProjectedBounds(region.focusGeometry || region.geometry)
  const rawWidth = Math.max(bounds.width / 1.36, 18)
  const rawHeight = Math.max(bounds.height / 1.36, 18)
  const scale = Math.min(620 / rawWidth, 520 / rawHeight) * (REGION_FOCUS_SCALE[region.area] || 1)
  const centerX = bounds.x + bounds.width / 2
  const centerY = bounds.y + bounds.height / 2
  const translateX = 145 - scale * centerX
  const translateY = 280 - scale * centerY
  return {
    scale,
    translateX,
    translateY,
    matrix: `${scale.toFixed(4)} 0 0 ${scale.toFixed(4)} ${translateX.toFixed(2)} ${translateY.toFixed(2)}`,
  }
}

const transitionSvgTransform = computed(() => regionFocusTransform(transitionSvgRegion.value))
const selectedSvgTransform = computed(() => regionFocusTransform(selectedSvgRegion.value))

const transitionSvgMatrix = computed(() => {
  return `1 0 0 1 0 0; ${transitionSvgTransform.value.matrix}`
})

const regionalEventMarkers = computed(() => {
  if (!selectedSvgRegion.value) return []
  const bounds = selectedSvgBounds.value
  const cellWidth = bounds.width / 16
  const cellHeight = bounds.height / 12
  const clusters = new Map()

  props.items.forEach((item) => {
    const rawLat = item.place?.latitude
    const rawLng = item.place?.longitude
    if (rawLat == null || rawLat === '' || rawLng == null || rawLng === '') return
    const lat = Number(rawLat)
    const lng = Number(rawLng)
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return
    const point = projectSvgPoint(lng, lat)
    const column = Math.floor((point.x - bounds.x) / cellWidth)
    const row = Math.floor((point.y - bounds.y) / cellHeight)
    const key = `${column}:${row}`
    if (!clusters.has(key)) clusters.set(key, [])
    clusters.get(key).push({ item, point })
  })

  return [...clusters.entries()].map(([key, entries]) => {
    const categories = entries.reduce((result, { item }) => {
      result[item.main_category] = (result[item.main_category] || 0) + 1
      return result
    }, {})
    const category = Object.entries(categories).sort((a, b) => b[1] - a[1])[0]?.[0] || '축제·행사'
    const titles = entries.slice(0, 3).map(({ item }) => item.title).join(', ')
    return {
      key,
      item: entries[0].item,
      items: entries.map(({ item }) => item),
      count: entries.length,
      category,
      x: entries.reduce((sum, entry) => sum + entry.point.x, 0) / entries.length,
      y: entries.reduce((sum, entry) => sum + entry.point.y, 0) / entries.length,
      label: entries.length > 1 ? `${entries.length}개 행사: ${titles}` : titles,
    }
  })
})

const regionalMarkerSize = computed(() => (
  Math.max(selectedSvgBounds.value.width, selectedSvgBounds.value.height) / 39
))

const hoveredRegionalMarker = computed(() => (
  regionalEventMarkers.value.find((marker) => marker.key === hoveredMarkerKey.value) || null
))

const regionalTooltipPosition = computed(() => {
  const marker = hoveredRegionalMarker.value
  if (!marker) return { x: 0, y: 0 }
  const transform = selectedSvgTransform.value
  const markerX = marker.x * transform.scale + transform.translateX
  const markerY = (marker.y - regionalMarkerSize.value * 2.5) * transform.scale + transform.translateY
  return {
    x: markerX > 430 ? Math.max(markerX - 232, 12) : Math.min(markerX + 14, 500),
    y: Math.min(Math.max(markerY - 16, 12), 350),
  }
})

function clearRegionLabels() {
  regionOverlays.forEach((overlay) => overlay.setMap(null))
  regionConnectors.forEach((connector) => connector.setMap(null))
  regionOverlays = []
  regionConnectors = []
}

function clearRegionPolygons() {
  regionPolygons.forEach((polygon) => polygon.setMap(null))
  regionPolygons = []
  polygonGroups = new Map()
}

function clearMarkers(invalidatePendingRender = true) {
  if (invalidatePendingRender) markerRenderId += 1
  markers.forEach(({ marker }) => marker.setMap(null))
  markers = []
  mapPositions.clear()
  markerTooltip?.setMap(null)
}

function clearAllLayers() {
  clearRegionLabels()
  clearRegionPolygons()
  clearMarkers()
}

function polygonStyle(area, hovered = false) {
  const selected = selectedRegion.value?.area === area
  const muted = selectedRegion.value && !selected
  return {
    strokeWeight: hovered || selected ? 5 : 3,
    strokeColor: hovered ? '#ef6b3a' : selected ? '#1f6f52' : '#356b5a',
    strokeOpacity: muted ? 0.3 : 0.92,
    strokeStyle: 'solid',
    fillColor: hovered ? '#f8c9ac' : selected ? '#a8d9c4' : '#dceee4',
    fillOpacity: muted ? 0.03 : hovered ? 0.3 : selected ? 0.24 : 0.1,
  }
}

function setPolygonGroupStyle(area, hovered = false) {
  polygonGroups.get(area)?.forEach((polygon) => polygon.setOptions(polygonStyle(area, hovered)))
}

function updatePolygonStyles() {
  REGION_META.forEach(({ area }) => setPolygonGroupStyle(area))
}

function geometryPaths(geometry) {
  if (geometry.type === 'Polygon') return [geometry.coordinates]
  if (geometry.type === 'MultiPolygon') return geometry.coordinates
  return []
}

function renderRegionPolygons() {
  if (!map || !kakaoApi) return
  clearRegionPolygons()

  koreaProvinces.features.forEach((feature) => {
    const area = REGION_NAME_TO_AREA[feature.properties?.name]
    const region = REGION_BY_AREA[area]
    if (!region) return

    const polygons = geometryPaths(feature.geometry).map((polygonCoordinates) => {
      const paths = polygonCoordinates.map((ring) => ring.map(([lng, lat]) => (
        new kakaoApi.maps.LatLng(lat, lng)
      )))
      const polygon = new kakaoApi.maps.Polygon({
        map,
        path: paths,
        ...polygonStyle(area),
      })
      kakaoApi.maps.event.addListener(polygon, 'click', () => selectRegion(region))
      kakaoApi.maps.event.addListener(polygon, 'mouseover', () => setPolygonGroupStyle(area, true))
      kakaoApi.maps.event.addListener(polygon, 'mouseout', () => setPolygonGroupStyle(area))
      regionPolygons.push(polygon)
      return polygon
    })
    polygonGroups.set(area, polygons)
  })
}

function createRegionBadge(region) {
  const button = document.createElement('button')
  button.type = 'button'
  button.className = `culture-region-badge${region.count ? '' : ' is-empty'}`
  button.setAttribute('aria-label', `${region.name} 문화행사 ${region.count.toLocaleString()}건`)

  const name = document.createElement('strong')
  name.textContent = region.area
  const count = document.createElement('span')
  count.textContent = `${region.count.toLocaleString()}건`
  button.append(name, count)
  button.addEventListener('click', () => selectRegion(region))
  return button
}

function renderRegionLabels() {
  if (!map || !kakaoApi || selectedRegion.value) return
  clearRegionLabels()

  visibleRegions.value.forEach((region) => {
    const [centerLat, centerLng] = region.center
    const [labelLat, labelLng] = region.label
    const labelPosition = new kakaoApi.maps.LatLng(labelLat, labelLng)
    const overlay = new kakaoApi.maps.CustomOverlay({
      map,
      position: labelPosition,
      content: createRegionBadge(region),
      xAnchor: 0.5,
      yAnchor: 0.5,
      zIndex: 4,
    })
    regionOverlays.push(overlay)

    if (Math.abs(centerLat - labelLat) + Math.abs(centerLng - labelLng) > 0.12) {
      regionConnectors.push(new kakaoApi.maps.Polyline({
        map,
        path: [new kakaoApi.maps.LatLng(centerLat, centerLng), labelPosition],
        strokeWeight: 2,
        strokeColor: '#447564',
        strokeOpacity: 0.62,
        strokeStyle: 'shortdot',
      }))
    }
  })
}

function renderRegions() {
  renderRegionPolygons()
  renderRegionLabels()
}

function findPlacePosition(item) {
  const cached = geocodeCache.get(item.seq)
  if (cached !== undefined) return Promise.resolve(cached)

  const placeName = item.place?.place_name
  if (!placeName || !kakaoApi?.maps?.services) return Promise.resolve(null)

  const query = [item.place?.area, item.place?.sigungu, placeName].filter(Boolean).join(' ')
  const places = new kakaoApi.maps.services.Places()
  return new Promise((resolve) => {
    places.keywordSearch(query, (results, status) => {
      const result = status === kakaoApi.maps.services.Status.OK ? results[0] : null
      const position = result ? { lat: Number(result.y), lng: Number(result.x) } : null
      geocodeCache.set(item.seq, position)
      resolve(position)
    })
  })
}

function markerCategory(item) {
  return MARKER_URLS[item.main_category] ? item.main_category : '축제·행사'
}

function buildMarkerImages() {
  markerImages = {}
  Object.entries(MARKER_URLS).forEach(([category, url]) => {
    markerImages[category] = {
      normal: new kakaoApi.maps.MarkerImage(
        url,
        new kakaoApi.maps.Size(44, 52),
        { offset: new kakaoApi.maps.Point(22, 51) },
      ),
      selected: new kakaoApi.maps.MarkerImage(
        url,
        new kakaoApi.maps.Size(52, 61),
        { offset: new kakaoApi.maps.Point(26, 60) },
      ),
    }
  })
}

function showMarkerTooltip(item, position) {
  if (!markerTooltipElement) return
  markerTooltipElement.textContent = item.title
  markerTooltip.setPosition(position)
  markerTooltip.setMap(map)
}

function hideMarkerTooltip() {
  markerTooltip?.setMap(null)
}

function updateSelectedMarker() {
  markers.forEach(({ marker, item, category }) => {
    const selected = selectedEvent.value?.seq === item.seq
    marker.setImage(markerImages[category][selected ? 'selected' : 'normal'])
    marker.setZIndex(selected ? 8 : 2)
  })
}

async function renderMarkers() {
  if (!map || !kakaoApi || !selectedRegion.value) return
  const currentRenderId = ++markerRenderId
  clearMarkers(false)
  const bounds = new kakaoApi.maps.LatLngBounds()

  const resolvedItems = await Promise.all(props.items.map(async (item) => {
    const rawLat = item.place?.latitude
    const rawLng = item.place?.longitude
    let lat = rawLat == null || rawLat === '' ? NaN : Number(rawLat)
    let lng = rawLng == null || rawLng === '' ? NaN : Number(rawLng)
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      const found = await findPlacePosition(item)
      lat = found?.lat
      lng = found?.lng
    }
    return { item, lat, lng }
  }))

  if (currentRenderId !== markerRenderId || !selectedRegion.value) return
  resolvedItems.forEach(({ item, lat, lng }) => {
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return
    const position = new kakaoApi.maps.LatLng(lat, lng)
    const category = markerCategory(item)
    const marker = new kakaoApi.maps.Marker({
      map,
      position,
      title: item.title,
      image: markerImages[category].normal,
    })
    kakaoApi.maps.event.addListener(marker, 'click', () => selectEvent(item))
    kakaoApi.maps.event.addListener(marker, 'mouseover', () => showMarkerTooltip(item, position))
    kakaoApi.maps.event.addListener(marker, 'mouseout', hideMarkerTooltip)
    markers.push({ marker, item, category })
    mapPositions.set(item.seq, { lat, lng })
    bounds.extend(position)
  })

  if (markers.length) map.setBounds(bounds, 70, 70, 70, 70)
  updateSelectedMarker()
}

async function selectRegion(region) {
  if (selectedRegion.value?.area === region.area || regionTransitioning.value) return
  transitionRegion.value = region
  regionTransitioning.value = true
  selectedEvent.value = null
  hoveredMarkerKey.value = ''
  clearMarkers()
  emit('select-region', region.area, selectedCategory.value)
  await new Promise((resolve) => {
    regionTransitionTimer = window.setTimeout(resolve, 620)
  })
  selectedRegion.value = region
  regionTransitioning.value = false
  transitionRegion.value = null
  regionTransitionTimer = null
  await nextTick()
}

async function selectEvent(item) {
  hoveredMarkerKey.value = ''
  selectedEvent.value = item
  hideMarkerTooltip()
  updateSelectedMarker()
  emit('select-event', item)
  await nextTick()
  if (!map) return
  map.relayout()
  const position = mapPositions.get(item.seq)
  if (position) map.panTo(new kakaoApi.maps.LatLng(position.lat, position.lng))
}

function openEventDetail(item) {
  selectedEvent.value = item
  emit('open-event', item)
}

function showRegionalTooltip(marker) {
  if (markerTooltipHideTimer) window.clearTimeout(markerTooltipHideTimer)
  markerTooltipHideTimer = null
  hoveredMarkerKey.value = marker.key
}

function keepRegionalTooltip() {
  if (markerTooltipHideTimer) window.clearTimeout(markerTooltipHideTimer)
  markerTooltipHideTimer = null
}

function hideRegionalTooltip(immediate = false) {
  if (markerTooltipHideTimer) window.clearTimeout(markerTooltipHideTimer)
  if (immediate) {
    markerTooltipHideTimer = null
    hoveredMarkerKey.value = ''
    return
  }
  markerTooltipHideTimer = window.setTimeout(() => {
    hoveredMarkerKey.value = ''
    markerTooltipHideTimer = null
  }, 220)
}

function activateRegionalMarker(marker) {
  if (selectedEvent.value) selectedEvent.value = null
  showRegionalTooltip(marker)
}

function selectTooltipEvent(item) {
  hideRegionalTooltip(true)
  selectEvent(item)
}

function showEventList() {
  selectedEvent.value = null
  hideRegionalTooltip(true)
}

function selectCategory(category) {
  if (selectedCategory.value === category) return
  selectedCategory.value = category
  selectedEvent.value = null
  clearMarkers()
  emit('select-category', category, selectedRegion.value?.area || '')
}

function browseMore() {
  const category = selectedCategory.value
    || selectedEvent.value?.main_category
    || props.items[0]?.main_category
    || ''
  emit('browse-more', category, selectedRegion.value?.area || '')
}

async function showNationwide() {
  if (regionTransitionTimer) window.clearTimeout(regionTransitionTimer)
  regionTransitionTimer = null
  regionTransitioning.value = false
  transitionRegion.value = null
  selectedRegion.value = null
  selectedEvent.value = null
  hideRegionalTooltip(true)
  clearMarkers()
}

function formatDate(value) {
  if (!value) return '-'
  return new Intl.DateTimeFormat('ko-KR').format(new Date(`${value}T00:00:00`))
}

async function initializeMap() {
  if (!selectedRegion.value) return
  loading.value = true
  error.value = ''
  try {
    kakaoApi = await loadKakaoMap()
    map = new kakaoApi.maps.Map(mapContainer.value, {
      center: new kakaoApi.maps.LatLng(...selectedRegion.value.center),
      level: selectedRegion.value.area === '제주' ? 9 : 10,
    })
    map.addControl(new kakaoApi.maps.ZoomControl(), kakaoApi.maps.ControlPosition.RIGHT)
    buildMarkerImages()
    markerTooltipElement = document.createElement('div')
    markerTooltipElement.className = 'culture-marker-tooltip'
    markerTooltip = new kakaoApi.maps.CustomOverlay({
      content: markerTooltipElement,
      xAnchor: 0.5,
      yAnchor: 1.45,
      zIndex: 12,
    })
    renderMarkers()
  } catch (loadError) {
    error.value = loadError.message || '지도를 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

watch(() => props.items, renderMarkers, { deep: true })

onBeforeUnmount(() => {
  if (regionTransitionTimer) window.clearTimeout(regionTransitionTimer)
  if (markerTooltipHideTimer) window.clearTimeout(markerTooltipHideTimer)
  clearAllLayers()
  map = null
})
</script>

<template>
  <div class="culture-map-widget">
    <div class="culture-map-controls">
      <div class="culture-map-categorybar" role="group" aria-label="문화지도 카테고리">
        <button
          v-for="category in MAP_CATEGORIES"
          :key="category[0]"
          type="button"
          :class="{ active: selectedCategory === category[0] }"
          @click="selectCategory(category[0])"
        >
          <img
            v-if="category[0]"
            :src="MARKER_URLS[category[0]]"
            alt=""
            aria-hidden="true"
          />
          {{ category[1] }}
        </button>
      </div>
    </div>

    <div
      class="culture-map-explorer"
      :class="{ 'is-compact': compact, 'has-results': selectedRegion }"
    >
      <section class="culture-map-pane">
        <div class="culture-map-toolbar">
          <p v-if="selectedRegion"><strong>{{ selectedRegion.name }}</strong> 문화행사 {{ items.length }}개</p>
          <p v-else><strong>지역을 선택해 주세요</strong><span>지도 경계 또는 지역명을 선택할 수 있어요.</span></p>
        </div>
        <div class="culture-map-frame">
          <svg
            class="culture-map-illustration"
            :class="{
              'is-region-transitioning': regionTransitioning,
              'has-selected-region': selectedRegion,
            }"
            :viewBox="`0 0 ${SVG_VIEWBOX.width} ${SVG_VIEWBOX.height}`"
            role="img"
            aria-label="지역별 문화행사 개수를 보여주는 대한민국 지도"
          >
            <defs>
              <filter id="region-shadow" x="-30%" y="-30%" width="160%" height="160%">
                <feDropShadow dx="0" dy="4" stdDeviation="5" flood-color="#61766a" flood-opacity=".16" />
              </filter>
            </defs>
            <rect width="960" height="600" rx="22" fill="#fafbfc" />
            <g class="culture-svg-provinces" filter="url(#region-shadow)">
              <path
                v-for="region in svgRegions"
                :key="`shape-${region.area}`"
                :d="region.path"
                fill-rule="evenodd"
                tabindex="0"
                role="button"
                :class="{ 'is-fading': regionTransitioning, 'is-background': selectedRegion }"
                :aria-label="`${region.name} 문화행사 ${region.count.toLocaleString()}개`"
                @click="selectRegion(region)"
                @keydown.enter.prevent="selectRegion(region)"
                @keydown.space.prevent="selectRegion(region)"
              />
            </g>
            <g
              v-for="region in svgRegions"
              :key="`callout-${region.area}`"
              class="culture-svg-callout"
              :class="{ 'is-fading': regionTransitioning, 'is-background': selectedRegion }"
              role="button"
              tabindex="0"
              :aria-label="`${region.name} 선택`"
              @click="selectRegion(region)"
              @keydown.enter.prevent="selectRegion(region)"
              @keydown.space.prevent="selectRegion(region)"
            >
              <path
                :d="`M ${region.center.x} ${region.center.y} L ${region.callout.anchorX} ${region.callout.y}`"
                class="culture-svg-connector"
              />
              <circle :cx="region.center.x" :cy="region.center.y" r="4" />
              <rect
                :x="region.callout.x"
                :y="region.callout.y - 22"
                :width="region.callout.width"
                height="44"
                rx="10"
              />
              <text :x="region.callout.x + 14" :y="region.callout.y + 5">{{ region.area }}</text>
              <text
                :x="region.callout.x + region.callout.width - 14"
                :y="region.callout.y + 5"
                class="culture-svg-count"
                text-anchor="end"
              >{{ region.count.toLocaleString() }}개</text>
            </g>
            <g v-if="transitionSvgRegion" class="culture-svg-transition-layer">
              <path
                :d="transitionSvgRegion.focusPath || transitionSvgRegion.path"
                class="culture-svg-transition-region"
                fill-rule="evenodd"
              >
                <animateTransform
                  attributeName="transform"
                  type="matrix"
                  :values="transitionSvgMatrix"
                  dur="0.58s"
                  calcMode="spline"
                  keyTimes="0;1"
                  keySplines="0.18 0.78 0.2 1"
                  fill="freeze"
                />
              </path>
            </g>
            <g
              v-if="selectedSvgRegion"
              class="culture-svg-focused-region"
              :transform="`matrix(${selectedSvgTransform.matrix})`"
            >
              <path
                :d="selectedSvgRegion.focusPath || selectedSvgRegion.path"
                class="culture-region-detail-shape"
                fill-rule="evenodd"
              />
              <clipPath id="selected-region-clip">
                <path :d="selectedSvgRegion.focusPath || selectedSvgRegion.path" fill-rule="evenodd" />
              </clipPath>
              <g class="culture-region-detail-decor" clip-path="url(#selected-region-clip)">
                <path
                  v-for="(road, index) in selectedRegionDecorations.roads"
                  :key="`road-${index}`"
                  :d="road.map((point, pointIndex) => `${pointIndex ? 'L' : 'M'} ${point.x} ${point.y}`).join(' ')"
                  class="culture-region-road"
                />
                <g
                  v-for="(icon, index) in selectedRegionDecorations.icons"
                  :key="`icon-${index}`"
                  class="culture-region-mini-icon"
                  :transform="`translate(${icon.x} ${icon.y}) scale(${icon.size / 24})`"
                >
                  <g v-if="icon.type === 'house'">
                    <path d="M-13 2 L0 -9 L13 2 Z" class="roof" />
                    <rect x="-9" y="2" width="18" height="12" rx="2" class="wall" />
                    <rect x="-2" y="6" width="4" height="8" class="door" />
                  </g>
                  <g v-else-if="icon.type === 'tree'">
                    <path d="M0 -15 C-12 -12 -15 -1 -7 4 C-12 10 -5 16 0 10 C5 16 12 10 7 4 C15 -1 12 -12 0 -15Z" class="tree" />
                    <rect x="-2" y="8" width="4" height="9" rx="1" class="trunk" />
                  </g>
                  <g v-else-if="icon.type === 'pond'">
                    <path d="M-16 1 C-9 -12 9 -13 17 -3 C25 9 6 16 -9 12 C-21 9 -23 5 -16 1Z" class="pond" />
                  </g>
                  <g v-else>
                    <rect x="-4" y="-14" width="8" height="25" rx="2" class="tower" />
                    <path d="M-12 11 H12 L6 18 H-6 Z" class="tower-base" />
                    <circle cx="0" cy="-18" r="4" class="tower-top" />
                  </g>
                </g>
              </g>
              <g v-if="selectedSvgRegion.islands" class="culture-svg-islands">
                <circle
                  :cx="selectedSvgRegion.islands.dokdo.x - selectedSvgRegion.islands.dokdo.radius * .75"
                  :cy="selectedSvgRegion.islands.dokdo.y"
                  :r="selectedSvgRegion.islands.dokdo.radius"
                />
                <circle
                  :cx="selectedSvgRegion.islands.dokdo.x + selectedSvgRegion.islands.dokdo.radius"
                  :cy="selectedSvgRegion.islands.dokdo.y + selectedSvgRegion.islands.dokdo.radius * .45"
                  :r="selectedSvgRegion.islands.dokdo.radius * .72"
                />
              </g>
              <g
                v-for="(marker, index) in regionalEventMarkers"
                :key="`${marker.item.seq}-${index}`"
                class="culture-svg-event-marker"
                :class="{ active: selectedEvent?.seq === marker.item.seq }"
                role="button"
                tabindex="0"
                @mouseenter="showRegionalTooltip(marker)"
                @mouseleave="hideRegionalTooltip()"
                @focus="showRegionalTooltip(marker)"
                @blur="hideRegionalTooltip()"
                @click="activateRegionalMarker(marker)"
                @keydown.enter.prevent="activateRegionalMarker(marker)"
                @keydown.space.prevent="activateRegionalMarker(marker)"
              >
                <image
                  :href="MARKER_URLS[marker.category] || festivalMarkerUrl"
                  :x="marker.x - regionalMarkerSize * 1.05"
                  :y="marker.y - regionalMarkerSize * 2.45"
                  :width="regionalMarkerSize * 2.1"
                  :height="regionalMarkerSize * 2.5"
                />
                <g v-if="marker.count > 1" class="culture-svg-cluster-count">
                  <circle
                    :cx="marker.x + regionalMarkerSize * .8"
                    :cy="marker.y - regionalMarkerSize * 2"
                    :r="regionalMarkerSize * .62"
                  />
                  <text
                    :x="marker.x + regionalMarkerSize * .8"
                    :y="marker.y - regionalMarkerSize * 1.82"
                    :font-size="regionalMarkerSize * .72"
                    text-anchor="middle"
                  >{{ marker.count > 99 ? '99+' : marker.count }}</text>
                </g>
              </g>
            </g>
            <foreignObject
              v-if="hoveredRegionalMarker"
              :x="regionalTooltipPosition.x"
              :y="regionalTooltipPosition.y"
              width="220"
              :height="Math.min(hoveredRegionalMarker.items.length * 42 + 45, 260)"
              class="culture-svg-tooltip-object"
            >
              <div
                xmlns="http://www.w3.org/1999/xhtml"
                class="culture-svg-tooltip-list"
                @mouseenter="keepRegionalTooltip"
                @mouseleave="hideRegionalTooltip()"
              >
                <strong>{{ hoveredRegionalMarker.items.length > 1 ? `${hoveredRegionalMarker.items.length}개 행사` : '문화행사' }}</strong>
                <div>
                  <button
                    v-for="item in hoveredRegionalMarker.items"
                    :key="item.seq"
                    type="button"
                    @click.stop="selectTooltipEvent(item)"
                  >{{ item.title }}</button>
                </div>
              </div>
            </foreignObject>
          </svg>
        </div>
      </section>

      <Transition name="culture-panel-slide">
      <aside v-if="selectedRegion" class="culture-event-panel" aria-live="polite">
        <div class="culture-event-panel-heading">
          <div>
            <span>{{ selectedRegion.name }}</span>
            <h3 v-if="selectedEvent">문화행사 정보</h3>
            <h3 v-else>문화행사 목록</h3>
          </div>
          <div class="culture-event-panel-actions">
            <button type="button" class="more" @click="browseMore">더보기</button>
            <button v-if="selectedEvent" type="button" class="back" @click="showEventList">← 행사 목록</button>
            <button type="button" aria-label="전국 지도로 돌아가기" @click="showNationwide">×</button>
          </div>
        </div>
        <button
          v-if="selectedEvent"
          type="button"
          class="culture-event-row culture-event-detail-row active"
          @click="openEventDetail(selectedEvent)"
        >
          <img v-if="selectedEvent.thumbnail_url" :src="selectedEvent.thumbnail_url" :alt="`${selectedEvent.title} 이미지`" />
          <div v-else class="culture-event-thumb">문화</div>
          <div>
            <span>{{ selectedEvent.main_category }} · {{ selectedEvent.place?.sigungu || selectedRegion.name }}</span>
            <strong>{{ selectedEvent.title }}</strong>
            <p>{{ formatDate(selectedEvent.start_date) }} ~ {{ formatDate(selectedEvent.end_date) }}</p>
            <small>{{ selectedEvent.place?.place_name || selectedEvent.place?.address || '장소 정보 없음' }}</small>
          </div>
        </button>
        <template v-else>
        <button
          v-for="item in panelItems"
          :key="item.seq"
          type="button"
          class="culture-event-row"
          :class="{ active: selectedEvent?.seq === item.seq }"
          @click="openEventDetail(item)"
        >
          <img v-if="item.thumbnail_url" :src="item.thumbnail_url" :alt="`${item.title} 이미지`" />
          <div v-else class="culture-event-thumb">문화</div>
          <div>
            <span>{{ item.main_category }} · {{ item.place?.sigungu || selectedRegion.name }}</span>
            <strong>{{ item.title }}</strong>
            <p>{{ formatDate(item.start_date) }} ~ {{ formatDate(item.end_date) }}</p>
            <small>{{ item.place?.place_name || item.place?.address || '장소 정보 없음' }}</small>
          </div>
        </button>
        </template>
      </aside>
      </Transition>
    </div>
  </div>
</template>

<style scoped>
.culture-map-controls { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: .7rem; }
.culture-map-categorybar { display: flex; align-items: center; overflow-x: auto; gap: .45rem; }
.culture-map-categorybar > span { margin-right: .2rem; color: #68736b; font-size: .72rem; font-weight: 800; }
.culture-map-categorybar button { display: inline-flex; flex: 0 0 auto; align-items: center; gap: .28rem; border: 1px solid #dce5dc; border-radius: 999px; padding: .5rem .8rem; color: #59635b; background: #fff; font-weight: 700; cursor: pointer; }
.culture-map-categorybar button img { width: 1rem; height: 1rem; object-fit: contain; }
.culture-map-categorybar button.active { border-color: #2f6b4f; color: #fff; background: #2f6b4f; }
.culture-marker-legend { display: flex; flex: 0 0 auto; align-items: center; gap: .7rem; color: #68736b; font-size: .72rem; font-weight: 700; }
.culture-marker-legend span { display: inline-flex; align-items: center; gap: .25rem; }
.culture-marker-legend b { display: grid; width: 1.35rem; height: 1.35rem; border-radius: 50%; place-items: center; color: #fff; font-size: .7rem; }
.culture-marker-legend .performance { background: #7257d9; }
.culture-marker-legend .exhibition { background: #f07832; }
.culture-marker-legend .festival { background: #159567; }
.culture-map-explorer { position: relative; display: grid; grid-template-columns: minmax(0, 1fr); gap: 1rem; }
.culture-map-explorer.has-results { grid-template-columns: minmax(0, 1fr); }
.culture-map-pane { min-width: 0; }
.culture-map-toolbar { display: flex; align-items: center; min-height: 3rem; gap: 1rem; padding: .65rem 1rem; border: 1px solid #dde4dd; border-bottom: 0; border-radius: 1.25rem 1.25rem 0 0; background: #fff; }
.culture-map-toolbar button { border: 0; border-radius: 999px; padding: .55rem .8rem; color: #fff; background: #2f6b4f; font-weight: 800; cursor: pointer; }
.culture-map-toolbar p { display: flex; align-items: center; gap: .6rem; margin: 0; color: #68736b; font-size: .82rem; }
.culture-map-toolbar p strong { color: #17221a; }
.culture-map-frame { position: relative; overflow: hidden; min-height: 520px; border: 1px solid #dde4dd; border-radius: 0 0 1.25rem 1.25rem; background: #fafbfc; }
.culture-map-illustration { display: block; width: 100%; height: 520px; background: #fafbfc; }
.culture-svg-provinces path { stroke: #b8c4c2; stroke-width: 2.2; fill: #f1f3f5; vector-effect: non-scaling-stroke; cursor: pointer; transform-box: fill-box; transform-origin: center; transition: fill .16s ease, stroke .16s ease, opacity .38s ease, transform .42s cubic-bezier(.2,.75,.25,1); }
.culture-svg-provinces path:hover, .culture-svg-provinces path:focus { outline: none; stroke: #5ccfc3; stroke-width: 3.5; fill: #e2f5f2; }
.culture-svg-callout { color: #00a66b; cursor: pointer; transition: opacity .3s ease, transform .4s ease; }
.culture-svg-callout .culture-svg-connector { stroke: #2fc18b; stroke-width: 1.6; stroke-dasharray: 4 4; fill: none; vector-effect: non-scaling-stroke; }
.culture-svg-callout circle { stroke: #00a66b; stroke-width: 2; fill: #fff; }
.culture-svg-callout rect { stroke: #00a66b; stroke-width: 2; fill: rgba(255,255,255,.96); transition: fill .16s ease, transform .16s ease; }
.culture-svg-callout text { fill: #087a53; font-size: 16px; font-weight: 900; pointer-events: none; }
.culture-svg-callout .culture-svg-count { fill: #5c7467; font-size: 13px; }
.culture-svg-callout:hover rect, .culture-svg-callout:focus rect { fill: #009c68; }
.culture-svg-callout:hover text, .culture-svg-callout:focus text { fill: #fff; }
.culture-svg-callout:hover .culture-svg-count, .culture-svg-callout:focus .culture-svg-count { fill: #e8fff5; }
.culture-svg-callout:focus { outline: none; }
.culture-svg-caption { fill: #789082; font-size: 13px; font-weight: 700; }
.is-region-transitioning .culture-svg-provinces path.is-fading { opacity: .07; transform: translateY(38px) scale(.96); pointer-events: none; }
.is-region-transitioning .culture-svg-callout.is-fading { opacity: .04; transform: translateY(30px); pointer-events: none; }
.is-region-transitioning .culture-svg-caption { opacity: 0; }
.has-selected-region .culture-svg-provinces path.is-background { opacity: .18; transform: translateY(22px) scale(.98); pointer-events: none; }
.has-selected-region .culture-svg-callout.is-background { opacity: .08; transform: translateY(16px); pointer-events: none; }
.has-selected-region .culture-svg-caption { opacity: 0; }
.culture-svg-transition-layer { filter: drop-shadow(0 14px 9px rgba(30,80,53,.24)); pointer-events: none; }
.culture-svg-transition-region { stroke: #5ccfc3; stroke-width: 3.5; fill: #e2f5f2; vector-effect: non-scaling-stroke; pointer-events: none; }
.culture-svg-focused-region { filter: drop-shadow(0 14px 9px rgba(30,80,53,.24)); transform-origin: 0 0; transition: transform .48s cubic-bezier(.16,.82,.24,1); }
.culture-panel-slide-enter-active, .culture-panel-slide-leave-active { transition: opacity .28s ease, transform .4s cubic-bezier(.16,.82,.24,1); }
.culture-panel-slide-enter-from, .culture-panel-slide-leave-to { opacity: 0; transform: translateX(36px); }
.culture-region-detail { background: #fafbfc; }
.culture-region-detail-shape { stroke: #5ccfc3; stroke-width: 3; fill: #f1f3f5; vector-effect: non-scaling-stroke; }
.culture-region-detail-decor { pointer-events: none; opacity: .72; }
.culture-region-road { fill: none; stroke: rgba(255,255,255,.9); stroke-width: 4; stroke-linecap: round; stroke-linejoin: round; vector-effect: non-scaling-stroke; }
.culture-region-mini-icon { filter: drop-shadow(0 1px 0 rgba(255,255,255,.55)); }
.culture-region-mini-icon .roof { fill: #f2b642; }
.culture-region-mini-icon .wall { fill: #fff8d2; stroke: #85c58f; stroke-width: 1; }
.culture-region-mini-icon .door { fill: #6aa56b; }
.culture-region-mini-icon .tree { fill: #4fc36e; }
.culture-region-mini-icon .trunk { fill: #9b7b51; }
.culture-region-mini-icon .pond { fill: #86d9e8; opacity: .82; }
.culture-region-mini-icon .tower { fill: #929ba3; }
.culture-region-mini-icon .tower-base { fill: #707a82; }
.culture-region-mini-icon .tower-top { fill: #b8c0c7; }
.culture-svg-islands circle { stroke: #008f61; stroke-width: 1.5; fill: #e9fbdc; vector-effect: non-scaling-stroke; }
.culture-svg-islands text { fill: #087a53; font-weight: 900; paint-order: stroke; stroke: #fff9dc; stroke-width: 1.5; vector-effect: non-scaling-stroke; pointer-events: none; }
.culture-svg-event-marker { cursor: pointer; outline: none; }
.culture-svg-event-marker image { transform-box: fill-box; transform-origin: center; transition: filter .15s ease, opacity .15s ease, transform .15s ease; }
.culture-svg-event-marker:hover image, .culture-svg-event-marker:focus image, .culture-svg-event-marker.active image { filter: drop-shadow(0 3px 3px rgba(20, 52, 36, .38)); transform: scale(1.18); }
.culture-svg-cluster-count circle { stroke: #fff; stroke-width: 1.5; fill: #17271e; vector-effect: non-scaling-stroke; }
.culture-svg-cluster-count text { fill: #fff; font-weight: 900; pointer-events: none; }
.culture-svg-tooltip-object { overflow: visible; }
.culture-svg-tooltip-list { overflow: hidden; max-height: 250px; border: 1px solid #cfdacf; border-radius: 12px; padding: 10px; color: #17221a; background: rgba(255,255,255,.98); box-shadow: 0 10px 28px rgba(26,48,34,.22); font-family: inherit; }
.culture-svg-tooltip-list > strong { display: block; margin-bottom: 7px; color: #23805c; font-size: 12px; }
.culture-svg-tooltip-list > div { overflow-y: auto; max-height: 205px; }
.culture-svg-tooltip-list button { display: block; overflow: hidden; width: 100%; border: 0; border-radius: 7px; padding: 8px 9px; text-align: left; color: #1c2a21; background: transparent; font-size: 12px; font-weight: 750; text-overflow: ellipsis; white-space: nowrap; cursor: pointer; }
.culture-svg-tooltip-list button:hover, .culture-svg-tooltip-list button:focus { outline: none; color: #fff; background: #2f7658; }
.culture-svg-empty { fill: #68786d; font-weight: 800; }
.culture-map-canvas { width: 100%; height: 520px; }
.is-compact .culture-map-frame { min-height: 430px; }
.is-compact .culture-map-illustration { height: 430px; }
.is-compact .culture-map-canvas { height: 430px; }
.culture-map-status { position: absolute; z-index: 2; inset: 0; display: grid; place-content: center; gap: .75rem; text-align: center; color: #59635b; background: rgba(248, 250, 247, .92); }
.culture-map-status p { margin: 0; }
.culture-map-status button { justify-self: center; border: 0; border-radius: 999px; padding: .65rem 1rem; color: white; background: #2f6b4f; cursor: pointer; }
.culture-map-error { color: #a83e2a; }
.culture-event-panel { position: absolute; z-index: 8; top: 0; right: 0; bottom: 0; overflow-x: hidden; overflow-y: auto; width: min(43%, 520px); min-width: 300px; border: 1px solid #dde4dd; border-radius: 1.25rem; background: rgba(255,255,255,.98); box-shadow: -14px 12px 38px rgba(29, 42, 32, .14); }
.culture-event-panel-heading { position: sticky; z-index: 2; top: 0; display: flex; align-items: center; justify-content: space-between; padding: 1rem 1.1rem; border-bottom: 1px solid #e6eae5; background: rgba(255,255,255,.96); }
.culture-event-panel-heading span { color: #f0643a; font-size: .68rem; font-weight: 800; }
.culture-event-panel-heading h3 { margin: .15rem 0 0; }
.culture-event-panel-heading h3 small { margin-left: .3rem; color: #879088; font-size: .68rem; font-weight: 600; }
.culture-event-panel-heading button { border: 0; color: #68736b; background: transparent; font-size: 1.6rem; cursor: pointer; }
.culture-event-panel-actions { display: flex; align-items: center; gap: .45rem; }
.culture-event-panel-actions button.more { border-radius: 999px; padding: .45rem .78rem; color: #fff; background: #2f7658; font-size: .72rem; font-weight: 850; white-space: nowrap; }
.culture-event-panel-actions button.back { border-radius: 999px; padding: .45rem .7rem; color: #2f7658; background: #edf6ef; font-size: .72rem; font-weight: 850; white-space: nowrap; }
.culture-event-panel-actions button.more:hover { background: #245f47; }
.culture-event-panel-actions button.back:hover { color: #fff; background: #2f7658; }
.culture-event-row { display: grid; grid-template-columns: 72px minmax(0, 1fr); gap: .8rem; width: 100%; border: 0; border-bottom: 1px solid #edf0ec; padding: .9rem; text-align: left; color: #17221a; background: #fff; cursor: pointer; }
.culture-event-row:hover, .culture-event-row.active { background: #eff7f1; }
.culture-event-row img, .culture-event-thumb { display: block; width: 72px; min-width: 72px; max-width: 72px; height: 92px; min-height: 92px; max-height: 92px; border-radius: .65rem; object-fit: cover; }
.culture-event-thumb { display: grid; place-items: center; color: #2f6b4f; background: #dcecdf; font-size: .75rem; font-weight: 800; }
.culture-event-row > div:last-child { min-width: 0; }
.culture-event-row span, .culture-event-row p, .culture-event-row small { display: block; overflow: hidden; margin: 0; color: #68736b; font-size: .68rem; text-overflow: ellipsis; white-space: nowrap; }
.culture-event-row strong { display: block; overflow: hidden; margin: .35rem 0 .45rem; font-size: .88rem; text-overflow: ellipsis; white-space: nowrap; }
.culture-event-row small { margin-top: .35rem; }
.culture-event-detail-row { grid-template-columns: 120px minmax(0, 1fr); padding: 1.25rem; cursor: default; }
.culture-event-detail-row img, .culture-event-detail-row .culture-event-thumb { width: 120px; min-width: 120px; max-width: 120px; height: 155px; min-height: 155px; max-height: 155px; }
.culture-event-detail-row strong { overflow: visible; margin-top: .55rem; font-size: 1.05rem; line-height: 1.35; white-space: normal; }
.culture-event-detail-row span, .culture-event-detail-row p, .culture-event-detail-row small { overflow: visible; margin-top: .45rem; line-height: 1.45; text-overflow: clip; white-space: normal; }
.culture-event-more { position: sticky; bottom: 0; padding: .85rem 1rem; border-top: 1px solid #dfe6df; text-align: center; background: rgba(255,255,255,.97); }
.culture-event-more p { margin: 0 0 .55rem; color: #68736b; font-size: .72rem; }
.culture-event-more button { border: 0; border-radius: 999px; padding: .62rem 1rem; color: #fff; background: #2f6b4f; font-weight: 800; cursor: pointer; }
:global(.culture-region-badge) { display: flex; align-items: center; gap: .3rem; border: 2px solid #fff; border-radius: .75rem; padding: .38rem .48rem; color: #fff; background: #246dc2; box-shadow: 0 4px 12px rgba(22,61,104,.24); white-space: nowrap; cursor: pointer; transition: transform .15s ease, background .15s ease; }
:global(.culture-region-badge:hover) { background: #ed6b24; transform: translateY(-2px); }
:global(.culture-region-badge strong) { font-size: .72rem; }
:global(.culture-region-badge span) { border-radius: 999px; padding: .12rem .3rem; color: #245e9f; background: #fff; font-size: .6rem; font-weight: 800; }
:global(.culture-region-badge.is-empty) { opacity: .68; background: #708078; }
:global(.culture-marker-tooltip) { overflow: hidden; max-width: 220px; border: 1px solid #d8e0d9; border-radius: .55rem; padding: .48rem .65rem; color: #17221a; background: rgba(255,255,255,.97); box-shadow: 0 7px 20px rgba(22,35,27,.2); font-size: .76rem; font-weight: 800; text-overflow: ellipsis; white-space: nowrap; pointer-events: none; }
@media (max-width: 680px) {
  .culture-map-controls { align-items: flex-start; flex-direction: column; }
  .culture-marker-legend { align-self: flex-end; }
  .culture-event-panel { width: 48%; min-width: 220px; }
  .culture-event-row { grid-template-columns: 56px minmax(0, 1fr); gap: .55rem; padding: .65rem; }
  .culture-event-row img, .culture-event-thumb { width: 56px; min-width: 56px; max-width: 56px; height: 72px; min-height: 72px; max-height: 72px; }
  .culture-event-panel-heading { padding: .75rem; }
  .culture-event-panel-heading h3 { font-size: .9rem; }
  .culture-map-toolbar p span { display: none; }
  .culture-map-frame, .culture-map-canvas, .culture-map-illustration, .is-compact .culture-map-frame, .is-compact .culture-map-canvas, .is-compact .culture-map-illustration { min-height: 400px; height: 400px; }
  :global(.culture-region-badge) { padding: .3rem .4rem; }
  :global(.culture-region-badge strong) { font-size: .64rem; }
}
@media (max-width: 480px) {
  .culture-event-panel { width: 62%; min-width: 190px; }
  .culture-map-toolbar { padding: .5rem .65rem; }
  .culture-map-toolbar p { display: none; }
}
</style>
