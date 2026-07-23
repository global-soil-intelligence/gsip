import { cellToLatLng, latLngToCell } from 'h3-js'

export type FuzzedLocation = {
  h3R6: string
  h3R8: string
  latitude: number
  longitude: number
}

export function fuzzLocation(
  latitude: number,
  longitude: number,
): FuzzedLocation {
  const h3R8 = latLngToCell(latitude, longitude, 8)
  const h3R6 = latLngToCell(latitude, longitude, 6)
  const [fuzzedLatitude, fuzzedLongitude] = cellToLatLng(h3R8)
  return {
    h3R6,
    h3R8,
    latitude: fuzzedLatitude,
    longitude: fuzzedLongitude,
  }
}
