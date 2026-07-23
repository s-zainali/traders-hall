/**
 * Seat identity: one colour + one token per seat, assigned by seat_index.
 *
 * Both, not either. They do different jobs — the colour is what you read at a
 * glance to find your own panel across the table, and the token is what you
 * name a player by ("the crown seat"). Colour alone fails for colourblind
 * players; a token alone is too small to scan quickly at panel size.
 *
 * The palette is deliberately BRIGHT and saturated, because every card colour
 * in the game is muted (cream #DFD0B8, purple #5C3E94, teal #408175). That
 * contrast in saturation, not just hue, is what stops a seat badge from reading
 * as a card.
 */
export const SEATS = [
    {
      index: 0,
      name: 'Crown',
      token: 'crown',
      // full literal class strings — Tailwind's scanner cannot see interpolated ones
      text: 'text-orange-400',
      border: 'border-orange-400',
      borderSoft: 'border-orange-400/50',
      bgSoft: 'bg-orange-400/15',
      bgSolid: 'bg-orange-400',
      outline: 'outline-orange-400',
      shadow: 'shadow-orange-400/20',
      hex: '#fb923c',
    },
    {
      index: 1,
      name: 'Diamond',
      token: 'diamond',
      text: 'text-fuchsia-400',
      border: 'border-fuchsia-400',
      borderSoft: 'border-fuchsia-400/50',
      bgSoft: 'bg-fuchsia-400/15',
      bgSolid: 'bg-fuchsia-400',
      outline: 'outline-fuchsia-400',
      shadow: 'shadow-fuchsia-400/20',
      hex: '#e879f9',
    },
    {
      index: 2,
      name: 'Shield',
      token: 'shield',
      text: 'text-lime-400',
      border: 'border-lime-400',
      borderSoft: 'border-lime-400/50',
      bgSoft: 'bg-lime-400/15',
      bgSolid: 'bg-lime-400',
      outline: 'outline-lime-400',
      shadow: 'shadow-lime-400/20',
      hex: '#a3e635',
    },
    {
      index: 3,
      name: 'Anchor',
      token: 'anchor',
      text: 'text-cyan-400',
      border: 'border-cyan-400',
      borderSoft: 'border-cyan-400/50',
      bgSoft: 'bg-cyan-400/15',
      bgSolid: 'bg-cyan-400',
      outline: 'outline-cyan-400',
      shadow: 'shadow-cyan-400/20',
      hex: '#22d3ee',
    },
  ]
  
  /** Falls back to a neutral entry so an out-of-range seat never throws. */
  export const EMPTY_SEAT = {
    index: -1,
    name: 'Empty',
    token: 'empty',
    text: 'text-gray-x-light',
    border: 'border-gray-light',
    borderSoft: 'border-gray-light',
    bgSoft: 'bg-gray-light/20',
    bgSolid: 'bg-gray-light',
    outline: 'outline-gray-light',
    shadow: 'shadow-black/20',
    hex: '#6b7280',
  }
  
  export function seatStyle(index) {
    return SEATS[index] ?? EMPTY_SEAT
  }