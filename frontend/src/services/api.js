import axios from 'axios'

const client = axios.create({ baseURL: import.meta.env.VITE_API_URL || '' })

client.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('sm_token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

/** Normalizes backend errors to Error(message) with .code and .status */
function unwrap(promise) {
  return promise
    .then((r) => r.data.data)
    .catch((e) => {
      const body = e.response?.data?.error
      const err = new Error(body?.message || 'Could not reach the server. Please try again.')
      err.code = body?.code || 'network_error'
      err.status = e.response?.status
      err.details = body?.details
      throw err
    })
}

export const api = {
  devLogin: (email) => unwrap(client.post('/api/auth/dev-login', { email })),
  emailLogin: (email) => unwrap(client.post('/api/auth/email-login', { email })),
  guestLogin: () => unwrap(client.post('/api/auth/guest-login')),
  googleStart: (returnTo) => unwrap(client.post('/api/auth/google', returnTo ? { return_to: returnTo } : {})),
  googleDisconnect: () => unwrap(client.post('/api/auth/google/disconnect')),
  me: () => unwrap(client.get('/api/auth/me')),
  history: () => unwrap(client.get('/api/history')),
  createConversation: () => unwrap(client.post('/api/conversations')),
  getConversation: (id) => unwrap(client.get(`/api/conversations/${id}`)),
  deleteConversation: (id) => unwrap(client.delete(`/api/conversations/${id}`)),
  chat: (message, conversationId, presentationId, extra = {}) =>
    unwrap(
      client.post(
        '/api/chat',
        {
          message,
          conversation_id: conversationId,
          ...(presentationId ? { presentation_id: presentationId } : {}),
          ...(extra?.style ? { style: extra.style } : {}),
          ...(extra?.deepResearch !== undefined ? { deep_research: extra.deepResearch } : {}),
          ...(extra?.density ? { density: extra.density } : {}),
        },
        extra?.signal ? { signal: extra.signal } : {}
      )
    ),
  presentations: () => unwrap(client.get('/api/presentations')),
  presentation: (id) => unwrap(client.get(`/api/presentation/${id}`)),
  createPresentation: (body) => unwrap(client.post('/api/presentation/create', body)),
  jobStatus: (jobId) => unwrap(client.get('/api/presentation/status', { params: { job_id: jobId } })),
  publishPresentation: (id) => unwrap(client.post(`/api/presentation/${id}/publish`)),
  setTheme: (id, theme) => unwrap(client.post(`/api/presentation/${id}/theme`, { theme })),
  getIntelligence: (id, params = {}) => unwrap(client.get(`/api/presentation/${id}/intelligence`, { params })),
  fixIntelligence: (id, action_type, slide_position = null) =>
    unwrap(client.post(`/api/presentation/${id}/intelligence/fix`, { action_type, slide_position })),
  editPresentation: (body) => unwrap(client.post('/api/presentation/edit', body)),
  syncPresentation: (id) => unwrap(client.post(`/api/presentation/${id}/sync`)),
  practiceSlide: (body) => unwrap(client.post('/api/rehearsal', body)),
  practiceDeck: (body) => unwrap(client.post('/api/rehearsal/deck', body)),
  exportPresentation: async (id, format) => {
    try {
      const r = await client.get(`/api/presentation/${id}/export`, { params: { format }, responseType: 'blob' })
      return r.data
    } catch (e) {
      // error bodies arrive as blobs when responseType is 'blob'
      let msg = 'Export failed.'
      try { msg = JSON.parse(await e.response.data.text()).error.message } catch { /* keep default */ }
      throw new Error(msg)
    }
  },
  downloadPresentation: async (id, format) => {
    try {
      const r = await client.get(`/api/presentation/${id}/download`, { params: { format }, responseType: 'blob' })
      return r.data
    } catch (e) {
      let msg = 'Download failed.'
      try { msg = JSON.parse(await e.response.data.text()).error.message } catch { /* keep default */ }
      throw new Error(msg)
    }
  },
  designSystems: () => unwrap(client.get('/api/design-systems')),
  regenerateSlide: (id, position, payload = '') => {
    const body = typeof payload === 'string' ? { instructions: payload } : (payload || {})
    return unwrap(client.post(`/api/presentation/${id}/slide/${position}/regenerate`, body))
  },
  auditPresentation: (id) => unwrap(client.get(`/api/presentation/${id}/audit`)),
  autoCorrectPresentation: (id) => unwrap(client.post(`/api/presentation/${id}/audit/auto-correct`)),
  documents: () => unwrap(client.get('/api/documents')),
  deleteDocument: (id) => unwrap(client.delete(`/api/documents/${id}`)),
  exportUserData: () => unwrap(client.get('/api/user/export-data')),
  deleteAccount: () => unwrap(client.post('/api/user/delete-account')),
  upload: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return unwrap(client.post('/api/upload', fd))
  },
  // Visual Asset & Intelligence Engine APIs
  uploadVisualAsset: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return unwrap(client.post('/api/assets/upload', fd))
  },
  listVisualAssets: (category) => unwrap(client.get('/api/assets', { params: category ? { category } : {} })),
  getVisualCandidates: (pid, pos) => unwrap(client.get(`/api/presentation/${pid}/slide/${pos}/visual/candidates`)),
  selectSlideVisual: (pid, pos, image) => unwrap(client.post(`/api/presentation/${pid}/slide/${pos}/visual/select`, { image })),
  removeSlideVisual: (pid, pos) => unwrap(client.post(`/api/presentation/${pid}/slide/${pos}/visual/remove`)),
  switchSlideToDiagram: (pid, pos) => unwrap(client.post(`/api/presentation/${pid}/slide/${pos}/visual/switch-diagram`)),
}
