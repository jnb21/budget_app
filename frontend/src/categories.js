// How each category looks: one color and one icon, the same on every page, so
// "violet" always means Rent whether it's a card, a bar segment or a list icon.
//
// The eight colors are one categorical palette, chosen so neighbors stay
// apart for color-blind readers. On the light theme they appear as tints
// (card backgrounds, icon circles) with a deeper shade for icons and names,
// so text never sits on the full-strength color. Don't add a ninth hue:
// anything without a color of its own (Other, Uncategorized, categories you
// create) shares the neutral gray.

import {
  Bus,
  Clapperboard,
  DollarSign,
  HeartPulse,
  House,
  ShoppingBag,
  ShoppingCart,
  Tag,
  Utensils,
  Zap,
} from 'lucide-react'

const STYLES = {
  Rent: { color: '#8f75f5', Icon: House },
  Groceries: { color: '#1a9cbd', Icon: ShoppingCart },
  'Dining out': { color: '#d9692b', Icon: Utensils },
  Transport: { color: '#1fa37a', Icon: Bus },
  Utilities: { color: '#c98500', Icon: Zap },
  Shopping: { color: '#d55181', Icon: ShoppingBag },
  Entertainment: { color: '#4f7fe6', Icon: Clapperboard },
  Health: { color: '#e66767', Icon: HeartPulse },
  Income: { color: '#34c759', Icon: DollarSign },
}

export const NEUTRAL_COLOR = '#6e6e76'
const NEUTRAL = { color: NEUTRAL_COLOR, Icon: Tag }

export const INCOME_CATEGORY = 'Income'

/** { color, Icon } for a category name (null = uncategorized). */
export function categoryStyle(name) {
  return STYLES[name] ?? NEUTRAL
}
