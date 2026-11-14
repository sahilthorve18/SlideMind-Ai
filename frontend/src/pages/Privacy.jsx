import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, ShieldCheck, Lock, Download, Trash2, FileText, Globe } from 'lucide-react'
import BrandLogo from '../components/BrandLogo'

export default function Privacy() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-[#101114] text-[#F4E6D3] selection:bg-[#F28C28]/30 selection:text-[#F4E6D3] p-6 md:p-12 relative overflow-x-hidden font-sans">
      {/* Background glow */}
      <div className="pointer-events-none fixed -top-40 right-1/4 h-96 w-96 rounded-full bg-[#F28C28]/10 blur-[120px]" />
      <div className="pointer-events-none fixed top-1/2 -left-32 h-96 w-96 rounded-full bg-orange-600/5 blur-[140px]" />

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
            <ShieldCheck size={14} />
            <span>Legal Compliance & Privacy</span>
          </div>
          <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white">Privacy Policy</h1>
          <p className="text-sm text-[#888A90] font-mono">
            Last Updated: November 14, 2026 · Effective Date: November 14, 2026
          </p>
        </div>

        {/* Document Body */}
        <div className="space-y-10 text-sm leading-relaxed text-[#C5C0B8]">
          <section className="p-6 rounded-2xl bg-[#17191E] border border-white/[0.08] space-y-3">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Globe size={18} className="text-[#F28C28]" />
              1. Overview & Data Controller
            </h2>
            <p>
              SlideMind AI ("SlideMind", "we", "us", or "our") respects your privacy and is committed to protecting your personal data. This Privacy Policy explains how we collect, process, store, and safeguard your data when you access or use our AI-powered presentation platform.
            </p>
            <p className="text-xs text-[#888A90]">
              Data Controller Contact: <span className="text-[#F4E6D3] font-mono">privacy@slidemind.ai</span>
            </p>
          </section>

          <section className="space-y-4">
            <h2 className="text-lg font-bold text-white">2. Information We Collect</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>
                <strong className="text-[#F4E6D3]">Account Information:</strong> When signing in with email or Google OAuth, we collect your email address, display name, and avatar URL. If using a guest pass, a temporary pseudo-anonymous identifier is generated.
              </li>
              <li>
                <strong className="text-[#F4E6D3]">User Content & Presentations:</strong> Topic inputs, slide customizations, outlines, generated slides, speaker notes, and custom design settings.
              </li>
              <li>
                <strong className="text-[#F4E6D3]">Source Documents:</strong> Any files (PDF, DOCX, TXT) uploaded for RAG (Retrieval-Augmented Generation) context. These are stored securely and associated solely with your user account.
              </li>
              <li>
                <strong className="text-[#F4E6D3]">Google User Data:</strong> If you connect Google Slides, we store an encrypted OAuth refresh token to enable publishing directly to your Google Drive. We do not access or read your existing unrelated Google Drive files.
              </li>
            </ul>
          </section>

          <section className="space-y-4">
            <h2 className="text-lg font-bold text-white">3. How We Use Artificial Intelligence</h2>
            <p>
              SlideMind AI uses Google Gemini API to structure outlines, generate slide copy, analyze documents, and assist with editing.
            </p>
            <ul className="list-disc pl-5 space-y-2">
              <li>
                Your inputs and documents are transmitted via encrypted TLS connections to Google Gemini API for inference only.
              </li>
              <li>
                Under Google's API policies, your data transmitted through paid enterprise API tiers is <strong className="text-[#F4E6D3]">not used to train or improve</strong> foundation models.
              </li>
              <li>
                Presentations created by AI should be reviewed by you prior to professional or public distribution.
              </li>
            </ul>
          </section>

          <section className="space-y-4">
            <h2 className="text-lg font-bold text-white">4. Google API Limited Use Disclosure</h2>
            <p>
              SlideMind AI's use and transfer to any other app of information received from Google APIs will adhere to the{' '}
              <a
                href="https://developers.google.com/terms/api-services-user-data-policy"
                target="_blank"
                rel="noreferrer"
                className="text-[#F28C28] underline underline-offset-4"
              >
                Google API Services User Data Policy
              </a>
              , including the Limited Use requirements.
            </p>
            <p>
              Specifically, we request permissions strictly to create new Google Slides presentations and export decks to your Google Drive upon your explicit instruction.
            </p>
          </section>

          <section className="p-6 rounded-2xl bg-[#17191E] border border-white/[0.08] space-y-4">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Lock size={18} className="text-[#F28C28]" />
              5. Your GDPR & CCPA Rights (Data Export & Deletion)
            </h2>
            <p>
              Regardless of your jurisdiction, we uphold the highest international privacy standards, including full GDPR compliance:
            </p>
            <div className="grid md:grid-cols-2 gap-4 pt-2">
              <div className="p-4 rounded-xl bg-black/40 border border-white/[0.06] space-y-2">
                <div className="flex items-center gap-2 text-white font-semibold text-xs">
                  <Download size={14} className="text-[#F28C28]" />
                  <span>Right of Access & Portability</span>
                </div>
                <p className="text-xs text-[#888A90]">
                  You can download a complete, machine-readable JSON archive of all your account data, conversations, documents, and presentations via our API (<code className="text-[#F4E6D3]">GET /api/user/export-data</code>) or in the Settings modal.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-black/40 border border-white/[0.06] space-y-2">
                <div className="flex items-center gap-2 text-white font-semibold text-xs">
                  <Trash2 size={14} className="text-red-400" />
                  <span>Right to Erasure (Deletion)</span>
                </div>
                <p className="text-xs text-[#888A90]">
                  You can permanently delete your entire account and all associated records, presentations, and uploaded files with an immediate, irreversible cascade via <code className="text-[#F4E6D3]">POST /api/user/delete-account</code>.
                </p>
              </div>
            </div>
          </section>

          <section className="space-y-4">
            <h2 className="text-lg font-bold text-white">6. Security & Storage</h2>
            <p>
              We implement industry-grade technical and organizational safeguards:
            </p>
            <ul className="list-disc pl-5 space-y-2">
              <li>All OAuth tokens and credentials are encrypted at rest using AES-256 (Fernet encryption).</li>
              <li>All data in transit is encrypted using TLS 1.3.</li>
              <li>Production databases and storage are protected by strict access controls and rate limiters.</li>
            </ul>
          </section>

          <section className="space-y-4 border-t border-white/[0.08] pt-8">
            <h2 className="text-lg font-bold text-white">7. Contact Us</h2>
            <p>
              If you have any questions or wish to exercise your data rights, contact our Data Protection Officer at{' '}
              <a href="mailto:privacy@slidemind.ai" className="text-[#F28C28] hover:underline">
                privacy@slidemind.ai
              </a>.
            </p>
          </section>
        </div>

        {/* Footer */}
        <div className="mt-16 pt-8 border-t border-white/[0.08] flex flex-col md:flex-row items-center justify-between text-xs text-[#888A90] gap-4">
          <div>© 2026 SlideMind AI Studio. All rights reserved.</div>
          <div className="flex items-center gap-6">
            <Link to="/terms" className="hover:text-white transition-colors">
              Terms of Service
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
