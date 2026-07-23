import { Capacitor } from '@capacitor/core'
import { Camera, CameraResultType, CameraSource } from '@capacitor/camera'
import { Geolocation } from '@capacitor/geolocation'
import { Browser } from '@capacitor/browser'
import { App as NativeApp } from '@capacitor/app'
import type { GsipClient } from './supabase'

export const isNative = () => Capacitor.isNativePlatform()

export async function locateDevice(): Promise<{
  latitude: number
  longitude: number
  accuracy: number
}> {
  if (isNative()) {
    const result = await Geolocation.getCurrentPosition({
      enableHighAccuracy: true,
      timeout: 15000,
    })
    return result.coords
  }
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation)
      return reject(new Error('Location is unavailable. Enter it manually.'))
    navigator.geolocation.getCurrentPosition(
      (p) => resolve(p.coords),
      () =>
        reject(
          new Error('Location permission was not granted. Enter it manually.'),
        ),
      { enableHighAccuracy: true, timeout: 15000 },
    )
  })
}

export async function nativePhoto(): Promise<File> {
  const photo = await Camera.getPhoto({
    quality: 88,
    resultType: CameraResultType.Base64,
    source: CameraSource.Prompt,
    correctOrientation: true,
    saveToGallery: false,
    width: 2400,
    height: 2400,
  })
  if (!photo.base64String)
    throw new Error('The camera did not return a photo. Please try again.')
  const bytes = Uint8Array.from(atob(photo.base64String), (c) =>
    c.charCodeAt(0),
  )
  return new File([bytes], 'soil.jpg', { type: 'image/jpeg' })
}

export async function openResource(path: string): Promise<void> {
  const url = new URL(path, 'https://globalsoilintelligence.com/').href
  if (isNative()) await Browser.open({ url })
  else window.open(url, '_blank', 'noopener,noreferrer')
}

export const authRedirect = () =>
  isNative()
    ? 'org.globalsoilintelligence.gsip://auth/callback'
    : window.location.href.split('#')[0].split('?')[0]

export async function handleAuthUrl(
  client: GsipClient,
  raw: string,
): Promise<void> {
  const url = new URL(raw)
  if (
    url.protocol !== 'org.globalsoilintelligence.gsip:' ||
    url.host !== 'auth' ||
    url.pathname !== '/callback'
  )
    return
  const code = url.searchParams.get('code')
  if (code) {
    const { error } = await client.auth.exchangeCodeForSession(code)
    if (error)
      throw new Error(
        'The sign-in link expired. Request another link on this device.',
      )
  }
}

export async function listenNative(
  client: GsipClient | null,
  resume: () => void,
  failure: () => void,
): Promise<() => void> {
  if (!isNative()) return () => {}
  const active = await NativeApp.addListener(
    'appStateChange',
    ({ isActive }) => {
      if (isActive) resume()
    },
  )
  const opened = await NativeApp.addListener('appUrlOpen', ({ url }) => {
    if (client) void handleAuthUrl(client, url).then(resume).catch(failure)
  })
  const launched = await NativeApp.getLaunchUrl()
  if (client && launched)
    await handleAuthUrl(client, launched.url).then(resume).catch(failure)
  return () => {
    void active.remove()
    void opened.remove()
  }
}
