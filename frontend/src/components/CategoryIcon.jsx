import { categoryStyle } from '../categories.js'

/** A round dark badge with the category's icon in the category's color. */
export default function CategoryIcon({ name, size = 44 }) {
  const { color, Icon } = categoryStyle(name)
  return (
    <span className="category-icon" style={{ '--cat': color, width: size, height: size }} aria-hidden="true">
      <Icon size={Math.round(size * 0.45)} strokeWidth={1.8} />
    </span>
  )
}
