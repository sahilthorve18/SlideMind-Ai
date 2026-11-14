export default function BrandLogo({ size = 18, className = "text-brand-400" }) {
  return (
    <svg 
      width={size} 
      height={size} 
      viewBox="0 0 24 24" 
      fill="none" 
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <rect x="2.5" y="3.5" width="19" height="13" rx="2.5" stroke="currentColor" strokeWidth="1.8" />
      <path d="M7 10H13" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M7 7.5H17" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M12 16.5V20.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M8 20.5H16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="16" cy="10" r="1.2" fill="currentColor" />
    </svg>
  )
}
