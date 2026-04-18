export const novaBrandAssets = {
  isotipoDark: '/brand/nova/isotipo-dark.png',
  isotipoLight: '/brand/nova/isotipo-light.png',
  isotipoSvg: '/brand/nova/isotipo.svg',
}

export function getNovaIsotipoSrc(tone = 'dark') {
  return tone === 'light' ? novaBrandAssets.isotipoLight : novaBrandAssets.isotipoDark
}
