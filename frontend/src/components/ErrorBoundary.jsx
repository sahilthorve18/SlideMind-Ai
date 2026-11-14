import React from 'react'

/**
 * ErrorBoundary
 * Catches JavaScript errors anywhere in its child component tree,
 * logs those errors, and displays a fallback UI instead of crashing the app.
 */
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback({
          error: this.state.error,
          reset: this.handleReset,
        })
      }

      return (
        <div className="my-4 rounded-xl border border-red-500/30 bg-red-500/10 p-5 text-sm text-red-200 backdrop-blur-md">
          <div className="flex items-center gap-2.5 font-semibold text-red-300 mb-1">
            <span className="material-symbols-outlined text-base">error</span>
            <span>Something went wrong in this component</span>
          </div>
          <p className="text-xs font-mono text-red-300/80 mb-3 break-all">
            {this.state.error?.message || 'Unknown render error'}
          </p>
          <button
            type="button"
            onClick={this.handleReset}
            className="px-3 py-1 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-white text-xs font-medium transition-colors cursor-pointer"
          >
            Try Again
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
