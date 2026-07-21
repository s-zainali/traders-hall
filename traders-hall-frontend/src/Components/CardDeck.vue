<script>
import { h, cloneVNode, Fragment, Comment, Text } from 'vue'

export default {
  props: {
    offsetX: { type: Number, default: 7 },   // px each card shifts right
    offsetY: { type: Number, default: 7 },   // px each card shifts down
    maxVisible: { type: Number, default: 5 },  // how many cards are actually rendered/stacked
  },
  setup(props, { slots }) {
    // v-for / conditionals wrap children in Fragments; flatten and drop comment/text nodes
    const flatten = (nodes) =>
      nodes.flatMap((n) => {
        if (n.type === Fragment) return flatten(n.children || [])
        if (n.type === Comment || n.type === Text) return []
        return [n]
      })

    return () => {
      const all = flatten(slots.default?.() ?? [])
      const shown = Math.min(all.length, props.maxVisible)
      const visible = all.slice(-shown) // keep only the top `shown` cards
      const topIdx = shown - 1

      const cards = visible.map((vnode, j) =>
        // j = 0 is the back card at the origin; the top card (j === topIdx) is the most offset
        cloneVNode(vnode, {
          // only the front/top card receives hover/click; the rest are inert
          class: [
            'col-start-1 row-start-1',
            j === topIdx ? 'pointer-events-auto' : 'pointer-events-none',
          ],
          style: {
            transform: `translate(${j * props.offsetX}px, ${j * props.offsetY}px)`,
          },
        })
      )

      return h(
        'div',
        {
          class: 'inline-grid grid-cols-1 grid-rows-1',
          style: {
            // footprint is bounded to (shown - 1) * offset, no matter how many cards exist
            paddingRight: `${Math.max(0, shown - 1) * props.offsetX}px`,
            paddingBottom: `${Math.max(0, shown - 1) * props.offsetY}px`,
          },
        },
        cards
      )
    }
  },
}
</script>