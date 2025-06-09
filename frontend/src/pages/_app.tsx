import '../styles/globals.css'
import type { AppProps } from 'next/app'
import { QueryProvider } from '../context/QueryProvider'

export default function App({ Component, pageProps }: AppProps) {
  return (
    <QueryProvider>
      <Component {...pageProps} />
    </QueryProvider>
  )
}
