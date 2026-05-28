"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { authApi } from "@/lib/api"
import { cn } from "@/lib/utils"

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const res = await authApi.login(email, password)
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        setError(data.detail ?? "Nieprawidłowy email lub hasło")
        return
      }
      router.push("/chat")
      router.refresh()
    } catch {
      setError("Błąd połączenia z serwerem")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-full flex min-h-screen">
      {/* Brand panel */}
      <div className="hidden lg:flex flex-col justify-between w-[420px] bg-[hsl(var(--accent-600))] text-white p-12">
        <div>
          <div className="flex items-center gap-2 mb-16">
            <div className="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center font-bold text-lg">M</div>
            <span className="font-semibold text-lg tracking-tight">medRAG</span>
          </div>
          <h1 className="text-3xl font-bold leading-snug mb-4">
            Inteligentny doradca<br/>interakcji lekowych
          </h1>
          <p className="text-white/70 text-sm leading-relaxed">
            System RAG oparty na LLM, który pomaga wykrywać potencjalnie
            niebezpieczne interakcje między lekami przepisanymi przez różnych lekarzy.
          </p>
        </div>

        <div className="space-y-3">
          {[
            { label: "Vanilla RAG", desc: "Klasyczne wyszukiwanie hybrydowe" },
            { label: "HyDE", desc: "Hipotетyczne rozszerzenie dokumentu" },
            { label: "Self-Reflection", desc: "Iteracyjna samoocena odpowiedzi" },
            { label: "Multi-Agent", desc: "Równoległe perspektywy agentów" },
          ].map((m) => (
            <div key={m.label} className="flex gap-3 items-start">
              <div className="w-1.5 h-1.5 rounded-full bg-white/50 mt-2 shrink-0" />
              <div>
                <p className="text-sm font-medium">{m.label}</p>
                <p className="text-xs text-white/60">{m.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Form panel */}
      <div className="flex-1 flex items-center justify-center p-8 bg-background">
        <div className="w-full max-w-sm">
          <div className="mb-8">
            <h2 className="text-2xl font-semibold text-foreground">Zaloguj się</h2>
            <p className="mt-1 text-sm text-muted-foreground">Wprowadź swoje dane aby kontynuować</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="email">Email</label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@medrag.local"
                required
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="password">Hasło</label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>

            {error && (
              <p className="text-sm text-destructive bg-destructive/10 px-3 py-2 rounded-md">{error}</p>
            )}

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Logowanie…" : "Zaloguj się"}
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}
