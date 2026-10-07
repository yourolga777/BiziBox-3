import { Suspense, lazy } from 'react'

const Devtools = import.meta.env.DEV
  ? lazy(() =>
      import('@tanstack/react-query-devtools').then((m) => ({
        default: m.ReactQueryDevtools,
      }))
    )
  : null

export default function ReactQueryDevtoolsConditional() {
  if (!Devtools) return null
  return (
    <Suspense>
      <Devtools initialIsOpen={false} />
    </Suspense>
  )
}
