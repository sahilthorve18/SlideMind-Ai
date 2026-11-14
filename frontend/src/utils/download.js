/**
 * Reliable cross-browser file download trigger.
 * Handles filename sanitization, DOM attachment, and asynchronous object URL revocation.
 */
export function triggerFileDownload(blob, filename, defaultExt = 'pptx') {
  if (!blob) {
    throw new Error('Download failed: No file data received.')
  }

  // Ensure blob is treated as a Blob instance
  const safeBlob = blob instanceof Blob ? blob : new Blob([blob])

  // Sanitize filename for OS file systems (removes illegal characters: \ / : * ? " < > |)
  let cleanName = (filename || 'presentation')
    .replace(/[/\\?%*:|"<>]/g, '_')
    .replace(/\s+/g, ' ')
    .trim()

  if (!cleanName) {
    cleanName = 'presentation'
  }

  // Ensure proper extension
  if (defaultExt && !cleanName.toLowerCase().endsWith(`.${defaultExt.toLowerCase()}`)) {
    cleanName = `${cleanName}.${defaultExt.toLowerCase()}`
  }

  const url = window.URL.createObjectURL(safeBlob)
  const link = document.createElement('a')
  link.style.display = 'none'
  link.href = url
  link.setAttribute('download', cleanName)
  link.setAttribute('target', '_blank') // helps iOS safari handle blob downloads

  document.body.appendChild(link)
  link.click()

  // Delay revocation to ensure browser download thread has received the file stream
  setTimeout(() => {
    try {
      if (document.body.contains(link)) {
        document.body.removeChild(link)
      }
      window.URL.revokeObjectURL(url)
    } catch {
      // Ignore cleanup error if already removed
    }
  }, 3000)
}
