// Port of bloodborne/flags.py: the event flag store. See that file for where the rules come from.
const POOL_AFTER_AOB = 377, BLOCK = 125, POOL_BLOCKS = 1200
const GLOBAL_TYPES = [0, 1, 5, 6, 7], MAP_TYPES = [1, 5, 6, 7, 9]
const MAPS = [[21, 0], [21, 1], [22, 0], [23, 0], [24, 0], [24, 1], [24, 2], [25, 0], [26, 0], [27, 0], [28, 0], [29, 0], [32, 0], [33, 0], [34, 0], [35, 0], [36, 0]]

export function locate(flag) {
  const t = Math.floor(flag / 10000000), area = Math.floor(flag / 100000) % 100, block = Math.floor(flag / 10000) % 10, zone = Math.floor(flag / 1000) % 10, bit = flag % 1000
  let key
  if (flag < 10000 || (area === 0 && block === 0)) {
    if (!GLOBAL_TYPES.includes(t)) return null
    key = GLOBAL_TYPES.indexOf(t) + (flag < 10000 ? Math.floor(flag / 1000) : zone) * 5
  } else {
    const m = MAPS.findIndex(([a, b]) => a === area && b === block)
    if (!MAP_TYPES.includes(t) || m < 0) return null
    key = zone * 115 + 50 + 23 * MAP_TYPES.indexOf(t) + m
  }
  if (key >= POOL_BLOCKS) return null
  return [POOL_AFTER_AOB + key * BLOCK + (bit >> 3), 0x80 >> (bit & 7)]
}

export function isSet(d, lay, flag) {
  const w = locate(flag)
  return w === null ? null : Boolean(d[lay.aob + w[0]] & w[1])
}
