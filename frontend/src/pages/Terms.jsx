import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, Scale, AlertTriangle, CheckCircle, FileText, Globe } from 'lucide-react'
import BrandLogo from '../components/BrandLogo'

export default function Terms() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-[#101114] text-[#F4E6D3] selection:bg-[#F28C28]/30 selection:text-[#F4E6D3] p-6 md:p-12 relative overflow-x-hidden font-sans">
      {/* Background glow */}
      <div className="pointer-events-none fixed -top-40 left-1/4 h-96 w-96 rounded-full bg-[#F28C28]/10 blur-[120px]" />
      <div className="pointer-events-none fixed bottom-1/3 -right-32 h-96 w-96 rounded-full bg-orange-600/5 blur-[140px]" />

      <div className="max-w-4xl mx-auto relative z-10">
        {/* Header navigation */}
        <div className="flex items-center justify-between pb-8 border-b border-white/[0.08] mb-10">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 text-xs font-medium text-[#C5C0B8] hover:text-[#F4E6D3] transition-colors bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] px-3.5 py-1.5 rounded-full cursor-pointer"
          >
            <ArrowLeft size={14} />
            <span>Back</span>
          </button>

          <Link to="/" className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/[0.05] border border-white/[0.08] text-[#F28C28]">
              <BrandLogo size={18} />
            </div>
            <span className="text-sm font-bold tracking-tight text-[#F4E6D3]">SlideMind AI</span>
          </Link>
        </div>

        {/* Title */}
        <div className="space-y-3 mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#F28C28]/10 border border-[#F28C28]/25 text-xs font-mono text-[#F28C28]">
            <Scale size={14} />
            <span>User Agreement & Conditions</span>
          </div>
          <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white">Terms of Service</h1>
          <p className="text-sm text-[#888A90] font-mono">
            Last Updated: November 14, 2026 · Effective Date: November 14, 2026
          </p>
        </div>

        {/* Terms Body */}
        <div className="space-y-10 text-sm leading-relaxed text-[#C5C0B8]">
          <section className="p-6 rounded-2xl bg-[#17191E] border border-white/[0.08] space-y-3">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Globe size={18} className="text-[#F28C28]" />
              1. Acceptance of Terms
            </h2>
            <p>
              By accessing, browsing, creating an account, or using SlideMind AI ("SlideMind", "Service", "we", "us"), you agree to be bound by these Terms of Service ("Terms") and our Privacy Policy. If you do not agree to these Terms, you may not access or use the Service.
            </p>
          </section>

          <section className="space-y-4">
            <h2 className="text-lg font-bold text-white">2. User Accounts & Fair Usage</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>
                <strong className="text-[#F4E6D3]">Account Creation:</strong> You may authenticate using Google OAuth, verified email, or temporary guest access. You are responsible for maintaining the confidentiality of your session.
              </li>
              <li>
                <strong className="text-[#F4E6D3]">Guest Account Limits:</strong> Anonymous guest accounts are provided for demonstration purposes and are strictly limited to a maximum of 3 presentation generations. Continuous access and higher quotas require a standard account.
              </li>
              <li>
                <strong className="text-[#F4E6D3]">Rate Limiting:</strong> To safeguard system stability and prevent abuse, automated bots, high-frequency scripting, and API abuse are strictly forbidden and subject to IP and user rate limiting.
              </li>
            </ul>
          </section>

          {/* AI Content Disclaimer - CRITICAL LEGAL PROTECTION */}
          <section className="p-6 rounded-2xl bg-amber-500/[0.05] border border-amber-500/20 space-y-3">
            <div className="flex items-center gap-2 text-amber-400 font-bold text-base">
              <AlertTriangle size={18} />
              <span>3. AI-Generated Content Disclaimer & Due Diligence</span>
            </div>
            <p className="text-white/90">
              SlideMind AI uses advanced generative artificial intelligence models to synthesize outlines, slide copy, and design compositions. You expressly acknowledge and agree that:
            </p>
            <ul className="list-disc pl-5 space-y-2 text-[#C5C0B8]">
              <li>
                <strong className="text-white">Verification Required:</strong> AI models may occasionally generate inaccurate facts, incorrect numerical calculations, hallucinated citations, or outdated assertions. You must review, verify, and confirm all slide content before using it in any professional, educational, financial, legal, medical, or executive context.
              </li>
              <li>
                <strong className="text-white">User Responsibility:</strong> You are solely responsible for all final decisions, presentations delivered, and representations made based on content produced through the Service.
              </li>
              <li>
                <strong className="text-white">No Professional Advice:</strong> The Service does not provide financial, legal, tax, medical, or certified architectural advice.
              </li>
            </ul>
          </section>

          <section className="space-y-4">
            <h2 className="text-lg font-bold text-white">4. Intellectual Property & Ownership</h2>
            <div className="space-y-3">
              <div className="flex items-start gap-3 p-4 rounded-xl bg-[#17191E] border border-white/[0.06]">
                <CheckCircle size={18} className="text-[#F28C28] shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-white font-semibold text-xs mb-1">Your Content is Yours</h3>
                  <p className="text-xs text-[#888A90]">
                    You retain 100% full copyright and ownership of your uploaded documents, source prompts, and the final generated slide decks. SlideMind AI claims zero ownership or intellectual property rights over your presentations.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-4 rounded-xl bg-[#17191E] border border-white/[0.06]">
                <FileText size={18} className="text-[#F28C28] shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-white font-semibold text-xs mb-1">Platform License</h3>
                  <p className="text-xs text-[#888A90]">
                    You grant SlideMind AI a limited, non-exclusive license strictly necessary to store, render, transform, and transmit your presentations to you or to connected services (e.g., Google Drive) at your request.
                  </p>
                </div>
              </div>
            </div>
          </section>

          <section className="space-y-4">
            <h2 className="text-lg font-bold text-white">5. Acceptable Use Policy</h2>
            <p>You agree not to use SlideMind AI to generate, host, or disseminate:</p>
            <ul className="list-disc pl-5 space-y-2">
              <li>Defamatory, libelous, hateful, or harassing material.</li>
              <li>Content that infringes any third party’s copyright, patent, trademark, or trade secret.</li>
              <li>Malicious software, exploit payloads, phishing scams, or deceptive commercial schemes.</li>
              <li>Illegal material or content that promotes harm against individuals or communities.</li>
            </ul>
          </section>

          <section className="space-y-4">
            <h2 className="text-lg font-bold text-white">6. Limitation of Liability</h2>
            <p>
              To the maximum extent permitted by applicable law, SlideMind AI and its operators, affiliates, and suppliers shall not be liable for any indirect, incidental, special, consequential, or punitive damages, including loss of profits, data, goodwill, or business reputation, arising from or related to your use of or inability to use the Service or any AI-generated output.
            </p>
          </section>

          <section className="space-y-4">
            <h2 className="text-lg font-bold text-white">7. Termination</h2>
            <p>
              You may terminate your agreement with SlideMind AI at any time by exercising your right to deletion under GDPR (<code className="text-[#F4E6D3]">POST /api/user/delete-account</code>). We reserve the right to suspend or terminate accounts that violate our Acceptable Use Policy.
            </p>
          </section>

          <section className="space-y-4 border-t border-white/[0.08] pt-8">
            <h2 className="text-lg font-bold text-white">8. Contact Information</h2>
            <p>
              For legal inquiries or notices regarding these Terms, contact{' '}
              <a href="mailto:legal@slidemind.ai" className="text-[#F28C28] hover:underline">
                legal@slidemind.ai
              </a>.
            </p>
          </section>
        </div>

        {/* Footer */}
        <div className="mt-16 pt-8 border-t border-white/[0.08] flex flex-col md:flex-row items-center justify-between text-xs text-[#888A90] gap-4">
          <div>© 2026 SlideMind AI Studio. All rights reserved.</div>
          <div className="flex items-center gap-6">
            <Link to="/privacy" className="hover:text-white transition-colors">
              Privacy Policy
            </Link>
            <Link to="/" className="hover:text-white transition-colors">
              Studio Home
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
