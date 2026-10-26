import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { research, type ResearchResult } from "./api";

export default function App() {
  const [topic, setTopic] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<ResearchResult | null>(null);

  async function run() {
    if (!topic.trim() || loading) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      setResult(await research(topic));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  function download() {
    if (!result) return;
    const refs = result.bibliography
      .map((s) => `[${s.id}] ${s.title}. ${s.url}`)
      .join("\n");
    const blob = new Blob([`${result.report}\n\n## Bibliography\n${refs}`], {
      type: "text/markdown",
    });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "research-report.md";
    a.click();
  }

  return (
    <main className="mx-auto max-w-3xl px-5 py-10 font-sans text-slate-900">
      <h1 className="font-serif text-3xl font-semibold">Research assistant</h1>
      <p className="mt-1 text-slate-600">
        Enter a topic. The agent searches, reads sources and writes a cited report.
      </p>

      <div className="mt-6 flex gap-2">
        <input
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          placeholder="e.g. How do solid-state batteries work?"
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 focus:outline-2 focus:outline-teal-700"
        />
        <button
          onClick={run}
          disabled={loading || !topic.trim()}
          className="rounded-md bg-teal-800 px-4 py-2 font-medium text-white hover:bg-teal-900 disabled:opacity-50"
        >
          {loading ? "Researching…" : "Research"}
        </button>
      </div>

      {loading && (
        <p className="mt-6 text-slate-600" role="status">
          Searching the web, reading sources and writing the report. This can
          take up to a minute.
        </p>
      )}

      {error && (
        <p className="mt-6 rounded-md border border-red-300 bg-red-50 p-3 text-red-800" role="alert">
          {error}
        </p>
      )}

      {result && (
        <article className="mt-8">
          <p className="text-sm text-slate-500">
            Searched for: {result.queries.join("; ")}
          </p>

          <div className="prose-report mt-4 space-y-3 font-serif text-lg leading-8 [&_h1]:text-2xl [&_h1]:font-semibold [&_h2]:mt-6 [&_h2]:text-xl [&_h2]:font-semibold [&_ul]:list-disc [&_ul]:pl-6">
            <ReactMarkdown>{result.report}</ReactMarkdown>
          </div>

          <section className="mt-8 border-t border-slate-300 pt-4">
            <h2 className="font-serif text-xl font-semibold">Bibliography</h2>
            <ol className="mt-2 space-y-1 text-sm">
              {result.bibliography.map((s) => (
                <li key={s.id}>
                  [{s.id}]{" "}
                  <a href={s.url} target="_blank" rel="noreferrer" className="text-teal-800 underline">
                    {s.title}
                  </a>
                </li>
              ))}
            </ol>
          </section>

          <button onClick={download} className="mt-6 rounded-md border border-slate-400 px-3 py-1.5 text-sm hover:bg-slate-100">
            Download as Markdown
          </button>
        </article>
      )}
    </main>
  );
}
