import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import { searchSymptom } from '../api/symptomSearch'

const SPECIALTY_ICONS = {
  Cardiology: '❤️',
  Dermatology: '🧴',
  Pediatrics: '🧸',
  Orthopedics: '🦴',
  'General Physician': '🩺',
}

export default function Home() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [result, setResult] = useState(null)

  const searchMutation = useMutation({
    mutationFn: searchSymptom,
    onSuccess: (data) => setResult(data),
  })

  function handleSearch(e) {
    e.preventDefault()
    if (!query.trim()) return
    setResult(null)
    searchMutation.mutate(query.trim())
  }

  const specialties = Object.keys(SPECIALTY_ICONS)

  return (
    <div className="animate-fade-in space-y-10">
      <section className="rounded-2xl bg-gradient-to-br from-brand-600 to-brand-800 px-6 py-10 text-center text-white sm:py-14">
        <h1 className="text-2xl font-bold sm:text-3xl">What's bothering you today?</h1>
        <p className="mt-2 text-sm text-brand-100 sm:text-base">
          Describe your symptoms and we'll point you to the right specialist.
        </p>
        <form onSubmit={handleSearch} className="mx-auto mt-6 flex max-w-lg flex-col gap-2 sm:flex-row">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. chest pain, skin rash, back pain..."
            className="flex-1 rounded-lg border-0 px-4 py-3 text-sm text-slate-900 shadow-sm focus:outline-none focus:ring-2 focus:ring-white"
          />
          <Button type="submit" variant="secondary" loading={searchMutation.isPending} className="justify-center">
            Search
          </Button>
        </form>
        {result && <SearchResult result={result} onBrowse={() => navigate('/doctors')} />}
        {searchMutation.isError && (
          <p className="mt-4 text-sm text-red-100">{searchMutation.error.message}</p>
        )}
      </section>

      <section>
        <h2 className="text-base font-semibold text-slate-800">Or browse by specialty</h2>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5">
          {specialties.map((s) => (
            <Card
              key={s}
              hoverable
              className="animate-scale-in cursor-pointer text-center"
              onClick={() => navigate(`/doctors?specialty=${encodeURIComponent(s)}`)}
            >
              <div className="text-2xl">{SPECIALTY_ICONS[s]}</div>
              <div className="mt-2 text-sm font-medium text-slate-700">{s}</div>
            </Card>
          ))}
        </div>
      </section>
    </div>
  )
}

function SearchResult({ result, onBrowse }) {
  if (result.match === null) {
    return (
      <div className="animate-slide-up mx-auto mt-5 max-w-lg rounded-lg bg-white/10 px-4 py-3 text-sm text-white">
        <p>{result.message || "We couldn't confidently match that — browse specialties below instead."}</p>
      </div>
    )
  }

  const confidenceLabel = result.source === 'exact' ? 'Good match' : 'Possible match'

  return (
    <div className="animate-slide-up mx-auto mt-5 max-w-lg rounded-lg bg-white px-4 py-4 text-left shadow-lg">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-brand-600">{confidenceLabel}</span>
        <span className="text-xs text-slate-400">source: {result.source}</span>
      </div>
      <p className="mt-1 text-sm text-slate-700">
        Based on what you described, we recommend <strong>{result.specialty}</strong>.
      </p>
      <div className="mt-3 flex gap-2">
        <Link specialty={result.specialty} />
        <button onClick={onBrowse} className="text-sm text-slate-500 underline">
          Browse all specialties
        </button>
      </div>
    </div>
  )
}

function Link({ specialty }) {
  const navigate = useNavigate()
  return (
    <Button
      size="sm"
      onClick={() =>
        navigate(
          `/doctors?specialty=${encodeURIComponent(specialty)}&matchReason=${encodeURIComponent(
            `Matched to "${specialty}" from your symptoms`,
          )}`,
        )
      }
    >
      See {specialty} doctors
    </Button>
  )
}
