export default function TemplateCard({ template, onSelect }) {
  return (
    <button
      onClick={onSelect}
      className="glass-card rounded-xl p-6 group hover:scale-[1.02] transition-all text-left w-full"
    >
      {/* Preview Icon */}
      <div className="text-5xl mb-4 group-hover:scale-110 transition-transform">
        {template.preview}
      </div>

      {/* Name */}
      <h3 className="text-lg font-semibold text-white mb-2">
        {template.name}
      </h3>

      {/* Description */}
      <p className="text-sm text-white/60 mb-4 line-clamp-2">
        {template.description}
      </p>

      {/* Features */}
      <div className="flex flex-wrap gap-2 mb-4">
        {template.features.map((feature, idx) => (
          <span
            key={idx}
            className="text-xs px-2 py-1 bg-white/5 text-white/70 rounded-md"
          >
            {feature}
          </span>
        ))}
      </div>

      {/* Color Palette */}
      <div className="flex gap-2">
        {template.colors.map((color, idx) => (
          <div
            key={idx}
            className="w-8 h-8 rounded-lg border border-white/10 group-hover:scale-110 transition-transform"
            style={{ backgroundColor: color }}
            title={color}
          />
        ))}
      </div>
    </button>
  );
}
