export default function SuggestionChips({ onSelect }) {
  const suggestions = [
    {
      icon: '💼',
      label: 'Investor Pitch',
      prompt: 'Create a 10-slide investor pitch deck for a B2B SaaS startup in the HR tech space'
    },
    {
      icon: '📊',
      label: 'Quarterly Review',
      prompt: 'Prepare a Q4 business review presentation with key metrics, achievements, and 2024 goals'
    },
    {
      icon: '🎓',
      label: 'Training Module',
      prompt: 'Design an employee onboarding presentation covering company culture, tools, and processes'
    },
    {
      icon: '🔬',
      label: 'Research Findings',
      prompt: 'Present research findings on AI adoption trends in healthcare with data visualizations'
    },
    {
      icon: '🚀',
      label: 'Product Launch',
      prompt: 'Create a product launch presentation for a new mobile app with feature highlights'
    },
    {
      icon: '📈',
      label: 'Market Analysis',
      prompt: 'Analyze the renewable energy market with trends, opportunities, and competitive landscape'
    }
  ];

  return (
    <div>
      <p className="text-sm text-white/50 mb-4 text-center">
        or start with a template:
      </p>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {suggestions.map((suggestion, idx) => (
          <button
            key={idx}
            onClick={() => onSelect(suggestion.prompt)}
            className="glass-chip rounded-xl p-4 text-left group"
          >
            <div className="text-2xl mb-2 group-hover:scale-110 transition-transform">
              {suggestion.icon}
            </div>
            <div className="text-sm font-medium text-white/90">
              {suggestion.label}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
