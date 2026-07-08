let kakaoMapPromise = null

const KAKAO_MAP_SCRIPT_ID = 'kakao-map-sdk'

export function loadKakaoMap() {
  if (window.kakao?.maps?.services) {
    return Promise.resolve(window.kakao)
  }

  if (kakaoMapPromise) return kakaoMapPromise

  kakaoMapPromise = new Promise((resolve, reject) => {
    const appKey = import.meta.env.VITE_KAKAO_MAP_JS_KEY

    if (!appKey) {
      reject(new Error('카카오 지도 JavaScript 키가 설정되지 않았습니다.'))
      return
    }

    const staleScript = document.getElementById(KAKAO_MAP_SCRIPT_ID)
    if (staleScript) staleScript.remove()

    const script = document.createElement('script')
    let timeoutId = null
    let settled = false

    const fail = (message) => {
      if (settled) return
      settled = true
      window.clearTimeout(timeoutId)
      script.remove()
      reject(new Error(message))
    }

    const loadMaps = () => {
      if (settled) return
      if (!window.kakao?.maps) {
        fail('카카오 지도 SDK를 초기화하지 못했습니다.')
        return
      }
      window.kakao.maps.load(() => {
        if (settled) return
        if (!window.kakao?.maps?.services) {
          fail('카카오 장소 검색 라이브러리를 초기화하지 못했습니다.')
          return
        }
        settled = true
        window.clearTimeout(timeoutId)
        resolve(window.kakao)
      })
    }

    script.id = KAKAO_MAP_SCRIPT_ID
    script.async = true
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${encodeURIComponent(appKey)}&autoload=false&libraries=services`
    script.addEventListener('load', loadMaps, { once: true })
    script.addEventListener(
      'error',
      () => fail('카카오 지도 SDK를 불러오지 못했습니다.'),
      { once: true },
    )
    timeoutId = window.setTimeout(
      () => fail('카카오 지도 응답 시간이 초과되었습니다.'),
      8000,
    )
    document.head.appendChild(script)
  }).catch((error) => {
    kakaoMapPromise = null
    throw error
  })

  return kakaoMapPromise
}
