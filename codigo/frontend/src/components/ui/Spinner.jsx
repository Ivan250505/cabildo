export default function Spinner({ size = "md", className = "" }) {
  const s = { sm: "h-4 w-4", md: "h-8 w-8", lg: "h-12 w-12" }[size]
  return (
    <div className={`animate-spin rounded-full border-2 border-gray-200 border-t-primary ${s} ${className}`} />
  )
}

export function FullPageSpinner() {
  return (
    <div className="flex h-screen items-center justify-center">
      <Spinner size="lg" />
    </div>
  )
}
